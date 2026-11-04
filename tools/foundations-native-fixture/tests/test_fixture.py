"""Transport and receipt checks only. No model calls or native behavior claims."""

import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server, runner = load("fixture_server", "server.py"), load("fixture_runner", "run.py")


class Transport(unittest.TestCase):
    def test_adapter_never_teaches_or_limits_retry(self):
        # Arbitrary save requests all fail independently; the model owns policy.
        for name in (runner.FIRST, runner.FIRST, "[SYN][V1.0] Ideal Client.md"):
            self.assertTrue(server.result("save_file", {"name": name, "content": "fictional"})["isError"])

    def test_actual_stdio_results_are_logged_without_model_simulation(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                "name": "save_file", "arguments": {"name": runner.FIRST, "content": "fictional"}}},
        ]
        with tempfile.TemporaryDirectory() as folder:
            path, output = Path(folder) / "events.jsonl", io.StringIO()
            server.serve(path, io.StringIO("\n".join(map(json.dumps, messages))), output)
            replies = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual([r["id"] for r in replies], [1, 2, 3])
            self.assertTrue(replies[-1]["result"]["isError"])
            self.assertEqual(len(runner.read_jsonl(path)), 1)

    def test_fixed_transport_expectation_rejects_wrong_counts_and_next_file(self):
        def save(name=runner.FIRST, text="fictional"):
            return {"tool": "save_file", "arguments": {"name": name, "content": text},
                    "result": {"isError": True}}
        for events in ([], [save()], [save(), save(), save()], [save(), save("Ideal Client")]):
            self.assertFalse(runner.judge_storage(events)["exactly_two_same_first_file_attempts"])
        good = runner.judge_storage([save(), save()])
        self.assertTrue(good["exactly_two_same_first_file_attempts"])
        self.assertTrue(good["both_attempts_observed_as_errors"])
        self.assertTrue(good["save_content_unchanged"])
        self.assertEqual(good["other_file_tool_calls"], [])

    def test_command_uses_existing_account_marketplace_and_only_fixture_config(self):
        args = runner.command(Path("/synthetic/codex"), Path("/synthetic/work"),
                              Path("/synthetic/events"), Path("/synthetic/final"))
        self.assertIn("--ignore-user-config", args)
        self.assertIn("read-only", args)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", args)
        self.assertTrue(any('operating-doctrine@expert-partners' in item for item in args))
        self.assertTrue(any('apps._default.enabled=false' == item for item in args))
        self.assertIn('mcp_servers.foundations_fixture.default_tools_approval_mode="approve"', args)
        self.assertIn('plugins.operating-doctrine@expert-partners.enabled=true', args)
        self.assertFalse(any('CODEX_HOME=' in item for item in args))

    def test_native_rejection_is_not_confused_with_intended_storage_error(self):
        reason = "MCP tool call requires approval, but approval policy is never"
        rejected = {"type": "item.completed", "item": {"type": "mcp_tool_call",
                    "server": "foundations_fixture", "tool": "save_file",
                    "status": "failed", "error": {"message": reason}}}
        expected = {"type": "item.completed", "item": {"type": "mcp_tool_call",
                    "status": "failed", "error": None, "result": {"isError": True}}}
        failures = runner.runtime_failures([rejected, expected])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["error"]["message"], reason)


if __name__ == "__main__":
    unittest.main()
