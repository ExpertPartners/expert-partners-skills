#!/usr/bin/env python3
"""
brand-lint.py -- Expert Partners brand-naming and formatting linter (L6 Gatekeeper, F2 + F4).

Enforces the non-negotiable brand spelling, naming, and formatting standards from the
organization operating standard and the Aura CLAUDE.md, so violations are caught at
commit time and in CI rather than after publish.

What it checks (high-precision, word-boundary anchored):
  ERROR rules (fail the commit):
    - eXp casing:        EXP / Exp  ->  eXp
    - Allison spelling:  Alison / Allyson  ->  Allison
    - Melony spelling:   Melanie  ->  Melony
    - Em dashes:         U+2014 / U+2015 outside code fences/inline code  ->  comma, semicolon,
                         colon, parentheses, or double hyphen
  WARN rules (reported, do not fail unless --strict):
    - eXcelerate:        accelerate (and inflections)  ->  consider eXcelerate (brand program)
    - Don spelling:      Dawn  ->  Don (when the Expert Partners co-founder is meant)

Code awareness:
  Fenced code blocks (``` ... ``` and ~~~ ... ~~~) and inline code (`...`) are masked before
  the em-dash and prose rules run, so code samples and forensic log quotes are not flagged.

Escape hatches (for legitimate exceptions -- quotes, tickers, third-party names):
  - Whole-file skip:  put `brand-lint: ignore-file` anywhere in the file.
  - Single-line skip:  put `brand-lint: ignore` on the offending line (e.g. in an HTML comment).
  - Allowlist file:    tools/brand-lint-allow.txt -- one Python regex per line; any match is skipped.

Usage:
  python3 tools/brand-lint.py [FILE ...]        # lint the named files (pre-commit passes these)
  python3 tools/brand-lint.py                   # lint all git-tracked text files
  python3 tools/brand-lint.py --strict ...      # treat WARN as failure too
  python3 tools/brand-lint.py --rules           # print the active ruleset and exit

Exit code: 0 = clean, 1 = at least one ERROR (or any finding under --strict), 2 = bad invocation.

Verified against the org operating standard and Aura CLAUDE.md brand section, 2026-06-02.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Rule model
# ---------------------------------------------------------------------------

ERROR = "error"
WARN = "warn"


@dataclass(frozen=True)
class Rule:
    rule_id: str
    pattern: re.Pattern
    severity: str
    message: str
    suggestion: str


# Em-dash family: U+2014 EM DASH, U+2015 HORIZONTAL BAR. Both read as em dashes in prose.
EM_DASH_RE = re.compile("[—―]")

RULES: list[Rule] = [
    Rule(
        "exp-casing",
        re.compile(r"\b(EXP|Exp)\b"),
        ERROR,
        "Brand name must be 'eXp' (lowercase e, uppercase XP).",
        "eXp",
    ),
    Rule(
        "allison-spelling",
        re.compile(r"\b(Alison|Allyson|Allyson)\b"),
        ERROR,
        "Name must be spelled 'Allison' (two L's).",
        "Allison",
    ),
    Rule(
        "melony-spelling",
        re.compile(r"\bMelanie\b"),
        ERROR,
        "Name must be spelled 'Melony', never 'Melanie'.",
        "Melony",
    ),
    Rule(
        "em-dash",
        EM_DASH_RE,
        ERROR,
        "Em dashes are forbidden in copy.",
        "use a comma, semicolon, colon, parentheses, or double hyphen (--)",
    ),
    Rule(
        "excelerate-spelling",
        re.compile(r"\baccelerat(e|es|ed|ing|ion|or|ors)\b", re.IGNORECASE),
        WARN,
        "If this refers to the eXcelerate program, the brand spelling is 'eXcelerate'.",
        "eXcelerate",
    ),
    Rule(
        "don-spelling",
        re.compile(r"\bDawn\b"),
        WARN,
        "If this refers to Don Hobbs, the name is 'Don' (D-O-N), never 'Dawn'.",
        "Don",
    ),
]

# File extensions we lint. Keep to human-authored text; never lint binaries or lockfiles.
TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".mdx", ".rst"}

IGNORE_FILE_TOKEN = "brand-lint: ignore-file"
IGNORE_LINE_TOKEN = "brand-lint: ignore"


# ---------------------------------------------------------------------------
# Code masking
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"^(\s*)(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")


def mask_codeblocks(lines: list[str]) -> list[str]:
    """Return a copy of `lines` with fenced-code and inline-code spans blanked to spaces.

    Blanking (rather than deleting) preserves line numbers and columns so findings still
    point at the right place in the original file.
    """
    out: list[str] = []
    in_fence = False
    fence_marker = ""
    for line in lines:
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(2)
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            out.append(" " * len(line))
            continue
        if in_fence:
            out.append(" " * len(line))
            continue
        # Mask inline code spans on prose lines.
        out.append(INLINE_CODE_RE.sub(lambda mm: " " * len(mm.group(0)), line))
    return out


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------

def load_allowlist(repo_root: Path) -> list[re.Pattern]:
    allow_path = repo_root / "tools" / "brand-lint-allow.txt"
    patterns: list[re.Pattern] = []
    if not allow_path.exists():
        return patterns
    for raw in allow_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            patterns.append(re.compile(line))
        except re.error as exc:
            print(f"brand-lint: bad allowlist regex {line!r}: {exc}", file=sys.stderr)
    return patterns


def allowed(span_text: str, allowlist: list[re.Pattern]) -> bool:
    return any(p.search(span_text) for p in allowlist)


# ---------------------------------------------------------------------------
# Linting
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    path: str
    line_no: int
    col: int
    rule_id: str
    severity: str
    message: str
    suggestion: str
    excerpt: str


def lint_file(path: Path, allowlist: list[re.Pattern]) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []  # binary or unreadable -> skip silently

    if IGNORE_FILE_TOKEN in text:
        return []

    raw_lines = text.splitlines()
    masked_lines = mask_codeblocks(raw_lines)
    findings: list[Finding] = []

    for idx, (raw_line, masked_line) in enumerate(zip(raw_lines, masked_lines), start=1):
        if IGNORE_LINE_TOKEN in raw_line:
            continue
        for rule in RULES:
            # All brand rules run against code-masked text: brand naming and formatting
            # standards govern prose/copy, not code samples, config, or identifiers inside
            # fenced or inline code. This keeps the gate from failing on legitimate examples.
            target = masked_line
            for m in rule.pattern.finditer(target):
                span = m.group(0)
                if allowed(span, allowlist):
                    continue
                findings.append(
                    Finding(
                        path=str(path),
                        line_no=idx,
                        col=m.start() + 1,
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=rule.message,
                        suggestion=rule.suggestion,
                        excerpt=raw_line.strip()[:120],
                    )
                )
    return findings


def git_tracked_text_files(repo_root: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    files = []
    for rel in out.split("\0"):
        if not rel:
            continue
        p = repo_root / rel
        if p.suffix.lower() in TEXT_SUFFIXES:
            files.append(p)
    return files


def find_repo_root(start: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return start


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_rules() -> None:
    width = max(len(r.rule_id) for r in RULES)
    for r in RULES:
        print(f"{r.severity.upper():5}  {r.rule_id.ljust(width)}  {r.message}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Expert Partners brand-naming linter.")
    parser.add_argument("files", nargs="*", help="files to lint (default: all tracked text files)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--rules", action="store_true", help="print active rules and exit")
    args = parser.parse_args(argv)

    if args.rules:
        print_rules()
        return 0

    repo_root = find_repo_root(Path.cwd())
    allowlist = load_allowlist(repo_root)

    if args.files:
        targets = [Path(f) for f in args.files if Path(f).suffix.lower() in TEXT_SUFFIXES]
    else:
        targets = git_tracked_text_files(repo_root)

    all_findings: list[Finding] = []
    for path in targets:
        if path.exists():
            all_findings.extend(lint_file(path, allowlist))

    errors = [f for f in all_findings if f.severity == ERROR]
    warns = [f for f in all_findings if f.severity == WARN]

    for f in all_findings:
        tag = "ERROR" if f.severity == ERROR else "warn "
        print(f"{tag} {f.path}:{f.line_no}:{f.col}  [{f.rule_id}] {f.message}")
        print(f"      -> {f.suggestion}")
        print(f"      | {f.excerpt}")

    if all_findings:
        print(f"\nbrand-lint: {len(errors)} error(s), {len(warns)} warning(s).")
    else:
        print("brand-lint: clean.")

    if errors:
        return 1
    if warns and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
