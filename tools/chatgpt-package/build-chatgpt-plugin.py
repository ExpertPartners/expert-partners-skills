#!/usr/bin/env python3
"""
build-chatgpt-plugin.py -- generate the ChatGPT/Codex plugin package from
canonical SKILL.md sources. One authored behavioral source, one generated
surface adapter.

WHY THIS IS A GENERATOR AND NOT A SECOND COPY
---------------------------------------------
OpenAI does not define its own skill format. It adopts the open Agent Skills
standard and delegates frontmatter validation outward, verbatim: "Skill front
matter validation follows the agent skills specification"
(developers.openai.com/api/docs/guides/tools-skills, verified live 2026-09-03,
linking to agentskills.io/specification).

That is the same standard tools/skill-deploy/deploy-skill.sh already targets:
its SPEC_KEYS set (name, description, license, compatibility, metadata,
allowed-tools) IS the agentskills.io frontmatter field set. So a canonical
Expert Partners SKILL.md is already portable to ChatGPT at the body and
frontmatter level with no rewriting. What ChatGPT needs on top is only
packaging:

  1. frontmatter reduced to the spec's six keys (estate skill-map keys such as
     tier/zone/status/subtitle are Claude Code extensions; the upload path
     treats any extra key as a hard error)
  2. a `.codex-plugin/plugin.json` manifest pointing at ./skills/
  3. an optional `agents/openai.yaml` carrying OpenAI UI metadata, the
     implicit-invocation policy, and the MCP tool dependency

None of that is doctrine. All of it is derived. Edit the canonical SKILL.md;
never hand-edit anything this script writes.

VERIFIED SPEC FACTS THIS SCRIPT ENFORCES (all read live 2026-09-03)
-------------------------------------------------------------------
agentskills.io/specification:
  name         required, 1-64 chars, lowercase a-z 0-9 and hyphens only, must
               not start or end with a hyphen, must not contain consecutive
               hyphens, must match the parent directory name
  description  required, 1-1024 chars, non-empty
  optional     license, compatibility (max 500), metadata (string->string),
               allowed-tools (space-separated string, experimental)

developers.openai.com/api/docs/guides/tools-skills ("Limits and validation"):
  "Exactly one `skill.md`/`SKILL.md` file is allowed in a skill bundle" and
  matching is case-insensitive; max zip upload 50 MB; max 500 files per skill
  version; max uncompressed file size 25 MB; the zip "contains a single
  top-level folder".

developers.openai.com/plugins/build/plugins:
  "Every plugin has a `.codex-plugin/plugin.json` manifest"; "Use `skills` for
  bundled skill folders"; "Keep manifest paths relative to the plugin root and
  start them with `./`"; "Only `plugin.json` belongs in `.codex-plugin/`."

WHY NO .mcp.json IS EMITTED (deliberate, not an omission)
----------------------------------------------------------
help.openai.com, "Why is a plugin marked Desktop only?": "A plugin marked
Desktop only cannot run in ChatGPT on the web. Imported plugins can receive
this label when they declare MCP servers, such as in `mcp.json` or
`.mcp.json`, even if a server uses a remote HTTPS URL."

The Estate Brain door is already connected in ChatGPT as its own app (Cognito
client chatgpt-estate-control-tower, wired 2026-08-14). Bundling a second
declaration of the same server would risk the Desktop-only label and would not
add reach. So the package declares the dependency in agents/openai.yaml only.
If a live install still lands as Desktop only, rebuild with
--no-mcp-dependency and the skill drives the separately connected app by tool
name.

Usage:
  build-chatgpt-plugin.py [--out DIR] [--zip PATH] [--no-mcp-dependency]
  build-chatgpt-plugin.py --selftest     # spec validators against fixtures
  build-chatgpt-plugin.py --check        # validate canonical sources only

Exit: 0 ok, 1 a canonical source or built artifact violates the spec, 2 bad
invocation.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import shutil
import sys
import unicodedata
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    sys.exit("FATAL: build-chatgpt-plugin.py needs PyYAML (pip3 install pyyaml)")

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST = Path(__file__).resolve().parent / "plugin-source.json"

# The agentskills.io frontmatter field set. Identical to deploy-skill.sh's
# SPEC_KEYS, because it is the same standard.
SPEC_KEYS = ["name", "description", "license", "compatibility", "metadata", "allowed-tools"]

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# developers.openai.com/api/docs/guides/tools-skills, "Limits and validation"
MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_FILES_PER_SKILL = 500
MAX_UNCOMPRESSED_BYTES = 25 * 1024 * 1024


class SpecError(Exception):
    """A violation of the Agent Skills specification OpenAI defers to."""


def parse_frontmatter(text: str, where: str) -> tuple[dict, str]:
    """Split a SKILL.md into (frontmatter mapping, body-including-closing-fence)."""
    if not text.startswith("---"):
        raise SpecError(f"{where}: no YAML frontmatter block at the very start of the file")
    try:
        end = text.index("\n---", 3)
    except ValueError:
        raise SpecError(f"{where}: frontmatter block is never closed by a '---' line")
    try:
        fm = yaml.safe_load(text[3:end])
    except yaml.YAMLError as exc:
        raise SpecError(f"{where}: frontmatter is not valid YAML: {exc}")
    if not isinstance(fm, dict):
        raise SpecError(f"{where}: frontmatter must be a YAML mapping")
    return fm, text[end:]


def validate_spec(fm: dict, skill_dir_name: str, where: str) -> list[str]:
    """Enforce agentskills.io's name and description rules. Returns warnings."""
    errs: list[str] = []
    warns: list[str] = []

    name = fm.get("name")
    if not isinstance(name, str) or not name.strip():
        errs.append("'name' is missing, empty, or not a string")
    else:
        n = name.strip()
        if not 1 <= len(n) <= 64:
            errs.append(f"name is {len(n)} characters, the spec allows 1 to 64")
        if not NAME_RE.fullmatch(n):
            errs.append(
                f"name {n!r} must be lowercase a-z, 0-9 and single internal hyphens "
                f"(no leading, trailing, or consecutive hyphens)"
            )
        if unicodedata.normalize("NFKC", n) != unicodedata.normalize("NFKC", skill_dir_name):
            errs.append(f"name {n!r} must match its parent directory name {skill_dir_name!r}")

    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errs.append("'description' is missing, empty, or not a string")
    else:
        d = desc.strip()
        u16 = len(d.encode("utf-16-le")) // 2
        if len(d) > 1024 or u16 > 1024:
            errs.append(
                f"description is {len(d)} codepoints / {u16} UTF-16 units, the spec "
                f"allows at most 1024"
            )

    compat = fm.get("compatibility")
    if compat is not None:
        if not isinstance(compat, str):
            errs.append("'compatibility' must be a string")
        elif len(compat) > 500:
            errs.append(f"compatibility is {len(compat)} characters, the spec allows at most 500")

    md = fm.get("metadata")
    if md is not None:
        if not isinstance(md, dict):
            errs.append("'metadata' must be a mapping")
        else:
            bad = [k for k in md if not isinstance(k, str) or not isinstance(md[k], str)]
            if bad:
                errs.append("'metadata' must map strings to strings; offending keys: "
                            + ", ".join(map(str, sorted(bad)[:6])))

    extra = sorted(set(fm) - set(SPEC_KEYS))
    if extra:
        warns.append(
            "canonical frontmatter carries non-spec keys "
            + ", ".join(extra)
            + " (expected for Claude Code; this build strips them)"
        )

    if errs:
        raise SpecError(f"{where} violates the Agent Skills specification:\n  - "
                        + "\n  - ".join(errs))
    return warns


