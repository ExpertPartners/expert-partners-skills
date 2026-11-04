"""Execute the workflow's actual shell command with a harmless Droid stand-in."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/factory-builder-reusable.yml"


def step_command(name):
    step = WORKFLOW.read_text().split("      - name: " + name + "\n", 1)[1].split("\n      - name:", 1)[0]
    script = step.split("        run: |\n", 1)[1]
    lines = []
    for line in script.splitlines():
        if line and not line.startswith("          "):
            break
        lines.append(line[10:])
    return "\n".join(lines)


class WorkflowCommandTests(unittest.TestCase):
    def invoke(self, enabled):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "droid"
            executable.write_text('#!/bin/bash\nprintf "%s\\n" "$@" > "$ARGUMENT_RECEIPT"\n')
            executable.chmod(0o700)
            environment = dict(os.environ, PATH=directory + os.pathsep + os.environ["PATH"],
                               ARGUMENT_RECEIPT=str(root / "arguments"), FACTORY_MODEL="test-model",
                               FACTORY_LEDGER_ACCESS_ENABLED=enabled, RUNNER_TEMP=directory)
            subprocess.run(["bash", "-e", "-o", "pipefail", "-c", step_command("Run Factory Droid")], env=environment, check=True)
            return (root / "arguments").read_text().splitlines(), directory

    def test_disabled_caller_keeps_original_arguments_without_ledger_credentials(self):
        arguments, directory = self.invoke("false")
        self.assertEqual(arguments, ["exec", "--auto", "high", "-m", "test-model", "-f", directory + "/factory-automation-prompt.txt"])

    def test_enabled_caller_explicitly_adds_ledger_tools(self):
        arguments, directory = self.invoke("true")
        self.assertEqual(arguments, ["exec", "--auto", "high", "--add-tools", "MCP:factory-ledger", "-m", "test-model", "-f", directory + "/factory-automation-prompt.txt"])

    def test_disabled_caller_droid_environment_does_not_receive_credential(self):
        step = WORKFLOW.read_text().split("      - name: Run Factory Droid\n", 1)[1].split("\n  release:", 1)[0]
        self.assertIn("FACTORY_LEDGER_MCP_TOKEN: ${{ inputs.ledger_access_enabled && secrets.FACTORY_LEDGER_MCP_TOKEN || '' }}", step)
        self.assertNotIn("FACTORY_LEDGER_MCP_TOKEN: ${{ secrets.FACTORY_LEDGER_MCP_TOKEN }}", step)

    def test_helper_staging_leaves_caller_checkout_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            caller = root / "caller"
            temporary = root / "runner-temp"
            temporary.mkdir()
            subprocess.run(["git", "init", "-q", str(caller)], check=True)
            environment = dict(os.environ, GITHUB_WORKSPACE=str(caller), RUNNER_TEMP=str(temporary), GITHUB_ENV=str(temporary / "environment"))
            command = lambda name: subprocess.run(["bash", "-e", "-o", "pipefail", "-c", step_command(name)], cwd=caller, env=environment, check=True)
            command("Assert clean caller checkout before access setup")
            nested = caller / ".factory-access-tools"
            subprocess.run(["git", "init", "-q", str(nested)], check=True)
            helper = nested / "tools" / "factory-access" / "preflight.py"
            helper.parent.mkdir(parents=True)
            helper.write_text("# trusted helper stand-in\n")
            command("Stage canonical helper outside caller checkout")
            self.assertFalse(nested.exists())
            staged = Path((temporary / "environment").read_text().strip().split("=", 1)[1])
            self.assertTrue(staged.is_file())
            self.assertFalse(staged.is_relative_to(caller))
            self.assertEqual(subprocess.check_output(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=caller), b"")


if __name__ == "__main__":
    unittest.main()
