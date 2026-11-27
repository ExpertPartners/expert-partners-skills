#!/usr/bin/env python3
"""m4-scratch-janitor: expire AI copies so they never pile up on the M4 again.

Default run (launchd, every 6 hours, lowest CPU and IO priority):
  Walks each top-level entry of the approved scratch root
  (~/HQ-AI-Workspace-M4/Scratch) and
    - removes rebuildable caches (node_modules, .venv, .next, __pycache__ and the like)
      idle for --cache-idle-days (default 2)
    - removes a whole entry idle for --idle-days (default 7; 3 when free space is below
      --pressure-gib) when every git repository in it is safe to drop
  It also removes linked git worktrees left in Projects/*/worktrees, Projects/*/.claude/worktrees,
  Projects/*-worktrees and ~/.codex/worktrees once they are safe and idle for --idle-days.
  Entries that were already in Scratch when the janitor was installed are legacy: for
  them only safe git repositories and rebuildable caches are removed, never other files.

--sweep PATH [PATH ...] applies the legacy rules to other folders, for a one-time cleanup.

A git repository is safe to drop only when, after a fetch, it has no uncommitted or
untracked changes, no stash, no commit that is missing from its remotes, and no ignored
file other than rebuildable caches. Anything open by a running process is skipped.
Every removal and every kept item that needs a person is logged as JSON lines in
~/Library/Logs/m4-scratch-janitor/. Removal is permanent because the Trash sits on
the same disk and would free nothing; only verified pushed clones and rebuildable
caches are eligible for removal.
"""

import argparse
import datetime as dt
from io import BytesIO
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from zipfile import BadZipFile, ZipFile

HOME = Path.home()
SCRATCH = HOME / "HQ-AI-Workspace-M4" / "Scratch"
STATE_DIR = HOME / "Library" / "Application Support" / "ExpertPartners" / "m4-scratch-janitor"
STATE = STATE_DIR / "state.json"
LOG_DIR = HOME / "Library" / "Logs" / "m4-scratch-janitor"
GIB = 1024**3
DAY = 86400
CACHE_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    ".next",
    "__pycache__",
    ".turbo",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".parcel-cache",
    ".nuxt",
    ".svelte-kit",
    "playwright-report",
    "test-results",
    ".gradle",
    ".tox",
}
IGNORED_OK = tuple(CACHE_DIRS) + (
    ".DS_Store",
    "dist",
    "build",
    "out",
    "coverage",
    ".cache",
    ".eslintcache",
    ".vercel",
    "target",
    ".wrangler",
    "tsconfig.tsbuildinfo",
    ".pyc",
    ".output",
    ".results",
    "next-env.d.ts",
)


def git(repo, *args, timeout=120):
    try:
        p = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        return 124, ""


def open_paths():
    """Every path a running process has open or uses as its working folder."""
    try:
        out = subprocess.run(
            # launchd's PATH has no /usr/sbin, so a bare "lsof" is never found there.
            ["/usr/sbin/lsof", "-n", "-w", "-Fn", "-u", str(os.getuid())],
            capture_output=True,
            text=True,
            timeout=180,
        ).stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    return {line[1:] for line in out.splitlines() if line.startswith("n/")}


def in_use(path, opened):
    if opened is None:
        return True
    p = str(path).rstrip("/") + "/"
    return any(o == str(path) or o.startswith(p) for o in opened)


def newest_mtime(path):
    """Newest file modification time, ignoring .git internals and caches that fetches touch.

    Directory mtimes are ignored because removing a cache inside an entry bumps them,
    which would make an idle entry look freshly changed.
    """
    try:
        own = path.lstat().st_mtime
    except OSError:
        return time.time()
    if path.is_symlink() or not path.is_dir():
        return own
    newest = 0.0
    for dp, dn, fn in os.walk(path):
        dn[:] = [d for d in dn if d != ".git" and d not in CACHE_DIRS]
        for f in fn:
            if f == ".DS_Store":
                continue
            try:
                newest = max(newest, os.lstat(os.path.join(dp, f)).st_mtime)
            except OSError:
                pass
    return newest or own


def size_kb(path):
    try:
        out = subprocess.run(
            ["du", "-sk", str(path)], capture_output=True, text=True, timeout=600
        ).stdout
        return int(out.split()[0])
    except Exception:
        return 0


