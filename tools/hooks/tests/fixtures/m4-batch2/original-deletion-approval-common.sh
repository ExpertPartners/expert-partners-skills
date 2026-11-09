#!/usr/bin/env bash
# deletion-approval-common.sh
# Shared definitions for the deletion approval-note path.
#
# Sourced by BOTH:
#   ~/HQ-AI-Workspace-M4/Workbench/scripts/deletion-approval-note.sh      (writes notes)
#   ~/HQ-AI-Workspace-M4/Workbench/scripts/pre-tool-use-enforcement.sh    (reads, honors, consumes notes)
#
# Both sides MUST agree byte-for-byte on what "the exact target path" means,
# which is why normalization lives here once instead of twice.
#
# Ruled by Allison 2026-08-07: an approved deletion goes THROUGH the guard via
# an approval note, never around it. See ~/.claude/rules/behavior-defaults.md.

# Where notes live. One file per granted approval.
DELETION_APPROVAL_DIR="${DELETION_APPROVAL_DIR:-$HOME/.claude/deletion-approvals}"

# Append-only audit log of grants, allowances, consumptions, and expiry rejects.
DELETION_APPROVAL_LOG="${DELETION_APPROVAL_LOG:-$HOME/.claude/logs/deletion-approvals.log}"

# Default note lifetime, and the hard ceiling a caller may request.
# Short by design: a stale approval must die on its own, not linger.
DELETION_APPROVAL_TTL_DEFAULT="${DELETION_APPROVAL_TTL_DEFAULT:-900}"    # 15 minutes
DELETION_APPROVAL_TTL_MAX="${DELETION_APPROVAL_TTL_MAX:-3600}"           # 1 hour ceiling

# -------------------------------------------------------------------------
# now_epoch -- seconds since epoch (portable)
# -------------------------------------------------------------------------
now_epoch() { date +%s; }

# -------------------------------------------------------------------------
# da_log <event> <message>
#
# Appends one timestamped line to the audit log. Never fails the caller:
# a logging problem must not turn into a guard failure in either direction.
# -------------------------------------------------------------------------
da_log() {
  local event="$1" msg="$2" ts
  ts=$(date '+%Y-%m-%dT%H:%M:%S%z')
  mkdir -p "$(dirname "$DELETION_APPROVAL_LOG")" 2>/dev/null || true
  printf '%s [%s] %s\n' "$ts" "$event" "$msg" >>"$DELETION_APPROVAL_LOG" 2>/dev/null || true
}

