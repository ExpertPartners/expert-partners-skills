#!/bin/bash -p
# Explicit M4 execution is a separate command, never a PreToolUse side effect.
# Fixed privileged startup ignores ENV/BASH_ENV and inherited shell functions.
if [[ $# -gt 0 ]]; then
  case "$1" in
    --execute-m4-batch2) _m4_mode=execute ;;
    --preview-m4-batch2) _m4_mode=preview ;;
    *) printf '%s\n' 'M4 guard: unknown explicit mode' >&2; exit 2 ;;
  esac
  if [[ $# -ne 2 || -n "${BASH_ENV+x}" || -n "${ENV+x}" ]]; then
    printf '%s\n' 'M4 guard: invalid arguments or shell startup override' >&2
    exit 2
  fi
  exec /opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/bin/python3.14 -I /Users/allisongaddy/HQ-AI-Workspace-M4/Workbench/scripts/lib/m4-batch2-executor.py "$_m4_mode" "$2"
  exit 2
fi
# pre-tool-use-enforcement.sh
# PreToolUse hook: block and warn on destructive commands on M4.
#
# Enforcement rules:
#   BLOCK: rm -rf on user-data paths (exit 2 + stderr → deny)
#          UNLESS an unexpired single-use approval note covers every target
#   BLOCK: git force-push to any branch (exit 2 + stderr → deny)
#   WARN:  git commit directly to main (additionalContext advisory)
#   WARN:  Write tool targeting ~/.claude/settings.json (requires explicit go)
#
# APPROVAL-NOTE PATH (added 2026-08-07, ruled by Allison):
#   An explicitly approved deletion goes THROUGH this guard, never around it.
#   The session writes a note with ~/HQ-AI-Workspace-M4/Workbench/scripts/deletion-approval-note.sh grant
#   (exact target, Allison's approval quote, session name, timestamp, short
#   expiry). On a matching destructive delete this hook honors an unexpired
#   note covering EVERY target in the command, logs the allowance with the
#   note contents, and consumes the note. No note, or an expired note, and the
#   block stands exactly as before. Bypassing this hook (shutil.rmtree or any
#   equivalent) is retired as a practice as of that ruling.
#   Audit log: ~/.claude/logs/deletion-approvals.log
#
# KILL-SWITCH:
#   Sentinel file: touch ~/.claude/pre-tool-use-enforcement-off
#                  rm    ~/.claude/pre-tool-use-enforcement-off
#   Env var:       PRE_TOOL_USE_OFF=1
#
# Reads JSON from stdin (fields: tool_name, tool_input, cwd, permission_mode).
# Block: exit 2 to stderr. Advisory: exit 0 + JSON additionalContext.
# References: code.claude.com/docs/en/claude-code/hooks (verified 2026-06-02)

set -uo pipefail

INPUT=$(cat)

# Kill-switch: bail silently if disabled
if [[ -f "$HOME/.claude/pre-tool-use-enforcement-off" || "${PRE_TOOL_USE_OFF:-}" == "1" ]]; then
  exit 0
fi

# -------------------------------------------------------------------------
# FAIL CLOSED (added 2026-10-25, Handoffs row "Finish AI HQ folder before
# checking 181 empty parent folders", step 4).
#
# Claude Code treats a hook that times out or exits with any status other than
# 2 as a NON-BLOCKING error and lets the tool call run. On 2026-10-25 a long rm
# overran the 10 second hook timeout and about 313 deletions ran with their
# approval notes unconsumed. This guard therefore refuses by itself, with exit
# 2, in every case it cannot finish deciding:
#   - jq is missing, or stdin is not a JSON object with a tool_name
#   - the guard runs past its own deadline (7 seconds, under the 10 second
#     harness timeout, so the refusal always lands first)
#   - any unexpected crash or exit status other than a deliberate 0 or 2
# The kill-switch above stays the only way to switch the guard off.
# -------------------------------------------------------------------------
GUARD_CLEAN_EXIT=0
GUARD_DEADLINE_SECONDS="${GUARD_DEADLINE_SECONDS:-7}"
GUARD_WATCHDOG_PID=""

guard_on_exit() {
  local rc=$?
  # A claimed but unconsumed approval note goes back where it was.
  declare -F release_claimed_notes >/dev/null 2>&1 && release_claimed_notes
  # Ignore a late TERM, then stop the watchdog subshell itself. Never kill its
  # sleep first: the subshell would move on and send the TERM we are avoiding.
  # The orphaned sleep holds no pipes and ends on its own.
  trap '' TERM
  if [[ -n "$GUARD_WATCHDOG_PID" ]]; then
    kill "$GUARD_WATCHDOG_PID" 2>/dev/null
  fi
  if [[ "$rc" -eq 2 ]] || { [[ "$rc" -eq 0 ]] && [[ "$GUARD_CLEAN_EXIT" -eq 1 ]]; }; then
    return 0
  fi
  printf '%s\n' "BLOCKED by pre-tool-use-enforcement: the guard ended unexpectedly (exit $rc) and fails closed. Nothing ran. Fix the guard or use the kill-switch ~/.claude/pre-tool-use-enforcement-off." >&2
  exit 2
}

guard_refuse() {
  printf '%s\n' "BLOCKED by pre-tool-use-enforcement: $1 The guard fails closed, so nothing ran." >&2
  exit 2
}

trap guard_on_exit EXIT
trap 'guard_refuse "the guard passed its ${GUARD_DEADLINE_SECONDS}s deadline."' TERM
# The watchdog must not hold the hook's stdout open, or the harness waits on it.
( sleep "$GUARD_DEADLINE_SECONDS"; kill -TERM "$$" 2>/dev/null ) >/dev/null 2>&1 </dev/null &
GUARD_WATCHDOG_PID=$!
disown "$GUARD_WATCHDOG_PID" 2>/dev/null

command -v jq >/dev/null 2>&1 || guard_refuse "jq is not available, so the hook input cannot be read."
printf '%s' "$INPUT" | jq -e 'type == "object" and ((.tool_name // "") | type == "string" and length > 0)' >/dev/null 2>&1 \
  || guard_refuse "the hook input is not a JSON object with a tool_name."

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""')
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""')
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // ""')

# -------------------------------------------------------------------------
# Approval-note library. FAIL CLOSED: if the library is unreadable, the
# approval path simply does not exist this run and every block stands as it
# did before the path was added. A missing library must never open the gate.
# -------------------------------------------------------------------------
DA_LIB="${DELETION_APPROVAL_LIB:-$HOME/HQ-AI-Workspace-M4/Workbench/scripts/lib/deletion-approval-common.sh}"
DA_AVAILABLE=0
if [[ -f "$DA_LIB" ]]; then
  # shellcheck source=lib/deletion-approval-common.sh
  if source "$DA_LIB" 2>/dev/null; then
    DA_AVAILABLE=1
  fi
fi

# -------------------------------------------------------------------------
# Helper: emit a block decision (deny) and exit
# -------------------------------------------------------------------------
block() {
  local reason="$1"
  printf '%s\n' "$reason" >&2
  # Also emit structured deny so Claude sees the reason in the UI
  jq -n --arg r "$reason" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 2
}

# -------------------------------------------------------------------------
# Helper: emit an advisory warning (allow but surface context)
# -------------------------------------------------------------------------
warn() {
  local msg="$1"
  jq -n --arg m "$msg" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$m}}'
  GUARD_CLEAN_EXIT=1
  exit 0
}