def find_repos(root):
    repos = []
    for dp, dn, fn in os.walk(root):
        if ".git" in dn or ".git" in fn:
            repos.append(Path(dp))
        dn[:] = [d for d in dn if d != ".git" and d not in CACHE_DIRS]
    return repos


def repo_safety(repo, fetch=True):
    """Return (safe, reasons). Safe means every byte of value is on a remote."""
    reasons = []
    rc, remotes = git(repo, "remote")
    if rc != 0 or not remotes.strip():
        return False, ["no remote"]
    if fetch:
        # --prune drops tracking refs for branches deleted on the remote, so their
        # commits only count as pushed if the remote still holds them.
        rc, _ = git(repo, "fetch", "--all", "--prune", "--quiet", timeout=300)
        if rc != 0:
            return False, ["fetch failed, remote state unknown"]
    rc, st = git(repo, "status", "--porcelain", "--ignored", "--untracked-files=all")
    if rc != 0:
        return False, ["git status failed"]
    for line in st.splitlines():
        code, name = line[:2], line[3:]
        if code == "!!":
            if not any(
                part in IGNORED_OK or part.endswith(IGNORED_OK)
                for part in Path(name.rstrip("/")).parts
            ):
                reasons.append(f"ignored file {name}")
        elif name.endswith(".DS_Store"):
            continue
        elif code.strip() == "M" and name.endswith(".zip") and same_archive(repo, name):
            continue
        else:
            reasons.append(f"uncommitted {name}")
        if len(reasons) >= 5:
            break
    if (repo / ".git").is_file():
        # A linked worktree's branches and stash live in its main clone, so dropping the
        # folder loses only uncommitted files or a detached HEAD that no ref holds.
        rc, _ = git(repo, "symbolic-ref", "-q", "HEAD")
        if rc != 0:
            rc, holders = git(repo, "for-each-ref", "--contains", "HEAD", "--format=%(refname)")
            if not [h for h in holders.split() if not h.startswith("refs/codex/")]:
                reasons.append("detached HEAD that no branch or tag holds")
        return not reasons, reasons
    rc, wt = git(repo, "worktree", "list", "--porcelain")
    here = str(repo.resolve())
    for line in wt.splitlines():
        if line.startswith("worktree "):
            other = line[len("worktree ") :]
            if other != here and not other.startswith(here + "/") and Path(other).exists():
                reasons.append(f"linked worktree outside it at {other}")
    for ref, n in unpushed_refs(repo):
        reasons.append(f"{ref} has {n} commit(s) whose changes are not on a remote")
    rc, stash = git(repo, "stash", "list")
    if stash.strip():
        reasons.append("stash present")
    return not reasons, reasons


def same_archive(repo, name):
    """A rebuilt zip whose entries and CRCs match the committed one is not a change."""
    try:
        p = subprocess.run(
            ["git", "-C", str(repo), "show", f"HEAD:{name}"], capture_output=True, timeout=60
        )
        if p.returncode != 0:
            return False

        def entries(z):
            return sorted((i.filename, i.CRC, i.file_size) for i in z.infolist())

        with ZipFile(BytesIO(p.stdout)) as a, ZipFile(repo / name) as b:
            return entries(a) == entries(b)
    except (OSError, BadZipFile, subprocess.TimeoutExpired):
        return False


def remote_tag_commits(repo):
    """Tag commits that exist on the remote; fetch does not map tags under refs/remotes."""
    rc, out = git(repo, "ls-remote", "--tags", "origin", timeout=120)
    shas = set()
    for line in out.splitlines():
        sha = line.split("\t", 1)[0]
        if sha and git(repo, "cat-file", "-e", f"{sha}^{{commit}}")[0] == 0:
            shas.add(sha)
    return sorted(shas)


