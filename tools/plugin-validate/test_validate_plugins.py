#!/usr/bin/env python3
"""Tests for validate_plugins.py. Run: python3 -m unittest discover tools/plugin-validate"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_plugins as vp  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def make_repo(root: Path, *, mp_version="1.0.0", pj_version="1.0.0", skill_name="alpha-skill",
              folder="alpha-skill", description="Does one job.", readme=True, extra_dir=False,
              frontmatter: str | None = None) -> Path:
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
    if frontmatter is None:
        frontmatter = f"name: {skill_name}\ndescription: >-\n  {description}\n# --- comment ---\ntier: plugin"
    (sdir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\n# Body\n")
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



try:
    import yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

# Parser modes every frontmatter regression runs under: the standard-library
# fallback always, and PyYAML when it is installed (CI installs it).
PARSER_MODES = [False] + ([True] if HAVE_YAML else [])


class SemverTest(unittest.TestCase):
    """Codex P2: versions must be SemVer 2.0.0, not a permissive lookalike."""

    VALID = ["0.0.0", "1.0.0", "10.20.30", "1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-0.3.7",
             "1.0.0-x.7.z.92", "1.0.0-x-y-z.--", "1.0.0-alpha+001", "1.0.0+20130313144700",
             "1.0.0-beta+exp.sha.5114f85", "1.0.0+21AF26D3----117B344092BD", "2.49.0"]
    INVALID = ["01.0.0", "1.01.0", "1.0.01", "1.0.0-01", "1.0.0-alpha.01", "1.0.0-", "1.0.0-a..b",
               "1.0.0-alpha.", "1.0.0+", "1.0.0+a_b", "1.0.0+.", "1.0.0-alpha..1", "1.0", "1",
               "v1.0.0", "1.0.0 ", "1.0.0\n", "1.0.0-a_b", "\u0661.0.0", ""]

    def test_valid_versions_accepted(self):
        for v in self.VALID:
            with self.subTest(v=v):
                self.assertTrue(vp.is_semver(v), v)

    def test_invalid_versions_rejected(self):
        for v in self.INVALID:
            with self.subTest(v=v):
                self.assertFalse(vp.is_semver(v), repr(v))

    def test_leading_zero_version_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = vp.validate(make_repo(Path(tmp), mp_version="01.0.0", pj_version="01.0.0"))
        self.assertTrue(any("not semver" in e for e in errors), errors)

    def test_numeric_prerelease_leading_zero_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = vp.validate(make_repo(Path(tmp), mp_version="1.0.0-01", pj_version="1.0.0-01"))
        self.assertTrue(any("not semver" in e for e in errors), errors)


class InlineCommentTest(unittest.TestCase):
    """Codex P2: inline YAML comments are not part of the value; '#' inside
    quotes or without preceding whitespace is."""

    CASES = {
        "name: alpha-skill # stable id": "alpha-skill",
        "name: alpha-skill\t# tab comment": "alpha-skill",
        'name: "a # b"': "a # b",
        "name: 'a # b'": "a # b",
        'name: "a # b" # trailing': "a # b",
        'name: "say \\"hi\\" # x" # c': 'say "hi" # x',
        "name: 'it''s # x' # c": "it's # x",
        "name: a#b": "a#b",
        "name: a#b # c": "a#b",
    }

    def test_scalar_values(self):
        for use_yaml in PARSER_MODES:
            for line, want in self.CASES.items():
                with self.subTest(line=line, use_yaml=use_yaml):
                    fm = vp.read_frontmatter(f"---\n{line}\n---\n", use_yaml=use_yaml)
                    self.assertEqual(fm["name"], want)

    def test_commented_name_matches_folder(self):
        for use_yaml in PARSER_MODES:
            with self.subTest(use_yaml=use_yaml), mock.patch.object(vp, "_HAVE_YAML", use_yaml):
                with tempfile.TemporaryDirectory() as tmp:
                    errors, _ = vp.validate(make_repo(
                        Path(tmp), frontmatter="name: alpha-skill # stable id\ndescription: Does one job."))
                self.assertEqual(errors, [])

    def test_quoted_hash_name_is_compared_whole(self):
        for use_yaml in PARSER_MODES:
            with self.subTest(use_yaml=use_yaml), mock.patch.object(vp, "_HAVE_YAML", use_yaml):
                with tempfile.TemporaryDirectory() as tmp:
                    errors, _ = vp.validate(make_repo(
                        Path(tmp), frontmatter='name: "alpha-skill # x"\ndescription: Does one job.'))
                self.assertTrue(any("!= folder" in e for e in errors), errors)


def long_plain_description(total: int) -> str:
    """A plain (unquoted) description spanning many indented lines whose
    folded length is exactly `total` characters and whose first line is short."""
    text = " ".join(f"word{i:05d}" for i in range(total // 10 + 1))[:total]
    text = text.rstrip() + "y" * (total - len(text.rstrip()))
    assert len(text) == total
    # Break only at spaces, so folding (one space per line break) rebuilds text.
    lines, cur = [], ""
    for tok in text.split(" "):
        if cur and len(cur) + 1 + len(tok) > 60:
            lines.append(cur)
            cur = tok
        else:
            cur = f"{cur} {tok}" if cur else tok
    lines.append(cur)
    return "description: " + lines[0] + "".join(f"\n  {ln}" for ln in lines[1:])


class PlainMultilineTest(unittest.TestCase):
    """Claude nit: a plain multi-line description must be read in full, so the
    1024-character cap measures the whole value, not its first line."""

    def test_folding_rules(self):
        for use_yaml in PARSER_MODES:
            with self.subTest(use_yaml=use_yaml):
                fm = vp.read_frontmatter("---\ndescription: one\n  two\n\n  three\n    four\nname: x\n---\n",
                                         use_yaml=use_yaml)
                self.assertEqual(fm["description"], "one two\nthree four")
                fm = vp.read_frontmatter("---\ndescription:\n  starts below\n  the key\n---\n", use_yaml=use_yaml)
                self.assertEqual(fm["description"], "starts below the key")
                fm = vp.read_frontmatter("---\ndescription: one\n  two # comment\nname: x\n---\n", use_yaml=use_yaml)
                self.assertEqual(fm["description"], "one two")

    def test_block_and_quoted_multiline_still_supported(self):
        cases = {
            "description: >-\n  a\n  b\n\n  c\nname: x": "a b\nc",
            "description: >\n  a\n  b\nname: x": "a b\n",
            "description: |\n  a\n  b\nname: x": "a\nb\n",
            "description: |-\n  a\n  b\nname: x": "a\nb",
            "description: |+\n  a\n\nname: x": "a\n\n",
            'description: "one\n  two\n\n  three"\nname: x': "one two\nthree",
            "description: 'it''s\n  here'\nname: x": "it's here",
        }
        for use_yaml in PARSER_MODES:
            for block, want in cases.items():
                with self.subTest(block=block, use_yaml=use_yaml):
                    fm = vp.read_frontmatter(f"---\n{block}\n---\n", use_yaml=use_yaml)
                    self.assertEqual(fm["description"], want)

    def test_over_cap_only_when_fully_read(self):
        fm_text = "name: alpha-skill\n" + long_plain_description(1100)
        first_line = fm_text.splitlines()[1][len("description: "):]
        self.assertLess(len(first_line), 100)
        for use_yaml in PARSER_MODES:
            with self.subTest(use_yaml=use_yaml), mock.patch.object(vp, "_HAVE_YAML", use_yaml):
                parsed = vp.read_frontmatter(f"---\n{fm_text}\n---\n", use_yaml=use_yaml)
                self.assertEqual(len(parsed["description"]), 1100)
                with tempfile.TemporaryDirectory() as tmp:
                    errors, _ = vp.validate(make_repo(Path(tmp), frontmatter=fm_text))
                self.assertTrue(any("description 1100 chars" in e for e in errors), errors)

    def test_under_cap_multiline_passes(self):
        fm_text = "name: alpha-skill\n" + long_plain_description(1000)
        for use_yaml in PARSER_MODES:
            with self.subTest(use_yaml=use_yaml), mock.patch.object(vp, "_HAVE_YAML", use_yaml):
                with tempfile.TemporaryDirectory() as tmp:
                    errors, _ = vp.validate(make_repo(Path(tmp), frontmatter=fm_text))
                self.assertEqual(errors, [])


@unittest.skipUnless(HAVE_YAML, "PyYAML not installed; agreement check needs it")
class FallbackAgreesWithPyYAMLTest(unittest.TestCase):
    """The fallback must read exactly what PyYAML reads, on every SKILL.md in
    the repo and on a corpus of edge cases."""

    CORPUS = [
        "name: x # id", 'name: "a # b"', "name: a#b", "description: one\n  two\n\n\n  three",
        'description: "\n  foo"', 'description: "foo\n  "', 'description: "a\\\n  b"',
        "description: >2\n   a\n  b", "description: > # c\n  a\n  b", "description: >\n\n  a\n  b",
        "description: >\n  a\n   b\n  c\nname: d", "description: >\n  a\n\n   b\n\n  c\nname: d",
        "description: |+\n  a\n\n", "description: >+\n  a\n\nname: q", 'description: "\\u00e9t\\u00e9"',
        "name: x\n# comment\ndescription: y", "description: a # c\nname: b",
    ]

    KEYS = ("name", "description")  # the only keys the validator reads

    def _yaml(self, block: str) -> dict:
        data = yaml.safe_load(block)
        return {k: data[k] for k in self.KEYS if isinstance(data.get(k), str)}

    def _fallback(self, lines: list[str]) -> dict:
        data = vp.read_frontmatter_fallback(lines)
        return {k: data[k] for k in self.KEYS if k in data}

    def test_corpus(self):
        for block in self.CORPUS:
            with self.subTest(block=block):
                self.assertEqual(self._fallback(block.split("\n")), self._yaml(block))

    def test_every_repo_skill(self):
        files = sorted(REPO.glob("plugins/*/skills/*/SKILL.md")) + sorted(REPO.glob("skills/*/SKILL.md"))
        self.assertTrue(files)
        for sf in files:
            fm = vp.frontmatter_lines(sf.read_text(encoding="utf-8"))
            if fm is None:
                continue
            with self.subTest(skill=str(sf.relative_to(REPO))):
                self.assertEqual(self._fallback(fm), self._yaml("\n".join(fm)))


if __name__ == "__main__":
    unittest.main()
