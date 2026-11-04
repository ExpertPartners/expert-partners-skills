#!/usr/bin/env python3
"""Retire the four old user-tier helpers once the operating-doctrine plugin replaces them.

intake, new-project, session-home and verify-docs were once deployed as standalone copies
into ~/.claude/skills and ~/.agents/skills. They now ship in the operating-doctrine plugin
(verify-docs as part of research-before-guessing), but native plugin delivery cannot touch
the old copies, so they stay discoverable. codex-sync.sh and claude-code-sync.sh call this
after each full delivery run. For each old name it:

1. recognizes the copy: its SKILL.md, with any skill-deploy DEPLOYED COPY header naming
   expert-partners-skills skills/<name>/SKILL.md removed, must equal a committed version
   of that file in this checkout's first-parent history. Anything else is left alone and
   reported;
2. proves the replacement: the operating-doctrine plugin is installed and enabled on this
   surface and its skill folder holds exactly the bytes committed at HEAD;
3. turns off only the old copy through the surface's own per-skill setting, after a
   private, verified backup: Claude Code user settings skillOverrides <name> = "off"
   (plugin skills are unaffected, code.claude.com/docs/en/skills, read 2026-11-04), and
   Codex app-server skills/config/write with the exact SKILL.md path and enabled false
   (codex-rs app-server-protocol v2, read 2026-11-04);
4. reads the setting back and writes a receipt.

No file under ~/.claude/skills or ~/.agents/skills is moved, edited or deleted, and no
plugin cache is written. A failure is reported in the receipt and fails the run, so the
next five-minute slot retries it. A replacement that is not yet proven leaves the old copy
on and is checked again on the next full run.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import queue
import re
import signal
import subprocess
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

MK = "expert-partners"
PLUGIN = "operating-doctrine"
PLUGIN_ID = f"{PLUGIN}@{MK}"
# Old user-tier name -> the operating-doctrine skill folder that replaces it.
LEGACY = {
    "intake": "intake",
    "new-project": "new-project",
    "session-home": "session-home",
    "verify-docs": "research-before-guessing",
}
HEADER = re.compile(
    rb"^# DEPLOYED COPY \(\d{4}-\d{2}-\d{2}, skill-deploy pipeline\): the canonical home is\n"
    rb"# (\S+) (\S+?SKILL\.md)\. Deployed at [^\n]+?\.\n"
    rb"# Edit the canonical copy first, then redeploy via tools/skill-deploy\.\n",
    re.M,
)
JUNK = {".DS_Store", "checksums.sha256"}
NOTE = ("Turns off only the old user-tier copies through each surface's own per-skill setting. "
        "Runtime use is unverified until a new or reloaded session lists the skills.")
LOCK_WAIT = 60.0
REQUEST_TIMEOUT = 60.0

Log = Callable[[str], None]


class MigrationError(Exception):
    pass


def blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def junk(rel: str) -> bool:
    parts = rel.split("/")
    return parts[-1] in JUNK or parts[-1].startswith("._") or parts[-1].endswith(".pyc") or "__pycache__" in parts


class Repo:
    def __init__(self, root: str) -> None:
        self.root = root

    def git(self, *args: str) -> bytes:
        r = subprocess.run(["git", "--no-replace-objects", "-C", self.root, *args],
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
        if r.returncode != 0:
            raise subprocess.CalledProcessError(r.returncode, args, r.stdout, r.stderr)
        return r.stdout

    def history_blobs(self, path: str) -> Set[str]:
        """Every blob the path held on the checked-out first-parent lineage."""
        blobs = set()
        for commit in self.git("log", "--first-parent", "--format=%H", "HEAD", "--", path).decode().split():
            try:
                blobs.add(self.git("rev-parse", "--verify", "--quiet", f"{commit}:{path}").decode().strip())
            except subprocess.CalledProcessError:
                continue  # the commit that deleted it
        return blobs

    def tree(self, folder: str) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for entry in self.git("ls-tree", "-r", "-z", "HEAD", "--", folder + "/").split(b"\0"):
            if not entry:
                continue
            meta, _, path = entry.decode("utf-8", "surrogateescape").partition("\t")
            mode, kind, obj = meta.split()
            rel = path[len(folder) + 1:]
            if kind == "blob" and not junk(rel):
                out[rel] = obj
        return out


def classify(repo: Repo, name: str, skills_root: str) -> Tuple[str, str]:
    """('absent' | 'trusted' | 'unrecognized', detail) for one old copy."""
    folder = os.path.join(skills_root, name)
    path = os.path.join(folder, "SKILL.md")
    if not os.path.lexists(folder):
        return "absent", ""
    if os.path.islink(folder) or os.path.islink(path):
        return "unrecognized", "it is a symlink, not a copy this producer made"
    if not os.path.isfile(path):
        return "unrecognized", "it has no regular SKILL.md"
    with open(path, "rb") as f:
        data = f.read()
    source = f"skills/{name}/SKILL.md"
    m = HEADER.search(data)
    if m:
        if (m.group(1), m.group(2)) != (b"expert-partners-skills", source.encode()):
            return "unrecognized", "its DEPLOYED COPY header names another canonical home"
        data = data[:m.start()] + data[m.end():]
    blob = blob_id(data)
    if blob in repo.history_blobs(source):
        return "trusted", blob
    return "unrecognized", f"its bytes match no committed version of {source}"


def tree_mismatch(repo: Repo, skill: str, installed: str) -> Optional[str]:
    """None when the installed skill folder holds exactly the bytes committed at HEAD."""
    want = repo.tree(f"plugins/{PLUGIN}/skills/{skill}")
    if "SKILL.md" not in want:
        return f"this checkout has no {PLUGIN}/skills/{skill}"
    if not os.path.isdir(installed) or os.path.islink(installed):
        return f"the installed {skill} folder is missing"
    have: Dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(installed):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, installed).replace(os.sep, "/")
            if junk(rel):
                continue
            if os.path.islink(full):
                return f"the installed {skill}/{rel} is a symlink"
            with open(full, "rb") as f:
                have[rel] = blob_id(f.read())
    for rel in sorted(set(want) | set(have)):
        if want.get(rel) != have.get(rel):
            return f"the installed {skill}/{rel} does not match the repo"
    return None


# ------------------------------------------------------------------ private, verified writes

def private_backup(backup_dir: str, label: str, data: bytes) -> Dict[str, str]:
    os.makedirs(backup_dir, mode=0o700, exist_ok=True)
    os.chmod(backup_dir, 0o700)
    stamp = f"{label}.{time.strftime('%Y%m%d-%H%M%S')}.{os.getpid()}"
    for n in range(1000):
        path = os.path.join(backup_dir, f"{stamp}.{n}.bak")
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            break
        except FileExistsError:
            continue
    else:
        raise MigrationError(f"no free backup name in {backup_dir}")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    with open(path, "rb") as f:
        if f.read() != data:
            raise MigrationError(f"backup {path} did not read back")
    return {"path": path, "sha256": hashlib.sha256(data).hexdigest()}


def read_or_none(path: str) -> Optional[bytes]:
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None


def set_claude_overrides(settings: str, names: List[str], backup_dir: str,
                         backups: List[Dict[str, str]]) -> Dict[str, str]:
    """Set skillOverrides <name> = "off" for each name, keeping every other field.

    Claude Code can write the same file, so the new file only replaces the bytes it was
    computed from; when they changed underneath, it starts over."""
    if os.path.islink(settings):
        raise MigrationError(f"{settings} is a symlink, left unchanged")
    for _ in range(5):
        raw = read_or_none(settings)
        try:
            data = json.loads(raw) if raw and raw.strip() else {}
        except ValueError as e:
            raise MigrationError(f"{settings} is not valid JSON, left unchanged: {e}")
        if not isinstance(data, dict):
            raise MigrationError(f"{settings} is not a JSON object, left unchanged")
        overrides = data.get("skillOverrides", {})
        if not isinstance(overrides, dict):
            raise MigrationError(f"{settings} skillOverrides is not an object, left unchanged")
        states: Dict[str, str] = {}
        todo = []
        for n in names:
            v = overrides.get(n)
            if v == "off":
                states[n] = "already off"
            elif v is not None:
                states[n] = f"left alone, skillOverrides already sets it to {v!r}"
            else:
                todo.append(n)
        if not todo:
            return states
        if raw is not None:
            backups.append(private_backup(backup_dir, "claude-settings.json", raw))
        new = dict(data)
        new["skillOverrides"] = dict(overrides, **{n: "off" for n in todo})
        text = json.dumps(new, indent=2, ensure_ascii=False) + "\n"
        mode = os.stat(settings).st_mode & 0o777 if raw is not None else 0o600
        os.makedirs(os.path.dirname(settings), exist_ok=True)
        tmp = f"{settings}.{os.getpid()}.legacy-skills.tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if read_or_none(settings) != raw:
            os.unlink(tmp)
            time.sleep(0.2)
            continue
        os.replace(tmp, settings)
        back = read_or_none(settings)
        if back is None or json.loads(back) != new:
            raise MigrationError(f"{settings} did not read back with the new skillOverrides")
        states.update({n: "turned off" for n in todo})
        return states
    raise MigrationError(f"{settings} kept changing during the update")


# ------------------------------------------------------------------ Codex app-server client

class AppServer:
    """JSON-RPC over stdio to one app-server this run started and stops."""

    def __init__(self, argv: List[str], cwd: str) -> None:
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, cwd=cwd, start_new_session=True)
        self.inbox: "queue.Queue[Optional[Dict[str, Any]]]" = queue.Queue()
        self.next_id = 1
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        assert self.proc.stdout is not None
        try:
            for line in self.proc.stdout:
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if isinstance(msg, dict):
                    self.inbox.put(msg)
        finally:
            self.inbox.put(None)

    def _write(self, msg: Dict[str, Any]) -> None:
        assert self.proc.stdin is not None
        try:
            self.proc.stdin.write(json.dumps(msg).encode() + b"\n")
            self.proc.stdin.flush()
        except (OSError, ValueError):
            raise MigrationError("codex app-server closed its input")

    def notify(self, method: str) -> None:
        self._write({"method": method})

    def request(self, method: str, params: Dict[str, Any], timeout: float = REQUEST_TIMEOUT) -> Any:
        rid = self.next_id
        self.next_id += 1
        self._write({"id": rid, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise MigrationError(f"codex app-server {method} timed out")
            try:
                msg = self.inbox.get(timeout=min(left, 0.25))
            except queue.Empty:
                continue
            if msg is None:
                raise MigrationError(f"codex app-server exited during {method}")
            if "method" in msg:
                if "id" in msg:  # a server request this client never grants
                    self._write({"id": msg["id"], "error": {"code": -32601, "message": "not supported"}})
                continue
            if msg.get("id") != rid:
                continue
            if "error" in msg:
                err = msg["error"]
                raise MigrationError(f"codex app-server {method} failed: "
                                     f"{err.get('message') if isinstance(err, dict) else err}")
            return msg.get("result")

    def close(self) -> None:
        try:
            if self.proc.stdin is not None:
                self.proc.stdin.close()
        except OSError:
            pass
        for sig in (None, signal.SIGTERM, signal.SIGKILL):
            if sig is not None:
                try:
                    os.killpg(self.proc.pid, sig)
                except (ProcessLookupError, PermissionError, OSError):
                    pass
            try:
                self.proc.wait(timeout=3)
                return
            except subprocess.TimeoutExpired:
                continue


def codex_skills(server: AppServer, cwd: str) -> List[Dict[str, Any]]:
    result = server.request("skills/list", {"cwds": [cwd], "forceReload": True})
    if not isinstance(result, dict) or not isinstance(result.get("data"), list):
        raise MigrationError("codex app-server skills/list returned an unexpected shape")
    skills: List[Dict[str, Any]] = []
    for entry in result["data"]:
        if isinstance(entry, dict) and isinstance(entry.get("skills"), list):
            skills.extend(s for s in entry["skills"] if isinstance(s, dict) and isinstance(s.get("path"), str))
    return skills


def same_file(a: str, b: str) -> bool:
    return os.path.realpath(a) == os.path.realpath(b)


# ------------------------------------------------------------------ shared run

def run(surface: str, repo_root: str, state_dir: str, head: str, log: Log,
        skills_root: str, act: Callable[[Repo, List[str], Dict[str, Dict[str, Any]], List[Dict[str, str]]], None]) -> Dict[str, Any]:
    receipt_path = os.path.join(state_dir, f"{surface}-legacy-skills.json")
    repo = Repo(repo_root)
    skills: Dict[str, Dict[str, Any]] = {}
    backups: List[Dict[str, str]] = []
    failures: List[str] = []
    os.makedirs(state_dir, exist_ok=True)
    lock = open(os.path.join(state_dir, "legacy-skills.lock"), "a")
    try:
        deadline = time.time() + LOCK_WAIT
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() >= deadline:
                    raise MigrationError("another legacy skill migration held the lock for a minute")
                time.sleep(0.5)
        trusted = []
        for name in LEGACY:
            path = os.path.join(skills_root, name, "SKILL.md")
            kind, detail = classify(repo, name, skills_root)
            if kind == "absent":
                skills[name] = {"copy": path, "state": "no old copy"}
            elif kind == "unrecognized":
                skills[name] = {"copy": path, "state": f"left alone, not recognized: {detail}"}
                log(f"legacy {name}: left alone, {detail}")
            else:
                skills[name] = {"copy": path, "matched_blob": detail}
                trusted.append(name)
        if trusted:
            act(repo, trusted, skills, backups)
    except (MigrationError, OSError, ValueError, subprocess.SubprocessError) as e:
        failures.append(str(e))
    finally:
        lock.close()
    for name, row in skills.items():
        if str(row.get("state", "")).startswith("failed"):
            failures.append(f"{name}: {row['state']}")
    waiting = [n for n, row in skills.items() if str(row.get("state", "")).startswith("waiting")]
    status = "failed" if failures else "waiting" if waiting else "ok"
    receipt = {"surface": surface, "commit": head, "status": status, "failures": failures,
               "skills": skills, "backups": backups, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "note": NOTE}
    tmp = f"{receipt_path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(receipt, f, indent=2)
        f.write("\n")
    os.replace(tmp, receipt_path)
    for name, row in skills.items():
        if row.get("state") not in ("no old copy",) and not str(row.get("state", "")).startswith("left alone, not"):
            log(f"legacy {name}: {row.get('state')}")
    if failures:
        log("FAILED: legacy skill migration: " + "; ".join(failures))
    return {"status": status, "failures": failures, "receipt": receipt_path}


def claude_migrate(repo_root: str, state_dir: str, head: str, log: Log, claude: str, timeout: float) -> Dict[str, Any]:
    config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    settings = os.path.join(config, "settings.json")

    def act(repo: Repo, trusted: List[str], skills: Dict[str, Dict[str, Any]], backups: List[Dict[str, str]]) -> None:
        r = subprocess.run([claude, "plugin", "list", "--json"], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            raise MigrationError("claude plugin list --json failed")
        rows = json.loads(r.stdout)
        rows = rows.get("installed", []) if isinstance(rows, dict) else rows
        mine = [row for row in rows if isinstance(row, dict) and row.get("id") == PLUGIN_ID]
        enabled = [row for row in mine if row.get("enabled") is True and isinstance(row.get("installPath"), str)]
        enabled.sort(key=lambda row: row.get("scope") != "user")
        proven = []
        for name in trusted:
            if not mine:
                why = f"{PLUGIN} is not installed"
            elif not enabled:
                why = f"{PLUGIN} is installed but disabled"
            else:
                why = tree_mismatch(repo, LEGACY[name], os.path.join(enabled[0]["installPath"], "skills", LEGACY[name])) or ""
            if why:
                skills[name]["state"] = f"waiting, replacement not proven: {why}"
            else:
                proven.append(name)
        if proven:
            for name, state in set_claude_overrides(settings, proven, os.path.join(state_dir, "legacy-skill-backups"), backups).items():
                skills[name]["state"] = state
                skills[name]["setting"] = f"{settings} skillOverrides.{name}"

    return run("claude-code", repo_root, state_dir, head, log,
               os.path.join(config, "skills"), act)


def codex_migrate(repo_root: str, state_dir: str, head: str, log: Log, codex: str, skip: Set[str]) -> Dict[str, Any]:
    home = os.path.expanduser("~")
    codex_home = os.environ.get("CODEX_HOME") or os.path.join(home, ".codex")

    def act(repo: Repo, trusted: List[str], skills: Dict[str, Dict[str, Any]], backups: List[Dict[str, str]]) -> None:
        if PLUGIN in skip:
            for name in trusted:
                skills[name]["state"] = f"waiting, replacement not proven: {PLUGIN} is in codex-skip.txt"
            return
        server = AppServer([codex, "app-server", "--listen", "stdio://"], home)
        try:
            server.request("initialize", {"clientInfo": {"name": "expert-partners-plugin-sync",
                                                         "title": "plugin-sync legacy skills", "version": "1"}})
            server.notify("initialized")
            listed = codex_skills(server, home)
            todo: Dict[str, Tuple[str, str]] = {}
            for name in trusted:
                copy = skills[name]["copy"]
                skill = LEGACY[name]
                candidates = [s for s in listed if s.get("pluginId") == PLUGIN_ID
                              and os.path.basename(os.path.dirname(s["path"])) == skill]
                why = f"{PLUGIN} does not list {skill}" if not candidates else ""
                replacement = ""
                for s in candidates:
                    if s.get("enabled") is not True:
                        why = f"{PLUGIN} {skill} is disabled"
                        continue
                    why = tree_mismatch(repo, skill, os.path.dirname(s["path"])) or ""
                    if not why:
                        replacement = s["path"]
                        break
                old = [s for s in listed if same_file(s["path"], copy)]
                if why:
                    skills[name]["state"] = f"waiting, replacement not proven: {why}"
                elif not old:
                    skills[name]["state"] = "not listed by Codex, nothing to turn off"
                elif old[0].get("enabled") is False:
                    skills[name]["state"] = "already off"
                else:
                    todo[name] = (os.path.abspath(copy), replacement)
            if not todo:
                return
            raw = read_or_none(os.path.join(codex_home, "config.toml"))
            if raw is not None:
                backups.append(private_backup(os.path.join(state_dir, "legacy-skill-backups"), "codex-config.toml", raw))
            for name, (path, _) in todo.items():
                result = server.request("skills/config/write", {"path": path, "enabled": False})
                if not isinstance(result, dict) or result.get("effectiveEnabled") is not False:
                    skills[name]["state"] = "failed, Codex did not report the old copy as off"
                    continue
                skills[name]["state"] = "turned off"
                skills[name]["setting"] = f"codex skills/config/write path={path} enabled=false"
            after = codex_skills(server, home)
            for name, (path, replacement) in todo.items():
                if skills[name]["state"] != "turned off":
                    continue
                old = [s for s in after if same_file(s["path"], path)]
                new = [s for s in after if same_file(s["path"], replacement)]
                if old and old[0].get("enabled") is not False:
                    skills[name]["state"] = "failed, the old copy still reads back as on"
                elif not new or new[0].get("enabled") is not True:
                    skills[name]["state"] = "failed, the replacement no longer reads back as on"
        finally:
            server.close()

    return run("codex", repo_root, state_dir, head, log, os.path.join(home, ".agents", "skills"), act)


# The sync scripts load this file by path and call through this table.
MIGRATIONS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "claude-code": claude_migrate,
    "codex": codex_migrate,
}
