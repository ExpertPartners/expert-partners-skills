"""Real-script tests for the legacy user-tier skill migration in codex-sync.sh and
claude-code-sync.sh. Each test runs the actual sync script against the stub CLIs and the
local git remotes from test_local_sync, with old deployed copies under a fake home, so it
touches no real machine, setting or network."""
import importlib.util
import json
import os
import shutil
import stat
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("local_sync", HERE / "test_local_sync.py")
ls = importlib.util.module_from_spec(spec)
sys.modules["local_sync"] = ls
spec.loader.exec_module(ls)

MK = ls.MK
NAMES = {"intake": "intake", "new-project": "new-project", "session-home": "session-home",
         "verify-docs": "research-before-guessing"}
VERSIONS = {"a": "1.0.0", "b": "1.0.0", "c": "1.0.0", "operating-doctrine": "1.0.0"}


def legacy_text(name, rev):
    return f"---\nname: {name}\ndescription: old user-tier {name} rev {rev}\n---\n\n# {name}\n\nOld body {rev}.\n"


def deployed(text, name):
    """The skill-deploy render: three header lines before the closing front matter fence."""
    lines = text.split("\n")
    end = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
    lines[end:end] = ["# DEPLOYED COPY (2026-08-05, skill-deploy pipeline): the canonical home is",
                      f"# expert-partners-skills skills/{name}/SKILL.md. Deployed at v1.0.",
                      "# Edit the canonical copy first, then redeploy via tools/skill-deploy."]
    return "\n".join(lines)


