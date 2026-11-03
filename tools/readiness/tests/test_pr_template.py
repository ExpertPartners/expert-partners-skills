"""Offline checks for the pull request template in .github/pull_request_template.md.

Nothing here touches the network. The first-line contract is checked against the real
auto-merge gate parser, so the template cannot drift from what the gate reads.

Run from the repo root: python3 -m unittest discover -s tools/readiness/tests -v
"""

import importlib.util
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TEMPLATE_PATH = os.path.join(ROOT, ".github", "pull_request_template.md")
GATE_PATH = os.path.join(ROOT, "tools", "auto-merge-gate", "gate.py")

spec = importlib.util.spec_from_file_location("gate", GATE_PATH)
gate = importlib.util.module_from_spec(spec)
# dataclasses resolves annotations through sys.modules, so register before executing.
sys.modules["gate"] = gate
spec.loader.exec_module(gate)

PLACEHOLDER_FIRST_LINE = "Closes #N"

REQUIRED_SECTIONS = {
    "description": "Description",
    "linked job and context": "Linked job and context",
    "scope": "Files and scope",
    "testing": "Testing done",
    "dependencies and overlap": "Dependencies and overlap",
    "risks and rollback": "Risks and rollback",
}

# Numeric caps on open pull requests or review rounds were removed (Decision Log
# 2026-11-02, No caps stop work). A template that brings one back would tell builders
# to stop work that should continue.
STALE_CAP_PATTERNS = [
    re.compile(r"\b(?:five|5)\s+(?:open\s+)?(?:pull\s+requests?|PRs?)\b", re.IGNORECASE),
    re.compile(r"\b(?:three|3)\s+(?:review\s+)?rounds?\b", re.IGNORECASE),
    re.compile(
        r"\b(?:max(?:imum)?|at\s+most|no\s+more\s+than|limit\s+of|cap\s+of|up\s+to)\s+\w+\s+"
        r"(?:open\s+)?(?:pull\s+requests?|PRs?|review\s+rounds?|rounds?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bstop\s+after\s+\w+\s+(?:review\s+)?rounds?\b", re.IGNORECASE),
    re.compile(r"\bround\s+(?:3|three)\s+of\s+(?:3|three)\b", re.IGNORECASE),
]

# A template must never arrive with success already claimed. Results come only from
# pasted output.
UNVERIFIED_CLAIM_PATTERNS = [
    re.compile(r"^\s*[-*]\s*\[[xX]\]", re.MULTILINE),
    re.compile(r"\b(?:all|every)\s+(?:tests?|checks?)\s+(?:pass|passed|passing|green|succeed(?:ed)?)\b", re.IGNORECASE),
    re.compile(r"\b(?:tests?|checks?)\s+(?:pass|passed|passing|succeeded)\b", re.IGNORECASE),
    re.compile(r"\b(?:tested|verified)\s+(?:locally|manually|and\s+working)\b", re.IGNORECASE),
    re.compile(r"\bworks\s+(?:as\s+expected|on\s+my\s+machine)\b", re.IGNORECASE),
    re.compile(r"validate-job:\s*PASS", re.IGNORECASE),
    re.compile(r"\bResult:\s*PASS\s*$", re.IGNORECASE | re.MULTILINE),
]

