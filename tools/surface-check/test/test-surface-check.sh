#!/usr/bin/env bash
# Tests for scripts/surface-check.sh. Builds throwaway Claude Code and Codex plugin caches
# and a throwaway repo, points the script at them through its SURFACE_CHECK_* overrides,
# and checks each line and the exit code. Nothing outside the temp folder is touched.
#
# Run: bash tools/surface-check/test/test-surface-check.sh   (needs python3)
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
SC="$REPO_ROOT/scripts/surface-check.sh"
SKILL=file-to-knowledge-base-optimizer
PLUGIN=operating-doctrine
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0 FAIL=0
ok()  { PASS=$((PASS + 1)); echo "PASS $1"; }
bad() { FAIL=$((FAIL + 1)); echo "FAIL $1"; [ -n "${2:-}" ] && printf '%s\n' "$2" | sed 's/^/     /'; }
check() { if [ "$2" -eq 0 ]; then ok "$1"; else bad "$1" "${3:-}"; fi; }
has() { printf '%s\n' "$1" | grep -qF -- "$2"; }

MAIN_VERSION="$(python3 -c 'import json,sys;print(next(p["version"] for p in json.load(open(sys.argv[1]))["plugins"] if p["name"]==sys.argv[2]))' \
  "$REPO_ROOT/.claude-plugin/marketplace.json" "$PLUGIN")"
OLD_VERSION=0.0.1

# cache_plugin <cache root> <manifest dir> <version> -- one cached plugin copy holding the skill
cache_plugin() {
  local root="$1/expert-partners/$PLUGIN/$3"
  mkdir -p "$root/$2" "$root/skills/$SKILL"
  printf '{"name": "%s", "version": "%s"}\n' "$PLUGIN" "$3" > "$root/$2/plugin.json"
  printf -- '---\nname: %s\n---\n' "$SKILL" > "$root/skills/$SKILL/SKILL.md"
}

# A codex stand-in, so the PATH check passes wherever the test runs.
mkdir -p "$TMP/bin"
printf '#!/bin/sh\nexit 0\n' > "$TMP/bin/codex"
chmod +x "$TMP/bin/codex"
WITH_CODEX="$TMP/bin:$PATH"

run() { # run <claude cache> <codex cache> [PATH] -- sets OUT and RC
  OUT="$(SURFACE_CHECK_CLAUDE_CACHE="$1" SURFACE_CHECK_CODEX_CACHE="$2" PATH="${3:-$WITH_CODEX}" \
    bash "$SC" "$SKILL" 2>&1)"
  RC=$?
}

# ---- T1 main is VERIFIED with the plugin's current version ----
run "$TMP/none" "$TMP/none"
has "$OUT" "main: VERIFIED plugins/$PLUGIN/skills/$SKILL/SKILL.md, name matches, $PLUGIN $MAIN_VERSION in plugin.json and marketplace.json"
check "T1 main is VERIFIED with $PLUGIN $MAIN_VERSION" $? "$OUT"

# ---- T2 older cached versions are GAPs that name both versions and fail the run ----
cache_plugin "$TMP/old/claude" .claude-plugin "$OLD_VERSION"
cache_plugin "$TMP/old/codex" .codex-plugin "$OLD_VERSION"
run "$TMP/old/claude" "$TMP/old/codex"
has "$OUT" "Claude Code: GAP cache has $PLUGIN $OLD_VERSION, main has $MAIN_VERSION"
check "T2 Claude Code GAP names both versions" $? "$OUT"
has "$OUT" "Codex: GAP cache has $PLUGIN $OLD_VERSION, main has $MAIN_VERSION"
check "T2 Codex GAP names both versions" $? "$OUT"
[ "$RC" -ne 0 ]
check "T2 a GAP exits non-zero" $? "exit $RC"

# ---- T3 current caches are VERIFIED, MANUAL lines print and the run exits 0 ----
cache_plugin "$TMP/cur/claude" .claude-plugin "$OLD_VERSION"
cache_plugin "$TMP/cur/claude" .claude-plugin "$MAIN_VERSION"
cache_plugin "$TMP/cur/codex" .codex-plugin "$MAIN_VERSION"
run "$TMP/cur/claude" "$TMP/cur/codex"
has "$OUT" "Claude Code: VERIFIED $PLUGIN $MAIN_VERSION holds $SKILL"
check "T3 Claude Code VERIFIED when one cached copy matches main" $? "$OUT"
has "$OUT" "Codex: VERIFIED $PLUGIN $MAIN_VERSION holds $SKILL" && has "$OUT" "codex command at $TMP/bin/codex"
check "T3 Codex VERIFIED with the codex command found" $? "$OUT"
has "$OUT" "claude.ai chat: MANUAL browser check on Ember's M2" && has "$OUT" "Cowork: MANUAL browser check on Ember's M2"
check "T3 claude.ai chat and Cowork print MANUAL" $? "$OUT"
[ "$RC" -eq 0 ]
check "T3 MANUAL lines do not change the exit code" $? "exit $RC
$OUT"
[ "$(printf '%s\n' "$OUT" | grep -c .)" -eq 5 ]
check "T3 one line per surface" $? "$OUT"

