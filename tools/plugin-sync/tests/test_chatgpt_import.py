import contextlib
import importlib.util
import io
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

    def test_only_named_front_matter_is_live(self):
        self.assertTrue(chk.is_live_skill(LIVE.format(n="a")))
        for text in ("# Title\n", "---\nname: a\n", "---\nname: [a\n---\n", "---\nname: a\n---\n"):
            with self.subTest(text=text):
                self.assertFalse(chk.is_live_skill(text))

    def test_current_repo_source_is_covered(self):
        self.assertEqual(chk.check_coverage(chk.ROOT), [])


SKILL = "---\nname: {n}\ndescription: Does {n}.\n---\n\nBody.\n"


def plugin_dir(manifest=None, skills=None):
    """A synthetic plugin: manifest fields and {directory: SKILL.md text} for its skills."""
    plug = Path(tempfile.mkdtemp()) / "demo"
    (plug / ".claude-plugin").mkdir(parents=True)
    m = {"name": "demo", "version": "1.2.3", "description": "Demo plugin."}
    m.update(manifest or {})
    (plug / ".claude-plugin" / "plugin.json").write_text(json.dumps(m))
    (plug / "skills").mkdir()
    for name, text in (skills if skills is not None else {"alpha": SKILL.format(n="alpha")}).items():
        (plug / "skills" / name).mkdir()
        if text is not None:
            (plug / "skills" / name / "SKILL.md").write_text(text)
    return plug


