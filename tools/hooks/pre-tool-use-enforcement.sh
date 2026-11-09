#!/bin/bash -p
# Explicit M4 execution is a separate command, never a PreToolUse side effect.
# Fixed privileged startup ignores ENV/BASH_ENV and inherited shell functions.
if [[ $# -gt 0 ]]; then
  case "$1" in
    --execute-m4-batch2) _m4_mode=execute ;;
    --preview-m4-batch2) _m4_mode=preview ;;
    *) printf '%s\n' 'M4 guard: unknown explicit mode' >&2; exit 2 ;;
  esac
  if [[ $# -ne 2 || -n "${BASH_ENV+x}" || -n "${ENV+x}" ]]; then
    printf '%s\n' 'M4 guard: invalid arguments or shell startup override' >&2
    exit 2
  fi
  exec /opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/bin/python3.14 -I /Users/allisongaddy/HQ-AI-Workspace-M4/Workbench/scripts/lib/m4-batch2-executor.py "$_m4_mode" "$2"
  exit 2
fi
# pre-tool-use-enforcement.sh
# PreToolUse hook: block and warn on destructive commands on M4.
#
# Enforcement rules:
#   BLOCK: rm -rf on user-data paths (exit 2 + stderr → deny)
#          UNLESS an unexpired single-use approval note covers every target
#   BLOCK: git force-push to any branch (exit 2 + stderr → deny)
#   WARN:  git commit directly to main (additionalContext advisory)
#   WARN:  Write tool targeting ~/.claude/settings.json (requires explicit go)
#
# APPROVAL-NOTE PATH (added 2026-08-07, ruled by Allison):
#   An explicitly approved deletion goes THROUGH this guard, never around it.
#   The session writes a note with ~/HQ-AI-Workspace-M4/Workbench/scripts/deletion-approval-note.sh grant
#   (exact target, Allison's approval quote, session name, timestamp, short
#   expiry). On a matching destructive delete this hook honors an unexpired
#   note covering EVERY target in the command, logs the allowance with the
#   note contents, and consumes the note. No note, or an expired note, and the
#   block stands exactly as before. Bypassing this hook (shutil.rmtree or any
#   equivalent) is retired as a practice as of that ruling.
#   Audit log: ~/.claude/logs/deletion-approvals.log
#
# KILL-SWITCH:
#   Sentinel file: touch ~/.claude/pre-tool-use-enforcement-off
#                  rm    ~/.claude/pre-tool-use-enforcement-off
#   Env var:       PRE_TOOL_USE_OFF=1
#
# Reads JSON from stdin (fields: tool_name, tool_input, cwd, permission_mode).
# Block: exit 2 to stderr. Advisory: exit 0 + JSON additionalContext.
# References: code.claude.com/docs/en/claude-code/hooks (verified 2026-06-02)

set -uo pipefail

INPUT=$(cat)

# Kill-switch: bail silently if disabled
if [[ -f "$HOME/.claude/pre-tool-use-enforcement-off" || "${PRE_TOOL_USE_OFF:-}" == "1" ]]; then
  exit 0
fi

# -------------------------------------------------------------------------
# FAIL CLOSED (added 2026-10-25, Handoffs row "Finish AI HQ folder before
# checking 181 empty parent folders", step 4).
#
# Claude Code treats a hook that times out or exits with any status other than
# 2 as a NON-BLOCKING error and lets the tool call run. On 2026-10-25 a long rm
# overran the 10 second hook timeout and about 313 deletions ran with their
# approval notes unconsumed. This guard therefore refuses by itself, with exit
# 2, in every case it cannot finish deciding:
#   - jq is missing, or stdin is not a JSON object with a tool_name
#   - the guard runs past its own deadline (7 seconds, under the 10 second
#     harness timeout, so the refusal always lands first)
#   - any unexpected crash or exit status other than a deliberate 0 or 2
# The kill-switch above stays the only way to switch the guard off.
# -------------------------------------------------------------------------
GUARD_CLEAN_EXIT=0
GUARD_DEADLINE_SECONDS="${GUARD_DEADLINE_SECONDS:-7}"
GUARD_WATCHDOG_PID=""

guard_on_exit() {
  local rc=$?
  # A claimed but unconsumed approval note goes back where it was.
  declare -F release_claimed_notes >/dev/null 2>&1 && release_claimed_notes
  # Ignore a late TERM, then stop the watchdog subshell itself. Never kill its
  # sleep first: the subshell would move on and send the TERM we are avoiding.
  # The orphaned sleep holds no pipes and ends on its own.
  trap '' TERM
  if [[ -n "$GUARD_WATCHDOG_PID" ]]; then
    kill "$GUARD_WATCHDOG_PID" 2>/dev/null
  fi
  if [[ "$rc" -eq 2 ]] || { [[ "$rc" -eq 0 ]] && [[ "$GUARD_CLEAN_EXIT" -eq 1 ]]; }; then
    return 0
  fi
  printf '%s\n' "BLOCKED by pre-tool-use-enforcement: the guard ended unexpectedly (exit $rc) and fails closed. Nothing ran. Fix the guard or use the kill-switch ~/.claude/pre-tool-use-enforcement-off." >&2
  exit 2
}

guard_refuse() {
  printf '%s\n' "BLOCKED by pre-tool-use-enforcement: $1 The guard fails closed, so nothing ran." >&2
  exit 2
}

trap guard_on_exit EXIT
trap 'guard_refuse "the guard passed its ${GUARD_DEADLINE_SECONDS}s deadline."' TERM
# The watchdog must not hold the hook's stdout open, or the harness waits on it.
( sleep "$GUARD_DEADLINE_SECONDS"; kill -TERM "$$" 2>/dev/null ) >/dev/null 2>&1 </dev/null &
GUARD_WATCHDOG_PID=$!
disown "$GUARD_WATCHDOG_PID" 2>/dev/null

command -v jq >/dev/null 2>&1 || guard_refuse "jq is not available, so the hook input cannot be read."
printf '%s' "$INPUT" | jq -e 'type == "object" and ((.tool_name // "") | type == "string" and length > 0)' >/dev/null 2>&1 \
  || guard_refuse "the hook input is not a JSON object with a tool_name."

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""')
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""')
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // ""')

# -------------------------------------------------------------------------
# Approval-note library. FAIL CLOSED: if the library is unreadable, the
# approval path simply does not exist this run and every block stands as it
# did before the path was added. A missing library must never open the gate.
# -------------------------------------------------------------------------
DA_LIB="${DELETION_APPROVAL_LIB:-$HOME/HQ-AI-Workspace-M4/Workbench/scripts/lib/deletion-approval-common.sh}"
DA_AVAILABLE=0
if [[ -f "$DA_LIB" ]]; then
  # shellcheck source=lib/deletion-approval-common.sh
  if source "$DA_LIB" 2>/dev/null; then
    DA_AVAILABLE=1
  fi
fi

# -------------------------------------------------------------------------
# Helper: emit a block decision (deny) and exit
# -------------------------------------------------------------------------
block() {
  local reason="$1"
  printf '%s\n' "$reason" >&2
  # Also emit structured deny so Claude sees the reason in the UI
  jq -n --arg r "$reason" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 2
}

# -------------------------------------------------------------------------
# Helper: emit an advisory warning (allow but surface context)
# -------------------------------------------------------------------------
warn() {
  local msg="$1"
  jq -n --arg m "$msg" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$m}}'
  GUARD_CLEAN_EXIT=1
  exit 0
}

