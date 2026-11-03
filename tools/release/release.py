#!/usr/bin/env python3
"""Release step: fold the notes in .changeset/ into one version bump and one CHANGELOG
entry per plugin. Run on main after merges, never on a builder branch.

A builder pull request adds one note, .changeset/<issue number>-<slug>.md, and never
edits a version or the top of a CHANGELOG (the auto-merge gate refuses that).
.changeset/README.md gives the note format. This step, for each plugin named by at
least one note:

  - takes the largest bump any note asks for (major > minor > patch),
  - writes the new version to plugins/<plugin>/.claude-plugin/plugin.json and to the
    plugin's entry in .claude-plugin/marketplace.json,
  - adds one entry, "## <version> - <date>", to the top of plugins/<plugin>/CHANGELOG.md
    (creating the file when it does not exist yet), carrying every note's text in
    file name order,
  - and deletes the notes it used.

Every note is read and checked before anything is written, so a bad note changes
nothing. Standard library only.

Usage, from the repository root:
  python3 tools/release/release.py            # apply the notes
  python3 tools/release/release.py --check    # validate and print the plan, write nothing
Options: --root DIR (repository root, default the current directory), --date YYYY-MM-DD
(entry date, default today in UTC).

Exit code: 0 = released or nothing to release, 1 = a note or a version is invalid.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

CHANGESET_DIR = ".changeset"
MARKETPLACE = ".claude-plugin/marketplace.json"
BUMPS = ("patch", "minor", "major")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
KEY_RE = re.compile(r"""^\s*(?:"([^"]+)"|'([^']+)'|([A-Za-z0-9._-]+))\s*:\s*(\S+?)\s*$""")
MANIFEST_VERSION_RE = re.compile(r'("version"\s*:\s*")([^"\\]*)(")')


class ReleaseError(Exception):
    pass


@dataclass
class Note:
    path: Path
    bumps: dict[str, str]
    body: str


@dataclass
class Plan:
    plugin: str
    old: str
    new: str
    bump: str
    notes: list[Note] = field(default_factory=list)


def parse_note(path: Path) -> Note:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ReleaseError(f"{path}: is not UTF-8 text") from None
    return parse_note_text(path, text)