class Legacy(ls.Base, unittest.TestCase):
    def setUp(self):
        super().setUp()
        m = self.m
        seed = m.seed
        for name in NAMES:
            (seed / "skills" / name).mkdir(parents=True, exist_ok=True)
            (seed / "skills" / name / "SKILL.md").write_text(legacy_text(name, 1))
        m.publish(dict(a="1.0.0", b="1.0.0", c="1.0.0"), message="old user-tier skills")
        (seed / "skills" / "intake" / "SKILL.md").write_text(legacy_text("intake", 2))
        m.publish(dict(a="1.0.0", b="1.0.0", c="1.0.0"), message="intake rev 2")
        self.state({})
        self.home = m.home
        for root in (".claude/skills", ".agents/skills"):
            for name in NAMES:
                rev = 1 if name != "verify-docs" else 9  # verify-docs was edited by hand
                text = legacy_text(name, rev)
                d = self.home / root / name
                d.mkdir(parents=True)
                (d / "SKILL.md").write_text(deployed(text, name) if name != "session-home" else text)
            mine = self.home / root / "my-own"
            mine.mkdir()
            (mine / "SKILL.md").write_text("---\nname: my-own\ndescription: mine\n---\n")
        self.originals = {p: p.read_bytes() for p in self.home.rglob("SKILL.md")}

    # -------------------------------------------------------------- fixture helpers

    def state(self, installed, catalog=None, **extra):
        s = {"catalog": catalog or {k: v for k, v in VERSIONS.items() if k != "operating-doctrine"},
             "installed": {"a": {"version": "1.0.0", "enabled": True}, **installed}}
        s.update(extra)
        self.m.state.write_text(json.dumps(s))

    def release_replacement(self, version="1.0.0"):
        """Publish the migration commit: old sources removed, plugin skills added."""
        seed = self.m.seed
        shutil.rmtree(seed / "skills")
        base = seed / "plugins" / "operating-doctrine" / "skills"
        for skill in NAMES.values():
            (base / skill).mkdir(parents=True, exist_ok=True)
            (base / skill / "SKILL.md").write_text(f"---\nname: {skill}\ndescription: plugin {skill}\n---\n\nNew.\n")
        (base / "research-before-guessing" / "references").mkdir(exist_ok=True)
        (base / "research-before-guessing" / "references" / "verify-current-docs.md").write_text("ref\n")
        return self.m.publish(dict(VERSIONS, **{"operating-doctrine": version}), message="migrate into the plugin")

    def install_copy(self, where):
        dst = self.m.root / where
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(self.m.seed / "plugins" / "operating-doctrine", dst)
        return dst

    def claude_installed(self, enabled=True):
        path = self.install_copy("claude-cache/operating-doctrine/1.0.0")
        self.state({"operating-doctrine": {"version": "1.0.0", "enabled": enabled, "installPath": str(path)}},
                   catalog=VERSIONS)
        return path

    def codex_installed(self, enabled=True):
        path = self.install_copy("codex-cache/operating-doctrine")
        skills = [{"name": f"operating-doctrine:{s}", "path": str(path / "skills" / s / "SKILL.md"),
                   "pluginId": f"operating-doctrine@{MK}", "enabled": enabled} for s in NAMES.values()]
        self.state({"operating-doctrine": {"version": "1.0.0", "enabled": enabled}}, catalog=VERSIONS,
                   codex_plugin_skills=skills)
        return path

    @property
    def settings(self):
        return self.home / ".claude" / "settings.json"

    def legacy(self, surface):
        return self.m.receipt(f"{surface}-legacy-skills.json")

    def assertCopiesUntouched(self):
        for p, data in self.originals.items():
            self.assertEqual(p.read_bytes(), data, f"{p} must never be edited, moved or deleted")

    def writes(self):
        return [c["args"][2]["path"] for c in self.m.take_calls()
                if c["args"][:2] == ["app-server", "skills/config/write"]]

    # -------------------------------------------------------------- Claude Code

    def test_claude_first_migration_keeps_unrelated_settings_and_backs_up(self):
        self.release_replacement()
        self.claude_installed()
        self.settings.write_text(json.dumps({"model": "opus", "enabledPlugins": {f"a@{MK}": True},
                                             "skillOverrides": {"my-own": "name-only"}}, indent=4))
        before = self.settings.read_bytes()
        r = self.m.sync("claude-code")
        self.assertEqual(r.returncode, 0, self.m.log("claude-code"))
        got = json.loads(self.settings.read_text())
        self.assertEqual(got["model"], "opus")
        self.assertEqual(got["enabledPlugins"], {f"a@{MK}": True})
        self.assertEqual(got["skillOverrides"], {"my-own": "name-only", "intake": "off",
                                                 "new-project": "off", "session-home": "off"})
        rec = self.legacy("claude-code")
        self.assertEqual(rec["status"], "ok")
        self.assertEqual(rec["skills"]["intake"]["state"], "turned off")
        self.assertIn("left alone, not recognized", rec["skills"]["verify-docs"]["state"])
        [backup] = rec["backups"]
        bpath = Path(backup["path"])
        self.assertEqual(bpath.read_bytes(), before)
        self.assertEqual(stat.S_IMODE(bpath.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(bpath.parent.stat().st_mode), 0o700)
        self.assertEqual(self.m.receipt("claude-code-delivery.json")["legacy_skills"]["status"], "ok")
        self.assertIn("legacy verify-docs: left alone", self.m.log("claude-code"))
        self.assertCopiesUntouched()

        after = self.settings.read_bytes()
        r = self.m.sync("claude-code", PLUGIN_SYNC_FORCE="1")
        self.assertEqual(r.returncode, 0, self.m.log("claude-code"))
        self.assertEqual(self.settings.read_bytes(), after, "a rerun changes nothing")
        rec = self.legacy("claude-code")
        self.assertEqual(rec["skills"]["intake"]["state"], "already off")
        self.assertEqual(rec["backups"], [])
        self.assertEqual(len(list(bpath.parent.iterdir())), 1, "no second backup")

    def test_claude_no_replacement_then_offline_then_reconnect(self):
        r = self.m.sync("claude-code")
        self.assertEqual(r.returncode, 0, self.m.log("claude-code"))
        rec = self.legacy("claude-code")
        self.assertEqual(rec["status"], "waiting")
        self.assertIn("operating-doctrine is not installed", rec["skills"]["intake"]["state"])
        self.assertFalse(self.settings.exists(), "nothing is written while the replacement is unproven")

        ls.sh("git", "-C", str(self.m.checkout), "remote", "set-url", "origin", str(self.m.root / "offline.git"))
        self.release_replacement()
        self.claude_installed()
        self.assertEqual(self.m.sync("claude-code").returncode, 1, "offline is a visible failure")
        self.assertFalse(self.settings.exists())

        ls.sh("git", "-C", str(self.m.checkout), "remote", "set-url", "origin", str(self.m.origin))
        r = self.m.sync("claude-code")
        self.assertEqual(r.returncode, 0, self.m.log("claude-code"))
        got = json.loads(self.settings.read_text())
        self.assertEqual(got, {"skillOverrides": {"intake": "off", "new-project": "off", "session-home": "off"}})
        self.assertEqual(stat.S_IMODE(self.settings.stat().st_mode), 0o600)
        self.assertCopiesUntouched()

    def test_claude_wrong_bytes_waits_for_that_skill_only(self):
        self.release_replacement()
        path = self.claude_installed()
        (path / "skills" / "intake" / "SKILL.md").write_text("tampered\n")
        r = self.m.sync("claude-code")
        self.assertEqual(r.returncode, 0, self.m.log("claude-code"))
        rec = self.legacy("claude-code")
        self.assertEqual(rec["status"], "waiting")
        self.assertIn("does not match the repo", rec["skills"]["intake"]["state"])
        self.assertEqual(json.loads(self.settings.read_text())["skillOverrides"],
                         {"new-project": "off", "session-home": "off"})

    def test_claude_disabled_replacement_leaves_the_old_copies_on(self):
        self.release_replacement()
        self.claude_installed(enabled=False)
        r = self.m.sync("claude-code")
        self.assertEqual(r.returncode, 0, self.m.log("claude-code"))
        rec = self.legacy("claude-code")
        self.assertIn("installed but disabled", rec["skills"]["session-home"]["state"])
        self.assertFalse(self.settings.exists())

    def test_claude_explicit_user_choice_is_kept(self):
        self.release_replacement()
        self.claude_installed()
        self.settings.write_text(json.dumps({"skillOverrides": {"intake": "on"}}))
        self.assertEqual(self.m.sync("claude-code").returncode, 0, self.m.log("claude-code"))
        got = json.loads(self.settings.read_text())["skillOverrides"]
        self.assertEqual(got["intake"], "on")
        self.assertIn("left alone", self.legacy("claude-code")["skills"]["intake"]["state"])

    def test_claude_unreadable_settings_fail_visibly_and_retry_next_slot(self):
        self.release_replacement()
        self.claude_installed()
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.write_text("{ not json")
        r = self.m.sync("claude-code")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.settings.read_text(), "{ not json", "a file it cannot read is never rewritten")
        self.assertEqual(self.legacy("claude-code")["status"], "failed")
        self.assertIn("not valid JSON", self.m.log("claude-code"))
        delivery = self.m.receipt("claude-code-delivery.json")
        self.assertEqual(delivery["status"], "ok", "delivery itself stays honest")
        self.assertEqual(delivery["legacy_skills"]["status"], "failed")

        self.settings.write_text("{}")
        r = self.m.sync("claude-code")  # same commit, so only the failed migration forces the full run
        self.assertEqual(r.returncode, 0, self.m.log("claude-code"))
        self.assertEqual(json.loads(self.settings.read_text())["skillOverrides"]["intake"], "off")

    def test_claude_symlinked_settings_are_not_replaced(self):
        self.release_replacement()
        self.claude_installed()
        real = self.m.root / "dotfiles-settings.json"
        real.write_text("{}")
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.symlink_to(real)
        self.assertEqual(self.m.sync("claude-code").returncode, 1)
        self.assertTrue(self.settings.is_symlink())
        self.assertEqual(real.read_text(), "{}")

    # -------------------------------------------------------------- Codex

    def test_codex_first_migration_writes_exact_paths_and_is_idempotent(self):
        self.release_replacement()
        self.codex_installed()
        config = self.home / ".codex" / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text('model = "gpt"\n[[skills.config]]\npath = "/elsewhere/SKILL.md"\nenabled = false\n')
        before = config.read_bytes()
        self.m.take_calls()
        r = self.m.sync("codex")
        self.assertEqual(r.returncode, 0, self.m.log("codex"))
        expected = sorted(str(self.home / ".agents" / "skills" / n / "SKILL.md")
                          for n in ("intake", "new-project", "session-home"))
        self.assertEqual(sorted(self.writes()), expected, "only recognized copies, by exact path")
        rec = self.legacy("codex")
        self.assertEqual(rec["status"], "ok")
        self.assertIn("left alone, not recognized", rec["skills"]["verify-docs"]["state"])
        [backup] = rec["backups"]
        self.assertEqual(Path(backup["path"]).read_bytes(), before)
        self.assertTrue(config.read_bytes().startswith(before), "unrelated config is kept")
        self.assertCopiesUntouched()

        r = self.m.sync("codex", PLUGIN_SYNC_FORCE="1")
        self.assertEqual(r.returncode, 0, self.m.log("codex"))
        self.assertEqual(self.writes(), [], "a rerun writes nothing")
        self.assertEqual(self.legacy("codex")["skills"]["intake"]["state"], "already off")

    def test_codex_skipped_replacement_starts_no_app_server(self):
        def skip(folder):
            with open(folder / "codex-skip.txt", "a") as f:
                f.write("operating-doctrine\n")
        self.release_replacement()
        self.m.publish(VERSIONS, skip)
        self.codex_installed()
        self.m.take_calls()
        self.assertEqual(self.m.sync("codex").returncode, 0, self.m.log("codex"))
        self.assertFalse([c for c in self.m.take_calls() if c["args"][:1] == ["app-server"]])
        self.assertIn("codex-skip.txt", self.legacy("codex")["skills"]["intake"]["state"])

    def test_codex_disabled_or_wrong_replacement_waits(self):
        self.release_replacement()
        path = self.codex_installed(enabled=False)
        self.assertEqual(self.m.sync("codex").returncode, 0, self.m.log("codex"))
        self.assertEqual(self.writes(), [])
        self.assertIn("is disabled", self.legacy("codex")["skills"]["intake"]["state"])

        self.codex_installed()
        (path / "skills" / "new-project" / "SKILL.md").write_text("tampered\n")
        self.assertEqual(self.m.sync("codex", PLUGIN_SYNC_FORCE="1").returncode, 0, self.m.log("codex"))
        self.assertNotIn(str(self.home / ".agents" / "skills" / "new-project" / "SKILL.md"), self.writes())
        self.assertIn("does not match the repo", self.legacy("codex")["skills"]["new-project"]["state"])

    def test_codex_ignored_write_fails_then_retries(self):
        self.release_replacement()
        self.codex_installed()
        r = self.m.sync("codex", STUB_FAIL="skills-write-ignored")
        self.assertEqual(r.returncode, 1)
        rec = self.legacy("codex")
        self.assertEqual(rec["status"], "failed")
        self.assertIn("did not report the old copy as off", rec["skills"]["intake"]["state"])
        r = self.m.sync("codex")
        self.assertEqual(r.returncode, 0, self.m.log("codex"))
        self.assertEqual(self.legacy("codex")["skills"]["intake"]["state"], "turned off")

    def test_codex_app_server_failure_is_visible(self):
        self.release_replacement()
        self.codex_installed()
        r = self.m.sync("codex", STUB_FAIL="app-server")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.legacy("codex")["status"], "failed")
        self.assertCopiesUntouched()