# -------------------------------------------------------------------------
# Helper: is the rm target(s) confined to an ephemeral scratch/clone path?
#
# Returns 0 (true) ONLY when EVERY non-flag path token in the captured rm
# command is a scratch path. If even one token is a non-scratch user-data
# path, returns 1 (false) so the full block stands. Narrow allowlist --
# it only ever turns a block into an allow, never the reverse.
#
# Scratch = session scratchpad base /private/tmp/claude-501/ , OR a repo
# clone/scratch glob: working/_clone_* , working/*.clone , */scratchpad/* .
# -------------------------------------------------------------------------
is_scratch_target() {
  local rmcmd="$1"
  local saw_path=0 tok
  for tok in $(printf '%s' "$rmcmd" | sed -E 's/^[[:space:];|&]*//; s/^rm[[:space:]]+//'); do
    [[ "$tok" == -* ]] && continue
    # path-traversal tokens are never exempt
    case "$tok" in *..*) return 1 ;; esac
    saw_path=1
    if printf '%s' "$tok" | grep -qE '(^|/)/private/tmp/claude-501/' \
      || printf '%s' "$tok" | grep -qE '(^|/)working/_clone_[^/]*' \
      || printf '%s' "$tok" | grep -qE '(^|/)working/[^/]*\.clone(/|$)' \
      || printf '%s' "$tok" | grep -qE '/scratchpad/'; then
      continue
    fi
    return 1
  done
  [[ "$saw_path" -eq 1 ]] && return 0
  return 1
}

# -------------------------------------------------------------------------
# Helper: emit an allowance and exit (approval-note path only)
#
# Emits NO permissionDecision at all -- exit 0 with additionalContext only.
# Per the hooks reference (code.claude.com/docs/en/hooks, verified
# 2026-08-07), exit 0 with no decision means "no decision; normal permission
# flow applies", which is exactly right: an approval note is authority to
# stop BLOCKING, not authority to also suppress Claude Code's own permission
# prompt. Every other guard in the stack stays intact.
#
# Why not "defer": the docs scope "defer" to non-interactive (-p) mode, and
# live testing 2026-08-07 confirmed it -- emitting defer in an interactive
# session made the harness fail the tool call with an internal error (the rm
# never ran, twice). Why not "allow": that skips the interactive permission
# prompt, which grants more than the note authorizes.
# -------------------------------------------------------------------------
allow_by_note() {
  local msg="$1"
  jq -n --arg m "$msg" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$m}}'
  GUARD_CLEAN_EXIT=1
  exit 0
}

# -------------------------------------------------------------------------
# Helper: does an unexpired approval note cover EVERY target in this rm?
#
# Returns 0 only when every non-flag path token normalizes cleanly AND has its
# own unexpired note. Partial coverage returns 1 and the block stands -- one
# approved path in a multi-path rm never carries the unapproved ones with it.
# On success, DA_MATCHED_NOTES holds the note files to consume.
# -------------------------------------------------------------------------
DA_MATCHED_NOTES=()
approval_covers_all_targets() {
  local rmcmd="$1" cwd="$2"
  local tok norm note saw_path=0
  DA_MATCHED_NOTES=()

  [[ "$DA_AVAILABLE" -eq 1 ]] || return 1

  # One pass over the notes directory for the whole command. Built here in the
  # main shell, not inside the $(find_approval_note) subshell, so the index is
  # reused for every target instead of re-reading every note once per target.
  da_build_index || return 1

  while IFS= read -r tok; do
    [[ -z "$tok" ]] && continue
    saw_path=1
    norm=$(normalize_target "$tok" "$cwd" literal) || return 1
    note=$(find_approval_note "$norm") || return 1
    DA_MATCHED_NOTES+=("$note")
  done < <(extract_rm_paths "$rmcmd")

  [[ "$saw_path" -eq 1 ]] || return 1
  [[ "${#DA_MATCHED_NOTES[@]}" -gt 0 ]] || return 1
  return 0
}

# Guarantee the array is defined even if the function never ran, so no code
# path can hit an unbound-variable crash (which would fail OPEN, see above).
DA_MATCHED_NOTES=("${DA_MATCHED_NOTES[@]+${DA_MATCHED_NOTES[@]}}")

# -------------------------------------------------------------------------
# Helper: does an unexpired note cover EVERY remote target of an ssh delete?
#
# Same contract as approval_covers_all_targets, for the "<host>:<path>" keys
# that ssh_delete_scan prints. On success DA_MATCHED_NOTES holds the notes.
# -------------------------------------------------------------------------
remote_approval_covers_all() {
  local scan="$1" line k note saw=0
  DA_MATCHED_NOTES=()
  [[ "$DA_AVAILABLE" -eq 1 ]] || return 1
  da_build_index || return 1
  while IFS= read -r line; do
    [[ "$line" == KEY\ * ]] || continue
    k="${line#KEY }"
    [[ -n "$k" ]] || return 1
    saw=1
    note=$(find_approval_note "$k") || return 1
    DA_MATCHED_NOTES+=("$note")
  done <<< "$scan"
  [[ "$saw" -eq 1 ]] || return 1
  [[ "${#DA_MATCHED_NOTES[@]}" -gt 0 ]] || return 1
  return 0
}

# -------------------------------------------------------------------------
# Helper: find a note for every target, then claim them all.
#
# A claim lost to a racing call rebuilds the index and tries again, so a second
# note for the same target can still be used. Three tries, then the block stands.
# -------------------------------------------------------------------------
cover_and_claim() {
  local kind="$1" tries=0
  while (( tries < 3 )); do
    tries=$(( tries + 1 ))
    if [[ "$kind" == remote ]]; then
      remote_approval_covers_all "$2" || return 1
    else
      approval_covers_all_targets "$2" "$3" || return 1
    fi
    claim_approval_notes ${DA_MATCHED_NOTES[@]+"${DA_MATCHED_NOTES[@]}"} && return 0
  done
  return 1
}

if [[ "$TOOL" == "Bash" ]]; then
  CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""')

  # -----------------------------------------------------------------------
  # Rule 0: BLOCK deletes and Trash moves sent over ssh (2026-11-01, Job
  # Tracker row 130). Ember's M2 is reached over ssh, so a delete there never
  # names a local path and Rule 1 cannot see it. Every ssh command is checked.
  # A remote delete passes only when an unexpired single-use note covers every
  # target by host AND path (grant with --host). Read-only ssh passes as before.
  # -----------------------------------------------------------------------
  # Local and remote quote layers disagree about when a continuation joins
  # command words. Refuse it rather than approving a normalized other command.
  if [[ "$CMD" == *$'\\\n'* ]]; then
    block "BLOCKED by pre-tool-use-enforcement: a backslash-newline continuation can assemble hidden local or remote command words. Use literal program names on one physical line; an approval note cannot authorize opaque command text."
  fi
  # Validate visible shell execution boundaries BEFORE wrappers lose operands
  # and BEFORE either approval-library mode. Success is not an authorization.
  # This is not a sandbox for opaque programs/files or inherited shell state:
  # ordinary local DATA, assignments and external scripts retain their policy.
  # No payload, variable, arithmetic expression or external file is evaluated.
  if ! python3 -I - "$CMD" <<'LOCAL_COMMAND_WORDS_PY'