# ---- T4 Codex is a GAP when the codex command is not on the PATH ----
if PATH=/usr/bin:/bin command -v codex >/dev/null 2>&1; then
  echo "SKIP T4 codex is installed in /usr/bin or /bin"
else
  run "$TMP/cur/claude" "$TMP/cur/codex" /usr/bin:/bin
  has "$OUT" "Codex: GAP" && has "$OUT" "the codex command is not on the PATH"
  check "T4 Codex GAP without the codex command" $? "$OUT"
  [ "$RC" -ne 0 ]
  check "T4 exits non-zero" $? "exit $RC"
fi

# ---- T5 a missing cache or a cache without the skill is a GAP ----
run "$TMP/none" "$TMP/cur/codex"
has "$OUT" "Claude Code: GAP no Claude Code plugin cache at $TMP/none"
check "T5 missing cache root is a GAP" $? "$OUT"
mkdir -p "$TMP/empty"
run "$TMP/empty" "$TMP/cur/codex"
has "$OUT" "Claude Code: GAP no copy of $SKILL from $PLUGIN in $TMP/empty"
check "T5 cache without the skill is a GAP" $? "$OUT"

# ---- T6 main GAPs in a fixture repo ----
FR="$TMP/repo"
mkdir -p "$FR/.claude-plugin" "$FR/plugins/$PLUGIN/.claude-plugin" "$FR/plugins/$PLUGIN/skills/$SKILL"
printf '{"name": "%s", "version": "1.0.0"}\n' "$PLUGIN" > "$FR/plugins/$PLUGIN/.claude-plugin/plugin.json"
printf '{"plugins": [{"name": "%s", "version": "1.0.1"}]}\n' "$PLUGIN" > "$FR/.claude-plugin/marketplace.json"
printf -- '---\nname: %s\n---\n' "$SKILL" > "$FR/plugins/$PLUGIN/skills/$SKILL/SKILL.md"
OUT="$(SURFACE_CHECK_REPO="$FR" SURFACE_CHECK_CLAUDE_CACHE="$TMP/cur/claude" SURFACE_CHECK_CODEX_CACHE="$TMP/cur/codex" \
  PATH="$WITH_CODEX" bash "$SC" "$SKILL" 2>&1)"; RC=$?
has "$OUT" "main: GAP $PLUGIN is 1.0.0 in plugin.json but 1.0.1 in marketplace.json" && [ "$RC" -ne 0 ]
check "T6 plugin.json and marketplace.json disagreeing is a GAP" $? "$OUT"
printf -- '---\nname: something-else\n---\n' > "$FR/plugins/$PLUGIN/skills/$SKILL/SKILL.md"
OUT="$(SURFACE_CHECK_REPO="$FR" bash "$SC" "$SKILL" 2>&1)"
has "$OUT" "main: GAP plugins/$PLUGIN/skills/$SKILL/SKILL.md name line is 'something-else', expected '$SKILL'"
check "T6 a wrong name line is a GAP" $? "$OUT"

# ---- T7 usage errors exit 2 ----
bash "$SC" >/dev/null 2>&1; rc=$?
[ "$rc" -eq 2 ]
check "T7 no argument exits 2" $? "exit $rc"
bash "$SC" ../etc >/dev/null 2>&1; rc=$?
[ "$rc" -eq 2 ]
check "T7 a path for a name exits 2" $? "exit $rc"

# ---- T8 read only ----
stamp() { ( cd "$1" && find . -print | LC_ALL=C sort && find . -type f -exec cat {} + ) | cksum; }
before="$(stamp "$TMP/cur") $(cd "$REPO_ROOT" && git status --porcelain | cksum)"
run "$TMP/cur/claude" "$TMP/cur/codex"
after="$(stamp "$TMP/cur") $(cd "$REPO_ROOT" && git status --porcelain | cksum)"
[ "$before" = "$after" ]
check "T8 the caches and the repo are unchanged after a run" $?

echo "surface-check tests: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
