"""Run the manual smoke workflow's real inline Python with harmless stand-ins."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/factory-access-smoke.yml"
CANARY = "SYNTHETIC-PRIVATE-PROVIDER-CANARY-7935"
CONNECTED_ROW = "  factory-ledger  connected  user  http  11  2025-11-25"


def inline_python(step):
    section = WORKFLOW.read_text().split("      - name: " + step + "\n", 1)[1].split("\n      - name:", 1)[0]
    script = section.split("          python3 - <<'PY'\n", 1)[1].split("          PY", 1)[0]
    return "\n".join(line[10:] for line in script.splitlines())


class ManualSmokeTests(unittest.TestCase):
    def invoke(self, lines, preflight_code=0, cli_code=0, has_api_key=True, slow_cli=False,
               cli_stream="stdout", extra_error=""):
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
                "if sys.argv[1:]==['--version']:\n    print('1.2.0'); raise SystemExit(0)\n"
                "assert sys.argv[1:]==['mcp','list']\n"
                "assert os.environ['FACTORY_API_KEY']\n"
                "assert os.environ['FACTORY_LEDGER_MCP_TOKEN']\n"
                "print(" + repr(lines) + ",file=sys." + cli_stream + ")\n"
                "print(" + repr(CANARY + extra_error) + ",file=sys.stderr)\n"
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
            for line in result.stdout.splitlines():
                if line.startswith("Factory access smoke diagnostic: "):
                    data = json.loads(line.split(": ", 1)[1])
                    self.assertEqual(set(data), {"stage", "cli_exit", "version", "stdout_candidates",
                                                 "stderr_candidates", "status", "auth_state"})
                    self.assertIn(data["stage"], {"credentials", "preflight", "cli_version", "cli", "row_contract"})
                    self.assertIn(data["status"], {"unknown", "no_candidate", "ambiguous", "not_connected", "connected"})
                    self.assertIn(data["auth_state"], {"unknown", "auth_required", "no_auth_error_detected"})
                    self.assertIn(data["version"], {"unknown", "1.2.0"})
                    self.assertIsInstance(data["stdout_candidates"], int)
                    self.assertIsInstance(data["stderr_candidates"], int)
                else:
                    self.assertTrue(line.endswith((": PASS", ": FAIL")))
            return result

    def test_exact_connected_line_passes_without_provider_output(self):
        result = self.invoke(CONNECTED_ROW + "\n" + CANARY)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "Factory exact-job ledger read: PASS\nFactory native ledger MCP: PASS\n")

    def test_ansi_connected_line_passes(self):
        self.assertEqual(self.invoke("\x1b[32m" + CONNECTED_ROW + "\x1b[0m").returncode, 0)

    def test_connected_table_on_stderr_passes_without_raw_output(self):
        self.assertEqual(self.invoke(CONNECTED_ROW, cli_stream="stderr").returncode, 0)

    def test_authenticated_connected_table_passes(self):
        row = CONNECTED_ROW.replace("connected", "connected (authenticated)")
        self.assertEqual(self.invoke(row).returncode, 0)

    def test_table_failure_and_malformed_columns_fail(self):
        for row in (CONNECTED_ROW.replace("connected", "disconnected"),
                    CONNECTED_ROW.replace("connected", "connected, tools unavailable"),
                    CONNECTED_ROW.replace("11", "0", 1),
                    CONNECTED_ROW.replace("user", "unexpected-source"),
                    CONNECTED_ROW.replace("factory-ledger", "factory-ledger-extra"),
                    CONNECTED_ROW + "\n" + CONNECTED_ROW):
            with self.subTest(row=row):
                self.assertEqual(self.invoke(row).returncode, 1)

    def test_auth_error_with_connected_row_does_not_pass(self):
        result = self.invoke(CONNECTED_ROW, extra_error=" authentication required")
        self.assertEqual(result.returncode, 1)
        self.assertIn('"auth_state": "auth_required"', result.stdout)

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
        self.assertEqual(self.invoke(CONNECTED_ROW, cli_code=1).returncode, 1)

    def test_preflight_failure_is_redacted_and_never_runs_cli_proof(self):
        result = self.invoke(CONNECTED_ROW, preflight_code=1)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stdout.endswith("Factory access smoke: FAIL\n"))
        self.assertIn('"stage": "preflight"', result.stdout)

    def test_missing_factory_key_fails_closed(self):
        result = self.invoke(CONNECTED_ROW, has_api_key=False)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stdout.endswith("Factory access smoke: FAIL\n"))
        self.assertIn('"stage": "credentials"', result.stdout)

    def test_timed_out_cli_fails_without_exposing_captured_output(self):
        result = self.invoke(CONNECTED_ROW + "\n" + CANARY, slow_cli=True)
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
