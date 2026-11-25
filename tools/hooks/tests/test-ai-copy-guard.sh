#!/usr/bin/env bash
# test-ai-copy-guard.sh
#
# Contract under test for tools/hooks/ai-copy-guard.py:
#   BLOCK -- git clone, git worktree add and media or archive downloads whose
#            destination is outside the approved scratch roots.
#   ALLOW -- the same commands aimed at ~/HQ-AI-Workspace-M4/Scratch or a temp
#            folder, a deliberate canonical clone in Projects, and unrelated commands.
#
# Exit 0 = all pass. Any failure prints and exits 1.

set -uo pipefail

HOOK="${HOOK_UNDER_TEST:-$(cd "$(dirname "$0")/.." && pwd)/ai-copy-guard.py}"
WS="$HOME/HQ-AI-Workspace-M4"
WB="$WS/Workbench"
SC="$WS/Scratch"
PASS=0
FAIL=0

run() {
  local expect="$1" cwd="$2" cmd="$3" tool="${4:-Bash}"
  local out rc
  out=$(jq -n --arg c "$cmd" --arg w "$cwd" --arg t "$tool" \
    '{tool_name:$t, tool_input:{command:$c}, cwd:$w, session_id:"test"}' \
    | AI_COPY_GUARD_OFF= python3 "$HOOK" 2>&1)
  rc=$?
  local actual="allow"
  [[ "$rc" -eq 2 ]] && actual="block"
  if [[ "$actual" == "$expect" ]]; then
    PASS=$((PASS + 1)); printf '  ok   [%-5s] %s\n' "$expect" "$cmd"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL [want %s, got %s] %s\n' "$expect" "$actual" "$cmd"
    printf '       output: %s\n' "${out:0:240}"
  fi
}

echo "== MUST BLOCK: clones and worktrees outside scratch =="
run block "$WB" 'git clone https://github.com/ExpertPartners/hub.git hub-offer-ui'
run block "$WB" 'git clone https://github.com/ExpertPartners/hub.git'
run block "$HOME" 'git clone --depth 1 -b main https://github.com/ExpertPartners/hub.git ~/hub-copy'
run block "$SC" 'cd ~/HQ-AI-Workspace-M4/Workbench && git clone git@github.com:ExpertPartners/hub.git'
run block "$WS/Projects/Aura" 'git worktree add ../aura-lane-2 -b lane-2'
run block "$SC" 'git -C ~/HQ-AI-Workspace-M4/Projects/Aura worktree add ~/HQ-AI-Workspace-M4/Workbench/aura-x'
run block "$WB" 'git clone https://github.com/ExpertPartners/hub.git x' Execute
run block "$WB" 'git clone https://github.com/ExpertPartners/hub.git x' exec_command
run block "$WS/Projects" 'git clone https://github.com/ExpertPartners/hub.git hub-again'

echo
echo "== MUST BLOCK: heavy media or archives downloaded outside scratch =="
run block "$HOME/Downloads" 'curl -L -o talk.mp4 https://example.com/talk.mp4'
run block "$WB" 'curl -sLO https://example.com/footage.mov'
run block "$WB" 'curl -sLo ~/Desktop/clip.m4a https://example.com/clip'
run block "$WB" 'wget -O ~/Movies/take3.wav https://example.com/take3.wav'
run block "$WB" 'yt-dlp -P ~/Documents https://youtu.be/abc'
run block "$WB" 'gdown 1abcDEF -O ~/Desktop/'
run block "$WB" 'rclone copy gdrive:Video ~/Movies/from-drive'
run block "$WB" 'aws s3 cp s3://bucket/a.zip ./a.zip'

echo
echo "== MUST ALLOW: the same work inside the approved roots =="
run allow "$SC" 'git clone https://github.com/ExpertPartners/hub.git 20261125-hub-check'
run allow "$WB" 'git clone --depth 1 https://github.com/ExpertPartners/hub.git ~/HQ-AI-Workspace-M4/Scratch/20261125-hub'
run allow "$WS/Projects/Aura" 'git worktree add ~/HQ-AI-Workspace-M4/Scratch/20261125-aura-lane -b lane'
run allow "$WB" 'git clone https://github.com/ExpertPartners/hub.git /tmp/hub'
run allow "$WB" 'cd ~/HQ-AI-Workspace-M4/Scratch && git clone https://github.com/ExpertPartners/hub.git'
run allow "$WS/Projects" 'EP_CANONICAL_CLONE=1 git clone https://github.com/ExpertPartners/new-repo.git'
run allow "$WB" 'curl -L -o ~/HQ-AI-Workspace-M4/Scratch/20261125-voice/take.wav https://example.com/take.wav'
run allow "$WB" 'yt-dlp -P /tmp/clip https://youtu.be/abc'
run allow "$WB" 'rclone copy ~/HQ-AI-Workspace-M4/Scratch/x gdrive:Video'

echo
echo "== MUST ALLOW: unrelated commands =="
run allow "$WB" 'git status'
run allow "$WB" 'git worktree list'
run allow "$WB" 'git worktree remove ../old'
run allow "$WB" 'curl -s https://api.github.com/repos/x/y'
run allow "$WB" 'curl -o result.json https://api.example.com/x'
run allow "$WB" 'echo "git clone https://x/y.git"' 
run allow "$WB" 'git clone https://github.com/ExpertPartners/hub.git x' Read

echo
echo "-------------------------------------------"
printf 'passed: %d   failed: %d\n' "$PASS" "$FAIL"
[[ "$FAIL" -eq 0 ]] || exit 1
echo "ALL GREEN"
