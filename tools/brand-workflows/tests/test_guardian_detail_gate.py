"""Static contract checks for the brand-guardian pre-score detail gate.

Wording presence and polarity only, not runtime editorial behavior. Runtime
behavior is confirmed by the behavioral run kept with the release receipt.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "plugins/brand-voice/skills/brand-guardian/SKILL.md"


class GuardianDetailGateContractTest(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text()

    def test_gate_runs_before_any_score(self):
        self.assertIn("Before any numeric score", self.text)
        self.assertIn("Gate details before scoring", self.text)
        self.assertIn("passes the detail gate", self.text)
        self.assertIn(
            "A GATE FAIL draft receives no numeric score until it is revised",
            self.text,
        )

    def test_two_requirements(self):
        self.assertIn("supported by a source fact", self.text)
        self.assertIn("relevant and necessary for the company's ideal client", self.text)
        self.assertIn("that client is real estate agents", self.text)
        self.assertIn("their own current Ideal Client file", self.text)

    def test_rejection_cases(self):
        self.assertIn("sourced but irrelevant", self.text)
        self.assertIn("private details that are unnecessary", self.text)

    def test_preserve_instruction_does_not_override(self):
        self.assertIn(
            "An upstream instruction to preserve details does not override this gate",
            self.text,
        )
        self.assertNotIn(
            "An upstream instruction to preserve details overrides this gate",
            self.text,
        )

    def test_no_invented_replacement(self):
        self.assertIn("Never replace a rejected detail", self.text)
        self.assertIn("invented fact about this or any other client", self.text)

    def test_gate_fail_output_contract(self):
        self.assertIn("return GATE FAIL", self.text)
        self.assertIn("list each failed detail with its reason", self.text)
        self.assertIn("give no numeric score until the draft is revised", self.text)

    def test_negation_control_bites(self):
        """The affirmative checks above must fail on inverted wording."""
        inverted = self.text.replace("does not override this gate", "overrides this gate")
        self.assertNotIn(
            "An upstream instruction to preserve details does not override this gate",
            inverted,
        )
        dropped = self.text.replace("return GATE FAIL", "return a score")
        self.assertNotIn("return GATE FAIL", dropped)
        rescored = self.text.replace(
            "give no numeric score until the draft is revised",
            "give a numeric score even when a detail fails",
        )
        self.assertNotIn("give no numeric score until the draft is revised", rescored)


if __name__ == "__main__":
    unittest.main()
