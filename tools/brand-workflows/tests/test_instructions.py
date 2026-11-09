"""Synthetic parser fixtures, not evidence of company output or voice fidelity."""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "plugins/brand-voice/skills/custom-instruction-builder/scripts/validate_instructions.py"
spec = importlib.util.spec_from_file_location("validate_instructions", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NAME = "marketing-workspace-custom-instructions.md"


def fixture(voice_words=80, total=None):
    content = ["# Fixture Marketing Workspace"]
    for heading in module.HEADINGS:
        content.append(f"## {heading}")
        if heading == "VOICE":
            content.append(" ".join(["voice"] * voice_words))
        elif heading == "GROUND RULES":
            content.append("### Always Do\nVerify facts.\n### Never Do\nInvent evidence.")
        else:
            content.append("Use verified evidence.")
    text = "\n\n".join(content) + "\n"
    if total is not None:
        text += " ".join(["context"] * (total - module.word_count(text))) + "\n"
    return text


class InstructionsTest(unittest.TestCase):
    def test_inclusive_voice_boundaries(self):
        for count in (80, 120):
            with self.subTest(count=count):
                self.assertTrue(module.validate(fixture(count), NAME)["valid"])

    def test_voice_outside_boundaries(self):
        for count in (0, 79, 121):
            with self.subTest(count=count):
                self.assertFalse(module.validate(fixture(count), NAME)["valid"])

    def test_total_boundary(self):
        self.assertTrue(module.validate(fixture(total=1000), NAME)["valid"])
        self.assertFalse(module.validate(fixture(total=1001), NAME)["valid"])

    def test_heading_order_missing_and_duplicate(self):
        good = fixture()
        for bad in (
            good.replace("## ICP", "## Audience"),
            good.replace("## ICP", "## VOICE"),
            good.replace("## VOICE", "## ICP", 1),
            good + "\n## VOICE\nextra\n",
        ):
            self.assertFalse(module.validate(bad, NAME)["valid"])

    def test_ground_rules_order(self):
        self.assertFalse(module.validate(fixture().replace("### Always Do", "### Never Do"), NAME)["valid"])

    def test_inventory_leaks(self):
        for leak in ("about-us.md", "Source.PDF", "https://example.invalid", "Voice-Guide.docx"):
            with self.subTest(leak=leak):
                self.assertFalse(module.validate(fixture() + leak, NAME)["valid"])

    def test_placeholders_and_fences(self):
        for bad in ("[Company Name]", "[MISSING proof]", "TBD", "```markdown\n"):
            with self.subTest(bad=bad):
                self.assertFalse(module.validate(fixture() + bad, NAME)["valid"])

    def test_filename(self):
        self.assertFalse(module.validate(fixture(), "wrong.md")["valid"])

    def test_cli_success_failure_and_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / NAME
            path.write_text(fixture())
            result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout)
            path.write_text(fixture(79))
            result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            result = subprocess.run([sys.executable, str(SCRIPT), str(path.parent / "absent.md")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('"valid": false', result.stdout)


if __name__ == "__main__":
    unittest.main()