import os
import re
import sys

shells = {"sh", "bash", "zsh", "dash", "ksh", "fish", "csh", "tcsh"}
wrappers = {"env", "command", "builtin", "exec", "sudo", "doas", "nohup", "nice", "timeout", "gtimeout", "time"}
launchers = {"xargs", "parallel", "watch", "stdbuf", "unbuffer", "caffeinate", "arch", "script", "launchctl"}
assignment = re.compile(r"[A-Za-z_][A-Za-z_0-9]*=.*", re.S)
dynamic = re.compile(r"[$`{}*?\[\]]|[@+!]\(")
# Preserve the old scope of unsupported-grammar refusals. This is NOT a safety
# proof: plain opaque local files/options keep their existing executor boundary.
# The provenance/consumer checks below still run for every submission.
legacy_boundary_policy = bool(re.search(
    r"[$`{}*?(|]|\[|\]|(^|[\s;|&])alias\s", sys.argv[1]))


def substitution_end(text, i):
    tick = text[i] == "`"
    start = i + (1 if tick else 2)
    j, level, quote, escaped = start, 1, None, False
    while j < len(text):
        c = text[j]
        if escaped:
            escaped = False
        elif c == "\\" and quote != "'":
            escaped = True
        elif tick and c == "`":
            return start, j
        elif c in "'\"" and (quote is None or quote == c):
            quote = c if quote is None else None
        elif not tick and quote is None:
            if c == "(":
                level += 1
            elif c == ")":
                level -= 1
                if not level:
                    return start, j
        j += 1
    raise ValueError("unbalanced substitution")


class Word(str):
    """A symbolic word, not expanded argv. Only constant words have known bytes.

    Keep the original span and quote/expansion segments at this language layer.
    `one` proves field count, NOT literal value or a passive consumer role.
    """
    def __new__(cls, raw, start=0):
        value, segments, quote, i = [], [], None, 0
        constant, one, prefix, minimum = True, True, [], 0
        while i < len(raw):
            c, begin = raw[i], i
            if c == "\\" and quote != "'":
                if i + 1 == len(raw):
                    raise ValueError("trailing escape")
                if quote is None or raw[i + 1] in '$`"\\\n':
                    value.append(raw[i + 1])
                    minimum += 1
                    if constant:
                        prefix.append(raw[i + 1])
                    segments.append((start + i, start + i + 2, quote, "escaped"))
                    i += 2
                    continue
            if c in "'\"" and (quote is None or quote == c):
                quote = c if quote is None else None
                segments.append((start + i, start + i + 1, quote, "quote"))
                i += 1
                continue
            active = quote != "'" and (c in "$`" or
                     (quote is None and raw.startswith(("<(", ">("), i)))
            if active:
                constant = False
                if raw.startswith(("$(", "<(", ">("), i) or c == "`":
                    _, end = substitution_end(raw, i)
                    token = raw[i:end + 1]
                    # Process substitution is one filename; unquoted command
                    # substitution and parameters can supply zero/many fields.
                    one &= quote is not None or c in "<>"
                    i = end + 1
                else:
                    m = re.match(r"\$(?:[A-Za-z_]\w*|[0-9#?*$!-]|\{[A-Za-z_]\w*\})", raw[i:])
                    token = m[0] if m else c
                    one &= quote is not None and m is not None
                    i += len(token)
                value.append(token)
                segments.append((start + begin, start + i, quote, "expansion"))
                continue
            if quote is None and (c in "*?[]" or raw.startswith(("@(", "+(", "!("), i) or
                                  (c == "{" and re.match(r"\{[^}]*[,\.][^}]*\}", raw[i:]))):
                constant, one = False, False
            value.append(c)
            minimum += 1
            if constant:
                prefix.append(c)
            segments.append((start + i, start + i + 1, quote, "literal"))
            i += 1
        if quote is not None:
            raise ValueError("unbalanced quote")
        obj = str.__new__(cls, "".join(value))
        obj.raw, obj.span, obj.segments = raw, (start, start + len(raw)), segments
        obj.constant, obj.one, obj.prefix = constant, one, "".join(prefix)
        obj.minimum = minimum
        obj.external = False
        return obj

    def derived(self, value, constant=None):
        # A consumer's next language layer, never re-quoted into shell source.
        obj = str.__new__(Word, value)
        obj.raw, obj.span, obj.segments = self.raw, self.span, self.segments
        obj.constant = self.constant if constant is None else constant
        obj.one, obj.prefix = True, value if obj.constant else ""
        obj.minimum = len(value) if obj.constant else 0
        obj.external = False
        return obj


def split_words(text):
    words, quote, start, i = [], None, None, 0
    while i < len(text):
        c = text[i]
        if quote is None and c.isspace():
            if start is not None:
                words.append(Word(text[start:i], start))
                start = None
            i += 1
            continue
        if start is None:
            start = i
        if c == "\\" and quote != "'":
            i += 2
            continue
        if quote != "'" and (text.startswith(("$(", "<(", ">("), i) or c == "`"):
            _, end = substitution_end(text, i)
            i = end + 1
            continue
        if quote is None and c in "<>":
            # Preserve redirection grammar rather than misclassifying its
            # target as a builtin variable name or executable operand.
            match = re.match(r"(?:<<<|<<-|<<|>>|<>|>\||[<>]&|[<>])", text[i:])
            prefix = text[start:i]
            if prefix and not prefix.isdigit():
                words.append(Word(prefix, start))
                start = i
            words.append(Word(text[start:i + len(match[0])], start))
            i += len(match[0])
            start = None
            continue
        if c in "'\"" and (quote is None or quote == c):
            quote = c if quote is None else None
        i += 1
    if start is not None:
        words.append(Word(text[start:], start))
    return words


def field(word):
    if not word.one:
        raise ValueError("unknown zero/many fields in an execution control operand")


def literal(word):
    if not word.constant:
        raise ValueError("unknown executable, option grammar or re-evaluated code")


def attached_field(word, prefix):
    field(word)
    if not prefix.endswith("=") and word.minimum <= len(prefix):
        # "-u$EMPTY" can become "-u", consuming the NEXT operand instead.
        # ONE field alone does not prove this option's consumption grammar.
        raise ValueError("possibly empty attached short-option value")


def context():
    return {"values": {}, "integers": set(), "refs": {}, "aliases": {}}


def remember(word, state, depth):
    name, sep, value = word.partition("=")
    if not sep or not re.fullmatch(r"[A-Za-z_]\w*", name) or not word.prefix.startswith(name + "="):
        raise ValueError("unknown assignment target")
    rhs = word.derived(value)
    state["values"].setdefault(name, []).append(rhs)
    # Only source-visible attributes/indirection are modeled. Unknown inherited
    # attributes do not turn ordinary assignments or scalar DATA into new holds.
    if integer_target(name, state, depth):
        arithmetic(rhs, state, depth + 1)
    for target in state["refs"].get(name, ()):
        variable(target, state, depth + 1)


