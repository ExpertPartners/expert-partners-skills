"""Pre-forward refusals are actionable without leaking sealed arguments."""

import json
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_browser_jobs as fixtures


class PreForwardRefusals(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.route = fixtures.JobTests().route(directory)
        self.jid = "a" * 32
        self.receipt = Path(directory) / f"{self.jid}.json"
        self.job = {
            "job_id": self.jid,
            "label": "fixture",
            "status": "ready",
            "client_name": "fixture",
            "generation": self.route.preflight(),
            "metadata": self.route.metadata(None),
            "lock": threading.RLock(),
        }
        self.route.jobs[self.jid] = self.job
        self.args = {
            "job_id": self.jid,
            "sealed": True,
            "code": "async page => 'synthetic-secret'",
        }
        self.route.sealed_call = Mock(return_value=fixtures.b.result({"sealed": "ok"}))

    def assert_refusal(self, reply, code):
        self.assertTrue(reply["isError"])
        self.assertEqual(fixtures.decode(reply)["code"], code)
        raw = self.receipt.read_text()
        record = json.loads(raw)
        self.assertNotIn("synthetic-secret", raw + str(reply))
        self.assertFalse(record["ownership_pending"])
        self.assertFalse(record["sealed"])
        self.assertEqual(record["status"], "ready")
        self.assertEqual(
            [stage for stage, _ in record["timings"][-1]["stages"]],
            ["received", f"refused:{code}"],
        )
        self.route.sealed_call.assert_not_called()

    def test_missing_inventory_records_reason_and_retry_works_after_list(self):
        self.route.inventory = None
        policy = Mock(return_value=None)
        self.route.guard.decide = policy
        reply = self.route.call("browser_run_code_unsafe", self.args)
        self.assert_refusal(reply, "tool_inventory_required")
        self.assertIn("call tools/list first", fixtures.decode(reply)["error"])
        policy.assert_not_called()

        vendor = Mock()
        vendor.call.return_value = {
            "tools": [{"name": "browser_run_code_unsafe", "inputSchema": {}}]
        }
        self.route.client = Mock(return_value=vendor)
        self.route.tools()
        vendor.call.assert_called_once_with("tools/list")
        vendor.close.assert_called_once_with()
        reply = self.route.call("browser_run_code_unsafe", self.args)
        self.assertEqual(fixtures.decode(reply), {"sealed": "ok"})
        policy.assert_called_once()
        self.route.sealed_call.assert_called_once()

    def test_unknown_name_and_policy_exception_keep_only_static_reason(self):
        reply = self.route.call("synthetic-secret", {"job_id": self.jid})
        self.assert_refusal(reply, "unknown_browser_tool")
        self.route.inventory = [{"name": "browser_run_code_unsafe"}]
        self.route.guard = SimpleNamespace(decide=Mock(side_effect=ValueError("synthetic-secret")))
        reply = self.route.call("browser_run_code_unsafe", self.args)
        self.assert_refusal(reply, "headless_policy_failed")
