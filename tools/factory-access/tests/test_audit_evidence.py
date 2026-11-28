"""Wrong-result regressions observed in the real EP proof audit."""

import importlib.util
from pathlib import Path
import unittest

SOURCE = (
    Path(__file__).resolve().parents[3]
    / "plugins/operating-doctrine/skills/business-brain-foundations/references/validate-audit-evidence.py"
)
SPEC = importlib.util.spec_from_file_location("audit_evidence", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AuditEvidenceTests(unittest.TestCase):
    def test_report_must_not_drop_a_thin_pieces_declared_gaps(self):
        evidence = {
            "pieces": [{"contentStatus": "thin", "gaps": ["Missing dated outcome evidence."]}],
            "renderedReportText": "Open field questions\nNone in checked fields.",
        }
        self.assertTrue(MODULE.validate(evidence))
        evidence["renderedReportText"] = "Open field questions\nMissing dated outcome evidence."
        self.assertFalse(MODULE.validate(evidence))

    def test_commenter_is_not_an_editor_finding(self):
        finding = {
            "status": "editor finding",
            "permissions": [{"type": "anyone", "role": "commenter"}],
        }
        self.assertTrue(MODULE.validate({"sharingFindings": [finding]}))
        finding["permissions"][0]["role"] = "writer"
        self.assertFalse(MODULE.validate({"sharingFindings": [finding]}))

    def claim(self):
        return {
            "status": "confirmed",
            "basis": "body comparison",
            "a": {
                "id": "one",
                "version": "2",
                "excerpt": "same paragraph",
                "role": "approved policy",
                "scope": "operations",
            },
            "b": {
                "id": "two",
                "version": "3",
                "excerpt": "same paragraph",
                "role": "approved policy",
                "scope": "operations",
            },
            "sameRoleReason": "Both govern the same operating decision for the same audience.",
        }

    def test_same_file_in_overlapping_scopes_is_not_a_duplicate(self):
        claim = self.claim()
        claim["b"]["id"] = "one"
        self.assertTrue(MODULE.validate({"duplicateClaims": [claim]}))

    def test_paired_bodies_and_role_reasoning_are_required(self):
        claim = self.claim()
        self.assertFalse(MODULE.validate({"duplicateClaims": [claim]}))
        del claim["b"]["excerpt"]
        self.assertTrue(MODULE.validate({"duplicateClaims": [claim]}))

    def test_long_text_does_not_prove_filled_fields(self):
        piece = {
            "contentStatus": "filled",
            "sourceId": "one",
            "masterId": "master",
            "basis": "length",
        }
        self.assertTrue(MODULE.validate({"pieces": [piece]}))

    def test_unverified_candidates_do_not_become_confirmed_findings(self):
        self.assertFalse(MODULE.validate({"duplicateClaims": [{"status": "unverified"}]}))

    def test_supported_field_judgment_is_eligible_for_independent_review(self):
        piece = {
            "contentStatus": "healthy",
            "sourceId": "one",
            "masterId": "master",
            "basis": "field review",
            "fieldChecks": [
                {
                    "field": "mission",
                    "evidence": "Source section Mission",
                    "assessment": "Required mission is present; authority remains draft.",
                }
            ],
        }
        self.assertFalse(MODULE.validate({"pieces": [piece]}))


if __name__ == "__main__":
    unittest.main()
