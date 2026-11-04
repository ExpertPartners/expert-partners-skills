"""Offline tests for the local plugin updater: codex-sync.sh, claude-code-sync.sh,
install.sh and the two launch agent templates. Every CLI is a stub and every remote
is a local bare repository, so nothing here touches a real machine or network.

Each fake Mac also has the ChatGPT app's codex and a Homebrew claude under a fake
system root, where a real Mac keeps them. Those copies only record that they ran,
and every test checks that none did: isolated tests name the fixture CLIs through
CODEX_BIN and CLAUDE_BIN, and only the Discovery tests let the scripts search."""
import json
import os
import plistlib
import shutil
import subprocess
import tempfile
import textwrap
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
MK = "expert-partners"
LABELS = {"codex": "com.expertpartners.codex-plugin-sync",
          "claude-code": "com.expertpartners.claude-code-plugin-sync"}
SYNC_FILES = ["codex-sync.sh", "claude-code-sync.sh", "install.sh", "codex-skip.txt", "legacy-skills.py",
              f"{LABELS['codex']}.plist", f"{LABELS['claude-code']}.plist"]

# One stub plays both CLIs. It keeps the catalog it last refreshed and the installed
# plugins in STUB_STATE, takes the upstream catalog from STUB_CATALOG, and appends each
# call to STUB_CALLS. STUB_FAIL holds comma separated failure points.
STUB = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys, time
    tool = os.path.basename(sys.argv[0])
    args = sys.argv[1:]
    with open(os.environ["STUB_CALLS"], "a") as f:
        f.write(json.dumps({"tool": tool, "args": args, "path": os.environ.get("PATH", "")}) + "\\n")
    fail = set(filter(None, os.environ.get("STUB_FAIL", "").split(",")))
    state_path = os.environ["STUB_STATE"]
    state = json.load(open(state_path))
    MK = "expert-partners"

    def save():
        json.dump(state, open(state_path, "w"))

    def die(msg):
        print(msg, file=sys.stderr)
        sys.exit(1)

    if args[:2] == ["plugin", "marketplace"]:
        time.sleep(float(os.environ.get("STUB_SLEEP", "0")))
        if "marketplace" in fail or args[3:4] != [MK]:
            die("network unreachable")
        state["catalog"] = json.load(open(os.environ["STUB_CATALOG"]))
        save()
    elif args[:2] == ["plugin", "list"]:
        if "list" in fail:
            die("list failed")
        if tool == "claude":
            rows = [{"id": f"{n}@{MK}", "version": p["version"], "scope": "user",
                     "enabled": p["enabled"], "installPath": p.get("installPath", "/x")}
                    for n, p in state["installed"].items()]
            rows.append({"id": "other@else", "version": "9", "scope": "user", "enabled": True, "installPath": "/x"})
            avail = [{"pluginId": f"{n}@{MK}", "name": n, "marketplaceName": MK, "version": v}
                     for n, v in state["catalog"].items() if n not in state["installed"]]
            print(json.dumps({"installed": rows, "available": avail} if "--available" in args else rows))
        else:
            if "--json" not in args:
                print("Marketplace `expert-partners`")
                sys.exit(0)
            rows = [{"pluginId": f"{n}@{MK}", "name": n, "marketplaceName": MK, "version": p["version"],
                     "installed": True, "enabled": p["enabled"]} for n, p in state["installed"].items()]
            avail = [{"pluginId": f"{n}@{MK}", "name": n, "marketplaceName": MK, "version": v,
                      "installed": False, "enabled": False}
                     for n, v in state["catalog"].items() if n not in state["installed"]]
            if args[2:4] != ["--marketplace", MK]:
                rows.append({"pluginId": "other@else", "name": "other", "marketplaceName": "else",
                             "version": "9", "installed": True, "enabled": True})
            print(json.dumps({"installed": rows, "available": avail}))
    elif args[:2] in (["plugin", "update"], ["plugin", "install"], ["plugin", "add"]):
        name, _, mk = args[2].partition("@")
        if f"{args[1]}:{name}" in fail or mk != MK or name not in state["catalog"]:
            die(f"{args[1]} {args[2]} failed")
        old = state["installed"].get(name, {"enabled": True})
        state["installed"][name] = dict(old, version=state["catalog"][name], enabled=old["enabled"])
        save()
    elif tool == "codex" and args == ["app-server", "--listen", "stdio://"]:
        # The skills/list and skills/config/write shapes of codex-rs app-server-protocol v2.
        if "app-server" in fail:
            die("app-server failed to start")
        home = os.environ["HOME"]
        codex_home = os.environ.get("CODEX_HOME") or os.path.join(home, ".codex")
        real = os.path.realpath

        def listing():
            off = {real(p) for p in state.get("codex_disabled", [])}
            root = os.path.join(home, ".agents", "skills")
            rows = []
            for n in sorted(os.listdir(root)) if os.path.isdir(root) else []:
                p = os.path.join(root, n, "SKILL.md")
                if os.path.isfile(p):
                    rows.append({"name": n, "description": "", "path": p, "scope": "user",
                                 "enabled": real(p) not in off, "pluginId": None})
            for s in state.get("codex_plugin_skills", []):
                rows.append(dict(s, description="", scope="user", enabled=s["enabled"] and real(s["path"]) not in off))
            return {"data": [{"cwd": home, "skills": rows, "errors": []}]}

        for line in sys.stdin:
            msg = json.loads(line)
            if "id" not in msg:
                continue
            method, params = msg["method"], msg.get("params") or {}
            with open(os.environ["STUB_CALLS"], "a") as f:
                f.write(json.dumps({"tool": tool, "args": ["app-server", method, params]}) + "\\n")
            if method == "initialize":
                result = {"userAgent": "stub", "codexHome": codex_home}
            elif method == "skills/list":
                result = listing()
            elif method == "skills/config/write":
                if "skills-write" in fail:
                    print(json.dumps({"id": msg["id"], "error": {"code": -32603, "message": "write refused"}}), flush=True)
                    continue
                if "skills-write-ignored" not in fail:
                    state.setdefault("codex_disabled", []).append(params["path"])
                    save()
                    os.makedirs(codex_home, exist_ok=True)
                    with open(os.path.join(codex_home, "config.toml"), "a") as f:
                        f.write('\\n[[skills.config]]\\npath = "%s"\\nenabled = false\\n' % params["path"])
                result = {"effectiveEnabled": "skills-write-ignored" in fail}
            else:
                print(json.dumps({"id": msg["id"], "error": {"code": -32600, "message": "unknown variant"}}), flush=True)
                continue
            print(json.dumps({"id": msg["id"], "result": result}), flush=True)
    else:
        die("unexpected " + " ".join(args))
