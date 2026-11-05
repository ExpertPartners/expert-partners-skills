"""Contract tests for job routing, concurrent calls and fail-closed recovery."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins/operating-doctrine/skills/browser-automation/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("owned_browser_job_source", SCRIPTS / "browser_jobs.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
StdioClient, Refusal = b.StdioClient, b.Refusal


def decode(reply):
    return json.loads(reply["content"][0]["text"])


class JobTests(unittest.TestCase):
    def route(self, root):
        route = b.Route.__new__(b.Route)
        route.root = Path(root)
        route.lock = threading.RLock()
        route.jobs = {}
        route.inventory = [{"name": "browser_navigate", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
                           {"name": "browser_install", "inputSchema": {"type": "object", "properties": {}}}]
        route.guard = SimpleNamespace(decide=lambda _: None)
        route.bootstrap = contextlib.nullcontext
        route.preflight = lambda: {"pid": 123, "started": "synthetic"}
        route.prime = lambda _: None
        route.metadata = lambda _: {"connectorId": 1, "windowId": 1, "groupId": 1, "groupTitle": "fixture"}
        return route

    def test_required_handle_and_no_shared_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            tools = route.tools()["tools"]
            self.assertNotIn("browser_install", [t["name"] for t in tools])
            navigate = next(t for t in tools if t["name"] == "browser_navigate")
            self.assertIn("job_id", navigate["inputSchema"]["required"])
            for args in ({}, {"job_id": "f" * 32}, {"job_id": "../foreign"}):
                with self.assertRaises(Refusal):
                    route.call("browser_navigate", args)

    def test_start_failure_returns_owned_handle_without_retry(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            with patch.object(route, "connect", side_effect=Refusal("fixture_failure")) as connect:
                reply = route.start("fixture")
            self.assertTrue(reply["isError"])
            row = decode(reply)
            self.assertEqual(row["status"], "failed")
            self.assertEqual(connect.call_count, 1)
            self.assertIn(row["job_id"], route.jobs)
            receipt = Path(root) / (row["job_id"] + ".json")
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("client", json.loads(receipt.read_text()))

    def test_policy_denial_never_reaches_browser(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = {"job_id": "a" * 32, "lock": threading.RLock(), "status": "ready"}
            route.jobs[job["job_id"]] = job
            route.guard = SimpleNamespace(decide=lambda payload: ("deny", "Use connected API"))
            with patch.object(route, "prime") as prime:
                reply = route.call("browser_navigate", {"job_id": job["job_id"], "url": "https://api-covered.example.test"})
            self.assertTrue(reply["isError"])
            self.assertEqual(decode(reply)["headless_route"], "Use connected API")
            prime.assert_not_called()

    def test_distinct_jobs_overlap_same_job_serializes_and_no_replay(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            windows = []
            window_lock = threading.Lock()

            def invoke(*_):
                start = time.monotonic()
                time.sleep(.08)
                with window_lock:
                    windows.append((start, time.monotonic()))
                return b.result({"worked": True})

            for handle in ("a" * 32, "b" * 32):
                route.jobs[handle] = {"job_id": handle, "label": "fixture", "client_name": "fixture", "generation": {}, "metadata": route.metadata(None), "updated": 0,
                                      "lock": threading.RLock(), "status": "ready", "client": SimpleNamespace(call=invoke)}

            def call(j):
                route.call("browser_navigate", {"job_id": j, "url": "http://127.0.0.1"})

            a, peer = route.jobs
            for handles, overlapping in (((a, peer), True), ((a, a), False)):
                windows.clear()
                threads = [threading.Thread(target=call, args=(j,)) for j in handles]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                self.assertEqual(min(x[1] for x in windows) > max(x[0] for x in windows), overlapping)
            with patch.object(route.jobs[a]["client"], "call", side_effect=Refusal("transport_closed")) as failed:
                reply = route.call("browser_navigate", {"job_id": a, "url": "http://127.0.0.1"})
            self.assertTrue(reply["isError"])
            self.assertEqual(failed.call_count, 1)
            self.assertEqual(route.jobs[a]["status"], "failed")
            self.assertEqual(route.jobs[peer]["status"], "ready")

    def test_changed_connection_is_never_adopted_or_closed(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            original = route.metadata(None)
            job = {"client": object(), "generation": route.preflight(), "metadata": original.copy()}
            for field, changed in (("windowId", 2), ("groupId", 2), ("connectorId", 2), ("groupTitle", "peer")):
                route.metadata = lambda _, field=field, changed=changed: {**original, field: changed}
                with patch.object(b, "code") as execute:
                    with self.assertRaises(Refusal):
                        route.dispose_live(job)
                execute.assert_not_called()
                self.assertEqual(job["metadata"], original)

    def test_connector_credential_redacted_recursively(self):
        url = b.EXTENSION + "?mcpRelayUrl=ws%3A%2F%2F127.0.0.1&token=SYNTHETIC_CANARY"
        actual = json.dumps(b.redact({"content": [{"text": "Welcome [link](" + url + ")"}], "nested": url}))
        self.assertNotIn("SYNTHETIC_CANARY", actual)
        self.assertNotIn("mcpRelayUrl", actual)

    def test_owned_transport_reaps_child_and_never_signals_peer(self):
        script = "import sys,json\nfor line in sys.stdin:\n q=json.loads(line); print(json.dumps({'jsonrpc':'2.0','id':q['id'],'result':{'ok':True}}),flush=True)\n"
        clients = [StdioClient([sys.executable, "-u", "-c", script], os.environ.copy(), timeout=3) for _ in range(2)]
        try:
            self.assertEqual(clients[0].call("ping"), {"ok": True})
            clients[0].close()
            self.assertTrue(clients[0].cleanup_verified)
            self.assertEqual(clients[1].call("ping"), {"ok": True})
        finally:
            for client in clients:
                client.close()


if __name__ == "__main__":
    unittest.main()
