#!/usr/bin/env python3
"""
skill-description-lint.py -- Agent Skills description cap gate (L6 Gatekeeper, F6).

Every SKILL.md frontmatter `description` is loaded into the system prompt at startup, and
Anthropic caps it. The claude.ai org Skills uploader rejects an over-cap skill with:

    field 'description' in SKILL.md must be at most 1024 characters

Before this gate existed, that rejection was discovered by hand, one upload at a time, weeks
after the description was written. This gate moves the failure to commit time, where the
author who wrote the sentence is still holding it.

Ruled by Allison 2026-08-07: hard fail at 1024, no warn band. Reasoning on the record -- six
skills already sat within 100 characters of the cap, so a warn band would fire against
existing files from day one and train everyone to ignore it. The headroom table below is the
substitute: it ALWAYS prints, so near-cap skills stay visible without being an alarm.

Vendor limit, verified live 2026-08-07 against
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
("`description`: Must be non-empty, Maximum 1,024 characters, Cannot contain XML tags").
Note the vendor wording is "at most 1024", which permits exactly 1024. Allison's ruling is
"at or over 1024 fails", one character stricter on purpose. CAP_INCLUSIVE records that.

What it checks:
  ERROR (fails the commit):
    - description length >= 1024 characters
    - description silently truncated by YAML: an UNQUOTED description containing " #" ends
      at that point, because " #" opens a comment in a plain scalar. The file then says more
      than the uploader and Claude ever read, with no error anywhere. Found live on
      2026-08-07 in ep-brand, whose 859-character description was being delivered as 371
      characters ending mid-word at "(Black". This failure is strictly worse than an over-cap
      one, which at least fails loudly at upload time, so it is gated the same way.
  Reported in the table, never fatal:
    - every skill's headroom, sorted ascending, so the next one to breach is always on screen

Scope:
  Sweeps EVERY git-tracked SKILL.md in the repo on every run, regardless of which files were
  passed as arguments. A breach anywhere fails, and the table always shows the whole estate.
  Passing file arguments (as pre-commit does) does not narrow the sweep; it only signals that
  a SKILL.md was touched.

Frontmatter parsing:
  Uses PyYAML when available. Otherwise falls back to a self-contained scalar reader that
  handles the four YAML forms this estate actually uses for `description`: plain, double
  quoted, single quoted, and block (| and > with any chomping indicator). The fallback is
  verified to agree with PyYAML character-for-character via --selftest.

Escape hatch:
  Put `skill-description-lint: ignore-file` anywhere in a SKILL.md to skip it entirely.
  Use this only for a skill that is deliberately not uploadable.

Usage:
  python3 .ep/skill-description-lint.py [FILE ...]   # sweep repo, table + gate
  python3 .ep/skill-description-lint.py --quiet      # table only on failure
  python3 .ep/skill-description-lint.py --selftest   # prove fallback == PyYAML, then sweep

Exit code: 0 = no breach, 1 = at least one description at or over the cap, 2 = bad invocation.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml  # type: ignore
    _HAVE_YAML = True
except ImportError:  # pragma: no cover - depends on environment
    _HAVE_YAML = False

# Allison's ruling 2026-08-07: fail AT the cap, not just over it. The vendor allows exactly
# 1024; we do not, so a description can never sit one keystroke from rejection.
CAP_INCLUSIVE = 1024

IGNORE_FILE_TOKEN = "skill-description-lint: ignore-file"
SKILL_FILENAME = "SKILL.md"


@dataclass
class Row:
    rel: str
    name: str
    length: int          # -1 when the description is missing or unparseable
    note: str = ""
    truncated_from: int = 0   # authored length when YAML silently ate part of it, else 0

    @property
    def headroom(self) -> int:
        return CAP_INCLUSIVE - self.length

    @property
    def over_cap(self) -> bool:
        return self.length >= CAP_INCLUSIVE

    @property
    def truncated(self) -> bool:
        return self.truncated_from > 0

    @property
    def breached(self) -> bool:
        return self.over_cap or self.truncated


# ---------------------------------------------------------------------------
# Frontmatter reading
# ---------------------------------------------------------------------------

def frontmatter_lines(text: str) -> list[str] | None:
    """Return the frontmatter block's lines, or None when the file has no leading block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return lines[1:i]
    return None  # unterminated frontmatter


def _dedent_block(raw: list[str]) -> tuple[list[str], int]:
    """Strip the common indent from a block scalar's lines. Blank lines stay blank."""
    indents = [len(ln) - len(ln.lstrip(" ")) for ln in raw if ln.strip()]
    indent = min(indents) if indents else 0
    return [ln[indent:] if ln.strip() else "" for ln in raw], indent


