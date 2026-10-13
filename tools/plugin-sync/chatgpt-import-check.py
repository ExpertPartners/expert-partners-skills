#!/usr/bin/env python3
"""Check every plugin against OpenAI's published plugin and skill import rules.

Rules come from developers.openai.com/plugins/deploy/submission-errors (read
2026-10-13). Run before a ChatGPT sync. Exit 1 on any error.
"""
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def check_svg(path: Path, errs: list, label: str) -> None:
    if path.suffix.lower() != ".svg":
        return
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<svg\b([^>]*)>", text)
    if not m:
        errs.append(f"{label}: svg root element missing")
        return
    attrs = dict(re.findall(r'([\w:-]+)="([^"]*)"', m.group(1)))
    if "viewBox" in attrs:
        parts = attrs["viewBox"].replace(",", " ").split()
        w, h = float(parts[2]), float(parts[3])
    else:
        w, h = float(attrs["width"]), float(attrs["height"])
    for key in ("width", "height"):
        if key in attrs and not re.fullmatch(r"[0-9.]+", attrs[key]):
            errs.append(f"{label}: svg {key} must be numeric with no units")
    if w != h:
        errs.append(f"{label}: svg is not square")
    sizes = [float(attrs[k]) for k in ("width", "height") if k in attrs] or [w, h]
    if min(sizes) < 48:
        errs.append(f"{label}: svg is smaller than 48x48")


def check_agent_yaml(skill: Path, errs: list) -> None:
    f = skill / "agents" / "openai.yaml"
    if not f.exists():
        return
    label = f"{skill.name}/agents/openai.yaml"
    d = yaml.safe_load(f.read_text(encoding="utf-8"))
    if not isinstance(d, dict) or not isinstance(d.get("interface"), dict):
        errs.append(f"{label}: interface mapping required")
        return
    i = d["interface"]
    for k in ("display_name", "short_description"):
        if not isinstance(i.get(k), str) or not i[k].strip():
            errs.append(f"{label}: interface.{k} required string")
    for k in ("icon_small", "icon_large"):
        if k in i:
            v = i[k]
            if not isinstance(v, str) or not v.strip():
                errs.append(f"{label}: interface.{k} must be a non-empty path")
                continue
            if not v.startswith("./"):
                errs.append(f"{label}: interface.{k} must start with ./")
            target = skill / v
            if not target.is_file():
                errs.append(f"{label}: interface.{k} file missing")
            else:
                check_svg(target, errs, f"{skill.name}/{v}")
    if "brand_color" in i and not HEX.match(str(i["brand_color"])):
        errs.append(f"{label}: interface.brand_color must be six-digit hex")
    pol = d.get("policy")
    if pol is not None:
        if not isinstance(pol, dict) or set(pol) - {"products", "allow_implicit_invocation"}:
            errs.append(f"{label}: policy may contain only products and allow_implicit_invocation")
        else:
            prods = pol.get("products")
            if prods is not None and (not isinstance(prods, list) or not prods or set(prods) - {"CHAT", "CODEX"}):
                errs.append(f"{label}: policy.products must be CHAT, CODEX or both")
            aii = pol.get("allow_implicit_invocation")
            if aii is not None and not isinstance(aii, bool):
                errs.append(f"{label}: allow_implicit_invocation must be true or false")
    deps = d.get("dependencies")
    if isinstance(deps, dict) and set(deps) - {"tools"}:
        errs.append(f"{label}: only dependencies.tools is supported")


def check_plugin(plug: Path) -> list:
    errs = []
    pn = plug.name
    mf = plug / ".claude-plugin" / "plugin.json"
    m = json.loads(mf.read_text(encoding="utf-8"))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", m.get("name", "")):
        errs.append(f"{pn}: plugin name format")
    if not re.fullmatch(r"\d+\.\d+\.\d+.*", str(m.get("version", ""))):
        errs.append(f"{pn}: version must be semver")
    d = m.get("description")
    if not isinstance(d, str) or not d.strip() or len(d) > 1024:
        errs.append(f"{pn}: description missing or over 1024")
    names = set()
    for sd in sorted((plug / "skills").iterdir()):
        if not sd.is_dir():
            continue
        if sd.name.startswith("."):
            errs.append(f"{pn}/{sd.name}: hidden skill directory")
        md = sd / "SKILL.md"
        if not md.is_file() or md.is_symlink():
            errs.append(f"{pn}/{sd.name}: SKILL.md must be a regular file")
            continue
        text = md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            errs.append(f"{pn}/{sd.name}: front matter missing")
            continue
        end = text.find("\n---", 3)
        if end < 0:
            errs.append(f"{pn}/{sd.name}: front matter unclosed")
            continue
        fm = yaml.safe_load(text[3:end])
        if not isinstance(fm, dict):
            errs.append(f"{pn}/{sd.name}: front matter must be a mapping")
            continue
        n, desc = fm.get("name"), fm.get("description")
        if not isinstance(n, str) or not n.strip():
            errs.append(f"{pn}/{sd.name}: name must be a non-empty string")
        elif len(pn) + 1 + len(n) > 64:
            errs.append(f"{pn}/{sd.name}: plugin:skill identity over 64")
        if n in names:
            errs.append(f"{pn}/{sd.name}: duplicate skill name")
        names.add(n)
        if not isinstance(desc, str) or not desc.strip() or len(desc) > 1024:
            errs.append(f"{pn}/{sd.name}: description missing or over 1024")
        if not text[end + 4:].strip():
            errs.append(f"{pn}/{sd.name}: empty body")
        if any(p.name.lower() == "skill.md" for p in sd.rglob("*") if p != md):
            errs.append(f"{pn}/{sd.name}: nested SKILL.md")
        check_agent_yaml(sd, errs)
    for p in plug.rglob("*"):
        if p.is_symlink():
            errs.append(f"{pn}: symlink {p.relative_to(plug)}")
    return errs


def main() -> int:
    bad = 0
    for plug in sorted((ROOT / "plugins").iterdir()):
        if not (plug / ".claude-plugin" / "plugin.json").exists():
            continue
        errs = check_plugin(plug)
        print(f"{plug.name}: {'OK' if not errs else 'FAIL'}")
        for e in errs:
            print(f"   {e}")
        bad += len(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