def spec_clean(fm: dict) -> dict:
    """Reduce frontmatter to the spec's six keys, normalizing allowed-tools."""
    kept = {k: fm[k] for k in SPEC_KEYS if k in fm}
    at = kept.get("allowed-tools")
    if at is not None:
        if isinstance(at, (list, tuple)):
            joined = " ".join(str(x).strip() for x in at if str(x).strip())
        elif isinstance(at, str):
            joined = " ".join(x.strip() for x in at.replace(",", " ").split() if x.strip())
        else:
            joined = str(at).strip()
        if joined:
            kept["allowed-tools"] = joined
        else:
            del kept["allowed-tools"]
    return kept


def resolve_skill(name: str) -> Path:
    """Find a canonical skill directory: skills/<name>/ or plugins/*/skills/<name>/."""
    standalone = REPO_ROOT / "skills" / name
    if (standalone / "SKILL.md").is_file():
        return standalone
    matches = [d for d in (REPO_ROOT / "plugins").glob(f"*/skills/{name}")
               if (d / "SKILL.md").is_file()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SpecError(f"skill {name!r} has no SKILL.md under skills/ or plugins/*/skills/")
    raise SpecError(f"skill {name!r} exists under more than one plugin; disambiguate manually")


def openai_yaml(source: dict, fm: dict, with_mcp: bool) -> str:
    """Build agents/openai.yaml: UI metadata, invocation policy, MCP dependency.

    developers.openai.com/codex/build-skills documents `interface`
    (display_name, short_description, ...), `policy.allow_implicit_invocation`
    (default true), and `dependencies.tools[]` with {type, value, description,
    transport, url}. OpenAI's skill-creator sizes short_description at 25-64
    characters.
    """
    iface = source.get("interface", {})
    short = iface.get("short_description", "")
    if short and not 25 <= len(short) <= 64:
        raise SpecError(
            f"interface.short_description is {len(short)} characters; OpenAI's skill-creator "
            f"specifies 25 to 64"
        )
    doc: dict = {
        "interface": {
            "display_name": iface.get("display_name", fm["name"]),
            "short_description": short or fm["name"],
        },
        # Explicit rather than relying on the documented default, because
        # implicit invocation IS the whole point of this skill: it must fire
        # with no magic words from Allison.
        "policy": {"allow_implicit_invocation": True},
    }
    if with_mcp and source.get("mcp_dependency"):
        doc["dependencies"] = {"tools": [source["mcp_dependency"]]}
    return yaml.dump(doc, sort_keys=False, default_flow_style=False,
                     width=10**6, allow_unicode=True)


def build(out_dir: Path, zip_path: Path | None, with_mcp: bool) -> dict:
    source = json.loads(SOURCE_MANIFEST.read_text())
    plugin_name = source["name"]
    root = out_dir / plugin_name
    if root.exists():
        shutil.rmtree(root)
    (root / ".codex-plugin").mkdir(parents=True)

    built: list[str] = []
    all_warns: list[str] = []
    for skill_name in source["skills"]:
        src = resolve_skill(skill_name)
        text = (src / "SKILL.md").read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text, f"{src.relative_to(REPO_ROOT)}/SKILL.md")
        all_warns += [f"{skill_name}: {w}"
                      for w in validate_spec(fm, src.name, f"{skill_name}/SKILL.md")]

        dest = root / "skills" / skill_name
        # Copy references/, scripts/, assets/ when present; never copy the
        # deployed-copy manifest or macOS metadata.
        dest.mkdir(parents=True)
        for sub in ("references", "scripts", "assets"):
            if (src / sub).is_dir():
                shutil.copytree(src / sub, dest / sub,
                                ignore=shutil.ignore_patterns(".DS_Store", "._*",
                                                              "checksums.sha256"))
        rendered = yaml.dump(spec_clean(fm), sort_keys=False, default_flow_style=False,
                             width=10**6, allow_unicode=True).rstrip("\n")
        (dest / "SKILL.md").write_text("---\n" + rendered + body, encoding="utf-8")

        (dest / "agents").mkdir()
        (dest / "agents" / "openai.yaml").write_text(
            openai_yaml(source, fm, with_mcp), encoding="utf-8")
        built.append(skill_name)

    manifest = {
        "name": plugin_name,
        "version": source["version"],
        "description": source["description"],
        "skills": "./skills/",
    }
    if source.get("author"):
        manifest["author"] = source["author"]
    if source.get("interface"):
        manifest["interface"] = {
            "displayName": source["interface"].get("display_name", plugin_name),
            "shortDescription": source["interface"].get("short_description", ""),
        }
    (root / ".codex-plugin" / "plugin.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = {"plugin": plugin_name, "version": source["version"],
              "skills": built, "root": str(root), "warnings": all_warns,
              "mcp_dependency_declared": bool(with_mcp and source.get("mcp_dependency"))}

    if zip_path is not None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        if zip_path.exists():
            zip_path.unlink()
        # Built with zipfile, never Finder/ditto: a __MACOSX/ sibling would be
        # a second top-level entry and break the single-top-level-folder rule.
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    zf.write(p, posixpath.join(plugin_name,
                                               p.relative_to(root).as_posix()))
        zip_preflight(zip_path, plugin_name, built)
        result["zip"] = str(zip_path)
        result["zip_bytes"] = zip_path.stat().st_size
    return result


