#!/usr/bin/env bash
# test-m4-scratch-janitor.sh
#
# Builds a throwaway HOME with a bare remote and several clones, then checks that the
# janitor removes only what is safe:
#   REMOVE -- a pushed, clean, idle clone; a stale node_modules; an idle new scratch entry
#   KEEP   -- a clone with an unpushed commit, a clone with untracked work, a clone with a
#             stash, a clone with an ignored .env, a recently changed clone, and every
#             non-git file in a legacy entry
# Exit 0 = all pass.

set -uo pipefail
JANITOR="$(cd "$(dirname "$0")/.." && pwd)/m4-scratch-janitor.py"
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
export HOME="$T/home" GIT_CONFIG_GLOBAL="$T/gitconfig"
git config --global user.name test && git config --global user.email test@example.com
git config --global init.defaultBranch main
SC="$HOME/HQ-AI-Workspace-M4/Scratch"
mkdir -p "$SC" "$T/remote"
git init -q --bare "$T/remote/repo.git"
seed="$T/seed"; git clone -q "$T/remote/repo.git" "$seed" 2>/dev/null
echo hi > "$seed/a.txt"; printf '.env\nnode_modules/\n' > "$seed/.gitignore"
git -C "$seed" add . && git -C "$seed" commit -qm init && git -C "$seed" push -q origin main

mk() { git clone -q "$T/remote/repo.git" "$1" 2>/dev/null; }
old() { find "$1" -exec touch -h -t 202601010000 {} + ; }

mkdir -p "$SC/legacy-audit"
mk "$SC/legacy-audit/pushed";      old "$SC/legacy-audit/pushed"
mk "$SC/legacy-audit/unpushed";    echo x > "$SC/legacy-audit/unpushed/b.txt"
git -C "$SC/legacy-audit/unpushed" add . && git -C "$SC/legacy-audit/unpushed" commit -qm local; old "$SC/legacy-audit/unpushed"
mk "$SC/legacy-audit/untracked";   echo x > "$SC/legacy-audit/untracked/notes.md"; old "$SC/legacy-audit/untracked"
mk "$SC/legacy-audit/stashed";     echo y >> "$SC/legacy-audit/stashed/a.txt"; git -C "$SC/legacy-audit/stashed" stash -q; old "$SC/legacy-audit/stashed"
mk "$SC/legacy-audit/envfile";     echo K=1 > "$SC/legacy-audit/envfile/.env"; old "$SC/legacy-audit/envfile"
mk "$SC/legacy-audit/fresh"
mkdir -p "$SC/legacy-audit/app/node_modules/x"; echo 1 > "$SC/legacy-audit/app/node_modules/x/i.js"
echo keep > "$SC/legacy-audit/evidence.json"; old "$SC/legacy-audit/app"; old "$SC/legacy-audit/evidence.json"

STATE="$HOME/Library/Application Support/ExpertPartners/m4-scratch-janitor"
mkdir -p "$STATE"
# Mark everything present as legacy.
python3 -c "import json,time;print(json.dumps({'installed_at':time.time()+3600}))" > "$STATE/state.json"

PASS=0; FAIL=0
expect() { # expect gone|present path
  if [[ "$1" == gone && ! -e "$2" ]] || [[ "$1" == present && -e "$2" ]]; then
    PASS=$((PASS+1)); echo "  ok   [$1] ${2#$SC/}"
  else FAIL=$((FAIL+1)); echo "  FAIL [want $1] ${2#$SC/}"; fi
}

echo "== dry run removes nothing =="
python3 "$JANITOR" --dry-run >/dev/null
expect present "$SC/legacy-audit/pushed"

echo "== legacy rules =="
python3 "$JANITOR" > "$T/out.jsonl"
expect gone    "$SC/legacy-audit/pushed"
expect present "$SC/legacy-audit/unpushed"
expect present "$SC/legacy-audit/untracked"
expect present "$SC/legacy-audit/stashed"
expect present "$SC/legacy-audit/envfile"
expect present "$SC/legacy-audit/fresh"
expect gone    "$SC/legacy-audit/app/node_modules"
expect present "$SC/legacy-audit/app"
expect present "$SC/legacy-audit/evidence.json"
grep -q '"needs_person": true' "$T/out.jsonl" && { PASS=$((PASS+1)); echo "  ok   kept work is flagged for a person"; } || { FAIL=$((FAIL+1)); echo "  FAIL no needs_person flag"; }

echo "== new entries expire whole when idle and safe =="
python3 -c "import json;print(json.dumps({'installed_at':0}))" > "$STATE/state.json"
mkdir -p "$SC/20260101-old-task"; echo x > "$SC/20260101-old-task/log.txt"; old "$SC/20260101-old-task"
mkdir -p "$SC/20260101-unpushed"; mk "$SC/20260101-unpushed/r"; echo z > "$SC/20260101-unpushed/r/c.txt"
git -C "$SC/20260101-unpushed/r" add . && git -C "$SC/20260101-unpushed/r" commit -qm z; old "$SC/20260101-unpushed"
mkdir -p "$SC/20991231-today"; echo x > "$SC/20991231-today/now.txt"
python3 "$JANITOR" >/dev/null
expect gone    "$SC/20260101-old-task"
expect present "$SC/20260101-unpushed"
expect present "$SC/20991231-today"

echo "== leftover linked worktrees in Projects =="
P="$HOME/HQ-AI-Workspace-M4/Projects/App"; mk "$P"
git -C "$P" worktree add -q "$P/worktrees/lane-done" -b lane-done 2>/dev/null
git -C "$P/worktrees/lane-done" push -q origin lane-done 2>/dev/null
git -C "$P" worktree add -q "$P/worktrees/lane-open" -b lane-open 2>/dev/null
echo w > "$P/worktrees/lane-open/w.txt"
old "$P/worktrees"
python3 "$JANITOR" >/dev/null
expect gone    "$P/worktrees/lane-done"
expect present "$P/worktrees/lane-open"
expect present "$P/a.txt"
git -C "$P" worktree list | grep -q lane-done && { FAIL=$((FAIL+1)); echo "  FAIL worktree not pruned"; } || { PASS=$((PASS+1)); echo "  ok   worktree metadata pruned"; }

echo "-------------------------------------------"
printf 'passed: %d   failed: %d\n' "$PASS" "$FAIL"
[[ "$FAIL" -eq 0 ]] || exit 1
echo "ALL GREEN"
