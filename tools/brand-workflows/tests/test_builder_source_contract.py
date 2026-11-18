"""Public routing checks, not a copy of the private original template."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "plugins/brand-voice/skills/custom-instruction-builder/SKILL.md"


class BuilderSourceContractTest(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text()

    def test_normal_invocation_requires_private_original(self):
        self.assertIn("On every normal invocation, retrieve and apply", self.text)
        self.assertIn("Cal Instruction Ledger", self.text)
        self.assertIn("GAP-108", self.text)
        self.assertIn("not an optional mode", self.text)

    def test_complete_source_not_addendum_or_snippet(self):
        self.assertIn("not a standalone complete prompt", self.text)
        self.assertIn("retrieve the remainder", self.text)
        self.assertIn("source qualification", self.text)

    def test_failed_source_does_not_fall_back(self):
        self.assertIn("name the exact failed read", self.text)
        self.assertIn("stop the source-dependent finished draft", self.text)
        self.assertIn("silently falling back", self.text)

    def test_preserves_contract_and_discloses_departures(self):
        for clause in (
            "Preserve its fixed wording and order",
            "original complex-task definition",
            "all four original questions in order",
            "original quality-threshold paragraph",
            "historical fixed question count and routine plan-approval gate",
            "Record this placement departure",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, self.text)

    def test_no_private_document_locator_or_raw_template(self):
        self.assertNotIn("docs.google.com", self.text)
        self.assertNotIn("drive.google.com", self.text)
        self.assertNotRegex(
            self.text,
            r"\b(?=[A-Za-z0-9_-]{25,}\b)(?=[A-Za-z0-9_-]*[0-9])"
            r"(?=[A-Za-z0-9_-]*[A-Z])[A-Za-z0-9_-]{25,}\b",
        )
        self.assertNotIn("# Custom Instructions for [Company Name]", self.text)

    def test_review_note_wording_contract(self):
        """Affirmative wording presence only, not delivery coverage.

        Actual delivery evidence is the observed run critique note, kept
        with the run receipt, not asserted here.
        """
        self.assertIn(
            "deliver the critique to the user as a separate note outside the copy",
            self.text,
        )
        self.assertNotIn("never deliver the critique to the user", self.text)
        self.assertNotIn("not deliver the critique to the user", self.text)
        self.assertIn("200-word threshold", self.text)
        self.assertIn("3-plus-1 critique", self.text)
        self.assertIn("not a per-company count", self.text)
        self.assertNotIn("separate internal review", self.text)

    def test_retains_existing_caller_and_output_contract(self):
        self.assertIn("marketing-workspace-custom-instructions.md", self.text)
        self.assertIn("at most 1,000 words", self.text)
        self.assertIn("VOICE is 80 to 120 words", self.text)
        self.assertIn("Run `brand-guardian`", self.text)


if __name__ == "__main__":
    unittest.main()
