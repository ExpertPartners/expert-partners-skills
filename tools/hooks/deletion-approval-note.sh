#!/bin/bash -p
# M4 grants use a separate operation-bound store and fixed isolated interpreter.
case "${1:-}" in
  grant-m4-batch2)
    if [[ $# -lt 2 || $# -gt 3 || -n "${BASH_ENV+x}" || -n "${ENV+x}" ]]; then
      printf '%s\n' 'M4 approval: invalid arguments or shell startup override' >&2
      exit 2
    fi
    shift
    exec /opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/bin/python3.14 -I /Users/allisongaddy/HQ-AI-Workspace-M4/Workbench/scripts/lib/m4-batch2-executor.py grant "$@"
    exit 2
    ;;
  *m4-batch2*) printf '%s\n' 'M4 approval: unknown explicit mode' >&2; exit 2 ;;
esac
# deletion-approval-note.sh
# Writes single-use, expiring deletion approval notes that the
# pre-tool-use-enforcement hook honors.
#
# WHY THIS EXISTS
#   Ruled by Allison 2026-08-07. The guard blocks destructive deletes. Before
#   this, an explicitly approved deletion had no way THROUGH the guard, so an
#   approved delete got done by going AROUND it (shutil.rmtree). Bypassing is
#   now retired as a practice: an approved deletion is recorded as a note and
#   passes the guard, logged and consumed. No note, no pass.
#
# USAGE
#   deletion-approval-note.sh grant  --target <path> --quote "<Allison's words>" \
#                                    [--session "<session name>"] [--ttl <seconds>] \
#                                    [--host <ssh host>]
#   --host makes a note for a delete sent over ssh (for example to Ember's M2,
#   --host ember --target /tmp/scratch-x). It matches only that host and that
#   exact remote path. A remote path must be absolute or start with ~.
#   deletion-approval-note.sh list
#   deletion-approval-note.sh revoke --target <path>
#   deletion-approval-note.sh purge
#
# A note is written ONLY when Allison has given an explicit deletion approval
# in the session. The --quote is her actual words; it lands in the audit log.
# Notes expire (default 15 min, ceiling 1 hour) and are consumed on first use.

set -uo pipefail

LIB="${DELETION_APPROVAL_LIB:-$HOME/HQ-AI-Workspace-M4/Workbench/scripts/lib/deletion-approval-common.sh}"
if [[ ! -f "$LIB" ]]; then
  printf 'deletion-approval-note: missing library at %s\n' "$LIB" >&2
  exit 1
fi
# shellcheck source=lib/deletion-approval-common.sh
source "$LIB"

die() { printf 'deletion-approval-note: %s\n' "$1" >&2; exit 1; }

usage() {
  # Stable comment boundaries retain the original help despite the M4 prefix.
  sed -n '/^#   approved delete got done by going AROUND it/,/^# A note is written ONLY when Allison has given an explicit deletion approval/p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-1}"
}

command -v jq >/dev/null 2>&1 || die "jq is required"

CMD="${1:-}"
[[ -z "$CMD" ]] && usage 1
shift || true

# -------------------------------------------------------------------------
cmd_grant() {
  local target="" quote="" session="" host="" ttl="$DELETION_APPROVAL_TTL_DEFAULT"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --target)  target="${2:-}"; shift 2 ;;
      --quote)   quote="${2:-}"; shift 2 ;;
      --session) session="${2:-}"; shift 2 ;;
      --ttl)     ttl="${2:-}"; shift 2 ;;
      --host)    host="${2:-}"; [[ -n "$host" ]] || die "--host needs a value"; shift 2 ;;
      *) die "unknown argument: $1" ;;
    esac
  done

  [[ -n "$target" ]] || die "--target is required"
  [[ -n "$quote" ]]  || die "--quote is required (Allison's explicit approval, verbatim)"

  [[ "$ttl" =~ ^[0-9]+$ ]] || die "--ttl must be an integer number of seconds"
  (( ttl > 0 )) || die "--ttl must be greater than zero"
  if (( ttl > DELETION_APPROVAL_TTL_MAX )); then
    printf 'deletion-approval-note: ttl %ss exceeds the %ss ceiling, clamping to ceiling\n' \
      "$ttl" "$DELETION_APPROVAL_TTL_MAX" >&2
    ttl="$DELETION_APPROVAL_TTL_MAX"
  fi

  [[ -n "$session" ]] || session="${CLAUDE_SESSION_NAME:-unnamed-session}"

  local norm
  if [[ -n "$host" ]]; then
    norm=$(normalize_remote_key "$host" "$target") || die "remote target is not approvable (relative, path traversal, a whole disk or home folder, or a bad host): $host $target"
  else
    norm=$(normalize_target "$target" "$PWD" literal) || die "target is not approvable (path traversal or empty): $target"
  fi

  local now expires created hash notefile
  now=$(now_epoch)
  expires=$(( now + ttl ))
  created=$(date '+%Y-%m-%dT%H:%M:%S%z')
  hash=$(printf '%s' "$norm" | shasum -a 256 | cut -c1-12)
  mkdir -p "$DELETION_APPROVAL_DIR" || die "cannot create $DELETION_APPROVAL_DIR"
  chmod 700 "$DELETION_APPROVAL_DIR" 2>/dev/null || true
  notefile="$DELETION_APPROVAL_DIR/${now}-${hash}.json"

  jq -n \
    --arg target "$norm" \
    --arg raw_target "$target" \
    --arg host "$host" \
    --arg quote "$quote" \
    --arg session "$session" \
    --arg created_at "$created" \
    --argjson created_epoch "$now" \
    --argjson expires_epoch "$expires" \
    --argjson ttl_seconds "$ttl" \
    '{target:$target, raw_target:$raw_target, approval_quote:$quote,
      host:(if $host == "" then null else $host end),
      session_name:$session, created_at:$created_at,
      created_epoch:$created_epoch, expires_epoch:$expires_epoch,
      ttl_seconds:$ttl_seconds, single_use:true}' >"$notefile" \
    || die "failed writing note"
  chmod 600 "$notefile" 2>/dev/null || true

  da_log "GRANT" "target=$norm ttl=${ttl}s expires_epoch=$expires session=$session quote=$(printf '%s' "$quote" | tr '\n' ' ')"

  printf 'Approval note written.\n'
  printf '  target:  %s\n' "$norm"
  printf '  expires: %s (in %ss)\n' "$(date -r "$expires" '+%Y-%m-%d %I:%M:%S %p %Z' 2>/dev/null || printf 'epoch %s' "$expires")" "$ttl"
  printf '  note:    %s\n' "$notefile"
  printf '  single-use: the guard consumes this note on first matching delete.\n'
}

