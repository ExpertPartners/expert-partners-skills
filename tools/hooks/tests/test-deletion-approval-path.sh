#!/usr/bin/env bash
# test-deletion-approval-path.sh
# Tests for the approval-note path in pre-tool-use-enforcement.sh.
#
# Run:  ~/HQ-AI-Workspace-M4/Workbench/scripts/tests/test-deletion-approval-path.sh
#
# Fully hermetic. Every note and log write is redirected into a temp dir via
# DELETION_APPROVAL_DIR / DELETION_APPROVAL_LOG, so the real notes directory at
# ~/.claude/deletion-approvals is never touched and no test can grant a real
# approval. No test deletes anything: the hook is driven with synthetic stdin
# and only its DECISION is inspected.
#
# The four required cases (ruled 2026-08-07):
#   1. blocked without a note
#   2. allowed with a note
#   3. note consumed after one use (second identical delete blocks again)
#   4. expired note blocks
# Plus regression cases proving nothing about existing behavior moved.

set -uo pipefail

HOOK="${HOOK:-$HOME/HQ-AI-Workspace-M4/Workbench/scripts/pre-tool-use-enforcement.sh}"
GRANT="${GRANT:-$(cd "$(dirname "$HOOK")" && pwd)/deletion-approval-note.sh}"
# Test the library that sits beside the hook under test, not whatever is deployed.
export DELETION_APPROVAL_LIB="${DELETION_APPROVAL_LIB:-$(cd "$(dirname "$HOOK")" && pwd)/lib/deletion-approval-common.sh}"
REAL_LIB="$DELETION_APPROVAL_LIB"

PASS=0
FAIL=0
RED=$'\033[31m'; GREEN=$'\033[32m'; DIM=$'\033[2m'; RESET=$'\033[0m'

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/da-test.XXXXXX") || { echo "mktemp failed"; exit 1; }
export DELETION_APPROVAL_DIR="$TMPROOT/notes"
export DELETION_APPROVAL_LOG="$TMPROOT/audit.log"
mkdir -p "$DELETION_APPROVAL_DIR"

# A stand-in for ssh -G, so remote keys resolve the same way on any runner.
# A target with user@ logs in as that user. The alias rootbox has User root in
# its config. Every other alias logs in as ember, as Ember's M2 does.
mkdir -p "$TMPROOT/bin"
cat > "$TMPROOT/bin/ssh" <<'FAKESSH'
#!/usr/bin/env bash
[[ "${1:-}" == "-G" ]] || exit 255
t="${!#}"
l=""
while [[ $# -gt 1 ]]; do
  case "$1" in
    -l) l="$2"; shift ;;
    -o) case "$2" in User=*|user=*) l="${2#*=}" ;; esac; shift ;;
  esac
  shift
done
if [[ -n "$l" ]]; then printf 'user %s\nhostname %s\n' "$l" "${t#*@}"; exit 0; fi
case "$t" in
  *@*) printf 'user %s\nhostname %s\n' "${t%%@*}" "${t#*@}" ;;
  rootbox) printf 'user root\nhostname rootbox\n' ;;
  *) printf 'user ember\nhostname %s\n' "$t" ;;
esac
FAKESSH
chmod +x "$TMPROOT/bin/ssh"
export DELETION_APPROVAL_SSH_BIN="$TMPROOT/bin/ssh"

cleanup() { rm -rf "$TMPROOT"; }
trap cleanup EXIT

# A fake user-data target. Never created, never deleted -- the hook decides on
# the command string, so the path does not need to exist.
TARGET="$HOME/HQ-AI-Workspace-M4/Projects/Aura/working/_test_approval_target"

# -------------------------------------------------------------------------
# run_hook <command> [cwd]  -> prints "<exit_code>|<stdout>"
# -------------------------------------------------------------------------
run_hook() {
  local cmd="$1" cwd="${2:-$HOME/HQ-AI-Workspace-M4/Projects/Aura}" out rc
  out=$(jq -n --arg c "$cmd" --arg w "$cwd" \
    '{session_id:"test-session",hook_event_name:"PreToolUse",cwd:$w,permission_mode:"default",tool_name:"Bash",tool_input:{command:$c}}' \
    | bash "$HOOK" 2>/dev/null)
  rc=$?
  printf '%s|%s' "$rc" "$out"
}

decision_of() { printf '%s' "${1#*|}" | jq -r '.hookSpecificOutput.permissionDecision // "none"' 2>/dev/null || printf 'none'; }
rc_of() { printf '%s' "${1%%|*}"; }

check() {
  local label="$1" want="$2" got="$3"
  if [[ "$want" == "$got" ]]; then
    printf '  %sPASS%s %s\n' "$GREEN" "$RESET" "$label"
    PASS=$(( PASS + 1 ))
  else
    printf '  %sFAIL%s %s\n        expected: %s\n        actual:   %s\n' "$RED" "$RESET" "$label" "$want" "$got"
    FAIL=$(( FAIL + 1 ))
  fi
}

grant_note() {
  local target="$1" ttl="${2:-900}"
  bash "$GRANT" grant --target "$target" \
    --quote "yes, delete it -- test fixture" \
    --session "Aura - Code Rule Fix - Guard Approval Path" \
    --ttl "$ttl" >/dev/null 2>&1
}

# Writes a note that is already expired. Built directly rather than by granting
# a 1-second note and sleeping, so the test is deterministic, not timing-flaky.
grant_expired_note() {
  local target="$1" past
  past=$(( $(date +%s) - 60 ))
  jq -n --arg t "$target" --argjson ce "$(( past - 900 ))" --argjson ee "$past" \
    '{target:$t,raw_target:$t,approval_quote:"expired test fixture",
      session_name:"Aura - Code Rule Fix - Guard Approval Path",
      created_at:"2026-08-07T00:00:00-0500",created_epoch:$ce,
      expires_epoch:$ee,ttl_seconds:900,single_use:true}' \
    >"$DELETION_APPROVAL_DIR/expired-fixture.json"
}

reset_notes() { rm -rf "$DELETION_APPROVAL_DIR"; mkdir -p "$DELETION_APPROVAL_DIR"; }

printf '\n%sApproval-note path -- pre-tool-use-enforcement.sh%s\n' "$DIM" "$RESET"
printf '%shook:  %s%s\n' "$DIM" "$HOOK" "$RESET"
printf '%snotes: %s (temp, isolated)%s\n\n' "$DIM" "$DELETION_APPROVAL_DIR" "$RESET"

# =========================================================================
printf 'THE FOUR REQUIRED CASES\n'
# =========================================================================

# --- 1. blocked without a note -------------------------------------------
reset_notes
R=$(run_hook "rm -rf $TARGET")
check "1. blocked without a note (exit 2)"        "2"    "$(rc_of "$R")"
check "1. blocked without a note (deny emitted)"  "deny" "$(decision_of "$R")"

