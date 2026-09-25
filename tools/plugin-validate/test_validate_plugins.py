#!/usr/bin/env python3
"""Tests for validate_plugins.py. Run: python3 -m unittest discover tools/plugin-validate"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_plugins as vp  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def make_repo(root: Path, *, mp_version="1.0.0", pj_version="1.0.0", skill_name="alpha-skill",
              folder="alpha-skill", description="Does one job.", readme=True, extra_dir=False) -> Path:
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "marketplace.json").write_text(json.dumps({
        "name": "fixture",
        "plugins": [{"name": "alpha", "source": "./plugins/alpha", "version": mp_version,
                     "description": "Alpha plugin."}],
    }))
    pdir = root / "plugins" / "alpha"
    (pdir / ".claude-plugin").mkdir(parents=True)
    (pdir / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": "alpha", "version": pj_version, "description": "Alpha plugin.",
        "author": {"name": "Fixture"},
    }))
    sdir = pdir / "skills" / folder
    sdir.mkdir(parents=True)
    (sdir / "SKILL.md").write_text(
        f"---\nname: {skill_name}\ndescription: >-\n  {description}\n# --- comment ---\ntier: plugin\n---\n\n# Body\n")
    if readme:
        (pdir / "README.md").write_text("# Alpha\n")
    if extra_dir:
        (root / "plugins" / "orphan").mkdir()
    return root


class ValidatePluginsTest(unittest.TestCase):
    def run_fixture(self, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            return vp.validate(make_repo(Path(tmp), **kw))

    def test_clean_fixture(self):
        errors, warnings = self.run_fixture()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_version_drift_is_error(self):
        errors, _ = self.run_fixture(pj_version="1.0.1")
        self.assertTrue(any("bump both files" in e for e in errors), errors)

    def test_non_semver_is_error(self):
        errors, _ = self.run_fixture(mp_version="1.0", pj_version="1.0")
        self.assertTrue(any("not semver" in e for e in errors), errors)

    def test_name_folder_mismatch_is_error(self):
        errors, _ = self.run_fixture(skill_name="other-name")
        self.assertTrue(any("!= folder" in e for e in errors), errors)

    def test_description_cap_is_error(self):
        errors, _ = self.run_fixture(description="x" * 1024)
        self.assertTrue(any("cap 1024" in e for e in errors), errors)

    def test_orphan_plugin_dir_is_error(self):
        errors, _ = self.run_fixture(extra_dir=True)
        self.assertTrue(any("not listed in marketplace.json" in e for e in errors), errors)

    def test_missing_readme_is_warning_only(self):
        errors, warnings = self.run_fixture(readme=False)
        self.assertEqual(errors, [])
        self.assertTrue(any("README.md" in w for w in warnings), warnings)

    def test_frontmatter_forms(self):
        fm = vp.read_frontmatter('---\nname: a\ndescription: "Say \\"hi\\" -- ok"\n---\n')
        self.assertEqual(fm["description"], 'Say "hi" -- ok')
        fm = vp.read_frontmatter("---\nname: b\ndescription: >-\n  one\n  two\n---\n")
        self.assertEqual(fm["description"], "one two")
        self.assertIsNone(vp.read_frontmatter("# no frontmatter\n"))

    def test_live_repo_has_no_errors(self):
        errors, _ = vp.validate(REPO)
        self.assertEqual(errors, [], "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
