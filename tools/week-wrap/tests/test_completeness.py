import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "plugins/content-engines/skills/week-wrap/scripts/check_completeness.py"
)
LINK = "https://example.com/evidence"


def check(statuses, **fields):
    return {
        "inventory_url": LINK,
        "expected": list(statuses),
        "evidence": {
            key: {"status": status, "url": LINK, **fields} for key, status in statuses.items()
        },
    }


def valid_week():
    return {
        "route": "week",
        "week": 10,
        "checks": {
            "readiness": check(
                {"HQ:first": "Covered", "EP:first": "Test", "AG:first": "Skip"},
                reason="example reason",
            ),
            "decisions": check(
                {"day-1-a": "implemented", "day-1-b": "routed"},
                receipt_url=LINK,
                owner="Fixture owner",
            ),
            "close": check(
                dict.fromkeys(
                    [
                        "engine",
                        "wheels",
                        "steering",
                        "gas",
                        "transmission",
                        "dashboard",
                        "maintenance",
                        "brain-walkthrough",
                    ],
                    "passed",
                )
            ),
            "tools": check({"doc-maker": "owned"}, owner="Fixture owner"),
            "sources": check(
                {"p1": "search", "p2": "have it", "p3": "create our own"}, reason="example reason"
            ),
            "package": check(
                dict.fromkeys(["advantage-brief", "run-of-show", "canva-chapter"], "ready")
            ),
        },
    }


class CompletenessCLI(unittest.TestCase):
    def run_gate(self, payload):
        p = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )
        return p.returncode, json.loads(p.stdout)

    def test_preflight_passes_without_existing_package(self):
        self.assertEqual(self.run_gate(valid_week()), (0, {"preflight": "passed", "gaps": []}))

    def test_every_week_criterion_blocks_missing_evidence(self):
        for section, key in [
            ("readiness", "AG:first"),
            ("decisions", "day-1-b"),
            ("close", "brain-walkthrough"),
            ("tools", "doc-maker"),
            ("sources", "p1"),
            ("package", "canva-chapter"),
        ]:
            with self.subTest(section=section):
                packet = valid_week()
                del packet["checks"][section]["evidence"][key]
                code, result = self.run_gate(packet)
                self.assertEqual(code, 1)
                self.assertEqual(
                    result["gaps"],
                    [{"check": section, "key": key, "gap": "missing evidence", "url": LINK}],
                )

    def test_cannot_hide_company_or_week_ten_close_key_by_dropping_both(self):
        data = valid_week()
        for section, key in [("readiness", "EP:first"), ("close", "dashboard")]:
            data["checks"][section]["expected"].remove(key)
            del data["checks"][section]["evidence"][key]
        code, result = self.run_gate(data)
        self.assertEqual(code, 1)
        self.assertEqual({gap["key"] for gap in result["gaps"]}, {"EP:first", "dashboard"})

    def test_dispositions_require_evidence_owner_and_reason(self):
        data = valid_week()
        for section, key, field in [
            ("readiness", "EP:first", "reason"),
            ("decisions", "day-1-a", "receipt_url"),
            ("decisions", "day-1-b", "owner"),
            ("tools", "doc-maker", "owner"),
            ("sources", "p2", "reason"),
        ]:
            data["checks"][section]["evidence"][key][field] = " "
        data["checks"]["package"]["evidence"]["canva-chapter"]["status"] = "read-only"
        code, result = self.run_gate(data)
        self.assertEqual(code, 1)
        self.assertEqual(len(result["gaps"]), 6)

    def test_attended_session_does_not_require_a_curriculum_week(self):
        data = {
            "route": "session",
            "checks": {
                "session": check({"intent": "verified", "source-review": "verified"}),
                "package": copy.deepcopy(valid_week()["checks"]["package"]),
            },
        }
        self.assertEqual(self.run_gate(data)[0], 0)
        del data["checks"]["session"]["evidence"]["intent"]
        self.assertEqual(self.run_gate(data)[0], 1)

    def test_missing_inventory_never_counts_as_empty(self):
        data = valid_week()
        data["checks"]["sources"] = check({})
        self.assertEqual(self.run_gate(data)[0], 0)
        del data["checks"]["sources"]["inventory_url"]
        self.assertEqual(self.run_gate(data)[0], 1)

    def test_week_zero_uses_its_own_close_criteria(self):
        data = valid_week()
        data["week"] = 0
        data["checks"]["close"] = check({"fixture-close": "passed"})
        self.assertEqual(self.run_gate(data)[0], 0)

    def test_malformed_inputs_fail_closed(self):
        self.assertEqual(self.run_gate(None)[0], 1)
        data = valid_week()
        data["checks"]["close"]["expected"] = [{}]
        self.assertEqual(self.run_gate(data)[0], 1)
        p = subprocess.run(
            [sys.executable, str(SCRIPT)], input="{", text=True, capture_output=True, check=False
        )
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["preflight"], "blocked")