# -------------------------------------------------------------------------
# Helper: is the rm target(s) confined to an ephemeral scratch/clone path?
#
# Returns 0 (true) ONLY when EVERY non-flag path token in the captured rm
# command is a scratch path. If even one token is a non-scratch user-data
# path, returns 1 (false) so the full block stands. Narrow allowlist --
# it only ever turns a block into an allow, never the reverse.
#
# Scratch = session scratchpad base /private/tmp/claude-501/ , OR a repo
# clone/scratch glob: working/_clone_* , working/*.clone , */scratchpad/* .
# -------------------------------------------------------------------------
is_scratch_target() {
  local rmcmd="$1"
  local saw_path=0 tok
  for tok in $(printf '%s' "$rmcmd" | sed -E 's/^[[:space:];|&]*//; s/^rm[[:space:]]+//'); do
    [[ "$tok" == -* ]] && continue
    # path-traversal tokens are never exempt
    case "$tok" in *..*) return 1 ;; esac
    saw_path=1
    if printf '%s' "$tok" | grep -qE '(^|/)/private/tmp/claude-501/' \
      || printf '%s' "$tok" | grep -qE '(^|/)working/_clone_[^/]*' \
      || printf '%s' "$tok" | grep -qE '(^|/)working/[^/]*\.clone(/|$)' \
      || printf '%s' "$tok" | grep -qE '/scratchpad/'; then
      continue
    fi
    return 1
  done
  [[ "$saw_path" -eq 1 ]] && return 0
  return 1
}

