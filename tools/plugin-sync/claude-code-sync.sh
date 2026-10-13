#!/usr/bin/env bash
# claude-code-sync.sh -- keep Claude Code current with this repo, once a day.
#
# Fired by ~/Library/LaunchAgents/com.expertpartners.claude-code-plugin-sync.plist
# at 7:40 AM. Refreshes the expert-partners marketplace, updates every installed
# plugin from it, and installs every plugin in the repo that is not installed
# yet, so Claude Code carries all of them. Silent on success. A failure shows up
# as drift in drift-check.py. Running sessions pick up changes after a restart.

set -uo pipefail

MARKETPLACE="expert-partners"
LOG_DIR="$HOME/Library/Logs/plugin-sync"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/claude-code-sync-$(date '+%Y-%m-%d').log"
log() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*" >>"$LOG"; }

CLAUDE="$(command -v claude 2>/dev/null || ls -1 "$HOME"/.nvm/versions/node/*/bin/claude 2>/dev/null | tail -1)"
[[ -n "$CLAUDE" && -x "$CLAUDE" ]] || { log "FAILED: claude binary not found"; exit 1; }

log "marketplace update $MARKETPLACE"
"$CLAUDE" plugin marketplace update "$MARKETPLACE" >>"$LOG" 2>&1 || { log "FAILED: marketplace update"; exit 1; }

MJ="$HOME/.claude/plugins/marketplaces/$MARKETPLACE/.claude-plugin/marketplace.json"
IJ="$HOME/.claude/plugins/installed_plugins.json"
names="$(python3 -c "import json,sys;print(' '.join(p['name'] for p in json.load(open(sys.argv[1]))['plugins']))" "$MJ")"
installed="$(python3 -c "import json,sys;d=json.load(open(sys.argv[1])).get('plugins',{});print(' '.join(k.split('@')[0] for k in d if k.endswith('@$MARKETPLACE')))" "$IJ" 2>/dev/null || true)"

rc=0
for p in $names; do
  if [[ " $installed " == *" $p "* ]]; then
    log "update $p"
    "$CLAUDE" plugin update "$p@$MARKETPLACE" >>"$LOG" 2>&1 || { log "FAILED: update $p"; rc=1; }
  else
    log "install $p"
    "$CLAUDE" plugin install "$p@$MARKETPLACE" >>"$LOG" 2>&1 || { log "FAILED: install $p"; rc=1; }
  fi
done
exit $rc
