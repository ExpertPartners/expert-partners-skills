#!/usr/bin/env python3
"""Validate the expert-partners plugin marketplace against its plugin packages.

Checks (all errors unless noted):
  1. .claude-plugin/marketplace.json parses and every entry has name, source,
     version, and description.
  2. Every entry's source directory exists and holds .claude-plugin/plugin.json.
  3. plugin.json name and version equal the marketplace entry (the two-file
     bump rule in the code-block-routing skill), and the version is semver.
  4. No plugin directory under plugins/ is missing from the marketplace.
  5. Every plugin ships at least one skills/<name>/SKILL.md; each SKILL.md has
     frontmatter whose name equals its folder and whose description is
     non-empty and under the 1024-character cap.
  6. Warning only: a plugin package has no README.md capability record.

Standard library only, so it runs anywhere the repo's other lints run.

Usage:
  python3 tools/plugin-validate/validate_plugins.py [--repo PATH] [--strict]

  --strict turns warnings into errors.
Exit code: 0 clean, 1 at least one error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
DESCRIPTION_CAP = 1024


def read_frontmatter(text: str) -> dict[str, str] | None:
    """Return top-level name/description from a SKILL.md frontmatter block.

    Handles plain, quoted, and folded (>-, >, |) scalars, which are the forms
    used in this repo. Returns None when there is no frontmatter block.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None
    block = lines[1:end]
    out: dict[str, str] = {}
    i = 0
    while i < len(block):
        line = block[i]
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest in (">-", ">", "|", "|-", ">+", "|+"):
            parts = []
            i += 1
            while i < len(block) and (block[i].startswith(" ") or not block[i].strip()):
                parts.append(block[i].strip())
                i += 1
            joiner = "\n" if rest.startswith("|") else " "
            out[key] = joiner.join(p for p in parts if p).strip()
            continue
        if len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in "\"'":
            inner = rest[1:-1]
            if rest[0] == '"':
                inner = inner.replace('\\"', '"').replace("\\\\", "\\")
            else:
                inner = inner.replace("''", "'")
            rest = inner
        out[key] = rest
        i += 1
    return out


def validate(repo: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    mp_path = repo / ".claude-plugin" / "marketplace.json"
    try:
        marketplace = json.loads(mp_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{mp_path}: missing"], warnings
    except json.JSONDecodeError as exc:
        return [f"{mp_path}: invalid JSON ({exc})"], warnings

    entries = marketplace.get("plugins")
    if not isinstance(entries, list) or not entries:
        return [f"{mp_path}: 'plugins' must be a non-empty list"], warnings

    seen_names: set[str] = set()
    listed_dirs: set[Path] = set()
    for idx, entry in enumerate(entries):
        where = f"marketplace.json plugins[{idx}]"
        for field in ("name", "source", "version", "description"):
            if not entry.get(field):
                errors.append(f"{where}: missing '{field}'")
        name = entry.get("name", "")
        if name in seen_names:
            errors.append(f"{where}: duplicate plugin name '{name}'")
        seen_names.add(name)
        if name and not NAME_RE.match(name):
            errors.append(f"{where}: name '{name}' is not kebab-case")
        version = entry.get("version", "")
        if version and not SEMVER_RE.match(version):
            errors.append(f"{where}: version '{version}' is not semver")
        source = entry.get("source", "")
        if not source:
            continue
        src_dir = (repo / source).resolve()
        listed_dirs.add(src_dir)
        if not src_dir.is_dir():
            errors.append(f"{where}: source '{source}' does not exist")
            continue
        pj_path = src_dir / ".claude-plugin" / "plugin.json"
        try:
            pj = json.loads(pj_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            errors.append(f"{name}: {pj_path.relative_to(repo)} missing")
            continue
        except json.JSONDecodeError as exc:
            errors.append(f"{name}: {pj_path.relative_to(repo)} invalid JSON ({exc})")
            continue
        if pj.get("name") != name:
            errors.append(f"{name}: plugin.json name '{pj.get('name')}' != marketplace name '{name}'")
        if pj.get("version") != version:
            errors.append(
                f"{name}: plugin.json version '{pj.get('version')}' != marketplace version '{version}' "
                "(bump both files together)"
            )
        if not pj.get("description"):
            errors.append(f"{name}: plugin.json missing description")
        if not pj.get("author"):
            warnings.append(f"{name}: plugin.json has no author")

        skills_dir = src_dir / "skills"
        skill_files = sorted(skills_dir.glob("*/SKILL.md")) if skills_dir.is_dir() else []
        if not skill_files:
            errors.append(f"{name}: no skills/<name>/SKILL.md found")
        for sf in skill_files:
            rel = sf.relative_to(repo)
            fm = read_frontmatter(sf.read_text(encoding="utf-8"))
            if fm is None:
                errors.append(f"{rel}: no frontmatter")
                continue
            folder = sf.parent.name
            if fm.get("name") != folder:
                errors.append(f"{rel}: frontmatter name '{fm.get('name')}' != folder '{folder}'")
            desc = fm.get("description", "")
            if not desc:
                errors.append(f"{rel}: empty description")
            elif len(desc) >= DESCRIPTION_CAP:
                errors.append(f"{rel}: description {len(desc)} chars (cap {DESCRIPTION_CAP}, fail at or over)")
        if not (src_dir / "README.md").is_file():
            warnings.append(f"{name}: no README.md capability record in {src_dir.relative_to(repo)}")

    plugins_root = repo / "plugins"
    if plugins_root.is_dir():
        for d in sorted(p for p in plugins_root.iterdir() if p.is_dir()):
            if d.resolve() not in listed_dirs:
                errors.append(f"plugins/{d.name}: directory not listed in marketplace.json")
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args(argv)
    errors, warnings = validate(Path(args.repo).resolve())
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    failed = bool(errors) or (args.strict and bool(warnings))
    status = "FAIL" if failed else "clean"
    print(f"plugin-validate: {status}. {len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
