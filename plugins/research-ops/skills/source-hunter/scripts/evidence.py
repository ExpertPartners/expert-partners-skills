"""Evidence folder guard and hunt bookkeeping.

Every Source Hunter output goes through a Hunt. A Hunt refuses an evidence
folder that sits anywhere inside a git working tree, so recovered course text
can never be committed by accident.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HUNT_FILE = "hunt.json"
ROUTES_FILE = "routes.jsonl"
REPORT_FILE = "report.md"


class EvidenceError(RuntimeError):
    """The evidence folder is unsafe or a write would leave it."""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slug(text: str, limit: int = 60) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return (cleaned[:limit].strip("-")) or "item"


def _nearest_existing(path: Path) -> Path:
    current = path
    while not current.exists() and current.parent != current:
        current = current.parent
    return current


def git_work_tree_for(path: str | os.PathLike) -> Path | None:
    """Return the git working tree that contains path, or None.

    The path may not exist yet. Its nearest existing ancestor is checked, both
    by looking for a .git entry and by asking git itself when git is installed.
    """
    absolute = Path(os.path.abspath(os.path.expanduser(os.fspath(path))))
    existing = _nearest_existing(absolute).resolve()
    if not existing.is_dir():
        existing = existing.parent
    for candidate in (existing, *existing.parents):
        if (candidate / ".git").exists():
            return candidate
    git = shutil.which("git")
    if git:
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        result = subprocess.run(
            [git, "-C", str(existing), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    return None


def guard_evidence_folder(path: str | os.PathLike) -> Path:
    """Resolve the evidence folder and refuse it if it is inside a git working tree."""
    if not os.fspath(path):
        raise EvidenceError("An evidence folder is required.")
    tree = git_work_tree_for(path)
    if tree is not None:
        raise EvidenceError(
            f"Refusing to write to {path}: it is inside the git working tree at {tree}. "
            "Use the private evidence folder outside any repository."
        )
    return Path(os.path.abspath(os.path.expanduser(os.fspath(path)))).resolve()


class Hunt:
    """One hunt, kept in one evidence folder."""

    def __init__(self, evidence: str | os.PathLike, name: str | None = None):
        self.root = guard_evidence_folder(evidence)
        self.root.mkdir(parents=True, exist_ok=True)
        meta = self._load_meta()
        if name and not meta.get("name"):
            meta["name"] = name
        self.meta = meta
        self._save_meta()

    # Paths and writes

    def path(self, relative: str | os.PathLike) -> Path:
        target = (self.root / relative).resolve()
        if target != self.root and self.root not in target.parents:
            raise EvidenceError(f"Refusing to write outside the evidence folder: {relative}")
        return target

    def rel(self, path: Path) -> str:
        return Path(path).resolve().relative_to(self.root).as_posix()

    def mkdir(self, relative: str | os.PathLike) -> Path:
        target = self.path(relative)
        target.mkdir(parents=True, exist_ok=True)
        return target

    def fresh_dir(self, prefix: str) -> Path:
        """Create a new numbered folder so earlier evidence is never overwritten."""
        number = 1
        while self.path(f"{prefix}-{number:02d}").exists():
            number += 1
        return self.mkdir(f"{prefix}-{number:02d}")

    def write_text(self, relative: str | os.PathLike, content: str) -> Path:
        target = self.path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def write_json(self, relative: str | os.PathLike, data) -> Path:
        return self.write_text(relative, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    # Hunt metadata

    def _load_meta(self) -> dict:
        meta_path = self.root / HUNT_FILE
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        else:
            meta = {"name": "", "created_at": now_iso()}
        meta.setdefault("wants", [])
        meta.setdefault("notes", [])
        return meta

    def _save_meta(self) -> None:
        self.write_json(HUNT_FILE, self.meta)

    @property
    def name(self) -> str:
        return self.meta.get("name") or self.root.name

    def add_wants(self, wants) -> None:
        for want in wants or []:
            want = want.strip()
            if want and want not in self.meta["wants"]:
                self.meta["wants"].append(want)
        self._save_meta()

    def add_notes(self, notes) -> None:
        for note in notes or []:
            note = note.strip()
            if note:
                self.meta["notes"].append({"at": now_iso(), "note": note})
        self._save_meta()

    # Routes

    def routes(self) -> list[dict]:
        routes_path = self.root / ROUTES_FILE
        if not routes_path.exists():
            return []
        return [json.loads(line) for line in routes_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def record_route(self, route: dict) -> dict:
        record = {"number": len(self.routes()) + 1, "recorded_at": now_iso(), **route}
        record.setdefault("found", [])
        record.setdefault("missing", [])
        record.setdefault("problems", [])
        record.setdefault("evidence", [])
        record.setdefault("text_files", [])
        with self.path(ROUTES_FILE).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record
