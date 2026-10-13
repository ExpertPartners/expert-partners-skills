import importlib.util
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


if __name__ == "__main__":
    unittest.main()
