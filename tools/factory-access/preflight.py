#!/usr/bin/env python3
"""Prove read-only ledger access and emit an MCP config with an env reference."""

import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


class PreflightError(Exception):
    pass


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "partnersync.app.n8n.cloud"
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path != "/mcp/chat-to-code-factory"
    ):
        raise PreflightError("Set FACTORY_LEDGER_MCP_URL to the approved HTTPS bearer MCP endpoint, without credentials or a query.")


class Client:
    def __init__(self, url, token, opener=None):
        self.url = url
        self.token = token
        self.opener = opener or urllib.request.build_opener(NoRedirects())
        self.session = None
        self.protocol = "2024-11-05"
        self.sequence = 0
        self.deadline = time.monotonic() + 120

    def call(self, method, params, notification=False):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise PreflightError("Ledger MCP preflight exceeded its two-minute budget.")
        self.sequence += 1
        body = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            body["id"] = self.sequence
        headers = {
            "Authorization": "Bearer " + self.token,
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": self.protocol,
        }
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with self.opener.open(request, timeout=min(20, remaining)) as response:
                self.session = response.headers.get("Mcp-Session-Id", self.session)
                if notification:
                    return None
                if "text/event-stream" in response.headers.get("Content-Type", ""):
                    data = []
                    total = 0
                    result = None
                    for raw_line in response:
                        if time.monotonic() >= self.deadline:
                            raise PreflightError("Ledger MCP preflight exceeded its two-minute budget.")
                        total += len(raw_line)
                        if total > 2_000_000:
                            raise PreflightError("Ledger MCP response exceeded the preflight limit.")
                        line = raw_line.decode("utf-8").rstrip("\r\n")
                        if line.startswith("data:"):
                            data.append(line[5:].lstrip())
                        elif not line and data:
                            candidate = json.loads("\n".join(data))
                            data = []
                            if candidate.get("id") == self.sequence:
                                result = candidate
                                break
                    if result is None:
                        raise PreflightError("Ledger MCP returned no matching RPC response.")
                else:
                    raw = response.read(2_000_001)
                    if len(raw) > 2_000_000:
                        raise PreflightError("Ledger MCP response exceeded the preflight limit.")
                    result = json.loads(raw)
        except urllib.error.HTTPError as error:
            error.close()
            if error.code in (401, 403):
                raise PreflightError("Ledger MCP rejected the runner credential; the access repair owner must verify its scope and endpoint.") from None
            raise PreflightError("Ledger MCP HTTP request failed (status %s); redirects are not followed." % error.code) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise PreflightError("Ledger MCP transport or JSON response failed; verify the approved endpoint and server health.") from None
        if not isinstance(result, dict) or result.get("jsonrpc") != "2.0" or result.get("id") != self.sequence or "error" in result or not isinstance(result.get("result"), dict):
            raise PreflightError("Ledger MCP RPC failed; inspect the server privately. Response content is withheld.")
        return result["result"]