class PluginRules(unittest.TestCase):
    def test_valid_plugin_passes(self):
        plug = plugin_dir(skills={"alpha": SKILL.format(n="alpha"), "beta": SKILL.format(n="beta")})
        (plug / "skills" / "README.txt").write_text("not a skill directory")
        self.assertEqual(chk.check_plugin(plug), [])

    def test_manifest_fields_are_checked(self):
        cases = {
            "plugin name format": {"name": "-bad name"},
            "version must be semver": {"version": "v1"},
            "description missing or over 1024": {"description": "x" * 1025},
        }
        for message, manifest in cases.items():
            with self.subTest(message=message):
                self.assertEqual(chk.check_plugin(plugin_dir(manifest)), [f"demo: {message}"])
        self.assertIn("demo: description missing or over 1024", chk.check_plugin(plugin_dir({"description": " "})))

    def test_each_broken_skill_is_reported(self):
        cases = {
            "front matter missing": "name: alpha\n",
            "front matter unclosed": "---\nname: alpha\n",
            "front matter must be a mapping": "---\n- alpha\n---\nBody.\n",
            "name must be a non-empty string": "---\nname: ''\ndescription: D.\n---\nBody.\n",
            "description missing or over 1024": "---\nname: alpha\n---\nBody.\n",
            "empty body": "---\nname: alpha\ndescription: D.\n---\n\n",
            "plugin:skill identity over 64": SKILL.format(n="a" * 60),
        }
        for message, text in cases.items():
            with self.subTest(message=message):
                self.assertEqual(chk.check_plugin(plugin_dir(skills={"alpha": text})), [f"demo/alpha: {message}"])

    def test_missing_or_symlinked_skill_file_fails(self):
        self.assertEqual(chk.check_plugin(plugin_dir(skills={"alpha": None})),
                         ["demo/alpha: SKILL.md must be a regular file"])
        plug = plugin_dir()
        (plug / "skills" / "beta").mkdir()
        (plug / "skills" / "beta" / "SKILL.md").symlink_to(plug / "skills" / "alpha" / "SKILL.md")
        errs = chk.check_plugin(plug)
        self.assertIn("demo/beta: SKILL.md must be a regular file", errs)
        self.assertIn("demo: symlink skills/beta/SKILL.md", errs)

    def test_hidden_duplicate_and_nested_skills_fail(self):
        plug = plugin_dir(skills={".hidden": SKILL.format(n="hidden"), "alpha": SKILL.format(n="same"),
                                  "beta": SKILL.format(n="same")})
        (plug / "skills" / "beta" / "inner").mkdir()
        (plug / "skills" / "beta" / "inner" / "skill.md").write_text("nested")
        self.assertEqual(chk.check_plugin(plug), [
            "demo/.hidden: hidden skill directory",
            "demo/beta: duplicate skill name",
            "demo/beta: nested SKILL.md",
        ])

    def test_agent_yaml_problems_are_attached_to_the_plugin(self):
        plug = plugin_dir()
        (plug / "skills" / "alpha" / "agents").mkdir()
        (plug / "skills" / "alpha" / "agents" / "openai.yaml").write_text("interface: none\n")
        self.assertEqual(chk.check_plugin(plug), ["alpha/agents/openai.yaml: interface mapping required"])

    def test_every_repository_plugin_passes_and_main_exits_zero(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(chk.main(), 0, out.getvalue())
        self.assertIn("source coverage: OK", out.getvalue())
        self.assertNotIn("FAIL", out.getvalue())


class AgentYamlRules(unittest.TestCase):
    BASE = "interface:\n  display_name: X\n  short_description: Y\n"

    def errors(self, yaml_text, svg=SVG48):
        errs = []
        chk.check_agent_yaml(skill_with(yaml_text, svg), errs)
        return errs

    def test_each_rule_reports_its_own_message(self):
        cases = {
            "interface.display_name required string": "interface:\n  short_description: Y\n",
            "interface.icon_large must be a non-empty path": self.BASE + "  icon_large: ''\n",
            "interface.icon_small file missing": self.BASE + "  icon_small: ./assets/missing.svg\n",
            "interface.brand_color must be six-digit hex": self.BASE + "  brand_color: red\n",
            "policy may contain only products and allow_implicit_invocation": self.BASE + "policy:\n  extra: 1\n",
            "allow_implicit_invocation must be true or false": self.BASE + "policy:\n  allow_implicit_invocation: yes please\n",
            "policy.products must be CHAT, CODEX or both": self.BASE + "policy:\n  products: []\n",
            "only dependencies.tools is supported": self.BASE + "dependencies:\n  services: []\n",
            "interface mapping required": "- not a mapping\n",
        }
        for message, yaml_text in cases.items():
            with self.subTest(message=message):
                self.assertEqual(self.errors(yaml_text), [f"s/agents/openai.yaml: {message}"])

    def test_good_optional_fields_pass(self):
        text = (self.BASE + "  icon_large: ./assets/icon.svg\n  brand_color: '#1A2b3C'\n"
                "policy:\n  products: [CHAT]\n  allow_implicit_invocation: false\ndependencies:\n  tools: []\n")
        self.assertEqual(self.errors(text), [])

    def test_no_agent_file_is_fine(self):
        errs = []
        chk.check_agent_yaml(Path(tempfile.mkdtemp()), errs)
        self.assertEqual(errs, [])


class SvgRules(unittest.TestCase):
    def errors(self, svg, name="icon.svg"):
        path = Path(tempfile.mkdtemp()) / name
        path.write_text(svg)
        errs = []
        chk.check_svg(path, errs, "x")
        return errs

    def test_each_svg_rule(self):
        cases = {
            "x: svg root element missing": "<png/>",
            "x: svg is not square": '<svg width="64" height="48"/>',
        }
        for message, svg in cases.items():
            with self.subTest(message=message):
                self.assertEqual(self.errors(svg), [message])

    def test_square_svg_without_viewbox_passes(self):
        self.assertEqual(self.errors('<svg width="48" height="48"/>'), [])

    def test_comma_separated_viewbox_is_read(self):
        self.assertEqual(self.errors('<svg viewBox="0,0,24,24"/>'), ["x: svg is smaller than 48x48"])

    def test_non_svg_icons_are_not_parsed(self):
        self.assertEqual(self.errors("binary", name="icon.png"), [])


if __name__ == "__main__":
    unittest.main()