def zip_preflight(zip_path: Path, plugin_name: str, skills: list[str]) -> None:
    """Assert the built artifact's own structure, not the source it came from."""
    errs: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        names = [i.filename for i in infos]
        if not names:
            errs.append("archive is empty")

        junk = sorted({n for n in names
                       if n.split("/")[0] == "__MACOSX"
                       or posixpath.basename(n.rstrip("/")).startswith("._")
                       or posixpath.basename(n.rstrip("/")) == ".DS_Store"})
        if junk:
            errs.append("archive carries macOS metadata entries: " + ", ".join(junk[:6]))

        for i in infos:
            n = i.filename
            if n.startswith("/") or ".." in n.split("/") or "\\" in n:
                errs.append(f"unsafe entry path: {n!r}")
            if (i.external_attr >> 16) & 0o170000 == 0o120000:
                errs.append(f"archive contains a symlink: {n!r}")
            if i.file_size > MAX_UNCOMPRESSED_BYTES:
                errs.append(f"{n} is {i.file_size} bytes, over the documented 25 MB per-file cap")

        tops = sorted({n.split("/")[0] for n in names if n.strip()})
        if len(tops) != 1:
            errs.append(f"archive must contain exactly one top-level folder; found {tops[:6]}")
        elif tops[0] != plugin_name:
            errs.append(f"top-level folder is {tops[0]!r}, expected {plugin_name!r}")

        if f"{plugin_name}/.codex-plugin/plugin.json" not in names:
            errs.append("archive is missing .codex-plugin/plugin.json, the required entry point")
        else:
            m = json.loads(zf.read(f"{plugin_name}/.codex-plugin/plugin.json"))
            if m.get("skills") != "./skills/":
                errs.append(f"manifest 'skills' is {m.get('skills')!r}, expected './skills/'")
            for key in ("name", "version", "description"):
                if not m.get(key):
                    errs.append(f"manifest is missing required field {key!r}")

        for skill in skills:
            sk = f"{plugin_name}/skills/{skill}/SKILL.md"
            if sk not in names:
                errs.append(f"archive is missing {sk}")
                continue
            if len(names) > MAX_FILES_PER_SKILL:
                errs.append(f"archive holds {len(names)} files, over the documented 500 cap")
            fm, _ = parse_frontmatter(zf.read(sk).decode("utf-8"), sk)
            extra = sorted(set(fm) - set(SPEC_KEYS))
            if extra:
                errs.append(f"packaged {sk} still carries non-spec frontmatter keys: "
                            + ", ".join(extra))
            if fm.get("name") != skill:
                errs.append(f"packaged name {fm.get('name')!r} does not match folder {skill!r}")
            # "Exactly one SKILL.md file is allowed in a skill bundle",
            # matched case-insensitively.
            dupes = [n for n in names
                     if n.lower().startswith(f"{plugin_name}/skills/{skill}/".lower())
                     and posixpath.basename(n).lower() == "skill.md"]
            if len(dupes) != 1:
                errs.append(f"skill {skill!r} must contain exactly one SKILL.md; found {dupes}")

    if zip_path.stat().st_size > MAX_ZIP_BYTES:
        errs.append(f"zip is {zip_path.stat().st_size} bytes, over the documented 50 MB cap")

    if errs:
        raise SpecError(f"{zip_path} would be rejected by the skill upload:\n  - "
                        + "\n  - ".join(errs))


