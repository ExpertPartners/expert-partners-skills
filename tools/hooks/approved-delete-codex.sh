#!/bin/bash -p
# Delete one approved regular file from Codex, whose shell tools do not invoke
# Claude Code's PreToolUse hook automatically. The same guard checks, logs, and
# consumes the same single-use approval note before this script executes rm.

set -euo pipefail
PATH=/opt/homebrew/bin:/usr/bin:/bin
export PATH
[[ "$-" == *p* ]] || {
  printf 'Codex delete: invoke the executable or use bash -p\n' >&2
  exit 2
}

if [[ $# -ne 1 || -n "${BASH_ENV+x}" || -n "${ENV+x}" ]]; then
  printf 'Usage: %s <absolute regular-file path>\n' "$0" >&2
  exit 2
fi

target="$1"
script_dir=$(cd "$(dirname "$0")" && pwd -P)
[[ "${script_dir##*/}" == scripts ]] || {
  printf 'Codex delete: runner must be installed in a scripts directory\n' >&2
  exit 2
}
installation_home=$(dirname "$script_dir")
hook="$script_dir/pre-tool-use-enforcement.sh"
library="$script_dir/lib/deletion-approval-common.sh"
approval_dir="$installation_home/.claude/deletion-approvals"
approval_log="$installation_home/.claude/logs/deletion-approvals.log"

[[ "$target" == /Users/* && -f "$target" && ! -L "$target" ]] || {
  printf 'Codex delete: target must be an existing regular file under /Users\n' >&2
  exit 2
}
[[ "$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$target")" == "$target" ]] || {
  printf 'Codex delete: symlinked path ancestry is not supported\n' >&2
  exit 2
}
[[ -f "$hook" && -f "$library" ]] || {
  printf 'Codex delete: guard or approval library is missing\n' >&2
  exit 2
}

before=$(stat -f '%d:%i' "$target")
quoted=$(python3 -c 'import shlex,sys; print(shlex.quote(sys.argv[1]))' "$target")
# Use the guard's recursive-command check to require a note. The actual
# deletion below is file-only, so a raced-in directory cannot be removed.
command_text="rm -rf -- $quoted"
payload=$(jq -n --arg command "$command_text" --arg cwd "$PWD" \
  '{session_id:"codex-approved-delete",hook_event_name:"PreToolUse",cwd:$cwd,
    permission_mode:"default",tool_name:"Bash",tool_input:{command:$command}}')

if ! response=$(printf '%s' "$payload" | HOME="$installation_home" \
  DELETION_APPROVAL_LIB="$library" DELETION_APPROVAL_DIR="$approval_dir" \
  DELETION_APPROVAL_LOG="$approval_log" /bin/bash -p "$hook"); then
  printf 'Codex delete: guard denied the deletion\n' >&2
  exit 2
fi
if ! printf '%s' "$response" | jq -e \
  '.hookSpecificOutput.additionalContext | strings | startswith("ALLOWED by pre-tool-use-enforcement approval-note path:")' \
  >/dev/null; then
  printf 'Codex delete: guard did not consume an approval note\n' >&2
  exit 2
fi

[[ -f "$target" && ! -L "$target" && "$(stat -f '%d:%i' "$target")" == "$before" ]] || {
  printf 'Codex delete: target changed after guard approval\n' >&2
  exit 2
}
/bin/rm -f -- "$target"
[[ ! -e "$target" && ! -L "$target" ]] || {
  printf 'Codex delete: target still exists\n' >&2
  exit 1
}
printf 'Deleted through approval guard: %s\n' "$target"
