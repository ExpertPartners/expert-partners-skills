import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "chatgpt_check", Path(__file__).parents[1] / "scripts" / "chatgpt_check.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BrowserProtocolTests(unittest.TestCase):
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
