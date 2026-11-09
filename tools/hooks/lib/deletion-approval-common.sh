#!/usr/bin/env bash
# deletion-approval-common.sh
# Shared definitions for the deletion approval-note path.
#
# Sourced by BOTH:
#   ~/HQ-AI-Workspace-M4/Workbench/scripts/deletion-approval-note.sh      (writes notes)
#   ~/HQ-AI-Workspace-M4/Workbench/scripts/pre-tool-use-enforcement.sh    (reads, honors, consumes notes)
#
# Both sides MUST agree byte-for-byte on what "the exact target path" means,
# which is why normalization lives here once instead of twice.
#
# Ruled by Allison 2026-08-07: an approved deletion goes THROUGH the guard via
# an approval note, never around it. See ~/.claude/rules/behavior-defaults.md.

# Where notes live. One file per granted approval.
DELETION_APPROVAL_DIR="${DELETION_APPROVAL_DIR:-$HOME/.claude/deletion-approvals}"

# Append-only audit log of grants, allowances, consumptions, and expiry rejects.
DELETION_APPROVAL_LOG="${DELETION_APPROVAL_LOG:-$HOME/.claude/logs/deletion-approvals.log}"

# Default note lifetime, and the hard ceiling a caller may request.
# Short by design: a stale approval must die on its own, not linger.
DELETION_APPROVAL_TTL_DEFAULT="${DELETION_APPROVAL_TTL_DEFAULT:-900}"    # 15 minutes
DELETION_APPROVAL_TTL_MAX="${DELETION_APPROVAL_TTL_MAX:-3600}"           # 1 hour ceiling

# -------------------------------------------------------------------------
# now_epoch -- seconds since epoch (portable)
# -------------------------------------------------------------------------
now_epoch() { date +%s; }

# -------------------------------------------------------------------------
# da_log <event> <message>
#
# Appends one timestamped line to the audit log. Never fails the caller:
# a logging problem must not turn into a guard failure in either direction.
# -------------------------------------------------------------------------
da_log() {
  local event="$1" msg="$2" ts
  ts=$(date '+%Y-%m-%dT%H:%M:%S%z')
  mkdir -p "$(dirname "$DELETION_APPROVAL_LOG")" 2>/dev/null || true
  printf '%s [%s] %s\n' "$ts" "$event" "$msg" >>"$DELETION_APPROVAL_LOG" 2>/dev/null || true
}

# -------------------------------------------------------------------------
# normalize_target <raw-token> <cwd> [literal]
#
# Turns a path token into the single canonical form both sides compare on.
# Prints the normalized path on stdout and returns 0, or returns 1 when the
# token must never be matchable by a note.
#
# Rules:
#   - surrounding single/double quotes stripped
#   - a token containing '..' is REJECTED (path traversal is never approvable,
#     matching the existing is_scratch_target stance in the hook)
#   - glob metacharacters (* ? [ ]) are REJECTED: an approval note names one
#     exact target, and a glob is not one exact target. The one exception is a
#     third argument of "literal" (2026-10-25), passed by callers that already
#     know the characters are literal: the grant script, which records one
#     exact path, and the hook, whose extract_rm_paths refuses any command
#     where a glob character is not quoted or escaped. A name such as
#     "Signature [All Versions]" is then one exact target, never a pattern.
#   - leading ~ expands to $HOME
#   - relative paths resolve against <cwd>
#   - '//' collapses, '/./' collapses, trailing '/' stripped (except root)
#
# Deliberately LEXICAL only -- no symlink resolution. The target of a delete
# may be about to stop existing, and realpath's behavior on a missing path is
# not uniform across platforms. Lexical normalization is deterministic on both
# sides, which is the property that matters here.
# -------------------------------------------------------------------------
normalize_target() {
  local tok="$1" cwd="${2:-}" mode="${3:-}"

  # strip one layer of surrounding quotes
  case "$tok" in
    \"*\") tok="${tok#\"}"; tok="${tok%\"}" ;;
    \'*\') tok="${tok#\'}"; tok="${tok%\'}" ;;
  esac

  [[ -z "$tok" ]] && return 1

  # never approvable
  case "$tok" in
    *..*) return 1 ;;
  esac
  if [[ "$mode" != "literal" ]]; then
    case "$tok" in
      *\**|*\?*|*\[*|*\]*) return 1 ;;
    esac
  fi

  # tilde expansion
  if [[ "$tok" == "~" ]]; then
    tok="$HOME"
  elif [[ "$tok" == "~/"* ]]; then
    tok="$HOME/${tok#\~/}"
  fi

  # resolve relative against cwd
  if [[ "$tok" != /* ]]; then
    [[ -z "$cwd" ]] && return 1
    tok="$cwd/$tok"
  fi

  # Collapse /./ and duplicate slashes.
  #
  # Done with sed, NOT bash ${var//pat/repl}, on purpose. System bash on macOS
  # is 3.2, and its replacement handling is a trap here: the inline form
  # ${tok//\/.\//\/} takes the replacement literally and yields 'working\/_test',
  # while the quoted-variable form ${tok//"$p"/"$r"} yields 'working"/"_test'.
  # Both silently break matching, so two spellings of the same path stop
  # matching one note. sed behaves identically on every bash we run.
  # The :a/ta loop re-runs the /./ rule so overlapping cases (/././) collapse.
  tok=$(printf '%s' "$tok" | sed -e ':a' -e 's|/\./|/|g' -e 'ta' -e 's|//*|/|g') || return 1
  [[ -z "$tok" ]] && return 1
  [[ "$tok" == */. ]] && tok="${tok%/.}"

  # strip trailing slashes, but keep root as "/"
  while [[ "$tok" == */ && "$tok" != "/" ]]; do tok="${tok%/}"; done

  [[ -z "$tok" ]] && tok="/"
  printf '%s' "$tok"
  return 0
}

