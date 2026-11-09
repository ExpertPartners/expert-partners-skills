#!/usr/bin/env bash
# routing-check.sh
# UserPromptSubmit hook: detect per-project topics typed into an Aura session.
# Reads stdin JSON from Claude Code (fields: cwd, prompt).
# Outputs additionalContext warning if mismatch detected; exits 0 silently otherwise.
#
# KILL-SWITCH (mirrors backup-claude-memory.sh pattern):
#   Sentinel file: touch ~/.claude/routing-check-off   -> disables the hook globally
#                  rm    ~/.claude/routing-check-off   -> re-enables
#   Env var:       ROUTING_CHECK_OFF=1                 -> disables for that launched session
# Use the sentinel during a GitHub reorg when you intentionally cross project lines.
#
# NARROWED 2026-09-08 (Startup Efficiency - Routing Simplification lane), under
# ADR 0015's own revisit clause ("if the keyword matcher produces too many false
# positives, tighten patterns"). Two tightenings, both pattern-scope only, the
# advisory contract is unchanged:
#   1. ENVELOPE TRUST. A prompt that carries a structured dispatch envelope
#      (a SESSION NAME:, SESSION:, CLAUDE HOME:, COWORK HOME:, DESTINATION:,
#      WORKTREE:, or CONVERSATION: header line at the start of a line) already
#      had its destination chosen by the dispatcher (decision 0072, Control
#      Tower owns routing) and is checked by the receiving session's own
#      envelope check (pin skill section 4, lane-spawn wrong-door rule). The
#      keyword matcher does not second-guess a declared destination.
#   2. NEGATION-LINE EXCLUSION. Lines that name a topic only to exclude it
#      (DO NOT, never, not in scope, out of scope, exclude, banned, retired,
#      superseded) are dropped before matching. Live false positive that
#      forced this: every NORTH dispatch whose DO NOT list said "GHL
#      Automation" fired a ROUTING MISMATCH in the Aura cwd (2026-09-07 and
#      2026-09-08 workers, plus the audit lane itself).
#   Matching is now per line: a positive line still fires even when a
#   negation line elsewhere in the same prompt names another project.
# Tests: hooks/tests/test-routing-check.sh (run against this file).

set -euo pipefail

INPUT=$(cat)

# Kill-switch: bail silently if disabled
if [[ -f "$HOME/.claude/routing-check-off" || "${ROUTING_CHECK_OFF:-}" == "1" ]]; then
  exit 0
fi

CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""')
RAW_PROMPT=$(printf '%s' "$INPUT" | jq -r '.prompt // ""')

