"""Threshold fixtures are not evidence of editorial or brand quality."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "plugins/brand-voice/skills/brand-guardian"
SCRIPT = SKILL / "scripts/check_score.py"
spec = importlib.util.spec_from_file_location("guardian_score", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GuardianScoreTest(unittest.TestCase):
    def test_threshold(self):
        for score, expected in (
            (0, "FAIL"),
            (89, "FAIL"),
            (89.9, "FAIL"),
            (90, "PASS"),
            (100, "PASS"),
        ):
            with self.subTest(score=score):
                self.assertEqual(
                    module.check_score({"score": score, "problems": []})["result"],
                    expected,
                )

    def test_invalid_scores(self):
        for score in (
            -1,
            101,
            float("nan"),
            float("inf"),
            float("-inf"),
            "90",
            True,
            False,
            None,
            [],
            {},
        ):
            with self.subTest(score=score):
                with self.assertRaises(ValueError):
                    module.check_score({"score": score, "problems": []})

    def test_problems_and_brand_findings_survive_pass(self):
        for score in (90, 100):
            record = {
                "score": score,
                "problems": ["Repetitive opening"],
                "brand_findings": ["Unsupported claim"],
                "brand_verdict": "unresolved",
                "result": "FAIL",
            }
            result = module.check_score(record)
            self.assertEqual(result["result"], "PASS")
            self.assertEqual(result["problems"], record["problems"])
            self.assertEqual(result["brand_findings"], record["brand_findings"])
            self.assertEqual(result["brand_verdict"], "unresolved")
            self.assertEqual(record["result"], "FAIL")

    def test_missing_or_invalid_problems(self):
        for problems in (None, "none", [""], [" "], [1], [{}]):
            with self.subTest(problems=problems):
                with self.assertRaises(ValueError):
                    module.check_score({"score": 90, "problems": problems})
        with self.assertRaises(ValueError):
            module.check_score({"score": 90})
        with self.assertRaises(ValueError):
            module.check_score([])

    def test_cli_valid_fail_invalid_and_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "score.json"
            for score in (89, 90, 100, "90"):
                path.write_text(json.dumps({"score": score, "problems": ["Keep finding"]}))
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True
                )
                self.assertEqual(result.returncode, 1 if score == "90" else 0)
                data = json.loads(result.stdout)
                if data["valid"]:
                    self.assertEqual(data["record"]["problems"], ["Keep finding"])
            path.write_text("{not JSON")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 1)
            path.unlink()
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 1)

    def test_skill_wiring_and_canon_precedence(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertIn("Always read [Anti AI Writing Guide]", text)
        self.assertIn("Use `brand-voice` to read current HQ authority", text)
        self.assertIn("Report `Anti AI score`, `Anti AI result` and `Problems` together", text)
        self.assertIn("Keep every identified problem alongside the score", text)
        self.assertIn("An Anti AI PASS does not clear those findings", text)
        self.assertIn("Current company canon and accepted calibration", text)
        self.assertIn("leave the score and editorial result unassessed", text)
        self.assertIn("An audit-only request", text)


if __name__ == "__main__":
    unittest.main()