def integer_target(name, state, depth):
    if depth > 8:
        raise ValueError("indirection nesting too deep")
    for target in state["refs"].get(name, ()):
        variable(target, state, depth + 1)
        if integer_target(target.split("[", 1)[0], state, depth + 1):
            return True
    return name in state["integers"]


def unwrap(words, state=None, depth=0, external=False):
    words = list(words)
    wrapped = False
    while words:
        while words and assignment.fullmatch(words[0]):
            word = words.pop(0)
            if wrapped:
                field(word)  # env NAME=$VALUE is not a Bash assignment word
            if state is not None:
                remember(word, state, depth)
        if not words or os.path.basename(words[0]) not in wrappers:
            if words:
                words[0].external = external
            return words
        original = list(words)
        selector = words.pop(0)
        literal(selector)
        wrapper, wrapped = os.path.basename(selector), True
        external |= wrapper not in {"command", "builtin", "time"} or "/" in selector
        if wrapper == "command" and words and re.fullmatch(r"-[pvV]*[vV][pvV]*", words[0]):
            literal(words[0])
            return [selector] + words  # query operand is DATA, not an executable
        while words and words[0].startswith("-"):
            flag = words.pop(0)
            if flag == "--":
                literal(flag)
                break
            values = {
                "env": {"-u", "--unset", "-C", "--chdir"},
                "sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-R", "-r", "-t",
                         "--user", "--group", "--host", "--prompt", "--close-from",
                         "--chdir", "--chroot", "--role", "--type"},
                "doas": {"-u", "-C"}, "exec": {"-a"}, "nice": {"-n"},
                "timeout": {"-s", "--signal", "-k", "--kill-after"},
                "gtimeout": {"-s", "--signal", "-k", "--kill-after"},
            }
            if flag in values.get(wrapper, set()):
                literal(flag)
                if not words:
                    raise ValueError("missing wrapper option value")
                field(words.pop(0))
            else:
                no_value = {
                    "env": {"-i", "--ignore-environment", "-0", "--null", "-v", "--debug"},
                    "command": {"-p"}, "exec": {"-c", "-l"}, "nohup": set(),
                    "sudo": {"-E", "-H", "-n", "-S", "-b", "-k"},
                    "doas": {"-n", "-s"}, "time": {"-p"},
                    "timeout": {"--foreground", "--preserve-status"},
                    "gtimeout": {"--foreground", "--preserve-status"},
                }
                attached = next((name + ("=" if name.startswith("--") else "")
                                 for name in values.get(wrapper, set())
                                 if flag.startswith(name + ("=" if name.startswith("--") else ""))
                                 and len(flag) > len(name)), None)
                if attached and flag.prefix.startswith(attached):
                    attached_field(flag, attached)
                elif flag in no_value.get(wrapper, set()):
                    literal(flag)
                else:
                    if not legacy_boundary_policy and all(w.constant and w.one for w in original):
                        original[0].external = external
                        return original  # opaque literal tooling, not proved DATA
                    raise ValueError("an unreadable wrapper option")
        if wrapper in {"timeout", "gtimeout"} and words:
            field(words.pop(0))  # duration must not become duration + executable
    return words


def substitutions(text, depth, heredoc=False, state=None):
    quote, escaped, i = None, False, 0
    while i < len(text):
        c = text[i]
        if escaped:
            escaped = False
        elif c == "\\" and (heredoc or quote != "'"):
            escaped = True
        elif ((heredoc or quote != "'") and (text.startswith("$(", i) or c == "`")) \
                or (quote is None and not heredoc and text.startswith(("<(", ">("), i)):
            start, j = substitution_end(text, i)
            if text.startswith("$((", i):
                arithmetic(Word("''").derived(text[start + 1:j - 1], True),
                           state or context(), depth + 1)
            else:
                check(text[start:j], depth + 1, state)
            i = j
        elif not heredoc and c in "'\"" and (quote is None or quote == c):
            quote = c if quote is None else None
        i += 1


def pieces(text):
    quote, escaped, start, i = None, False, 0, 0
    while i < len(text):
        c = text[i]
        if escaped:
            escaped = False
        elif c == "\\" and quote != "'":
            escaped = True
        elif c in "'\"" and (quote is None or quote == c):
            quote = c if quote is None else None
        elif quote != "'" and (text.startswith(("$(", "<(", ">("), i) or c == "`"):
            _, i = substitution_end(text, i)
        elif quote is None and c in ";|&\n" and not (c == "&" and i and text[i - 1] in "<>"):
            yield text[start:i]
            start = i + 1
        i += 1
    yield text[start:]


def command_words(piece, state=None, depth=0):
    piece = re.sub(r"^\s*(?:function\s+)?[A-Za-z_]\w*\s*\(\)\s*\{", "", piece)
    if piece.lstrip().startswith(("<(", ">(")):
        raise ValueError("a process substitution used as a command word")
    words = split_words(piece.lstrip(" ("))
    while words and words[0] in {"if", "then", "elif", "else", "while", "until", "do", "!", "{", "}"}:
        words.pop(0)
    operands, i = [], 0
    while i < len(words):
        if re.fullmatch(r"\d*(?:<<<|<<-|<<|>>|<>|>\||[<>]&|[<>])", words[i].raw):
            if i + 1 == len(words):
                raise ValueError("missing redirection target")
            if not operands and words[i + 1].startswith(("<(", ">(")):
                raise ValueError("a generated leading redirection target")
            i += 2
        else:
            operands.append(words[i])
            i += 1
    return unwrap(operands, state, depth)


def arithmetic(word, state, depth, seen=()):
    if depth > 8:
        raise ValueError("re-evaluation nesting too deep")
    literal(word)
    # Quotes in a literal variable/subscript or arithmetic operand belong to
    # the *consumer's* language, not the original shell-data quote layer.
    substitutions(str(word), depth, heredoc=True, state=state)
    if re.search(r"\$(?!\()|`", str(word)):
        raise ValueError("unknown expanded arithmetic/subscript code")
    for name in set(re.findall(r"\b[A-Za-z_]\w*\b", str(word))):
        if name not in seen:
            for value in state["values"].get(name, ()):
                arithmetic(value, state, depth + 1, seen + (name,))


def variable(word, state, depth):
    if depth > 8:
        raise ValueError("variable-reference nesting too deep")
    literal(word)
    match = re.fullmatch(r"([A-Za-z_]\w*)(?:\[(.*)\])?", word, re.S)
    if not match:
        raise ValueError("an unreadable variable/subscript reference")
    if match[2] is not None:
        arithmetic(word.derived(match[2], True), state, depth + 1)
    for target in state["refs"].get(match[1], ()):
        variable(target, state, depth + 1)
    return match[1]


def code(word, state, depth):
    literal(word)
    check(str(word), depth + 1, state)


