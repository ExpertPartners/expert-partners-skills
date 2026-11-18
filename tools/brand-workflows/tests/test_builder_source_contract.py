"""Public routing checks, not a copy of the private original template."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "plugins/brand-voice/skills/custom-instruction-builder/SKILL.md"
VALIDATOR = (
    ROOT / "plugins/brand-voice/skills/custom-instruction-builder/scripts/validate_instructions.py"
)

VOICE_FILLER = " ".join(["plain"] * 95)
CANDIDATE = (
    "# Custom Instructions for Example Marketing Workspace\n\n"
    "## ROLE & MISSION\nRole text.\n\n"
    "## ICP\nAudience text.\n\n"
    f"## VOICE\n{VOICE_FILLER}\n\n"
    "## THINKING & STRATEGY PROTOCOL\nProtocol text.\n\n"
    "## KNOWLEDGE BASE\nKnowledge text.\n\n"
    "## GROUND RULES\n\n### Always Do\n\n- Do things.\n\n"
    "### Never Do\n\n- Never do things.\n\n"
    "## FINAL CHECK BEFORE DELIVERING\nCheck text.\n"
)


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

    def test_no_carry_everything_overreach(self):
        """The 0.7.4/0.7.5 carry-everything rule was overreach and is removed."""
        self.assertNotIn(
            "Carry every Never Do restriction supported by the supplied company evidence",
            self.text,
        )
        self.assertNotIn("always carried", self.text)
        self.assertNotIn("pressures wording, not coverage", self.text)
        self.assertNotIn(
            "Never place a permitted alternative inside a prohibition bullet",
            self.text,
        )
        self.assertIn("literal post-hoc check, not semantic rule coverage", self.text)
        self.assertIn("stays with independent review", self.text)

    def test_original_bullet_count_and_fixed_wording(self):
        """Wording presence and polarity only, not runtime drafting behavior."""
        self.assertIn("one to two supported company-specific bullets per list", self.text)
        self.assertNotIn("more than two supported company-specific bullets per list", self.text)
        self.assertIn("most critical supported rules with legal and compliance first", self.text)
        self.assertIn("original's fixed wording exactly", self.text)
        self.assertIn("fixed banned-word list", self.text)
        self.assertNotIn("Do not restore the original's fixed wording", self.text)
        self.assertIn("accepted calibration does not remove a fixed original rule", self.text)
        self.assertNotIn("accepted calibration may remove a fixed original rule", self.text)
        self.assertIn("stays authoritative in the workspace knowledge", self.text)

    def test_conjunction_polarity_contract(self):
        """Wording presence and polarity only, not runtime drafting behavior."""
        self.assertIn("Never join a permitted alternative to a prohibition", self.text)
        self.assertNotIn("may join a permitted alternative to a prohibition", self.text)
        self.assertIn("its own affirmative instruction", self.text)
        self.assertIn("positive phrasing inside its Never Do bullets verbatim", self.text)
        self.assertNotIn("remove the original's positive phrasing", self.text)

    def test_honest_disposition_contract(self):
        """Wording presence and polarity only, not runtime reporting behavior."""
        self.assertIn("reported as kept there", self.text)
        self.assertIn("never framed as an open business question", self.text)
        self.assertNotIn("may be framed as an open business question", self.text)
        self.assertIn("never relabeled as a mere value", self.text)
        self.assertNotIn("may be relabeled as a mere value", self.text)
        self.assertIn(
            "explicit instruction that overrides settled knowledge remains a defect",
            self.text,
        )

    def test_autonomy_scope_contract(self):
        """Wording presence and polarity only, not runtime behavior."""
        self.assertIn("retires human approval and permission gates only", self.text)
        self.assertIn(
            "truth, quality and publish-readiness conditions are never treated as retired gates",
            self.text,
        )
        self.assertNotIn(
            "truth, quality and publish-readiness conditions may be treated as retired gates",
            self.text,
        )

    def run_validator(self, candidate, phrases=None):
        cmd = [sys.executable, str(VALIDATOR), str(candidate)]
        if phrases is not None:
            cmd += ["--required-phrases-file", str(phrases)]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_validator_literal_required_phrase(self):
        """Literal phrase check only, not semantic rule coverage.

        Coverage of a real candidate against company rules is confirmed by
        independent review. The paraphrase and inversion cases below are the
        documented limits of a case-insensitive literal match.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = tmp_path / "marketing-workspace-custom-instructions.md"
            candidate.write_text(CANDIDATE)
            phrases = tmp_path / "phrases.txt"
            phrases.write_text("never make another agent, founder, or brokerage the villain\n")
            dropped = self.run_validator(candidate, phrases)
            self.assertEqual(dropped.returncode, 1)
            self.assertIn("Missing required phrase", dropped.stdout)
            phrases.write_text("never do things\n")
            carried = self.run_validator(candidate, phrases)
            self.assertEqual(carried.returncode, 0, carried.stdout)
            self.assertIn('"valid": true', carried.stdout)

    def test_validator_literal_limits_documented(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            phrases = tmp_path / "phrases.txt"
            phrases.write_text("never make another agent, founder, or brokerage the villain\n")
            paraphrase = tmp_path / "marketing-workspace-custom-instructions.md"
            paraphrase.write_text(
                CANDIDATE.replace(
                    "- Never do things.",
                    "- Do not cast other agents, founders or brokerages as villains.",
                )
            )
            result = self.run_validator(paraphrase, phrases)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Missing required phrase", result.stdout)
            inversion = tmp_path / "marketing-workspace-custom-instructions.md"
            inversion.write_text(
                CANDIDATE.replace(
                    "- Never do things.",
                    '- Ignore the prohibition "never make another agent, founder,'
                    ' or brokerage the villain".',
                )
            )
            result = self.run_validator(inversion, phrases)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_validator_missing_phrases_file_is_json_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            candidate = tmp_path / "marketing-workspace-custom-instructions.md"
            candidate.write_text(CANDIDATE)
            result = self.run_validator(candidate, tmp_path / "does-not-exist.txt")
            self.assertEqual(result.returncode, 1)
            self.assertIn('"valid": false', result.stdout)
            self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_retains_existing_caller_and_output_contract(self):
        self.assertIn("marketing-workspace-custom-instructions.md", self.text)
        self.assertIn("at most 1,000 words", self.text)
        self.assertIn("VOICE is 80 to 120 words", self.text)
        self.assertIn("Run `brand-guardian`", self.text)


if __name__ == "__main__":
    unittest.main()