def remote_default(repo):
    rc, out = git(repo, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")
    if rc == 0 and out.strip():
        return out.strip()
    for cand in ("refs/remotes/origin/main", "refs/remotes/origin/master"):
        if git(repo, "rev-parse", "-q", "--verify", cand)[0] == 0:
            return cand
    return None


def unpushed_refs(repo):
    """Local branches, tags and HEAD whose changes are not on a remote.

    A ref whose commits are missing from every remote still counts as pushed when each
    file it changed has the same content on the remote default branch, which is what a
    squash merge leaves behind. Codex turn checkpoints under refs/codex are internal.
    """
    rc, out = git(repo, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/tags")
    refs = out.split() + ["HEAD"]
    default = remote_default(repo)
    tags = remote_tag_commits(repo)
    bad = []
    for ref in refs:
        rc, n = git(repo, "rev-list", "--count", ref, "--not", "--remotes", *tags)
        if rc != 0 or n.strip() == "0":
            continue
        if default:
            rc, base = git(repo, "merge-base", ref, default)
            if rc == 0 and base.strip():
                rc, files = git(repo, "diff", "--name-only", base.strip(), ref)
                names = [f for f in files.splitlines() if f]
                if rc == 0 and (
                    not names or git(repo, "diff", "--quiet", ref, default, "--", *names)[0] == 0
                ):
                    continue
        bad.append((ref, n.strip()))
        if len(bad) >= 5:
            break
    return bad


def leftover_worktree_roots():
    """Folders where tools park linked worktrees that sessions tend to leave behind."""
    projects = HOME / "HQ-AI-Workspace-M4" / "Projects"
    roots = [projects / "worktrees", HOME / ".codex" / "worktrees"]
    if projects.is_dir():
        for p in projects.iterdir():
            roots += [p / "worktrees", p / ".claude" / "worktrees"]
            if p.name.endswith("-worktrees"):
                roots.append(p)
    return [r for r in roots if r.is_dir() and not r.is_symlink()]


AI_AGENTS = {"droid", "claude", "codex"}
# Executables that only automation ever starts on this Mac.
AUTOMATION_PATHS = (
    "ms-playwright",
    "Google Chrome for Testing",
    "chrome-headless-shell",
    "Chromium.app",
)
BROWSER_PATHS = AUTOMATION_PATHS + (
    "/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Google Chrome Canary.app/Contents/MacOS/",
    "/Firefox.app/Contents/MacOS/firefox",
    "/Safari.app/Contents/MacOS/Safari",
    "/usr/bin/safaridriver",
)
AUTOMATION_FLAGS = ("--enable-automation", "--remote-debugging-pipe", "-marionette", "--headless")


def processes():
    """pid -> (ppid, executable path, argv) for this user's processes."""
    out = subprocess.run(
        ["ps", "-x", "-ww", "-o", "pid=,ppid=,comm=", "-u", str(os.getuid())],
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    args = subprocess.run(
        ["ps", "-x", "-ww", "-o", "pid=,args=", "-u", str(os.getuid())],
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    argv = {}
    for line in args.splitlines():
        pid, _, rest = line.strip().partition(" ")
        if pid.isdigit():
            argv[int(pid)] = rest
    table = {}
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            table[int(parts[0])] = (int(parts[1]), parts[2], argv.get(int(parts[0]), ""))
    return table


def is_browser(exe):
    return any(p in exe for p in BROWSER_PATHS) and "Helper" not in exe


def ai_ancestor(table, pid):
    """Nearest droid, claude or codex process above pid, or None."""
    seen = set()
    pid = table.get(pid, (1,))[0]
    while pid > 1 and pid in table and pid not in seen:
        seen.add(pid)
        ppid, exe, _ = table[pid]
        if os.path.basename(exe) in AI_AGENTS:
            return pid
        pid = ppid
    return None


def browser_violations(table):
    """Root browser processes an AI opened. Allison's own browsers never qualify.

    Her Chrome and Safari are started by launchd (parent pid 1) from the
    standard app with no automation flag, so none of the tests below match
    them. Only the root of a browser tree is returned; its helpers exit with it.
    """
    found = []
    for pid, (ppid, exe, argv) in table.items():
        if not is_browser(exe):
            continue
        parent = table.get(ppid)
        if parent and is_browser(parent[1]):
            continue
        agent = ai_ancestor(table, pid)
        if agent:
            why = "opened by " + os.path.basename(table[agent][1])
        elif any(p in exe for p in AUTOMATION_PATHS):
            why = "automation browser build"
        elif any(f in argv.split() for f in AUTOMATION_FLAGS):
            why = "automation flag"
        else:
            continue
        found.append({"pid": pid, "browser": os.path.basename(exe), "why": why, "agent_pid": agent})
    return found


def opening_session(pid):
    """The Factory, Claude or Codex session id in an agent's environment, if readable."""
    if not pid:
        return None
    try:
        out = subprocess.run(
            ["ps", "-E", "-ww", "-o", "command=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
    except (subprocess.TimeoutExpired, OSError):
        return None
    for name in ("FACTORY_SESSION_ID", "CLAUDE_SESSION_ID", "CODEX_SESSION_ID", "CODEX_THREAD_ID"):
        for token in out.split():
            if token.startswith(name + "="):
                return token.split("=", 1)[1][:160]
    return None


def common_dir(repo):
    rc, out = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(out.strip()).parent if rc == 0 and out.strip() else None


class Janitor:
    def __init__(self, args, scan_open=True):
        self.args = args
        self.freed_kb = 0
        self.events = []
        self.opened = open_paths() if scan_open else set()
        self.now = time.time()

    def log(self, **ev):
        ev["at"] = dt.datetime.now().isoformat(timespec="seconds")
        self.events.append(ev)
        print(json.dumps(ev), flush=True)

    def remove(self, path, reason, prune_from=None):
        kb = size_kb(path)
        if self.args.dry_run:
            self.log(action="would-remove", path=str(path), kb=kb, reason=reason)
            self.freed_kb += kb
            return
        try:
            if path.is_symlink() or path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
        except OSError as e:
            self.log(action="remove-failed", path=str(path), error=str(e))
            return
        self.freed_kb += kb
        self.log(action="removed", path=str(path), kb=kb, reason=reason)
        if prune_from:
            git(prune_from, "worktree", "prune")

    def keep(self, path, why, **extra):
        self.log(action="kept", path=str(path), why=why, **extra)

    def clear_caches(self, root, idle_days):
        for dp, dn, fn in os.walk(root):
            for d in list(dn):
                if d == ".git":
                    dn.remove(d)
                elif d in CACHE_DIRS:
                    dn.remove(d)
                    p = Path(dp) / d
                    if p.is_symlink():
                        continue
                    if in_use(p, self.opened):
                        self.keep(p, "cache in use")
                    elif self.now - newest_mtime(p.parent) > idle_days * DAY:
                        self.remove(p, "rebuildable cache, idle")

    def drop_safe_repos(self, root, idle_days, only_worktrees=False):
        """Legacy rules: remove only git repositories that are safe, idle and unused."""
        repos = sorted(find_repos(root), key=lambda p: len(p.parts))
        if only_worktrees:
            repos = [r for r in repos if (r / ".git").is_file()]
        removed = []
        for repo in repos:
            if any(repo == r or r in repo.parents for r in removed):
                continue
            nested = [r for r in repos if repo in r.parents]
            if in_use(repo, self.opened):
                self.keep(repo, "in use by a running process")
                continue
            if self.now - newest_mtime(repo) < idle_days * DAY:
                self.keep(repo, f"changed within {idle_days} day(s)")
                continue
            bad = []
            for r in [repo] + nested:
                ok, reasons = repo_safety(r, fetch=not self.args.no_fetch)
                if not ok:
                    bad.append({"repo": str(r), "reasons": reasons})
            if bad:
                self.keep(repo, "has work that is not on a remote", detail=bad, needs_person=True)
                continue
            prune = common_dir(repo) if (repo / ".git").is_file() else None
            self.remove(repo, "git clone or worktree fully on its remote, idle", prune_from=prune)
            removed.append(repo)

    def run_scratch(self):
        state = {}
        try:
            state = json.loads(STATE.read_text())
        except (FileNotFoundError, ValueError):
            pass
        if "installed_at" not in state:
            state["installed_at"] = self.now
            if not self.args.dry_run:
                STATE_DIR.mkdir(parents=True, exist_ok=True)
                STATE.write_text(json.dumps(state) + "\n")
        installed = state["installed_at"]
        free = shutil.disk_usage(str(HOME)).free / GIB
        idle = (
            self.args.pressure_idle_days if free < self.args.pressure_gib else self.args.idle_days
        )
        if not SCRATCH.is_dir():
            return
        self.clear_caches(SCRATCH, self.args.cache_idle_days)
        for root in leftover_worktree_roots():
            self.drop_safe_repos(root, self.args.idle_days, only_worktrees=True)
        for entry in sorted(SCRATCH.iterdir()):
            if entry.name.startswith(".") or not entry.exists():
                continue
            try:
                born = entry.stat().st_birthtime
            except AttributeError:
                born = entry.stat().st_ctime
            if born < installed:
                self.drop_safe_repos(entry, idle)
                continue
            if in_use(entry, self.opened):
                self.keep(entry, "in use by a running process")
                continue
            if self.now - newest_mtime(entry) < idle * DAY:
                continue
            bad = []
            for r in find_repos(entry):
                ok, reasons = repo_safety(r, fetch=not self.args.no_fetch)
                if not ok:
                    bad.append({"repo": str(r), "reasons": reasons})
            if bad:
                self.keep(
                    entry,
                    "expired, but has git work not on a remote",
                    detail=bad,
                    needs_person=True,
                )
                continue
            prune = common_dir(entry) if (entry / ".git").is_file() else None
            self.remove(entry, f"scratch entry idle more than {idle} days", prune_from=prune)

    def sweep_browsers(self):
        """No AI browser runs on the M4. Close any an AI opened and log who opened it."""
        try:
            table = processes()
        except (subprocess.TimeoutExpired, OSError):
            self.log(action="browser-sweep-failed", why="process list unavailable")
            return
        found = browser_violations(table)
        for v in found:
            row = {
                "pid": v["pid"],
                "browser": v["browser"],
                "why": v["why"],
                "session": opening_session(v["agent_pid"]),
            }
            if self.args.dry_run:
                self.log(action="would-close-browser", **row)
                continue
            try:
                os.kill(v["pid"], signal.SIGTERM)
                for _ in range(50):
                    os.kill(v["pid"], 0)
                    time.sleep(0.1)
                os.kill(v["pid"], signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as e:
                self.log(action="close-browser-failed", error=str(e), **row)
                continue
            self.log(action="closed-browser", **row)
        self.log(action="browser-sweep", violations=len(found))

    def finish(self):
        free = shutil.disk_usage(str(HOME)).free / GIB
        summary = {
            "action": "summary",
            "freed_gib": round(self.freed_kb / 1024 / 1024, 2),
            "free_gib_after": round(free, 2),
            "dry_run": self.args.dry_run,
            "needs_person": sum(1 for e in self.events if e.get("needs_person")),
        }
        self.log(**summary)
        if not self.args.dry_run:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(LOG_DIR / f"{dt.date.today().isoformat()}.jsonl", "a") as fh:
                for e in self.events:
                    fh.write(json.dumps(e) + "\n")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-fetch", action="store_true", help="Trust local remote refs (tests only)")
    ap.add_argument("--idle-days", type=float, default=7)
    ap.add_argument("--pressure-idle-days", type=float, default=3)
    ap.add_argument("--pressure-gib", type=float, default=15)
    ap.add_argument("--cache-idle-days", type=float, default=2)
    ap.add_argument(
        "--sweep",
        nargs="+",
        metavar="PATH",
        help="Apply legacy rules (safe repos and caches only) to these folders",
    )
    ap.add_argument("--sweep-idle-days", type=float, default=1)
    ap.add_argument(
        "--browsers-only", action="store_true", help="Only close browsers an AI opened on the M4"
    )
    args = ap.parse_args()
    if args.browsers_only:
        j = Janitor(args, scan_open=False)
        j.sweep_browsers()
        j.finish()
        return 0
    j = Janitor(args)
    browsers = not args.sweep and os.environ.get("EP_JANITOR_BROWSER_SWEEP") != "0"
    if j.opened is None:
        print("lsof unavailable, cannot tell what is in use; removing nothing", file=sys.stderr)
        # The browser check needs no open-file list, so it still runs.
        if browsers:
            j.sweep_browsers()
            j.finish()
        return 1
    if args.sweep:
        for p in args.sweep:
            root = Path(p).expanduser()
            if root.is_dir():
                j.clear_caches(root, args.sweep_idle_days)
                j.drop_safe_repos(root, args.sweep_idle_days)
    else:
        j.run_scratch()
        if browsers:
            j.sweep_browsers()
    j.finish()
    return 0


if __name__ == "__main__":
    sys.exit(main())