def builtin_roles(words, state, depth):
    """Classify each operand before DATA can bypass re-evaluation checks."""
    verb, args = str(words[0]), list(words[1:])
    if verb == "printf":
        destination = None
        while args:
            if args[0] == "--":
                literal(args.pop(0))
                break
            if args[0] == "-v":
                literal(args.pop(0))
                if not args:
                    return
                destination = variable(args.pop(0), state, depth)
            elif args[0].prefix.startswith("-v") and len(args[0]) > 2:
                flag = args.pop(0)
                field(flag)
                destination = variable(flag.derived(flag[2:]), state, depth)
            else:
                break
        if not args:
            return
        fmt = args.pop(0)
        literal(fmt)  # runtime format can change a DATA argument into %n's name
        roles, i = [], 0
        while i < len(fmt):
            if fmt[i] != "%":
                i += 1
                continue
            match = re.match(r"%[-+ #0']*(\*|\d+)?(?:\.(\*|\d+))?(?:[hlL])?(\([^)]*\)T|.)", fmt[i:], re.S)
            if not match:
                break  # invalid literal printf formats cannot introduce code
            conversion = match[3]
            if conversion != "%":
                roles.extend(["number"] * (int(match[1] == "*") + int(match[2] == "*")))
                roles.append("variable" if conversion == "n" else
                             "string" if conversion in {"s", "b", "q", "Q"} else "number")
            i += len(match[0])
        if roles:
            for i, arg in enumerate(args):
                if roles[i % len(roles)] == "variable":
                    variable(arg, state, depth)
        if destination is not None and integer_target(destination, state, depth):
            # Formatting can assemble CODE across individually inert fragments.
            # Prove a numeric-only image, an exact %s identity, or literal bytes;
            # inspecting each ingredient separately would not prove the result.
            decimal = re.sub(r"%[-+ #0']*(?:\*|\d+)?(?:\.(?:\*|\d+))?[diuo]", "", fmt)
            if re.fullmatch(r"[0-9+\-\s]*", decimal):
                pass
            elif fmt == "%s" and len(args) == 1:
                arithmetic(args[0], state, depth + 1)
            elif not args and "%" not in fmt and "\\" not in fmt:
                arithmetic(fmt, state, depth + 1)
            else:
                raise ValueError("unknown formatted CODE assigned to an integer")
        return
    if verb in {"read", "mapfile", "readarray", "unset", "declare", "typeset", "local", "export", "readonly"}:
        declares = verb in {"declare", "typeset", "local", "export", "readonly"}
        integer, nameref, query = False, False, False
        while args and args[0].startswith(("-", "+")) and args[0] not in {"-", "+"}:
            flag = args.pop(0)
            if flag == "--":
                literal(flag)
                break
            if declares:
                literal(flag)
                query |= "p" in flag or "f" in flag or "F" in flag
                integer |= flag.startswith("-") and "i" in flag
                nameref |= flag.startswith("-") and "n" in flag
                continue
            if verb == "unset":
                literal(flag)
                query |= "f" in flag  # function names are not variable subscripts
                continue
            takes = set("adiNnptu") if verb == "read" else set("dnosuOCc")
            flags = flag[1:]
            for j, option in enumerate(flags):
                if option in takes:
                    if not flag.prefix.startswith(flag[:j + 2]):
                        raise ValueError("unknown builtin option grammar")
                    attached = flags[j + 1:]
                    value = flag.derived(attached) if attached else (args.pop(0) if args else None)
                    if value is None:
                        return
                    field(value)
                    if attached:
                        attached_field(flag, flag[:j + 2])
                    if option == "a" and verb == "read":
                        variable(value, state, depth)
                    elif option == "C" and verb != "read":
                        code(value, state, depth)
                    break
            else:
                literal(flag)
        if query:
            return
        for arg in args:
            if declares and "=" in arg:
                name, _, value = arg.partition("=")
                if not arg.prefix.startswith(name + "="):
                    raise ValueError("unknown declaration target")
                target, rhs = arg.derived(name, True), arg.derived(value)
                base = variable(target, state, depth)
                if integer:
                    state["integers"].add(base)
                if nameref:
                    variable(rhs, state, depth)
                    state["refs"].setdefault(base, []).append(rhs)
                remember(arg, state, depth)
            else:
                base = variable(arg, state, depth)
                if integer:
                    state["integers"].add(base)
                if verb in {"read", "mapfile", "readarray"} and integer_target(base, state, depth):
                    raise ValueError("runtime input to a source-visible integer variable")
    elif verb == "let":
        for arg in args:
            arithmetic(arg, state, depth)
    elif verb == "getopts" and len(args) >= 2:
        field(args[0])  # option string is DATA, but its count locates the name
        variable(args[1], state, depth)
    elif verb == "wait":
        for i, arg in enumerate(args):
            match = re.match(r"-[fn]*p", arg)
            if match and arg.prefix.startswith(match[0]):
                field(arg)
                if len(arg) > len(match[0]):
                    variable(arg.derived(arg[len(match[0]):]), state, depth)
                elif i + 1 < len(args):
                    variable(args[i + 1], state, depth)
    elif verb in {"bind", "complete", "compgen"}:
        if verb == "complete" and any(arg == "-p" and arg.constant for arg in args):
            return  # print existing specifications; names are query DATA
        values = dict.fromkeys("fmqur", "data") if verb == "bind" else dict.fromkeys("oAGXPS", "data")
        values.update({"x": "keycode"} if verb == "bind" else
                      {"C": "code", "F": "selector", "W": "expansions"})
        while args:
            flag = args.pop(0)
            if flag == "--":
                literal(flag)
                break
            if not flag.startswith("-"):
                if not flag.prefix:
                    literal(flag)  # unknown first operand could be a CODE option
                break
            for j, option in enumerate(flag[1:]):
                if option not in values:
                    continue
                prefix = flag[:j + 2]
                if not flag.prefix.startswith(prefix):
                    raise ValueError("unknown callback option grammar")
                attached = flag[j + 2:]
                handler = flag.derived(attached) if attached else (args.pop(0) if args else None)
                if handler is None:
                    return
                field(handler)
                if attached:
                    attached_field(flag, prefix)
                role = values[option]
                if role == "keycode":
                    literal(handler)
                    match = re.fullmatch(r'"(?:\\.|[^"])*"\s*:\s*(.*)', handler, re.S)
                    if not match:
                        raise ValueError("unknown key callback grammar")
                    handler = handler.derived(match[1], True)
                if role in {"code", "keycode"}:
                    code(handler, state, depth)
                elif role == "selector":
                    literal(handler)
                elif role == "expansions":
                    literal(handler)
                    substitutions(handler, depth, heredoc=True, state=state)
                break
            else:
                literal(flag)
    elif verb in {"[", "[[", "test"}:
        for i, arg in enumerate(args[:-1]):
            if arg == "-v":
                variable(args[i + 1], state, depth)


def ssh_source(words, state, depth):
    # OpenSSH joins actual argument bytes with spaces. This is a new shell
    # source layer, unlike find's preserved argv and unlike outer shell quoting.
    i, host = 1, False
    value_options = set("BbcDEeFIiJLlmOopPQRSwW")
    while i < len(words):
        word = words[i]
        literal(word)
        if word == "--":
            i += 1
            if not host and i < len(words):
                literal(words[i])
                host, i = True, i + 1
            break
        if word.startswith("-") and len(word) > 1:
            flags = word[1:]
            for j, flag in enumerate(flags):
                if flag in value_options:
                    val = word.derived(flags[j + 1:], True)
                    if not val:
                        i += 1
                        if i == len(words):
                            return
                        val = words[i]
                        literal(val)
                    if flag == "o":
                        opt = re.split(r"[=\s]", val.strip(), maxsplit=1)
                        if opt[0].lower() in {"proxycommand", "localcommand", "remotecommand"} and len(opt) == 2:
                            code(val.derived(opt[1], True), state, depth)
                    break
            i += 1
        elif not host:
            host, i = True, i + 1
        else:
            break
    for word in words[i:]:
        literal(word)
    if i < len(words):
        check(" ".join(words[i:]), depth + 1)


