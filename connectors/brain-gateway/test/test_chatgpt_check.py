import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


spec = importlib.util.spec_from_file_location(
    "chatgpt_check", Path(__file__).parents[1] / "scripts" / "chatgpt_check.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BrowserProtocolTests(unittest.TestCase):
    def test_initialize_discovers_the_facades_vendor_inventory(self):
        with (
            patch.object(module.subprocess, "Popen", return_value=Mock()),
            patch.object(module.threading, "Thread"),
            patch.object(module.MCP, "request", return_value={}) as request,
        ):
            module.MCP("assigned-m2-route")
        self.assertEqual([c.args[0] for c in request.call_args_list], ["initialize", "tools/list"])

    def test_start_job_keeps_the_native_name_argument(self):
        client = object.__new__(module.MCP)
        calls = []
        client.request = lambda method, params: calls.append((method, params))
        client.tool("browser_job_start", name="Daily check")
        self.assertEqual(
            calls,
            [("tools/call", {"name": "browser_job_start", "arguments": {"name": "Daily check"}})],
        )


if __name__ == "__main__":
    unittest.main()