# -------------------------------------------------------------------------
# extract_rm_paths <rm-command-fragment>
#
# Prints one raw (un-normalized) path token per line from an rm command
# fragment, skipping the 'rm' word itself and every -flag. Callers normalize.
# -------------------------------------------------------------------------
extract_rm_paths() {
  # Shell word splitting loses the boundary of a quoted path containing spaces.
  # Parse the complete fragment before printing anything so malformed commands
  # cannot partially match an approval note.
  python3 - "$1" <<'PY'
import shlex
import sys

command = sys.argv[1].lstrip(" ;|&\t")
# Bash expands dollars and backticks outside single quotes. Reject active
# expansions before shlex removes quoting, including in option tokens.
quote = None
escaped = False
for char in command:
    if char in "\n\r" or (char in ";|&" and quote is None):
        sys.exit(1)
    if escaped:
        escaped = False
        continue
    if char == "\\" and quote != "'":
        escaped = True
        continue
    if char == "'" and quote is None:
        quote = "'"
    elif char == "'" and quote == "'":
        quote = None
    elif char == '"' and quote is None:
        quote = '"'
    elif char == '"' and quote == '"':
        quote = None
    elif char in "$`" and quote != "'":
        sys.exit(1)
    elif char in "{}<>()" and quote is None:
        # Brace expansion, process substitution, and shell grouping can turn
        # one apparent path token into a different command or multiple paths.
        sys.exit(1)

def split_words(text):
    """Split like bash and report, per word, whether a glob character (* ? [ ])
    appears outside quotes and escapes. Such a word would be expanded by the
    shell into paths the hook never saw, so the whole command is refused."""
    words, cur, unquoted_glob, in_word, quote, i = [], [], False, False, None, 0
    while i < len(text):
        c = text[i]
        if quote is None:
            if c in " \t":
                if in_word:
                    words.append(("".join(cur), unquoted_glob))
                    cur, unquoted_glob, in_word = [], False, False
            elif c == "\\":
                if i + 1 >= len(text):
                    raise ValueError("trailing backslash")
                cur.append(text[i + 1])
                in_word = True
                i += 1
            elif c in "'\"":
                quote = c
                in_word = True
            else:
                if c in "*?[]":
                    unquoted_glob = True
                cur.append(c)
                in_word = True
        elif quote == "'":
            if c == "'":
                quote = None
            else:
                cur.append(c)
        else:
            if c == '"':
                quote = None
            elif c == "\\" and i + 1 < len(text) and text[i + 1] in '"\\':
                cur.append(text[i + 1])
                i += 1
            else:
                cur.append(c)
        i += 1
    if quote is not None:
        raise ValueError("unterminated quote")
    if in_word:
        words.append(("".join(cur), unquoted_glob))
    return words

try:
    words = split_words(command)
    tokens = shlex.split(command, posix=True)
except ValueError:
    sys.exit(1)
# Two independent parsers must agree on every word, or the command is refused.
if [w for w, _ in words] != tokens:
    sys.exit(1)
if not tokens or tokens[0] != "rm":
    sys.exit(1)
glob_flags = [g for _, g in words]
paths = []
options = True
for index, token in enumerate(tokens[1:], start=1):
    if options and token == "--":
        options = False
        continue
    if options and not paths and token.startswith("-"):
        if any(char not in "-rfRivdP" for char in token):
            sys.exit(1)
        continue
    if options and token.startswith("-"):
        sys.exit(1)
    if glob_flags[index]:
        sys.exit(1)
    paths.append(token)
if not paths:
    sys.exit(1)
sys.stdout.write("\n".join(paths) + "\n")
PY
}