# Only check when inside the Aura project home (including worktrees)
AURA_ROOT="$HOME/HQ-AI-Workspace-M4/Projects/Aura"
if [[ "$CWD" != "$AURA_ROOT" && "$CWD" != "$AURA_ROOT"/* ]]; then
  exit 0
fi

# Tightening 1 -- envelope trust. A structured dispatch envelope names its own
# destination; the receiving session's envelope check owns that verification.
if printf '%s\n' "$RAW_PROMPT" | grep -qiE '^[[:space:]]*(SESSION NAME|SESSION|CLAUDE HOME|COWORK HOME|DESTINATION|WORKTREE|CONVERSATION)[[:space:]]*:'; then
  exit 0
fi

# Tightening 2 -- drop negation and exclusion lines, then match per line.
# A topic named only to be excluded is not the topic of the session.
NEGATION_RE="do not|don'?t|never|not in scope|out of scope|exclud|banned|retired|supersed|off[- ]limits|leave alone|forbidden"
PROMPT=$(printf '%s\n' "$RAW_PROMPT" \
  | { grep -viE "$NEGATION_RE" || true; } \
  | tr '[:upper:]' '[:lower:]')

if [[ -z "${PROMPT//[[:space:]]/}" ]]; then
  exit 0
fi

MATCH=""
CORRECT_PATH=""

# PartnerSync -- GHL 4-subaccount sync, Make.com scenarios S1-S10, webhook sync infra
if printf '%s' "$PROMPT" | grep -qiE 'partnersync|partner sync|make\.com scenario|webhook.*sync|sync.*webhook|s[0-9]+ scenario|ghl.*subaccount|subaccount.*sync|new location.*launch|location.*migration'; then
  MATCH="PartnerSync"
  CORRECT_PATH="$HOME/HQ-AI-Workspace-M4/Projects/PartnerSync/"

# Moxie Signature Group -- North Dallas luxury RE
elif printf '%s' "$PROMPT" | grep -qiE '\bmoxie\b|north dallas.*real estate|moxie signature'; then
  MATCH="Moxie Signature Group"
  CORRECT_PATH="$HOME/HQ-AI-Workspace-M4/Projects/MoxieSignatureGroup/"

# Free Agent Movement -- require the full brand name or FAMOS to avoid false hits
elif printf '%s' "$PROMPT" | grep -qiE 'free agent movement|free agent formula|free agent nation|fam launch|fam cohort|\bfamos\b'; then
  MATCH="Free Agent Movement"
  CORRECT_PATH="$HOME/HQ-AI-Workspace-M4/Projects/FAM/"

# GHL Automation -- GHL-native workflow/pipeline/snapshot building. ghl-automation was split and
# retired 2026-09-08 (GHL Split lane): GHL reference truth is partnersync, executable automation
# source is partnersync-automation-backend, so this route now lands in the PartnerSync home.
elif printf '%s' "$PROMPT" | grep -qiE 'ghl (workflow|trigger|pipeline|snapshot|automation)|ghl-automation'; then
  MATCH="GHL Automation"
  CORRECT_PATH="$HOME/HQ-AI-Workspace-M4/Projects/PartnerSync/"

# HeyGen -- avatar video work
elif printf '%s' "$PROMPT" | grep -qiE '\bheygen\b'; then
  MATCH="HeyGen"
  CORRECT_PATH="$HOME/HQ-AI-Workspace-M4/Projects/HeyGen/"

# EPIC inner circle -- tight match to avoid false positives on the generic word "epic"
elif printf '%s' "$PROMPT" | grep -qiE 'epic inner circle|epic member|epic cohort|epic program|epic community|epic curriculum|epic event|epic resource|epic coaching|epic content|epic monthly|join epic'; then
  MATCH="EPIC (Inner Circle)"
  CORRECT_PATH="$HOME/HQ-AI-Workspace-M4/Projects/EPIC/"

# The Strong Ones -- community brand
elif printf '%s' "$PROMPT" | grep -qiE 'the strong ones|strong ones community|strong ones content|strong ones event|strong ones brand'; then
  MATCH="The Strong Ones"
  CORRECT_PATH="$HOME/HQ-AI-Workspace-M4/Projects/TheStrongOnes/"

# Book -- manuscript-level work (working title "You've Got a Friend")
elif printf '%s' "$PROMPT" | grep -qiE "book manuscript|book chapter|you.ve got a friend|manuscript.*chapter|chapter.*manuscript|book outline|book research|trust gap chapter|aria.*book|book.*aria"; then
  MATCH="Book"
  CORRECT_PATH="$HOME/HQ-AI-Workspace-M4/Projects/book/"

# eXp Explained 2.0
elif printf '%s' "$PROMPT" | grep -qiE 'exp explained|exp 2\.0|exp explained 2'; then
  MATCH="eXp Explained 2.0"
  CORRECT_PATH="$HOME/HQ-AI-Workspace-M4/Projects/eXpExplained2/"
fi

if [[ -z "$MATCH" ]]; then
  exit 0
fi

WARNING="ROUTING MISMATCH -- action required before continuing: This topic ($MATCH) belongs in $CORRECT_PATH, not Aura. Aura is for cross-brand strategy and architecture only. Do not proceed with the work. Instead, tell the user: 'This topic belongs in $CORRECT_PATH. Open a new session there: cd $CORRECT_PATH && claude. Run /session-closeout here first if any work was done in this session.'"

jq -n --arg w "$WARNING" '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$w}}'