def _read_block_scalar(header: str, body: list[str]) -> str:
    """Decode a `|` or `>` block scalar. header is the text after the colon."""
    style = header[0]                       # '|' or '>'
    chomp = ""
    for ch in header[1:]:
        if ch in "+-":
            chomp = ch
    lines, _ = _dedent_block(body)

    if style == "|":
        out = "\n".join(lines)
    else:
        # Folded: a single newline between two non-empty lines becomes a space; runs of
        # blank lines become that many newlines minus one.
        parts: list[str] = []
        for ln in lines:
            if not ln:
                parts.append("\n")
            elif parts and parts[-1] not in ("\n",) and not parts[-1].endswith("\n"):
                parts.append(" " + ln)
            else:
                parts.append(ln)
        out = "".join(parts)

    out = out.rstrip("\n")
    if chomp == "-":
        return out
    if chomp == "+":
        trailing = len(body) - len("\n".join(body).rstrip("\n").splitlines() or [""])
        return out + "\n" * max(trailing, 1)
    return out + "\n"  # clip: exactly one trailing newline


def _decode_double_quoted(s: str) -> str:
    """Decode the YAML double-quoted escapes this estate can realistically produce."""
    simple = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/", "0": "\0"}
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in simple:
                out.append(simple[nxt]); i += 2; continue
            if nxt in "uUx":
                width = {"x": 2, "u": 4, "U": 8}[nxt]
                hexpart = s[i + 2:i + 2 + width]
                if len(hexpart) == width:
                    try:
                        out.append(chr(int(hexpart, 16))); i += 2 + width; continue
                    except ValueError:
                        pass
            out.append(nxt); i += 2; continue
        out.append(c); i += 1
    return "".join(out)


def description_fallback(fm: list[str]) -> str | None:
    """Read the `description` scalar without PyYAML. Returns None when absent."""
    start = None
    for i, ln in enumerate(fm):
        if ln.startswith("description:"):
            start = i
            break
    if start is None:
        return None

    header = fm[start][len("description:"):].strip()

    # Block scalar: | or > with optional chomping/indent indicators.
    if header[:1] in ("|", ">"):
        body: list[str] = []
        for ln in fm[start + 1:]:
            if ln.strip() and not ln.startswith((" ", "\t")):
                break
            body.append(ln)
        while body and not body[-1].strip():
            body.pop()
        return _read_block_scalar(header, body)

    # Collect continuation lines (indented, and not a new top-level key or comment).
    chunk = [header]
    for ln in fm[start + 1:]:
        if not ln.strip():
            break
        if not ln.startswith((" ", "\t")):
            break
        chunk.append(ln.strip())

    if header.startswith('"'):
        joined = " ".join(chunk)
        # Find the closing quote, honouring backslash escapes.
        i, esc = 1, False
        while i < len(joined):
            if esc:
                esc = False
            elif joined[i] == "\\":
                esc = True
            elif joined[i] == '"':
                break
            i += 1
        return _decode_double_quoted(joined[1:i])

    if header.startswith("'"):
        joined = " ".join(chunk)
        i = 1
        while i < len(joined):
            if joined[i] == "'":
                if i + 1 < len(joined) and joined[i + 1] == "'":
                    i += 2; continue
                break
            i += 1
        return joined[1:i].replace("''", "'")

    # Plain scalar. YAML ends a plain scalar at " #", which opens a comment. Honour that,
    # so this fallback reports exactly what a real YAML parser (and the uploader) will read.
    return _strip_plain_comment(" ".join(chunk))


def _strip_plain_comment(s: str) -> str:
    """Cut a plain scalar at the first ' #', matching YAML comment semantics."""
    idx = s.find(" #")
    return s[:idx].rstrip() if idx != -1 else s


def authored_length(fm: list[str]) -> int | None:
    """
    Characters the author actually typed for an UNQUOTED description, ignoring YAML's
    comment rule. Returns None unless the scalar is plain (no quotes, no block indicator),
    which is the only style where a bare ' #' can silently eat content.
    """
    start = None
    for i, ln in enumerate(fm):
        if ln.startswith("description:"):
            start = i
            break
    if start is None:
        return None
    header = fm[start][len("description:"):].strip()
    if not header or header[:1] in ('"', "'", "|", ">", "&", "*"):
        return None
    chunk = [header]
    for ln in fm[start + 1:]:
        if not ln.strip() or not ln.startswith((" ", "\t")):
            break
        chunk.append(ln.strip())
    return len(" ".join(chunk))


def read_description(text: str) -> tuple[str | None, str | None, str]:
    """Return (description, name, note). description is None when absent/unparseable."""
    fm = frontmatter_lines(text)
    if fm is None:
        return None, None, "no frontmatter"

    if _HAVE_YAML:
        try:
            data = yaml.safe_load("\n".join(fm))
        except yaml.YAMLError as exc:
            return None, None, f"YAML error ({exc.__class__.__name__})"
        if not isinstance(data, dict):
            return None, None, "frontmatter is not a mapping"
        desc, name = data.get("description"), data.get("name")
        if desc is None:
            return None, (name if isinstance(name, str) else None), "no description key"
        if not isinstance(desc, str):
            return None, (name if isinstance(name, str) else None), "description is not a string"
        return desc, (name if isinstance(name, str) else None), ""

    desc = description_fallback(fm)
    name = None
    for ln in fm:
        if ln.startswith("name:"):
            name = ln[len("name:"):].strip().strip('"').strip("'")
            break
    if desc is None:
        return None, name, "no description key"
    return desc, name, ""


