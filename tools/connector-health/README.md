# connector-health

A read-only health check for the MCP servers already registered in Codex. It starts its own `codex app-server`, opens one ephemeral thread and calls a few harmless metadata reads directly with `mcpServer/tool/call`. It reports one line of JSON with only bounded diagnostic fields. It is not an MCP server, a gateway, a credential store or a scheduler. The approved native heartbeat runs it.

| File | What it does |
|---|---|
| `connector_health.py` | The checker. Python standard library only, minimum Python 3.11. |
| `tests/test_connector_health.py` | Offline tests. All runs use `tests/fake_codex.py` in place of the CLI, so no account, network or Codex install is needed. |
| `tests/fake_codex.py` | Stand-in for the Codex CLI that mirrors the shapes of codex-cli 0.166.0. Test use only. |
| `tests/fake_mcp_server.py` | Synthetic stdio MCP server for the optional real CLI test. |

## Invocation contract

```sh
python3 tools/connector-health/connector_health.py \
  --manifest /private/path/connector-probes.json \
  --codex /absolute/path/to/codex
```

- `--manifest` is the private probe manifest described below. It stays outside this repository.
- `--codex` is the absolute path to the installed official Codex executable. The checker never searches `PATH`.
- `CODEX_HOME` is honored the same way Codex honors it. The checker never changes it.

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Every probe passed. |
| 1 | The run completed and at least one probe did not pass. |
| 2 | The invocation or the manifest is invalid. Codex was not started. |
| 3 | The run could not reach a usable runtime: unsupported protocol, unavailable transport, a timeout before probing, a changed saved config, or an internal error. |
| 130 | Interrupted by SIGINT or SIGTERM. Owned processes were stopped first. |

Standard output is exactly one JSON object on one line. Standard error stays empty, except for the usage message argparse prints when a required option is missing.

```json
{"checked_at":"2026-11-04T00:59:20Z","duration_ms":385,"error_code":null,"format":1,"probes":[{"checked_at":"2026-11-04T00:59:21Z","duration_ms":6,"error_code":null,"probe_id":"probe-me","service":"synthetic","state":"ok"}],"report":"connector-health","state":"ok"}
```

Top-level fields: `report` (always `connector-health`), `format` (always 1), `checked_at`, `duration_ms`, `state`, `error_code`, `probes`, and `probe_index` only when a manifest entry is invalid. Each probe has exactly `probe_id`, `service`, `checked_at`, `duration_ms`, `state` and `error_code`. `probe_id` and `service` come from the manifest and must match `[a-z0-9][a-z0-9._-]{0,63}`. Every `error_code` is from the fixed list in `ERROR_CODES` or has the form `http_NNN`. The report never holds provider content, exception text, stderr, OAuth URLs, request bodies, cookies, headers, tokens, subjects or expected identities.

## Probe states

| State | Meaning |
|---|---|
| `ok` | The read met the tool's response contract and carried no error signal anywhere in its envelope. A legitimate empty list passes. |
| `auth_refused` | An explicit authentication refusal: HTTP 401, `UNAUTHENTICATED`, `invalid_grant`, an expired or revoked token, and similar. |
| `scope_refused` | An explicit permission or scope refusal: HTTP 403, `PERMISSION_DENIED`, insufficient scope, and similar. |
| `identity_mismatch` | The Gmail profile read succeeded for a mailbox other than the expected one. |
| `malformed_result` | The result did not meet its contract: no content, non-JSON text, a missing status or identity, or the wrong shape. |
| `service_error` | Any other error the service or MCP envelope reported, including `isError` with no recognizable reason. |
| `unsupported_protocol` | The installed CLI does not offer a method or parameter the checker needs, or answered the handshake in an unexpected shape. |
| `transport_unavailable` | The server is not configured, is disabled in saved config, failed to start, or the app-server process exited. |
| `timeout` | The request (`request_timeout`) or the whole run (`overall_timeout`) ran out of time. |
| `not_run` | The run was interrupted or failed internally before this probe ran. |

A process starting, a tool being advertised, or login metadata such as `auth_status` is never a passing read. Only a real tool result counts. `isError`, nested `error` and `errors` members, `ok` or `success` set to false, and status codes or status words are read through the wrapper members `result`, `response`, `data`, `body` and `payload`, including JSON carried as a string. A 403 inside a successful MCP envelope is a `scope_refused`, not a pass.

Run-level `state` is `ok` when every probe passed, `degraded` when the run completed with any other probe state, or the run failure (`manifest_invalid`, `unsupported_protocol`, `transport_unavailable`, `timeout`, `interrupted`, `internal_error`).

## Manifest

JSON, at most 64 KiB, no duplicate keys, no unknown fields. Example with synthetic values:

```json
{
  "schema": 1,
  "request_timeout_seconds": 30,
  "overall_timeout_seconds": 180,
  "probes": [
    {"id": "github-me", "service": "github", "server": "github", "tool": "get_me", "arguments": {}},
    {"id": "airtable-bases", "service": "airtable", "server": "airtable", "tool": "list_bases", "arguments": {}},
    {
      "id": "gmail-profile",
      "service": "google",
      "server": "google",
      "tool": "google_api",
      "arguments": {
        "method": "GET",
        "url": "https://gmail.googleapis.com/gmail/v1/users/me/profile",
        "subject": "mailbox@example.com"
      },
      "expected_identity": "mailbox@example.com"
    }
  ]
}
```

