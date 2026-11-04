#!/usr/bin/env python3
"""Plugin drift check: publication, delivery, enabled state and runtime use, per surface.

Every surface gets one record per plugin, and each record keeps four questions apart.

  publication  What main publishes: the version, a content fingerprint (the git tree id of
               the plugin folder) and the source commit. A later commit that leaves a plugin
               folder alone keeps the same fingerprint, so it is not new work for any surface.
  delivery     What the surface holds, judged on the strongest evidence it exposes:
                 delivered   installed bytes, or a human-verified receipt, match the fingerprint
                 pending     a local client differs and its deadline has not passed
                 behind      a local client holds other content past its deadline
                 missing     a local client has not installed the plugin past its deadline
                 unverified  some evidence, none of it proof (version only, or a cloud cache copy
                             that matches main)
                 stale       the newest destination evidence (installed bytes or a receipt)
                             describes older content than main publishes
                 unknown     no evidence about the destination (no receipt, inventory unreadable,
                             or only a local cache copy older than main)
                 skipped     excluded on purpose by codex-skip.txt
  enabled      enabled, disabled or unknown. A disabled plugin never counts as in use.
  runtime      verified only by a runtime receipt naming the published fingerprint, stale when
               the receipt names older content, otherwise unverified.

Surfaces:
  claude-code  installed_plugins.json, the installed bytes, and enabledPlugins in settings.json
  codex        `codex plugin list --marketplace expert-partners --json` and the documented
               install cache ~/.codex/plugins/cache/expert-partners/<plugin>/<version>/
  claude.ai    a human-verified receipt, claude-ai-last-sync.json, is the only proof. The copies
               Claude Code downloads into ~/.claude/plugins/synced are supporting evidence: a
               fresh download proves neither server inventory nor a loaded conversation, and an
               old one only shows that this local client has not refreshed. Without a receipt,
               an old cache marks the supporting evidence stale and cloud delivery unknown.
  chatgpt      a human-verified receipt, chatgpt-last-sync.json. No read API is documented
               (checked 2026-10-13), so a missing receipt is reported as unknown.

Receipts live in ~/.claude/plugin-sync/. This check only reads them. It never writes,
replaces or synthesizes one. A cloud receipt looks like this; older receipts carry only commit:
  {"commit": "<sha>", "observed_at": "2026-11-04T08:00:00Z", "verified_by": "<person>",
   "plugins": {"<name>": {"version": "...", "fingerprint": "<tree id>", "enabled": true}}}
runtime-receipts.json records a session that actually loaded a plugin:
  {"surfaces": {"<surface>": {"<name>": {"fingerprint": "<tree id>", "observed_at": "...",
   "verified_by": "..."}}}}

Deadlines: a record that is not delivered has a pending_since time. It starts at the last
commit that changed that plugin's folder, never the latest repo commit. drift-state.json keeps
it while the record stays undelivered, so a stream of pushes never postpones it. Local clients
get no grace. Cloud surfaces get 24 hours.

Exit status: 0 verified; 3 unverified (nothing behind, but some state is unknown, stale,
unverified, pending or disabled, or runtime use is unproven); 2 behind (a local client is
behind or missing a plugin); 1 the check itself failed.

Run: drift-check.py            reads GitHub, prints the JSON report, records deadlines, and
                               updates the existing open Job Tracker row (never adds one)
     drift-check.py --dry-run  the same reads; prints the planned row write, writes nothing
     drift-check.py --offline  reads publication from the local checkout (--repo, --ref); no
                               GitHub, no Google credentials, no writes of any kind
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Protocol

REPO = "ExpertPartners/expert-partners-skills"
MARKETPLACE = "expert-partners"
MARKETPLACE_FILE = ".claude-plugin/marketplace.json"
HOME = os.path.expanduser("~")
CODEX = os.environ.get("CODEX_BIN", "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex")
# The Sheet is found by its title at run time. This repo is public, so no Drive file ID lives here.
SHEET_TITLE = "Job Tracker"
TAB = "Untitled"
JOB = "Plugins are behind the skills repo"
KEY = os.path.join(HOME, ".openclaw/.secrets/service-account.json")
SUBJECT = "allison@expertpartners.com"
GRACE_SECONDS = 24 * 3600
LOCAL_GRACE_SECONDS = 0
RECEIPT_DIR = os.path.join(".claude", "plugin-sync")
STATE_FILE = "drift-state.json"
SCHEMA = "plugin-drift-check/2"

LABELS = {"claude-code": "Claude Code", "codex": "Codex",
          "claude.ai": "claude.ai (Cowork and chat)", "chatgpt": "ChatGPT"}
GRACE = {"claude-code": LOCAL_GRACE_SECONDS, "codex": LOCAL_GRACE_SECONDS,
         "claude.ai": GRACE_SECONDS, "chatgpt": GRACE_SECONDS}
RECEIPTS = {"claude.ai": "claude-ai-last-sync.json", "chatgpt": "chatgpt-last-sync.json"}
EXIT = {"verified": 0, "behind": 2, "unverified": 3}

DeliveryState = Literal["delivered", "pending", "behind", "missing", "unverified", "stale", "unknown", "skipped"]
EnabledState = Literal["enabled", "disabled", "unknown"]
RuntimeState = Literal["verified", "unverified", "stale"]
Verification = Literal["verified", "unverified", "behind"]
Judgment = tuple[DeliveryState, str, str]
Runner = Callable[[list[str], int], tuple[int, str, str]]

# googleapiclient is untyped, so its service objects are Any.
Service = Any


def run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, "", str(e)
    return r.returncode, r.stdout, r.stderr


def iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: str) -> float:
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.timestamp()


def short(sha: str | None) -> str:
    return (sha or "unknown")[:7]


def versions_from_marketplace(raw: str) -> dict[str, str]:
    d = json.loads(raw)
    return {p["name"]: p.get("version", "") for p in d.get("plugins", [])}


def plugins_from_marketplace(raw: str) -> dict[str, tuple[str, str]]:
    """{plugin: (version, repo-relative folder)}. The folder is empty for a non-path source."""
    out: dict[str, tuple[str, str]] = {}
    for p in json.loads(raw).get("plugins", []):
        src = p.get("source")
        path = src[2:] if isinstance(src, str) and src.startswith("./") else (src if isinstance(src, str) else "")
        out[str(p["name"])] = (str(p.get("version", "")), path.rstrip("/"))
    return out


def _object_id(kind: str, data: bytes) -> str:
    return hashlib.sha1(f"{kind} {len(data)}\0".encode() + data).hexdigest()


def git_tree_id(path: str) -> str | None:
    """The git tree id of a folder, computed from its bytes the way git stores it, so an
    installed copy compares directly with the published plugin folder. None when the
    folder is missing or holds no files."""
    if not os.path.isdir(path):
        return None
    entries: list[tuple[bytes, bytes, bytes]] = []
    for name in os.listdir(path):
        if name == ".git":
            continue
        full = os.path.join(path, name)
        st = os.lstat(full)
        if stat.S_ISLNK(st.st_mode):
            mode, oid = b"120000", _object_id("blob", os.fsencode(os.readlink(full)))
        elif stat.S_ISDIR(st.st_mode):
            sub = git_tree_id(full)
            if sub is None:  # git keeps no empty folders
                continue
            mode, oid = b"40000", sub
        elif stat.S_ISREG(st.st_mode):
            with open(full, "rb") as fh:
                oid = _object_id("blob", fh.read())
            mode = b"100755" if st.st_mode & stat.S_IXUSR else b"100644"
        else:
            continue
        raw = os.fsencode(name)
        # git orders a folder as if its name ended in a slash
        entries.append((raw + (b"/" if mode == b"40000" else b""), mode + b" " + raw + b"\0", bytes.fromhex(oid)))
    if not entries:
        return None
    entries.sort()
    return _object_id("tree", b"".join(head + oid for _, head, oid in entries))


# ---------------------------------------------------------------- publication


class Source(Protocol):
    name: str

    def head(self) -> tuple[str, float]: ...

    def read(self, commit: str, path: str) -> str: ...

    def tree_ids(self, commit: str, folder: str) -> dict[str, str]: ...

    def changed_at(self, commit: str, path: str) -> float | None: ...


class GitHubSource:
    """Publication as GitHub serves main."""
    name = "github"

    def __init__(self, runner: Runner = run) -> None:
        self.runner = runner

    def _api(self, *args: str) -> str:
        rc, out, err = self.runner(["gh", "api", *args], 60)
        if rc != 0:
            raise RuntimeError(f"cannot read {args[-1]} from GitHub: {err.strip()[:200]}")
        return out

    def head(self) -> tuple[str, float]:
        sha, date = self._api(f"repos/{REPO}/commits/main", "--jq", '.sha + " " + .commit.committer.date').split()
        return sha, parse_time(date)

    def read(self, commit: str, path: str) -> str:
        return self._api("-H", "Accept: application/vnd.github.raw", f"repos/{REPO}/contents/{path}?ref={commit}")

    def tree_ids(self, commit: str, folder: str) -> dict[str, str]:
        listing = json.loads(self._api(f"repos/{REPO}/contents/{folder}?ref={commit}"))
        return {str(e["name"]): str(e["sha"]) for e in listing if isinstance(e, dict) and e.get("type") == "dir"}

    def changed_at(self, commit: str, path: str) -> float | None:
        out = self._api(f"repos/{REPO}/commits?sha={commit}&path={path}&per_page=1",
                        "--jq", ".[0].commit.committer.date // empty").strip()
        return parse_time(out) if out else None


class GitSource:
    """Publication as a local checkout holds it, for the offline mode."""
    name = "git"

    def __init__(self, repo: str, ref: str, runner: Runner = run) -> None:
        self.repo, self.ref, self.runner = repo, ref, runner

    def _git(self, *args: str) -> str:
        rc, out, err = self.runner(["git", "-C", self.repo, *args], 60)
        if rc != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {err.strip()[:200]}")
        return out

    def head(self) -> tuple[str, float]:
        sha, at = self._git("log", "-1", "--format=%H %ct", self.ref).split()
        return sha, float(at)

    def read(self, commit: str, path: str) -> str:
        return self._git("show", f"{commit}:{path}")

    def tree_ids(self, commit: str, folder: str) -> dict[str, str]:
        out: dict[str, str] = {}
        for line in self._git("ls-tree", f"{commit}:{folder}").splitlines():
            meta, _, name = line.partition("\t")
            parts = meta.split()
            if len(parts) == 3 and parts[1] == "tree":
                out[name] = parts[2]
        return out

    def changed_at(self, commit: str, path: str) -> float | None:
        out = self._git("log", "-1", "--format=%ct", commit, "--", path).strip()
        return float(out) if out else None


@dataclass
class Published:
    version: str
    path: str
    fingerprint: str | None
    published_at: float | None


@dataclass
class Publication:
    source: str
    source_commit: str
    committed_at: float
    plugins: dict[str, Published]


def fingerprints_at(source: Source, commit: str, paths: dict[str, str]) -> dict[str, str]:
    """{plugin: tree id} at a commit, one listing per parent folder."""
    listings: dict[str, dict[str, str]] = {}
    out: dict[str, str] = {}
    for name, path in paths.items():
        if not path:
            continue
        parent, _, base = path.rpartition("/")
        if parent not in listings:
            listings[parent] = source.tree_ids(commit, parent)
        if base in listings[parent]:
            out[name] = listings[parent][base]
    return out


def load_publication(source: Source) -> Publication:
    sha, at = source.head()
    entries = plugins_from_marketplace(source.read(sha, MARKETPLACE_FILE))
    fps = fingerprints_at(source, sha, {n: p for n, (_, p) in entries.items()})
    plugins = {n: Published(v, p, fps.get(n), source.changed_at(sha, p) if p else None)
               for n, (v, p) in entries.items()}
    return Publication(source.name, sha, at, plugins)


# ---------------------------------------------------------------- evidence


@dataclass
class Installed:
    version: str
    path: str | None
    enabled: EnabledState


@dataclass
class CacheCopy:
    folder: str
    version: str
    fetched_at: float
    fingerprint: str | None


@dataclass
class ReceiptEntry:
    version: str | None
    fingerprint: str | None
    enabled: bool | None


@dataclass
class Receipt:
    path: str
    commit: str | None
    observed_at: str | None
    verified_by: str | None
    plugins: dict[str, ReceiptEntry]


def read_json(path: str) -> tuple[object, str]:
    """(data, problem). problem is empty on success, otherwise says why there is no data."""
    if not os.path.exists(path):
        return None, f"{path} not found"
    try:
        with open(path, encoding="utf-8") as fh:
            data: object = json.load(fh)
        return data, ""
    except (OSError, ValueError) as e:
        return None, f"{path} unreadable: {e}"


def _text(d: dict[Any, Any], key: str) -> str | None:
    v = d.get(key)
    return v if isinstance(v, str) and v else None


def git_head(path: str, runner: Runner = run) -> str | None:
    rc, out, _ = runner(["git", "-C", path, "rev-parse", "HEAD"], 60)
    return out.strip() if rc == 0 else None


def claude_code_inventory(home: str) -> tuple[dict[str, Installed] | None, str]:
    data, problem = read_json(os.path.join(home, ".claude/plugins/installed_plugins.json"))
    if not isinstance(data, dict):
        return None, problem or "installed_plugins.json has no plugins object"
    settings, _ = read_json(os.path.join(home, ".claude/settings.json"))
    flags = settings.get("enabledPlugins") if isinstance(settings, dict) else None
    flags = flags if isinstance(flags, dict) else {}
    out: dict[str, Installed] = {}
    plugins = data.get("plugins")
    for key, entries in (plugins.items() if isinstance(plugins, dict) else []):
        name, _, mk = str(key).partition("@")
        if mk != MARKETPLACE or not isinstance(entries, list) or not entries:
            continue
        dicts = [e for e in entries if isinstance(e, dict)]
        if not dicts:
            continue
        entry = next((e for e in dicts if e.get("scope") == "user"), dicts[0])
        flag = flags.get(key)
        enabled: EnabledState = "enabled" if flag is True else "disabled" if flag is False else "unknown"
        out[name] = Installed(_text(entry, "version") or "", _text(entry, "installPath"), enabled)
    return out, "installed_plugins.json"


def parse_codex_json(text: str, home: str) -> dict[str, Installed] | None:
    """Installed expert-partners plugins from `codex plugin list --json`, or None if unparseable."""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("installed"), list):
        return None
    out: dict[str, Installed] = {}
    for e in data["installed"]:
        if not isinstance(e, dict) or e.get("marketplaceName", MARKETPLACE) != MARKETPLACE or e.get("installed") is False:
            continue
        name, version = _text(e, "name"), _text(e, "version") or ""
        if not name:
            continue
        flag = e.get("enabled")
        enabled: EnabledState = "enabled" if flag is True else "disabled" if flag is False else "unknown"
        cache = os.path.join(home, ".codex/plugins/cache", MARKETPLACE, name, version) if version else None
        out[name] = Installed(version, cache, enabled)
    return out


def parse_codex_inventory(text: str) -> dict[str, tuple[str | None, EnabledState]]:
    """{plugin: (version or None when not installed, enabled)} from the plain `codex plugin list`."""
    out: dict[str, tuple[str | None, EnabledState]] = {}
    inblock = "Marketplace `" not in text
    for line in text.splitlines():
        if line.startswith("Marketplace `"):
            inblock = line.startswith(f"Marketplace `{MARKETPLACE}`")
            continue
        if inblock and "@" + MARKETPLACE in line:
            name = line.split()[0].split("@")[0]
            if "not installed" in line:
                out[name] = (None, "unknown")
            else:
                m = re.search(r"installed, (enabled|disabled)\s+(\S+)", line)
                out[name] = (m.group(2), "enabled" if m.group(1) == "enabled" else "disabled") if m else ("", "unknown")
    return out


def parse_codex_list(text: str) -> dict[str, str | None]:
    """{plugin: version or None} for our marketplace block of `codex plugin list`."""
    return {n: v for n, (v, _) in parse_codex_inventory(text).items()}


def codex_bin() -> str:
    return CODEX if os.access(CODEX, os.X_OK) else (shutil.which("codex") or CODEX)


def codex_inventory(home: str, runner: Runner, binary: str) -> tuple[dict[str, Installed] | None, str]:
    """Only the expert-partners marketplace is listed. JSON first; the plain scoped listing
    covers a Codex CLI that predates --json, and nothing else is ever listed."""
    cmd = [binary, "plugin", "list", "--marketplace", MARKETPLACE]
    rc, out, err = runner(cmd + ["--json"], 120)
    if rc == 0:
        parsed = parse_codex_json(out, home)
        if parsed is not None:
            return parsed, " ".join(cmd[1:] + ["--json"])
    rc, out, err2 = runner(cmd, 120)
    if rc != 0:
        return None, f"codex plugin list failed: {(err2 or err).strip()[:200]}"
    inv = {n: Installed(v, os.path.join(home, ".codex/plugins/cache", MARKETPLACE, n, v) if v else None, e)
           for n, (v, e) in parse_codex_inventory(out).items() if v is not None}
    return inv, " ".join(cmd[1:])


def synced_copies(home: str) -> dict[str, list[CacheCopy]]:
    """Every copy Claude Code holds in ~/.claude/plugins/synced, grouped by plugin name.
    Older generations of one server plugin can sit beside the newest, so all are kept."""
    out: dict[str, list[CacheCopy]] = {}
    for pj in sorted(glob.glob(os.path.join(home, ".claude/plugins/synced/*/*/.claude-plugin/plugin.json"))):
        data, _ = read_json(pj)
        if not isinstance(data, dict) or not _text(data, "name"):
            continue
        folder = os.path.dirname(os.path.dirname(pj))
        copy = CacheCopy(folder, _text(data, "version") or "", os.path.getmtime(pj), git_tree_id(folder))
        out.setdefault(str(data["name"]), []).append(copy)
    return out


def parse_receipt(path: str, data: object) -> Receipt | None:
    if not isinstance(data, dict):
        return None
    plugins: dict[str, ReceiptEntry] = {}
    raw = data.get("plugins")
    for name, e in (raw.items() if isinstance(raw, dict) else []):
        if isinstance(e, dict):
            flag = e.get("enabled")
            plugins[str(name)] = ReceiptEntry(_text(e, "version"), _text(e, "fingerprint"),
                                              flag if isinstance(flag, bool) else None)
    return Receipt(path, _text(data, "commit"), _text(data, "observed_at"), _text(data, "verified_by"), plugins)


def read_receipt(home: str, filename: str) -> tuple[Receipt | None, str]:
    path = os.path.join(home, RECEIPT_DIR, filename)
    data, problem = read_json(path)
    receipt = parse_receipt(path, data) if not problem else None
    return receipt, problem or ("" if receipt else f"{path} is not a receipt object")


def runtime_receipts(home: str) -> dict[str, dict[str, str]]:
    """{surface: {plugin: fingerprint a session was seen to load}}."""
    data, _ = read_json(os.path.join(home, RECEIPT_DIR, "runtime-receipts.json"))
    out: dict[str, dict[str, str]] = {}
    surfaces = data.get("surfaces") if isinstance(data, dict) else None
    for surface, plugins in (surfaces.items() if isinstance(surfaces, dict) else []):
        if isinstance(plugins, dict):
            out[str(surface)] = {str(n): fp for n, e in plugins.items()
                                 if isinstance(e, dict) and (fp := _text(e, "fingerprint"))}
    return out


# ---------------------------------------------------------------- judgment


@dataclass
class Record:
    surface: str
    plugin: str
    delivery: DeliveryState
    evidence: str
    detail: str = ""
    version: str | None = None
    fingerprint: str | None = None
    enabled: EnabledState = "unknown"
    runtime: RuntimeState = "unverified"
    runtime_detail: str = "no runtime receipt"
    supporting: dict[str, object] = field(default_factory=dict)
    pending_since: float | None = None
    due_at: float | None = None
    overdue: bool = False

    def as_json(self) -> dict[str, object]:
        return {"delivery": {"state": self.delivery, "evidence": self.evidence, "detail": self.detail,
                             "version": self.version, "fingerprint": self.fingerprint},
                "enabled": self.enabled,
                "runtime": {"state": self.runtime, "detail": self.runtime_detail},
                "supporting": self.supporting or None,
                "deadline": None if self.pending_since is None else
                {"pending_since": iso(self.pending_since), "due_at": iso(self.due_at), "overdue": self.overdue}}


def judge_local(want: Published, version: str, fingerprint: str | None) -> Judgment:
    """A local install, before its deadline turns behind into pending."""
    if fingerprint and want.fingerprint and fingerprint == want.fingerprint:
        return "delivered", "installed bytes", "installed bytes match the published folder"
    if version != want.version:
        return "behind", "installed version", f"has {version or 'no version'}, main publishes {want.version}"
    if fingerprint is None:
        return "unverified", "version only", "installed bytes could not be read"
    if want.fingerprint is None:
        return "unverified", "version only", "the published fingerprint is unknown"
    return "unverified", "installed bytes", "same version, but the installed bytes differ from the published folder"


def judge_receipt(receipt: Receipt, name: str, want: Published, at_commit: dict[str, str] | None) -> Judgment:
    entry = receipt.plugins.get(name)
    who = f"receipt ({receipt.verified_by})" if receipt.verified_by else "receipt"
    when = f"observed {receipt.observed_at}" if receipt.observed_at else "observation time not recorded"
    if entry and entry.fingerprint:
        fp: str | None = entry.fingerprint
    elif receipt.commit:
        if at_commit is None:
            return "unknown", who, f"receipt commit {short(receipt.commit)} could not be read"
        fp = at_commit.get(name)
        if fp is None:
            return "stale", who, f"receipt commit {short(receipt.commit)} predates this plugin"
    else:
        fp = None
    if fp is None:
        if entry and entry.version:
            return "unverified", f"{who}, version only", f"receipt names version {entry.version}, no content"
        return "unknown", who, "receipt does not name this plugin"
    if want.fingerprint and fp == want.fingerprint:
        return "delivered", who, f"receipt content matches main; {when}"
    return "stale", who, f"receipt describes older content than main publishes; {when}"


def cache_matches(want: Published, copies: list[CacheCopy]) -> bool:
    newest = max(copies, key=lambda c: c.fetched_at)
    return bool(want.fingerprint) and newest.fingerprint == want.fingerprint


def cache_support(want: Published, copies: list[CacheCopy]) -> dict[str, object]:
    newest = max(copies, key=lambda c: c.fetched_at)
    return {"source": "local synced cache, supporting evidence only",
            "state": "current" if cache_matches(want, copies) else "stale",
            "copies": len(copies), "versions": sorted({c.version for c in copies}),
            "newest_version": newest.version, "newest_fetched_at": iso(newest.fetched_at),
            "newest_matches_published": cache_matches(want, copies)}


def judge_cache(want: Published, copies: list[CacheCopy]) -> Judgment:
    """Cloud delivery when there is no receipt. The cache shows only what this local client
    last downloaded, so an old copy is stale supporting evidence, never stale cloud delivery."""
    if not copies:
        return "unknown", "none", "no receipt and no local cache copy"
    newest = max(copies, key=lambda c: c.fetched_at)
    extra = f"; {len(copies)} cached generations" if len(copies) > 1 else ""
    if cache_matches(want, copies):
        return ("unverified", "local cache, supporting only",
                "no receipt; a fresh local copy proves neither server inventory nor a loaded conversation" + extra)
    return ("unknown", "local cache, supporting only",
            f"no receipt; the newest local copy is {newest.version}, which shows only that this client "
            f"has not refreshed, not what the server holds{extra}")


def local_records(surface: str, pub: Publication, inv: dict[str, Installed] | None, detail: str,
                  skip: set[str]) -> list[Record]:
    out: list[Record] = []
    missing = set(missing_in_claude_code(pub.plugins, inv)) if inv is not None else set()
    for name, want in sorted(pub.plugins.items()):
        if name in skip:
            out.append(Record(surface, name, "skipped", "codex-skip.txt", "excluded on purpose"))
        elif inv is None:
            out.append(Record(surface, name, "unknown", "none", detail))
        elif name in missing:
            out.append(Record(surface, name, "missing", "inventory", f"not installed; main publishes {want.version}"))
        else:
            have = inv[name]
            fp = git_tree_id(have.path) if have.path else None
            state, evidence, why = judge_local(want, have.version, fp)
            out.append(Record(surface, name, state, evidence, why, have.version, fp, have.enabled))
    return out


def cloud_records(surface: str, pub: Publication, receipt: Receipt | None, problem: str,
                  at_commit: dict[str, str] | None, copies: dict[str, list[CacheCopy]] | None) -> list[Record]:
    out: list[Record] = []
    for name, want in sorted(pub.plugins.items()):
        mine = copies.get(name, []) if copies is not None else []
        support = cache_support(want, mine) if mine else {}
        enabled: EnabledState = "unknown"
        if receipt is not None:
            state, evidence, why = judge_receipt(receipt, name, want, at_commit)
            entry = receipt.plugins.get(name)
            if entry and entry.enabled is not None:
                enabled = "enabled" if entry.enabled else "disabled"
        elif copies is not None:
            state, evidence, why = judge_cache(want, mine)
            why = f"{problem}; {why}" if problem else why
        else:
            state, evidence, why = "unknown", "none", f"no receipt: {problem}"
        out.append(Record(surface, name, state, evidence, why, enabled=enabled, supporting=support))
    return out


def judge_runtime(rec: Record, want: Published, seen: dict[str, str]) -> None:
    fp = seen.get(rec.plugin)
    if fp is None:
        return
    if want.fingerprint and fp == want.fingerprint:
        rec.runtime, rec.runtime_detail = "verified", "a session loaded the published content"
    else:
        rec.runtime, rec.runtime_detail = "stale", "the last session seen loaded older content"


def apply_deadline(rec: Record, want: Published, grace: int, now: float, state: dict[str, float]) -> None:
    """The clock starts when the plugin's current content was published and, once recorded,
    holds while the record stays undelivered. A later unrelated commit never moves it."""
    key = f"{rec.surface}/{rec.plugin}"
    if rec.delivery in ("delivered", "skipped"):
        state.pop(key, None)
        return
    known = [t for t in (state.get(key), want.published_at) if t is not None]
    since = min(known) if known else now
    state[key] = since
    rec.pending_since, rec.due_at = since, since + grace
    rec.overdue = now >= rec.due_at
    if rec.delivery in ("behind", "missing") and not rec.overdue:
        rec.delivery = "pending"


def is_complete(rec: Record) -> bool:
    if rec.delivery == "skipped":
        return True
    return rec.delivery == "delivered" and rec.enabled == "enabled" and rec.runtime == "verified"


def summary_lines(records: list[Record]) -> list[str]:
    """Plain-words lines, empty only when every record is verified end to end."""
    lines: list[str] = []
    for r in records:
        label = LABELS[r.surface]
        if r.delivery in ("behind", "missing"):
            lines.append(f"{label} {r.plugin}: {r.detail}")
    for surface in LABELS:
        mine = [r for r in records if r.surface == surface]
        counts: dict[str, int] = {}
        for r in mine:
            if r.delivery not in ("delivered", "skipped", "behind", "missing"):
                counts[r.delivery] = counts.get(r.delivery, 0) + 1
        if counts:
            lines.append(f"{LABELS[surface]} delivery " + ", ".join(f"{n} {s}" for s, n in sorted(counts.items())))
        off = sorted(r.plugin for r in mine if r.delivery != "skipped" and r.enabled != "enabled")
        if off:
            lines.append(f"{LABELS[surface]} not confirmed enabled: {', '.join(off)}")
    unproven = [r for r in records if r.delivery != "skipped" and r.runtime != "verified"]
    if unproven:
        lines.append(f"runtime use unproven for {len(unproven)} of "
                     f"{len([r for r in records if r.delivery != 'skipped'])} plugin records")
    return lines


def summarize(records: list[Record]) -> tuple[Verification, dict[str, object]]:
    verification: Verification = (
        "behind" if any(r.delivery in ("behind", "missing") for r in records)
        else "verified" if all(is_complete(r) for r in records) else "unverified")

    def tally(values: list[str]) -> dict[str, int]:
        out: dict[str, int] = {}
        for v in values:
            out[v] = out.get(v, 0) + 1
        return dict(sorted(out.items()))

    active = [r for r in records if r.delivery != "skipped"]
    return verification, {
        "verification": verification,
        "publication": "published",
        "delivery": {s: tally([r.delivery for r in records if r.surface == s]) for s in LABELS},
        "enabled": tally([r.enabled for r in active]),
        "runtime": tally([r.runtime for r in active]),
        "overdue": [f"{r.surface}/{r.plugin}: {r.delivery}" for r in records if r.overdue],
    }


@dataclass
class Outcome:
    report: dict[str, object]
    state: dict[str, float]
    lines: list[str]
    verification: Verification
    head: str


def skip_list() -> set[str]:
    sf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codex-skip.txt")
    if not os.path.exists(sf):
        return set()
    with open(sf, encoding="utf-8") as fh:
        return {line.strip() for line in fh if line.strip() and not line.startswith("#")}


def build_report(source: Source, home: str, now: float, state: dict[str, float], runner: Runner = run,
                 codex: str | None = None, skip: set[str] | None = None) -> Outcome:
    pub = load_publication(source)
    state = dict(state)
    surfaces: dict[str, dict[str, object]] = {}
    records: list[Record] = []

    def snapshot(path: str) -> dict[str, object]:
        sha = git_head(path, runner)
        return {"commit": sha, "state": "unknown" if sha is None else "current" if sha == pub.source_commit else "stale",
                "note": "the marketplace snapshot commit is context; delivery is judged per plugin"}

    cc, cc_detail = claude_code_inventory(home)
    cx, cx_detail = codex_inventory(home, runner, codex or codex_bin())
    groups: list[tuple[str, list[Record], dict[str, object] | None, str]] = [
        ("claude-code", local_records("claude-code", pub, cc, cc_detail, set()),
         snapshot(os.path.join(home, ".claude/plugins/marketplaces", MARKETPLACE)), cc_detail),
        ("codex", local_records("codex", pub, cx, cx_detail, skip if skip is not None else skip_list()),
         snapshot(os.path.join(home, ".codex/.tmp/marketplaces", MARKETPLACE)), cx_detail),
    ]
    copies = synced_copies(home)
    for surface, filename in RECEIPTS.items():
        receipt, problem = read_receipt(home, filename)
        at_commit: dict[str, str] | None = None
        if receipt and receipt.commit:
            try:
                at_commit = fingerprints_at(source, receipt.commit, {n: p.path for n, p in pub.plugins.items()})
            except RuntimeError:
                at_commit = None
        recs = cloud_records(surface, pub, receipt, problem, at_commit, copies if surface == "claude.ai" else None)
        evidence = receipt.path if receipt else f"no receipt ({problem})"
        groups.append((surface, recs, None, evidence))

    seen = runtime_receipts(home)
    for surface, recs, snap, evidence in groups:
        for r in recs:
            judge_runtime(r, pub.plugins[r.plugin], seen.get(surface, {}))
            apply_deadline(r, pub.plugins[r.plugin], GRACE[surface], now, state)
        records.extend(recs)
        surfaces[surface] = {"label": LABELS[surface], "evidence": evidence, "snapshot": snap,
                             "plugins": {r.plugin: r.as_json() for r in recs}}

    verification, summary = summarize(records)
    report: dict[str, object] = {
        "schema": SCHEMA,
        "checked_at": iso(now),
        "publication": {"source": pub.source, "source_commit": pub.source_commit,
                        "committed_at": iso(pub.committed_at),
                        "plugins": {n: {"state": "published", "version": p.version, "fingerprint": p.fingerprint,
                                        "published_at": iso(p.published_at)} for n, p in sorted(pub.plugins.items())}},
        "surfaces": surfaces,
        "summary": summary,
    }
    return Outcome(report, state, summary_lines(records), verification, pub.source_commit)


def missing_in_claude_code(head_versions: Mapping[str, object], installed: Mapping[str, object]) -> list[str]:
    """Plugins in the repo that the client has not installed from the marketplace."""
    return sorted(n for n in head_versions if n not in installed)


def load_state(home: str) -> dict[str, float]:
    data, _ = read_json(os.path.join(home, RECEIPT_DIR, STATE_FILE))
    pending = data.get("pending_since") if isinstance(data, dict) else None
    return {str(k): float(v) for k, v in (pending.items() if isinstance(pending, dict) else [])
            if isinstance(v, (int, float))}


def save_state(home: str, state: dict[str, float]) -> None:
    folder = os.path.join(home, RECEIPT_DIR)
    os.makedirs(folder, exist_ok=True)
    tmp = os.path.join(folder, STATE_FILE + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"pending_since": dict(sorted(state.items()))}, fh, indent=1)
    os.replace(tmp, os.path.join(folder, STATE_FILE))


# ---------------------------------------------------------------- legacy Job Tracker row


def find_sheet_id(drive: Service, title: str) -> str:
    """Find the one Sheet whose name is title behind its bracketed tag and version, such as
    [HQ][V1.0] Job Tracker. Zero or several matches stop the check, it never guesses."""
    q = f"name contains '{title}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
    found: list[dict[str, str]] = drive.files().list(q=q, fields="files(id,name)", pageSize=50, supportsAllDrives=True,
                                                     includeItemsFromAllDrives=True).execute().get("files", [])
    hits = [f for f in found if re.fullmatch(r"(\[[^\]]+\])+ " + re.escape(title), f["name"])]
    if len(hits) != 1:
        raise RuntimeError(f"expected one Sheet titled {title}, found {len(hits)}")
    return hits[0]["id"]


def sheets() -> tuple[Service, str]:
    """Returns the Sheets values API and the id of the Sheet found by title."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        KEY, scopes=["https://www.googleapis.com/auth/spreadsheets",
                     "https://www.googleapis.com/auth/drive.readonly"], subject=SUBJECT)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    values = build("sheets", "v4", credentials=creds, cache_discovery=False).spreadsheets().values()
    return values, find_sheet_id(drive, SHEET_TITLE)


