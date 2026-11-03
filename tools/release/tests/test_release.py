"""Tests for the release step. Each test builds a small repository in a temporary folder.

Run from the repo root: python3 -m unittest discover -s tools/release/tests -v
"""

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "release", os.path.join(os.path.dirname(__file__), "..", "release.py"))
release = importlib.util.module_from_spec(spec)
sys.modules["release"] = release
spec.loader.exec_module(release)

DATE = "2026-11-03"

MARKETPLACE = {
    "name": "expert-partners",
    "plugins": [
        {"name": "operating-doctrine", "source": "./plugins/operating-doctrine", "version": "2.78.0", "description": "d"},
        {"name": "brand-voice", "source": "./plugins/brand-voice", "description": "d", "version": "0.6.7"},
    ],
}
DOCTRINE_LOG = "## 2.78.0 - 2026-11-02\n\nOlder entry.\n## 2.77.0 - 2026-11-01\n\nOldest entry.\n"
COMPACT_MANIFEST = '{\n  "name": "brand-voice",\n  "version": "0.6.7",\n  "author": { "name": "A" }\n}\n'


def note(bumps: dict, body: str) -> str:
    return "---\n" + "".join(f"{k}: {v}\n" for k, v in bumps.items()) + "---\n\n" + body + "\n"


class Repo(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.write(".claude-plugin/marketplace.json", json.dumps(MARKETPLACE, indent=2) + "\n")
        self.write("plugins/operating-doctrine/.claude-plugin/plugin.json",
                   json.dumps({"name": "operating-doctrine", "version": "2.78.0"}, indent=2) + "\n")
        self.write("plugins/operating-doctrine/CHANGELOG.md", DOCTRINE_LOG)
        self.write("plugins/brand-voice/.claude-plugin/plugin.json", COMPACT_MANIFEST)
        self.write(".changeset/README.md", "# Changesets\n\nNot a note.\n")

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")

    def version(self, plugin):
        market = json.loads(self.read(".claude-plugin/marketplace.json"))
        listed = next(p["version"] for p in market["plugins"] if p["name"] == plugin)
        manifest = json.loads(self.read(f"plugins/{plugin}/.claude-plugin/plugin.json"))["version"]
        self.assertEqual(listed, manifest, "marketplace and plugin.json must agree")
        return listed

    def run_release(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = release.main(["--root", str(self.root), "--date", DATE, *extra])
        return code, out.getvalue(), err.getvalue()

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_text(encoding="utf-8")
                for p in self.root.rglob("*") if p.is_file() and ".git" not in p.parts}


class Releases(Repo):
    def test_one_note_bumps_both_files_and_adds_one_entry(self):
        self.write(".changeset/159-one-owner.md", note({"operating-doctrine": "minor"}, "Adds the release step."))
        code, out, _ = self.run_release()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.version("operating-doctrine"), "2.79.0")
        self.assertEqual(self.read("plugins/operating-doctrine/CHANGELOG.md"),
                         "## 2.79.0 - 2026-11-03\n\nAdds the release step.\n" + DOCTRINE_LOG)
        self.assertFalse((self.root / ".changeset/159-one-owner.md").exists(), "a used note is removed")
        self.assertTrue((self.root / ".changeset/README.md").exists(), "the README is never a note")
        self.assertEqual(self.version("brand-voice"), "0.6.7", "a plugin no note names is untouched")

    def test_two_notes_for_one_plugin_make_one_bump_at_the_largest_level(self):
        self.write(".changeset/160-a.md", note({"operating-doctrine": "patch"}, "First change."))
        self.write(".changeset/161-b.md", note({"operating-doctrine": "minor"}, "Second change."))
        self.assertEqual(self.run_release()[0], 0)
        self.assertEqual(self.version("operating-doctrine"), "2.79.0")
        log = self.read("plugins/operating-doctrine/CHANGELOG.md")
        self.assertTrue(log.startswith("## 2.79.0 - 2026-11-03\n\nFirst change.\n\nSecond change.\n## 2.78.0"))
        self.assertEqual(log.count("## 2.79.0"), 1)
        self.assertEqual(list((self.root / ".changeset").glob("*.md")), [self.root / ".changeset/README.md"])

    def test_major_bump_resets_minor_and_patch(self):
        self.write(".changeset/1-x.md", note({"brand-voice": "major"}, "Breaking."))
        self.assertEqual(self.run_release()[0], 0)
        self.assertEqual(self.version("brand-voice"), "1.0.0")

    def test_one_note_can_name_several_plugins_and_creates_a_missing_changelog(self):
        self.write(".changeset/2-x.md", note({'"operating-doctrine"': "patch", "brand-voice": "minor"}, "Shared edit."))
        self.assertEqual(self.run_release()[0], 0)
        self.assertEqual(self.version("operating-doctrine"), "2.78.1")
        self.assertEqual(self.version("brand-voice"), "0.7.0")
        self.assertEqual(self.read("plugins/brand-voice/CHANGELOG.md"), "## 0.7.0 - 2026-11-03\n\nShared edit.\n")

    def test_manifest_layout_is_kept(self):
        self.write(".changeset/3-x.md", note({"brand-voice": "patch"}, "Fix."))
        self.assertEqual(self.run_release()[0], 0)
        self.assertEqual(self.read("plugins/brand-voice/.claude-plugin/plugin.json"),
                         COMPACT_MANIFEST.replace("0.6.7", "0.6.8"))

    def test_marketplace_changes_only_the_version(self):
        self.write(".changeset/4-x.md", note({"brand-voice": "patch"}, "Fix."))
        self.assertEqual(self.run_release()[0], 0)
        expected = json.loads(json.dumps(MARKETPLACE))
        expected["plugins"][1]["version"] = "0.6.8"
        self.assertEqual(self.read(".claude-plugin/marketplace.json"), json.dumps(expected, indent=2) + "\n")

    def test_no_notes_changes_nothing(self):
        before = self.snapshot()
        code, out, _ = self.run_release()
        self.assertEqual(code, 0)
        self.assertIn("nothing to release", out)
        self.assertEqual(self.snapshot(), before)

    def test_check_writes_nothing(self):
        self.write(".changeset/5-x.md", note({"operating-doctrine": "minor"}, "Change."))
        before = self.snapshot()
        code, out, _ = self.run_release("--check")
        self.assertEqual(code, 0)
        self.assertIn("operating-doctrine 2.78.0 -> 2.79.0", out)
        self.assertEqual(self.snapshot(), before)