def without_documents(text, depth):
    lines, output, pending, body = text.splitlines(keepends=True), [], [], []
    quote, escaped, in_word = None, False, False
    sub_level, sub_quote, sub_escape, sub_tick = 0, None, False, False
    for line in lines:
        if pending:
            delimiter, tabs, quoted, code = pending[0]
            if (line.rstrip("\r\n").lstrip("\t") if tabs else line.rstrip("\r\n")) == delimiter:
                data = "".join(body)
                if code:
                    check(data, depth + 1)
                elif not quoted:
                    substitutions(data, depth + 1, heredoc=True)
                pending.pop(0)
                body = []
            else:
                body.append(line)
            output.append("\n")
            continue
        i = 0
        while i < len(line):
            c = line[i]
            if sub_level:
                if sub_escape:
                    sub_escape = False
                elif c == "\\" and sub_quote != "'":
                    sub_escape = True
                elif sub_tick and c == "`":
                    sub_level = 0
                elif c in "'\"" and (sub_quote is None or sub_quote == c):
                    sub_quote = c if sub_quote is None else None
                elif not sub_tick and sub_quote is None:
                    if c == "(":
                        sub_level += 1
                    elif c == ")":
                        sub_level -= 1
                i += 1
                continue
            if escaped:
                escaped = False
                in_word = True
            elif c == "\\" and quote != "'":
                escaped = True
                in_word = True
            elif (quote != "'" and (line.startswith("$(", i) or c == "`")) \
                    or (quote is None and line.startswith(("<(", ">(" , "(("), i)):
                sub_tick = c == "`"
                sub_level = 2 if line.startswith("((", i) else 1
                sub_quote, sub_escape, in_word = None, False, True
                if not sub_tick:
                    i += 1
            elif c in "'\"" and (quote is None or quote == c):
                quote = c if quote is None else None
                in_word = True
            elif quote is None and c == "#" and not in_word:
                line = line[:i] + "\n"
                break  # comments cannot introduce data bodies or commands
            elif quote is None and line.startswith("<<<", i):
                head = command_words(list(pieces(line[:i]))[-1])
                if not head or head[0].isdigit() or os.path.basename(head[0]) in shells:
                    raise ValueError("an executable or unreadable here-string")
                i += 2
            elif quote is None and line.startswith("<<", i):
                m = re.match(r"""<<(-?)\s*(['"]?)([A-Za-z_][A-Za-z_0-9-]*)\2(?=\s|[;|&]|$)""", line[i:])
                if not m:
                    raise ValueError("an unreadable here-document delimiter")
                prefix = list(pieces(line[:i]))[-1]
                head = command_words(prefix)
                if not head or head[0].isdigit():
                    raise ValueError("a here-document without a readable consumer")
                pending.append((m[3], bool(m[1]), bool(m[2]), bool(head and os.path.basename(head[0]) in shells)))
                i += len(m[0]) - 1
                in_word = True
            else:
                in_word = quote is not None or (not c.isspace() and c not in ";|&()<>")
            i += 1
        output.append(line)
    if pending or sub_level:
        raise ValueError("an unterminated here-document or substitution")
    return "".join(output)


def check_words(words, state, depth, from_pipe=False, external=False):
    if depth > 8:
        raise ValueError("shell nesting too deep")
    words = unwrap(words, state, depth, external)
    if not words:
        return
    if words[0] not in {"[", "[["}:
        literal(words[0])
    verb = os.path.basename(words[0])
    if not words[0].external and words[0] in state["aliases"]:
        alias = state["aliases"][words[0]]
        check_words(split_words(alias) + words[1:], state, depth + 1, from_pipe)
        return
    if verb in {"case", "coproc", "function", "source", "."}:
        if legacy_boundary_policy:
            raise ValueError("unsupported compound grammar or sourced shell code")
        return  # preserve literal opaque local-file/tooling policy; do not read it
    elif verb in {"ssh", "mosh"}:
        ssh_source(words, state, depth)
    elif verb == "eval":
        for word in words[1:]:
            literal(word)
        check(" ".join(words[1:]), depth + 1, state)
    elif verb == "trap":
        args = words[1:]
        if args and args[0] == "--":
            literal(args[0])
            args = args[1:]
        if args and args[0] not in {"-p", "-l", "", "-"}:
            code(args[0], state, depth)
    elif verb in shells:
        if "<<<" in words:
            raise ValueError("an executable shell here-string")
        for i, word in enumerate(words[1:], 1):
            if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", word):
                literal(word)
                if i + 1 == len(words):
                    raise ValueError("missing shell command string")
                code(words[i + 1], state, depth)
                break
        else:
            # Ordinary opaque script files keep the existing trusted-executor
            # boundary. Generated shell input still is not a proved script.
            if from_pipe or any(w.startswith(("<(", ">(")) for w in words[1:]):
                raise ValueError("uninspected generated shell input")
    elif verb == "find":
        for i, word in enumerate(words):
            if word in {"-exec", "-execdir", "-ok", "-okdir"}:
                literal(word)
                end = next((j for j in range(i + 1, len(words)) if words[j] in {";", "+"}), len(words))
                if end == i + 1:
                    raise ValueError("a missing find executable operand")
                # find passes argv; re-quoting would erase the original field
                # cardinality. Its child is external, not a Bash builtin.
                check_words(words[i + 1:end], state, depth + 1, external=True)
    elif verb in launchers:
        if dynamic.search(" ".join(words[1:])):
            raise ValueError("opaque operands of a command-launching utility")
    elif verb == "alias":
        for word in words[1:]:
            if "=" in word:
                literal(word)
                name, _, value = word.partition("=")
                check(value, depth + 1, state)
                for alias_piece in pieces(value):
                    effective = command_words(alias_piece)
                    if not effective:
                        raise ValueError("an alias without a literal effective program")
                    if os.path.basename(effective[0]) in shells | launchers | {"ssh", "mosh", "sftp", "rsync", "eval", "trap", "source", "."}:
                        raise ValueError("an alias hiding a remote command or shell")
                state["aliases"][name] = value
    elif "/" not in words[0] and not words[0].external:
        builtin_roles(words, state, depth)


def check(text, depth=0, state=None):
    if depth > 8:
        raise ValueError("shell nesting too deep")
    if state is None:
        state = context()
    text = without_documents(text, depth)
    offset = 0
    for piece in pieces(text):
        before = text[:offset].rstrip()
        from_pipe = (before.endswith("|") and not before.endswith("||")) or before.endswith("|&")
        offset += len(piece) + 1
        if piece.strip().startswith("((") and piece.strip().endswith("))"):
            arithmetic(Word("''").derived(piece.strip()[2:-2], True), state, depth)
            continue
        # Keep original word objects through unwrapping and argv consumers.
        words = command_words(piece, state, depth)
        substitutions(piece, depth, state=state)
        check_words(words, state, depth, from_pipe,
                    external=bool(words and words[0].external))


try:
    check(sys.argv[1])
except ValueError:
    sys.exit(1)
