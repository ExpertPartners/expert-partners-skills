"""Offline fixtures for the publication, delivery, enabled and runtime states in drift-check.py."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "drift_states", os.path.join(os.path.dirname(__file__), "..", "drift-check.py"))
drift = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drift)

NOW = 1_800_000_000.0
HOUR = 3600.0
DAY = 24 * HOUR
C1, C2, C3 = "1" * 40, "2" * 40, "3" * 40
SURFACES = ("claude-code", "codex", "claude.ai", "chatgpt")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_json(path, data):
    write(path, json.dumps(data))


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def make_plugin(root, name, version, body="first"):
    folder = os.path.join(root, name)
    write_json(os.path.join(folder, ".claude-plugin", "plugin.json"), {"name": name, "version": version})
    write(os.path.join(folder, "skills", name, "SKILL.md"), f"# {name}\n{body}\n")
    return folder


class FakeSource:
    """Publication from fixtures: {commit: {plugin: (version, folder, published_at)}}."""
    name = "fake"

    def __init__(self, head, committed_at, commits):
        self.sha, self.at, self.commits = head, committed_at, commits

    def _plugins(self, commit):
        if commit not in self.commits:
            raise RuntimeError(f"unknown commit {commit}")
        return self.commits[commit]

    def head(self):
        return self.sha, self.at

    def read(self, commit, path):
        assert path == drift.MARKETPLACE_FILE
        return json.dumps({"plugins": [{"name": n, "version": v, "source": f"./plugins/{n}"}
                                       for n, (v, _, _) in self._plugins(commit).items()]})

    def tree_ids(self, commit, folder):
        assert folder == "plugins"
        return {n: drift.git_tree_id(f) for n, (_, f, _) in self._plugins(commit).items()}

    def changed_at(self, commit, path):
        return self._plugins(commit)[path.rsplit("/", 1)[-1]][2]


def make_runner(codex_json=None, codex_text=None):
    calls = []

    def runner(cmd, timeout):
        calls.append(list(cmd))
        if cmd[0] == "git":
            return 1, "", "not a repository"
        if "--json" in cmd:
            return (0, codex_json, "") if codex_json is not None else (1, "", "unknown flag --json")
        return (0, codex_text, "") if codex_text is not None else (1, "", "codex failed")
    return runner, calls


class States(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        src = os.path.join(self.tmp, "c1")
        self.folders = {"alpha": make_plugin(src, "alpha", "1.0.0"), "beta": make_plugin(src, "beta", "2.0.0")}
        self.versions = {"alpha": "1.0.0", "beta": "2.0.0"}
        self.fp = {n: drift.git_tree_id(f) for n, f in self.folders.items()}
        self.published = NOW - 3 * DAY
        self.source = FakeSource(C1, NOW - 2 * DAY, {C1: {
            n: (self.versions[n], f, self.published) for n, f in self.folders.items()}})
        self.codex_json = json.dumps({"installed": [], "available": []})

    # ---- fixture builders

    def install_claude_code(self, plugins):
        entries, flags = {}, {}
        for name, (version, folder, enabled) in plugins.items():
            path = os.path.join(self.home, ".claude/plugins/cache/expert-partners", name, version)
            if folder:
                shutil.copytree(folder, path)
            key = f"{name}@expert-partners"
            entries[key] = [{"scope": "user", "installPath": path, "version": version}]
            if enabled is not None:
                flags[key] = enabled
        write_json(os.path.join(self.home, ".claude/plugins/installed_plugins.json"), {"version": 2, "plugins": entries})
        write_json(os.path.join(self.home, ".claude/settings.json"), {"enabledPlugins": flags})

    def install_codex(self, plugins):
        installed = []
        for name, (version, folder, enabled) in plugins.items():
            if folder:
                shutil.copytree(folder, os.path.join(self.home, ".codex/plugins/cache/expert-partners", name, version))
            installed.append({"pluginId": f"{name}@expert-partners", "name": name, "marketplaceName": "expert-partners",
                              "version": version, "installed": True, "enabled": enabled})
        installed.append({"pluginId": "other@elsewhere", "name": "other", "marketplaceName": "elsewhere",
                          "version": "9", "installed": True, "enabled": True})
        self.codex_json = json.dumps({"installed": installed, "available": []})

    def sync_copy(self, server_id, folder, mtime):
        dest = os.path.join(self.home, ".claude/plugins/synced", server_id, os.path.basename(folder))
        shutil.copytree(folder, dest)
        os.utime(os.path.join(dest, ".claude-plugin", "plugin.json"), (mtime, mtime))

    def receipt(self, filename, data):
        write_json(os.path.join(self.home, ".claude/plugin-sync", filename), data)

    def fingerprint_receipt(self, fps=None):
        fps = fps or self.fp
        return {"observed_at": "2026-11-04T08:00:00Z", "verified_by": "Allison",
                "plugins": {n: {"version": self.versions[n], "fingerprint": fps[n], "enabled": True} for n in fps}}

    def runtime(self, fps=None, surfaces=SURFACES):
        fps = fps or self.fp
        self.receipt("runtime-receipts.json", {"surfaces": {
            s: {n: {"fingerprint": fp, "observed_at": "2026-11-04T09:00:00Z"} for n, fp in fps.items()}
            for s in surfaces}})

    def deliver_everything(self, enabled=True):
        plugins = {n: (self.versions[n], f, enabled) for n, f in self.folders.items()}
        self.install_claude_code(plugins)
        self.install_codex(plugins)
        for filename in drift.RECEIPTS.values():
            self.receipt(filename, self.fingerprint_receipt())

    def check(self, now=NOW, state=None, source=None, codex_text=None):
        runner, self.calls = make_runner(self.codex_json, codex_text)
        return drift.build_report(source or self.source, self.home, now, state or {}, runner=runner,
                                  codex="codex", skip=set())

    @staticmethod
    def rec(out, surface, plugin):
        return out.report["surfaces"][surface]["plugins"][plugin]

    # ---- baseline

    def test_everything_proven_is_verified(self):
        self.deliver_everything()
        self.runtime()
        out = self.check()
        self.assertEqual(out.verification, "verified")
        self.assertEqual(out.lines, [])
        self.assertEqual(drift.EXIT[out.verification], 0)

    # ---- required fixtures

    def test_missing_chatgpt_receipt_is_reported_unknown(self):
        self.deliver_everything()
        self.runtime()
        os.remove(os.path.join(self.home, ".claude/plugin-sync/chatgpt-last-sync.json"))
        out = self.check()
        self.assertIn("chatgpt", out.report["surfaces"])
        for name in self.folders:
            r = self.rec(out, "chatgpt", name)
            self.assertEqual(r["delivery"]["state"], "unknown")
            self.assertIn("not found", r["delivery"]["detail"])
        self.assertEqual(out.verification, "unverified")
        self.assertIn("ChatGPT delivery 2 unknown", out.lines)
        self.assertEqual(drift.EXIT[out.verification], 3)

    def test_disabled_plugin_at_the_same_version_is_not_in_use(self):
        self.deliver_everything(enabled=False)
        self.runtime()
        out = self.check()
        for surface in ("claude-code", "codex"):
            r = self.rec(out, surface, "alpha")
            self.assertEqual((r["delivery"]["state"], r["enabled"]), ("delivered", "disabled"))
        self.assertEqual(out.verification, "unverified")
        self.assertIn("Claude Code not confirmed enabled: alpha, beta", out.lines)
        self.assertEqual(out.report["summary"]["enabled"]["disabled"], 4)

    def test_unchanged_content_under_a_new_unrelated_commit_stays_delivered(self):
        self.deliver_everything()
        self.receipt("chatgpt-last-sync.json", {"commit": C1})
        later = make_plugin(os.path.join(self.tmp, "c2"), "beta", "2.1.0", body="changed")
        commits = {C1: self.source.commits[C1], C2: {
            "alpha": ("1.0.0", self.folders["alpha"], self.published),
            "beta": ("2.1.0", later, NOW - HOUR)}}
        out = self.check(source=FakeSource(C2, NOW - HOUR, commits))
        for surface in ("claude-code", "codex"):
            self.assertEqual(self.rec(out, surface, "alpha")["delivery"]["state"], "delivered")
        self.assertEqual(self.rec(out, "chatgpt", "alpha")["delivery"]["state"], "delivered")
        self.assertEqual(self.rec(out, "chatgpt", "beta")["delivery"]["state"], "stale")
        self.assertEqual(self.rec(out, "claude-code", "beta")["delivery"]["state"], "behind")
        self.assertEqual(out.report["publication"]["plugins"]["alpha"]["fingerprint"], self.fp["alpha"])
        self.assertEqual(out.report["publication"]["source_commit"], C2)

    def test_cloud_receipt_stale_while_local_cache_is_new(self):
        old = make_plugin(os.path.join(self.tmp, "c0"), "alpha", "0.9.0", body="old")
        self.receipt("claude-ai-last-sync.json", self.fingerprint_receipt(
            {"alpha": drift.git_tree_id(old), "beta": self.fp["beta"]}))
        self.sync_copy("srv-alpha", self.folders["alpha"], NOW - 60)
        out = self.check()
        r = self.rec(out, "claude.ai", "alpha")
        self.assertEqual(r["delivery"]["state"], "stale")
        self.assertTrue(r["supporting"]["newest_matches_published"])
        self.assertEqual(self.rec(out, "claude.ai", "beta")["delivery"]["state"], "delivered")

    def test_fresh_local_cache_without_a_receipt_is_never_proof(self):
        self.sync_copy("srv-alpha", self.folders["alpha"], NOW - 60)
        os.makedirs(os.path.join(self.home, ".claude/plugin-sync"), exist_ok=True)
        out = self.check()
        r = self.rec(out, "claude.ai", "alpha")
        self.assertEqual((r["delivery"]["state"], r["delivery"]["evidence"]),
                         ("unverified", "local cache, supporting only"))
        self.assertEqual(self.rec(out, "claude.ai", "beta")["delivery"]["state"], "unknown")

    def test_two_cached_generations_with_the_same_plugin_id(self):
        old = make_plugin(os.path.join(self.tmp, "c0"), "alpha", "0.9.0", body="old")
        # the old generation sorts last on disk, so file order cannot pick the answer
        self.sync_copy("srv-alpha-a", self.folders["alpha"], NOW - HOUR)
        self.sync_copy("srv-alpha-z", old, NOW - 5 * DAY)
        r = self.rec(self.check(), "claude.ai", "alpha")
        self.assertEqual(r["supporting"]["copies"], 2)
        self.assertEqual(r["supporting"]["versions"], ["0.9.0", "1.0.0"])
        self.assertEqual(r["supporting"]["newest_version"], "1.0.0")
        self.assertEqual(r["delivery"]["state"], "unverified")
        self.assertIn("2 cached generations", r["delivery"]["detail"])

        os.utime(os.path.join(self.home, ".claude/plugins/synced/srv-alpha-z/alpha/.claude-plugin/plugin.json"),
                 (NOW - 60, NOW - 60))
        r = self.rec(self.check(), "claude.ai", "alpha")
        # an old local copy says nothing about the server, so only the cache is stale
        self.assertEqual((r["supporting"]["newest_version"], r["supporting"]["state"]), ("0.9.0", "stale"))
        self.assertEqual(r["delivery"]["state"], "unknown")

    def test_old_local_cache_without_a_receipt_is_unknown_cloud_delivery(self):
        plugins = {n: (self.versions[n], f, True) for n, f in self.folders.items()}
        self.install_claude_code(plugins)
        self.install_codex(plugins)
        for name in self.folders:
            old = make_plugin(os.path.join(self.tmp, "old"), name, "0.1.0", body="old")
            self.sync_copy(f"srv-{name}", old, NOW - 30 * DAY)
        out = self.check()
        delivery = out.report["summary"]["delivery"]
        self.assertEqual(delivery["claude-code"], {"delivered": 2})
        self.assertEqual(delivery["codex"], {"delivered": 2})
        self.assertEqual(delivery["claude.ai"], {"unknown": 2})
        self.assertNotIn("stale", delivery["claude.ai"])
        for name in self.folders:
            r = self.rec(out, "claude.ai", name)
            self.assertEqual(r["supporting"]["state"], "stale")
            self.assertEqual(r["runtime"]["state"], "unverified")
        self.assertEqual(out.verification, "unverified")

    def test_continuous_main_pushes_do_not_reset_the_deadline(self):
        dues, state = [], {}
        for i, head in enumerate((C1, C2, C3)):
            at = self.published + (1 + 12 * i) * HOUR
            src = FakeSource(head, at, {head: self.source.commits[C1]})
            out = self.check(now=at + 60, state=state, source=src)
            state = out.state
            r = self.rec(out, "chatgpt", "alpha")
            dues.append(r["deadline"]["due_at"])
        self.assertEqual(len(set(dues)), 1)
        self.assertEqual(dues[0], drift.iso(self.published + drift.GRACE_SECONDS))
        self.assertTrue(r["deadline"]["overdue"])
        self.assertIn("chatgpt/alpha: unknown", out.report["summary"]["overdue"])

    def test_recorded_deadline_holds_when_the_same_plugin_keeps_changing(self):
        out = self.check(now=self.published + HOUR)
        changed = make_plugin(os.path.join(self.tmp, "c2"), "alpha", "1.0.1", body="again")
        commits = {C2: {"alpha": ("1.0.1", changed, self.published + 20 * HOUR),
                        "beta": ("2.0.0", self.folders["beta"], self.published)}}
        later = self.check(now=self.published + 30 * HOUR, state=out.state,
                           source=FakeSource(C2, self.published + 20 * HOUR, commits))
        r = self.rec(later, "claude.ai", "alpha")
        self.assertEqual(r["deadline"]["pending_since"], drift.iso(self.published))
        self.assertTrue(r["deadline"]["overdue"])
        fresh = self.check(now=self.published + 30 * HOUR, source=FakeSource(C2, self.published + 20 * HOUR, commits))
        self.assertFalse(self.rec(fresh, "claude.ai", "alpha")["deadline"]["overdue"])

    def test_absent_runtime_proof_keeps_the_result_unverified(self):
        self.deliver_everything()
        out = self.check()
        for surface in SURFACES:
            r = self.rec(out, surface, "alpha")
            self.assertEqual(r["runtime"]["state"], "unverified")
        self.assertEqual(out.verification, "unverified")
        self.assertEqual(out.lines, ["runtime use unproven for 8 of 8 plugin records"])
        self.assertEqual(drift.EXIT[out.verification], 3)

    def test_publication_and_delivery_verify_independently_of_runtime(self):
        self.deliver_everything()
        out = self.check()
        pubs = out.report["publication"]["plugins"]
        self.assertEqual({p["state"] for p in pubs.values()}, {"published"})
        self.assertEqual({n: p["fingerprint"] for n, p in pubs.items()}, self.fp)
        for surface in SURFACES:
            self.assertEqual(out.report["summary"]["delivery"][surface], {"delivered": 2})
        self.assertEqual(out.report["summary"]["enabled"], {"enabled": 8})
        self.assertEqual(out.report["summary"]["runtime"], {"unverified": 8})

    def test_runtime_receipt_for_older_content_is_stale(self):
        self.deliver_everything()
        old = make_plugin(os.path.join(self.tmp, "c0"), "alpha", "0.9.0", body="old")
        self.runtime({"alpha": drift.git_tree_id(old), "beta": self.fp["beta"]})
        out = self.check()
        self.assertEqual(self.rec(out, "codex", "alpha")["runtime"]["state"], "stale")
        self.assertEqual(self.rec(out, "codex", "beta")["runtime"]["state"], "verified")

    # ---- delivery evidence

    def test_version_only_match_is_unverified(self):
        self.install_claude_code({"alpha": ("1.0.0", None, True)})
        r = self.rec(self.check(), "claude-code", "alpha")
        self.assertEqual((r["delivery"]["state"], r["delivery"]["evidence"]), ("unverified", "version only"))

    def test_same_version_with_different_bytes_is_unverified(self):
        edited = make_plugin(os.path.join(self.tmp, "x"), "alpha", "1.0.0", body="edited")
        self.install_claude_code({"alpha": ("1.0.0", edited, True)})
        r = self.rec(self.check(), "claude-code", "alpha")
        self.assertEqual(r["delivery"]["state"], "unverified")
        self.assertIn("differ", r["delivery"]["detail"])

    def test_local_behind_and_missing_fail(self):
        old = make_plugin(os.path.join(self.tmp, "c0"), "alpha", "0.9.0", body="old")
        self.install_claude_code({"alpha": ("0.9.0", old, True)})
        out = self.check()
        self.assertEqual(self.rec(out, "claude-code", "alpha")["delivery"]["state"], "behind")
        self.assertEqual(self.rec(out, "claude-code", "beta")["delivery"]["state"], "missing")
        self.assertEqual(out.verification, "behind")
        self.assertEqual(drift.EXIT[out.verification], 2)
        self.assertIn("Claude Code alpha: has 0.9.0, main publishes 1.0.0", out.lines)

    def test_missing_installed_plugins_file_is_unknown_not_missing(self):
        r = self.rec(self.check(), "claude-code", "alpha")
        self.assertEqual(r["delivery"]["state"], "unknown")

    def test_codex_lists_only_the_expert_partners_marketplace(self):
        self.check()
        codex_calls = [c for c in self.calls if c[0] == "codex"]
        self.assertEqual(codex_calls, [["codex", "plugin", "list", "--marketplace", "expert-partners", "--json"]])

    def test_codex_plain_listing_is_still_scoped(self):
        self.codex_json = None
        text = ("PLUGIN  STATUS  VERSION  SOURCE\n"
                "alpha@expert-partners  installed, disabled 1.0.0  /x\n")
        out = self.check(codex_text=text)
        self.assertTrue(all("--marketplace" in c for c in self.calls if c[0] == "codex"))
        r = self.rec(out, "codex", "alpha")
        self.assertEqual((r["delivery"]["state"], r["enabled"]), ("unverified", "disabled"))
        self.assertEqual(self.rec(out, "codex", "beta")["delivery"]["state"], "missing")

    def test_unreadable_codex_inventory_is_unknown_not_matched(self):
        self.codex_json = None
        out = self.check()
        self.assertEqual(out.report["summary"]["delivery"]["codex"], {"unknown": 2})

    def test_check_never_writes_receipts(self):
        self.deliver_everything()
        self.runtime()
        folder = os.path.join(self.home, ".claude/plugin-sync")
        before = {n: read_bytes(os.path.join(folder, n)) for n in os.listdir(folder)}
        self.check()
        after = {n: read_bytes(os.path.join(folder, n)) for n in os.listdir(folder)}
        self.assertEqual(before, after)

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_tree_fingerprint_matches_git(self):
        repo = os.path.join(self.tmp, "repo")
        folder = make_plugin(os.path.join(repo, "plugins"), "alpha", "1.0.0")
        write(os.path.join(folder, "bin", "tool.sh"), "#!/bin/sh\necho hi\n")
        os.chmod(os.path.join(folder, "bin", "tool.sh"), 0o755)
        write(os.path.join(folder, "a-b", "x.md"), "dash sorts before slash\n")
        write(os.path.join(folder, "a.md"), "dot sorts after the folder a\n")
        os.makedirs(os.path.join(folder, "empty"))
        git = ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run(["git", "init", "-q", repo], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "fixture"], check=True)
        want = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD:plugins/alpha"],
                              capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(drift.git_tree_id(folder), want)

    # ---- modes and the legacy row

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_offline_mode_needs_no_google_and_writes_nothing(self):
        repo = os.path.join(self.tmp, "repo")
        make_plugin(os.path.join(repo, "plugins"), "alpha", "1.0.0")
        write_json(os.path.join(repo, ".claude-plugin", "marketplace.json"),
                   {"plugins": [{"name": "alpha", "version": "1.0.0", "source": "./plugins/alpha"}]})
        git = ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run(["git", "init", "-q", repo], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "fixture"], check=True)
        self.receipt("chatgpt-last-sync.json", {"commit": "0" * 40})

        def walk():
            return sorted((p, read_bytes(os.path.join(p, f))) for p, _, fs in os.walk(self.home) for f in fs)
        before = walk()
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(drift, "sheets", side_effect=AssertionError("Google was called")), \
                mock.patch.object(drift, "save_state", side_effect=AssertionError("state was written")), \
                mock.patch.object(drift, "codex_bin", return_value=os.path.join(self.tmp, "no-codex")), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = drift.main(["--offline", "--repo", repo, "--home", self.home])
        report = json.loads(stdout.getvalue())
        self.assertEqual(code, 3)
        self.assertEqual(report["mode"], "offline")
        self.assertEqual(report["summary"]["verification"], "unverified")
        self.assertEqual(report["surfaces"]["chatgpt"]["plugins"]["alpha"]["delivery"]["state"], "unknown")
        self.assertEqual(report["surfaces"]["codex"]["plugins"]["alpha"]["delivery"]["state"], "unknown")
        self.assertEqual(walk(), before)

    JOB_ROW = [drift.JOB, "HQ", "job", "Not started", "w", "n", "2026-10-01", "2026-10-01"]

    def test_legacy_writer_never_adds_or_reopens_rows(self):
        job = self.JOB_ROW
        done = job[:3] + ["Done"] + job[4:]
        lines = ["runtime use unproven for 8 of 8 plugin records"]
        write = drift.legacy_row_write
        self.assertEqual(write([["Job"]], lines, C1, "2026-11-04", "unverified")[0], "none")
        self.assertEqual(write([["Job"], done], lines, C1, "2026-11-04", "unverified")[0], "none")
        action, n, vals = write([["Job"], job], lines, C1, "2026-11-04", "unverified")
        self.assertEqual((action, n, vals[3]), ("update", 2, "Not started"))
        self.assertIn("runtime use unproven", vals[5])
        action, n, vals = write([["Job"], job], [], C1, "2026-11-04", "verified")
        self.assertEqual((action, vals[3]), ("update", "Done"))

    def test_legacy_writer_closes_only_on_structured_verification(self):
        for verification in ("unverified", "behind"):
            action, n, vals = drift.legacy_row_write([["Job"], self.JOB_ROW], [], C1, "2026-11-04", verification)
            self.assertEqual((action, vals[3]), ("update", "Not started"))
            self.assertIn(f"verification is {verification}", vals[5])
        action, n, vals = drift.legacy_row_write([["Job"], self.JOB_ROW], ["x"], C1, "2026-11-04", "verified")
        self.assertEqual(vals[3], "Not started")

    def test_cloud_disabled_or_unknown_enabled_never_marks_done(self):
        path = os.path.join(self.home, ".claude/plugin-sync/chatgpt-last-sync.json")
        self.deliver_everything()
        self.runtime()
        for flag, state in ((False, "disabled"), (None, "unknown")):
            with self.subTest(enabled=state):
                receipt = self.fingerprint_receipt()
                if flag is None:
                    del receipt["plugins"]["alpha"]["enabled"]
                else:
                    receipt["plugins"]["alpha"]["enabled"] = flag
                write_json(path, receipt)
                out = self.check()
                self.assertEqual(self.rec(out, "chatgpt", "alpha")["enabled"], state)
                self.assertEqual(out.verification, "unverified")
                self.assertIn("ChatGPT not confirmed enabled: alpha", out.lines)
                action, _, vals = drift.legacy_row_write([["Job"], self.JOB_ROW], out.lines, out.head,
                                                         "2026-11-04", out.verification)
                self.assertEqual((action, vals[3]), ("update", "Not started"))
                self.assertIn("ChatGPT not confirmed enabled: alpha", vals[5])


if __name__ == "__main__":
    unittest.main()
