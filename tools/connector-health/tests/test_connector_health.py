"""Offline tests for the connector health checker. No live account, network or real Codex
install is needed: end-to-end runs use tests/fake_codex.py in place of the CLI. Canary values
below are synthetic and exist only to prove they never reach the report.

Run from the repo root: python3 -m unittest discover -s tools/connector-health/tests -v

The optional RealCodexTest runs only when CONNECTOR_HEALTH_REAL_CODEX names an installed
codex executable. It registers synthetic stdio MCP servers in a throwaway CODEX_HOME.
"""

import importlib.util
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "connector_health.py")
FAKE_CODEX = os.path.join(HERE, "fake_codex.py")
FAKE_MCP = os.path.join(HERE, "fake_mcp_server.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ch = load("connector_health", TOOL)

CANARIES = (
    "canary-env-value-alpha",
    "canary-stderr-value-bravo",
    "canary-provider-content-charlie",
    "canary-rpc-message-delta",
    "canary.subject@example.com",
    "canary.expected@example.com",
    "canary-late-echo",
)
CONFIG_BYTES = (
    b'[mcp_servers.github]\ncommand = "gh-mcp"\n\n'
    b'[mcp_servers.github.env]\nTOKEN_NAME = "canary-env-value-alpha"\n'
    b'[mcp_servers.airtable]\nurl = "https://mcp.example/"\n'
    b'[mcp_servers.browser-controller]\ncommand = "synthetic-browser"\n'
    b'[mcp_servers.desktop_bridge]\nurl = "https://desktop.example/"\n'
)
REPORT_KEYS = {"report", "format", "checked_at", "duration_ms", "state", "error_code", "probes"}
PROBE_KEYS = {"probe_id", "service", "checked_at", "duration_ms", "state", "error_code"}
GMAIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"


def text_result(body, is_error=False):
    text = body if isinstance(body, str) else json.dumps(body)
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def probe(tool="get_me", arguments=None, expected=None, server="github", probe_id="p1"):
    return ch.Probe(probe_id, "svc", server, tool, arguments or {}, expected)


GOOGLE = probe("google_api", {"method": "GET", "url": GMAIL_URL, "subject": "probe@example.com"}, "probe@example.com", "google")


def manifest(probes, **extra):
    body = {"schema": 1, "probes": probes}
    body.update(extra)
    return json.dumps(body).encode()


def entry(probe_id, server, tool, arguments=None, **extra):
    item = {"id": probe_id, "service": server.lower(), "server": server, "tool": tool, "arguments": arguments or {}}
    item.update(extra)
    return item


def google_entry(**overrides):
    args = {"method": "GET", "url": GMAIL_URL, "subject": "probe@example.com"}
    args.update(overrides.pop("arguments", {}))
    item = entry("gmail-profile", "google", "google_api", args, expected_identity="probe@example.com")
    item.update(overrides)
    return item


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as fh:
            return fh.read().split(")")[-1].split()[0] != "Z"
    except OSError:
        return True


def wait_dead(pid, seconds=6.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if not alive(pid):
            return True
        time.sleep(0.05)
    return not alive(pid)


class ManifestTest(unittest.TestCase):
    def rejects(self, data, code):
        with self.assertRaises(ch.ManifestError) as ctx:
            ch.parse_manifest(data)
        self.assertEqual(ctx.exception.code, code)

    def test_valid_manifest_parses_with_defaults(self):
        m = ch.parse_manifest(manifest([entry("github-me", "github", "get_me"), google_entry()]))
        self.assertEqual([p.probe_id for p in m.probes], ["github-me", "gmail-profile"])
        self.assertEqual(m.request_timeout, ch.DEFAULT_REQUEST_TIMEOUT)
        self.assertEqual(m.overall_timeout, ch.DEFAULT_OVERALL_TIMEOUT)

    def test_malformed_manifests_are_refused(self):
        self.rejects(b"{not json", "manifest_invalid_json")
        self.rejects(b"[]", "manifest_invalid")
        self.rejects(b'{"schema": 1, "schema": 1, "probes": []}', "duplicate_key")
        self.rejects(manifest([]), "manifest_invalid")
        self.rejects(json.dumps({"schema": 2, "probes": [entry("a", "github", "get_me")]}).encode(), "manifest_invalid")
        self.rejects(json.dumps({"schema": True, "probes": [entry("a", "github", "get_me")]}).encode(), "manifest_invalid")
        self.rejects(manifest([entry("a", "github", "get_me")], extra=1), "unknown_field")
        self.rejects(manifest([entry("a", "github", "get_me", note="x")]), "unknown_field")
        self.rejects(manifest([entry("A B", "github", "get_me")]), "invalid_id")
        self.rejects(manifest([entry("a", "git hub", "get_me", service="github")]), "invalid_server")
        self.rejects(manifest([entry("a", "github", "get_me", service="Git Hub")]), "invalid_service")
        self.rejects(manifest([entry("a", "github", "get_me"), entry("a", "github", "get_me")]), "duplicate_probe_id")
        self.rejects(manifest([entry("a", "github", "get_me")], request_timeout_seconds=0), "invalid_timeout")
        self.rejects(manifest([entry("a", "github", "get_me")], overall_timeout_seconds="60"), "invalid_timeout")
        self.rejects(b" " * (ch.MAX_MANIFEST_BYTES + 1), "manifest_too_large")

    def test_unsupported_and_mutating_probes_are_refused(self):
        for tool in ("send_message", "create_issue", "post_message", "run_workflow", "get_usage", "get_balance", "generate_image", "http_request"):
            with self.subTest(tool=tool):
                self.rejects(manifest([entry("a", "github", tool)]), "unsupported_tool")
        self.rejects(manifest([entry("a", "github", "get_me", {"body": "x"})]), "invalid_arguments")
        self.rejects(manifest([entry("a", "linear", "search_projects", {"query": {"$ne": 1}})]), "invalid_arguments")
        self.rejects(manifest([entry("a", "linear", "search_projects", {"limit": 500})]), "invalid_arguments")
        self.rejects(manifest([entry("a", "linear", "search_projects", {"limit": True})]), "invalid_arguments")
        self.rejects(manifest([entry("a", "airtable", "list_bases", {"offset": "x"})]), "invalid_arguments")
        self.rejects(manifest([dict(entry("a", "github", "get_me"), arguments=[])]), "invalid_arguments")
        self.rejects(manifest([entry("a", "github", "get_me", expected_identity="probe@example.com")]), "unexpected_field")
        ok = ch.parse_manifest(manifest([entry("a", "linear", "search_projects", {"query": "health", "limit": 5})]))
        self.assertEqual(ok.probes[0].arguments, {"query": "health", "limit": 5})

    def test_google_api_only_allows_gmail_profile_get(self):
        cases = [
            ({"arguments": {"method": "POST"}}, "unsupported_method"),
            ({"arguments": {"method": "get"}}, "unsupported_method"),
            ({"arguments": {"url": "http://gmail.googleapis.com/gmail/v1/users/me/profile"}}, "untrusted_scheme"),
            ({"arguments": {"url": "https://gmail.googleapis.com.evil.example/gmail/v1/users/me/profile"}}, "untrusted_host"),
            ({"arguments": {"url": "https://www.googleapis.com/gmail/v1/users/me/profile"}}, "untrusted_host"),
            ({"arguments": {"url": "https://GMAIL.googleapis.com/gmail/v1/users/me/profile"}}, "untrusted_host"),
            ({"arguments": {"url": "https://gmail.googleapis.com:8443/gmail/v1/users/me/profile"}}, "untrusted_host"),
            ({"arguments": {"url": "https://user:pw@gmail.googleapis.com/gmail/v1/users/me/profile"}}, "credentials_in_url"),
            ({"arguments": {"url": GMAIL_URL + "?access_token=abc"}}, "credentials_in_url"),
            ({"arguments": {"url": GMAIL_URL + "?fields=emailAddress"}}, "unexpected_query"),
            ({"arguments": {"url": "https://gmail.googleapis.com/gmail/v1/users/me/messages"}}, "unsupported_path"),
            ({"arguments": {"url": "https://gmail.googleapis.com/gmail/v1/users/other/profile"}}, "unsupported_path"),
            ({"arguments": {"url": "https://gmail.googleapis.com/gmail/v1/users/me/../me/profile"}}, "unsupported_path"),
            ({"arguments": {"url": "https://gmail.googleapis.com/gmail/v1/users/%6de/profile"}}, "malformed_url"),
            ({"arguments": {"url": GMAIL_URL + "#frag"}}, "malformed_url"),
            ({"arguments": {"url": "https://gmail.googleapis.com:notaport/x"}}, "malformed_url"),
            ({"arguments": {"url": GMAIL_URL + " "}}, "malformed_url"),
            ({"arguments": {"url": 7}}, "malformed_url"),
            ({"arguments": {"subject": "not-an-email"}}, "invalid_subject"),
            ({"arguments": {"body": "x"}}, "invalid_arguments"),
            ({"expected_identity": "nobody"}, "invalid_expected_identity"),
        ]
        for overrides, code in cases:
            with self.subTest(overrides=overrides):
                self.rejects(manifest([google_entry(**overrides)]), code)
        missing = google_entry()
        del missing["arguments"]["subject"]
        self.rejects(manifest([missing]), "missing_subject")
        missing = google_entry()
        del missing["expected_identity"]
        self.rejects(manifest([missing]), "missing_expected_identity")

    def test_manifest_errors_carry_only_code_and_index(self):
        with self.assertRaises(ch.ManifestError) as ctx:
            ch.parse_manifest(manifest([entry("a", "github", "get_me"), google_entry(arguments={"url": "https://canary-host.example/x"})]))
        self.assertEqual((ctx.exception.code, ctx.exception.probe_index), ("untrusted_host", 1))
        self.assertNotIn("canary", str(ctx.exception))


class ClassifyTest(unittest.TestCase):
    def judge(self, result, p=None):
        return ch.classify_result(result, p or probe())

    def test_identity_read_passes_and_empty_object_does_not(self):
        self.assertEqual(self.judge(text_result({"id": "u1", "login": "synthetic"})), ("ok", None))
        self.assertEqual(self.judge(text_result({"viewer": {"id": "u1"}}), probe("get_current_user")), ("ok", None))
        self.assertEqual(self.judge(text_result({})), ("malformed_result", "contract_mismatch"))

    def test_valid_empty_results_pass(self):
        self.assertEqual(self.judge(text_result({"bases": []}), probe("list_bases")), ("ok", None))
        self.assertEqual(self.judge(text_result([]), probe("search_projects")), ("ok", None))
        self.assertEqual(self.judge(text_result({"data": {"projects": []}}), probe("agentopus_list_projects")), ("ok", None))
        self.assertEqual(self.judge(text_result({}), probe("get_preferences")), ("ok", None))
        self.assertEqual(self.judge(text_result({"items": []}), probe("list_bases")), ("malformed_result", "contract_mismatch"))

    def test_structured_content_is_read(self):
        result = {"content": [], "structuredContent": {"bases": [{"id": "b1"}]}}
        self.assertEqual(self.judge(result, probe("list_bases")), ("ok", None))

    def test_mcp_is_error_with_auth_words(self):
        self.assertEqual(self.judge(text_result("Token has expired, please re-authenticate", True)), ("auth_refused", "auth_error"))
        self.assertEqual(self.judge(text_result({"error": "invalid_grant"}, True)), ("auth_refused", "auth_error"))
        self.assertEqual(self.judge(text_result("Request failed: missing required scopes", True)), ("scope_refused", "scope_error"))
        self.assertEqual(self.judge(text_result("something broke", True)), ("service_error", "mcp_is_error"))

    def test_hidden_nested_auth_errors_in_successful_envelope(self):
        nested = {"result": {"response": {"error": {"code": 401, "message": "Unauthorized"}}}}
        self.assertEqual(self.judge(text_result(nested)), ("auth_refused", "http_401"))
        graph = {"data": None, "errors": [{"message": "Authentication required", "extensions": {"code": "UNAUTHENTICATED"}}]}
        self.assertEqual(self.judge(text_result(graph)), ("auth_refused", "auth_error"))
        stringly = {"body": json.dumps({"error": {"status": "UNAUTHENTICATED"}})}
        self.assertEqual(self.judge(text_result(stringly)), ("auth_refused", "auth_error"))
        self.assertEqual(self.judge(text_result({"ok": False, "error": "token_revoked"})), ("auth_refused", "auth_error"))
        self.assertEqual(self.judge(text_result({"ok": False, "error": "rate_limited"})), ("service_error", "status_failed"))
        self.assertEqual(self.judge(text_result({"success": False})), ("service_error", "status_failed"))
        self.assertEqual(self.judge(text_result("Error: Unauthorized")), ("auth_refused", "auth_error"))

    def test_nested_mcp_errors_override_valid_identity(self):
        for wrapper in ("result", "response", "data", "body", "payload"):
            for reason, expected in (
                ("Unauthorized", ("auth_refused", "auth_error")),
                ("Forbidden", ("scope_refused", "scope_error")),
                ("provider failed", ("service_error", "mcp_is_error")),
            ):
                nested = {wrapper: {"id": "synthetic-id", **text_result(reason, True)}}
                with self.subTest(wrapper=wrapper, reason=reason):
                    self.assertEqual(self.judge(text_result(nested)), expected)

    def test_nested_content_and_structured_errors_are_inspected(self):
        nested = {"result": {"id": "synthetic-id", "content": [
            {"type": "text", "text": json.dumps({"error": {"code": 401}})},
        ]}}
        self.assertEqual(self.judge(text_result(nested)), ("auth_refused", "http_401"))
        nested = {"result": {"id": "synthetic-id", "structuredContent": {
            "response": text_result("Unauthorized", True),
        }}}
        self.assertEqual(self.judge(text_result(nested)), ("auth_refused", "auth_error"))

        nested = {"result": {"id": "synthetic-id", "isError": False,
                             "content": [{"type": "text", "text": "Unauthorized"}]}}
        self.assertEqual(self.judge(text_result(nested)), ("auth_refused", "auth_error"))

    def test_service_content_field_is_not_a_malformed_mcp_envelope(self):
        self.assertEqual(self.judge(text_result({"content": "ordinary preference"}),
                                    probe("get_preferences")), ("ok", None))

    def test_error_envelope_limits_fail_closed_before_identity(self):
        nested = text_result("Unauthorized", True)
        for _ in range(20):
            nested = {"result": nested}
        self.assertEqual(self.judge(text_result({"id": "synthetic-id", "result": nested})),
                         ("malformed_result", "envelope_limit"))
        wide = [{"result": {}} for _ in range(300)]
        self.assertEqual(self.judge(text_result({"id": "synthetic-id", "result": wide})),
                         ("malformed_result", "envelope_limit"))

    def test_scope_refusal(self):
        body = {"error": {"code": 403, "status": "PERMISSION_DENIED", "message": "Request had insufficient authentication scopes."}}
        self.assertEqual(self.judge(text_result(body)), ("scope_refused", "http_403"))
        self.assertEqual(self.judge(text_result({"errors": ["insufficient_scope"]})), ("scope_refused", "scope_error"))

    def test_status_403_wrapped_in_successful_mcp_envelope(self):
        self.assertEqual(self.judge(text_result({"status": 403, "body": {"id": "u1"}})), ("scope_refused", "http_403"))
        self.assertEqual(self.judge(text_result({"status": 403, "body": {}}), GOOGLE), ("scope_refused", "http_403"))
        self.assertEqual(self.judge(text_result({"statusCode": "403"}), GOOGLE), ("scope_refused", "http_403"))
        self.assertEqual(self.judge(text_result({"status": 500}), GOOGLE), ("service_error", "http_500"))

    def test_google_profile_identity(self):
        good = {"status": 200, "body": {"emailAddress": "Probe@Example.com", "messagesTotal": 3}}
        self.assertEqual(self.judge(text_result(good), GOOGLE), ("ok", None))
        as_string = {"status": 200, "body": json.dumps({"emailAddress": "probe@example.com"})}
        self.assertEqual(self.judge(text_result(as_string), GOOGLE), ("ok", None))
        wrong = {"status": 200, "body": {"emailAddress": "someone.else@example.com"}}
        self.assertEqual(self.judge(text_result(wrong), GOOGLE), ("identity_mismatch", "identity_mismatch"))
        self.assertEqual(self.judge(text_result({"emailAddress": "probe@example.com"}), GOOGLE), ("malformed_result", "missing_status"))
        self.assertEqual(self.judge(text_result({"status": 302, "body": {}}), GOOGLE), ("malformed_result", "unexpected_status"))
        self.assertEqual(self.judge(text_result({"status": 200, "body": {}}), GOOGLE), ("malformed_result", "missing_identity"))
        self.assertEqual(self.judge(text_result({"status": True, "body": {}}), GOOGLE), ("malformed_result", "missing_status"))

    def test_malformed_results(self):
        self.assertEqual(self.judge(None), ("malformed_result", "missing_content"))
        self.assertEqual(self.judge({"structuredContent": {}}), ("malformed_result", "missing_content"))
        self.assertEqual(self.judge({"content": [], "isError": "no"}), ("malformed_result", "missing_content"))
        self.assertEqual(self.judge({"content": ["text"]}), ("malformed_result", "missing_content"))
        self.assertEqual(self.judge({"content": [{"type": "text", "text": 5}]}), ("malformed_result", "missing_content"))
        self.assertEqual(self.judge(text_result("Here is your profile")), ("malformed_result", "not_json"))
        self.assertEqual(self.judge({"content": []}), ("malformed_result", "not_json"))
        self.assertEqual(self.judge(text_result("{truncated")), ("malformed_result", "not_json"))

    def test_rpc_errors(self):
        self.assertEqual(ch.classify_rpc_error("unknown MCP server 'x'", False), ("transport_unavailable", "server_unknown"))
        self.assertEqual(ch.classify_rpc_error("tool call failed", True), ("transport_unavailable", "server_startup_failed"))
        self.assertEqual(ch.classify_rpc_error("MCP startup failed: handshake", False), ("transport_unavailable", "server_startup_failed"))
        self.assertEqual(ch.classify_rpc_error("401 Unauthorized", False), ("auth_refused", "auth_error"))
        self.assertEqual(ch.classify_rpc_error("request timed out", False), ("timeout", "request_timeout"))
        self.assertEqual(ch.classify_rpc_error("boom", False), ("service_error", "rpc_error"))


class CliParsingTest(unittest.TestCase):
    def test_isolation_reads_only_saved_user_transport_names(self):
        with tempfile.TemporaryDirectory() as home:
            with open(os.path.join(home, "config.toml"), "w", encoding="utf-8") as fh:
                fh.write('[mcp_servers.user_stdio]\ncommand = "synthetic"\n'
                         '[mcp_servers.user_http]\nurl = "https://example.invalid/mcp"\n'
                         '[mcp_servers.partial]\nenabled = false\n')
            with patch.dict(os.environ, {"CODEX_HOME": home}):
                saved = ch.saved_transport_names()
            self.assertEqual(saved, {"user_stdio", "user_http"})
            args = ch._isolation_args({"user_stdio"}, saved, set())
            self.assertEqual(args, ["-c", "mcp_servers.user_http.enabled=false"])

    def test_mcp_list_keeps_only_names_and_enabled(self):
        raw = json.dumps([
            {"name": "github", "enabled": True, "transport": {"env": {"TOKEN_NAME": CANARIES[0]}}},
            {"name": "off", "enabled": False},
            {"name": "legacy"},
        ]).encode()
        servers = ch.parse_mcp_list(raw)
        self.assertEqual(servers, {"github": True, "off": False, "legacy": True})
        self.assertNotIn(CANARIES[0], repr(servers))
        for bad in (b"nope", b"{}", b'[{"enabled": true}]'):
            with self.assertRaises(ch.CheckError):
                ch.parse_mcp_list(bad)

    def test_features_skip_removed_names(self):
        out = b"apps  stable  true\nin_app_browser  removed  false\ncode_mode  under development  false\n"
        self.assertEqual(ch.parse_features(out), {"apps", "code_mode"})

    def test_isolation_disables_every_unselected_server_and_refuses_unsafe_names(self):
        args = ch._isolation_args({"github"}, {"github": True, "browser": True, "desk_top": False}, {"apps", "hooks"})
        self.assertEqual(args, ["--disable", "apps", "--disable", "hooks", "-c", "mcp_servers.browser.enabled=false", "-c", "mcp_servers.desk_top.enabled=false"])
        with self.assertRaises(ch.CheckError) as ctx:
            ch._isolation_args({"github"}, {"github": True, "odd.name": True}, set())
        self.assertEqual(ctx.exception.code, "unsafe_server_name")

    def test_protocol_verified_from_schema(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        fake = load("fake_codex", FAKE_CODEX)
        for mode, code in (("ok", None), ("no_tool_call", "method_missing"), ("no_ephemeral", "param_missing")):
            with self.subTest(mode=mode):
                out = os.path.join(tmp, mode)
                fake.write_schema(out, mode)
                if code is None:
                    self.assertTrue(ch.verify_protocol(out).read_only_sandbox)
                else:
                    with self.assertRaises(ch.CheckError) as ctx:
                        ch.verify_protocol(out)
                    self.assertEqual((ctx.exception.state, ctx.exception.code), ("unsupported_protocol", code))
        with self.assertRaises(ch.CheckError):
            ch.verify_protocol(os.path.join(tmp, "missing"))

    def test_report_fields_are_allowlisted_and_codes_bounded(self):
        result = ch.ProbeResult(probe(), "2026-11-04T00:00:00Z", 5, "auth_refused", "raw provider text " + CANARIES[2])
        report = ch.build_report("2026-11-04T00:00:00Z", 7, [result])
        self.assertEqual(set(report), REPORT_KEYS)
        self.assertEqual(report["probes"][0]["error_code"], "internal_error")
        self.assertNotIn(CANARIES[2], json.dumps(report))
        weird = ch.ProbeResult(probe(), "t", 1, "made_up_state", None)
        self.assertEqual(weird.record()["state"], "service_error")


class EndToEndBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ch-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.codex = os.path.join(self.tmp, "codex")
        with open(self.codex, "w", encoding="utf-8") as fh:
            fh.write(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(FAKE_CODEX)} \"$@\"\n")
        os.chmod(self.codex, 0o755)
        self.home = os.path.join(self.tmp, "home")
        os.mkdir(self.home)
        self.config = os.path.join(self.home, "config.toml")
        with open(self.config, "wb") as fh:
            fh.write(CONFIG_BYTES)
        self.path = lambda name: os.path.join(self.tmp, name)

    def scenario(self, **overrides):
        sc = {
            "argv_file": self.path("argv.jsonl"),
            "requests_file": self.path("requests.txt"),
            "replies_file": self.path("replies.jsonl"),
            "record_thread_params": self.path("thread-params.json"),
            "stderr": "panic with " + CANARIES[1],
            "mcp_list": [
                {"name": "github", "enabled": True, "transport": {"type": "stdio", "command": "gh-mcp", "env": {"TOKEN_NAME": CANARIES[0]}}},
                {"name": "airtable", "enabled": True, "transport": {"type": "streamable_http", "url": "https://mcp.example/" + CANARIES[0]}},
                {"name": "browser-controller", "enabled": True},
                {"name": "desktop_bridge", "enabled": True},
            ],
            "calls": {
                "github/get_me": {"result": text_result({"id": "synthetic", "bio": CANARIES[2]})},
                "airtable/list_bases": {"result": text_result({"bases": []})},
            },
        }
        sc.update(overrides)
        return sc

    def default_probes(self):
        return [entry("github-me", "github", "get_me"), entry("airtable-bases", "airtable", "list_bases")]

    def start(self, sc, probes, **manifest_extra):
        manifest_extra.setdefault("request_timeout_seconds", 5)
        manifest_extra.setdefault("overall_timeout_seconds", 30)
        with open(self.path("scenario.json"), "w", encoding="utf-8") as fh:
            json.dump(sc, fh)
        with open(self.path("manifest.json"), "wb") as fh:
            fh.write(manifest(probes, **manifest_extra))
        env = dict(os.environ, CODEX_HOME=self.home, FAKE_CODEX_SCENARIO=self.path("scenario.json"))
        return subprocess.Popen(
            [sys.executable, TOOL, "--manifest", self.path("manifest.json"), "--codex", self.codex],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
        )

    def check(self, sc, probes, timeout=60, **manifest_extra):
        proc = self.start(sc, probes, **manifest_extra)
        out, err = proc.communicate(timeout=timeout)
        self.assertEqual(err, "", "the checker must not write to stderr")
        report = json.loads(out)
        self.assert_safe(report, out)
        return proc.returncode, report

    def assert_safe(self, report, raw):
        self.assertTrue(set(report) <= REPORT_KEYS | {"probe_index"})
        self.assertIn(report["state"], ch.RUN_STATES)
        for item in report["probes"]:
            self.assertEqual(set(item), PROBE_KEYS)
            self.assertIn(item["state"], ch.PROBE_STATES)
            code = item["error_code"]
            self.assertTrue(code is None or code in ch.ERROR_CODES or re.fullmatch(r"http_[1-5][0-9]{2}", code))
        for canary in CANARIES:
            self.assertNotIn(canary, raw)

    def states(self, report):
        return {p["probe_id"]: (p["state"], p["error_code"]) for p in report["probes"]}

    def invocations(self):
        try:
            with open(self.path("argv.jsonl"), encoding="utf-8") as fh:
                return [json.loads(line) for line in fh]
        except FileNotFoundError:
            return []

    def launches(self):
        return [argv for argv in self.invocations() if argv[:1] == ["app-server"] and argv[-2:] == ["--listen", "stdio://"]]

    def requests(self):
        try:
            with open(self.path("requests.txt"), encoding="utf-8") as fh:
                return fh.read().split()
        except FileNotFoundError:
            return []

    def read_pid(self, name):
        with open(self.path(name), encoding="utf-8") as fh:
            return int(fh.read())


class EndToEndTest(EndToEndBase):
    def test_healthy_run_isolates_unselected_servers_and_preserves_config(self):
        rc, report = self.check(self.scenario(), self.default_probes())
        self.assertEqual(rc, 0)
        self.assertEqual(report["state"], "ok")
        self.assertEqual(self.states(report), {"github-me": ("ok", None), "airtable-bases": ("ok", None)})
        [launch] = self.launches()
        self.assertIn("mcp_servers.browser-controller.enabled=false", launch)
        self.assertIn("mcp_servers.desktop_bridge.enabled=false", launch)
        self.assertFalse(any("github" in a or "airtable" in a for a in launch))
        disabled = [launch[i + 1] for i, a in enumerate(launch) if a == "--disable"]
        self.assertEqual(sorted(disabled), ["apps", "browser_use", "computer_use", "hooks", "memories", "plugins"])
        self.assertEqual(self.requests(), ["initialize", "initialized", "thread/start", "mcpServer/tool/call", "mcpServer/tool/call"])
        with open(self.path("thread-params.json"), encoding="utf-8") as fh:
            params = json.load(fh)
        self.assertIs(params["ephemeral"], True)
        self.assertEqual(params["sandbox"], "read-only")
        with open(self.config, "rb") as fh:
            self.assertEqual(fh.read(), CONFIG_BYTES)
        with open(self.path("server-pid"), encoding="utf-8") as fh:
            self.assertTrue(wait_dead(int(fh.read())))

    def test_redaction_across_every_failure_path(self):
        sc = self.scenario(calls={
            "github/get_me": {"result": text_result({"error": {"code": 401, "message": CANARIES[2]}})},
            "airtable/list_bases": {"error": {"code": -32603, "message": "upstream said " + CANARIES[3]}},
            "google/google_api": {"result": text_result({"status": 200, "body": {"emailAddress": "other." + CANARIES[5]}})},
        })
        sc["mcp_list"].append({"name": "google", "enabled": True})
        google = google_entry(arguments={"subject": CANARIES[4]}, expected_identity=CANARIES[5])
        rc, report = self.check(sc, self.default_probes() + [google])
        self.assertEqual(rc, 1)
        self.assertEqual(report["state"], "degraded")
        self.assertEqual(self.states(report), {
            "github-me": ("auth_refused", "http_401"),
            "airtable-bases": ("service_error", "rpc_error"),
            "gmail-profile": ("identity_mismatch", "identity_mismatch"),
        })

    def test_request_timeout_then_stale_reply_is_ignored(self):
        sc = self.scenario(late_text=CANARIES[6])
        sc["calls"]["github/get_me"] = {"hang": True, "late": True}
        started = time.monotonic()
        rc, report = self.check(sc, self.default_probes(), request_timeout_seconds=1)
        self.assertLess(time.monotonic() - started, 15)
        self.assertEqual(rc, 1)
        self.assertEqual(self.states(report), {"github-me": ("timeout", "request_timeout"), "airtable-bases": ("ok", None)})

    def test_overall_timeout_bounds_the_run(self):
        sc = self.scenario()
        sc["calls"]["github/get_me"] = {"hang": True}
        sc["calls"]["airtable/list_bases"] = {"hang": True}
        probes = self.default_probes() + [entry("github-again", "github", "get_me")]
        started = time.monotonic()
        rc, report = self.check(sc, probes, request_timeout_seconds=1.5, overall_timeout_seconds=2)
        self.assertLess(time.monotonic() - started, 2 + 3 * ch.CLEANUP_GRACE + 3)
        self.assertEqual(rc, 1)
        states = self.states(report)
        self.assertEqual(states["github-me"], ("timeout", "request_timeout"))
        self.assertEqual(states["airtable-bases"], ("timeout", "overall_timeout"))
        self.assertEqual(states["github-again"], ("timeout", "overall_timeout"))

    def test_cli_step_timeout_is_bounded(self):
        sc = self.scenario(hang_cli="features")
        started = time.monotonic()
        rc, report = self.check(sc, self.default_probes(), request_timeout_seconds=1)
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(rc, 3)
        self.assertEqual(report["state"], "timeout")
        self.assertEqual(self.launches(), [])

    def test_stubborn_owned_process_and_children_are_stopped_but_shared_server_is_not(self):
        shared = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], start_new_session=True)
        self.addCleanup(shared.wait)
        self.addCleanup(shared.kill)
        sc = self.scenario(stubborn=True, spawn_child_pidfile=self.path("child-pid"))
        rc, report = self.check(sc, self.default_probes())
        self.assertEqual(rc, 0)
        self.assertTrue(wait_dead(self.read_pid("server-pid")), "owned app-server survived")
        self.assertTrue(wait_dead(self.read_pid("child-pid")), "owned child survived")
        self.assertIsNone(shared.poll(), "a process the checker does not own was stopped")

    def test_process_exit_mid_run_is_transport_failure(self):
        sc = self.scenario()
        sc["calls"]["github/get_me"] = {"exit": True}
        rc, report = self.check(sc, self.default_probes())
        self.assertEqual(rc, 3)
        self.assertEqual(report["state"], "transport_unavailable")
        self.assertEqual(self.states(report)["github-me"], ("transport_unavailable", "process_exited"))

    def test_unsupported_protocol_never_launches_app_server(self):
        for mode in ("no_tool_call", "no_ephemeral", "fail"):
            with self.subTest(mode=mode):
                if os.path.exists(self.path("argv.jsonl")):
                    os.remove(self.path("argv.jsonl"))
                rc, report = self.check(self.scenario(schema=mode), self.default_probes())
                self.assertEqual(rc, 3)
                self.assertEqual(report["state"], "unsupported_protocol")
                self.assertTrue(all(s == "unsupported_protocol" for s, _ in self.states(report).values()))
                self.assertEqual(self.launches(), [])

    def test_invalid_initialize_and_non_ephemeral_thread(self):
        rc, report = self.check(self.scenario(initialize="bad"), self.default_probes())
        self.assertEqual((rc, report["error_code"]), (3, "initialize_invalid"))
        rc, report = self.check(self.scenario(thread_ephemeral=False), self.default_probes())
        self.assertEqual((rc, report["error_code"]), (3, "ephemeral_not_honored"))
        self.assertNotIn("mcpServer/tool/call", self.requests())

    def test_missing_or_disabled_servers(self):
        sc = self.scenario()
        sc["mcp_list"][1]["enabled"] = False
        probes = self.default_probes() + [entry("linear-projects", "linear", "search_projects")]
        rc, report = self.check(sc, probes)
        self.assertEqual(rc, 1)
        self.assertEqual(self.states(report), {
            "github-me": ("ok", None),
            "airtable-bases": ("transport_unavailable", "server_disabled"),
            "linear-projects": ("transport_unavailable", "server_not_configured"),
        })
        rc, report = self.check(self.scenario(), [entry("linear-projects", "linear", "search_projects")])
        self.assertEqual(rc, 1)
        self.assertEqual(len(self.launches()), 1, "no app-server starts when nothing can run")

    def test_startup_failure_notice_is_transport(self):
        sc = self.scenario(startup={"github": "failed"})
        sc["calls"]["github/get_me"] = {"error": {"code": -32603, "message": "tool call failed"}}
        rc, report = self.check(sc, self.default_probes())
        self.assertEqual(self.states(report)["github-me"], ("transport_unavailable", "server_startup_failed"))

    def test_unsafe_unselected_name_fails_closed(self):
        sc = self.scenario()
        sc["mcp_list"].append({"name": "odd.name", "enabled": True})
        with open(self.config, "a", encoding="utf-8") as fh:
            fh.write('\n[mcp_servers."odd.name"]\ncommand = "synthetic"\n')
        rc, report = self.check(sc, self.default_probes())
        self.assertEqual((rc, report["state"], report["error_code"]), (3, "unsupported_protocol", "unsafe_server_name"))
        self.assertEqual(self.launches(), [])

    def test_managed_list_names_never_become_partial_user_registrations(self):
        sc = self.scenario()
        sc["mcp_list"].extend([
            {"name": "managed_app", "enabled": True, "transport": {"type": "managed"}},
            {"name": "plugin.injected", "enabled": True},
        ])
        rc, report = self.check(sc, self.default_probes())
        self.assertEqual((rc, report["state"]), (0, "ok"))
        [launch] = self.launches()
        self.assertFalse(any("managed_app" in arg or "plugin.injected" in arg for arg in launch))
        self.assertIn("mcp_servers.browser-controller.enabled=false", launch)

    def test_server_requests_and_notices_do_not_deadlock(self):
        rc, report = self.check(self.scenario(pre_messages=True), self.default_probes())
        self.assertEqual(rc, 0)
        with open(self.path("replies.jsonl"), encoding="utf-8") as fh:
            replies = {r["id"]: r for r in map(json.loads, fh)}
        self.assertEqual(replies["srv-1"]["result"], {"action": "decline"})
        self.assertEqual(replies["srv-2"]["error"]["code"], -32601)

    def test_saved_config_change_is_reported(self):
        rc, report = self.check(self.scenario(touch_config=True), self.default_probes())
        self.assertEqual((rc, report["error_code"]), (3, "saved_config_changed"))

    def test_invalid_manifest_never_runs_codex(self):
        rc, report = self.check(self.scenario(), [entry("a", "github", "delete_repository")])
        self.assertEqual((rc, report["state"], report["error_code"], report["probe_index"]), (2, "manifest_invalid", "unsupported_tool", 0))
        self.assertEqual(self.invocations(), [])

    def test_codex_must_be_an_absolute_executable(self):
        with open(self.path("manifest.json"), "wb") as fh:
            fh.write(manifest(self.default_probes()))
        out = subprocess.run([sys.executable, TOOL, "--manifest", self.path("manifest.json"), "--codex", "codex"], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 2)
        self.assertEqual(json.loads(out.stdout)["error_code"], "codex_not_executable")

    def test_interrupt_stops_owned_processes(self):
        sc = self.scenario(spawn_child_pidfile=self.path("child-pid"))
        sc["calls"]["github/get_me"] = {"hang": True}
        proc = self.start(sc, self.default_probes())
        end = time.monotonic() + 20
        while "mcpServer/tool/call" not in self.requests() and time.monotonic() < end:
            time.sleep(0.05)
        proc.send_signal(signal.SIGTERM)
        out, err = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 130)
        self.assertEqual(err, "")
        report = json.loads(out)
        self.assert_safe(report, out)
        self.assertEqual(report["state"], "interrupted")
        self.assertTrue(wait_dead(self.read_pid("server-pid")))
        self.assertTrue(wait_dead(self.read_pid("child-pid")))


