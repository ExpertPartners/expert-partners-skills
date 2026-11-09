#!/usr/bin/env bash
# test-routing-check.sh
#
# Tests hooks/routing-check.sh (ADR 0015 UserPromptSubmit routing hook) after
# the 2026-09-08 narrowing (Startup Efficiency - Routing Simplification lane).
#
# Contract under test:
#   WARN   -- an ad hoc prompt typed in the Aura cwd that positively names a
#             per-project topic (PartnerSync build, GHL workflow build, Moxie).
#   SILENT -- cross-brand strategy prose; a topic named only inside a
#             negation or exclusion line (DO NOT / never / out of scope);
#             a structured dispatch envelope (SESSION NAME:, CLAUDE HOME:,
#             DESTINATION:, WORKTREE:, CONVERSATION: header lines), whose
#             destination the dispatcher already chose; any cwd outside
#             Aura; the kill switch.
#   Per-line matching: a positive line still warns when a negation line in
#   the same prompt names a different project.
#
# Exit 0 = all pass. Any failure prints and exits 1.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="${HOOK_UNDER_TEST:-$HERE/../routing-check.sh}"
AURA_CWD="$HOME/HQ-AI-Workspace-M4/Projects/Aura"
AURA_WT_CWD="$HOME/HQ-AI-Workspace-M4/Projects/Aura/.claude/worktrees/some-lane"
OTHER_CWD="$HOME/HQ-AI-Workspace-M4/Projects/PartnerSync"

PASS=0
FAIL=0

# run <expect: warn|silent> <cwd> <prompt> [expected-match-label]
run() {
  local expect="$1" cwd="$2" prompt="$3" label="${4:-}"
  local out rc actual="silent"
  out=$(jq -n --arg p "$prompt" --arg w "$cwd" \
    '{hook_event_name:"UserPromptSubmit", prompt:$p, cwd:$w, session_id:"test"}' \
    | ROUTING_CHECK_OFF="${ROUTING_CHECK_OFF:-}" bash "$HOOK" 2>&1)
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    FAIL=$((FAIL + 1))
    printf '  FAIL [hook exited %s] %s\n       output: %s\n' "$rc" "${prompt:0:70}" "${out:0:200}"
    return
  fi
  if printf '%s' "$out" | grep -q 'ROUTING MISMATCH'; then actual="warn"; fi
  if [[ "$actual" == "$expect" ]]; then
    if [[ "$actual" == "warn" && -n "$label" ]] && ! printf '%s' "$out" | grep -qF "($label)"; then
      FAIL=$((FAIL + 1))
      printf '  FAIL [warned, wrong project; want %s] %s\n       output: %s\n' "$label" "${prompt:0:70}" "${out:0:200}"
      return
    fi
    PASS=$((PASS + 1))
    printf '  ok   [%-6s] %s\n' "$expect" "${prompt//$'\n'/ | }"
  else
    FAIL=$((FAIL + 1))
    printf '  FAIL [want %s, got %s] %s\n       output: %s\n' "$expect" "$actual" "${prompt//$'\n'/ | }" "${out:0:200}"
  fi
}

echo "== MUST WARN: ad hoc per-project work typed in Aura =="
run warn "$AURA_CWD" "Let's build the PartnerSync S3 scenario today" "PartnerSync"
run warn "$AURA_CWD" "Add a GHL workflow trigger for EPIC onboarding" "GHL Automation"
run warn "$AURA_CWD" "Fix the Moxie listing page copy" "Moxie Signature Group"
run warn "$AURA_WT_CWD" "Build the GHL pipeline snapshot for the new location" "GHL Automation"
# per-line: a negation line about one project must not shield a positive line about another
run warn "$AURA_CWD" $'Never touch Moxie in this lane.\nNow build the GHL pipeline snapshot for EPIC.' "GHL Automation"

echo "== MUST STAY SILENT: cross-brand prose, negation lines, envelopes, other cwd, kill switch =="
run silent "$AURA_CWD" "Draft an ADR on the cross-brand routing architecture"
run silent "$AURA_CWD" "DO NOT touch GHL automation or PartnerSync in this lane."
run silent "$AURA_CWD" $'Boundaries:\n- Do not modify ghl-automation\n- Never open a PartnerSync scenario\n- Moxie is out of scope'
run silent "$AURA_CWD" "a routing hook falsely flagged GHL Automation even though the phrase appeared only inside a DO NOT list"
run silent "$AURA_CWD" $'SESSION NAME: Routing Simplification\n\nROOM: NORTH\nCLAUDE HOME: NORTH / Startup Efficiency\n\nMISSION\nAudit why the GHL Automation hook fired on a PartnerSync mention.'
run silent "$AURA_CWD" $'Ember Rail Repair\n\nCONVERSATION: Aura: Strategic Advisor / Ember Rail Repair\nSURFACE: chat conversation\nBuild the GHL workflow for the rail.'
run silent "$OTHER_CWD" "Let's build the PartnerSync S3 scenario today"
ROUTING_CHECK_OFF=1 run silent "$AURA_CWD" "Let's build the PartnerSync S3 scenario today"

echo
echo "PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