LOCAL_COMMAND_WORDS_PY
  then
    block "BLOCKED by pre-tool-use-enforcement: an unknown execution selector, wrapper field count or re-evaluating operand could hide ssh before its deletion check. Keep execution controls literal and evaluation roles readable; an approval note cannot authorize this ambiguity."
  fi
  # The cheap gate strips quotes and backslashes first, so "ssh", \ssh and
  # s''sh still reach the scanner. The scanner makes the real decision.
  if printf '%s' "$CMD" | tr -d "\"'\\\\" | grep -E '(^|[^[:alnum:]_.-])(ssh|mosh|sftp|rsync)([^[:alnum:]_.-]|$)' >/dev/null; then
    SSH_HOLD="Get Allison's explicit yes for this exact remote path, record it, and retry, never bypass this hook: ~/HQ-AI-Workspace-M4/Workbench/scripts/deletion-approval-note.sh grant --host <ssh host> --target <exact remote path> --quote \"<her approval, verbatim>\" --session \"<session name>\"."
    if [[ "$DA_AVAILABLE" -ne 1 ]]; then
      # No library, no scanner. Fail closed on anything that looks like a delete.
      # Case variants name the same Trash on case-insensitive macOS volumes.
      # A dynamic mv can choose the Trash without any literal Trash name.
      # Quotes are deliberately flattened here: with no parser, ambiguity
      # must hold rather than treating an unreadable destination as harmless.
      SSH_TEXT=$(printf '%s' "$CMD" | tr -d "\"'\\\\")
      SSH_DYNAMIC_HOLD=0
      # Without the approval parser, hold opaque shell syntax even when the
      # command word is assembled and never literally spells mv. Keep plain
      # read-only commands with parameter arguments, not scripts/options.
      # shellcheck disable=SC2016 # Regex backticks/operators are literal data.
      if printf '%s' "$SSH_TEXT" | grep -E '[$`{}*?]|\[|\]|(^|[[:space:]])~[^/[:space:]]' >/dev/null; then
        if ! python3 -I - "$CMD" <<'SSH_READ_ONLY_PY'
import os
import shlex
import sys
try:
    words = shlex.split(sys.argv[1])
    if len(words) < 3 or os.path.basename(words[0]) not in {"ssh", "mosh"} \
            or words[1].startswith("-"):
        raise ValueError("not a plain ssh invocation")
    remote = " ".join(words[2:])
    if any(c in remote for c in "\n\r\x1f`") or "$(" in remote:
        raise ValueError("opaque remote syntax")
    lexer = shlex.shlex(remote, posix=True, punctuation_chars=";|&()<>")
    lexer.whitespace_split, lexer.commenters = True, ""
    tokens = list(lexer)
    readonly = {
        "ls", "cat", "du", "df", "grep", "egrep", "fgrep", "rg", "which", "whereis", "type",
        "man", "tail", "head", "wc", "stat", "file", "echo", "printf", "pwd", "uptime",
        "whoami", "id", "hostname", "sw_vers", "uname", "date", "ps", "tree", "md5",
        "shasum", "sha256sum", "diff", "sort", "uniq", "cut", "less", "more", "tee", "true",
        "test", "readlink", "realpath", "dirname", "basename", "mdls", "system_profiler",
    }
    if not tokens or os.path.basename(tokens[0]) not in readonly \
            or any(t and all(c in ";|&()<>" for c in t) for t in tokens):
        raise ValueError("not one literal read-only command")
except ValueError:
    sys.exit(1)