# -------------------------------------------------------------------------
# REMOTE DELETES OVER SSH (added 2026-11-01, Job Tracker row 130)
#
# A delete sent over ssh to Ember's M2 (ssh ember 'rm -rf /tmp/x') never
# touches a local path, so Rule 1 cannot see it. These helpers let the hook
# catch it and let a note approve it, matched by host AND path.
#
# A remote note's target is the key "<host>:<path>", for example
# "ember:/tmp/scratch-x". A local note's target always starts with "/", so the
# two kinds can never match each other.
#
# Remote paths are normalized on their own terms. A leading ~ stays as ~,
# because it means the remote user's home, not this Mac's. A relative path is
# never approvable, because the remote working folder is not known here.
#
# Every ssh command is checked, not only the host named ember, so a different
# alias or user@address for the M2 can never slip past. A plain read-only ssh
# command still passes untouched.
#
#   normalize_remote_key <host> <path>   prints the key, or returns 1
#   ssh_delete_scan <full command>       prints one of
#       NONE                  no remote delete here, carry on
#       BLOCK <reason>        a remote delete no note can approve
#       TARGETS               followed by one "KEY <host>:<path>" per target
# -------------------------------------------------------------------------
da_ssh_py() {
  python3 -I - "$@" <<'PY'
import os
import re
import shlex
import sys

PATH_VERBS = {"rm", "rmdir", "unlink", "trash"}
DELETE_VERBS = PATH_VERBS | {"srm", "shred"}
INTERPRETERS = {
    "bash", "sh", "zsh", "dash", "ksh", "fish", "csh", "tcsh", "python", "python3",
    "perl", "ruby", "node", "osascript", "php", "lua", "tclsh", "expect", "pwsh",
}
WRAPPERS = {
    "sudo", "doas", "env", "command", "builtin", "exec", "eval", "nice", "nohup",
    "time", "timeout", "gtimeout", "xargs", "caffeinate", "arch", "script", "stdbuf",
    "unbuffer", "launchctl", "find", "git", "rsync", "parallel", "watch",
}
SSH_VALUE_OPTS = set("BbcDEeFIiJLlmOoPpQRSWw")
READ_ONLY = {
    "ls", "cat", "du", "df", "grep", "egrep", "fgrep", "rg", "which", "whereis", "type",
    "man", "tail", "head", "wc", "stat", "file", "echo", "printf", "pwd", "uptime",
    "whoami", "id", "hostname", "sw_vers", "uname", "date", "ps", "tree", "md5",
    "shasum", "sha256sum", "diff", "sort", "uniq", "cut", "less", "more", "tee", "true",
    "test", "readlink", "realpath", "dirname", "basename", "mdls", "system_profiler",
}
COMMAND_OPTS = {"remotecommand", "proxycommand", "localcommand"}
RISKY_OPTS = COMMAND_OPTS | {
    "hostname", "proxyjump", "include", "match", "permitlocalcommand", "controlpath",
    "controlmaster", "canonicaldomains", "canonicalizehostname",
}
DESTRUCTIVE = [
    re.compile(r"(?:^|[\s;|&(`=/{,])(?:rm|rmdir|unlink|trash|shred|srm)(?=$|[\s;|&)`},])"),
    re.compile(r"-delete\b"),
    re.compile(r"--del"),
    re.compile(r"(?:^|[/\s{,])\.Trash(?:es)?(?=$|[/\s;|&(){},$`*?\[\]<>])", re.IGNORECASE),
    re.compile(r"rmtree|os\.(?:remove|unlink|rmdir)|\.(?:unlink|rmdir|remove)\(|rmSync|unlinkSync|rmdirSync|rm_rf|rm_r\b|FileUtils\.rm", re.IGNORECASE),
    re.compile(r"osascript.*\bdelete\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bgit\b.*\bclean\b", re.DOTALL),
]
# A dynamic move may resolve to the Trash without spelling a Trash component
# at all ("mv /tmp/x $D"), or join it to an expanded prefix ("${P}.Trash").
# Never try to approve destinations the shell, rather than this guard, chooses.
MOVE_WORD = re.compile(r"(?:^|[\s;|&(`=/{,])mv(?=$|[\s;|&)`},])")
DYNAMIC_SHELL = re.compile(r"[$`;|&(){}<>*?\[\]]")
BIN = r"(?:(?:/usr/bin|/usr/local/bin|/opt/homebrew/bin|/bin)/)?"
SSH_WORD = re.compile(r"(?:^|[\s;|&(`$])" + BIN + r"=?(?:ssh|mosh)(?=\s|$)")
FED_INTO_SSH = re.compile(r"\|\s*" + BIN + r"=?(?:ssh|mosh)(?=\s|$)|(?:^|[\s;|&(`$])" + BIN + r"=?(?:ssh|mosh)\s[^|;&]*<")


def plain(text):
    """The text with every quote and backslash removed, so a word cannot hide
    behind quoting (r''m, \\rm, "ssh")."""
    return re.sub(r"[\"'\\]", "", text)


def dynamic_tilde(word):
    # Only the plain home anchor is predictable. ~+/~- (including stack
    # indices) and zsh named directories can resolve to an attacker-set Trash.
    return (not word.first_quoted and word.text.startswith("~")
            and word.text != "~" and not word.text.startswith("~/"))


def known_non_deleting_move_piece(text):
    """Recognize a literal non-Trash destination, not a whole shell script.

    Inspect words without expanding them. An expanded source needs -- or a
    quoted scalar with a stable literal prefix. Never exempt
    substitutions, redirections or grouping.
    Pure assignments are data; any later hidden command is checked separately
    against the full command's move context.
    """
    if "$(" in text or "`" in text or unquoted_has(text, ";|&<>()"):
        return False
    try:
        words = split_words(text)
        if not words or [w.text for w in words] != shlex.split(text):
            return False
    except ValueError:
        return False
    # A comment can hide the actual final argument. Keep escaped/quoted
    # literal hashes, but never use comment words as destination evidence.
    if any(w.text.startswith("#") and not w.first_quoted for w in words):
        return False
    assignment = re.compile(r"[A-Za-z_][A-Za-z_0-9]*=.*", re.DOTALL)
    if all(assignment.fullmatch(w.text) for w in words):
        return not any(p.search(plain(text)) for p in DESTRUCTIVE)
    # Only transparent wrappers with no options can be inspected this way.
    while words and not words[0].quoted and not words[0].glob \
            and words[0].text in {"env", "command", "exec", "sudo", "doas", "nohup"}:
        wrapper = words.pop(0).text
        if wrapper == "env":
            while words and assignment.fullmatch(words[0].text):
                words.pop(0)
    if len(words) < 3 or words[0].quoted or words[0].glob \
            or os.path.basename(words[0].text) != "mv":
        return False
    destination = words[-1]
    if destination.glob or dynamic_tilde(destination) or any(c in destination.text for c in "$`{}") \
            or destination.text.startswith("-"):
        return False
    options, saw_source = True, False
    for word in words[1:-1]:
        if options and word.text == "--" and not word.quoted:
            options = False
        elif options and word.text.startswith("-"):
            if saw_source or not re.fullmatch(r"-[fvin]+", word.text):
                return False
        else:
            # Quoting alone does not stop --target-directory=... from being
            # an option. A leading variable/glob/brace needs an earlier --.
            if options and word.text and word.text[0] in "$`{*?[~":
                return False
            # An unquoted scalar can split off a later --target-directory
            # field despite a stable prefix. Quoted arrays/$@ can do so too.
            scalar_only = re.sub(r"\$(?:[A-Za-z_][A-Za-z_0-9]*|\{[A-Za-z_][A-Za-z_0-9]*\})", "", word.text)
            if options and (word.unquoted_expansion or "$" in scalar_only):
                return False
            saw_source = True
    path = norm_path(destination.text) or destination.text
    return saw_source and not is_trash(path) and not has_trash_component(path)


def looks_dynamic_move(text):
    t = plain(text)
    expansion = DYNAMIC_SHELL.search(t) or re.search(r"(?:^|\s)~[^/\s]", t)
    return bool(MOVE_WORD.search(t) and expansion
                and not known_non_deleting_move_piece(text))


def looks_destructive(text):
    t = plain(text)
    if any(p.search(t) for p in DESTRUCTIVE) or looks_dynamic_move(text):
        return True
    for _seps, piece in split_unquoted(text):
        first = first_word(piece)
        if re.search(r"[$`{}*?\[\]]", first):
            return True
        if first in INTERPRETERS | WRAPPERS and DYNAMIC_SHELL.search(plain(piece)):
            return True
    return False


def out(*lines):
    sys.stdout.write("\n".join(lines) + "\n")
    sys.exit(0)


def unsafe(command):
    """True when the text holds anything the shell would expand, chain,
    redirect, group or comment out, or a quote that never closes."""
    quote = None
    escaped = False
    in_word = False
    for ch in command:
        if ch in "\n\r\x1f":
            return True
        if escaped:
            escaped = False
            in_word = True
            continue
        if ch == "\\" and quote != "'":
            escaped = True
            in_word = True
            continue
        if ch == "'" and quote is None:
            quote = "'"
        elif ch == "'" and quote == "'":
            quote = None
        elif ch == '"' and quote is None:
            quote = '"'
        elif ch == '"' and quote == '"':
            quote = None
        elif quote is None and ch in ";|&":
            return True
        elif ch in "$`" and quote != "'":
            return True
        elif quote is None and ch in "{}<>()":
            return True
        elif quote is None and ch == "#" and not in_word:
            # shlex.split keeps comments as words. In "mv source ~/.Trash #
            # cleanup", that would misread cleanup as a non-Trash destination
            # and allow the actual Trash move. Comments are not approvable.
            return True
        # Escaped whitespace, quoted text and even empty quotes keep a word
        # open. Only unquoted, unescaped whitespace starts a new shell word.
        in_word = quote is not None or ch not in " \t"
    return quote is not None or escaped


class Word:
    def __init__(self):
        self.chars, self.glob, self.quoted, self.first_quoted = [], False, False, None
        self.unquoted_expansion = False

    @property
    def text(self):
        return "".join(self.chars)


def split_words(text):
    """Split like bash. Per word, record a glob character outside quotes,
    any quoting or escaping, and whether the first character was quoted."""
    words, cur, quote, i = [], None, None, 0

    def add(ch, q):
        cur.chars.append(ch)
        if not q and ch in "$`":
            cur.unquoted_expansion = True
        if cur.first_quoted is None:
            cur.first_quoted = q

    while i < len(text):
        c = text[i]
        if quote is None:
            if c in " \t":
                if cur is not None:
                    words.append(cur)
                    cur = None
            elif c == "\\":
                if i + 1 >= len(text):
                    raise ValueError("trailing backslash")
                cur = cur or Word()
                cur.quoted = True
                add(text[i + 1], True)
                i += 1
            elif c in "'\"":
                cur = cur or Word()
                cur.quoted = True
                quote = c
            else:
                cur = cur or Word()
                if c in "*?[]":
                    cur.glob = True
                add(c, False)
        elif quote == "'":
            if c == "'":
                quote = None
            else:
                add(c, True)
        else:
            if c == '"':
                quote = None
            elif c == "\\" and i + 1 < len(text) and text[i + 1] in '"\\':
                add(text[i + 1], True)
                i += 1
            else:
                add(c, True)
        i += 1
    if quote is not None:
        raise ValueError("unterminated quote")
    if cur is not None:
        words.append(cur)
    return words


def parse(text):
    """Two independent parsers must agree, or the text is refused."""
    if unsafe(text):
        return None
    try:
        words = split_words(text)
        tokens = shlex.split(text, posix=True)
    except ValueError:
        return None
    if [w.text for w in words] != tokens or not tokens:
        return None
    return words


def norm_host(raw):
    """The host as typed, lower case. A login name stays in the key
    (root@ember is not ember), because ~ and file ownership depend on it."""
    user, _, host = raw.rpartition("@")
    host = host.lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", host):
        return None
    if user:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", user):
            return None
        # Login names are case sensitive on the remote, so keep them exact.
        return user + "@" + host
    return host


def norm_path(tok):
    if not tok or ".." in tok or "\x1f" in tok or "\n" in tok:
        return None
    if not (tok == "~" or tok.startswith("~/") or tok.startswith("/")):
        return None
    while "/./" in tok:
        tok = tok.replace("/./", "/")
    tok = re.sub(r"/+", "/", tok)
    if tok.endswith("/."):
        tok = tok[:-2]
    while tok.endswith("/") and tok != "/":
        tok = tok[:-1]
    if tok in ("", "/", "~"):
        # A whole disk or a whole home folder is never one approvable target.
        return None
    if tok.count("/") == 1 and tok.startswith("/"):
        # A top-level folder such as /tmp, /Users or /Applications.
        return None
    if re.fullmatch(
        r"/(System/Volumes/Data/)?(Users|home|Volumes)/[^/]+|/System/Volumes(/[^/]+)?"
        r"|/System/Volumes/Data/(Users|home|Volumes|private|Applications|Library)"
        r"|/(System/Volumes/Data/)?private/(tmp|var|etc)|/(System/Volumes/Data/)?(private/)?var/root",
        tok,
        re.IGNORECASE,
    ):
        # macOS volumes are usually case-insensitive, so /users/x is /Users/x.
        # A whole home folder or disk, spelled out.
        return None
    return tok


_USER_CACHE = {}


def effective_user(target, opts=()):
    """The login name ssh will really use, read with ssh -G given the same
    options as the command (-l, -o User, -P tags and the rest), which applies
    ~/.ssh/config without connecting. Read once per invocation. None when it
    cannot be read, and the caller then refuses."""
    import subprocess
    cache_key = (target, tuple(opts))
    if cache_key in _USER_CACHE:
        return _USER_CACHE[cache_key]
    cmd = [os.environ.get("DELETION_APPROVAL_SSH_BIN") or "ssh", "-G"]
    if os.environ.get("DELETION_APPROVAL_SSH_CONFIG"):
        cmd += ["-F", os.environ["DELETION_APPROVAL_SSH_CONFIG"]]
    cmd += list(opts)
    cmd.append(target)
    _USER_CACHE[cache_key] = None
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode != 0:
        return None
    for line in res.stdout.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "user":
            user = parts[1].strip()
            if re.fullmatch(r"[A-Za-z0-9._-]+", user):
                _USER_CACHE[cache_key] = user
            return _USER_CACHE[cache_key]
    return None


def key(host, path, opts=()):
    """host:path for a note, where host is always user@alias with the user ssh
    will really log in as, so a note never covers a different account."""
    h = norm_host(host)
    p = norm_path(path)
    if h is None or p is None:
        return None
    user = effective_user(h, opts)
    if user is None:
        return None
    alias = h.rpartition("@")[2]
    return user + "@" + alias + ":" + p


def is_trash(path):
    # Ember's macOS volume can be case-insensitive. A different case must
    # never turn a Trash move into an ordinary, unguarded rename.
    return bool(re.match(r"^(~|/Users/[^/]+)/\.Trash(/|$)", path, re.IGNORECASE)
                or re.match(r"^/Volumes/[^/]+/\.Trashes(/|$)", path, re.IGNORECASE))


def has_trash_component(path):
    return any(part.lower() in (".trash", ".trashes") for part in path.split("/"))


def ssh_invocation(tokens):
    """Read ssh's options wherever they sit (OpenSSH accepts them after the
    host too). Returns host, remote command tokens, risky flag, option values."""
    i, host, risky, command_opts, user, opts = 1, None, False, [], None, []
    while i < len(tokens):
        tok = tokens[i]
        if tok == "--":
            i += 1
            if host is None and i < len(tokens):
                host = tokens[i]
                i += 1
            break
        if tok.startswith("-") and len(tok) > 1:
            opts.append(tok)
            flags, j, consumed = tok[1:], 0, False
            while j < len(flags):
                c = flags[j]
                if c in SSH_VALUE_OPTS:
                    val = flags[j + 1:]
                    if not val:
                        val = tokens[i + 1] if i + 1 < len(tokens) else ""
                        consumed = True
                        opts.append(val)
                    if c in "FJWS":
                        risky = True
                    if c == "l":
                        user = val
                    if c == "o":
                        name = re.split(r"[=\s]", val.strip(), maxsplit=1)[0].lower()
                        rest = val.strip()[len(name):].lstrip(" \t=")
                        if name in RISKY_OPTS:
                            risky = True
                        if name == "user":
                            user = rest
                        if name in COMMAND_OPTS:
                            command_opts.append(rest)
                    break
                j += 1
            i += 2 if consumed else 1
            continue
        if host is None:
            host = tok
            i += 1
            continue
        break
    if host is not None and user and "@" not in host:
        host = user + "@" + host
    return host, tokens[i:] if host is not None else [], risky, command_opts, opts


def first_word(text):
    try:
        toks = shlex.split(plain(text))
    except ValueError:
        return ""
    return os.path.basename(toks[0].lstrip("=")) if toks else ""


def check_command_opts(command_opts):
    for val in command_opts:
        if looks_destructive(val) or first_word(val) in INTERPRETERS | WRAPPERS | DELETE_VERBS:
            block("an ssh option (RemoteCommand, ProxyCommand or LocalCommand) that runs a delete or a shell. Put the command after the host in plain words instead.")


class Verdict(Exception):
    def __init__(self, kind, payload):
        super().__init__(kind)
        self.kind, self.payload = kind, payload


def none():
    raise Verdict("NONE", None)


def block(reason):
    raise Verdict("BLOCK", reason)


def remote_verdict(host, remote, risky, opts=()):
    """Decide one remote command. Raises Verdict NONE, BLOCK or TARGETS."""
    rwords = parse(remote.strip())
    if rwords is None:
        # Chained or piped remote text. Read-only pieces (ls ~/.Trash | wc -l)
        # pass. Command substitutions can run hidden command words which
        # spell no literal delete verb. None of them is approvable.
        if "`" in remote or "$(" in remote:
            block("a remote command substitution this guard cannot read, which no note can approve.")
        # Keep the full command's context when splitting it. In A=mv; "$A"
        # neither isolated piece still spells both the move and expansion.
        dynamic_move = looks_dynamic_move(remote)
        for _seps, piece in split_unquoted(remote):
            if first_word(re.sub(r"\d*[<>]+&?\S*", " ", piece)) in READ_ONLY:
                continue
            if known_non_deleting_move_piece(piece):
                continue
            # Unknown non-read-only shell pieces cannot be proved harmless
            # by the absence of a literal mv: "$A"v can construct it instead.
            if looks_destructive(piece) or dynamic_move or re.search(r"[$`{}*?\[\]]", plain(piece)):
                block("a remote delete with chained, piped, expanded or unbalanced text. Send one plain delete per ssh command.")
        none()
    first = rwords[0]
    raw_verb = first.text
    verb = os.path.basename(raw_verb.lstrip("="))
    if first.quoted or first.glob or raw_verb.startswith("="):
        if looks_destructive(remote) or verb not in READ_ONLY:
            block("a remote command whose first word is quoted, escaped, a pattern or starts with =, which hides what it runs.")

    if verb in PATH_VERBS:
        paths, options = [], True
        for w in rwords[1:]:
            tok = w.text
            if options and tok == "--" and not w.quoted:
                options = False
                continue
            if options and not paths and tok.startswith("-"):
                if not re.fullmatch(r"-[A-Za-z]+", tok):
                    block("a remote delete with an option this guard cannot read.")
                continue
            if options and tok.startswith("-"):
                block("a remote delete with an option after a path.")
            paths.append(w)
        if not paths:
            block("a remote delete with no path.")
    elif verb == "mv":
        args, options = [], True
        for w in rwords[1:]:
            tok = w.text
            if options and tok == "--" and not w.quoted:
                options = False
                continue
            if options and not args and re.fullmatch(r"-[fvin]+", tok):
                continue
            if options and tok.startswith("-"):
                block("a remote move with an option this guard cannot read.")
            if options and w.glob and tok and tok[0] in "*?[":
                block("a remote move whose leading wildcard could become a destination-changing option. Put -- before source arguments.")
            args.append(w)
        if len(args) < 2:
            block("a remote move this guard cannot read.")
        if args[-1].glob:
            block("a remote move whose destination the shell would expand. Give one literal destination so the guard can check whether it is the Trash.")
        if dynamic_tilde(args[-1]):
            block("a remote move whose special tilde destination the shell would choose. Give one literal destination.")
        dest = norm_path(args[-1].text) or args[-1].text
        if not (is_trash(dest) or has_trash_component(args[-1].text)):
            # A plain move that does not land in the Trash is not a delete.
            none()
        if not is_trash(dest):
            block("a remote move into the Trash this guard cannot read.")
        paths = args[:-1]
    elif verb in READ_ONLY:
        none()
    else:
        # Anything else (env, sudo, a NAME=value prefix, zsh noglob, busybox,
        # another ssh, an interpreter) passes only when nothing in it looks
        # like a delete. A delete wrapped this way is never approvable.
        if looks_destructive(remote):
            block("a remote delete run through " + verb + ", which no note can approve. Use rm, rmdir, unlink, trash, or mv into the Trash, one exact path each.")
        none()

    if risky:
        # Checked before ssh -G ever runs, so a -F config or Include with a
        # Match exec line never gets to run a command from inside the guard.
        block("a remote delete with ssh options that can change which machine it reaches or load other config (-F, -J, -W, -S, or -o Hostname, ProxyJump, ProxyCommand, ControlPath, Include, Match). A note is matched to the plain host alias only.")
    keys = []
    for w in paths:
        if w.glob:
            block("a remote delete with a wildcard the remote shell would expand. A note names one exact path.")
        if w.text.startswith("~") and w.first_quoted:
            block("a remote path with a quoted ~, which the remote shell would not expand. Write ~ unquoted or give the full path.")
        k = key(host, w.text, opts)
        if k is None:
            block("a remote path that is relative, uses .., or names a whole disk or home folder, or a login the guard could not read with ssh -G. Give the full path.")
        keys.append(k)
    raise Verdict("TARGETS", keys)


def split_unquoted(command):
    """Split the line at separators outside quotes (; | & ( ) and newlines).
    Returns (separators before the piece, piece) pairs. Text inside quotes,
    including bash -c "...", stays in one piece."""
    parts, cur, seps, quote, escaped = [], [], "", None, False
    for ch in command:
        if escaped:
            cur.append(ch)
            escaped = False
            continue
        if ch == "\\" and quote != "'":
            cur.append(ch)
            escaped = True
            continue
        if quote is None and ch in "'\"":
            quote = ch
        elif quote == ch:
            quote = None
        if quote is None and ch in ";|&()\n\r":
            piece = "".join(cur)
            if piece.strip():
                parts.append((seps, piece))
                seps = ""
            seps += ch
            cur = []
            continue
        cur.append(ch)
    piece = "".join(cur)
    if piece.strip():
        parts.append((seps, piece))
    return parts


def active_expansion(text):
    """True when $ or a backtick sits outside single quotes, so this Mac's
    shell would rewrite the words before ssh ever sees them."""
    quote = None
    escaped = False
    for ch in text:
        if escaped:
            escaped = False
            continue
        if ch == "\\" and quote != "'":
            escaped = True
            continue
        if ch == "'" and quote is None:
            quote = "'"
        elif ch == "'" and quote == "'":
            quote = None
        elif ch == '"' and quote is None:
            quote = '"'
        elif ch == '"' and quote == '"':
            quote = None
        elif ch in "$`" and quote != "'":
            return True
    return False


def unquoted_has(text, chars):
    quote, escaped = None, False
    for ch in text:
        if escaped:
            escaped = False
            continue
        if ch == "\\" and quote != "'":
            escaped = True
            continue
        if quote is None and ch in "'\"":
            quote = ch
        elif quote == ch:
            quote = None
        elif quote is None and ch in chars:
            return True
    return False


def judge_compound(command):
    """A line with more than one plain ssh command in it. Nothing here is
    approvable by a note. Each piece that runs ssh is judged on its own."""
    for seps, part in split_unquoted(command):
        if not SSH_WORD.search(plain(part)):
            continue
        if active_expansion(part):
            block("a delete check on ssh text that this Mac's shell would rewrite first ($ or a backtick). Write the remote command out in plain words.")
        part = re.sub(r"\d*<\s*/dev/null", " ", part)
        fed = "|" in seps or unquoted_has(part, "<")
        try:
            toks = shlex.split(part.replace("<", " < "))
        except ValueError:
            block("an ssh command this guard cannot read.")
        if not toks or os.path.basename(toks[0].lstrip("=")) not in ("ssh", "mosh"):
            # ssh wrapped in env, timeout, bash -c and the like.
            if looks_destructive(part) or fed:
                block("a delete sent over ssh inside a wrapped, piped or redirected command. Send the delete as its own plain ssh command so it can be checked.")
            continue
        toks = [t for t in toks if t != "<"]
        host, rest, risky, copts, opts = ssh_invocation(toks)
        check_command_opts(copts)
        remote = " ".join(rest)
        if fed:
            verb = first_word(remote) if rest else ""
            if verb not in READ_ONLY or looks_destructive(remote):
                block("ssh reading commands from a pipe or a file, which this guard cannot see. Send the delete as its own plain ssh command.")
            continue
        if not remote.strip():
            continue
        if host is None or norm_host(host) is None:
            if looks_destructive(remote):
                block("a delete sent over ssh to a host this guard cannot read.")
            continue
        try:
            remote_verdict(host, remote, risky, opts)
        except Verdict as v:
            if v.kind == "BLOCK":
                raise
            if v.kind == "TARGETS":
                block("a delete sent over ssh inside a compound or piped command. Send the delete as its own plain ssh command so a note can match it.")
    none()


def scan(command):
    p = plain(command)

    # rsync --delete or --remove-source-files toward a remote host removes
    # files there with no ssh word on the line.
    if re.search(r"(?:^|[\s;|&(`])" + BIN + r"rsync(?=\s)", p) \
            and re.search(r"--del|--remove-source-files", p) \
            and re.search(r"(?:^|\s)[A-Za-z0-9._@-]+:", p):
        block("rsync that removes files on or from a remote host, which no note can approve.")
    # sftp batch files and batch deletes.
    if re.search(r"(?:^|[\s;|&(`])" + BIN + r"sftp(?=\s)", p) and (looks_destructive(p) or re.search(r"\s-b\b", p)):
        block("an sftp delete or batch file, which no note can approve.")

    if not SSH_WORD.search(p):
        none()

    words = parse(command.lstrip(" \t"))
    if words is None or os.path.basename(words[0].text.lstrip("=")) != "ssh":
        judge_compound(command)

    tokens = [w.text for w in words]
    host, rest, risky, command_opts, opts = ssh_invocation(tokens)
    check_command_opts(command_opts)
    remote = " ".join(rest)
    if not remote.strip():
        none()
    if host is None or norm_host(host) is None:
        if looks_destructive(remote):
            block("a delete sent over ssh to a host this guard cannot read. Use the plain host alias, for example ssh ember.")
        none()
    remote_verdict(host, remote, risky, opts)


def run_scan(command):
    try:
        scan(command)
        none()
    except Verdict as v:
        if v.kind == "NONE":
            out("NONE")
        if v.kind == "BLOCK":
            out("BLOCK " + v.payload)
        out("TARGETS", *["KEY " + k for k in v.payload])


mode = sys.argv[1] if len(sys.argv) > 1 else ""
if mode == "normalize" and len(sys.argv) == 4:
    k = key(sys.argv[2], sys.argv[3])
    if k is None:
        sys.exit(1)
    sys.stdout.write(k)
    sys.exit(0)
if mode == "scan" and len(sys.argv) == 3:
    run_scan(sys.argv[2])
sys.exit(2)
PY
}

