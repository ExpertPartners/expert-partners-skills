#!/usr/bin/env python3
"""Retire audited old user-tier helpers once the operating-doctrine plugin replaces them.

The intake and continuity helpers were once deployed as standalone copies
into ~/.claude/skills and ~/.agents/skills. Their useful behavior now ships in the operating-doctrine plugin
(verify-docs as part of research-before-guessing and continuity helpers in existing owners), but native plugin delivery cannot touch
the old copies, so they stay discoverable. codex-sync.sh and claude-code-sync.sh call this
after each full delivery run. For each old name it:

1. recognizes an exact audited deployment fingerprint. For the original four helpers
   only, its SKILL.md with a verified skill-deploy DEPLOYED COPY header removed may
   instead equal a committed version in this checkout's first-parent history. Anything
   else is left alone and reported;
2. proves the replacement: the operating-doctrine plugin is installed and enabled on this
   surface and every required owner's skill folder holds the bytes committed at HEAD;
3. retires only that old copy after a private, verified backup: Claude Code's old SKILL.md
   moves to a private archive without rewriting shared settings, and Codex uses
   Codex app-server skills/config/write with the exact SKILL.md path and enabled false
   (codex-rs app-server-protocol v2, read 2026-11-04);
4. checks the archive or reads the native setting back and writes a receipt.

The Claude archive preserves the exact original bytes, path and rollback information;
other files in that folder are untouched. No plugin cache is written. A failure is
reported in the receipt and fails the run, so the
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
import stat
import subprocess
import tempfile
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

MK = "expert-partners"
PLUGIN = "operating-doctrine"
PLUGIN_ID = f"{PLUGIN}@{MK}"
# Old user-tier name -> primary operating-doctrine owner; REQUIRES adds supporting owners.
LEGACY = {
    "intake": "intake",
    "new-project": "new-project",
    "session-home": "session-home",
    "verify-docs": "research-before-guessing",
    "handoff": "session-wrap",
    "park": "session-wrap",
    "resume-work": "session-wrap",
    "session-audit": "session-steward",
    "session-closeout": "session-wrap",
    "implement": "build-standard",
}
# Every required owner must be installed, enabled and byte-equal before retirement.
# These are existing canonical skills, not new copies of the legacy helpers.
REQUIRES = {
    "handoff": ("session-wrap", "code-block-routing"),
    "park": ("session-wrap", "session-steward"),
    "resume-work": ("session-wrap", "session-home", "code-block-routing"),
    "session-audit": ("session-steward", "session-wrap"),
    "session-closeout": ("session-wrap", "session-steward"),
    "implement": ("build-standard", "session-home", "code-block-routing", "session-wrap"),
}
# Exact whole-file SHA256s of the twenty previously deployed copies inspected by the
# migration audit. They include platform-specific renders absent from a shallow clone.
# This is a bounded compatibility input, never a name-only or header-only trust rule.
DEPLOYED_SHA256 = {
    "intake": {
        "1396a1db2775e46fe781867ff0e41d8367fb76bba6c11454be901b6da85ce669",
        "5ac7a43b3e4b2b060acb24b9ab24d8827df14e55aa83f9887ecce74b8764f3e4",
    },
    "new-project": {
        "fc9314ae70c7209505dcfc95418ef8a9311bc5905109b9cc8f92e25d49d07d22",
        "47022cf4aa60b910bce8a51b0571dd021e537be610756e53398f917713e5cd9a",
    },
    "session-home": {
        "4bd7bc488b0c24221a971c5ba57ad8bbb2fade0c13d03a6d75197e3100ff3b52",
        "6a2dabdb8bebf70b24ecc28bb2e3d99f7a0564f3c935a589095d41a4ca8a47c3",
    },
    "verify-docs": {
        "579ea9935ce9ed7d0bb013fae70bd663d2d9832e69e855f36316cafbca778423",
        "ca06b3f4506cf917faeed9c4587c2629f0deb216cbf63a75525f92ae3a811b08",
    },
    'handoff': {
        "1319436e39e6b3bf6fb3226e064d30154a5b463d2b4a969ba08bdfcf4906698b",
        "3b0fbd8f48f2262ee500ca8586dd72d9edf2b946a64b6b4a7a7b5d31c74dea90",
    },
    'park': {
        "e8f95b79c77c60cc61a176470c69b5c2152377eed84c2614563a9ae3766df235",
        "66f6ae8cc70a28951069a625c5db82f492a6a09799584f8d696ab8d65ddb8c7f",
    },
    'resume-work': {
        "785c57449d1ea47301434f8aaaea6bb8522416d76b40b97e8550eb034b296f5b",
        "177cab6c3dcca1221687c4753f9c7956b27167f309061bfb571c1716f2c6b939",
    },
    'session-audit': {
        "447886ead5aea9bce31541628e288b3faa88bd89d3649a9f353166ab36f6c51e",
        "94a2cd416c56dd44c109efdd7be989fd486bfa4a0b2bf3dd3b1781e95caddc4e",
    },
    'session-closeout': {
        "1a4ae080cdf4c0545b516cedc79f340aa53be7a035b679f0aeee15dc275b5858",
        "4fcb05cc3629e84b94ea36753b8cfb842d30d11d38981e6ee427256aa5ba3d1a",
    },
    'implement': {
        "1a5f7dcf567c5dd146a51b37ffc1361ba90deb87f7c72dc5e42ea3a25f875576",
        "c216f532ee15490e5a793ef50ee1880d66e981430faf13d2594ad120aa7dba24",
    },
}
HEADER = re.compile(
    rb"^# DEPLOYED COPY \(\d{4}-\d{2}-\d{2}, skill-deploy pipeline\): the canonical home is\n"
    rb"# (\S+) (\S+?SKILL\.md)\. Deployed at [^\n]+?\.\n"
    rb"# Edit the canonical copy first, then redeploy via tools/skill-deploy\.\n",
    re.M,
)
JUNK = {".DS_Store", "checksums.sha256"}
NOTE = ("Retires only recognized old user-tier copies after proving their replacements. "
        "Claude copies are privately archived without rewriting settings; Codex uses its native setting. "
        "Runtime use is unverified until a new or reloaded session lists the skills.")
LOCK_WAIT = 60.0
REQUEST_TIMEOUT = 60.0

Log = Callable[[str], None]


class MigrationError(Exception):
    pass


def replacements(name: str) -> Tuple[str, ...]:
    return REQUIRES.get(name, (LEGACY[name],))


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
    if not os.path.lexists(folder) or not os.path.lexists(path):
        return "absent", ""
    if os.path.islink(folder) or os.path.islink(path):
        return "unrecognized", "it is a symlink, not a copy this producer made"
    if not os.path.isfile(path):
        return "unrecognized", "it has no regular SKILL.md"
    with open(path, "rb") as f:
        data = f.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest in DEPLOYED_SHA256.get(name, set()):
        return "trusted", f"sha256:{digest}"
    if name in REQUIRES:
        return "unrecognized", f"its bytes match no audited deployment of {name}"
    source = f"skills/{name}/SKILL.md"
    m = HEADER.search(data)
    if m:
        if (m.group(1), m.group(2)) != (b"expert-partners-skills", source.encode()):
            return "unrecognized", "its DEPLOYED COPY header names another canonical home"
        data = data[:m.start()] + data[m.end():]
    blob = blob_id(data)
    if blob in repo.history_blobs(source):
        return "trusted", f"sha256:{digest}"
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


def claude_choices(settings: str) -> Dict[str, Any]:
    """Read existing choices only. A separate native writer owns this shared file."""
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
    return overrides


def archive_claude_copy(path: str, expected_sha256: str, backup_dir: str,
                        backups: List[Dict[str, str]]) -> Dict[str, str]:
    """Archive a single proven obsolete SKILL.md, leaving shared settings untouched.

    Re-check the moved inode and bytes. A concurrent replacement is restored without
    clobbering any new source path; both files and the original backup survive a conflict.
    """
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise MigrationError(f"{path} is no longer a regular file, left unchanged")
        data = source.read()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise MigrationError(f"{path} changed after classification, left unchanged")
    backup = private_backup(backup_dir, "claude-" + os.path.basename(os.path.dirname(path)), data)
    archive_dir = tempfile.mkdtemp(prefix="claude-retired-", dir=backup_dir)
    archived = os.path.join(archive_dir, "SKILL.md")
    backup.update({"source": path, "archive": archived, "original_mode": oct(stat.S_IMODE(before.st_mode))})
    manifest = os.path.join(archive_dir, "restore.json")
    backup["manifest"] = manifest
    # The per-run receipt may later report no work. Keep rollback metadata beside the
    # archived copy for its entire lifetime, not only in that replaceable receipt.
    manifest_bytes = (json.dumps(backup, indent=2) + "\n").encode("utf-8")
    fd = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as record:
        record.write(manifest_bytes)
        record.flush()
        os.fsync(record.fileno())
    if read_or_none(manifest) != manifest_bytes:
        raise MigrationError(f"{manifest} did not read back, original file left unchanged")
    backups.append(backup)
    os.rename(path, archived)
    moved = os.lstat(archived)
    matches = (stat.S_ISREG(moved.st_mode) and moved.st_dev == before.st_dev
               and moved.st_ino == before.st_ino)
    if matches:
        fd = os.open(archived, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as source:
            matches = source.read() == data
    if not matches:
        try:
            os.link(archived, path, follow_symlinks=False)
            restored = "restored the changed copy without overwriting any source file"
        except FileExistsError:
            restored = "a new source file exists; preserved both it and the moved copy"
        raise MigrationError(f"{path} changed during archive; {restored}; moved copy at {archived}")
    os.chmod(archived, 0o600)
    if os.path.lexists(path):
        return {"state": "attention, a new source copy appeared after archive", "archive": archived}
    return {"state": "archived", "archive": archived}


def restore_archive(backup: Dict[str, str]) -> None:
    """Restore verified original bytes without replacing an existing source path.

    A private temporary sibling and a no-clobber link publish the complete file at once.
    The original backup and archive remain available after rollback.
    """
    source = backup["source"]
    with open(backup["path"], "rb") as f:
        data = f.read()
    if hashlib.sha256(data).hexdigest() != backup["sha256"]:
        raise MigrationError("the rollback backup does not match its recorded SHA256")
    fd, temp = tempfile.mkstemp(prefix=".legacy-restore-", dir=os.path.dirname(source))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(temp, int(backup["original_mode"], 8))
        os.link(temp, source)
    finally:
        os.unlink(temp)


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
            self.proc.stdout.close()
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


def codex_choices(server: AppServer, cwd: str) -> Dict[str, bool]:
    """Read explicit per-path choices through the native API, without a TOML dependency."""
    result = server.request("config/read", {"cwd": cwd, "includeLayers": False})
    if not isinstance(result, dict) or not isinstance(result.get("config"), dict):
        raise MigrationError("codex app-server config/read returned an unexpected shape")
    skills = result["config"].get("skills", {})
    if skills is None:
        skills = {}
    if not isinstance(skills, dict) or not isinstance(skills.get("config", []), list):
        raise MigrationError("codex config/read skills.config is not a list")
    choices: Dict[str, bool] = {}
    for entry in skills.get("config", []):
        if isinstance(entry, dict) and isinstance(entry.get("path"), str) and isinstance(entry.get("enabled"), bool):
            choices[os.path.realpath(entry["path"])] = entry["enabled"]
    return choices


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
                skills[name] = {"copy": path, "matched_source": detail,
                                "source_sha256": detail.removeprefix("sha256:"),
                                "required_replacements": list(replacements(name))}
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
    attention = [n for n, row in skills.items()
                 if str(row.get("state", "")).startswith(("left alone", "attention"))]
    status = "failed" if failures else "waiting" if waiting else "attention" if attention else "ok"
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
                why = ""
                for replacement in replacements(name):
                    why = tree_mismatch(repo, replacement, os.path.join(enabled[0]["installPath"], "skills", replacement)) or ""
                    if why:
                        break
            if why:
                skills[name]["state"] = f"waiting, replacement not proven: {why}"
            else:
                proven.append(name)
        if proven:
            for name in proven:
                # Read immediately before retirement, but never rewrite this shared
                # settings file. A producer lock cannot coordinate unrelated writers.
                value = claude_choices(settings).get(name)
                if value == "off":
                    skills[name]["state"] = "already off"
                elif value is not None:
                    skills[name]["state"] = f"left alone, skillOverrides already sets it to {value!r}"
                else:
                    skills[name].update(archive_claude_copy(
                        skills[name]["copy"], skills[name]["source_sha256"],
                        os.path.join(state_dir, "legacy-skill-backups"), backups))

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
            choices = codex_choices(server, home)
            todo: Dict[str, Tuple[str, List[str]]] = {}
            for name in trusted:
                copy = skills[name]["copy"]
                why = ""
                replacement_paths = []
                for skill in replacements(name):
                    candidates = [s for s in listed if s.get("pluginId") == PLUGIN_ID
                                  and os.path.basename(os.path.dirname(s["path"])) == skill]
                    why = f"{PLUGIN} does not list {skill}" if not candidates else ""
                    replacement = ""
                    for candidate in candidates:
                        if candidate.get("enabled") is not True:
                            why = f"{PLUGIN} {skill} is disabled"
                            continue
                        why = tree_mismatch(repo, skill, os.path.dirname(candidate["path"])) or ""
                        if not why:
                            replacement = candidate["path"]
                            break
                    if why:
                        break
                    replacement_paths.append(replacement)
                old = [s for s in listed if same_file(s["path"], copy)]
                if why:
                    skills[name]["state"] = f"waiting, replacement not proven: {why}"
                elif not old:
                    skills[name]["state"] = "not listed by Codex, nothing to turn off"
                elif old[0].get("enabled") is False:
                    skills[name]["state"] = "already off"
                elif choices.get(os.path.realpath(copy)) is True:
                    skills[name]["state"] = "left alone, skills.config explicitly sets enabled=true"
                else:
                    todo[name] = (os.path.abspath(copy), replacement_paths)
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
            for name, (path, replacement_paths) in todo.items():
                if skills[name]["state"] != "turned off":
                    continue
                old = [s for s in after if same_file(s["path"], path)]
                if old and old[0].get("enabled") is not False:
                    skills[name]["state"] = "failed, the old copy still reads back as on"
                else:
                    for replacement in replacement_paths:
                        new = [s for s in after if same_file(s["path"], replacement)]
                        if not new or new[0].get("enabled") is not True:
                            skills[name]["state"] = "failed, a required replacement no longer reads back as on"
                            break
        finally:
            server.close()

    return run("codex", repo_root, state_dir, head, log, os.path.join(home, ".agents", "skills"), act)


# The sync scripts load this file by path and call through this table.
MIGRATIONS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "claude-code": claude_migrate,
    "codex": codex_migrate,
}
