"""Run the manual smoke workflow's real inline Python with harmless stand-ins."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/factory-access-smoke.yml"
CANARY = "SYNTHETIC-PRIVATE-PROVIDER-CANARY-7935"


def inline_python(step):
    section = WORKFLOW.read_text().split("      - name: " + step + "\n", 1)[1].split("\n      - name:", 1)[0]
    script = section.split("          python3 - <<'PY'\n", 1)[1].split("          PY", 1)[0]
    return "\n".join(line[10:] for line in script.splitlines())


class ManualSmokeTests(unittest.TestCase):
    def invoke(self, lines, preflight_code=0, cli_code=0, has_api_key=True, slow_cli=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = root / "tools/factory-access/preflight.py"
            helper.parent.mkdir(parents=True)
            helper.write_text(
                "import os,sys\n"
                "assert os.environ['GITHUB_REPOSITORY']=='ExpertPartners/example'\n"
                "assert os.environ['FACTORY_LEDGER_JOB_ID']=='236'\n"
                "assert os.environ['FACTORY_LEDGER_MCP_TOKEN']\n"
                "print(" + repr(CANARY) + ")\n"
                "print(" + repr(CANARY) + ",file=sys.stderr)\n"
                "raise SystemExit(" + str(preflight_code) + ")\n"
            )
            droid = root / "droid"
            droid.write_text(
                "#!" + sys.executable + "\nimport os,sys\n"
                "assert sys.argv[1:]==['mcp','list']\n"
                "assert os.environ['FACTORY_API_KEY']\n"
                "assert os.environ['FACTORY_LEDGER_MCP_TOKEN']\n"
                "print(" + repr(lines) + ")\n"
                "print(" + repr(CANARY) + ",file=sys.stderr)\n"
                + ("import time; time.sleep(10)\n" if slow_cli else "") +
                "raise SystemExit(" + str(cli_code) + ")\n"
            )
            droid.chmod(0o700)
            environment = dict(os.environ, PATH=directory + os.pathsep + os.environ.get("PATH", ""),
                               FACTORY_API_KEY=CANARY if has_api_key else "",
                               FACTORY_LEDGER_MCP_TOKEN=CANARY, FACTORY_LEDGER_JOB_ID="236",
                               GITHUB_REPOSITORY="ExpertPartners/example")
            script = inline_python("Verify exact job read and native MCP connection")
            if slow_cli:
                script = script.replace('run_captured(["droid", "mcp", "list"], 45)',
                                        'run_captured(["droid", "mcp", "list"], 0.1)')
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=root, env=environment, capture_output=True, text=True, timeout=8,
            )
            self.assertNotIn(CANARY, result.stdout + result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertTrue(all(line.endswith((": PASS", ": FAIL")) for line in result.stdout.splitlines()))
            return result

    def test_exact_connected_line_passes_without_provider_output(self):
        result = self.invoke("factory-ledger: https://example.invalid/mcp (HTTP) - Connected\n" + CANARY)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "Factory exact-job ledger read: PASS\nFactory native ledger MCP: PASS\n")

    def test_ansi_connected_line_passes(self):
        self.assertEqual(self.invoke("\x1b[32m✓ factory-ledger: Connected\x1b[0m").returncode, 0)

    def test_disconnected_or_wrong_server_never_passes(self):
        for output in ("factory-ledger: Disconnected", "factory-ledger: Not Connected", "factory-ledger: Connecting",
                       "factory-ledger-extra: Connected", "other: Connected", "factory-ledger: Failed (was connected)",
                       "factory-ledger: Connected false", "factory-ledger: connected.invalid (HTTP) - needs authentication",
                       "factory-ledger: Connected\nfactory-ledger: Disconnected"):
            with self.subTest(output=output):
                result = self.invoke(output)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn("Factory native ledger MCP: PASS", result.stdout)

    def test_failure_exit_with_connected_text_fails(self):
        self.assertEqual(self.invoke("factory-ledger: Connected", cli_code=1).returncode, 1)

    def test_preflight_failure_is_redacted_and_never_runs_cli_proof(self):
        result = self.invoke("factory-ledger: Connected", preflight_code=1)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "Factory access smoke: FAIL\n")

    def test_missing_factory_key_fails_closed(self):
        result = self.invoke("factory-ledger: Connected", has_api_key=False)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "Factory access smoke: FAIL\n")

    def test_timed_out_cli_fails_without_exposing_captured_output(self):
        result = self.invoke("factory-ledger: Connected\n" + CANARY, slow_cli=True)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Factory native ledger MCP: PASS", result.stdout)

    def test_positive_issue_validation_never_echoes_input(self):
        for value, expected in (("236", 0), ("0", 1), ("-1", 1), ("1;echo " + CANARY, 1), ("", 1)):
            result = subprocess.run([sys.executable, "-c", inline_python("Validate existing issue input")],
                                    env=dict(os.environ, FACTORY_LEDGER_JOB_ID=value), capture_output=True, text=True)
            self.assertEqual(result.returncode, expected)
            self.assertNotIn(CANARY, result.stdout + result.stderr)
            self.assertEqual(result.stderr, "")

    def test_workflow_security_contract_and_main_checkout(self):
        source = WORKFLOW.read_text()
        self.assertIn("  workflow_dispatch:\n", source)
        self.assertNotIn("pull_request", source)
        self.assertIn("    timeout-minutes: 5", source)
        self.assertIn("    if: github.ref == 'refs/heads/main'", source)
        self.assertIn("          ref: main", source)
        self.assertIn("          persist-credentials: false", source)
        self.assertIn("permissions:\n  contents: read\n", source)
        self.assertNotIn("id-token:", source)
        self.assertNotIn("droid exec", source)
        self.assertNotIn("job_claim", source)
        self.assertIn('run_captured(["droid", "mcp", "list"], 45)', source)
        self.assertIn("FACTORY_LEDGER_JOB_ID: ${{ inputs.issue }}", source)
        self.assertIn("FACTORY_LEDGER_MCP_TOKEN: ${{ secrets.FACTORY_LEDGER_MCP_TOKEN }}", source)
        self.assertIn("FACTORY_API_KEY: ${{ secrets.FACTORY_API_KEY }}", source)


if __name__ == "__main__":
    unittest.main()
