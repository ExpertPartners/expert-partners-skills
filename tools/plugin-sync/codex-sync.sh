#!/usr/bin/env bash
# codex-sync.sh -- keep Codex current with this repo, once a day.
#
# Fired by ~/Library/LaunchAgents/com.expertpartners.codex-plugin-sync.plist at
# 7:30 AM. Runs `codex plugin marketplace upgrade expert-partners`, then installs
# every plugin in the marketplace that Codex does not have yet, except names
# listed in tools/plugin-sync/codex-skip.txt. Silent on success. A failure here
# shows up as drift in drift-check.py, which is the safety net.
#
# Official commands: developers.openai.com/plugins/build/plugins (read 2026-10-13).

set -uo pipefail

MARKETPLACE="expert-partners"
HERE="$(cd "$(dirname "$0")" && pwd)"
CODEX="${CODEX_BIN:-/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex}"
[[ -x "$CODEX" ]] || CODEX="$(command -v codex || true)"
LOG_DIR="$HOME/Library/Logs/plugin-sync"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/codex-sync-$(date '+%Y-%m-%d').log"

log() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*" >>"$LOG"; }

[[ -n "$CODEX" && -x "$CODEX" ]] || { log "FAILED: codex binary not found"; exit 1; }

log "upgrade $MARKETPLACE"
"$CODEX" plugin marketplace upgrade "$MARKETPLACE" >>"$LOG" 2>&1 || { log "FAILED: marketplace upgrade"; exit 1; }

SKIP="$HERE/codex-skip.txt"
missing="$("$CODEX" plugin list 2>/dev/null \
  | awk -v m="$MARKETPLACE" '$0 ~ "^Marketplace `" m "`" {f=1; next} /^Marketplace `/ {f=0} f && /not installed/ {split($1,a,"@"); print a[1]}')"

rc=0
for p in $missing; do
  if [[ -f "$SKIP" ]] && grep -qxF "$p" "$SKIP"; then log "skip $p (codex-skip.txt)"; continue; fi
  log "add $p@$MARKETPLACE"
  "$CODEX" plugin add "$p@$MARKETPLACE" >>"$LOG" 2>&1 || { log "FAILED: add $p"; rc=1; }
done
exit $rc