@unittest.skipUnless(os.environ.get("CONNECTOR_HEALTH_REAL_CODEX"), "set CONNECTOR_HEALTH_REAL_CODEX to an installed codex")
class RealCodexTest(EndToEndBase):
    def test_against_installed_cli_with_synthetic_servers(self):
        codex = os.environ["CONNECTOR_HEALTH_REAL_CODEX"]
        env = dict(os.environ, CODEX_HOME=self.home)
        os.remove(self.config)
        marker = self.path("bystander-started")
        for name, mode in (("probe", "ok"), ("walled", "forbidden"), ("bystander", "marker:" + marker)):
            subprocess.run([codex, "mcp", "add", name, "--", sys.executable, FAKE_MCP, mode], env=env, check=True, capture_output=True, timeout=60)
        # Only the list is augmented. Initialization and tool calls still run through
        # the installed official app-server, with synthetic saved transports only.
        with open(self.codex, "w", encoding="utf-8") as fh:
            fh.write(f"#!{sys.executable}\nimport json, os, subprocess, sys\n"
                     f"real = {codex!r}\n"
                     "if sys.argv[1:] == ['mcp', 'list', '--json']:\n"
                     "    out = subprocess.check_output([real, *sys.argv[1:]])\n"
                     "    entries = json.loads(out)\n"
                     "    entries.append({'name': 'managed.injected', 'enabled': True})\n"
                     "    print(json.dumps(entries))\n"
                     "else:\n"
                     "    os.execv(real, [real, *sys.argv[1:]])\n")
        with open(self.config, "rb") as fh:
            saved = fh.read()
        with open(self.path("manifest.json"), "wb") as fh:
            fh.write(manifest([
                entry("probe-me", "probe", "get_me"),
                entry("probe-bases", "probe", "list_bases"),
                entry("walled-me", "walled", "get_me"),
            ], request_timeout_seconds=30, overall_timeout_seconds=120))
        out = subprocess.run([sys.executable, TOOL, "--manifest", self.path("manifest.json"), "--codex", self.codex], capture_output=True, text=True, env=env, timeout=180)
        report = json.loads(out.stdout)
        self.assert_safe(report, out.stdout + out.stderr)
        self.assertEqual(out.stderr, "")
        self.assertEqual(self.states(report), {
            "probe-me": ("ok", None),
            "probe-bases": ("ok", None),
            "walled-me": ("scope_refused", "http_403"),
        })
        self.assertEqual(out.returncode, 1)
        self.assertFalse(os.path.exists(marker), "an unselected MCP server was started")
        with open(self.config, "rb") as fh:
            self.assertEqual(fh.read(), saved)


if __name__ == "__main__":
    unittest.main()
