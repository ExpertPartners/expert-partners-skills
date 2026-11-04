import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "chk", Path(__file__).resolve().parents[1] / "chatgpt-import-check.py"
)
chk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chk)

OLD = """interface:
  display_name: X
  short_description: Y
  icon_small: assets/icon.svg
policy:
  products:
  - chatgpt
  - codex
  - api
  - atlas
  allow_implicit_invocation: true
"""
SVG24 = '<svg width="24" height="24" viewBox="0 0 24 24"><path d="M0 0"/></svg>'
SVG48 = '<svg width="48" height="48" viewBox="0 0 24 24"><path d="M0 0"/></svg>'


def skill_with(yaml_text, svg):
    d = Path(tempfile.mkdtemp()) / "s"
    (d / "agents").mkdir(parents=True)
    (d / "assets").mkdir()
    (d / "agents" / "openai.yaml").write_text(yaml_text)
    (d / "assets" / "icon.svg").write_text(svg)
    return d


class ChatgptImportRules(unittest.TestCase):
    def test_old_file_fails(self):
        errs = []
        chk.check_agent_yaml(skill_with(OLD, SVG24), errs)
        text = "\n".join(errs)
        self.assertIn("policy.products", text)
        self.assertIn("must start with ./", text)

    def test_fixed_file_passes(self):
        fixed = OLD.split("policy:")[0].replace("assets/", "./assets/")
        fixed += "policy:\n  allow_implicit_invocation: true\n"
        errs = []
        chk.check_agent_yaml(skill_with(fixed, SVG48), errs)
        self.assertEqual(errs, [])

    def test_small_svg_flagged(self):
        errs = []
        chk.check_svg(skill_with(OLD, SVG24) / "assets" / "icon.svg", errs, "x")
        self.assertTrue(any("48x48" in e for e in errs))

    def test_chat_and_codex_products_allowed(self):
        y = OLD.split("policy:")[0].replace("assets/", "./assets/")
        y += "policy:\n  products:\n  - CHAT\n  - CODEX\n"
        errs = []
        chk.check_agent_yaml(skill_with(y, SVG48), errs)
        self.assertEqual(errs, [])


LIVE = "---\nname: {n}\ndescription: Does {n}.\n---\n\nBody.\n"


def coverage_root(listed=("p",), extra_plugins=()):
    root = Path(tempfile.mkdtemp())
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "marketplace.json").write_text(json.dumps(
        {"plugins": [{"name": n, "source": f"./plugins/{n}"} for n in listed]}))
    for n in tuple(listed) + tuple(extra_plugins):
        (root / "plugins" / n / ".claude-plugin").mkdir(parents=True)
        (root / "plugins" / n / ".claude-plugin" / "plugin.json").write_text("{}")
        (root / "plugins" / n / "skills" / "a").mkdir(parents=True)
        (root / "plugins" / n / "skills" / "a" / "SKILL.md").write_text(LIVE.format(n="a"))
    return root


def put(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class SourceCoverage(unittest.TestCase):
    def test_packaged_skills_pass(self):
        self.assertEqual(chk.check_coverage(coverage_root()), [])

    def test_omitted_live_root_skill_fails(self):
        root = coverage_root()
        put(root, "skills/intake/SKILL.md", LIVE.format(n="intake"))
        self.assertEqual(chk.check_coverage(root),
                         ["skills/intake/SKILL.md: live skill has no marketplace plugin bundle"])

    def test_live_skill_in_unlisted_plugin_fails(self):
        errs = chk.check_coverage(coverage_root(extra_plugins=("q",)))
        self.assertIn("plugins/q: plugin is not listed in .claude-plugin/marketplace.json", errs)
        self.assertIn("plugins/q/skills/a/SKILL.md: live skill has no marketplace plugin bundle", errs)

    def test_historical_and_deployed_evidence_pass(self):
        root = coverage_root()
        put(root, "operating-doctrine/SKILL.md",
            "# operating-doctrine has one true copy\n\nRetired; see plugins/operating-doctrine.\n")
        put(root, "archive/skills/old/SKILL.md",
            "# DEPLOYED COPY (2026-09-04, skill-deploy pipeline): the canonical home is\n"
            + LIVE.format(n="old"))
        put(root, ".agents/skills/intake/SKILL.md", LIVE.format(n="intake"))
        self.assertEqual(chk.check_coverage(root), [])

    def test_current_repo_source_is_covered(self):
        self.assertEqual(chk.check_coverage(chk.ROOT), [])


if __name__ == "__main__":
    unittest.main()