# -------------------------------------------------------------------------
cmd_list() {
  local now note nt ne state count=0
  now=$(now_epoch)
  if [[ ! -d "$DELETION_APPROVAL_DIR" ]]; then
    printf 'No approval notes (directory does not exist).\n'; return 0
  fi
  for note in "$DELETION_APPROVAL_DIR"/*.json; do
    [[ -f "$note" ]] || continue
    nt=$(jq -r '.target // "?"' "$note" 2>/dev/null)
    ne=$(jq -r '.expires_epoch // 0' "$note" 2>/dev/null)
    if [[ "$ne" =~ ^[0-9]+$ ]] && (( now < ne )); then
      state="LIVE ($(( ne - now ))s left)"
    else
      state="EXPIRED"
    fi
    printf '%-28s %s\n' "$state" "$nt"
    printf '  %s\n' "$(basename "$note")"
    count=$(( count + 1 ))
  done
  (( count == 0 )) && printf 'No approval notes.\n'
  return 0
}

# -------------------------------------------------------------------------
cmd_revoke() {
  local target="" host=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --target) target="${2:-}"; shift 2 ;;
      --host)   host="${2:-}"; shift 2 ;;
      *) die "unknown argument: $1" ;;
    esac
  done
  [[ -n "$target" ]] || die "--target is required"

  local norm note nt removed=0
  if [[ -n "$host" ]]; then
    # Fall back to the granted host and path when the login can't be read now.
    norm=$(normalize_remote_key "$host" "$target") || norm="$host:$target"
  else
    norm=$(normalize_target "$target" "$PWD" literal) || die "not a normalizable target: $target"
  fi
  [[ -d "$DELETION_APPROVAL_DIR" ]] || { printf 'No notes to revoke.\n'; return 0; }

  for note in "$DELETION_APPROVAL_DIR"/*.json; do
    [[ -f "$note" ]] || continue
    nt=$(jq -r '.target // ""' "$note" 2>/dev/null)
    # A remote note also matches on the host and path it was granted with, so
    # a later change to ~/.ssh/config (a new User line) can't hide it from revoke.
    if [[ -n "$host" ]] && jq -e --arg h "$host" --arg t "$target" \
        '.host == $h and .raw_target == $t' "$note" >/dev/null 2>&1; then
      nt="$norm"
    fi
    if [[ "$nt" == "$norm" ]]; then
      rm -f "$note" && removed=$(( removed + 1 ))
      da_log "REVOKE" "target=$norm note=$(basename "$note")"
    fi
  done
  printf 'Revoked %s note(s) for %s\n' "$removed" "$norm"
}

# -------------------------------------------------------------------------
cmd_purge() {
  local now note ne removed=0
  now=$(now_epoch)
  [[ -d "$DELETION_APPROVAL_DIR" ]] || { printf 'Nothing to purge.\n'; return 0; }
  for note in "$DELETION_APPROVAL_DIR"/*.json; do
    [[ -f "$note" ]] || continue
    ne=$(jq -r '.expires_epoch // 0' "$note" 2>/dev/null)
    if ! [[ "$ne" =~ ^[0-9]+$ ]] || (( now >= ne )); then
      rm -f "$note" && removed=$(( removed + 1 ))
      da_log "PURGE" "expired note removed: $(basename "$note")"
    fi
  done
  printf 'Purged %s expired note(s).\n' "$removed"
}

case "$CMD" in
  grant)  cmd_grant "$@" ;;
  list)   cmd_list "$@" ;;
  revoke) cmd_revoke "$@" ;;
  purge)  cmd_purge "$@" ;;
  -h|--help|help) usage 0 ;;
  *) die "unknown command: $CMD (expected grant, list, revoke, or purge)" ;;
esac