# --- 2. allowed with a note ----------------------------------------------
reset_notes
grant_note "$TARGET"
R=$(run_hook "rm -rf $TARGET")
check "2. allowed with a note (exit 0)"           "0"    "$(rc_of "$R")"
# No permissionDecision on the allow path, by design: exit 0 + additionalContext
# only = "no decision; normal permission flow applies". "defer" is scoped to
# non-interactive (-p) mode and crashed the interactive harness in live testing
# 2026-08-07; "allow" would skip the permission prompt, which over-authorizes.
check "2. allow emits NO permissionDecision"      "none" "$(decision_of "$R")"
check "2. allow carries additionalContext"        "yes"  "$(printf '%s' "${R#*|}" | jq -e '.hookSpecificOutput.additionalContext | test("ALLOWED by pre-tool-use-enforcement")' >/dev/null 2>&1 && echo yes || echo no)"

# --- 3. note consumed after one use --------------------------------------
reset_notes
grant_note "$TARGET"
R1=$(run_hook "rm -rf $TARGET")   # first use: allowed, consumes the note
R2=$(run_hook "rm -rf $TARGET")   # second use: nothing left to honor
check "3. first use allowed"                      "0"    "$(rc_of "$R1")"
check "3. second use blocked (exit 2)"            "2"    "$(rc_of "$R2")"
check "3. second use blocked (deny emitted)"      "deny" "$(decision_of "$R2")"
check "3. note file gone from disk"               "0"    "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

# --- 4. expired note blocks ----------------------------------------------
reset_notes
grant_expired_note "$TARGET"
R=$(run_hook "rm -rf $TARGET")
check "4. expired note blocks (exit 2)"           "2"    "$(rc_of "$R")"
check "4. expired note blocks (deny emitted)"     "deny" "$(decision_of "$R")"
check "4. expired note was NOT consumed"          "1"    "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

# =========================================================================
printf '\nAUDIT LOG\n'
# =========================================================================
reset_notes
: >"$DELETION_APPROVAL_LOG"
grant_note "$TARGET"
run_hook "rm -rf $TARGET" >/dev/null
check "GRANT logged"                  "1" "$(grep -c '\[GRANT\]' "$DELETION_APPROVAL_LOG" | tr -d ' ')"
check "ALLOW logged"                  "1" "$(grep -c '\[ALLOW\]' "$DELETION_APPROVAL_LOG" | tr -d ' ')"
check "CONSUMED logged"               "1" "$(grep -c '\[CONSUMED\]' "$DELETION_APPROVAL_LOG" | tr -d ' ')"
# The quote and session name appear on BOTH the GRANT line and the ALLOW line
# (ALLOW logs the full note contents), so assert presence, not an exact count.
check "approval quote in log"         "yes" "$(grep -q 'test fixture' "$DELETION_APPROVAL_LOG" && echo yes || echo no)"
check "session name in log"           "yes" "$(grep -q 'Guard Approval Path' "$DELETION_APPROVAL_LOG" && echo yes || echo no)"
check "quote present on the ALLOW line" "yes" "$(grep '\[ALLOW\]' "$DELETION_APPROVAL_LOG" | grep -q 'test fixture' && echo yes || echo no)"

reset_notes
: >"$DELETION_APPROVAL_LOG"
grant_expired_note "$TARGET"
run_hook "rm -rf $TARGET" >/dev/null
check "EXPIRED-REJECT logged"         "1" "$(grep -c '\[EXPIRED-REJECT\]' "$DELETION_APPROVAL_LOG" | tr -d ' ')"

# =========================================================================
printf '\nSCOPE OF THE NOTE (a note must not over-authorize)\n'
# =========================================================================

# A note for path A must not authorize deleting path B.
reset_notes
grant_note "$TARGET"
R=$(run_hook "rm -rf $HOME/HQ-AI-Workspace-M4/Projects/Aura/working/_test_DIFFERENT")
check "note for A does not authorize B"           "2" "$(rc_of "$R")"

# Multi-path rm: one covered, one not -> the whole command still blocks.
reset_notes
grant_note "$TARGET"
R=$(run_hook "rm -rf $TARGET $HOME/HQ-AI-Workspace-M4/Projects/Aura/working/_test_UNCOVERED")
check "partial coverage still blocks"             "2" "$(rc_of "$R")"
check "unused note NOT consumed on a block"       "1" "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

# Multi-path rm with every path covered -> allowed, both notes consumed.
reset_notes
OTHER="$HOME/HQ-AI-Workspace-M4/Projects/Aura/working/_test_second_target"
grant_note "$TARGET"; grant_note "$OTHER"
R=$(run_hook "rm -rf $TARGET $OTHER")
check "full coverage of both paths allowed"       "0" "$(rc_of "$R")"
check "both notes consumed"                       "0" "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

# A parent-directory note must not authorize deleting the parent's contents
# by a different spelling, nor vice versa.
reset_notes
grant_note "$HOME/HQ-AI-Workspace-M4/Projects/Aura/working"
R=$(run_hook "rm -rf $TARGET")
check "parent note does not authorize a child"    "2" "$(rc_of "$R")"

# Globs are never approvable: a note names one exact target.
reset_notes
grant_note "$TARGET"
R=$(run_hook "rm -rf $HOME/HQ-AI-Workspace-M4/Projects/Aura/working/_test_approval_target*")
check "glob target blocks even with a note"       "2" "$(rc_of "$R")"

# Path traversal is never matchable.
reset_notes
grant_note "$TARGET"
R=$(run_hook "rm -rf $HOME/HQ-AI-Workspace-M4/Projects/Aura/working/../working/_test_approval_target")
check "traversal target blocks even with a note"  "2" "$(rc_of "$R")"

# Equivalent spellings of the SAME path do normalize together.
reset_notes
grant_note "$TARGET"
R=$(run_hook "rm -rf $HOME/HQ-AI-Workspace-M4/Projects/Aura/working/./_test_approval_target/")
check "trailing slash + /./ normalizes to a match" "0" "$(rc_of "$R")"

# A relative path resolved against cwd matches an absolute note.
reset_notes
grant_note "$TARGET"
R=$(run_hook "rm -rf working/_test_approval_target" "$HOME/HQ-AI-Workspace-M4/Projects/Aura")
check "relative path resolves against cwd"        "0" "$(rc_of "$R")"

# Literal paths containing spaces must match one note, and malformed or
# expandable command text must never consume a note.
SPACED="$HOME/HQ-AI-Workspace-M4/Projects/Aura/working/_test approval target"
reset_notes
grant_note "$SPACED"
R=$(run_hook "rm -rf -- \"$SPACED\"")
check "quoted path with spaces allowed"            "0" "$(rc_of "$R")"
check "quoted path note consumed"                 "0" "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

reset_notes
grant_note "$SPACED"
R=$(run_hook "rm -rf -- ${SPACED// /\\ }")
check "escaped path with spaces allowed"           "0" "$(rc_of "$R")"

reset_notes
grant_note "$SPACED"
R=$(run_hook "rm -rf -- \"$SPACED")
check "unterminated quote blocks"                 "2" "$(rc_of "$R")"
check "malformed command leaves note unconsumed" "1" "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

reset_notes
grant_note "$TARGET"
R=$(run_hook 'rm -rf -- /Users/allisongaddy/HQ-AI-Workspace-M4/Projects/Aura/working/$(printf _test_approval_target)')
check "shell expansion blocks"                    "2" "$(rc_of "$R")"

reset_notes
DOLLAR="$HOME/HQ-AI-Workspace-M4/Projects/Aura/working/_test_dollar\$2026"
grant_note "$DOLLAR"
R=$(run_hook "rm -rf -- '$DOLLAR'")
check "single-quoted dollar path allowed"          "0" "$(rc_of "$R")"

reset_notes
AMP="$HOME/HQ-AI-Workspace-M4/Projects/Aura/working/_test Funnels & Fire"
grant_note "$AMP"
R=$(run_hook "rm -rf -- '$AMP'")
check "quoted ampersand path allowed"             "0" "$(rc_of "$R")"
check "quoted ampersand note consumed"            "0" "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

reset_notes
grant_note "$TARGET"
R=$(run_hook "rm -rf -- $TARGET && /bin/echo unsafe")
check "unquoted command chain blocks"             "2" "$(rc_of "$R")"
check "command chain leaves note unconsumed"     "1" "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

reset_notes
grant_note "$TARGET"
R=$(run_hook "rm -rf -rf\$(printf unapproved) $TARGET")
check "expansion inside option blocks"             "2" "$(rc_of "$R")"
check "option expansion leaves note unconsumed"   "1" "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

reset_notes
grant_note "$TARGET"
R=$(run_hook "rm -rf -- -unapproved $TARGET" "$HOME/HQ-AI-Workspace-M4/Projects/Aura/working")
check "dash-named path after -- needs own note"   "2" "$(rc_of "$R")"

# =========================================================================
printf '\nFAIL-CLOSED AND UNCHANGED BEHAVIOR\n'
# =========================================================================

# Library unreadable -> approval path does not exist -> block stands.
reset_notes
grant_note "$TARGET"
R=$(DELETION_APPROVAL_LIB="$TMPROOT/nonexistent-lib.sh" run_hook "rm -rf $TARGET")
check "missing library fails CLOSED (blocks)"     "2" "$(rc_of "$R")"

# Notes directory absent entirely -> block stands.
rm -rf "$DELETION_APPROVAL_DIR"
R=$(run_hook "rm -rf $TARGET")
check "absent notes dir blocks"                   "2" "$(rc_of "$R")"
mkdir -p "$DELETION_APPROVAL_DIR"

# Pre-existing exemptions and rules must be untouched.
reset_notes
R=$(run_hook "rm -rf /private/tmp/claude-501/somesession/scratchpad/x")
check "scratch-path exemption still allows"       "0" "$(rc_of "$R")"

R=$(run_hook "git push --force origin main")
check "force-push still blocked"                  "2" "$(rc_of "$R")"

R=$(run_hook "rm -rf /tmp/build")
check "non-user-data rm still unaffected"         "0" "$(rc_of "$R")"

R=$(run_hook "ls -la $HOME")
check "harmless command unaffected"               "0" "$(rc_of "$R")"

# A note must not turn into a force-push exemption.
reset_notes
grant_note "$TARGET"
R=$(run_hook "git push --force origin main")
check "note does not unlock force-push"           "2" "$(rc_of "$R")"

# Kill-switch still wins over everything.
reset_notes
R=$(PRE_TOOL_USE_OFF=1 run_hook "rm -rf $TARGET")
check "kill-switch still bypasses the hook"       "0" "$(rc_of "$R")"

# =========================================================================
printf '\nFAIL CLOSED ON ERRORS, TIMEOUTS AND SCALE (2026-10-25)\n'
# =========================================================================
# Claude Code lets a tool call run when a hook times out or exits with any
# status other than 2. Each case below must come back as exit 2.

raw_hook() { # raw_hook <stdin-text> -> "<rc>|<stderr>"
  local out rc
  out=$(printf '%s' "$1" | bash "$HOOK" 2>&1 >/dev/null)
  rc=$?
  printf '%s|%s' "$rc" "$out"
}

R=$(raw_hook '{not json')
check "malformed hook input fails closed"          "2" "$(rc_of "$R")"
R=$(raw_hook '')
check "empty hook input fails closed"              "2" "$(rc_of "$R")"
R=$(raw_hook '[1,2,3]')
check "non-object hook input fails closed"         "2" "$(rc_of "$R")"
R=$(raw_hook '{"cwd":"/tmp","tool_input":{"command":"ls"}}')
check "hook input without tool_name fails closed"  "2" "$(rc_of "$R")"

# jq missing: only cat is reachable, so the hook can read stdin but not parse it.
NOJQ_BIN="$TMPROOT/nojq-bin"
mkdir -p "$NOJQ_BIN"
ln -sf /bin/cat "$NOJQ_BIN/cat"
R=$(printf '%s' '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | PATH="$NOJQ_BIN" /bin/bash "$HOOK" 2>&1 >/dev/null)
check "missing jq fails closed"                    "2" "$?"
check "missing jq says why"                        "1" "$(printf '%s' "$R" | grep -c 'jq is not available')"

# An unexpected crash (a library that exits 9 when sourced) must become exit 2.
printf 'exit 9\n' > "$TMPROOT/crash-lib.sh"
reset_notes
grant_note "$TARGET"
R=$(DELETION_APPROVAL_LIB="$TMPROOT/crash-lib.sh" run_hook "rm -rf $TARGET")
check "unexpected crash fails closed (exit 2, not 9)" "2" "$(rc_of "$R")"
R=$(DELETION_APPROVAL_LIB="$TMPROOT/crash-lib.sh" run_hook "ls -la $HOME")
check "unexpected crash blocks even a harmless command" "2" "$(rc_of "$R")"

# Deadline: a library whose note lookup is slow AND would approve. With a long
# deadline the hook approves (so the test is meaningful); with a 1 second
# deadline the watchdog refuses before the approval can land.
reset_notes
grant_note "$TARGET"
SLOW_NOTE=$(ls -1 "$DELETION_APPROVAL_DIR"/*.json | head -1)
cat > "$TMPROOT/slow-lib.sh" <<SLOW
source "$REAL_LIB"
find_approval_note() { sleep 3; printf '%s' "$SLOW_NOTE"; return 0; }
SLOW
R=$(GUARD_DEADLINE_SECONDS=60 DELETION_APPROVAL_LIB="$TMPROOT/slow-lib.sh" run_hook "rm -rf $TARGET")
check "slow lookup approves when inside the deadline" "0" "$(rc_of "$R")"
reset_notes
grant_note "$TARGET"
SLOW_NOTE=$(ls -1 "$DELETION_APPROVAL_DIR"/*.json | head -1)
cat > "$TMPROOT/slow-lib.sh" <<SLOW
source "$REAL_LIB"
find_approval_note() { sleep 3; printf '%s' "$SLOW_NOTE"; return 0; }
SLOW
R=$(GUARD_DEADLINE_SECONDS=1 DELETION_APPROVAL_LIB="$TMPROOT/slow-lib.sh" run_hook "rm -rf $TARGET")
check "slow lookup past the deadline fails closed"   "2" "$(rc_of "$R")"
check "deadline refusal leaves the note unconsumed"  "1" "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

# Scale: 100 targets with 100 notes (the failing shape of 2026-10-25) must
# decide well inside the 7 second deadline and consume every note.
reset_notes
SCALE_CMD="rm -rf --"
NOW_EPOCH=$(date +%s)
for i in $(seq 1 100); do
  SCALE_T="$HOME/HQ-AI-Workspace-M4/Projects/Aura/working/_scale_target_$i"
  printf '{"target":"%s","raw_target":"%s","approval_quote":"scale test","session_name":"scale test","created_epoch":%s,"expires_epoch":%s,"ttl_seconds":900,"single_use":true}\n' \
    "$SCALE_T" "$SCALE_T" "$NOW_EPOCH" "$((NOW_EPOCH + 900))" > "$DELETION_APPROVAL_DIR/$NOW_EPOCH-scale-$i.json"
  SCALE_CMD="$SCALE_CMD \"$SCALE_T\""
done
SCALE_START=$(date +%s)
R=$(run_hook "$SCALE_CMD")
SCALE_ELAPSED=$(( $(date +%s) - SCALE_START ))
check "100 targets with 100 notes allowed"           "0" "$(rc_of "$R")"
check "100 targets decided in under 7 seconds"       "yes" "$([[ $SCALE_ELAPSED -lt 7 ]] && echo yes || echo "no (${SCALE_ELAPSED}s)")"
check "all 100 notes consumed"                       "0" "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"
check "all 100 consumptions logged"                  "100" "$(grep -c '\[CONSUMED\].*scale-' "$DELETION_APPROVAL_LOG")"

# 100 targets with ONE target uncovered still blocks and consumes nothing.
reset_notes
for i in $(seq 1 99); do
  SCALE_T="$HOME/HQ-AI-Workspace-M4/Projects/Aura/working/_scale_target_$i"
  printf '{"target":"%s","raw_target":"%s","approval_quote":"scale test","session_name":"scale test","created_epoch":%s,"expires_epoch":%s,"ttl_seconds":900,"single_use":true}\n' \
    "$SCALE_T" "$SCALE_T" "$NOW_EPOCH" "$((NOW_EPOCH + 900))" > "$DELETION_APPROVAL_DIR/$NOW_EPOCH-scale-$i.json"
done
R=$(run_hook "$SCALE_CMD")
check "99 notes for 100 targets blocks"              "2" "$(rc_of "$R")"
check "partial coverage consumes nothing"            "99" "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

# =========================================================================
printf '\nQUOTED BRACKET, ASTERISK AND QUESTION-MARK NAMES (2026-10-25)\n'
# =========================================================================
# A folder named "Signature [All Versions]" or "*BEN - EDIT REQUESTS" is one
# exact path when its name is quoted or escaped, and a pattern the shell would
# expand when it is not. Quoted or escaped is approvable. Anything else is not.
W="$HOME/HQ-AI-Workspace-M4/Projects/Aura/working"
count_notes() { ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' '; }

BR="$W/_test Signature [All Versions]"
reset_notes; grant_note "$BR"
check "grant stores the bracket name literally"      "$BR" "$(jq -r '.target' "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | head -1)"
R=$(run_hook "rm -rf -- \"$BR\"")
check "double-quoted bracket name allowed"           "0" "$(rc_of "$R")"
check "bracket note consumed"                        "0" "$(count_notes)"
check "bracket consumption logged"                   "1" "$(grep -c '\[CONSUMED\].*' "$DELETION_APPROVAL_LOG" | tr -d ' ' | awk '{print ($1>0)?1:0}')"

reset_notes; grant_note "$BR"
R=$(run_hook "rm -rf -- '$BR'")
check "single-quoted bracket name allowed"           "0" "$(rc_of "$R")"

ST="$W/_test *BEN - EDIT REQUESTS PENDING/3_10_21-001"
reset_notes; grant_note "$ST"
R=$(run_hook "rm -rf -- \"$ST\"")
check "double-quoted asterisk name allowed"          "0" "$(rc_of "$R")"
check "asterisk note consumed"                       "0" "$(count_notes)"

QM="$W/_test what? now"
reset_notes; grant_note "$QM"
R=$(run_hook "rm -rf -- \"$QM\"")
check "quoted question-mark name allowed"            "0" "$(rc_of "$R")"

ESC="$W/_test_esc[x]"
reset_notes; grant_note "$ESC"
R=$(run_hook "rm -rf -- $W/_test_esc\\[x\\]")
check "backslash-escaped bracket name allowed"       "0" "$(rc_of "$R")"

# Unquoted wildcards stay refused, even with a note for the literal name.
GB="$W/_test_gl[ob]x"
reset_notes; grant_note "$GB"
R=$(run_hook "rm -rf -- $GB")
check "unquoted bracket pattern blocks"              "2" "$(rc_of "$R")"
check "unquoted bracket pattern leaves note"         "1" "$(count_notes)"

GS="$W/_test_star*"
reset_notes; grant_note "$GS"
R=$(run_hook "rm -rf -- $GS")
check "unquoted asterisk pattern blocks"             "2" "$(rc_of "$R")"
check "unquoted asterisk pattern leaves note"        "1" "$(count_notes)"

R=$(run_hook "rm -rf -- $W/_test_q?")
check "unquoted question-mark pattern blocks"        "2" "$(rc_of "$R")"

# A note for a literal name never authorizes a different name or a wider set.
reset_notes; grant_note "$GS"
R=$(run_hook "rm -rf -- \"$W/_test_starX\"")
check "asterisk note does not match another name"    "2" "$(rc_of "$R")"
R=$(run_hook "rm -rf -- \"$W/_test_\"")
check "asterisk note does not match its prefix"      "2" "$(rc_of "$R")"
check "mismatches leave the asterisk note"           "1" "$(count_notes)"

# One unquoted wildcard poisons the whole command, quoted siblings included.
reset_notes; grant_note "$BR"; grant_note "$ST"
R=$(run_hook "rm -rf -- \"$BR\" $W/_test_other*")
check "quoted name plus unquoted wildcard blocks"    "2" "$(rc_of "$R")"
check "mixed command consumes no note"               "2" "$(count_notes)"

# Quoted names with and without glob characters in one command, each with its own note.
reset_notes; grant_note "$BR"; grant_note "$ST"; grant_note "$TARGET"
R=$(run_hook "rm -rf -- \"$BR\" \"$ST\" \"$TARGET\"")
check "three quoted names, three notes, allowed"     "0" "$(rc_of "$R")"
check "all three notes consumed"                     "0" "$(count_notes)"
reset_notes; grant_note "$BR"; grant_note "$ST"
R=$(run_hook "rm -rf -- \"$BR\" \"$ST\" \"$TARGET\"")
check "one quoted name without a note blocks all"    "2" "$(rc_of "$R")"
check "partial coverage consumes nothing"            "2" "$(count_notes)"

# Quote handling must not be fooled. Each of these is refused.
reset_notes; grant_note "$BR"
R=$(run_hook "rm -rf -- \"$BR")
check "unterminated quote around bracket blocks"     "2" "$(rc_of "$R")"
R=$(run_hook "rm -rf -- \"$W/_test\"[x]")
check "quote then bare bracket blocks"               "2" "$(rc_of "$R")"
R=$(run_hook "rm -rf -- \"$BR\"*")
check "quoted name with trailing asterisk blocks"    "2" "$(rc_of "$R")"
R=$(run_hook "rm -rf -- \"$W/_test Signature \"[All Versions]")
check "split quote that exposes brackets blocks"     "2" "$(rc_of "$R")"
check "refused quote tricks leave the note"          "1" "$(count_notes)"

# Traversal stays refused for glob-character names as well.
reset_notes
bash "$GRANT" grant --target "$W/_test [x]/../y" --quote "q" >/dev/null 2>&1
check "grant still rejects traversal with brackets"  "1" "$([[ $? -ne 0 ]] && echo 1 || echo 0)"

# =========================================================================
printf '\nDELETES SENT OVER SSH TO EMBER'"'"'S M2 (2026-11-01, Job Tracker row 130)\n'
# =========================================================================
grant_remote() { # grant_remote <host> <path>
  bash "$GRANT" grant --host "$1" --target "$2" \
    --quote "yes, delete it -- remote test fixture" \
    --session "Factory.ai Mission Team - ssh guard" >/dev/null 2>&1
}

# The three required cases.
reset_notes
R=$(run_hook "ssh ember 'rm -rf /tmp/scratch-x'")
check "ssh ember rm -rf blocked without a note (exit 2)"  "2"    "$(rc_of "$R")"
check "ssh ember rm -rf blocked without a note (deny)"    "deny" "$(decision_of "$R")"

reset_notes
grant_remote ember /tmp/scratch-x
check "remote grant stores user@host:path"                "ember@ember:/tmp/scratch-x" "$(jq -r '.target' "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | head -1)"
R1=$(run_hook "ssh ember 'rm -rf /tmp/scratch-x'")
R2=$(run_hook "ssh ember 'rm -rf /tmp/scratch-x'")
check "ssh ember rm -rf allowed once with a note"         "0"    "$(rc_of "$R1")"
check "remote allow emits NO permissionDecision"          "none" "$(decision_of "$R1")"
check "remote note consumed"                              "0"    "$(count_notes)"
check "second remote delete blocked again"                "2"    "$(rc_of "$R2")"
check "remote ALLOW logged"                               "yes"  "$(grep '\[ALLOW\]' "$DELETION_APPROVAL_LOG" | grep -q 'ember:/tmp/scratch-x' && echo yes || echo no)"

reset_notes
R=$(run_hook "ssh ember 'ls ~'")
check "ssh ember 'ls ~' allowed"                          "0"    "$(rc_of "$R")"
check "read-only ssh prints nothing"                      ""     "${R#*|}"

# Read-only ssh in other shapes still passes.
R=$(run_hook "ssh ember")
check "interactive ssh allowed"                           "0" "$(rc_of "$R")"
R=$(run_hook "ssh -o ConnectTimeout=5 ember 'cat ~/.zshrc; ls -la /tmp'")
check "read-only compound ssh allowed"                    "0" "$(rc_of "$R")"
R=$(run_hook "ssh ember 'mv ~/Desktop/a.txt ~/Documents/a.txt'")
check "plain move that is not to the Trash allowed"       "0" "$(rc_of "$R")"

# Host AND path must both match.
reset_notes
grant_remote ember /tmp/scratch-x
R=$(run_hook "ssh ember 'rm -rf /tmp/scratch-y'")
check "note for one remote path does not cover another"   "2" "$(rc_of "$R")"
R=$(run_hook "ssh other-mac 'rm -rf /tmp/scratch-x'")
check "note for one host does not cover another host"     "2" "$(rc_of "$R")"
R=$(run_hook "rm -rf /tmp/scratch-x")
check "remote note does not touch local rule behavior"    "0" "$(rc_of "$R")"
check "mismatches leave the remote note"                  "1" "$(count_notes)"

reset_notes
grant_note "$TARGET"
R=$(run_hook "ssh ember 'rm -rf $TARGET'")
check "local note does not approve a remote delete"       "2" "$(rc_of "$R")"
check "local note left unconsumed"                        "1" "$(count_notes)"

# Spellings that mean the same host and path match one note.
reset_notes
grant_remote ember /tmp/scratch-x
R=$(run_hook "ssh -p 22 EMBER rm -rf -- /tmp/./scratch-x/")
check "host case, options and /./ spelling match"          "0" "$(rc_of "$R")"
reset_notes
grant_remote ember@ember /tmp/scratch-x
R=$(run_hook "ssh -p 22 ember@EMBER rm -rf -- /tmp/scratch-x")
check "user@host note matches the same user@host"          "0" "$(rc_of "$R")"

# The login name is part of the key (Codex review, 2026-11-02). A note for
# ember never covers root@ember, and ~ belongs to the user who logs in.
reset_notes
grant_remote ember "~/Desktop/old"
R=$(run_hook "ssh root@ember rm -rf ~/Desktop/old")
check "note for ember does not cover root@ember"          "2" "$(rc_of "$R")"
R=$(run_hook "ssh -l root ember rm -rf ~/Desktop/old")
check "note for ember does not cover -l root"             "2" "$(rc_of "$R")"
R=$(run_hook "ssh -o User=root ember rm -rf ~/Desktop/old")
check "note for ember does not cover -o User=root"        "2" "$(rc_of "$R")"
check "other-user deletes leave the note"                 "1" "$(count_notes)"
reset_notes
grant_remote root@ember /tmp/scratch-x
R=$(run_hook "ssh -l root ember rm -rf /tmp/scratch-x")
check "-l root matches a root@ember note"                 "0" "$(rc_of "$R")"

# Whole homes, disks and top-level folders are never approvable, however spelled.
for T in /Users/allisongaddy /Users /Volumes/Backup /home/ember /tmp /Applications /private/tmp; do
  bash "$GRANT" grant --host ember --target "$T" --quote "q" >/dev/null 2>&1
  check "remote grant rejects $T" "1" "$([[ $? -ne 0 ]] && echo 1 || echo 0)"
done

# The login comes from ssh's own config, not just the command (Codex review
# of PR 669). rootbox logs in as root, so its key is root@rootbox.
reset_notes
grant_remote ember@rootbox "~/Desktop/old"
R=$(run_hook "ssh rootbox rm -rf ~/Desktop/old")
check "config User root is not covered by an ember note"  "2" "$(rc_of "$R")"
reset_notes
grant_remote rootbox "~/Desktop/old"
check "grant records the configured login"                "root@rootbox:~/Desktop/old" "$(jq -r '.target' "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | head -1)"
R=$(run_hook "ssh rootbox rm -rf ~/Desktop/old")
check "configured login matches its own note"             "0" "$(rc_of "$R")"
reset_notes
bash "$GRANT" grant --host ember --target /private/var/root --quote "q" >/dev/null 2>&1
check "remote grant rejects /private/var/root"            "1" "$([[ $? -ne 0 ]] && echo 1 || echo 0)"
R=$(DELETION_APPROVAL_SSH_BIN="$TMPROOT/no-such-ssh" run_hook "ssh ember 'rm -rf /tmp/scratch-x'")
check "unreadable ssh login blocks"                       "2" "$(rc_of "$R")"

# One target spelled twice uses its one note once, and is allowed.
reset_notes
grant_note "$TARGET"
R=$(run_hook "rm -rf $TARGET $TARGET/")
check "same target spelled twice allowed"                 "0" "$(rc_of "$R")"
check "its one note consumed"                             "0" "$(count_notes)"

# A run killed between claim and consume puts the note back.
reset_notes
grant_note "$TARGET"
cat > "$TMPROOT/stall-lib.sh" <<STALL
source "$REAL_LIB"
commit_claimed_notes() { sleep 5; }
STALL
R=$(GUARD_DEADLINE_SECONDS=1 DELETION_APPROVAL_LIB="$TMPROOT/stall-lib.sh" run_hook "rm -rf $TARGET")
check "deadline between claim and consume blocks"         "2" "$(rc_of "$R")"
check "the claimed note is put back"                      "1" "$(count_notes)"
check "no claimed file left behind"                       "0" "$(ls -1 "$DELETION_APPROVAL_DIR" 2>/dev/null | grep -c claimed)"

# Third Codex round on PR 669.
reset_notes
grant_remote Admin@box /tmp/old-x
R=$(run_hook "ssh admin@box rm -rf /tmp/old-x")
check "login case is kept (Admin is not admin)"           "2" "$(rc_of "$R")"
R=$(run_hook "ssh Admin@box rm -rf /tmp/old-x")
check "exact login case matches"                          "0" "$(rc_of "$R")"
for T in /System/Volumes/Data /System/Volumes/Data/Users/allisongaddy /System/Volumes/Data/private/var/root /System/Volumes/Data/Users; do
  bash "$GRANT" grant --host ember --target "$T" --quote "q" >/dev/null 2>&1
  check "remote grant rejects $T" "1" "$([[ $? -ne 0 ]] && echo 1 || echo 0)"
done
reset_notes
grant_remote ember@ember /tmp/scratch-x
R=$(run_hook "ssh -l root ember@ember rm -rf /tmp/scratch-x")
check "-l root wins over user@ and is not covered"        "2" "$(rc_of "$R")"
check "the ember note is left"                            "1" "$(count_notes)"

# Two notes for one target and two racing deletes, both proceed.
reset_notes
grant_remote ember /tmp/twice-x
sleep 1
grant_remote ember /tmp/twice-x
for i in 1 2; do
  ( run_hook "ssh ember 'rm -rf /tmp/twice-x'" > "$TMPROOT/tw$i" ) &
done
wait
check "two notes, two racing deletes, both allowed"       "2" "$(for f in "$TMPROOT"/tw*; do rc_of "$(cat "$f")"; echo; done | grep -c '^0$')"
check "both notes spent"                                  "0" "$(count_notes)"

# A log write that hangs during the allow step must not outlast the deadline,
# and the note must come back (Codex review of 1a05c9e).
reset_notes
grant_note "$TARGET"
cat > "$TMPROOT/hang-lib.sh" <<HANG
source "$REAL_LIB"
da_log() { case "\$1" in ALLOW) sleep 5 ;; esac; }
HANG
R=$(GUARD_DEADLINE_SECONDS=1 DELETION_APPROVAL_LIB="$TMPROOT/hang-lib.sh" run_hook "rm -rf $TARGET")
check "hung audit log hits the deadline and blocks"       "2" "$(rc_of "$R")"
check "hung audit log leaves the note in place"           "1" "$(count_notes)"

# Fourth Codex round on PR 669.
# A -F config with Match exec never runs from inside the guard.
cat > "$TMPROOT/evil.cfg" <<EVIL
Match exec "touch $TMPROOT/match-exec-ran"
  User ember
EVIL
cat > "$TMPROOT/bin/ssh-real-ish" <<'REALISH'
#!/usr/bin/env bash
# Records that ssh -G was called at all.
touch "${MARK_DIR}/ssh-g-called"
exec "$(dirname "$0")/ssh" "$@"
REALISH
chmod +x "$TMPROOT/bin/ssh-real-ish"
reset_notes
grant_remote ember /tmp/x
rm -f "$TMPROOT/ssh-g-called"
R=$(MARK_DIR="$TMPROOT" DELETION_APPROVAL_SSH_BIN="$TMPROOT/bin/ssh-real-ish" run_hook "ssh -F $TMPROOT/evil.cfg ember rm -rf /tmp/x")
check "-F delete blocks"                                  "2" "$(rc_of "$R")"
check "-F delete never calls ssh -G"                      "no" "$([[ -e "$TMPROOT/ssh-g-called" ]] && echo yes || echo no)"
R=$(MARK_DIR="$TMPROOT" DELETION_APPROVAL_SSH_BIN="$TMPROOT/bin/ssh-real-ish" run_hook "ssh -o Include=$TMPROOT/evil.cfg ember rm -rf /tmp/x")
check "-o Include delete blocks before ssh -G"            "no" "$([[ -e "$TMPROOT/ssh-g-called" ]] && echo yes || echo no)"

# Revoke finds a note by the host and path it was granted with, even after
# the configured login changes.
reset_notes
grant_remote box /tmp/item
bash "$GRANT" revoke --host box --target /tmp/item >/dev/null 2>&1
check "revoke by granted host and path"                   "0" "$(count_notes)"
reset_notes
grant_remote box /tmp/item
DELETION_APPROVAL_SSH_BIN="$TMPROOT/no-such-ssh" bash "$GRANT" revoke --host box --target /tmp/item >/dev/null 2>&1
check "revoke works when the login can't be read now"     "0" "$(count_notes)"

# Fifth Codex round. Protected roots are refused in any letter case.
for T in /users/allisongaddy /USERS/allisongaddy /system/volumes/data /System/Volumes/data/Users/ember /VOLUMES/Backup; do
  bash "$GRANT" grant --host ember --target "$T" --quote "q" >/dev/null 2>&1
  check "remote grant rejects $T" "1" "$([[ $? -ne 0 ]] && echo 1 || echo 0)"
done
reset_notes
R=$(run_hook "ssh ember rm -rf /users/allisongaddy")
check "lower-case home delete blocks"                     "2" "$(rc_of "$R")"

# Two identical deletes at the same moment spend one note once.
reset_notes
grant_remote ember /tmp/race-x
grant_note "$TARGET"
RACE="$TMPROOT/race"
mkdir -p "$RACE"
for i in 1 2 3 4 5 6; do
  ( run_hook "ssh ember 'rm -rf /tmp/race-x'" > "$RACE/r$i" ) &
done
wait
ALLOWED=$(for f in "$RACE"/r*; do rc_of "$(cat "$f")"; echo; done | grep -c '^0$')
check "six racing remote deletes, one allowed"            "1" "$ALLOWED"
for i in 1 2 3 4 5 6; do
  ( run_hook "rm -rf $TARGET" > "$RACE/l$i" ) &
done
wait
ALLOWED=$(for f in "$RACE"/l*; do rc_of "$(cat "$f")"; echo; done | grep -c '^0$')
check "six racing local deletes, one allowed"             "1" "$ALLOWED"
check "no claimed notes left behind"                      "0" "$(ls -1 "$DELETION_APPROVAL_DIR" 2>/dev/null | grep -c claimed)"

# Trash moves and other deletes are caught.
reset_notes
R=$(run_hook "ssh ember 'mv ~/Desktop/old ~/.Trash/'")
check "remote move to the Trash blocked without a note"   "2" "$(rc_of "$R")"
grant_remote ember "~/Desktop/old"
R=$(run_hook "ssh ember 'mv ~/Desktop/old ~/.Trash/'")
check "remote move to the Trash allowed with a note"      "0" "$(rc_of "$R")"
check "Trash move note consumed"                          "0" "$(count_notes)"
for C in "ssh ember 'trash ~/Desktop/old'" "ssh ember 'rm ~/notes.txt'" "ssh ember 'rmdir /tmp/empty'" \
         "ssh ember 'find /tmp/scratch -delete'" "ssh ember 'cd /tmp && rm -rf scratch-x'" \
         "ssh ember 'rm -rf /tmp/scratch-*'" "ssh ember 'rm -rf scratch-x'" "ssh ember 'rm -rf ~'" \
         "ssh ember 'rm -rf \$HOME/x'" "echo hi && ssh ember 'rm -rf /tmp/scratch-x'" \
         "ssh ember /bin/rm -rf /tmp/scratch-x" "timeout 5 ssh ember 'rm -rf /tmp/scratch-x'" \
         "ssh ember \"osascript -e 'tell app \\\"Finder\\\" to delete POSIX file \\\"/tmp/x\\\"'\""; do
  R=$(run_hook "$C")
  check "blocked: $C" "2" "$(rc_of "$R")"
done

# Disguised words, options that carry commands, stdin and other machines
# (independent review, 2026-11-01). Each must block with no note.
for C in "ssh ember '\\rm -rf /tmp/x'" "ssh ember \\\\rm -rf /tmp/x" "ssh ember \"r''m -rf /tmp/x\"" \
         "ssh ember 'r\\m -rf /tmp/x'" "ssh ember '=rm -rf /tmp/x'" \
         "\"ssh\" ember rm -rf /tmp/x" "\\ssh ember rm -rf /tmp/x" "s''sh ember rm -rf /tmp/x" \
         "ssh -o RemoteCommand='rm -rf /tmp/x' ember" "ssh -oRemoteCommand='rm -rf /tmp/x' ember" \
         "ssh ember -o RemoteCommand='rm -rf /tmp/x'" "ssh -o ProxyCommand='rm -rf /tmp/x' ember" \
         "echo 'rm -rf /tmp/x' | ssh ember" "cat script.sh | ssh ember bash" "ssh ember bash < script.sh" \
         "rsync -a --delete /tmp/a/ ember:/tmp/x" "mosh ember -- rm -rf /tmp/x" \
         "ssh ember 'python3 -c \"import shutil; shutil.rmtree(\\\"/tmp/x\\\")\"'" \
         "ssh ember 'git -C /tmp/x clean -fdx'" "ssh ember 'sudo rm -rf /tmp/x'" "ssh ember 'xargs rm < /tmp/list'"; do
  R=$(run_hook "$C")
  check "blocked: $C" "2" "$(rc_of "$R")"
done

# Second review round: unknown first words, patterns, local expansion,
# more ways to feed ssh, and control sockets.
for C in "ssh ember FOO=1 rm -rf /tmp/x" "ssh ember noglob rm -rf /tmp/x" "ssh ember busybox rm -rf /tmp/x" \
         "ssh ember su root -c 'rm -rf /tmp/x'" "ssh ember ssh other rm -rf /tmp/x" "ssh ember flock /tmp/l rm -rf /tmp/x" \
         "ssh ember '/bin/r[m] -rf /tmp/x'" "ssh ember '/bin/r? -rf /tmp/x'" "ssh ember '{rm,-rf,/tmp/x}'" \
         "ssh ember \$'\\x72m' -rf /tmp/x" "ssh ember \$(echo r)m -rf /tmp/x" "R=rm; ssh ember \$R -rf /tmp/x" \
         "echo 'rm -rf /tmp/x' | env ssh ember" "echo 'rm -rf /tmp/x' | command ssh ember" \
         "echo 'rm -rf /tmp/x' | (ssh ember)" "echo 'rm -rf /tmp/x' |& ssh ember" "< /tmp/script.sh ssh ember" \
         "ssh ember true; echo 'rm -rf /tmp/x' | ssh ember" "cat s | ssh ember busybox sh" \
         "rsync -a --remove-source-files ember:/tmp/x /tmp/y" "sftp -b /tmp/batch ember"; do
  R=$(run_hook "$C")
  check "blocked: $C" "2" "$(rc_of "$R")"
done
reset_notes
grant_remote ember /tmp/x
R=$(run_hook "ssh -S /tmp/other.sock ember rm -rf /tmp/x")
check "note not honored with -S"                          "2" "$(rc_of "$R")"
R=$(run_hook "ssh -o ControlPath=/tmp/other.sock ember rm -rf /tmp/x")
check "note not honored with -o ControlPath"              "2" "$(rc_of "$R")"
check "control socket deletes leave the note"             "1" "$(count_notes)"
for C in "ssh ember 'ls ~/.Trash' | head" "ssh ember 'grep -r rmtree ~/code' | wc -l" "ssh ember 'ls' > /tmp/out.txt"; do
  R=$(run_hook "$C")
  check "allowed: $C" "0" "$(rc_of "$R")"
done

# Third review round.
for C in "ssh ember 'node -e \"require(\\\"fs\\\").rmSync(\\\"/tmp/x\\\",{recursive:true})\"'" \
         "ssh ember \"ruby -e 'require \\\"fileutils\\\"; FileUtils.rm_rf(\\\"/tmp/x\\\")'\"" \
         "ssh ember \"python3 -c 'from pathlib import Path; Path(\\\"/tmp/x\\\").rmdir()'\"" \
         "ssh ember 'ls \`rm -rf /tmp/x\`'" "ssh ember 'ls ~ | xargs rm -rf'"; do
  R=$(run_hook "$C")
  check "blocked: $C" "2" "$(rc_of "$R")"
done
for C in "ssh ember 'ls ~/.Trash | wc -l'" "ssh ember 'ls -la ~/.Trash | head'" "ssh ember 'du -sh ~/.Trash 2>/dev/null'" \
         "ssh ember 'git -C ~/repo pull' < /dev/null"; do
  R=$(run_hook "$C")
  check "allowed: $C" "0" "$(rc_of "$R")"
done

# A note for ember never follows the command to a different machine or a
# quoted ~ that the remote shell would read literally.
reset_notes
grant_remote ember /tmp/x
R=$(run_hook "ssh -o Hostname=10.9.9.9 ember rm -rf /tmp/x")
check "note not honored with -o Hostname"                 "2" "$(rc_of "$R")"
R=$(run_hook "ssh -F /tmp/other.cfg ember rm -rf /tmp/x")
check "note not honored with -F"                          "2" "$(rc_of "$R")"
R=$(run_hook "ssh -J jump ember rm -rf /tmp/x")
check "note not honored with -J"                          "2" "$(rc_of "$R")"
check "redirected deletes leave the note"                 "1" "$(count_notes)"
reset_notes
grant_remote ember "~/x"
R=$(run_hook "ssh ember \"rm -rf '~/x'\"")
check "quoted ~ is refused even with a note"              "2" "$(rc_of "$R")"
check "quoted ~ leaves the note"                          "1" "$(count_notes)"

# Read-only commands that only mention a delete word still pass.
for C in "ssh ember 'ls ~/.Trash'" "ssh ember 'du -sh ~/.Trash'" "ssh ember 'cat /tmp/rm'" \
         "ssh ember 'grep -c rmdir /var/log/x'" "ssh ember 'which rm'" "ssh ember 'man unlink'" \
         "ssh ember 'tail -n 5 /tmp/log' | grep rm" "ls /etc/ssh && rm -rf /tmp/build" \
         "cat notes.txt | ssh ember 'cat > /tmp/notes.txt'" "ssh -p 2222 ember uptime"; do
  R=$(run_hook "$C")
  check "allowed: $C" "0" "$(rc_of "$R")"
done

# A note can never approve a wildcard, a relative path or a compound command.
reset_notes
grant_remote ember /tmp/scratch-x
R=$(run_hook "ssh ember 'rm -rf /tmp/scratch-x; rm -rf /tmp/other'")
check "chained remote delete blocks even with a note"     "2" "$(rc_of "$R")"
R=$(run_hook "ssh ember 'rm -rf /tmp/scratch-x /tmp/other'")
check "partial remote coverage blocks"                    "2" "$(rc_of "$R")"
check "refused remote deletes leave the note"             "1" "$(count_notes)"

# The grant script refuses remote targets no hook could match.
reset_notes
bash "$GRANT" grant --host ember --target "relative/path" --quote "q" >/dev/null 2>&1
check "remote grant rejects a relative path"              "1" "$([[ $? -ne 0 ]] && echo 1 || echo 0)"
bash "$GRANT" grant --host ember --target "/tmp/../etc" --quote "q" >/dev/null 2>&1
check "remote grant rejects traversal"                    "1" "$([[ $? -ne 0 ]] && echo 1 || echo 0)"
bash "$GRANT" grant --host ember --target "~" --quote "q" >/dev/null 2>&1
check "remote grant rejects a whole home folder"          "1" "$([[ $? -ne 0 ]] && echo 1 || echo 0)"
grant_remote ember /tmp/scratch-x
bash "$GRANT" revoke --host ember --target /tmp/scratch-x >/dev/null 2>&1
check "remote revoke removes the note"                    "0" "$(count_notes)"

# Missing library fails closed for remote deletes too.
reset_notes
grant_remote ember /tmp/scratch-x
R=$(DELETION_APPROVAL_LIB="$TMPROOT/nonexistent-lib.sh" run_hook "ssh ember 'rm -rf /tmp/scratch-x'")
check "missing library blocks a remote delete"            "2" "$(rc_of "$R")"
R=$(DELETION_APPROVAL_LIB="$TMPROOT/nonexistent-lib.sh" run_hook "ssh ember 'ls ~'")
check "missing library still allows read-only ssh"        "0" "$(rc_of "$R")"

# =========================================================================
printf '\nGRANT SCRIPT GUARDS\n'
# =========================================================================
reset_notes
bash "$GRANT" grant --target "$TARGET" >/dev/null 2>&1
check "grant requires --quote (nonzero exit)"     "1" "$([[ $? -ne 0 ]] && echo 1 || echo 0)"

bash "$GRANT" grant --target "$HOME/x/../y" --quote "q" >/dev/null 2>&1
check "grant rejects traversal target"            "1" "$([[ $? -ne 0 ]] && echo 1 || echo 0)"

# Since 2026-10-25 a glob character in a grant target is one literal name. The
# hook still refuses any rm where such a character is not quoted or escaped.
reset_notes
bash "$GRANT" grant --target "$HOME/x*" --quote "q" >/dev/null 2>&1
check "grant accepts a literal asterisk name"     "0" "$?"
check "grant stores the asterisk name literally"  "$HOME/x*" "$(jq -r '.target' "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | head -1)"
reset_notes

reset_notes
bash "$GRANT" grant --target "$TARGET" --quote "q" --ttl 99999 >/dev/null 2>&1
CLAMPED=$(jq -r '.ttl_seconds' "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | head -1)
check "grant clamps ttl to the 3600s ceiling"     "3600" "$CLAMPED"

reset_notes
bash "$GRANT" grant --target "$TARGET" --quote "q" --ttl 900 >/dev/null 2>&1
bash "$GRANT" revoke --target "$TARGET" >/dev/null 2>&1
check "revoke removes the note"                   "0" "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

reset_notes
grant_expired_note "$TARGET"
bash "$GRANT" purge >/dev/null 2>&1
check "purge removes expired notes"               "0" "$(ls -1 "$DELETION_APPROVAL_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"

# =========================================================================
printf '\n%s─────────────────────────────%s\n' "$DIM" "$RESET"
if [[ "$FAIL" -eq 0 ]]; then
  printf '%sALL %s CHECKS PASSED%s\n\n' "$GREEN" "$PASS" "$RESET"
  exit 0
else
  printf '%s%s PASSED, %s FAILED%s\n\n' "$RED" "$PASS" "$FAIL" "$RESET"
  exit 1
fi
