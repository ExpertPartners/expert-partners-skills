import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

SPEC = importlib.util.spec_from_file_location("preflight", Path(__file__).parents[1] / "preflight.py")
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)
URL = "https://partnersync.app.n8n.cloud/mcp/chat-to-code-factory"
TOKEN = "test-only-credential-do-not-print"


class Response(io.BytesIO):
    def __init__(self, result=None, sequence=None, *, sse=False, headers=None):
        body = {"jsonrpc": "2.0", "id": sequence, "result": result}
        raw = json.dumps(body).encode()
        super().__init__(b"event: message\ndata: " + raw + b"\n\n" if sse else raw)
        self.headers = {"Content-Type": "text/event-stream" if sse else "application/json", **(headers or {})}


class Opener:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def responses(*, repo="ExpertPartners/example", job=42, is_error=False, paginated=False):
    result = [
        Response({"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}}, 1, headers={"Mcp-Session-Id": "test-session"}),
        Response(),
    ]
    if paginated:
        result.append(Response({"tools": [], "nextCursor": "next-page"}, 3))
    sequence = 4 if paginated else 3
    result.append(Response({"tools": [{"name": "job_status"}]}, sequence, sse=True))
    payload = [{"found": 1, "jobs": [{"job_id": job, "repo": repo}]}]
    result.append(Response({"isError": is_error, "content": [{"type": "text", "text": json.dumps(payload)}]}, sequence + 1, sse=True))
    return result


class PreflightTests(unittest.TestCase):
    def test_authenticated_read_only_protocol_and_pagination(self):
        opener = Opener(responses(paginated=True))
        preflight.prove_access(preflight.Client(URL, TOKEN, opener), 42, "ExpertPartners/example")
        bodies = [json.loads(request.data) for request in opener.requests]
        self.assertEqual([body["method"] for body in bodies], ["initialize", "notifications/initialized", "tools/list", "tools/list", "tools/call"])
        self.assertEqual(bodies[-1]["params"], {"name": "job_status", "arguments": {"job_id": 42, "mission": "", "repo": "ExpertPartners/example"}})
        self.assertEqual(opener.requests[-1].get_header("Mcp-session-id"), "test-session")
        self.assertEqual(opener.requests[-1].get_header("Authorization"), "Bearer " + TOKEN)

    def test_wrong_job_or_repository_fails(self):
        for kwargs in [{"repo": "Other/repository"}, {"job": 43}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(preflight.PreflightError):
                preflight.prove_access(preflight.Client(URL, TOKEN, Opener(responses(**kwargs))), 42, "ExpertPartners/example")

    def test_same_issue_number_in_another_repository_stays_fail_closed(self):
        repository = "ExpertPartners/target-repository"
        opener = Opener(responses(repo="ExpertPartners/other-repository", job=42))
        with self.assertRaises(preflight.PreflightError):
            preflight.prove_access(preflight.Client(URL, TOKEN, opener), 42, repository)
        call = json.loads(opener.requests[-1].data)
        self.assertEqual(call["params"]["arguments"], {"job_id": 42, "mission": "", "repo": repository})

    def test_repository_qualified_read_still_requires_exact_job(self):
        repository = "ExpertPartners/target-repository"
        opener = Opener(responses(repo=repository, job=43))
        with self.assertRaises(preflight.PreflightError):
            preflight.prove_access(preflight.Client(URL, TOKEN, opener), 42, repository)
        self.assertEqual(json.loads(opener.requests[-1].data)["params"]["arguments"]["repo"], repository)

    def test_repository_qualified_read_accepts_only_matching_result(self):
        repository = "ExpertPartners/target-repository"
        opener = Opener(responses(repo=repository, job=42))
        preflight.prove_access(preflight.Client(URL, TOKEN, opener), 42, repository)
        self.assertEqual(json.loads(opener.requests[-1].data)["params"]["arguments"]["repo"], repository)

    def test_tool_error_fails(self):
        with self.assertRaises(preflight.PreflightError):
            preflight.prove_access(preflight.Client(URL, TOKEN, Opener(responses(is_error=True))), 42, "ExpertPartners/example")

    def test_missing_tool_fails_before_tool_call(self):
        opener = Opener([Response({"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}}, 1), Response(), Response({"tools": []}, 3)])
        with self.assertRaises(preflight.PreflightError):
            preflight.prove_access(preflight.Client(URL, TOKEN, opener), 42, "ExpertPartners/example")
        self.assertEqual(len(opener.requests), 3)

    def test_http_failure_never_exposes_body_or_credential(self):
        for status in [301, 401, 403, 500]:
            error = urllib.error.HTTPError(URL, status, TOKEN, {}, io.BytesIO(TOKEN.encode()))
            with self.subTest(status=status), self.assertRaises(preflight.PreflightError) as caught:
                preflight.Client(URL, TOKEN, Opener([error])).call("initialize", {})
            self.assertNotIn(TOKEN, str(caught.exception))

    def test_redirects_cannot_forward_authorization(self):
        self.assertIsNone(preflight.NoRedirects().redirect_request(None, None, 302, "redirect", {}, "https://other.example/mcp"))

    def test_url_validation(self):
        preflight.validate_url(URL)
        for url in ["http://partnersync.app.n8n.cloud/mcp", "https://other.example/mcp", "https://partnersync.app.n8n.cloud/mcp/chat-to-code", URL + "?token=secret", "https://user@partnersync.app.n8n.cloud/mcp"]:
            with self.subTest(url=url), self.assertRaises(preflight.PreflightError):
                preflight.validate_url(url)

    def test_config_contains_env_reference_and_preserves_other_server(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mcp.json"
            existing = {"mcpServers": {"existing": {"type": "http", "url": "https://example.test/mcp"}}, "other": True}
            path.write_text(json.dumps(existing))
            preflight.provision_config(path, URL)
            saved = path.read_text()
            self.assertNotIn(TOKEN, saved)
            self.assertIn("${FACTORY_LEDGER_MCP_TOKEN}", saved)
            self.assertEqual(json.loads(saved)["mcpServers"]["existing"], existing["mcpServers"]["existing"])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            preflight.provision_config(path, URL)
            self.assertEqual(path.read_text(), saved)

    def test_conflicting_definition_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mcp.json"
            original = json.dumps({"mcpServers": {"factory-ledger": {"url": "https://other.example"}}})
            path.write_text(original)
            with self.assertRaises(preflight.PreflightError):
                preflight.provision_config(path, URL)
            self.assertEqual(path.read_text(), original)

    def test_missing_credentials_fail_without_network_or_config(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(preflight, "Client") as client:
            with self.assertRaises(preflight.PreflightError):
                preflight.main()
            client.assert_not_called()

    def test_invalid_initialize_fails_before_discovery(self):
        for result in [{}, {"protocolVersion": "2025-03-26", "capabilities": {}}, {"protocolVersion": "bad\nheader", "capabilities": {"tools": {}}}]:
            opener = Opener([Response(result, 1)])
            with self.subTest(result=result), self.assertRaises(preflight.PreflightError):
                preflight.prove_access(preflight.Client(URL, TOKEN, opener), 42, "ExpertPartners/example")
            self.assertEqual(len(opener.requests), 1)

    def test_invalid_result_shape_is_withheld(self):
        with self.assertRaises(preflight.PreflightError) as caught:
            preflight.Client(URL, TOKEN, Opener([Response(TOKEN, 1)])).call("initialize", {})
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_invalid_job_records_fail_without_printing_them(self):
        replies = responses()
        replies[-1] = Response({"structuredContent": {"jobs": TOKEN}}, 4)
        with self.assertRaises(preflight.PreflightError) as caught:
            preflight.prove_access(preflight.Client(URL, TOKEN, Opener(replies)), 42, "ExpertPartners/example")
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_deadline_fails_before_another_request(self):
        opener = Opener([])
        client = preflight.Client(URL, TOKEN, opener)
        client.deadline = 0
        with self.assertRaises(preflight.PreflightError):
            client.call("initialize", {})
        self.assertEqual(opener.requests, [])

    def test_project_and_ancestor_overrides_cannot_shadow_proved_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "parent" / "project"
            project.mkdir(parents=True)
            for folder in [root / "parent", project]:
                config = folder / ".factory" / "mcp.json"
                config.parent.mkdir()
                before = json.dumps({"mcpServers": {"factory-ledger": {"url": "https://other.example/mcp"}}})
                config.write_text(before)
                with self.subTest(folder=folder), self.assertRaises(preflight.PreflightError):
                    preflight.check_project_overrides(project, root / "user" / ".factory" / "mcp.json", URL)
                self.assertEqual(config.read_text(), before)
                config.unlink()

    def test_identical_project_definition_and_user_definition_are_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            config = project / ".factory" / "mcp.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({"mcpServers": {"factory-ledger": preflight.server_config(URL)}}))
            preflight.check_project_overrides(project, root / "user" / ".factory" / "mcp.json", URL)
            config.write_text(json.dumps({"mcpServers": {"factory-ledger": {"url": "https://old.example/mcp"}}}))
            preflight.check_project_overrides(project, config, URL)


if __name__ == "__main__":
    unittest.main()