# -------------------------------------------------------------------------
# normalize_target <raw-token> <cwd>
#
# Turns a path token into the single canonical form both sides compare on.
# Prints the normalized path on stdout and returns 0, or returns 1 when the
# token must never be matchable by a note.
#
# Rules:
#   - surrounding single/double quotes stripped
#   - a token containing '..' is REJECTED (path traversal is never approvable,
#     matching the existing is_scratch_target stance in the hook)
#   - glob metacharacters (* ? [ ]) are REJECTED: an approval note names one
#     exact target, and a glob is not one exact target
#   - leading ~ expands to $HOME
#   - relative paths resolve against <cwd>
#   - '//' collapses, '/./' collapses, trailing '/' stripped (except root)
#
# Deliberately LEXICAL only -- no symlink resolution. The target of a delete
# may be about to stop existing, and realpath's behavior on a missing path is
# not uniform across platforms. Lexical normalization is deterministic on both
# sides, which is the property that matters here.
# -------------------------------------------------------------------------
normalize_target() {
  local tok="$1" cwd="${2:-}"

  # strip one layer of surrounding quotes
  case "$tok" in
    \"*\") tok="${tok#\"}"; tok="${tok%\"}" ;;
    \'*\') tok="${tok#\'}"; tok="${tok%\'}" ;;
  esac

  [[ -z "$tok" ]] && return 1

  # never approvable
  case "$tok" in
    *..*) return 1 ;;
    *\**|*\?*|*\[*|*\]*) return 1 ;;
  esac

  # tilde expansion
  if [[ "$tok" == "~" ]]; then
    tok="$HOME"
  elif [[ "$tok" == "~/"* ]]; then
    tok="$HOME/${tok#\~/}"
  fi

  # resolve relative against cwd
  if [[ "$tok" != /* ]]; then
    [[ -z "$cwd" ]] && return 1
    tok="$cwd/$tok"
  fi

  # Collapse /./ and duplicate slashes.
  #
  # Done with sed, NOT bash ${var//pat/repl}, on purpose. System bash on macOS
  # is 3.2, and its replacement handling is a trap here: the inline form
  # ${tok//\/.\//\/} takes the replacement literally and yields 'working\/_test',
  # while the quoted-variable form ${tok//"$p"/"$r"} yields 'working"/"_test'.
  # Both silently break matching, so two spellings of the same path stop
  # matching one note. sed behaves identically on every bash we run.
  # The :a/ta loop re-runs the /./ rule so overlapping cases (/././) collapse.
  tok=$(printf '%s' "$tok" | sed -e ':a' -e 's|/\./|/|g' -e 'ta' -e 's|//*|/|g') || return 1
  [[ -z "$tok" ]] && return 1
  [[ "$tok" == */. ]] && tok="${tok%/.}"

  # strip trailing slashes, but keep root as "/"
  while [[ "$tok" == */ && "$tok" != "/" ]]; do tok="${tok%/}"; done

  [[ -z "$tok" ]] && tok="/"
  printf '%s' "$tok"
  return 0
}

# -------------------------------------------------------------------------
# extract_rm_paths <rm-command-fragment>
#
# Prints one raw (un-normalized) path token per line from an rm command
# fragment, skipping the 'rm' word itself and every -flag. Callers normalize.
# -------------------------------------------------------------------------
extract_rm_paths() {
  local rmcmd="$1" tok
  for tok in $(printf '%s' "$rmcmd" | sed -E 's/^[[:space:];|&]*//; s/^rm[[:space:]]+//'); do
    [[ "$tok" == -* ]] && continue
    printf '%s\n' "$tok"
  done
}

# -------------------------------------------------------------------------
# find_approval_note <normalized-target>
#
# Prints the path of ONE unexpired note file covering exactly this target,
# and returns 0. Returns 1 when no such note exists.
#
# Expired notes matching the target are logged as rejects and left on disk
# for the purge path -- an expired note must behave exactly like no note.
# -------------------------------------------------------------------------
find_approval_note() {
  local want="$1" note now nt ne
  now=$(now_epoch)
  [[ -d "$DELETION_APPROVAL_DIR" ]] || return 1

  for note in "$DELETION_APPROVAL_DIR"/*.json; do
    [[ -f "$note" ]] || continue
    nt=$(jq -r '.target // ""' "$note" 2>/dev/null) || continue
    [[ "$nt" == "$want" ]] || continue
    ne=$(jq -r '.expires_epoch // 0' "$note" 2>/dev/null) || continue
    if [[ "$ne" =~ ^[0-9]+$ ]] && (( now < ne )); then
      printf '%s' "$note"
      return 0
    fi
    da_log "EXPIRED-REJECT" "note=$note target=$nt expired_epoch=$ne now=$now -- treated as no note, delete stays blocked"
  done
  return 1
}

# -------------------------------------------------------------------------
# consume_approval_note <note-file> <context>
#
# Logs the full note contents, then deletes the note. Single-use by design:
# one grant authorizes exactly one delete.
# -------------------------------------------------------------------------
consume_approval_note() {
  local note="$1" ctx="${2:-}" body
  body=$(jq -c '.' "$note" 2>/dev/null || printf '<unreadable>')
  da_log "ALLOW" "context=$ctx note=$(basename "$note") contents=$body"
  rm -f "$note" 2>/dev/null || true
  da_log "CONSUMED" "note=$(basename "$note") -- single-use note removed"
}