# ---------------------------------------------------------------------------
# Repo walk
# ---------------------------------------------------------------------------

def find_repo_root(start: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return start


def git_tracked_skills(repo_root: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=repo_root, capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return sorted(
        repo_root / rel
        for rel in out.split("\0")
        if rel and Path(rel).name == SKILL_FILENAME
    )


def collect(repo_root: Path) -> list[Row]:
    rows: list[Row] = []
    for path in git_tracked_skills(repo_root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if IGNORE_FILE_TOKEN in text:
            continue
        rel = str(path.relative_to(repo_root))
        desc, name, note = read_description(text)
        length = len(desc) if desc is not None else -1

        # Did YAML silently eat part of an unquoted description?
        truncated_from = 0
        fm = frontmatter_lines(text)
        if fm is not None and desc is not None:
            authored = authored_length(fm)
            if authored is not None and authored > length:
                truncated_from = authored

        rows.append(Row(rel, name or "?", length, note, truncated_from))
    # Ascending headroom == descending length. Unparseable rows (-1) sink to the bottom.
    rows.sort(key=lambda r: (-r.length, r.rel))
    return rows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_table(rows: list[Row]) -> None:
    if not rows:
        print("skill-description-lint: no SKILL.md files tracked.")
        return
    wname = max((len(r.name) for r in rows), default=4)
    print(f"skill-description-lint: description headroom (cap {CAP_INCLUSIVE}, "
          f"fail at or over). {len(rows)} skills, nearest the cap first.")
    print(f"  {'chars':>5}  {'left':>5}  {'skill'.ljust(wname)}  path")
    for r in rows:
        if r.length < 0:
            print(f"  {'--':>5}  {'--':>5}  {r.name.ljust(wname)}  {r.rel}   [{r.note}]")
            continue
        mark = ""
        if r.over_cap:
            mark = "  <== OVER CAP"
        elif r.truncated:
            mark = f"  <== TRUNCATED, author wrote {r.truncated_from}"
        print(f"  {r.length:>5}  {r.headroom:>5}  {r.name.ljust(wname)}  {r.rel}{mark}")


def selftest(repo_root: Path) -> int:
    """Prove the no-PyYAML fallback agrees with PyYAML on every real file in the repo."""
    if not _HAVE_YAML:
        print("skill-description-lint: --selftest needs PyYAML installed.", file=sys.stderr)
        return 2
    bad = 0
    checked = 0
    for path in git_tracked_skills(repo_root):
        text = path.read_text(encoding="utf-8")
        if IGNORE_FILE_TOKEN in text:
            continue
        fm = frontmatter_lines(text)
        if fm is None:
            continue
        try:
            data = yaml.safe_load("\n".join(fm))
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict) or not isinstance(data.get("description"), str):
            continue
        want = data["description"]
        got = description_fallback(fm)
        checked += 1
        if got != want:
            bad += 1
            print(f"  MISMATCH {path.relative_to(repo_root)}: "
                  f"pyyaml {len(want)} vs fallback {len(got) if got is not None else 'None'}")
    print(f"skill-description-lint: fallback selftest {checked - bad}/{checked} exact.")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Agent Skills description cap gate (fails at or over 1024 characters)."
    )
    parser.add_argument("files", nargs="*",
                        help="ignored for scope; the sweep is always repo-wide")
    parser.add_argument("--quiet", action="store_true",
                        help="print the headroom table only when something breaches")
    parser.add_argument("--selftest", action="store_true",
                        help="verify the no-PyYAML fallback against PyYAML, then sweep")
    args = parser.parse_args(argv)

    repo_root = find_repo_root(Path.cwd())

    if args.selftest:
        rc = selftest(repo_root)
        if rc:
            return rc

    rows = collect(repo_root)
    breaches = [r for r in rows if r.breached]

    if not args.quiet or breaches:
        print_table(rows)

    if breaches:
        print()
        for r in breaches:
            if r.over_cap:
                print(f"skill-description-lint: ERROR {r.rel}: description is {r.length} "
                      f"characters, cap is {CAP_INCLUSIVE}. Trim "
                      f"{r.length - CAP_INCLUSIVE + 1} or more. The claude.ai org Skills "
                      f"upload rejects this file as written.")
            else:
                print(f"skill-description-lint: ERROR {r.rel}: description is silently "
                      f"truncated. The author wrote {r.truncated_from} characters but YAML "
                      f"delivers {r.length}, because an unquoted plain scalar ends at the "
                      f"first ' #'. Wrap the description in double quotes to restore it.")
        print(f"\nskill-description-lint: {len(breaches)} breach(es), "
              f"{len(rows)} skills checked.")
        return 1

    print(f"\nskill-description-lint: clean. {len(rows)} skills, "
          f"tightest headroom {min((r.headroom for r in rows if r.length >= 0), default=0)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