def parse_note_text(path: Path, text: str) -> Note:
    """tools/auto-merge-gate/gate.py (note_problem) applies the same rules before a note
    can merge; its tests run both on the same notes, so change them together."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines[0].strip() != "---":
        raise ReleaseError(f"{path}: must start with a --- line, then one plugin: bump line per plugin, then ---")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ReleaseError(f"{path}: the opening --- has no closing ---") from None
    bumps: dict[str, str] = {}
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = KEY_RE.match(raw)
        if not m:
            raise ReleaseError(f"{path}: cannot read {raw.strip()!r}; write it as <plugin>: patch|minor|major")
        name = m.group(1) or m.group(2) or m.group(3)
        bump = m.group(4).strip("\"'").lower()
        if bump not in BUMPS:
            raise ReleaseError(f"{path}: {name} asks for {bump!r}; use patch, minor or major")
        if name in bumps:
            raise ReleaseError(f"{path}: names {name} twice")
        bumps[name] = bump
    if not bumps:
        raise ReleaseError(f"{path}: names no plugin")
    body = "\n".join(lines[end + 1:]).strip()
    if not body:
        raise ReleaseError(f"{path}: says nothing about the change; write it below the closing ---")
    # Each release adds exactly one "## " heading, the line the gate splits CHANGELOG entries on.
    if any(line.startswith("## ") for line in body.split("\n")):
        raise ReleaseError(f"{path}: has a '## ' heading in its text, which would start a second CHANGELOG entry; "
                           "use ### or lower")
    return Note(path, bumps, body)


def read_notes(root: Path) -> list[Note]:
    folder = root / CHANGESET_DIR
    if not folder.is_dir():
        return []
    return [parse_note(p) for p in sorted(folder.glob("*.md")) if p.name.lower() != "readme.md"]


def bump_version(version: str, bump: str) -> str:
    m = VERSION_RE.match(version)
    if not m:
        raise ReleaseError(f"version {version!r} is not MAJOR.MINOR.PATCH")
    major, minor, patch = (int(x) for x in m.groups())
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def manifest_path(root: Path, plugin: str) -> Path:
    return root / "plugins" / plugin / ".claude-plugin" / "plugin.json"


def changelog_path(root: Path, plugin: str) -> Path:
    return root / "plugins" / plugin / "CHANGELOG.md"


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReleaseError(f"{path}: cannot be read as JSON ({exc})") from None
    if not isinstance(data, dict):
        raise ReleaseError(f"{path}: is not a JSON object")
    return data


def plan_release(root: Path, notes: list[Note]) -> list[Plan]:
    market = load_json(root / MARKETPLACE)
    if not isinstance(market.get("plugins"), list):
        raise ReleaseError(f"{MARKETPLACE}: has no plugins list")
    entries = {p.get("name"): p for p in market["plugins"] if isinstance(p, dict)}
    plans: dict[str, Plan] = {}
    for note in notes:
        for plugin, bump in note.bumps.items():
            if plugin not in entries:
                raise ReleaseError(f"{note.path}: {plugin} is not a plugin in {MARKETPLACE}")
            if plugin not in plans:
                manifest = manifest_path(root, plugin)
                versions = {v for v in (entries[plugin].get("version"),
                                        load_json(manifest).get("version") if manifest.exists() else None) if v}
                if len(versions) != 1:
                    raise ReleaseError(
                        f"{plugin}: {MARKETPLACE} and {manifest.relative_to(root)} must carry one version, "
                        f"found {sorted(versions) or 'none'}")
                plans[plugin] = Plan(plugin, versions.pop(), "", bump)
            plan = plans[plugin]
            if BUMPS.index(bump) > BUMPS.index(plan.bump):
                plan.bump = bump
            plan.notes.append(note)
    for plan in plans.values():
        plan.new = bump_version(plan.old, plan.bump)
        log = changelog_path(root, plan.plugin)
        if log.exists() and re.search(rf"^## {re.escape(plan.new)}\b", log.read_text(encoding="utf-8"), re.M):
            raise ReleaseError(f"{log.relative_to(root)} already has an entry for {plan.new}")
    return [plans[name] for name in sorted(plans)]


def set_manifest_version(text: str, version: str) -> str:
    data = json.loads(text)
    new_text, count = MANIFEST_VERSION_RE.subn(lambda m: m.group(1) + version + m.group(3), text, count=1)
    # Keep the file's own layout when a plain substitution does exactly the one change.
    if count == 1 and json.loads(new_text) == dict(data, version=version):
        return new_text
    data["version"] = version
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def changelog_entry(plan: Plan, date: str) -> str:
    return f"## {plan.new} - {date}\n\n" + "\n\n".join(n.body for n in plan.notes) + "\n"


def apply_release(root: Path, plans: list[Plan], date: str) -> None:
    market_path = root / MARKETPLACE
    market = load_json(market_path)
    writes: dict[Path, str] = {}
    for plan in plans:
        for entry in market["plugins"]:
            if isinstance(entry, dict) and entry.get("name") == plan.plugin:
                entry["version"] = plan.new
        manifest = manifest_path(root, plan.plugin)
        if manifest.exists():
            writes[manifest] = set_manifest_version(manifest.read_text(encoding="utf-8"), plan.new)
        log = changelog_path(root, plan.plugin)
        old_log = log.read_text(encoding="utf-8") if log.exists() else ""
        writes[log] = changelog_entry(plan, date) + old_log
    writes[market_path] = json.dumps(market, indent=2, ensure_ascii=False) + "\n"
    for path, text in writes.items():
        path.write_text(text, encoding="utf-8")
    for note in {n.path for plan in plans for n in plan.notes}:
        note.unlink()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Fold .changeset notes into version bumps and CHANGELOG entries.")
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    parser.add_argument("--date", help="entry date as YYYY-MM-DD (default: today in UTC)")
    parser.add_argument("--check", action="store_true", help="validate the notes and print the plan; write nothing")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    date = args.date or dt.datetime.now(dt.timezone.utc).date().isoformat()
    try:
        dt.date.fromisoformat(date)
        notes = read_notes(root)
        plans = plan_release(root, notes)
    except (ReleaseError, ValueError) as exc:
        print(f"release: {exc}", file=sys.stderr)
        return 1
    if not plans:
        print("release: no notes in .changeset; nothing to release.")
        return 0
    for plan in plans:
        names = ", ".join(n.path.name for n in plan.notes)
        print(f"release: {plan.plugin} {plan.old} -> {plan.new} ({plan.bump}; {names})")
    if args.check:
        print("release: check only, nothing written.")
        return 0
    apply_release(root, plans, date)
    print(f"release: wrote {len(plans)} version bump(s) and CHANGELOG entr{'y' if len(plans) == 1 else 'ies'}, "
          f"removed {len({n.path for p in plans for n in p.notes})} note(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
