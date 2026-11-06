"""New CLI sessions start in Auto without rewriting other command behavior."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "auto_model.py"
SPEC = importlib.util.spec_from_file_location("auto_model", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AutoModelTests(unittest.TestCase):
    def test_new_session_gets_auto(self):
        self.assertEqual(MODULE.auto_arguments(["exec", "prompt"]),
                         ["exec", "-m", "auto", "prompt"])

    def test_explicit_pins_and_effort_are_replaced(self):
        for flag in ("-m", "--model"):
            for model in ("gpt-6.1-sol", "claude-opus-5-5", "auto"):
                with self.subTest(flag=flag, model=model):
                    self.assertEqual(
                        MODULE.auto_arguments(["exec", flag, model, "-r", "high", "prompt"]),
                        ["exec", "-m", "auto", flag, "auto", "-r", "none", "prompt"])

    def test_equals_and_attached_flags(self):
        self.assertEqual(MODULE.auto_arguments(["exec", "--model=opus", "-mgpt", "-rhigh"]),
                         ["exec", "-m", "auto", "--model", "auto", "-m", "auto", "-r", "none"])

    def test_spec_and_mission_pins_are_replaced(self):
        for flag, value in MODULE.AUTO_OPTIONS.items():
            with self.subTest(flag=flag):
                self.assertEqual(MODULE.auto_arguments(["exec", flag, "incoming"])[-2:],
                                 [flag, value])

    def test_prompt_and_option_values_are_not_parsed_as_flags(self):
        self.assertEqual(
            MODULE.auto_arguments(["exec", "-f", "--model", "--append-system-prompt", "-s", "--", "-mgpt"]),
            ["exec", "-m", "auto", "-f", "--model", "--append-system-prompt", "-s", "--", "-mgpt"])

    def test_resumes_and_other_commands_are_unchanged(self):
        for arguments in ([], ["mcp", "list"], ["--help"], ["resume", "id"],
                          ["exec", "-s", "id", "-m", "gpt"],
                          ["exec", "--session-id=id", "prompt"],
                          ["exec", "-sid", "prompt"], ["exec", "-m"]):
            with self.subTest(arguments=arguments):
                self.assertEqual(MODULE.auto_arguments(arguments), arguments)

    def test_protocol_settings_are_not_claimed_as_cli_enforced(self):
        for arguments in (["exec", "--input-format", "stream-jsonrpc"],
                          ["exec", "--output-format=acp"]):
            self.assertEqual(MODULE.auto_arguments(arguments), arguments)

    def test_real_entry_point_preserves_stdin_and_exit_status(self):
        with tempfile.TemporaryDirectory() as directory:
            vendor = Path(directory) / ".local/bin/droid"
            vendor.parent.mkdir(parents=True)
            vendor.write_text(
                "#!" + sys.executable + "\n"
                "import json,sys\n"
                "print(json.dumps([sys.argv[1:],sys.stdin.read()]))\n"
                "sys.exit(17)\n")
            vendor.chmod(0o700)
            result = subprocess.run(
                [sys.executable, str(SOURCE), "exec", "--model=gpt-6.1-sol",
                 "--auto", "high", "--cwd", "/path with spaces"],
                input="prompt from stdin", capture_output=True, text=True,
                env=dict(os.environ, HOME=directory), check=False)
            self.assertEqual(result.returncode, 17)
            self.assertEqual(json.loads(result.stdout), [
                ["exec", "-m", "auto", "--model", "auto", "--auto", "high",
                 "--cwd", "/path with spaces"], "prompt from stdin"])


if __name__ == "__main__":
    unittest.main()