class SettingsWrite(unittest.TestCase):
    """set_claude_overrides directly: a write that races Claude Code starts over."""

    def test_a_concurrent_edit_is_kept_and_the_update_is_redone(self):
        spec = importlib.util.spec_from_file_location("legacy_skills", HERE.parent / "legacy-skills.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        tmp = Path(ls.tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        settings = tmp / "settings.json"
        settings.write_text(json.dumps({"theme": "dark"}))
        real_read = mod.read_or_none
        calls = []

        def racing_read(path):
            calls.append(path)
            if len(calls) == 2:  # the pre-replace check of the first attempt
                settings.write_text(json.dumps({"theme": "dark", "model": "set meanwhile"}))
            return real_read(path)

        mod.read_or_none = racing_read
        backups = []
        states = mod.set_claude_overrides(str(settings), ["intake"], str(tmp / "b"), backups)
        self.assertEqual(states, {"intake": "turned off"})
        self.assertEqual(json.loads(settings.read_text()),
                         {"theme": "dark", "model": "set meanwhile", "skillOverrides": {"intake": "off"}})
        self.assertEqual(len(backups), 2, "each attempt backs up the bytes it read")
        self.assertFalse(list(tmp.glob("*.tmp")), "no temporary file is left behind")

if __name__ == "__main__":
    unittest.main()