class Refuses(Repo):
    def assert_refused(self, fragment):
        before = self.snapshot()
        code, _, err = self.run_release()
        self.assertEqual(code, 1)
        self.assertIn(fragment, err)
        self.assertEqual(self.snapshot(), before, "a bad note changes nothing")

    def test_unknown_plugin(self):
        self.write(".changeset/6-x.md", note({"no-such-plugin": "patch"}, "Change."))
        self.assert_refused("is not a plugin")

    def test_bad_bump(self):
        self.write(".changeset/7-x.md", note({"brand-voice": "huge"}, "Change."))
        self.assert_refused("use patch, minor or major")

    def test_empty_body(self):
        self.write(".changeset/8-x.md", note({"brand-voice": "patch"}, ""))
        self.assert_refused("says nothing about the change")

    def test_missing_frontmatter(self):
        self.write(".changeset/9-x.md", "Just text.\n")
        self.assert_refused("must start with a --- line")

    def test_no_plugin_named(self):
        self.write(".changeset/10-x.md", "---\n---\n\nText.\n")
        self.assert_refused("names no plugin")

    def test_one_bad_note_stops_every_note(self):
        self.write(".changeset/11-good.md", note({"brand-voice": "patch"}, "Fine."))
        self.write(".changeset/12-bad.md", note({"brand-voice": "sideways"}, "Bad."))
        self.assert_refused("sideways")

    def test_versions_that_disagree(self):
        self.write("plugins/brand-voice/.claude-plugin/plugin.json", COMPACT_MANIFEST.replace("0.6.7", "0.6.9"))
        self.write(".changeset/13-x.md", note({"brand-voice": "patch"}, "Fix."))
        self.assert_refused("must carry one version")

    def test_entry_for_the_new_version_already_exists(self):
        self.write("plugins/operating-doctrine/CHANGELOG.md", "## 2.79.0 - 2026-11-03\n\nHand edit.\n" + DOCTRINE_LOG)
        self.write(".changeset/14-x.md", note({"operating-doctrine": "minor"}, "Change."))
        self.assert_refused("already has an entry for 2.79.0")


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


@unittest.skipIf(shutil.which("git") is None, "needs git")
class ParallelPullRequests(Repo):
    """Two builder branches that each add a note merge into main without conflict,
    and one release on main then makes a single bump that carries both notes."""

    def test_two_changesets_merge_without_conflict(self):
        r = self.root
        self.assertEqual(git(r, "init", "-q", "-b", "main").returncode, 0)
        if git(r, "var", "GIT_AUTHOR_IDENT").returncode != 0:
            self.skipTest("git has no global identity to commit with in a scratch repository")
        git(r, "add", "-A")
        self.assertEqual(git(r, "commit", "-q", "-m", "base").returncode, 0)
        for branch, issue in (("job/a", 201), ("job/b", 202)):
            git(r, "checkout", "-q", "-b", branch, "main")
            self.write(f".changeset/{issue}-change.md", note({"operating-doctrine": "minor"}, f"Change from #{issue}."))
            git(r, "add", "-A")
            self.assertEqual(git(r, "commit", "-q", "-m", branch).returncode, 0)
        git(r, "checkout", "-q", "main")
        for branch in ("job/a", "job/b"):
            merged = git(r, "merge", "--no-ff", "-q", "-m", f"merge {branch}", branch)
            self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
        self.assertEqual(git(r, "diff", "--name-only", "--diff-filter=U").stdout, "")
        self.assertEqual(self.run_release()[0], 0)
        self.assertEqual(self.version("operating-doctrine"), "2.79.0")
        log = self.read("plugins/operating-doctrine/CHANGELOG.md")
        self.assertTrue(log.startswith("## 2.79.0 - 2026-11-03\n\nChange from #201.\n\nChange from #202.\n## 2.78.0"))


if __name__ == "__main__":
    unittest.main()