# The repository is public: the template may never ask for a secret value or a private
# Brain link, and may never carry one.
SECRET_REQUEST_PATTERNS = [
    re.compile(
        r"\b(?:paste|enter|add|provide|include|share|attach|insert)\s+(?:the\s+|your\s+|a\s+|an\s+)?"
        r"(?:secret|token|password|api\s*key|credential|private\s+key|access\s+key)s?\b",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*[-*]?\s*(?:secret|token|password|api\s*key|credentials?|private\s+key)\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\b(?:link|url)\s+to\s+(?:the\s+)?(?:brain|google\s+(?:doc|drive))\b", re.IGNORECASE),
]
PRIVATE_LINK_PATTERNS = [
    re.compile(r"https?://(?:docs|drive)\.google\.com/\S*", re.IGNORECASE),
    re.compile(r"\b[0-9A-Za-z_-]{33,}\b"),  # Drive document and folder IDs
]


def read_template() -> str:
    with open(TEMPLATE_PATH, encoding="utf-8") as fh:
        return fh.read()


def sections(text: str) -> dict:
    """Second-level heading text to the body under it."""
    found: dict = {}
    current = None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            current = m.group(1)
            found[current] = []
        elif current is not None:
            found[current].append(line)
    return {k: "\n".join(v) for k, v in found.items()}


def render(text: str, issue: int) -> str:
    """The body a builder submits: the first-line placeholder filled with a job number."""
    first, _, rest = text.partition("\n")
    return first.replace("#N", f"#{issue}", 1) + "\n" + rest


def findings(text: str, patterns: list) -> list[str]:
    return [m.group(0) for p in patterns for m in p.finditer(text)]


class TemplateSections(unittest.TestCase):
    def setUp(self):
        self.text = read_template()
        self.sections = sections(self.text)

    def test_every_required_section_exists_with_guidance(self):
        for purpose, heading in REQUIRED_SECTIONS.items():
            with self.subTest(purpose=purpose):
                self.assertIn(heading, self.sections, f"missing the {purpose} section (## {heading})")
                self.assertTrue(self.sections[heading].strip(), f"## {heading} has no guidance under it")

    def test_linked_job_section_names_the_job_issue_and_decisions(self):
        body = self.sections["Linked job and context"]
        self.assertRegex(body, r"Job issue:\s*#N")
        self.assertIn("Decision Log", body)

    def test_scope_section_asks_for_the_exact_changed_files(self):
        body = self.sections["Files and scope"]
        self.assertIn("git diff --name-only", body)
        self.assertIn("files in scope", body)

    def test_testing_section_asks_for_real_commands_and_output(self):
        body = self.sections["Testing done"]
        self.assertIn("```", body, "testing section needs a code block for pasted output")
        self.assertRegex(body, r"(?i)\bcommand\b")
        self.assertRegex(body, r"(?i)\breal output\b")
        self.assertIn("PASS or FAIL", body)
        self.assertIn("bash tools/validate-job.sh", body)

    def test_dependencies_section_covers_dependencies_and_overlap(self):
        body = self.sections["Dependencies and overlap"]
        self.assertRegex(body, r"(?i)depends on")
        self.assertRegex(body, r"(?i)overlaps with")
        self.assertRegex(body, r"(?i)overlap check")

    def test_risks_section_covers_risks_and_rollback(self):
        body = self.sections["Risks and rollback"]
        self.assertRegex(body, r"(?i)\brisks:")
        self.assertRegex(body, r"(?i)\brollback\b")


class FirstLineContract(unittest.TestCase):
    def setUp(self):
        self.text = read_template()

    def test_template_starts_with_the_closes_placeholder(self):
        self.assertEqual(self.text.splitlines()[0], PLACEHOLDER_FIRST_LINE)

    def test_rendered_body_is_read_by_the_auto_merge_gate(self):
        self.assertEqual(gate.job_issue_number(render(self.text, 185)), 185)
        self.assertEqual(gate.job_issue_number(render(self.text, 7)), 7)

    def test_unfilled_placeholder_is_never_taken_for_a_job(self):
        self.assertIsNone(gate.job_issue_number(self.text))

    def test_anything_placed_before_the_closes_line_breaks_the_contract(self):
        broken = "<!-- note -->\n" + render(self.text, 185)
        self.assertIsNone(gate.job_issue_number(broken))


class NoSecretsOrPrivateLinks(unittest.TestCase):
    def test_template_does_not_ask_for_or_carry_secrets_or_private_links(self):
        text = read_template()
        self.assertEqual(findings(text, SECRET_REQUEST_PATTERNS), [])
        self.assertEqual(findings(text, PRIVATE_LINK_PATTERNS), [])

    def test_template_tells_authors_to_keep_private_material_out(self):
        text = read_template()
        self.assertRegex(text, r"(?i)keep secret values, tokens and credentials out")
        self.assertRegex(text, r"(?i)keep private brain links and document ids out")

    def test_checks_catch_secret_requests_and_private_links(self):
        bad = [
            "- API key:",
            "Token: ",
            "Paste your token here so the check can run.",
            "Provide the password for the bot.",
            "Add a link to the Brain doc you used.",
            "See https://docs.google.com/document/d/abc/edit",
            "Folder 1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789",
        ]
        for sample in bad:
            with self.subTest(sample=sample):
                self.assertTrue(
                    findings(sample, SECRET_REQUEST_PATTERNS + PRIVATE_LINK_PATTERNS),
                    f"not caught: {sample!r}",
                )


class NoStaleCapsOrUnverifiedClaims(unittest.TestCase):
    def test_template_has_no_numeric_pull_request_or_review_caps(self):
        self.assertEqual(findings(read_template(), STALE_CAP_PATTERNS), [])

    def test_template_has_no_success_claimed_in_advance(self):
        self.assertEqual(findings(read_template(), UNVERIFIED_CLAIM_PATTERNS), [])

    def test_checks_catch_stale_cap_instructions(self):
        bad = [
            "Stop when five open PRs are waiting.",
            "Never have more than 5 pull requests open.",
            "Stop after three review rounds and ask Allison.",
            "Review is capped at 3 rounds.",
            "At most three rounds of review.",
            "Maximum five PRs per builder.",
            "This is round 3 of 3.",
        ]
        for sample in bad:
            with self.subTest(sample=sample):
                self.assertTrue(findings(sample, STALE_CAP_PATTERNS), f"not caught: {sample!r}")

    def test_checks_catch_unverified_success_claims(self):
        bad = [
            "- [x] Tests pass",
            "* [X] validate-job ran",
            "All tests passed.",
            "Checks passing.",
            "Tested locally.",
            "Works as expected.",
            "validate-job: PASS",
            "   - Result: PASS",
        ]
        for sample in bad:
            with self.subTest(sample=sample):
                self.assertTrue(findings(sample, UNVERIFIED_CLAIM_PATTERNS), f"not caught: {sample!r}")

    def test_checks_leave_honest_placeholders_alone(self):
        fine = "- Result: PASS or FAIL\nMark PASS only when the pasted output shows it.\n- [ ] not done yet"
        self.assertEqual(findings(fine, UNVERIFIED_CLAIM_PATTERNS), [])


if __name__ == "__main__":
    unittest.main()
