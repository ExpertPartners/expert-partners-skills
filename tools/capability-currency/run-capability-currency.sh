#!/usr/bin/env bash
# run-capability-currency.sh -- twice-monthly estate capability sweep runner.
#
# Fired by ~/Library/LaunchAgents/com.expertpartners.capability-currency.plist
# on the 1st and 15th at 7:00 AM CDT (after the 6:15 AM session janitor).
# The sweep itself is the capability-currency skill, canonical at
# expert-partners-skills plugins/research-ops/skills/capability-currency/SKILL.md (deployed copy
# at ~/.claude/skills/capability-currency/). This script only frames the run:
# heartbeat, kill switches, headless Claude invocation, logging.
#
# Heartbeat: healthchecks check capability-currency-m4. Ping URL lives in
# 1Password only (op://Automation/capability-currency-heartbeat/ping_url),
# never on disk (session-janitor precedent). Success ping only when the
# sweep exits clean; /fail pages on a crash; a run that never fires at all
# alerts through the check's own cron schedule (0 7 1,15 * * America/Chicago,
# 3h grace).
#
# Dry run: CAPABILITY_CURRENCY_DRY_RUN=1 skips the heartbeat and the sweep. It
# proves two things a headless run needs: the service account can read the
# Capability Watch Doc and add an entry to the Capability Refresh Changelog Doc,
# and claude -p can authenticate. Exit 0 only when both pass.
#
# Kill switches:
#   ~/.claude/backup-recovery-mode   estate-wide freeze (ADR 0003)
#   ~/.claude/capability-currency-off  this job only
#
# Built 2026-08-05 by the Capability Currency Build session per the locked
# Capability Currency plan (Allison, 2026-08-05). Moved 2026-10-13 from the aura
# repo (tools/capability-currency/) to expert-partners-skills in the clean-slate
# cutover. The run now writes the Capability Watch and Capability Refresh
# Changelog Docs in HQ Business Brain (Drive), not aura reference files.

set -uo pipefail

[[ -f "$HOME/.claude/backup-recovery-mode" ]] && exit 0
[[ -f "$HOME/.claude/capability-currency-off" ]] && exit 0

DRY_RUN="${CAPABILITY_CURRENCY_DRY_RUN:-}"
HEARTBEAT_OP_REF="op://Automation/capability-currency-heartbeat/ping_url"
SKILLS_HOME="$HOME/Claude/projects/ExpertPartnersSkills"
LOG_DIR="$HOME/Library/Logs/capability-currency"
mkdir -p "$LOG_DIR"
RUN_STAMP="$(date '+%Y-%m-%d')"
RUN_LOG="$LOG_DIR/run-$RUN_STAMP.log"

# launchd runs have no op token in env; ~/.zshenv is where it lives on the M4
# (session-janitor precedent). The URL is read at call time, never stored.
ping_url() {
  /bin/zsh -c "source ~/.zshenv 2>/dev/null; op read $HEARTBEAT_OP_REF" 2>/dev/null
}

