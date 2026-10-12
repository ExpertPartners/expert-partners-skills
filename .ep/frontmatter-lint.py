#!/usr/bin/env python3
"""
frontmatter-lint.py -- data-classification frontmatter validator (L6 Gatekeeper, F5).

Enforces the Expert Partners data-classification standard so brand content is born tagged
rather than retrofitted. Wired to the classification-schema.json shipped next to this
script (the canonical schema, ratified by ADR-0025).

Two layers of enforcement, by design non-breaking on the existing untagged estate:

  1. VALUE CHECK (everywhere): any markdown file that DECLARES a `classification:` key in its
     YAML frontmatter must use one of the allowed values. Catches typos like "internel" or
     "confedential" repo-wide, with zero risk to untagged files.

  2. PRESENCE CHECK (scoped): files whose path matches schema.required_in_paths MUST carry a
     valid classification tag. This list is empty today (so no existing commit breaks); L5
     populates it per brand repo as tagged content lands, at which point missing tags fail.

Frontmatter parsing:
  Uses PyYAML when available; otherwise falls back to a minimal scanner that reads top-level
  `key: value` pairs from the leading `--- ... ---` block. The fallback is sufficient for the
  flat frontmatter this gate cares about and keeps the hook dependency-free in CI.

Escape hatch:
  Put `frontmatter-lint: ignore-file` anywhere in a file to skip it entirely.

Usage (the kit directory is tools/ in aura, .ep/ in deployed repos):
  python3 .ep/frontmatter-lint.py [FILE ...]   # validate named files (pre-commit passes these)
  python3 .ep/frontmatter-lint.py              # validate all git-tracked markdown
  python3 .ep/frontmatter-lint.py --schema P   # use an alternate schema path

Exit code: 0 = clean, 1 = at least one violation, 2 = bad invocation / unreadable schema.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml  # type: ignore
    _HAVE_YAML = True
except ImportError:  # pragma: no cover - depends on environment
    _HAVE_YAML = False

IGNORE_FILE_TOKEN = "frontmatter-lint: ignore-file"
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}
# The schema ships beside this script (tools/ in aura, .ep/ in deployed repos), so the
# default resolves script-adjacent; --schema still overrides (deployed CI passes it
# explicitly). A repo-relative tools/ default previously broke bare runs in deployed repos.
DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent / "classification-schema.json"


@dataclass
class Finding:
    path: str
    message: str


def find_repo_root(start: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return start


def git_tracked_markdown(repo_root: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=repo_root, capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    files = []
    for rel in out.split("\0"):
        if rel and (repo_root / rel).suffix.lower() in MARKDOWN_SUFFIXES:
            files.append(repo_root / rel)
    return files


def extract_frontmatter(text: str) -> str | None:
    """Return the raw YAML frontmatter block, or None if the file has no leading block."""
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    # First line must be exactly the opening fence.
    if lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return "\n".join(lines[1:i])
    return None  # unterminated frontmatter -> treat as none


def parse_frontmatter(block: str) -> dict:
    if _HAVE_YAML:
        try:
            data = yaml.safe_load(block)
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError:
            return {}
    # Minimal fallback: top-level `key: value` pairs only.
    out: dict = {}
    for line in block.splitlines():
        if not line or line[0] in " \t#-":  # skip nested/comment/list lines
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def path_matches(rel_path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, g) for g in globs)


def validate_file(path: Path, repo_root: Path, schema: dict) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    if IGNORE_FILE_TOKEN in text:
        return []

    try:
        rel = str(path.relative_to(repo_root)) if path.is_absolute() else str(path)
    except ValueError:
        rel = str(path)  # path is outside the repo root (e.g. ad-hoc invocation)
    key = schema["frontmatter_key"]
    allowed = set(schema["allowed_values"])
    required_in = schema.get("required_in_paths", [])
    exempt = schema.get("exempt_paths", [])

    is_exempt = path_matches(rel, exempt)
    is_required = (not is_exempt) and path_matches(rel, required_in)

    block = extract_frontmatter(text)
    findings: list[Finding] = []

    if block is None:
        if is_required:
            findings.append(Finding(rel, f"missing YAML frontmatter; '{key}' is required here"))
        return findings

    fm = parse_frontmatter(block)

    if key not in fm:
        if is_required:
            findings.append(Finding(rel, f"frontmatter missing required '{key}' key"))
        return findings  # value check only applies when the key is present

    value = fm[key]
    if value not in allowed:
        findings.append(
            Finding(rel, f"'{key}: {value}' is not a valid class; allowed: {sorted(allowed)}")
        )
    return findings


def load_schema(override: str | None) -> dict:
    schema_path = Path(override) if override else DEFAULT_SCHEMA_PATH
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"frontmatter-lint: cannot read schema {schema_path}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    for required_key in ("frontmatter_key", "allowed_values"):
        if required_key not in schema:
            print(f"frontmatter-lint: schema missing '{required_key}'", file=sys.stderr)
            raise SystemExit(2)
    return schema


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Data-classification frontmatter validator.")
    parser.add_argument("files", nargs="*", help="files to validate (default: all tracked markdown)")
    parser.add_argument("--schema", help="path to an alternate classification schema JSON")
    args = parser.parse_args(argv)

    repo_root = find_repo_root(Path.cwd())
    schema = load_schema(args.schema)

    if args.files:
        targets = [Path(f) for f in args.files if Path(f).suffix.lower() in MARKDOWN_SUFFIXES]
    else:
        targets = git_tracked_markdown(repo_root)

    findings: list[Finding] = []
    for path in targets:
        if path.exists():
            findings.extend(validate_file(path, repo_root, schema))

    for f in findings:
        print(f"ERROR {f.path}: {f.message}")

    if schema.get("status", "").startswith("provisional"):
        print(f"frontmatter-lint: schema status = {schema['status']}", file=sys.stderr)

    if findings:
        print(f"\nfrontmatter-lint: {len(findings)} violation(s).")
        return 1
    print("frontmatter-lint: clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