SSH_READ_ONLY_PY
        then
          SSH_DYNAMIC_HOLD=1
        fi
      fi
      # shellcheck disable=SC2016 # Regex backticks/operators are literal data.
      if printf '%s' "$SSH_TEXT" | grep -E '(^|[^[:alnum:]_])(rm|rmdir|unlink|trash|shred|srm)([^[:alnum:]_-]|$)|-delete|--del|(^|[[:space:]/{,])\.[Tt][Rr][Aa][Ss][Hh]([Ee][Ss])?($|[[:space:]/;|&(),]|[*?$`{}<>]|\[|\])|git[[:space:]]+clean|osascript|rmtree|[|<]' >/dev/null \
        || { printf '%s' "$SSH_TEXT" | grep -E '(^|[[:space:];|&(`=/{,])mv($|[[:space:];|&)`},])' >/dev/null \
             && printf '%s' "$SSH_TEXT" | grep -E '[$`;|&(){}<>*?]|\[|\]' >/dev/null; } \
        || [[ "$SSH_DYNAMIC_HOLD" -eq 1 ]]; then
        block "BLOCKED by pre-tool-use-enforcement: a delete sent over ssh, and the approval library is missing, so it cannot be checked. Command: ${CMD:0:200}"
      fi
    else
      SSH_SCAN=$(ssh_delete_scan "$CMD") || SSH_SCAN="BLOCK the remote delete scanner failed."
      case "$SSH_SCAN" in
        NONE) : ;;
        TARGETS*)
          if cover_and_claim remote "$SSH_SCAN"; then
            commit_claimed_notes "remote session_id=$SESSION_ID cwd=$CWD cmd=${CMD:0:200}"
            allow_by_note "ALLOWED by pre-tool-use-enforcement approval-note path: an unexpired single-use note covered every remote target (host and path) in this ssh delete. The note(s) have been logged and consumed (${DA_SUMMARY% }); they will not authorize a second delete. Audit trail: ~/.claude/logs/deletion-approvals.log. Command: ${CMD:0:200}"
          fi
          SSH_TARGETS=$(printf '%s\n' "$SSH_SCAN" | sed -n 's/^KEY //p' | tr '\n' ' ')
          block "BLOCKED by pre-tool-use-enforcement: a delete sent over ssh with no approval note for every remote target (${SSH_TARGETS% }). $SSH_HOLD Command: ${CMD:0:200}"
          ;;
        BLOCK*)
          block "BLOCKED by pre-tool-use-enforcement: ${SSH_SCAN#BLOCK } $SSH_HOLD Command: ${CMD:0:200}"
          ;;
        *)
          block "BLOCKED by pre-tool-use-enforcement: the remote delete scanner gave an unreadable answer, so the guard fails closed. Command: ${CMD:0:200}"
          ;;
      esac
    fi
  fi

  # -----------------------------------------------------------------------
  # Rule 1: BLOCK rm -rf on user-data paths
  # -----------------------------------------------------------------------

  # Detect rm with recursive + force flags targeting user-data paths.
  # Match only when 'rm' appears as a standalone command token (start of string,
  # after whitespace, semicolon, pipe, or &&/||) -- avoids false positives on
  # 'rm -rf' appearing inside string literals in Python/shell scripts.
  # Preserve quoted separators in a standalone rm command. The approval
  # parser rejects unquoted separators before it can consume any note.
  if [[ "$CMD" =~ ^[[:space:]]*rm[[:space:]]+ ]]; then
    RM_CMD="$CMD"
  else
    RM_CMD=$(printf '%s' "$CMD" | grep -oE '(^|[;|&[:space:]])\s*rm\s+[^;|&]*' | head -1 || true)
  fi
  if [[ -n "$RM_CMD" ]]; then
    if printf '%s' "$RM_CMD" | grep -qE 'rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|-(rf|fr))'; then
      if printf '%s' "$RM_CMD" | grep -qE '(~/|/Users/|/home/)'; then
        # Narrow exemption: ephemeral scratch/clone paths proceed without the hold.
        if is_scratch_target "$RM_CMD"; then
          : # exempt -- scratch/clone path only; allow without hold
        elif cover_and_claim local "$RM_CMD" "$CWD"; then
          # Approval-note path: every target carries an unexpired single-use
          # note. Log the allowance with note contents, consume the notes, and
          # let the normal permission flow proceed from here.
          # bash 3.2 (system bash) errors on "${arr[@]}" for an empty array under
          # set -u, and a crashing hook exits 1 -> "non-blocking error, action
          # proceeds" -> fail OPEN. The ${arr[@]+...} idiom is 3.2-safe.
          commit_claimed_notes "session_id=$SESSION_ID cwd=$CWD cmd=${CMD:0:200}"
          allow_by_note "ALLOWED by pre-tool-use-enforcement approval-note path: an unexpired single-use deletion approval note covered every target in this command. The note(s) have been logged and consumed (${DA_SUMMARY% }); they will not authorize a second delete. Audit trail: ~/.claude/logs/deletion-approvals.log. Command: ${CMD:0:200}"
        else
          block "BLOCKED by pre-tool-use-enforcement: rm -rf targeting user-data path detected. Run the pre-flight jsonl check (count ~/.claude/projects/*/*.jsonl bound sessions) and get explicit approval before proceeding. If Allison HAS explicitly approved this deletion, record it and retry -- do not bypass this hook: ~/HQ-AI-Workspace-M4/Workbench/scripts/deletion-approval-note.sh grant --target <exact path> --quote \"<her approval, verbatim>\" --session \"<session name>\". Command: ${CMD:0:200}"
        fi
      fi
    fi
  fi

  # Rule 2: BLOCK git force-push (any variant)
  if printf '%s' "$CMD" | grep -qE 'git\s+push.*(--force|-f)\b|git\s+push.*--force-with-lease'; then
    block "BLOCKED by pre-tool-use-enforcement: force-push is not permitted without explicit Allison go. Describe why force-push is needed and get a per-step approval before retrying. Command: ${CMD:0:200}"
  fi

  # Rule 2b: BLOCK unscoped git identity writes in Allison's real clones
  #
  # Why: git worktree SHARES the parent repo's .git/config for user.name and
  # user.email. Those keys always land in the shared repo-local config unless
  # --global or --worktree is given, so one unscoped `git config user.name`
  # in ANY worktree silently rewrites the committer identity for every other
  # worktree of that repo, existing and future. This is exactly how the
  # 2026-08-07 board-snapshot incident put a CI-bot identity on 59 local lane
  # commits across aura. Canonical: aura doctrine/worktree-git-identity.md.
  #
  # Scope: SETS only. Reads (--get/--list/--show-origin/--show-scope) and the
  # corrective --unset/--unset-all stay allowed, as does anything explicitly
  # --global or --worktree, and any repo under a disposable scratch path
  # (doctrine's sanctioned way to reproduce a CI commit step locally).
  if printf '%s' "$CMD" | grep -qE 'git\s+(-C\s+[^[:space:]]+\s+)?(-c\s+[^[:space:]]+\s+)*config\b' \
    && printf '%s' "$CMD" | grep -qE 'user\.(name|email)[[:space:]]+[^[:space:]-]'; then
    if ! printf '%s' "$CMD" | grep -qE '\-\-(global|system|worktree|get|get-all|get-regexp|list|show-origin|show-scope|unset|unset-all)\b'; then
      # Resolve which repo this would poison: -C <path> if given, else cwd.
      GC_TARGET=$(printf '%s' "$CMD" | sed -nE 's/.*git[[:space:]]+-C[[:space:]]+([^[:space:]]+).*/\1/p')
      [[ -z "$GC_TARGET" ]] && GC_TARGET="$CWD"
      # Disposable scratch clones are the sanctioned place to do this.
      if ! printf '%s' "$GC_TARGET" | grep -qE '/private/tmp/claude-501/|/scratchpad/|/working/_clone_|/working/[^/]*\.clone(/|$)'; then
        block "BLOCKED by pre-tool-use-enforcement: unscoped git identity write. \`git config user.name/user.email\` without --global or --worktree writes to the SHARED repo-local .git/config, which silently rewrites the commit identity for EVERY worktree of this repo (this is the 2026-08-07 board-snapshot incident: 59 local lane commits landed under a CI-bot identity). Allison's standing convention is one global identity, Allison Gaddy <allison@expertpartners.com>, with no repo-local or worktree-local override anywhere. If you are setting the estate identity, use --global. If you are reproducing a CI workflow's commit step, do it in a disposable clone under a scratchpad path, never in ~/HQ-AI-Workspace-M4/Projects/. Reads and --unset are not blocked. Doctrine: aura doctrine/worktree-git-identity.md. Target repo: $GC_TARGET. Command: ${CMD:0:200}"
      fi
    fi
  fi

  # Rule 3: WARN on git commit directly to main (advisory only)
  if printf '%s' "$CMD" | grep -qE 'git\s+commit'; then
    BRANCH=$(git -C "$CWD" branch --show-current 2>/dev/null || true)
    if [[ "$BRANCH" == "main" ]]; then
      # Check if the commit is in a delegated category (Push-Policy trailer present)
      if ! printf '%s' "$CMD" | grep -qiE 'Push-Policy:'; then
        warn "ADVISORY (pre-tool-use-enforcement): You are committing directly to main with no Push-Policy trailer. Verify this commit falls into a delegated category (closeout/doctrine/adr/tracker/docs). If it is code, schema, or config -- stop and create a branch. Current branch: main, CWD: $CWD"
      fi
    fi
  fi

  # Rule 4: WARN on git reset --hard
  if printf '%s' "$CMD" | grep -qE 'git\s+reset\s+--hard'; then
    warn "ADVISORY (pre-tool-use-enforcement): git reset --hard detected. This is destructive and cannot be undone. Verify the target ref and that no unreachable commits will be lost. Command: ${CMD:0:200}"
  fi
fi

# -------------------------------------------------------------------------
# Rule 5: WARN on Write tool targeting sensitive config files
# -------------------------------------------------------------------------
if [[ "$TOOL" == "Write" ]]; then
  FILEPATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""')

  # ~/.claude/settings.json or settings.local.json
  if printf '%s' "$FILEPATH" | grep -qE '\.claude/settings(\.local)?\.json$'; then
    warn "ADVISORY (pre-tool-use-enforcement): Writing to Claude Code settings.json. This affects ALL sessions and hooks globally. Verify the exact change before proceeding. If you are adding a hook, confirm the hook script exists and is tested. File: $FILEPATH"
  fi

  # ~/.zshrc, ~/.bashrc, ~/.zprofile, ~/.bash_profile
  if printf '%s' "$FILEPATH" | grep -qE '(\.zshrc|\.bashrc|\.zprofile|\.bash_profile)$'; then
    warn "ADVISORY (pre-tool-use-enforcement): Writing to shell init file. Changes affect every new shell on M4. Verify the exact content before proceeding. File: $FILEPATH"
  fi
fi

GUARD_CLEAN_EXIT=1
exit 0