def plan_row(
    rows: list[list[str]], behind: list[str], head_sha: str, today: str
) -> tuple[Literal["append", "update", "none"], int | None, list[str] | None]:
    """Pure: the original row decision, kept for compatibility. legacy_row_write limits it."""
    idx = next((i for i, r in enumerate(rows) if r and r[0] == JOB), None)
    is_open = idx is not None and (len(rows[idx]) < 4 or rows[idx][3] != "Done")
    if behind:
        waiting = f"RETURN WHEN: the daily check finds every surface at {short(head_sha)} or newer"
        nxt = "; ".join(behind)[:900]
        if idx is None:
            return ("append", None, [JOB, "HQ / Chief HR Officer", "launchd drift check", "Not started",
                                      waiting, nxt, today, today])
        row = rows[idx] + [""] * (8 - len(rows[idx]))
        return ("update", idx + 1, [row[0], row[1], row[2], "Not started", waiting, nxt, row[6], today])
    if idx is not None and is_open:
        row = rows[idx] + [""] * (8 - len(rows[idx]))
        return ("update", idx + 1, [row[0], row[1], row[2], "Done", "None",
                                    f"Every surface matched {short(head_sha)} on {today}", row[6], today])
    return ("none", None, None)


def legacy_row_write(
    rows: list[list[str]], lines: list[str], head_sha: str, today: str, verification: Verification
) -> tuple[Literal["update", "none"], int | None, list[str] | None]:
    """The legacy writer only maintains an existing open row. New rows stopped with the
    retired tracker rows, and a closed row is never reopened. The row closes only on the
    structured verification; empty prose lines alone never prove anything."""
    reasons = list(lines)
    if verification != "verified" and not reasons:
        reasons = [f"verification is {verification}; see the drift-check JSON report"]
    action, n, values = plan_row(rows, reasons, head_sha, today)
    if action != "update" or n is None:
        return ("none", None, None)
    existing = rows[n - 1]
    if len(existing) >= 4 and existing[3] == "Done":
        return ("none", None, None)
    return ("update", n, values)