- `schema` must be 1. `probes` holds 1 to 32 entries with unique `id` values.
- `request_timeout_seconds` (0.5 to 120, default 30) bounds every CLI step and every request. `overall_timeout_seconds` (1 to 900, default 180) bounds the whole run. Stopping owned processes adds at most about 6 seconds after the overall limit.
- `server` is the registration name as `codex mcp list` shows it, `[A-Za-z0-9_-]{1,64}`.
- `tool` must be on the allowlist below, with exactly the arguments it allows.

| Tool | Arguments allowed | A passing read |
|---|---|---|
| `list_bases` | none | an object with a `bases` list, empty allowed |
| `get_preferences` | none | a JSON object |
| `get_me`, `get_current_user` | none | an object with an identifier such as `id`, `login` or `email`, directly or under `user`, `viewer`, `me`, `account`, `profile`, `data` or `result` |
| `search_projects` | optional `query` (text, up to 100 characters), optional `limit` (1 to 25) | a list, or an object holding one under a known collection key, empty allowed |
| `agentopus_list_projects` | optional `limit` (1 to 25) | the same as `search_projects` |
| `google_api` | exactly `method`, `url` and `subject` | HTTP status 200 and an `emailAddress` equal (case-insensitive) to `expected_identity` |

Anything else is refused before Codex starts, including generation, sending, publishing, workflow execution, billing, usage or balance reads, and arbitrary API requests. A tool name that looks harmless is not enough: only the entries above exist.

`google_api` is limited to `GET https://gmail.googleapis.com/gmail/v1/users/me/profile`, character for character. Other methods, `http`, other hosts or ports, credentials in the URL, any query string, a fragment, percent-encoding and other paths are refused. `subject` and `expected_identity` must be email addresses and come only from the manifest. The response must carry its HTTP status as `status`, `statusCode`, `status_code`, `http_status` or `httpStatus`, and the Gmail profile under `body`, `data`, `json`, `response` or `result` (an object or JSON text).

## What one run does

1. Validates the invocation and the manifest. Nothing starts if either is invalid.
2. Runs `codex app-server generate-json-schema` into a private temporary directory and proves from that schema that `initialize`, the `initialized` notice, `thread/start` with `ephemeral` and `cwd`, and `mcpServer/tool/call` with `server`, `threadId`, `tool` and `arguments` exist. `sandbox: read-only` is sent only when the schema offers it.
3. Runs `codex features list` and `codex mcp list --json`. Only server names and their enabled flag are kept. Commands, environment values and URLs are dropped at once and never printed.
4. Starts `codex app-server --listen stdio://` in its own process group and a fresh temporary directory, with stderr discarded and:
   - `-c mcp_servers.<name>.enabled=false` for every registration the manifest does not select, so no other server starts. A registration whose name cannot be passed safely stops the run (`unsafe_server_name`) before anything starts.
   - `--disable` for each of `apps`, `plugins`, `remote_plugin`, `plugin_discovery_prefetch`, `hooks`, `browser_use`, `browser_use_external`, `computer_use`, `in_app_browser`, `skill_mcp_dependency_install`, `memories` and `daemon_auto_start` that the installed CLI lists and has not removed. These can launch browser controllers, desktop integrations, connector bundles, user hooks or a shared background daemon.
5. Sends `initialize`, `initialized` and `thread/start` with `ephemeral: true`, and refuses a thread that is not ephemeral. It never sends `turn/start`, so no model turn runs and no saved chat is created.
6. Calls each probe with `mcpServer/tool/call`, one at a time. Notices are read, server requests are answered (elicitations declined, anything else refused), and stale replies to a timed-out request are ignored, so nothing deadlocks.
7. Closes stdin, then stops the owned process group with SIGTERM and then SIGKILL, each bounded. It never signals any process it did not start, so a shared app-server or the desktop app is never touched.
8. Compares the SHA-256 of `$CODEX_HOME/config.toml` before and after. The checker never writes it; a change from any source is reported as `saved_config_changed`.

The checker never reads OAuth credential files, never queries a keychain, never copies tokens and never adds credentials. It does not recover credentials or billing.

## Tests

```sh
python3 -m unittest discover -s tools/connector-health/tests -v
```

The suite covers hidden and nested authentication errors, scope refusals, a 403 inside a successful MCP envelope, a wrong Gmail identity, valid empty results, unsupported and mutating probes, malformed URLs and manifests, request and overall timeouts, cleanup of an owned process that ignores SIGTERM and of its child, leaving an unrelated process alone, interruption, and redaction checked with synthetic canary values.

The optional real-CLI test registers synthetic stdio servers in a throwaway `CODEX_HOME` and runs the checker against an installed Codex. It is skipped unless the variable is set:

```sh
CONNECTOR_HEALTH_REAL_CODEX=/absolute/path/to/codex \
  python3 -m unittest tools/connector-health/tests/test_connector_health.py -k RealCodex -v
```