normalize_remote_key() { da_ssh_py normalize "$1" "$2"; }
ssh_delete_scan() { da_ssh_py scan "$1"; }

# -------------------------------------------------------------------------
# find_approval_note <normalized-target>
#
# Prints the path of ONE unexpired note file covering exactly this target,
# and returns 0. Returns 1 when no such note exists.
#
# Expired notes matching the target are logged as rejects and left on disk
# for the purge path -- an expired note must behave exactly like no note.
# -------------------------------------------------------------------------
find_approval_note() {
  local want="$1" now i
  now=$(now_epoch)
  [[ -d "$DELETION_APPROVAL_DIR" ]] || return 1
  [[ "${DA_IDX_READY:-0}" -eq 1 ]] || da_build_index || return 1

  for (( i = 0; i < ${#DA_IDX_TGTS[@]}; i++ )); do
    [[ "${DA_IDX_TGTS[$i]}" == "$want" ]] || continue
    if (( now < DA_IDX_EXPS[i] )); then
      printf '%s' "${DA_IDX_FILES[$i]}"
      return 0
    fi
    da_log "EXPIRED-REJECT" "note=${DA_IDX_FILES[$i]} target=$want expired_epoch=${DA_IDX_EXPS[$i]} now=$now -- treated as no note, delete stays blocked"
  done
  return 1
}

# -------------------------------------------------------------------------
# da_build_index
#
# Reads every note in ONE python3 pass into three parallel arrays
# (DA_IDX_FILES, DA_IDX_EXPS, DA_IDX_TGTS) so a delete with many targets costs
# one pass over the notes, not two jq processes per note per target. That
# quadratic cost is what pushed a 100-folder rm past the hook's 10 second
# timeout on 2026-10-25. Call it from the main shell, not inside $( ), so the
# arrays survive. An unreadable note is skipped (same as no note), and a note
# with a bad expiry loads as expired. Returns 1 when the index cannot be built,
# which every caller treats as "no approval" and the block stands.
# -------------------------------------------------------------------------
DA_IDX_READY=0
DA_IDX_FILES=()
DA_IDX_EXPS=()
DA_IDX_TGTS=()
da_build_index() {
  local f e t out
  DA_IDX_READY=0
  DA_IDX_FILES=()
  DA_IDX_EXPS=()
  DA_IDX_TGTS=()
  if [[ ! -d "$DELETION_APPROVAL_DIR" ]]; then
    DA_IDX_READY=1
    return 0
  fi
  out=$(python3 - "$DELETION_APPROVAL_DIR" <<'PY'
import glob, json, os, sys

for path in sorted(glob.glob(os.path.join(sys.argv[1], "*.json"))):
    try:
        with open(path) as fh:
            note = json.load(fh)
        target = note.get("target") or ""
        if not isinstance(target, str) or not target or "\x1f" in target or "\n" in target:
            continue
    except Exception:
        continue
    try:
        expires = int(note.get("expires_epoch", 0))
    except Exception:
        expires = -1
    sys.stdout.write("%s\x1f%d\x1f%s\n" % (path, expires, target))
PY
  ) || return 1
  while IFS=$'\037' read -r f e t; do
    [[ -n "$f" ]] || continue
    DA_IDX_FILES+=("$f")
    DA_IDX_EXPS+=("$e")
    DA_IDX_TGTS+=("$t")
  done <<< "$out"
  DA_IDX_READY=1
  return 0
}

# -------------------------------------------------------------------------
# claim_approval_notes <note-file>...
#
# Renames every matched note out of the index in one atomic step each, so two
# identical delete calls running at once can never both spend the same note.
# The rename that loses the race fails, every note this call already took is
# put back, and the caller blocks. On success DA_CLAIMED_NOTES holds the
# renamed files, ready for consume_approval_note.
# -------------------------------------------------------------------------
DA_CLAIMED_NOTES=()
claim_approval_notes() {
  local n claimed i seen=" "
  DA_CLAIMED_NOTES=()
  for n in "$@"; do
    # Two spellings of one target point at the same note. Claim it once.
    case "$seen" in *" $n "*) continue ;; esac
    seen="$seen$n "
    claimed="$n.claimed.$$"
    if mv "$n" "$claimed" 2>/dev/null && [[ -f "$claimed" ]]; then
      DA_CLAIMED_NOTES+=("$claimed")
    else
      for (( i = 0; i < ${#DA_CLAIMED_NOTES[@]}; i++ )); do
        mv "${DA_CLAIMED_NOTES[$i]}" "${DA_CLAIMED_NOTES[$i]%.claimed.*}" 2>/dev/null || true
      done
      DA_CLAIMED_NOTES=()
      da_log "CLAIM-LOST" "note=$(basename "$n") -- another call took it first, this delete stays blocked"
      return 1
    fi
  done
  [[ "${#DA_CLAIMED_NOTES[@]}" -gt 0 ]]
}

# -------------------------------------------------------------------------
# release_claimed_notes
#
# Puts back every note this run claimed but did not consume. The hook calls it
# on every exit, so a deadline, a signal or a crash between claim and consume
# never strands an approval as an invisible *.claimed file.
# -------------------------------------------------------------------------
release_claimed_notes() {
  local i c
  for (( i = 0; i < ${#DA_CLAIMED_NOTES[@]}; i++ )); do
    c="${DA_CLAIMED_NOTES[$i]}"
    [[ -f "$c" ]] && mv "$c" "${c%.claimed.*}" 2>/dev/null || true
  done
  DA_CLAIMED_NOTES=()
}

# -------------------------------------------------------------------------
# commit_claimed_notes <context>
#
# The allow step. Every log line is written first, while the notes are still
# claimed files the exit trap can put back, so a slow log or a deadline in that
# part blocks the delete and spends nothing. Then one rm removes every note and
# the claim list is cleared straight away. The watchdog stays armed throughout.
# Sets DA_SUMMARY to the note names.
# -------------------------------------------------------------------------
commit_claimed_notes() {
  local ctx="${1:-}" c body
  DA_SUMMARY=""
  for c in ${DA_CLAIMED_NOTES[@]+"${DA_CLAIMED_NOTES[@]}"}; do
    body=$(jq -c '.' "$c" 2>/dev/null || printf '<unreadable>')
    da_log "ALLOW" "context=$ctx note=$(basename "${c%.claimed.*}") contents=$body"
    da_log "CONSUMED" "note=$(basename "${c%.claimed.*}") -- single-use note removed"
    DA_SUMMARY="${DA_SUMMARY}$(basename "${c%.claimed.*}") "
  done
  rm -f ${DA_CLAIMED_NOTES[@]+"${DA_CLAIMED_NOTES[@]}"} 2>/dev/null || true
  DA_CLAIMED_NOTES=()
}

# -------------------------------------------------------------------------
# consume_approval_note <note-file> <context>
#
# Logs the full note contents, then deletes the note. Single-use by design:
# one grant authorizes exactly one delete.
# -------------------------------------------------------------------------
consume_approval_note() {
  local note="$1" ctx="${2:-}" body
  body=$(jq -c '.' "$note" 2>/dev/null || printf '<unreadable>')
  da_log "ALLOW" "context=$ctx note=$(basename "${note%.claimed.*}") contents=$body"
  rm -f "$note" 2>/dev/null || true
  da_log "CONSUMED" "note=$(basename "${note%.claimed.*}") -- single-use note removed"
}
