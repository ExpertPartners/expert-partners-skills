"""Public prompt-contract checks; private business cases run outside this repo."""

import unittest
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "plugins/content-engines/skills"


class ContentSourceContractTest(unittest.TestCase):
    def test_standalone_claims_cannot_be_rescued_by_labels(self):
        for name in ("hook-engine", "post-value-filter"):
            with self.subTest(name=name):
                text = (ROOT / name / "SKILL.md").read_text()
                for clause in (
                    "Standalone literal check",
                    "A suggestion label is not evidence",
                    "An external disclaimer cannot rescue an unsupported sentence",
                    "A question must not smuggle in an unsupported premise",
                    "implied causes, diagnoses, comparisons, frequency and promised outcomes",
                    "supports their exact scope",
                    "without a guaranteed result",
                    "Keep truthful specific persuasive language",
                    "Hypothetical framing permits an invented situation",
                ):
                    self.assertIn(clause, text)
        for path in (
            "hook-engine/references/architectures.md",
            "post-value-filter/references/idea-check.md",
            "post-value-filter/references/rewrite-playbook.md",
        ):
            with self.subTest(path=path):
                text = (ROOT / path).read_text()
                self.assertIn("external disclaimer", text)
                self.assertIn(
                    "line"
                    if "architectures" in path
                    else "sentence"
                    if "idea-check" in path
                    else "line itself",
                    text,
                )

    def test_reader_prose_is_neutral_except_fixed_compatibility_labels(self):
        labels = (
            "Most valuable thing she saw today",
            "She'd send it to a friend",
            "Valuable even if she never buys",
            "Her Exact Words",
            "Her moment",
            "Her bad day",
            "Her words",
            "What she wants",
        )
        for name in ("hook-engine", "post-value-filter"):
            for path in (ROOT / name).rglob("*.md"):
                with self.subTest(path=path):
                    text = path.read_text()
                    for label in labels:
                        text = re.sub(re.escape(label), "", text, flags=re.I)
                    self.assertNotRegex(text, r"(?i)\b(?:she|her|hers|herself)\b")
            text = (ROOT / name / "SKILL.md").read_text()
            for clause in ("critiques", "score explanations", "ancillary advice"):
                self.assertIn(clause, text)

    def test_her_moment_scores_recognition_not_permission(self):
        text = (ROOT / "post-value-filter/references/idea-check.md").read_text()
        for clause in (
            "Score this criterion only on whether",
            "separate from permission to publish",
            "Missing prevalence data, publication permission or profile fields",
            "can carry a whole post, does not lower this score",
        ):
            self.assertIn(clause, text)

    def test_idea_check_allows_labeled_hypothetical_mirror(self):
        text = (ROOT / "post-value-filter/references/idea-check.md").read_text()
        for clause in (
            "may be a clearly labeled hypothetical scenario",
            "must not present itself as a real customer event",
            "quote unpermitted customer language",
            "invented proof, numbers or causal rules",
        ):
            self.assertIn(clause, text)

    def test_both_entrypoints_bound_suggestions_and_gender(self):
        for name in ("hook-engine", "post-value-filter"):
            with self.subTest(name=name):
                text = (ROOT / name / "SKILL.md").read_text()
                for term in ("they/their", "approved method", "caus", "urgency"):
                    self.assertIn(term, text)
                self.assertIn("frontmatter", text)
                self.assertIn("Slash injection may omit", text)

    def test_unlock_advice_has_separate_requirements(self):
        text = (ROOT / "hook-engine/SKILL.md").read_text()
        self.assertIn("Before/After; Credential Bridge separately needs", text)
        self.assertIn("pattern's actual `Requires`", text)
        self.assertIn("Hook Doctor check", text)
        self.assertNotIn("Eight of the 12 patterns need none", text)
        architectures = (ROOT / "hook-engine/references/architectures.md").read_text()
        self.assertNotIn("Patterns 5-12 need none", architectures)
        for term in ("Wrong Answer needs", "Her Exact Words needs", "Hot Seat needs"):
            self.assertIn(term, architectures)
        self.assertIn("permitted for the intended use", architectures)

    def test_shared_setup_preserves_legacy_keys_without_gender_inference(self):
        copies = [
            (ROOT / name / "references/setup-interview.md").read_text()
            for name in ("hook-engine", "post-value-filter")
        ]
        self.assertEqual(copies[0], copies[1])
        for key in ("Her bad day:", "Her words:", "What she wants:"):
            self.assertIn(key, copies[0])
        self.assertIn("must not infer gender", copies[0])
        self.assertIn("What's their biggest frustration", copies[0])
        self.assertIn("task-only", copies[0])

    def test_idea_check_preserves_criteria_verdicts_and_three_angles(self):
        text = (ROOT / "post-value-filter/references/idea-check.md").read_text()
        for clause in (
            "Her moment (0-10)",
            "all four are 7 or higher",
            "any criterion is 5 or 6, nothing lower",
            "any criterion is 4 or below",
            "Always give three",
            "not just its score",
        ):
            self.assertIn(clause, text)

    def test_hook_doctor_keeps_existing_score_and_rewrite_contract(self):
        text = (ROOT / "hook-engine/SKILL.md").read_text()
        for clause in (
            "five tests, 1 point each",
            "three rewrites",
            "each using a different pattern",
            "which rewrite you'd test first",
            "respecting the truth check",
            "Preserve an approved original",
        ):
            self.assertIn(clause, text)


if __name__ == "__main__":
    unittest.main()