# -------------------------------------------------------------------------
# Helper: emit an allowance and exit (approval-note path only)
#
# Emits NO permissionDecision at all -- exit 0 with additionalContext only.
# Per the hooks reference (code.claude.com/docs/en/hooks, verified
# 2026-08-07), exit 0 with no decision means "no decision; normal permission
# flow applies", which is exactly right: an approval note is authority to
# stop BLOCKING, not authority to also suppress Claude Code's own permission
# prompt. Every other guard in the stack stays intact.
#
# Why not "defer": the docs scope "defer" to non-interactive (-p) mode, and
# live testing 2026-08-07 confirmed it -- emitting defer in an interactive
# session made the harness fail the tool call with an internal error (the rm
# never ran, twice). Why not "allow": that skips the interactive permission
# prompt, which grants more than the note authorizes.
# -------------------------------------------------------------------------
allow_by_note() {
  local msg="$1"
  jq -n --arg m "$msg" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$m}}'
  GUARD_CLEAN_EXIT=1
  exit 0
}

# -------------------------------------------------------------------------
# Helper: does an unexpired approval note cover EVERY target in this rm?
#
# Returns 0 only when every non-flag path token normalizes cleanly AND has its
# own unexpired note. Partial coverage returns 1 and the block stands -- one
# approved path in a multi-path rm never carries the unapproved ones with it.
# On success, DA_MATCHED_NOTES holds the note files to consume.
# -------------------------------------------------------------------------
DA_MATCHED_NOTES=()
approval_covers_all_targets() {
  local rmcmd="$1" cwd="$2"
  local tok norm note saw_path=0
  DA_MATCHED_NOTES=()

  [[ "$DA_AVAILABLE" -eq 1 ]] || return 1

  # One pass over the notes directory for the whole command. Built here in the
  # main shell, not inside the $(find_approval_note) subshell, so the index is
  # reused for every target instead of re-reading every note once per target.
  da_build_index || return 1

  while IFS= read -r tok; do
    [[ -z "$tok" ]] && continue
    saw_path=1
    norm=$(normalize_target "$tok" "$cwd" literal) || return 1
    note=$(find_approval_note "$norm") || return 1
    DA_MATCHED_NOTES+=("$note")
  done < <(extract_rm_paths "$rmcmd")

  [[ "$saw_path" -eq 1 ]] || return 1
  [[ "${#DA_MATCHED_NOTES[@]}" -gt 0 ]] || return 1
  return 0
}

# Guarantee the array is defined even if the function never ran, so no code
# path can hit an unbound-variable crash (which would fail OPEN, see above).
DA_MATCHED_NOTES=("${DA_MATCHED_NOTES[@]+${DA_MATCHED_NOTES[@]}}")

# -------------------------------------------------------------------------
# Helper: does an unexpired note cover EVERY remote target of an ssh delete?
#
# Same contract as approval_covers_all_targets, for the "<host>:<path>" keys
# that ssh_delete_scan prints. On success DA_MATCHED_NOTES holds the notes.
# -------------------------------------------------------------------------
remote_approval_covers_all() {
  local scan="$1" line k note saw=0
  DA_MATCHED_NOTES=()
  [[ "$DA_AVAILABLE" -eq 1 ]] || return 1
  da_build_index || return 1
  while IFS= read -r line; do
    [[ "$line" == KEY\ * ]] || continue
    k="${line#KEY }"
    [[ -n "$k" ]] || return 1
    saw=1
    note=$(find_approval_note "$k") || return 1
    DA_MATCHED_NOTES+=("$note")
  done <<< "$scan"
  [[ "$saw" -eq 1 ]] || return 1
  [[ "${#DA_MATCHED_NOTES[@]}" -gt 0 ]] || return 1
  return 0
}

