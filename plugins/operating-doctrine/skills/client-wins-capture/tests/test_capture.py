"""Synthetic contract cases, never live client content."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).parents[1] / "scripts" / "capture.py"
SPEC = importlib.util.spec_from_file_location("capture", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "sources": [{"id": "synthetic", "status": "ok", "complete": True}],
            "destinations": [
                {
                    "company": "EP",
                    "folder": "private-test-folder",
                    "verified": True,
                    "private": True,
                    "access_preserved": True,
                }
            ],
            "records": [
                {
                    "source": "synthetic",
                    "id": "example-1",
                    "company": "EP",
                    "date": "2026-11-27",
                    "url": "https://example.invalid/win/1",
                    "person": "Synthetic participant",
                    "quote": "Synthetic contract example, not a testimonial.",
                    "kind": "client_win",
                }
            ],
            "files": [],
        }

    def run_capture(self):
        return MODULE.capture(self.data)

    def receipt(self):
        action = self.run_capture()["actions"][0]
        self.data["files"] = [
            {
                "id": "test-file",
                "folder": action["folder"],
                "key": action["key"],
                "revision": action["revision"],
                "verified": True,
            }
        ]

    def test_create_requires_real_arrival(self):
        before = self.run_capture()
        self.assertFalse(before["complete"])
        self.assertEqual(before["actions"][0]["case"]["visibility"], "internal_only")
        self.assertEqual(before["actions"][0]["case"]["quote"], self.data["records"][0]["quote"])
        self.receipt()
        after = self.run_capture()
        self.assertTrue(after["complete"])
        self.assertEqual(after["missing_arrivals"], [])
        self.assertEqual(len(after["unchanged"]), 1)

    def test_changed_quote_updates_in_place(self):
        self.receipt()
        self.data["records"][0]["quote"] += " Revised evidence."
        action = self.run_capture()["actions"][0]
        self.assertEqual(action["action"], "update")
        self.assertEqual(action["file_id"], "test-file")

    def test_consent_revoked_updates_private_case(self):
        self.data["records"][0].update(consent="granted", consent_evidence="Synthetic scope")
        self.receipt()
        self.data["records"][0]["consent"] = "revoked"
        action = self.run_capture()["actions"][0]
        self.assertEqual(action["action"], "update")
        self.assertEqual(action["case"]["visibility"], "internal_only")

    def test_public_or_unverified_destination_blocks_even_granted(self):
        self.data["records"][0].update(consent="granted", consent_evidence="Synthetic scope")
        for field in ("private", "verified", "access_preserved"):
            with self.subTest(field=field):
                self.data["destinations"][0][field] = False
                result = self.run_capture()
                self.assertEqual(result["actions"], [])
                self.assertEqual(result["blocked"][0]["reason"], "destination_unsafe")
                self.data["destinations"][0][field] = True

    def test_failed_and_paginated_incomplete_source_never_zero_success(self):
        for status, complete in (("failed", True), ("ok", False)):
            self.data["sources"][0].update(status=status, complete=complete)
            result = self.run_capture()
            self.assertFalse(result["complete"])
            self.assertEqual(result["failed_sources"], ["synthetic"])
            self.assertEqual(result["actions"], [])

    def test_missing_fields_block(self):
        original = copy.deepcopy(self.data["records"][0])
        for field in ("id", "person", "quote", "date", "url"):
            with self.subTest(field=field):
                self.data["records"][0] = copy.deepcopy(original)
                del self.data["records"][0][field]
                self.assertEqual(self.run_capture()["actions"], [])
                self.assertEqual(len(self.run_capture()["blocked"]), 1)

    def test_fixture_and_sales_are_not_testimonials(self):
        original = copy.deepcopy(self.data["records"][0])
        for updates in (
            {"fixture": True},
            {"quote": "Lorem ipsum text"},
            {"kind": "won_opportunity"},
        ):
            self.data["records"][0] = copy.deepcopy(original)
            self.data["records"][0].update(updates)
            result = self.run_capture()
            self.assertEqual(result["actions"], [])
            self.assertEqual(len(result["excluded"]), 1)

    def test_consent_needs_evidence_and_is_not_truthy(self):
        for consent in ("granted", True, "yes"):
            self.data["records"][0]["consent"] = consent
            self.assertEqual(self.run_capture()["actions"], [])

    def test_duplicate_keys_and_wrong_parent_block(self):
        self.receipt()
        self.data["files"].append(copy.deepcopy(self.data["files"][0]))
        self.assertEqual(self.run_capture()["blocked"][0]["reason"], "duplicate_destination_key")
        self.data["files"].pop()
        self.data["files"][0]["folder"] = "wrong-parent"
        self.assertEqual(self.run_capture()["blocked"][0]["reason"], "unverified_existing_file")

    def test_repeat_source_is_deduplicated_but_conflicts_fail(self):
        self.data["records"].append(copy.deepcopy(self.data["records"][0]))
        self.assertEqual(len(self.run_capture()["actions"]), 1)
        self.data["records"][1]["quote"] = "Conflicting synthetic revision"
        with self.assertRaises(ValueError):
            self.run_capture()

    def test_company_is_never_guessed(self):
        self.data["records"][0]["company"] = "AG"
        self.assertEqual(self.run_capture()["blocked"][0]["reason"], "destination_missing")

    def test_empty_source_configuration_is_not_complete(self):
        self.assertFalse(MODULE.capture({})["complete"])

    def test_zero_wins_does_not_hide_destination_gap(self):
        self.data["records"] = []
        self.data["destinations"][0]["private"] = False
        result = self.run_capture()
        self.assertFalse(result["complete"])
        self.assertEqual(result["destination_gaps"], ["EP"])
        self.data["destinations"] = []
        self.assertFalse(self.run_capture()["complete"])

    def test_real_entry_point_and_malformed_input(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(self.data),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), self.run_capture())
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], input="{", text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["complete"])


if __name__ == "__main__":
    unittest.main()
