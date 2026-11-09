#!/usr/bin/env bash
# test-git-identity-guard.sh
#
# Tests Rule 2b of ~/HQ-AI-Workspace-M4/Workbench/scripts/pre-tool-use-enforcement.sh: the unscoped git
# identity write guard added 2026-08-10 after the board-snapshot incident
# (aura doctrine/worktree-git-identity.md).
#
# Contract under test:
#   BLOCK  -- a SET of user.name/user.email with no --global/--worktree,
#             targeting a real clone (cwd, or the -C path if one is given).
#   ALLOW  -- reads, --unset/--unset-all, --global, --worktree, and any set
#             aimed at a disposable scratch clone.
#
# Exit 0 = all pass. Any failure prints and exits 1.

set -uo pipefail

HOOK="${HOOK_UNDER_TEST:-$HOME/HQ-AI-Workspace-M4/Workbench/scripts/pre-tool-use-enforcement.sh}"
REAL_CWD="$HOME/HQ-AI-Workspace-M4/Projects/Aura/worktrees/lane-commit-identity-fix"
SCRATCH_CWD="/private/tmp/claude-501/-Users-allisongaddy/deadbeef/scratchpad/aura-clone"

PASS=0
FAIL=0

# run <expect: block|allow> <cwd> <command...>
run() {
  local expect="$1" cwd="$2" cmd="$3"
  local out rc
  out=$(jq -n --arg c "$cmd" --arg w "$cwd" \
    '{tool_name:"Bash", tool_input:{command:$c}, cwd:$w, session_id:"test"}' \
    | bash "$HOOK" 2>&1)
  rc=$?

  local actual="allow"
  [[ "$rc" -eq 2 ]] && actual="block"

  if [[ "$actual" == "$expect" ]]; then
    PASS=$((PASS + 1))
    printf '  ok   [%-5s] %s\n' "$expect" "$cmd"
  else
    FAIL=$((FAIL + 1))
    printf '  FAIL [want %s, got %s] %s\n' "$expect" "$actual" "$cmd"
    printf '       output: %s\n' "${out:0:200}"
  fi
}

echo "== MUST BLOCK: unscoped identity sets in a real clone =="
run block "$REAL_CWD" 'git config user.name "board-snapshot"'
run block "$REAL_CWD" 'git config user.email "actions@users.noreply.github.com"'
run block "$REAL_CWD" 'git config --local user.name "board-snapshot"'
run block "$REAL_CWD" 'git config --local user.email "actions@users.noreply.github.com"'
# a CORRECT value is still a repo-local override, and doctrine forbids those
run block "$REAL_CWD" 'git config user.email "allison@expertpartners.com"'
run block "$REAL_CWD" 'git config user.name "Allison Gaddy"'
# -C form must resolve to the -C path, not cwd
run block "$SCRATCH_CWD" 'git -C ~/HQ-AI-Workspace-M4/Projects/Aura config user.name "board-snapshot"'
# chained behind another command
run block "$REAL_CWD" 'cd /tmp && git config user.name "board-snapshot"'
# the exact workflow lines that caused the incident
run block "$REAL_CWD" 'git config user.name "board-snapshot" && git config user.email "actions@users.noreply.github.com"'

echo
echo "== MUST ALLOW: reads and inspection =="
run allow "$REAL_CWD" 'git config user.name'
run allow "$REAL_CWD" 'git config --get user.name'
run allow "$REAL_CWD" 'git config --get-all user.email'
run allow "$REAL_CWD" 'git config --show-origin --show-scope --get-all user.email'
run allow "$REAL_CWD" 'git config --list'

echo
echo "== MUST ALLOW: the corrective unset (this is the fix) =="
run allow "$REAL_CWD" 'git config --local --unset-all user.name'
run allow "$REAL_CWD" 'git config --local --unset-all user.email'
run allow "$REAL_CWD" 'git config --unset user.name'

echo
echo "== MUST ALLOW: correctly scoped writes =="
run allow "$REAL_CWD" 'git config --global user.name "Allison Gaddy"'
run allow "$REAL_CWD" 'git config --global user.email "allison@expertpartners.com"'
run allow "$REAL_CWD" 'git config --worktree user.name "lane-bot"'

echo
echo "== MUST ALLOW: disposable scratch clones (sanctioned CI reproduction) =="
run allow "$SCRATCH_CWD" 'git config user.name "board-snapshot"'
run allow "$SCRATCH_CWD" 'git config user.email "actions@users.noreply.github.com"'
run allow "$REAL_CWD" 'git -C /private/tmp/claude-501/x/scratchpad/clone config user.name "board-snapshot"'

echo
echo "== MUST ALLOW: unrelated git config keys =="
run allow "$REAL_CWD" 'git config core.hooksPath /Users/allisongaddy/x'
run allow "$REAL_CWD" 'git config init.defaultBranch main'
run allow "$REAL_CWD" 'git config --local gc.auto 0'

echo
echo "== REGRESSION: pre-existing rules still fire =="
run block "$REAL_CWD" 'git push --force origin main'
run allow "$REAL_CWD" 'git push origin main'
run allow "$REAL_CWD" 'git status'

echo
echo "-------------------------------------------"
printf 'passed: %d   failed: %d\n' "$PASS" "$FAIL"
[[ "$FAIL" -eq 0 ]] || exit 1
echo "ALL GREEN"
