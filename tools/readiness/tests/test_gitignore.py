"""Tests for the root .gitignore. Each case runs git against a throwaway repository that
carries a copy of the root .gitignore, so nothing touches the real working tree.

Run from the repo root: python3 -m unittest discover -s tools/readiness/tests -v
"""

import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
GITIGNORE = os.path.join(ROOT, ".gitignore")

# A user's global excludes file must not change what these tests prove about the repo file.
GIT = ["git", "-c", f"core.excludesFile={os.devnull}"]

IGNORED = [
    ".env",
    ".env.local",
    ".env.production",
    "tools/capability-feed/.env",
    "tools/capability-feed/.env.local",
    ".envrc",
    "tools/skill-map/settings.local.env",
    "node_modules/left-pad/index.js",
    "tools/skill-map/node_modules/d3/package.json",
    "tools/capability-feed/node_modules/.package-lock.json",
    "plugins/research-ops/skills/video-discovery/node_modules/x/index.js",
    ".venv/bin/python",
    "venv/lib/site.py",
    "plugins/research-ops/skills/source-hunter/.venv/pyvenv.cfg",
    "tools/release/__pycache__/release.cpython-312.pyc",
    "tools/release/release.pyc",
    ".pytest_cache/v/cache/lastfailed",
    "tools/release/.mypy_cache/3.12/release.meta.json",
    ".ruff_cache/0.6.0/123",
    ".tox/py312/log.txt",
    ".coverage",
    "htmlcov/index.html",
    "tools/release/release.egg-info/PKG-INFO",
    "npm-debug.log",
    "tools/skill-map/npm-debug.log.1",
    "tools/capability-feed/coverage/lcov.info",
    "tools/skill-map/.eslintcache",
    "tools/skill-map/tsconfig.tsbuildinfo",
    "build/lib/thing.py",
    "dist/package.tar.gz",
    "tools/skill-map/dist/bundle.js",
    "tools/capability-feed/.cache/feed.tmp",
]

TRACKABLE = [
    ".env.example",
    ".env.sample",
    ".env.template",
    "tools/capability-feed/.env.example",
    ".gitignore",
    "README.md",
    "AGENTS.md",
    ".github/workflows/ci.yml",
    ".changeset/README.md",
    ".claude-plugin/marketplace.json",
    "skills/intake/SKILL.md",
    "plugins/operating-doctrine/skills/operating-doctrine/SKILL.md",
    "plugins/operating-doctrine/.claude-plugin/plugin.json",
    "tools/release/release.py",
    "tools/validate-job.sh",
    "tools/capability-feed/lib/build-feed.mjs",
    "tools/capability-feed/package.json",
    "tools/capability-feed/package-lock.json",
    "tools/capability-feed/ai-workforce-feed.json",
    "tools/skill-map/skills-graph.json",
    "tools/skill-map/extract-skills-graph.mjs",
]

PRODUCER_OWNED = [
    "tools/capability-feed/ai-workforce-feed.json",
    "tools/skill-map/skills-graph.json",
]


def git(cwd, *args):
    return subprocess.run(GIT + list(args), cwd=cwd, capture_output=True, text=True)


class SyntheticRepoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="gitignore-test-")
        result = git(cls.tmp, "init", "-q")
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        shutil.copyfile(GITIGNORE, os.path.join(cls.tmp, ".gitignore"))
        for rel in IGNORED + TRACKABLE:
            if rel == ".gitignore":
                continue
            path = os.path.join(cls.tmp, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                fh.write("fixture\n")
        result = git(cls.tmp, "add", "-A")
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        cls.staged = set(git(cls.tmp, "ls-files").stdout.splitlines())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_check_ignore_matches_secrets_dependencies_and_build_output(self):
        for rel in IGNORED:
            with self.subTest(path=rel):
                result = git(self.tmp, "check-ignore", "-q", "--no-index", rel)
                self.assertEqual(result.returncode, 0, f"{rel} should be ignored")

    def test_ignored_fixtures_are_not_staged(self):
        for rel in IGNORED:
            with self.subTest(path=rel):
                self.assertNotIn(rel, self.staged)

    def test_check_ignore_leaves_templates_and_sources_trackable(self):
        for rel in TRACKABLE:
            with self.subTest(path=rel):
                result = git(self.tmp, "check-ignore", "-q", "--no-index", rel)
                self.assertEqual(result.returncode, 1, f"{rel} should not be ignored: {result.stdout}")

    def test_templates_and_sources_are_staged(self):
        for rel in TRACKABLE:
            with self.subTest(path=rel):
                self.assertIn(rel, self.staged)


@unittest.skipUnless(os.path.isdir(os.path.join(ROOT, ".git")) or os.path.isfile(os.path.join(ROOT, ".git")),
                     "needs a git checkout of the repository")
class RealRepoTest(unittest.TestCase):
    def test_no_tracked_file_matches_an_ignore_rule(self):
        result = git(ROOT, "ls-files", "--cached", "--ignored", "--exclude-standard")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [])

    def test_producer_owned_artifacts_stay_tracked(self):
        tracked = set(git(ROOT, "ls-files").stdout.splitlines())
        for rel in PRODUCER_OWNED:
            with self.subTest(path=rel):
                self.assertIn(rel, tracked)
                result = git(ROOT, "check-ignore", "-q", "--no-index", rel)
                self.assertEqual(result.returncode, 1, f"{rel} is matched by an ignore rule")


if __name__ == "__main__":
    unittest.main()
