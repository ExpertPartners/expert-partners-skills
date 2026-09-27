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

Standard library only. When PyYAML is installed (CI installs it for the
other lints) it reads frontmatter; otherwise a tested fallback parser does,
mirroring .ep/skill-description-lint.py. Description length is the parsed
YAML value's length, as that lint measures it.

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

# SemVer 2.0.0, the regex published at semver.org, with [0-9] for \d so only
# ASCII digits count. No leading zeros in major, minor, patch, or numeric
# prerelease identifiers; prerelease and build are non-empty dot-separated
# identifiers of [0-9A-Za-z-].
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-((?:0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?\Z"
)
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
DESCRIPTION_CAP = 1024
KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(?:[ \t]+(.*)|)$")
BLOCK_HEADER_RE = re.compile(r"^([|>])([+-]?)([1-9]?)([+-]?)[ \t]*(?:#.*)?$")

try:  # Same optional-dependency pattern as .ep/skill-description-lint.py.
    import yaml  # type: ignore

    _HAVE_YAML = True
except ImportError:  # pragma: no cover - depends on the environment
    yaml = None
    _HAVE_YAML = False


def is_semver(version: str) -> bool:
    """True when version is a valid SemVer 2.0.0 string."""
    return isinstance(version, str) and SEMVER_RE.match(version) is not None


def frontmatter_lines(text: str) -> list[str] | None:
    """Lines between the opening and closing '---' of a SKILL.md, or None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i]
    return None


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _comment_start(s: str) -> int:
    """Index of a YAML comment in a plain scalar line: '#' at the start of the
    text or preceded by whitespace. -1 when there is none. 'a#b' has none."""
    for i, ch in enumerate(s):
        if ch == "#" and (i == 0 or s[i - 1] in " \t"):
            return i
    return -1


def _fold(lines: list[str]) -> str:
    """Flow folding for plain multi-line scalars: each line is trimmed, a
    single line break becomes one space, and each blank line becomes one
    newline."""
    out = ""
    pending_newlines = 0
    started = False
    for ln in lines:
        t = ln.strip(" \t")
        if not t:
            pending_newlines += 1
            continue
        if started:
            out += "\n" * pending_newlines if pending_newlines else " "
        out += t
        started = True
        pending_newlines = 0
    return out


def _fold_quoted(lines: list[str]) -> str:
    """Flow folding for a quoted scalar spanning lines. Like _fold, but the
    first line keeps its leading whitespace, the last line keeps its trailing
    whitespace, and an empty first or last line still folds to one space."""
    out = lines[0].rstrip(" \t")
    pending = 0
    for ln in lines[1:-1]:
        t = ln.strip(" \t")
        if not t:
            pending += 1
            continue
        out += ("\n" * pending if pending else " ") + t
        pending = 0
    return out + ("\n" * pending if pending else " ") + lines[-1].lstrip(" \t")


def _read_block(header: re.Match, body: list[str], at_end: bool = False) -> str:
    """Decode a | or > block scalar with optional chomping/indent indicators.

    at_end: the scalar closes the frontmatter, so (as in PyYAML reading the
    joined block) no line break follows its last line and clip adds none."""
    style = header.group(1)
    chomp = header.group(2) or header.group(4)
    explicit = header.group(3)
    content = [ln for ln in body if ln.strip()]
    if explicit:
        # An explicit indicator counts from the parent key's indent (0 here).
        indent = int(explicit)
    else:
        indent = _indent(content[0]) if content else 0
    lines = [ln[indent:] if ln.strip() else "" for ln in body]
    # Trailing blank lines only matter for keep chomping.
    trailing = 0
    while lines and not lines[-1]:
        lines.pop()
        trailing += 1
    if style == "|":
        text = "\n".join(lines)
    else:
        text = ""
        prev = None  # previous non-empty line
        blanks = 0
        for ln in lines:
            if not ln:
                blanks += 1
                continue
            if prev is None:
                text += "\n" * blanks + ln
            else:
                more = ln[:1] in (" ", "\t") or prev[:1] in (" ", "\t")
                if blanks:
                    text += "\n" * (blanks + (1 if more else 0)) + ln
                else:
                    text += ("\n" if more else " ") + ln
            prev = ln
            blanks = 0
    if not lines:
        return "\n" * trailing if chomp == "+" else ""
    if chomp == "-" or (at_end and not trailing):
        return text
    if chomp == "+":
        return text + "\n" + "\n" * (trailing - 1 if at_end else trailing)
    return text + "\n"


def _decode_double(s: str) -> str:
    simple = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/",
              "0": "\0", " ": " ", "a": "\a", "b": "\b", "e": "\x1b", "f": "\f", "v": "\v"}
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in simple:
                out.append(simple[nxt])
                i += 2
                continue
            if nxt in "xuU":
                width = {"x": 2, "u": 4, "U": 8}[nxt]
                hexpart = s[i + 2:i + 2 + width]
                try:
                    out.append(chr(int(hexpart, 16)))
                    i += 2 + width
                    continue
                except ValueError:
                    pass
            out.append(nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _read_quoted(chunk: list[str]) -> str:
    """Decode a single- or double-quoted scalar that may span lines. Text after
    the closing quote (such as an inline comment) is ignored."""
    joined = "\n".join(chunk)
    q = joined[0]
    i = 1
    while i < len(joined):
        ch = joined[i]
        if q == '"' and ch == "\\":
            i += 2
            continue
        if ch == q:
            if q == "'" and joined[i + 1:i + 2] == "'":
                i += 2
                continue
            break
        i += 1
    inner = joined[1:i]
    if q == '"':
        # Escaped line breaks join without a space; everything else folds.
        inner = re.sub(r"\\\n[ \t]*", "", inner)
        return _decode_double(_fold_quoted(inner.split("\n")) if "\n" in inner else inner)
    folded = _fold_quoted(inner.split("\n")) if "\n" in inner else inner
    return folded.replace("''", "'")


def _read_plain(chunk: list[str]) -> str:
    """Decode a plain scalar that may span lines, ending at an inline comment."""
    kept: list[str] = []
    for ln in chunk:
        cut = _comment_start(ln)
        if cut != -1:
            head = ln[:cut]
            if head.strip():
                kept.append(head)
            break
        kept.append(ln)
    return _fold(kept)


def _starts_collection(body: list[str]) -> bool:
    """True when an empty-valued key's indented body is a list or mapping."""
    for ln in body:
        t = ln.strip()
        if not t or t.startswith("#"):
            continue
        return t.startswith("- ") or t == "-" or KEY_RE.match(t) is not None
    return False


def read_frontmatter_fallback(fm: list[str]) -> dict[str, str]:
    """Read top-level scalar keys without PyYAML.

    Handles plain scalars (single or multi-line, with inline comments),
    single- and double-quoted scalars (single or multi-line, escapes, '' in
    single quotes, '#' inside quotes kept), and | / > block scalars with
    chomping and indentation indicators. Nested mappings, lists, and flow
    collections are skipped. Plain scalars are returned as text without YAML
    type resolution (null, booleans, numbers); the validator only reads the
    name and description keys.
    """
    out: dict[str, str] = {}
    i = 0
    while i < len(fm):
        m = KEY_RE.match(fm[i])
        if not m:
            i += 1
            continue
        key, rest = m.group(1), (m.group(2) or "").strip()
        j = i + 1
        body: list[str] = []
        while j < len(fm) and (not fm[j].strip() or _indent(fm[j]) > 0):
            body.append(fm[j])
            j += 1
        while body and not body[-1].strip() and not BLOCK_HEADER_RE.match(rest):
            body.pop()
        block = BLOCK_HEADER_RE.match(rest)
        if block:
            out[key] = _read_block(block, body, at_end=(j == len(fm)))
        elif rest[:1] in ("\"", "'"):
            out[key] = _read_quoted([rest] + body)
        elif rest[:1] in ("[", "{", "&", "*", "!") or (not rest and _starts_collection(body)):
            pass  # flow collections, anchors, tags, and lists are not scalars we check
        else:
            chunk = ([rest] if rest else []) + body
            if chunk and chunk[0].lstrip().startswith("#"):
                chunk = []
            value = _read_plain(chunk)
            if value:
                out[key] = value
        i = j
    return out


def read_frontmatter(text: str, use_yaml: bool | None = None) -> dict[str, str] | None:
    """Return top-level string keys (name, description, ...) from a SKILL.md.

    Uses PyYAML when it is installed (CI installs it for the other lints);
    otherwise the standard-library fallback above, which is tested to agree
    with PyYAML on every SKILL.md in the repo. Returns None when there is no
    frontmatter block. On a PyYAML parse error, falls back and records the
    error under the '__yaml_error__' key.
    """
    fm = frontmatter_lines(text)
    if fm is None:
        return None
    if use_yaml is None:
        use_yaml = _HAVE_YAML
    if use_yaml:
        try:
            data = yaml.safe_load("\n".join(fm))
        except yaml.YAMLError as exc:
            result = read_frontmatter_fallback(fm)
            result["__yaml_error__"] = exc.__class__.__name__
            return result
        if not isinstance(data, dict):
            return {}
        return {str(k): v for k, v in data.items() if isinstance(v, str)}
    return read_frontmatter_fallback(fm)


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
        if version and not is_semver(version):
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
            if "__yaml_error__" in fm:
                warnings.append(f"{rel}: frontmatter is not valid YAML ({fm['__yaml_error__']}); read with the fallback parser")
            folder = sf.parent.name
            if fm.get("name") != folder:
                errors.append(f"{rel}: frontmatter name '{fm.get('name')}' != folder '{folder}'")
            desc = fm.get("description", "")
            if not desc.strip():
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