''')

LAUNCHCTL = textwrap.dedent('''\
    #!/bin/sh
    echo "$*" >> "$STUB_LAUNCHCTL"
''')

# Stands in for a CLI the Mac itself has installed. A test must never run one.
REAL_CLI = textwrap.dedent('''\
    #!/bin/sh
    echo "$0 $*" >> "$REAL_CLI_CALLS"
    exit 1
''')
APP_CODEX = Path("Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex")
BREW_CLAUDE = Path("opt/homebrew/bin/claude")
DISCOVER = {"CLAUDE_BIN": "", "CODEX_BIN": ""}


def sh(*cmd, cwd=None, env=None, check=True):
    r = subprocess.run(list(cmd), cwd=cwd, env=env, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"{cmd} failed: {r.stdout}{r.stderr}")
    return r


def write_exe(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)


class Machine:
    """One fake Mac: a home, an authorized checkout cloned from a fake GitHub, stub CLIs."""

    def __init__(self, root, user="alpha", checkout_rel="Claude/projects/ExpertPartnersSkills"):
        self.root = Path(root)
        self.home = self.root / "Users" / user
        self.checkout = self.home / checkout_rel
        self.origin = self.root / "github" / "ExpertPartners" / "expert-partners-skills.git"
        self.seed = self.root / "seed"
        self.bin = self.root / "bin"
        self.state = self.root / "stub-state.json"
        self.catalog = self.root / "catalog.json"
        self.calls = self.root / "calls.jsonl"
        self.system = self.root / "system"
        self.real_calls = self.root / "real-cli-calls.txt"
        self.home.mkdir(parents=True)
        self.git_env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com",
                            HOME=str(self.root))
        sh("git", "init", "-q", "--bare", "-b", "main", str(self.origin), env=self.git_env)
        sh("git", "init", "-q", "-b", "main", str(self.seed), env=self.git_env)
        (self.seed / "tools" / "plugin-sync").mkdir(parents=True)
        for name in SYNC_FILES:
            shutil.copy2(HERE / name, self.seed / "tools" / "plugin-sync" / name)
        self.publish({"a": "1.0.0", "b": "1.0.0", "c": "1.0.0"})
        self.checkout.parent.mkdir(parents=True, exist_ok=True)
        sh("git", "clone", "-q", "-b", "main", str(self.origin), str(self.checkout), env=self.git_env)
        write_exe(self.bin / "claude", STUB)
        write_exe(self.bin / "codex", STUB)
        write_exe(self.bin / "plutil", "#!/bin/sh\nexit 0\n")
        write_exe(self.bin / "launchctl", LAUNCHCTL)
        write_exe(self.system / APP_CODEX, REAL_CLI)
        write_exe(self.system / BREW_CLAUDE, REAL_CLI)
        self.set_installed({"a": ("1.0.0", True), "b": ("1.0.0", False)})
        self.catalog.write_text(json.dumps({"a": "1.0.0", "b": "1.0.0", "c": "1.0.0"}))

    def publish(self, versions, script_patch=None, message="release"):
        """Merge a release into the fake GitHub main."""
        mj = {"name": MK, "plugins": [{"name": n, "source": f"./plugins/{n}", "version": v}
                                      for n, v in versions.items()]}
        (self.seed / ".claude-plugin").mkdir(exist_ok=True)
        (self.seed / ".claude-plugin" / "marketplace.json").write_text(json.dumps(mj, indent=2) + "\n")
        if script_patch:
            script_patch(self.seed / "tools" / "plugin-sync")
        sh("git", "add", "-A", cwd=self.seed, env=self.git_env)
        sh("git", "commit", "-q", "-m", message, cwd=self.seed, env=self.git_env)
        sh("git", "push", "-q", str(self.origin), "main", cwd=self.seed, env=self.git_env)
        self.catalog.write_text(json.dumps(versions))
        return sh("git", "rev-parse", "HEAD", cwd=self.seed).stdout.strip()

    def set_installed(self, plugins):
        self.state.write_text(json.dumps({
            "catalog": {"a": "1.0.0", "b": "1.0.0", "c": "1.0.0"},
            "installed": {n: {"version": v, "enabled": e} for n, (v, e) in plugins.items()}}))

    def installed(self):
        return json.loads(self.state.read_text())["installed"]

    def env(self, **extra):
        env = {"HOME": str(self.home), "PATH": f"{self.bin}:/usr/bin:/bin",
               "STUB_STATE": str(self.state), "STUB_CATALOG": str(self.catalog),
               "STUB_CALLS": str(self.calls), "STUB_LAUNCHCTL": str(self.root / "launchctl.txt"),
               "GIT_CONFIG_GLOBAL": str(self.root / "gitconfig"), "LANG": "C",
               "CLAUDE_BIN": str(self.bin / "claude"), "CODEX_BIN": str(self.bin / "codex"),
               "PLUGIN_SYNC_SYSTEM_ROOT": str(self.system), "REAL_CLI_CALLS": str(self.real_calls)}
        env.update(extra)
        return env

    def real_cli_runs(self):
        return self.real_calls.read_text() if self.real_calls.exists() else ""

    def sync(self, surface, *args, **extra):
        return subprocess.run(["/bin/bash", str(self.checkout / "tools" / "plugin-sync" / f"{surface}-sync.sh"), *args],
                              env=self.env(**extra), capture_output=True, text=True, timeout=120)

    def take_calls(self):
        if not self.calls.exists():
            return []
        rows = [json.loads(l) for l in self.calls.read_text().splitlines()]
        self.calls.unlink()
        return rows

    def head(self):
        return sh("git", "rev-parse", "HEAD", cwd=self.checkout).stdout.strip()

    @property
    def state_dir(self):
        return self.home / "Library" / "Application Support" / "plugin-sync"

    def receipt(self, name):
        p = self.state_dir / name
        return json.loads(p.read_text()) if p.exists() else None

    def log(self, surface):
        logs = sorted((self.home / "Library" / "Logs" / "plugin-sync").glob(f"{surface}-sync-*.log"))
        return "".join(p.read_text() for p in logs)


def add_marker(folder):
    """Make the published scripts record that the new copy, not the old one, ran."""
    for name in ("codex-sync.sh", "claude-code-sync.sh"):
        p = folder / name
        lines = p.read_text().splitlines(keepends=True)
        lines.insert(1, 'printf "%s\\n" "$0" >> "$HOME/new-code-ran"\n')
        p.write_text("".join(lines))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.m = Machine(self.tmp)

    def tearDown(self):
        self.assertEqual(self.m.real_cli_runs(), "", "a test ran this Mac's own CLI")


class Templates(unittest.TestCase):
    def test_both_agents_run_at_login_and_every_five_minutes(self):
        for surface, label in LABELS.items():
            raw = (HERE / f"{label}.plist").read_text()
            d = plistlib.loads(raw.encode())
            self.assertEqual(d["Label"], label)
            self.assertIs(d["RunAtLoad"], True)
            self.assertEqual(sorted(e["Minute"] for e in d["StartCalendarInterval"]), list(range(0, 60, 5)))
            self.assertTrue(all(set(e) == {"Minute"} for e in d["StartCalendarInterval"]))
            self.assertEqual(d["ProgramArguments"], ["/bin/bash", f"@CHECKOUT@/tools/plugin-sync/{surface}-sync.sh"])
            self.assertEqual(d["EnvironmentVariables"]["HOME"], "@HOME@")
            for banned in ("allisongaddy", ".nvm", "v24", "|| true", "git pull", "Hour"):
                self.assertNotIn(banned, raw)


class Install(unittest.TestCase):
    def assertSamePath(self, a, b):
        self.assertEqual(os.path.realpath(a), os.path.realpath(b))

    def install(self, user, rel):
        # macOS hands out temp folders under /var, a symlink to /private/var, so git
        # reports the checkout by its resolved path. A symlinked root gives every OS
        # that shape.
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "private").mkdir()
        (tmp / "link").symlink_to(tmp / "private")
        m = Machine(tmp / "link", user, rel)
        self.assertNotEqual(str(m.checkout), os.path.realpath(m.checkout))
        dest = m.home / "Library" / "LaunchAgents"
        dest.mkdir(parents=True)
        old = dest / f"{LABELS['codex']}.plist"
        old.write_text("old daily plist\n")
        r = subprocess.run(["/bin/bash", str(m.checkout / "tools" / "plugin-sync" / "install.sh")],
                           env=m.env(), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"codex binary: {m.bin / 'codex'}", r.stdout)
        self.assertIn(f"claude-code binary: {m.bin / 'claude'}", r.stdout)
        return m, dest, r

    def test_renders_for_either_home_and_checkout(self):
        for user, rel in (("alpha", "Claude/projects/ExpertPartnersSkills"),
                          ("beta two", "Developer/expert partners & skills")):
            with self.subTest(user=user):
                m, dest, r = self.install(user, rel)
                uid = os.getuid()
                for surface, label in LABELS.items():
                    raw = (dest / f"{label}.plist").read_bytes()
                    d = plistlib.loads(raw)
                    self.assertSamePath(d["ProgramArguments"][1], m.checkout / "tools" / "plugin-sync" / f"{surface}-sync.sh")
                    self.assertSamePath(d["WorkingDirectory"], m.checkout)
                    self.assertSamePath(d["EnvironmentVariables"]["HOME"], m.home)
                    for key in ("StandardOutPath", "StandardErrorPath"):
                        self.assertSamePath(os.path.dirname(d[key]), m.home / "Library" / "Logs" / "plugin-sync")
                    self.assertNotIn(b"@HOME@", raw)
                    self.assertNotIn(b"@CHECKOUT@", raw)
                    self.assertNotIn(b"allisongaddy", raw)
                prefix = f"bootstrap gui/{uid} "
                booted = [os.path.realpath(c[len(prefix):])
                          for c in (m.root / "launchctl.txt").read_text().splitlines() if c.startswith(prefix)]
                for label in LABELS.values():
                    self.assertIn(os.path.realpath(dest / f"{label}.plist"), booted)
                self.assertFalse((dest / "com.expertpartners.plugin-drift-check.plist").exists())
                backups = list(dest.glob(f"{LABELS['codex']}.plist.bak.*"))
                self.assertEqual(len(backups), 1)
                self.assertEqual(backups[0].read_text(), "old daily plist\n")
                again = subprocess.run(["/bin/bash", str(m.checkout / "tools" / "plugin-sync" / "install.sh")],
                                       env=m.env(), capture_output=True, text=True)
                self.assertEqual(again.returncode, 0, again.stderr)
                self.assertEqual(len(list(dest.glob("*.bak.*"))), 1, "an unchanged plist is not backed up again")
                self.assertEqual(m.real_cli_runs(), "")

    def test_refuses_a_checkout_of_another_repo(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        m = Machine(tmp)
        sh("git", "-C", str(m.checkout), "remote", "set-url", "origin", "https://github.com/someone/fork.git")
        r = subprocess.run(["/bin/bash", str(m.checkout / "tools" / "plugin-sync" / "install.sh")],
                           env=m.env(), capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((m.home / "Library" / "LaunchAgents").exists())


class Discovery(Base):
    """The only tests that let the scripts search. They locate without running, or
    run a fixture CLI after removing every copy that stands in for the Mac's own."""

    def locate(self, surface, **extra):
        return self.m.sync(surface, "--locate", **{**DISCOVER, **extra}).stdout.strip()

    def test_claude_on_path_wins_then_homebrew(self):
        self.assertEqual(self.locate("claude-code"), str(self.m.bin / "claude"))
        (self.m.bin / "claude").unlink()
        self.assertEqual(self.locate("claude-code"), str(self.m.system / BREW_CLAUDE))

    def test_newest_nvm_claude_wins_by_number_not_by_text(self):
        (self.m.bin / "claude").unlink()
        (self.m.system / BREW_CLAUDE).unlink()
        for v in ("v9.11.2", "v10.2.0", "v8.0.0"):
            write_exe(self.m.home / ".nvm" / "versions" / "node" / v / "bin" / "claude", STUB)
        self.assertEqual(self.locate("claude-code"), f"{self.m.home}/.nvm/versions/node/v10.2.0/bin/claude")

    def test_nvm_bin_dir_is_put_on_path_for_the_cli(self):
        (self.m.bin / "claude").unlink()
        (self.m.system / BREW_CLAUDE).unlink()
        nvm = self.m.home / ".nvm" / "versions" / "node" / "v22.3.0" / "bin"
        write_exe(nvm / "claude", STUB)
        r = self.m.sync("claude-code", **DISCOVER)
        self.assertEqual(r.returncode, 0, self.m.log("claude-code"))
        calls = self.m.take_calls()
        self.assertTrue(calls and all(c["path"].split(":")[0] == str(nvm) for c in calls))

    def test_codex_prefers_the_chatgpt_app_and_override_wins(self):
        self.assertEqual(self.locate("codex"), str(self.m.system / APP_CODEX), "the app comes before PATH")
        (self.m.system / APP_CODEX).unlink()
        app = self.m.home / APP_CODEX
        write_exe(app, STUB)
        self.assertEqual(self.locate("codex"), str(app))
        app.unlink()
        self.assertEqual(self.locate("codex"), str(self.m.bin / "codex"))
        other = self.m.root / "elsewhere" / "codex"
        write_exe(other, STUB)
        self.assertEqual(self.locate("codex", CODEX_BIN=str(other)), str(other))

    def test_missing_binary_fails_and_says_so(self):
        (self.m.bin / "claude").unlink()
        r = self.m.sync("claude-code", CLAUDE_BIN=str(self.m.root / "nope"))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.m.receipt("claude-code-delivery.json")["status"], "failed")
        self.assertIn("claude binary not found", self.m.receipt("claude-code-delivery.json")["failures"])


class Delivery(Base):
    def release(self):
        return self.m.publish({"a": "1.1.0", "b": "1.1.0", "c": "1.1.0"}, add_marker)

    def test_claude_code_update_arrives_and_reads_back(self):
        sha = self.release()
        r = self.m.sync("claude-code")
        self.assertEqual(r.returncode, 0, self.m.log("claude-code"))
        self.assertEqual(self.m.head(), sha)
        self.assertTrue((self.m.home / "new-code-ran").exists(), "the updated script must be the one that delivers")
        calls = [c["args"] for c in self.m.take_calls()]
        self.assertIn(["plugin", "marketplace", "update", MK], calls)
        self.assertIn(["plugin", "update", f"a@{MK}"], calls)
        self.assertIn(["plugin", "install", f"c@{MK}"], calls)
        self.assertFalse([c for c in calls if any(a.startswith("b@") for a in c)], "disabled b is left alone")
        self.assertEqual(self.m.installed(), {"a": {"version": "1.1.0", "enabled": True},
                                              "b": {"version": "1.0.0", "enabled": False},
                                              "c": {"version": "1.1.0", "enabled": True}})
        rec = self.m.receipt("claude-code-delivery.json")
        self.assertEqual((rec["status"], rec["commit"]), ("ok", sha))
        self.assertEqual(rec["plugins"]["a"], {"repo": "1.1.0", "installed": "1.1.0", "enabled": True, "state": "current"})
        self.assertEqual(rec["plugins"]["b"]["state"], "disabled, left alone")
        self.assertIn("unverified", rec["note"])
        src = self.m.receipt("source.json")
        self.assertEqual((src["status"], src["checkout_commit"], src["published_commit"]), ("ok", sha, sha))

        self.assertEqual(self.m.sync("claude-code").returncode, 0)
        self.assertEqual([c["args"][:2] for c in self.m.take_calls()], [], "a matching delivery is not redone")
        self.assertEqual(self.m.sync("claude-code", PLUGIN_SYNC_FORCE="1").returncode, 0)
        self.assertNotIn(["plugin", "update", f"a@{MK}"], [c["args"] for c in self.m.take_calls()])

    def test_codex_scoped_json_inventory_and_readback(self):
        sha = self.release()
        r = self.m.sync("codex")
        self.assertEqual(r.returncode, 0, self.m.log("codex"))
        calls = [c["args"] for c in self.m.take_calls()]
        self.assertIn(["plugin", "marketplace", "upgrade", MK], calls)
        lists = [c for c in calls if c[:2] == ["plugin", "list"]]
        self.assertTrue(lists)
        self.assertTrue(all(c == ["plugin", "list", "--marketplace", MK, "--available", "--json"] for c in lists))
        self.assertIn(["plugin", "add", f"a@{MK}"], calls)
        self.assertIn(["plugin", "add", f"c@{MK}"], calls)
        self.assertNotIn(["plugin", "add", f"b@{MK}"], calls)
        self.assertEqual(self.m.installed()["b"], {"version": "1.0.0", "enabled": False})
        rec = self.m.receipt("codex-delivery.json")
        self.assertEqual((rec["status"], rec["commit"]), ("ok", sha))
        self.assertNotIn("other", rec["plugins"])

    def test_codex_skip_list_is_honored(self):
        def skip_c(folder):
            add_marker(folder)
            with open(folder / "codex-skip.txt", "a") as f:
                f.write("c\n")
        self.m.publish({"a": "1.1.0", "b": "1.0.0", "c": "1.1.0"}, skip_c)
        r = self.m.sync("codex")
        self.assertEqual(r.returncode, 0, self.m.log("codex"))
        self.assertNotIn(["plugin", "add", f"c@{MK}"], [c["args"] for c in self.m.take_calls()])
        self.assertEqual(self.m.receipt("codex-delivery.json")["plugins"]["c"]["state"], "skipped, codex-skip.txt")


class Failures(Base):
    def test_offline_source_update_fails_without_running_stale_code(self):
        before = self.m.head()
        sh("git", "-C", str(self.m.checkout), "remote", "set-url", "origin", str(self.m.root / "offline.git"))
        for surface in ("claude-code", "codex"):
            r = self.m.sync(surface)
            self.assertEqual(r.returncode, 1)
            self.assertIsNone(self.m.receipt(f"{surface}-delivery.json"))
        self.assertEqual(self.m.take_calls(), [], "no CLI runs on stale code")
        self.assertEqual(self.m.receipt("source.json")["status"], "failed")
        self.assertIn("git fetch origin main failed", self.m.receipt("source.json")["reason"])
        self.assertEqual(self.m.head(), before)

        sh("git", "-C", str(self.m.checkout), "remote", "set-url", "origin", str(self.m.origin))
        sha = self.m.publish({"a": "1.1.0", "b": "1.0.0", "c": "1.0.0"})
        self.assertEqual(self.m.sync("claude-code").returncode, 0, "the next run catches up once online")
        self.assertEqual(self.m.receipt("claude-code-delivery.json")["commit"], sha)

    def test_marketplace_refresh_failure_is_not_success(self):
        for surface in ("claude-code", "codex"):
            r = self.m.sync(surface, STUB_FAIL="marketplace")
            self.assertEqual(r.returncode, 1)
            rec = self.m.receipt(f"{surface}-delivery.json")
            self.assertEqual(rec["status"], "failed")
            self.assertTrue(rec["failures"][0].endswith(f"{MK} failed"))
        self.assertFalse([c for c in self.m.take_calls() if c["args"][1] in ("add", "install", "update")])

    def test_list_failure_is_not_read_as_everything_missing(self):
        for surface in ("claude-code", "codex"):
            r = self.m.sync(surface, STUB_FAIL="list")
            self.assertEqual(r.returncode, 1)
            self.assertIn("plugin list --json failed", " ".join(self.m.receipt(f"{surface}-delivery.json")["failures"]))
        self.assertFalse([c for c in self.m.take_calls() if c["args"][1] in ("add", "install", "update")])

    def test_one_failed_update_fails_the_delivery(self):
        self.m.publish({"a": "1.1.0", "b": "1.0.0", "c": "1.0.0"})
        r = self.m.sync("claude-code", STUB_FAIL="update:a")
        self.assertEqual(r.returncode, 1)
        rec = self.m.receipt("claude-code-delivery.json")
        self.assertEqual(rec["plugins"]["a"]["state"], "behind")
        self.assertIn(f"claude plugin update a@{MK} failed", rec["failures"])
        self.assertEqual(self.m.sync("claude-code").returncode, 0, "a failed delivery is retried next run")

    def test_unrelated_local_changes_survive_and_conflicts_stop_the_run(self):
        notes = self.m.checkout / "my-notes.txt"
        notes.write_text("mine\n")
        sha = self.m.publish({"a": "1.1.0", "b": "1.0.0", "c": "1.0.0"})
        self.assertEqual(self.m.sync("claude-code").returncode, 0)
        self.assertEqual((self.m.head(), notes.read_text()), (sha, "mine\n"))

        mj = self.m.checkout / ".claude-plugin" / "marketplace.json"
        mj.write_text(mj.read_text() + " ")
        self.m.publish({"a": "1.2.0", "b": "1.0.0", "c": "1.0.0"})
        self.m.take_calls()
        r = self.m.sync("claude-code")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.m.head(), sha)
        self.assertTrue(mj.read_text().endswith(" "), "a local edit is never thrown away")
        self.assertEqual(self.m.take_calls(), [])
        self.assertIn("fast-forward refused", self.m.receipt("source.json")["reason"])

    def test_a_checkout_on_another_branch_is_left_there(self):
        sh("git", "-C", str(self.m.checkout), "checkout", "-q", "-b", "work")
        r = self.m.sync("codex")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(sh("git", "-C", str(self.m.checkout), "branch", "--show-current").stdout.strip(), "work")
        self.assertIn("not main", self.m.receipt("source.json")["reason"])


class Concurrency(Base):
    def test_overlapping_runs_do_not_stack(self):
        self.m.publish({"a": "1.1.0", "b": "1.0.0", "c": "1.0.0"})
        results = []
        threads = [threading.Thread(target=lambda: results.append(self.m.sync("claude-code", STUB_SLEEP="2")))
                   for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sorted(r.returncode for r in results), [0, 0])
        calls = [c["args"] for c in self.m.take_calls()]
        self.assertEqual(calls.count(["plugin", "marketplace", "update", MK]), 1)
        self.assertIn("another claude-code run is active", self.m.log("claude-code"))

    def test_codex_and_claude_code_runs_do_not_block_each_other(self):
        self.m.publish({"a": "1.1.0", "b": "1.0.0", "c": "1.0.0"})
        results = {}
        threads = [threading.Thread(target=lambda s=s: results.__setitem__(s, self.m.sync(s)))
                   for s in ("codex", "claude-code")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual({s: r.returncode for s, r in results.items()}, {"codex": 0, "claude-code": 0})
        self.assertEqual(self.m.receipt("codex-delivery.json")["status"], "ok")
        self.assertEqual(self.m.receipt("claude-code-delivery.json")["status"], "ok")

    def test_live_lock_is_respected_and_a_dead_holders_lock_is_not(self):
        self.m.state_dir.mkdir(parents=True)
        lock = self.m.state_dir / "claude-code.lock"
        lock.write_text("12345\n")
        holder = subprocess.Popen(["python3", "-c", textwrap.dedent(f'''\
            import fcntl, sys, time
            f = open({str(lock)!r}, "a")
            fcntl.flock(f, fcntl.LOCK_EX)
            print("held", flush=True)
            time.sleep(60)
        ''')], stdout=subprocess.PIPE, text=True)
        self.addCleanup(holder.stdout.close)
        self.addCleanup(holder.kill)
        self.assertEqual(holder.stdout.readline().strip(), "held")
        r = self.m.sync("claude-code")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.m.take_calls(), [])
        self.assertTrue(lock.exists())

        holder.kill()
        holder.wait()
        r = self.m.sync("claude-code")
        self.assertEqual(r.returncode, 0, self.m.log("claude-code"))
        self.assertEqual(self.m.receipt("claude-code-delivery.json")["status"], "ok")


if __name__ == "__main__":
    unittest.main()