ping_hc() { # $1 = "" | "/start" | "/fail"; $2 = body
  [[ -n "$DRY_RUN" ]] && return 0
  local url
  url="$(ping_url)"
  if [[ "$url" != https://* ]]; then
    echo "heartbeat: ping_url unreadable from 1Password, no ping sent" >&2
    return 0
  fi
  local attempt
  for attempt in 1 2 3; do
    curl -fsS -m 10 --data-raw "${2:-}" "${url}${1:-}" >/dev/null 2>&1 && return 0
    sleep 5
  done
  echo "heartbeat: ping undeliverable after 3 attempts" >&2
}

# Resolve claude across nvm node upgrades: PATH first, newest nvm bin second.
resolve_claude() {
  local c
  c="$(command -v claude 2>/dev/null)" && { echo "$c"; return 0; }
  c="$(ls -1 "$HOME"/.nvm/versions/node/*/bin/claude 2>/dev/null | tail -1)"
  [[ -n "$c" ]] && { echo "$c"; return 0; }
  return 1
}

ping_hc "/start" "capability-currency sweep starting $RUN_STAMP"

CLAUDE_BIN="$(resolve_claude)" || {
  ping_hc "/fail" "capability-currency: claude binary not found on PATH or under ~/.nvm"
  exit 1
}

# Long-lived claude -p login (claude setup-token, one year). Lives in 1Password
# only and is read at call time. When the item does not exist yet, the saved
# login is used instead, which can expire between runs.
TOKEN_REF="op://Automation/capability-currency-claude-token/credential"
tok="$(/bin/zsh -c "source ~/.zshenv 2>/dev/null; op read $TOKEN_REF" 2>/dev/null)"
[[ -n "$tok" ]] && export CLAUDE_CODE_OAUTH_TOKEN="$tok"
unset tok

WATCH_DOC="1aaWBVTySyMPfW9XFTiDRTy_Z3TnJKAXcc1BHJ1Nl09k"
CHANGELOG_DOC="1fGNxd_hsAIdnmKe7z677VYBuaR_szhSM9bbztbWEVQQ"
HERE="$(cd "$(dirname "$0")" && pwd)"
DRIVE="python3 $HERE/drive_docs.py"

dry_run() {
  local entry out
  entry="$(mktemp)"
  printf '## %s dry run\nHeadless dry run of the moved runner reached this Doc through the service account.\n' "$RUN_STAMP" >"$entry"
  $DRIVE read "$WATCH_DOC" | head -1 || { echo "DRY RUN FAILED: cannot read the Capability Watch Doc"; return 1; }
  $DRIVE prepend "$CHANGELOG_DOC" "$entry" || { echo "DRY RUN FAILED: cannot write the changelog Doc"; return 1; }
  $DRIVE read "$CHANGELOG_DOC" | grep -q "$RUN_STAMP dry run" || { echo "DRY RUN FAILED: entry not found on read-back"; return 1; }
  echo "DRIVE OK: read watch Doc, wrote and read back the changelog entry"
  out="$("$(resolve_claude)" -p "Reply with exactly: ok" --max-turns 1 --max-budget-usd 3 </dev/null 2>&1 | grep -v SEP-2352 | tail -3)"
  echo "CLAUDE: $out"
  [[ "$out" == *"Failed to authenticate"* || "$out" == *"Exceeded USD budget"* || "$out" != *ok* ]] \
    && { echo "DRY RUN FAILED: claude -p did not return ok"; return 1; }
  echo "DRY RUN OK"; return 0
}
[[ -n "$DRY_RUN" ]] && { dry_run; exit $?; }

PROMPT="Run the capability-currency skill now. This is the scheduled twice-monthly \
capability sweep on the M4 (launchd com.expertpartners.capability-currency, run of \
$RUN_STAMP). Execute the full sweep per the skill: all five heads, all five outputs, \
Firecrawl primary. Write the Capability Watch and Capability Refresh Changelog Docs \
and the run record in HQ Business Brain, Company Core. Use the Google Docs connector \
if you have it. If you do not (a long-lived token cannot reach connectors), use \
$HERE/drive_docs.py (read, prepend, replace) instead. Do not touch the \
capability-refresh skill. Nothing texts Allison \
unless she has an action to take, and any message honors the CI Alert Redesign three \
message rules."

cd "$SKILLS_HOME" || {
  ping_hc "/fail" "capability-currency: skills repo home missing at $SKILLS_HOME"
  exit 1
}

"$CLAUDE_BIN" -p "$PROMPT" \
  --permission-mode bypassPermissions \
  --max-turns 300 \
  --max-budget-usd 25 \
  --name "Capability Currency Sweep $RUN_STAMP" \
  >>"$RUN_LOG" 2>&1
STATUS=$?

if [[ $STATUS -eq 0 ]]; then
  ping_hc "" "capability-currency sweep $RUN_STAMP complete; log $RUN_LOG"
else
  ping_hc "/fail" "capability-currency sweep $RUN_STAMP exited $STATUS; log $RUN_LOG"
fi
exit $STATUS