def update_legacy_row(lines: list[str], head_sha: str, verification: Verification, dry: bool) -> None:
    today = time.strftime("%Y-%m-%d")
    vals, sheet_id = sheets()
    got = vals.get(spreadsheetId=sheet_id, range=f"{TAB}!A:H").execute().get("values", [])
    action, rownum, values = legacy_row_write(got, lines, head_sha, today, verification)
    if dry or action == "none":
        print(f"legacy row: {action} {rownum} {values}", file=sys.stderr)
        return
    vals.update(spreadsheetId=sheet_id, range=f"{TAB}!A{rownum}:H{rownum}", valueInputOption="USER_ENTERED",
                body={"values": [values]}).execute()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Report publication, delivery, enabled and runtime states per surface.")
    ap.add_argument("--dry-run", action="store_true", help="read everything, write nothing")
    ap.add_argument("--offline", action="store_true", help="local checkout only; no GitHub, Google or writes")
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ap.add_argument("--ref", default="HEAD", help="offline ref to treat as published main")
    ap.add_argument("--home", default=HOME, help="home folder to inspect")
    args = ap.parse_args(argv)
    source: Source = GitSource(args.repo, args.ref) if args.offline else GitHubSource()
    out = build_report(source, args.home, time.time(), load_state(args.home))
    out.report["mode"] = "offline" if args.offline else "dry-run" if args.dry_run else "live"
    print(json.dumps(out.report, indent=1))
    for line in out.lines:
        print(f"drift-check: {line}", file=sys.stderr)
    if not args.offline:
        if not args.dry_run:
            save_state(args.home, out.state)
        update_legacy_row(out.lines, out.head, out.verification, args.dry_run)
    return EXIT[out.verification]


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:  # a broken check must be visible, so it is not swallowed
        print(f"drift-check failed: {e}", file=sys.stderr)
        sys.exit(1)