def selftest() -> int:
    """Prove the validators reject what the spec rejects and accept what it allows."""
    cases: list[tuple[str, dict, str, bool]] = [
        ("valid minimal", {"name": "ok-skill", "description": "d"}, "ok-skill", True),
        ("uppercase name", {"name": "Ok-Skill", "description": "d"}, "Ok-Skill", False),
        ("leading hyphen", {"name": "-ok", "description": "d"}, "-ok", False),
        ("trailing hyphen", {"name": "ok-", "description": "d"}, "ok-", False),
        ("consecutive hyphens", {"name": "a--b", "description": "d"}, "a--b", False),
        ("underscore", {"name": "a_b", "description": "d"}, "a_b", False),
        ("name too long", {"name": "a" * 65, "description": "d"}, "a" * 65, False),
        ("name 64 ok", {"name": "a" * 64, "description": "d"}, "a" * 64, True),
        ("dir mismatch", {"name": "ok-skill", "description": "d"}, "other", False),
        ("empty description", {"name": "ok-skill", "description": "  "}, "ok-skill", False),
        ("missing description", {"name": "ok-skill"}, "ok-skill", False),
        ("description 1024 ok", {"name": "ok-skill", "description": "x" * 1024}, "ok-skill", True),
        ("description 1025", {"name": "ok-skill", "description": "x" * 1025}, "ok-skill", False),
        ("compatibility 500 ok",
         {"name": "ok-skill", "description": "d", "compatibility": "c" * 500}, "ok-skill", True),
        ("compatibility 501",
         {"name": "ok-skill", "description": "d", "compatibility": "c" * 501}, "ok-skill", False),
        ("metadata non-string value",
         {"name": "ok-skill", "description": "d", "metadata": {"a": 1}}, "ok-skill", False),
        ("metadata string ok",
         {"name": "ok-skill", "description": "d", "metadata": {"a": "b"}}, "ok-skill", True),
    ]
    failures = 0
    for label, fm, dirname, should_pass in cases:
        try:
            validate_spec(fm, dirname, "selftest")
            passed = True
        except SpecError:
            passed = False
        if passed != should_pass:
            print(f"  FAIL {label}: expected {'pass' if should_pass else 'reject'}, "
                  f"got {'pass' if passed else 'reject'}", file=sys.stderr)
            failures += 1
        else:
            print(f"  ok   {label}")

    # spec_clean must drop estate keys and normalize allowed-tools
    cleaned = spec_clean({"name": "n", "description": "d", "tier": "user", "zone": "routing",
                          "status": "live", "subtitle": "s",
                          "allowed-tools": ["Read", "Bash"]})
    if set(cleaned) != {"name", "description", "allowed-tools"}:
        print(f"  FAIL spec_clean kept {sorted(cleaned)}", file=sys.stderr)
        failures += 1
    elif cleaned["allowed-tools"] != "Read Bash":
        print(f"  FAIL spec_clean allowed-tools {cleaned['allowed-tools']!r}", file=sys.stderr)
        failures += 1
    else:
        print("  ok   spec_clean strips estate keys and normalizes allowed-tools")

    if spec_clean({"name": "n", "description": "d", "allowed-tools": []}).get("allowed-tools"):
        print("  FAIL spec_clean kept an empty allowed-tools", file=sys.stderr)
        failures += 1
    else:
        print("  ok   spec_clean drops an empty allowed-tools")

    print(f"selftest: {len(cases) + 3 - failures} passed, {failures} failed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(REPO_ROOT / "dist" / "chatgpt"))
    ap.add_argument("--zip", dest="zip_path", default=None)
    ap.add_argument("--no-mcp-dependency", action="store_true",
                    help="omit the agents/openai.yaml MCP dependency block (rebuild path if a "
                         "live install lands as Desktop only)")
    ap.add_argument("--selftest", action="store_true", help="run spec validator fixtures and exit")
    ap.add_argument("--check", action="store_true",
                    help="validate canonical sources against the spec without building")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    try:
        if args.check:
            source = json.loads(SOURCE_MANIFEST.read_text())
            for skill_name in source["skills"]:
                src = resolve_skill(skill_name)
                fm, _ = parse_frontmatter((src / "SKILL.md").read_text(encoding="utf-8"),
                                          f"{skill_name}/SKILL.md")
                for w in validate_spec(fm, src.name, f"{skill_name}/SKILL.md"):
                    print(f"warn: {w}", file=sys.stderr)
                print(f"ok: {src.relative_to(REPO_ROOT)}/SKILL.md is Agent-Skills-spec clean "
                      f"(name {len(fm['name'])} chars, description {len(fm['description'])} "
                      f"chars, {1024 - len(fm['description'])} chars of headroom)")
            return 0

        result = build(Path(args.out), Path(args.zip_path) if args.zip_path else None,
                       not args.no_mcp_dependency)
    except SpecError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1

    for w in result["warnings"]:
        print(f"warn: {w}", file=sys.stderr)
    print(json.dumps({k: v for k, v in result.items() if k != "warnings"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