def prove_access(client, job_id, repository):
    initialized = client.call("initialize", {
        "protocolVersion": client.protocol,
        "capabilities": {},
        "clientInfo": {"name": "factory-runner-access-preflight", "version": "1.0.0"},
    })
    protocol = initialized.get("protocolVersion")
    capabilities = initialized.get("capabilities")
    if not isinstance(protocol, str) or not protocol or any(character in protocol for character in "\r\n") or not isinstance(capabilities, dict) or not isinstance(capabilities.get("tools"), dict):
        raise PreflightError("Ledger MCP initialize did not negotiate a tool-capable session.")
    client.protocol = protocol
    client.call("notifications/initialized", {}, notification=True)
    cursor = None
    for _ in range(20):
        catalog = client.call("tools/list", {"cursor": cursor} if cursor else {})
        tool_list = catalog.get("tools")
        if not isinstance(tool_list, list) or any(not isinstance(tool, dict) for tool in tool_list):
            raise PreflightError("Ledger MCP returned an invalid tool catalog.")
        if any(tool.get("name") == "job_status" for tool in tool_list):
            break
        new_cursor = catalog.get("nextCursor")
        if not new_cursor or new_cursor == cursor:
            raise PreflightError("Authenticated ledger MCP does not expose job_status; verify the Factory endpoint tool set.")
        cursor = new_cursor
    else:
        raise PreflightError("Ledger MCP tool pagination exceeded the preflight limit.")
    result = client.call("tools/call", {"name": "job_status", "arguments": {"job_id": job_id, "mission": "", "repo": repository}})
    if result.get("isError"):
        raise PreflightError("Read-only job_status failed; the access repair owner must inspect the server privately.")
    payloads = [result.get("structuredContent")]
    content = result.get("content", [])
    if not isinstance(content, list) or any(not isinstance(block, dict) for block in content):
        raise PreflightError("Read-only job_status returned an invalid content envelope.")
    for block in content:
        if block.get("type") == "text":
            try:
                payloads.append(json.loads(block.get("text", "")))
            except ValueError:
                pass
    records = []
    for payload in payloads:
        for row in payload if isinstance(payload, list) else [payload]:
            if isinstance(row, dict):
                jobs = row.get("jobs", [])
                if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
                    raise PreflightError("Read-only job_status returned invalid job records.")
                records.extend(jobs)
    if not any(str(job.get("job_id")) == str(job_id) and job.get("repo", "").casefold() == repository.casefold() for job in records):
        raise PreflightError("job_status did not return this repository's exact job; verify the ledger mirror before building.")


def server_config(url):
    return {
        "type": "http", "url": url, "oauth": False,
        "headers": {"Authorization": "Bearer ${FACTORY_LEDGER_MCP_TOKEN}"},
    }


def check_project_overrides(cwd, user_config, url):
    expected = server_config(url)
    for directory in (cwd, *cwd.parents):
        path = directory / ".factory" / "mcp.json"
        if path == user_config or not path.exists():
            continue
        config = json.loads(path.read_text())
        servers = config.get("mcpServers", {})
        if not isinstance(servers, dict):
            raise PreflightError("A project or ancestor MCP server map is invalid; inspect it privately before building.")
        if "factory-ledger" in servers and servers["factory-ledger"] != expected:
            raise PreflightError("A project or ancestor factory-ledger MCP definition would override the approved runner config; resolve that definition before building.")


def provision_config(path, url):
    config = json.loads(path.read_text()) if path.exists() else {}
    server = server_config(url)
    servers = config.setdefault("mcpServers", {})
    if "factory-ledger" in servers and servers["factory-ledger"] != server:
        raise PreflightError("An existing factory-ledger MCP definition differs; preserve it and resolve the conflict before building.")
    servers["factory-ledger"] = server
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".preflight.tmp")
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")
    temporary.replace(path)


def main():
    token = os.environ.get("FACTORY_LEDGER_MCP_TOKEN", "")
    url = os.environ.get("FACTORY_LEDGER_MCP_URL", "")
    if not token or not url:
        raise PreflightError("Configure the approved FACTORY_LEDGER_MCP_URL and forward the existing Factory-specific FACTORY_LEDGER_MCP_TOKEN secret through the caller workflow.")
    if any(character in token for character in "\r\n"):
        raise PreflightError("The runner credential contains an invalid header character.")
    validate_url(url)
    try:
        job_id = int(os.environ.get("FACTORY_LEDGER_JOB_ID", ""))
    except ValueError:
        raise PreflightError("The authorized build has no valid issue number for the read-only ledger check.") from None
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if job_id <= 0 or not repository:
        raise PreflightError("The authorized build must provide a positive issue number and GITHUB_REPOSITORY.")
    user_config = Path.home() / ".factory" / "mcp.json"
    check_project_overrides(Path.cwd().resolve(), user_config, url)
    prove_access(Client(url, token), job_id, repository)
    provision_config(user_config, url)
    print("Factory ledger preflight: PASS (authenticated discovery and exact-job read; MCP config uses an environment reference).")


if __name__ == "__main__":
    try:
        main()
    except (PreflightError, ValueError, OSError, TypeError, AttributeError):
        error = sys.exc_info()[1]
        message = str(error) if isinstance(error, PreflightError) else "Local MCP configuration or response shape is invalid; inspect privately before building."
        print("Factory ledger preflight: FAIL: " + message, file=sys.stderr)
        sys.exit(1)