# -------------------------------------------------------------------------
# Helper: find a note for every target, then claim them all.
#
# A claim lost to a racing call rebuilds the index and tries again, so a second
# note for the same target can still be used. Three tries, then the block stands.
# -------------------------------------------------------------------------
cover_and_claim() {
  local kind="$1" tries=0
  while (( tries < 3 )); do
    tries=$(( tries + 1 ))
    if [[ "$kind" == remote ]]; then
      remote_approval_covers_all "$2" || return 1
    else
      approval_covers_all_targets "$2" "$3" || return 1
    fi
    claim_approval_notes ${DA_MATCHED_NOTES[@]+"${DA_MATCHED_NOTES[@]}"} && return 0
  done
  return 1
}

if [[ "$TOOL" == "Bash" ]]; then
  CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""')

  # -----------------------------------------------------------------------
  # Rule 0: BLOCK deletes and Trash moves sent over ssh (2026-11-01, Job
  # Tracker row 130). Ember's M2 is reached over ssh, so a delete there never
  # names a local path and Rule 1 cannot see it. Every ssh command is checked.
  # A remote delete passes only when an unexpired single-use note covers every
  # target by host AND path (grant with --host). Read-only ssh passes as before.
  # -----------------------------------------------------------------------
  # The cheap gate strips quotes and backslashes first, so "ssh", \ssh and
  # s''sh still reach the scanner. The scanner makes the real decision.
  if printf '%s' "$CMD" | tr -d "\"'\\\\" | grep -qE '(^|[^[:alnum:]_.-])(ssh|mosh|sftp|rsync)([^[:alnum:]_.-]|$)'; then
    SSH_HOLD="Get Allison's explicit yes for this exact remote path, record it, and retry, never bypass this hook: ~/HQ-AI-Workspace-M4/Workbench/scripts/deletion-approval-note.sh grant --host <ssh host> --target <exact remote path> --quote \"<her approval, verbatim>\" --session \"<session name>\"."
    if [[ "$DA_AVAILABLE" -ne 1 ]]; then
      # No library, no scanner. Fail closed on anything that looks like a delete.
      # Case variants name the same Trash on case-insensitive macOS volumes.
      if printf '%s' "$CMD" | tr -d "\"'\\\\" | grep -qE '(^|[^[:alnum:]_])(rm|rmdir|unlink|trash|shred|srm)([^[:alnum:]_-]|$)|-delete|--del|(^|[[:space:]/{,])\.[Tt][Rr][Aa][Ss][Hh]([Ee][Ss])?($|[[:space:]/;|&(),]|[*?$`{}<>]|\[|\])|git[[:space:]]+clean|osascript|rmtree|[|<]'; then
        block "BLOCKED by pre-tool-use-enforcement: a delete sent over ssh, and the approval library is missing, so it cannot be checked. Command: ${CMD:0:200}"
      fi
    else
      SSH_SCAN=$(ssh_delete_scan "$CMD") || SSH_SCAN="BLOCK the remote delete scanner failed."
      case "$SSH_SCAN" in
        NONE) : ;;
        TARGETS*)
          if cover_and_claim remote "$SSH_SCAN"; then
            commit_claimed_notes "remote session_id=$SESSION_ID cwd=$CWD cmd=${CMD:0:200}"
            allow_by_note "ALLOWED by pre-tool-use-enforcement approval-note path: an unexpired single-use note covered every remote target (host and path) in this ssh delete. The note(s) have been logged and consumed (${DA_SUMMARY% }); they will not authorize a second delete. Audit trail: ~/.claude/logs/deletion-approvals.log. Command: ${CMD:0:200}"
          fi
          SSH_TARGETS=$(printf '%s\n' "$SSH_SCAN" | sed -n 's/^KEY //p' | tr '\n' ' ')
          block "BLOCKED by pre-tool-use-enforcement: a delete sent over ssh with no approval note for every remote target (${SSH_TARGETS% }). $SSH_HOLD Command: ${CMD:0:200}"
          ;;
        BLOCK*)
          block "BLOCKED by pre-tool-use-enforcement: ${SSH_SCAN#BLOCK } $SSH_HOLD Command: ${CMD:0:200}"
          ;;
        *)
          block "BLOCKED by pre-tool-use-enforcement: the remote delete scanner gave an unreadable answer, so the guard fails closed. Command: ${CMD:0:200}"
          ;;
      esac
    fi
  fi

  # -----------------------------------------------------------------------
  # Rule 1: BLOCK rm -rf on user-data paths
  # -----------------------------------------------------------------------

  # Detect rm with recursive + force flags targeting user-data paths.
  # Match only when 'rm' appears as a standalone command token (start of string,
  # after whitespace, semicolon, pipe, or &&/||) -- avoids false positives on
  # 'rm -rf' appearing inside string literals in Python/shell scripts.
  # Preserve quoted separators in a standalone rm command. The approval
  # parser rejects unquoted separators before it can consume any note.
  if [[ "$CMD" =~ ^[[:space:]]*rm[[:space:]]+ ]]; then
    RM_CMD="$CMD"
  else
    RM_CMD=$(printf '%s' "$CMD" | grep -oE '(^|[;|&[:space:]])\s*rm\s+[^;|&]*' | head -1 || true)
  fi
  if [[ -n "$RM_CMD" ]]; then
    if printf '%s' "$RM_CMD" | grep -qE 'rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|-(rf|fr))'; then
      if printf '%s' "$RM_CMD" | grep -qE '(~/|/Users/|/home/)'; then
        # Narrow exemption: ephemeral scratch/clone paths proceed without the hold.
        if is_scratch_target "$RM_CMD"; then
          : # exempt -- scratch/clone path only; allow without hold
        elif cover_and_claim local "$RM_CMD" "$CWD"; then
          # Approval-note path: every target carries an unexpired single-use
          # note. Log the allowance with note contents, consume the notes, and
          # let the normal permission flow proceed from here.
          # bash 3.2 (system bash) errors on "${arr[@]}" for an empty array under
          # set -u, and a crashing hook exits 1 -> "non-blocking error, action
          # proceeds" -> fail OPEN. The ${arr[@]+...} idiom is 3.2-safe.
          commit_claimed_notes "session_id=$SESSION_ID cwd=$CWD cmd=${CMD:0:200}"
          allow_by_note "ALLOWED by pre-tool-use-enforcement approval-note path: an unexpired single-use deletion approval note covered every target in this command. The note(s) have been logged and consumed (${DA_SUMMARY% }); they will not authorize a second delete. Audit trail: ~/.claude/logs/deletion-approvals.log. Command: ${CMD:0:200}"
        else
          block "BLOCKED by pre-tool-use-enforcement: rm -rf targeting user-data path detected. Run the pre-flight jsonl check (count ~/.claude/projects/*/*.jsonl bound sessions) and get explicit approval before proceeding. If Allison HAS explicitly approved this deletion, record it and retry -- do not bypass this hook: ~/HQ-AI-Workspace-M4/Workbench/scripts/deletion-approval-note.sh grant --target <exact path> --quote \"<her approval, verbatim>\" --session \"<session name>\". Command: ${CMD:0:200}"
        fi
      fi
    fi
  fi

  # Rule 2: BLOCK git force-push (any variant)
  if printf '%s' "$CMD" | grep -qE 'git\s+push.*(--force|-f)\b|git\s+push.*--force-with-lease'; then
    block "BLOCKED by pre-tool-use-enforcement: force-push is not permitted without explicit Allison go. Describe why force-push is needed and get a per-step approval before retrying. Command: ${CMD:0:200}"
  fi

  # Rule 2b: BLOCK unscoped git identity writes in Allison's real clones
  #
  # Why: git worktree SHARES the parent repo's .git/config for user.name and
  # user.email. Those keys always land in the shared repo-local config unless
  # --global or --worktree is given, so one unscoped `git config user.name`
  # in ANY worktree silently rewrites the committer identity for every other
  # worktree of that repo, existing and future. This is exactly how the
  # 2026-08-07 board-snapshot incident put a CI-bot identity on 59 local lane
  # commits across aura. Canonical: aura doctrine/worktree-git-identity.md.
  #
  # Scope: SETS only. Reads (--get/--list/--show-origin/--show-scope) and the
  # corrective --unset/--unset-all stay allowed, as does anything explicitly
  # --global or --worktree, and any repo under a disposable scratch path
  # (doctrine's sanctioned way to reproduce a CI commit step locally).
  if printf '%s' "$CMD" | grep -qE 'git\s+(-C\s+[^[:space:]]+\s+)?(-c\s+[^[:space:]]+\s+)*config\b' \
    && printf '%s' "$CMD" | grep -qE 'user\.(name|email)[[:space:]]+[^[:space:]-]'; then
    if ! printf '%s' "$CMD" | grep -qE '\-\-(global|system|worktree|get|get-all|get-regexp|list|show-origin|show-scope|unset|unset-all)\b'; then
      # Resolve which repo this would poison: -C <path> if given, else cwd.
      GC_TARGET=$(printf '%s' "$CMD" | sed -nE 's/.*git[[:space:]]+-C[[:space:]]+([^[:space:]]+).*/\1/p')
      [[ -z "$GC_TARGET" ]] && GC_TARGET="$CWD"
      # Disposable scratch clones are the sanctioned place to do this.
      if ! printf '%s' "$GC_TARGET" | grep -qE '/private/tmp/claude-501/|/scratchpad/|/working/_clone_|/working/[^/]*\.clone(/|$)'; then
        block "BLOCKED by pre-tool-use-enforcement: unscoped git identity write. \`git config user.name/user.email\` without --global or --worktree writes to the SHARED repo-local .git/config, which silently rewrites the commit identity for EVERY worktree of this repo (this is the 2026-08-07 board-snapshot incident: 59 local lane commits landed under a CI-bot identity). Allison's standing convention is one global identity, Allison Gaddy <allison@expertpartners.com>, with no repo-local or worktree-local override anywhere. If you are setting the estate identity, use --global. If you are reproducing a CI workflow's commit step, do it in a disposable clone under a scratchpad path, never in ~/HQ-AI-Workspace-M4/Projects/. Reads and --unset are not blocked. Doctrine: aura doctrine/worktree-git-identity.md. Target repo: $GC_TARGET. Command: ${CMD:0:200}"
      fi
    fi
  fi

  # Rule 3: WARN on git commit directly to main (advisory only)
  if printf '%s' "$CMD" | grep -qE 'git\s+commit'; then
    BRANCH=$(git -C "$CWD" branch --show-current 2>/dev/null || true)
    if [[ "$BRANCH" == "main" ]]; then
      # Check if the commit is in a delegated category (Push-Policy trailer present)
      if ! printf '%s' "$CMD" | grep -qiE 'Push-Policy:'; then
        warn "ADVISORY (pre-tool-use-enforcement): You are committing directly to main with no Push-Policy trailer. Verify this commit falls into a delegated category (closeout/doctrine/adr/tracker/docs). If it is code, schema, or config -- stop and create a branch. Current branch: main, CWD: $CWD"
      fi
    fi
  fi

  # Rule 4: WARN on git reset --hard
  if printf '%s' "$CMD" | grep -qE 'git\s+reset\s+--hard'; then
    warn "ADVISORY (pre-tool-use-enforcement): git reset --hard detected. This is destructive and cannot be undone. Verify the target ref and that no unreachable commits will be lost. Command: ${CMD:0:200}"
  fi
fi

# -------------------------------------------------------------------------
# Rule 5: WARN on Write tool targeting sensitive config files
# -------------------------------------------------------------------------
if [[ "$TOOL" == "Write" ]]; then
  FILEPATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""')

  # ~/.claude/settings.json or settings.local.json
  if printf '%s' "$FILEPATH" | grep -qE '\.claude/settings(\.local)?\.json$'; then
    warn "ADVISORY (pre-tool-use-enforcement): Writing to Claude Code settings.json. This affects ALL sessions and hooks globally. Verify the exact change before proceeding. If you are adding a hook, confirm the hook script exists and is tested. File: $FILEPATH"
  fi

  # ~/.zshrc, ~/.bashrc, ~/.zprofile, ~/.bash_profile
  if printf '%s' "$FILEPATH" | grep -qE '(\.zshrc|\.bashrc|\.zprofile|\.bash_profile)$'; then
    warn "ADVISORY (pre-tool-use-enforcement): Writing to shell init file. Changes affect every new shell on M4. Verify the exact content before proceeding. File: $FILEPATH"
  fi
fi

GUARD_CLEAN_EXIT=1
exit 0
