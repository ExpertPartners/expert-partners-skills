#!/usr/bin/env python3
"""Read-only connector health checker for Codex MCP registrations.

Starts a fresh, checker-owned `codex app-server` over stdio, negotiates the installed
protocol, opens one ephemeral thread and calls a small allowlist of harmless metadata
reads with `mcpServer/tool/call`. It never starts a model turn, never writes Codex
configuration and never reads credential files. Every MCP registration the manifest does
not select is disabled for this one process with `-c mcp_servers.<name>.enabled=false`.

The report holds only allowlisted fields: probe identifier, service, check time, duration,
state and a bounded error code. Provider content, exception text and stderr never reach it.

Usage: connector_health.py --manifest PATH --codex /absolute/path/to/codex
Exit codes: 0 every probe passed, 1 at least one probe did not pass, 2 the manifest or the
invocation is invalid, 3 the run could not reach a usable runtime, 130 interrupted.

Python standard library only. Minimum Python 3.11.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import IO, Any, Callable
from urllib.parse import parse_qsl, urlsplit

MIN_PYTHON = (3, 11)
REPORT_NAME = "connector-health"
REPORT_FORMAT = 1
CLIENT_NAME = "connector_health"
CLIENT_VERSION = "1.0.0"

OK = "ok"
AUTH_REFUSED = "auth_refused"
SCOPE_REFUSED = "scope_refused"
IDENTITY_MISMATCH = "identity_mismatch"
MALFORMED = "malformed_result"
SERVICE_ERROR = "service_error"
UNSUPPORTED = "unsupported_protocol"
TRANSPORT = "transport_unavailable"
TIMEOUT = "timeout"
NOT_RUN = "not_run"
PROBE_STATES = frozenset(
    {OK, AUTH_REFUSED, SCOPE_REFUSED, IDENTITY_MISMATCH, MALFORMED, SERVICE_ERROR, UNSUPPORTED, TRANSPORT, TIMEOUT, NOT_RUN}
)
DEGRADED = "degraded"
MANIFEST_INVALID = "manifest_invalid"
INTERNAL_ERROR = "internal_error"
INTERRUPTED = "interrupted"
RUN_STATES = PROBE_STATES | {DEGRADED, MANIFEST_INVALID, INTERNAL_ERROR, INTERRUPTED}

ERROR_CODES = frozenset(
    {
        # results
        "mcp_is_error", "nested_error", "status_failed", "auth_error", "scope_error", "not_json",
        "contract_mismatch", "missing_content", "missing_status", "unexpected_status",
        "missing_identity", "identity_mismatch",
        # runtime
        "rpc_error", "server_unknown", "server_not_configured", "server_disabled",
        "server_startup_failed", "request_timeout", "overall_timeout", "process_exited",
        "broken_pipe", "spawn_failed", "schema_unavailable", "method_missing", "param_missing",
        "initialize_invalid", "thread_start_invalid", "ephemeral_not_honored",
        "mcp_list_unavailable", "mcp_list_unparseable", "unsafe_server_name",
        "features_unavailable", "saved_config_changed", "interrupted", "internal_error",
        # invocation and manifest
        "python_too_old", "codex_not_executable", "manifest_unreadable", "manifest_too_large",
        "manifest_invalid_json", "duplicate_key", "manifest_invalid", "unknown_field",
        "invalid_id", "duplicate_probe_id", "invalid_service", "invalid_server", "invalid_timeout",
        "unsupported_tool", "invalid_arguments", "unsupported_method", "untrusted_scheme",
        "untrusted_host", "credentials_in_url", "unexpected_query", "unsupported_path",
        "malformed_url", "missing_subject", "invalid_subject", "missing_expected_identity",
        "invalid_expected_identity", "unexpected_field",
    }
)
HTTP_CODE = re.compile(r"http_[1-5][0-9]{2}")

ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
SERVER_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}")
EMAIL = re.compile(r"[A-Za-z0-9._%+'-]{1,64}@[A-Za-z0-9-]{1,63}(\.[A-Za-z0-9-]{1,63}){1,8}")
THREAD_ID = re.compile(r"[A-Za-z0-9:_-]{1,128}")

MAX_MANIFEST_BYTES = 64 * 1024
MAX_PROBES = 32
MAX_LINE_BYTES = 8 * 1024 * 1024
MAX_CLI_OUTPUT = 8 * 1024 * 1024
DEFAULT_REQUEST_TIMEOUT = 30.0
DEFAULT_OVERALL_TIMEOUT = 180.0
CLEANUP_GRACE = 2.0

GMAIL_HOST = "gmail.googleapis.com"
GMAIL_PROFILE_PATH = "/gmail/v1/users/me/profile"
GMAIL_PROFILE_URL = "https://" + GMAIL_HOST + GMAIL_PROFILE_PATH
CREDENTIAL_QUERY_KEYS = frozenset({"access_token", "token", "key", "api_key", "apikey", "oauth_token", "id_token", "auth", "bearer"})

# Features that can launch browser controllers, desktop integrations, connector bundles,
# user hooks or a shared background daemon. Only names the installed CLI lists (and has not removed) are disabled, because
# `--disable` with an unknown name makes app-server refuse to start.
ISOLATING_FEATURES = (
    "apps",
    "plugins",
    "remote_plugin",
    "plugin_discovery_prefetch",
    "hooks",
    "browser_use",
    "browser_use_external",
    "computer_use",
    "in_app_browser",
    "skill_mcp_dependency_install",
    "memories",
    "daemon_auto_start",
)

REQUIRED_METHODS = ("initialize", "thread/start", "mcpServer/tool/call")
AUTH_WORDS = re.compile(
    r"unauthori[sz]ed|unauthenticated|not authenticated|authentication (?:required|failed)|"
    r"invalid[_ ]?grant|invalid[_ ]?token|invalid[_ ]?client|token (?:has )?expired|expired[_ ]token|revoked|"
    r"login required|re-?authenticate|reauth|\b401\b",
    re.IGNORECASE,
)
SCOPE_WORDS = re.compile(
    r"insufficient[_ ]?(?:scope|permission)s?|permission[_ ]?denied|forbidden|access[_ ]?denied|"
    r"missing (?:required )?scopes?|insufficient_scope|not authori[sz]ed to|\b403\b",
    re.IGNORECASE,
)
ERROR_WORDS = re.compile(r"^\s*(?:error|failed|failure|exception|fatal)\b", re.IGNORECASE)
TIMEOUT_WORDS = re.compile(r"timed? ?out|deadline exceeded", re.IGNORECASE)
STARTUP_WORDS = re.compile(
    r"failed to start|startup|not ready|connection closed|transport|spawn|handshak|no such file|not found",
    re.IGNORECASE,
)
STATUS_KEYS = ("status", "statusCode", "status_code", "http_status", "httpStatus", "code")
AUTH_STATUS_WORDS = frozenset({"unauthorized", "unauthenticated", "invalid_grant", "invalid_token", "expired"})
SCOPE_STATUS_WORDS = frozenset({"forbidden", "permission_denied", "insufficient_scope", "access_denied"})
FAILED_STATUS_WORDS = frozenset({"error", "failed", "failure", "fail", "denied"})
ENVELOPE_KEYS = ("result", "response", "data", "body", "payload")
IDENTITY_KEYS = ("id", "login", "email", "emailAddress", "username", "user_id", "userId", "name", "handle")
IDENTITY_WRAPPERS = ("user", "viewer", "me", "account", "profile", "data", "result")
COLLECTION_KEYS = ("bases", "projects", "results", "items", "nodes", "records", "data", "entries")


class CheckError(Exception):
    """A failure with a bounded machine code. Its args are never printed."""

    def __init__(self, state: str, code: str, probe_index: int | None = None) -> None:
        super().__init__(code)
        self.state = state
        self.code = code
        self.probe_index = probe_index


class ManifestError(CheckError):
    def __init__(self, code: str, probe_index: int | None = None) -> None:
        super().__init__(MANIFEST_INVALID, code, probe_index)


class RpcError(Exception):
    """A JSON-RPC error from app-server. The message is kept for classification only."""

    def __init__(self, message: str) -> None:
        super().__init__("rpc_error")
        self.message = message


class Interrupted(BaseException):
    pass


# While owned processes are being stopped, a signal is recorded instead of raised, so an
# interrupt can never cut cleanup short and leave a child running.
_CLEANING = threading.Event()
_INTERRUPTED = threading.Event()


# ---------------------------------------------------------------------------------------
# Manifest

ArgCheck = Callable[[Any], bool]


def _short_text(value: Any) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 100 and value.isprintable()


def _small_int(value: Any) -> bool:
    return type(value) is int and 1 <= value <= 25


@dataclass(frozen=True)
class ToolSpec:
    contract: str
    optional_args: tuple[tuple[str, ArgCheck], ...] = ()
    list_keys: tuple[str, ...] = COLLECTION_KEYS


# Explicit allowlist of harmless authenticated metadata reads. A tool's name alone never
# admits it: each entry fixes the argument keys and value shapes it accepts and the
# response contract a passing read must meet.
TOOL_SPECS: dict[str, ToolSpec] = {
    "list_bases": ToolSpec("collection", (), ("bases",)),
    "get_preferences": ToolSpec("object"),
    "get_me": ToolSpec("identity"),
    "get_current_user": ToolSpec("identity"),
    "search_projects": ToolSpec("collection", (("query", _short_text), ("limit", _small_int))),
    "agentopus_list_projects": ToolSpec("collection", (("limit", _small_int),)),
    "google_api": ToolSpec("gmail_profile"),
}


@dataclass(frozen=True)
class Probe:
    probe_id: str
    service: str
    server: str
    tool: str
    arguments: dict[str, Any]
    expected_identity: str | None = None


@dataclass(frozen=True)
class Manifest:
    probes: tuple[Probe, ...]
    request_timeout: float
    overall_timeout: float


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ManifestError("duplicate_key")
        out[key] = value
    return out


def _timeout(value: Any, default: float, low: float, high: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise ManifestError("invalid_timeout")
    return float(value)


def validate_gmail_url(url: Any) -> None:
    if not isinstance(url, str) or not url or len(url) > 200:
        raise ManifestError("malformed_url")
    if any(ch.isspace() or not ch.isprintable() for ch in url) or "\\" in url:
        raise ManifestError("malformed_url")
    try:
        parts = urlsplit(url)
        parts.port
    except ValueError:
        raise ManifestError("malformed_url") from None
    if parts.scheme != "https":
        raise ManifestError("untrusted_scheme")
    if "@" in parts.netloc or parts.username is not None or parts.password is not None:
        raise ManifestError("credentials_in_url")
    if parts.netloc != GMAIL_HOST or parts.hostname != GMAIL_HOST:
        raise ManifestError("untrusted_host")
    if parts.query or "?" in url:
        keys = {key.lower() for key, _ in parse_qsl(parts.query, keep_blank_values=True)}
        if keys & CREDENTIAL_QUERY_KEYS:
            raise ManifestError("credentials_in_url")
        raise ManifestError("unexpected_query")
    if parts.fragment or "#" in url or "%" in url:
        raise ManifestError("malformed_url")
    if parts.path != GMAIL_PROFILE_PATH:
        raise ManifestError("unsupported_path")
    if url != GMAIL_PROFILE_URL:
        raise ManifestError("malformed_url")


def _validate_google_arguments(args: dict[str, Any], index: int) -> None:
    if "method" not in args or "url" not in args:
        raise ManifestError("invalid_arguments", index)
    if "subject" not in args:
        raise ManifestError("missing_subject", index)
    if set(args) != {"method", "url", "subject"}:
        raise ManifestError("invalid_arguments", index)
    if args["method"] != "GET":
        raise ManifestError("unsupported_method", index)
    try:
        validate_gmail_url(args["url"])
    except ManifestError as exc:
        raise ManifestError(exc.code, index) from None
    if not isinstance(args["subject"], str) or not EMAIL.fullmatch(args["subject"]):
        raise ManifestError("invalid_subject", index)


def _validate_arguments(tool: str, args: Any, index: int) -> dict[str, Any]:
    if not isinstance(args, dict):
        raise ManifestError("invalid_arguments", index)
    spec = TOOL_SPECS[tool]
    if spec.contract == "gmail_profile":
        _validate_google_arguments(args, index)
        return dict(args)
    allowed = dict(spec.optional_args)
    for key, value in args.items():
        check = allowed.get(key)
        if check is None or not check(value):
            raise ManifestError("invalid_arguments", index)
    return dict(args)


def _validate_probe(raw: Any, index: int) -> Probe:
    if not isinstance(raw, dict):
        raise ManifestError("manifest_invalid", index)
    allowed = {"id", "service", "server", "tool", "arguments", "expected_identity"}
    if set(raw) - allowed:
        raise ManifestError("unknown_field", index)
    probe_id = raw.get("id")
    if not isinstance(probe_id, str) or not ID_PATTERN.fullmatch(probe_id):
        raise ManifestError("invalid_id", index)
    service = raw.get("service")
    if not isinstance(service, str) or not ID_PATTERN.fullmatch(service):
        raise ManifestError("invalid_service", index)
    server = raw.get("server")
    if not isinstance(server, str) or not SERVER_NAME.fullmatch(server):
        raise ManifestError("invalid_server", index)
    tool = raw.get("tool")
    if not isinstance(tool, str) or tool not in TOOL_SPECS:
        raise ManifestError("unsupported_tool", index)
    arguments = _validate_arguments(tool, raw.get("arguments", {}), index)
    expected = raw.get("expected_identity")
    if TOOL_SPECS[tool].contract == "gmail_profile":
        if expected is None:
            raise ManifestError("missing_expected_identity", index)
        if not isinstance(expected, str) or not EMAIL.fullmatch(expected):
            raise ManifestError("invalid_expected_identity", index)
    elif expected is not None:
        raise ManifestError("unexpected_field", index)
    return Probe(probe_id, service, server, tool, arguments, expected)


def parse_manifest(data: bytes) -> Manifest:
    if len(data) > MAX_MANIFEST_BYTES:
        raise ManifestError("manifest_too_large")
    try:
        raw = json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except ManifestError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise ManifestError("manifest_invalid_json") from None
    if not isinstance(raw, dict):
        raise ManifestError("manifest_invalid")
    if set(raw) - {"schema", "request_timeout_seconds", "overall_timeout_seconds", "probes"}:
        raise ManifestError("unknown_field")
    if raw.get("schema") != 1 or isinstance(raw.get("schema"), bool):
        raise ManifestError("manifest_invalid")
    probes_raw = raw.get("probes")
    if not isinstance(probes_raw, list) or not 1 <= len(probes_raw) <= MAX_PROBES:
        raise ManifestError("manifest_invalid")
    probes = tuple(_validate_probe(item, index) for index, item in enumerate(probes_raw))
    seen: set[str] = set()
    for index, probe in enumerate(probes):
        if probe.probe_id in seen:
            raise ManifestError("duplicate_probe_id", index)
        seen.add(probe.probe_id)
    request_timeout = _timeout(raw.get("request_timeout_seconds"), DEFAULT_REQUEST_TIMEOUT, 0.5, 120)
    overall_timeout = _timeout(raw.get("overall_timeout_seconds"), DEFAULT_OVERALL_TIMEOUT, 1, 900)
    return Manifest(probes, request_timeout, overall_timeout)


def load_manifest(path: str) -> Manifest:
    try:
        info = os.stat(path)
        if not stat.S_ISREG(info.st_mode):
            raise ManifestError("manifest_unreadable")
        if info.st_size > MAX_MANIFEST_BYTES:
            raise ManifestError("manifest_too_large")
        with open(path, "rb") as fh:
            data = fh.read(MAX_MANIFEST_BYTES + 1)
    except OSError:
        raise ManifestError("manifest_unreadable") from None
    return parse_manifest(data)


# ---------------------------------------------------------------------------------------
# Result classification


def _strings(node: Any, depth: int = 0, budget: list[int] | None = None) -> list[str]:
    budget = budget if budget is not None else [200]
    if depth > 6 or budget[0] <= 0:
        return []
    budget[0] -= 1
    if isinstance(node, str):
        return [node[:2000]]
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return [str(node)]
    out: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            out.append(str(key)[:200])
            out.extend(_strings(value, depth + 1, budget))
    elif isinstance(node, list):
        for value in node[:50]:
            out.extend(_strings(value, depth + 1, budget))
    return out


def _keyword_state(texts: list[str]) -> tuple[str, str] | None:
    joined = "\n".join(texts)
    if SCOPE_WORDS.search(joined):
        return SCOPE_REFUSED, "scope_error"
    if AUTH_WORDS.search(joined):
        return AUTH_REFUSED, "auth_error"
    return None


def _http_state(code: int) -> tuple[str, str]:
    if code in (401, 407):
        return AUTH_REFUSED, f"http_{code}"
    if code == 403:
        return SCOPE_REFUSED, f"http_{code}"
    return SERVICE_ERROR, f"http_{code}"


def _status_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit() and len(value) == 3:
        return int(value)
    return None


def _maybe_json(value: Any) -> Any:
    if isinstance(value, str) and len(value) <= MAX_LINE_BYTES:
        text = value.strip()
        if text[:1] in ("{", "["):
            try:
                return json.loads(text)
            except (ValueError, RecursionError):
                return value
    return value


def find_error(node: Any, depth: int = 0) -> tuple[str, str] | None:
    """Find an error signal in a service envelope: explicit status codes or words, ok or
    success false, a non-empty error or errors member, searched through wrapper members
    (result, response, data, body, payload). Records inside lists are not envelopes."""
    if depth > 5 or not isinstance(node, dict):
        return None
    for key in STATUS_KEYS:
        code = _status_int(node.get(key))
        if code is not None and 400 <= code <= 599:
            return _http_state(code)
    for key in STATUS_KEYS:
        value = node.get(key)
        if isinstance(value, str) and key != "code":
            word = value.strip().lower().replace(" ", "_")
            if word in AUTH_STATUS_WORDS:
                return AUTH_REFUSED, "auth_error"
            if word in SCOPE_STATUS_WORDS:
                return SCOPE_REFUSED, "scope_error"
            if word in FAILED_STATUS_WORDS:
                return _keyword_state(_strings(node)) or (SERVICE_ERROR, "status_failed")
    if node.get("ok") is False or node.get("success") is False:
        return _keyword_state(_strings(node)) or (SERVICE_ERROR, "status_failed")
    error = node.get("error")
    if error not in (None, False, "", {}, []):
        error = _maybe_json(error)
        return find_error(error, depth + 1) or _keyword_state(_strings(error)) or (SERVICE_ERROR, "nested_error")
    errors = node.get("errors")
    if isinstance(errors, list) and errors:
        for item in errors:
            found = find_error(_maybe_json(item), depth + 1)
            if found:
                return found
        return _keyword_state(_strings(errors)) or (SERVICE_ERROR, "nested_error")
    for key in ENVELOPE_KEYS:
        found = find_error(_maybe_json(node.get(key)), depth + 1)
        if found:
            return found
    return None


def _has_identity(node: Any, depth: int = 0) -> bool:
    if not isinstance(node, dict) or depth > 2:
        return False
    for key in IDENTITY_KEYS:
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return True
        if type(value) is int:
            return True
    return any(_has_identity(node.get(key), depth + 1) for key in IDENTITY_WRAPPERS)


def _is_collection(node: Any, keys: tuple[str, ...], depth: int = 0) -> bool:
    if isinstance(node, list):
        return True
    if not isinstance(node, dict) or depth > 2:
        return False
    for key in keys:
        if isinstance(node.get(key), list):
            return True
    return any(_is_collection(node.get(key), keys, depth + 1) for key in ("data", "result", "response"))


def _gmail_profile(payload: Any, expected: str) -> tuple[str, str | None]:
    if not isinstance(payload, dict):
        return MALFORMED, "contract_mismatch"
    status = None
    for key in ("status", "statusCode", "status_code", "http_status", "httpStatus"):
        if key in payload:
            status = _status_int(payload[key])
            break
    if status is None:
        return MALFORMED, "missing_status"
    if status != 200:
        if 400 <= status <= 599:
            return _http_state(status)
        return MALFORMED, "unexpected_status"
    body: Any = None
    for key in ("body", "data", "json", "response", "result"):
        candidate = _maybe_json(payload.get(key))
        if isinstance(candidate, dict):
            body = candidate
            break
    if body is None and "emailAddress" in payload:
        body = payload
    if not isinstance(body, dict):
        return MALFORMED, "missing_identity"
    address = body.get("emailAddress")
    if not isinstance(address, str) or not address.strip():
        return MALFORMED, "missing_identity"
    if address.strip().casefold() != expected.casefold():
        return IDENTITY_MISMATCH, "identity_mismatch"
    return OK, None


def classify_result(result: Any, probe: Probe) -> tuple[str, str | None]:
    """Judge one mcpServer/tool/call result. Only a read that meets the tool's response
    contract with no error signal anywhere in its envelope passes."""
    if not isinstance(result, dict) or not isinstance(result.get("content"), list):
        return MALFORMED, "missing_content"
    is_error = result.get("isError")
    if is_error is not None and not isinstance(is_error, bool):
        return MALFORMED, "missing_content"
    documents: list[Any] = []
    raw_texts: list[str] = []
    structured = result.get("structuredContent")
    if isinstance(structured, (dict, list)):
        documents.append(structured)
    for item in result["content"]:
        if not isinstance(item, dict):
            return MALFORMED, "missing_content"
        if item.get("type") == "text":
            text = item.get("text")
            if not isinstance(text, str):
                return MALFORMED, "missing_content"
            parsed = _maybe_json(text)
            if isinstance(parsed, (dict, list)):
                documents.append(parsed)
            else:
                raw_texts.append(text[:4000])
    found: tuple[str, str] | None = None
    for document in documents:
        candidates = document if isinstance(document, list) and len(document) == 1 else [document]
        for candidate in candidates:
            found = found or find_error(candidate)
    if is_error:
        if found:
            return found
        return _keyword_state(raw_texts + _strings(documents)) or (SERVICE_ERROR, "mcp_is_error")
    if found:
        return found
    for text in raw_texts:
        keyword = _keyword_state([text])
        if keyword:
            return keyword
        if ERROR_WORDS.search(text):
            return SERVICE_ERROR, "nested_error"
    if not documents:
        return MALFORMED, "not_json"
    payload = documents[0]
    spec = TOOL_SPECS[probe.tool]
    if spec.contract == "gmail_profile":
        assert probe.expected_identity is not None
        return _gmail_profile(payload, probe.expected_identity)
    if spec.contract == "identity":
        return (OK, None) if _has_identity(payload) else (MALFORMED, "contract_mismatch")
    if spec.contract == "collection":
        return (OK, None) if _is_collection(payload, spec.list_keys) else (MALFORMED, "contract_mismatch")
    return (OK, None) if isinstance(payload, dict) else (MALFORMED, "contract_mismatch")


def classify_rpc_error(message: str, startup_failed: bool) -> tuple[str, str]:
    if "unknown mcp server" in message.lower():
        return TRANSPORT, "server_unknown"
    if startup_failed:
        return TRANSPORT, "server_startup_failed"
    keyword = _keyword_state([message])
    if keyword:
        return keyword
    if TIMEOUT_WORDS.search(message):
        return TIMEOUT, "request_timeout"
    if STARTUP_WORDS.search(message):
        return TRANSPORT, "server_startup_failed"
    return SERVICE_ERROR, "rpc_error"


# ---------------------------------------------------------------------------------------
# Owned subprocesses


def _signal_group(proc: subprocess.Popen[bytes], sig: int) -> None:
    try:
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, sig)
        elif sig == getattr(signal, "SIGKILL", None):
            proc.kill()
        else:
            proc.terminate()
    except (ProcessLookupError, PermissionError, OSError):
        pass


def stop_owned(proc: subprocess.Popen[bytes], grace: float = CLEANUP_GRACE) -> None:
    """Stop a checker-owned process and its process group: polite exit first, then SIGTERM,
    then SIGKILL, each bounded. Only the group this checker created is ever signaled."""
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass
    _signal_group(proc, signal.SIGTERM)
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass
    _signal_group(proc, getattr(signal, "SIGKILL", signal.SIGTERM))
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass


def run_cli(argv: list[str], timeout: float, cwd: str) -> tuple[int, bytes]:
    """Run a short CLI command with stderr discarded, bounded output and bounded time."""
    if timeout <= 0:
        raise CheckError(TIMEOUT, "overall_timeout")
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=cwd,
            start_new_session=True,
        )
    except OSError:
        raise CheckError(TRANSPORT, "spawn_failed") from None
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        raise CheckError(TIMEOUT, "request_timeout") from None
    finally:
        # Only a command that is still running is stopped. Anything a finished command left
        # behind (for example a shared daemon) is not this checker's to stop.
        if proc.returncode is None:
            _CLEANING.set()
            try:
                _signal_group(proc, getattr(signal, "SIGKILL", signal.SIGTERM))
                try:
                    proc.wait(timeout=CLEANUP_GRACE)
                except subprocess.TimeoutExpired:
                    pass
            finally:
                _CLEANING.clear()
        if _INTERRUPTED.is_set():
            raise Interrupted()
    if len(out) > MAX_CLI_OUTPUT:
        raise CheckError(UNSUPPORTED, "schema_unavailable")
    return proc.returncode, out


class AppServer:
    """JSON-RPC over stdio to one checker-owned app-server. Messages are read on a daemon
    thread into a queue, so notifications, server requests, stale or garbled lines never
    block a waiting request, and every wait has a deadline."""

    def __init__(self, argv: list[str], cwd: str) -> None:
        try:
            self.proc: subprocess.Popen[bytes] = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=cwd,
                start_new_session=True,
            )
        except OSError:
            raise CheckError(TRANSPORT, "spawn_failed") from None
        self.inbox: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.next_id = 1
        self.eof = False
        self.startup: dict[str, str] = {}
        self.lock = threading.Lock()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self) -> None:
        stream = self.proc.stdout
        assert stream is not None
        try:
            while True:
                line = stream.readline(MAX_LINE_BYTES + 1)
                if not line:
                    break
                if len(line) > MAX_LINE_BYTES and not line.endswith(b"\n"):
                    while True:
                        rest = stream.readline(MAX_LINE_BYTES + 1)
                        if not rest or rest.endswith(b"\n"):
                            break
                    continue
                try:
                    message = json.loads(line)
                except (ValueError, RecursionError):
                    continue
                if isinstance(message, dict):
                    self.inbox.put(("message", message))
        except (OSError, ValueError):
            pass
        finally:
            self.inbox.put(("eof", None))

    def _write(self, message: dict[str, Any]) -> None:
        stdin: IO[bytes] | None = self.proc.stdin
        if stdin is None:
            raise CheckError(TRANSPORT, "broken_pipe")
        data = json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
        try:
            with self.lock:
                stdin.write(data)
                stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            raise CheckError(TRANSPORT, "broken_pipe") from None

    def notify(self, method: str) -> None:
        self._write({"method": method})

    def _answer_server_request(self, message: dict[str, Any]) -> None:
        if message.get("method") == "mcpServer/elicitation/request":
            self._write({"id": message["id"], "result": {"action": "decline"}})
        else:
            self._write({"id": message["id"], "error": {"code": -32601, "message": "not supported by the health checker"}})

    def _note(self, message: dict[str, Any]) -> None:
        if message.get("method") == "mcpServer/startupStatus/updated":
            params = message.get("params")
            if isinstance(params, dict) and isinstance(params.get("name"), str) and isinstance(params.get("status"), str):
                self.startup[params["name"]] = params["status"]

    def request(self, method: str, params: dict[str, Any], deadline: float) -> Any:
        if self.eof:
            raise CheckError(TRANSPORT, "process_exited")
        request_id = self.next_id
        self.next_id += 1
        self._write({"id": request_id, "method": method, "params": params})
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CheckError(TIMEOUT, "request_timeout")
            try:
                kind, message = self.inbox.get(timeout=min(remaining, 0.25))
            except queue.Empty:
                continue
            if kind == "eof":
                self.eof = True
                raise CheckError(TRANSPORT, "process_exited")
            if "method" in message:
                if "id" in message:
                    self._answer_server_request(message)
                else:
                    self._note(message)
                continue
            if message.get("id") != request_id:
                continue
            if "error" in message:
                error = message["error"]
                text = error.get("message") if isinstance(error, dict) else None
                raise RpcError(text if isinstance(text, str) else "")
            if "result" in message:
                return message["result"]
            raise CheckError(UNSUPPORTED, "rpc_error")

    def close(self) -> None:
        _CLEANING.set()
        try:
            stdin = self.proc.stdin
            try:
                if stdin is not None:
                    stdin.close()
            except OSError:
                pass
            stop_owned(self.proc)
            try:
                if self.proc.stdout is not None:
                    self.proc.stdout.close()
            except OSError:
                pass
        finally:
            _CLEANING.clear()
        if _INTERRUPTED.is_set():
            raise Interrupted()


# ---------------------------------------------------------------------------------------
# Protocol discovery from the installed CLI


def _load_json(path: str) -> Any:
    try:
        with open(path, "rb") as fh:
            return json.load(fh)
    except (OSError, ValueError, RecursionError):
        raise CheckError(UNSUPPORTED, "schema_unavailable") from None


def _union_methods(schema: Any) -> set[str]:
    methods: set[str] = set()
    variants = schema.get("oneOf", []) if isinstance(schema, dict) else []
    for variant in variants if isinstance(variants, list) else []:
        enum = variant.get("properties", {}).get("method", {}).get("enum") if isinstance(variant, dict) else None
        if isinstance(enum, list):
            methods.update(m for m in enum if isinstance(m, str))
    return methods


def _properties(schema: Any) -> dict[str, Any]:
    props = schema.get("properties") if isinstance(schema, dict) else None
    return props if isinstance(props, dict) else {}


@dataclass(frozen=True)
class Protocol:
    read_only_sandbox: bool


def verify_protocol(schema_dir: str) -> Protocol:
    """Prove from the installed CLI's own generated schema that every method and parameter
    the checker sends exists. Nothing is assumed from documentation."""
    requests = _union_methods(_load_json(os.path.join(schema_dir, "ClientRequest.json")))
    if not set(REQUIRED_METHODS) <= requests:
        raise CheckError(UNSUPPORTED, "method_missing")
    if "initialized" not in _union_methods(_load_json(os.path.join(schema_dir, "ClientNotification.json"))):
        raise CheckError(UNSUPPORTED, "method_missing")
    init = _properties(_load_json(os.path.join(schema_dir, "v1", "InitializeParams.json")))
    if "clientInfo" not in init:
        raise CheckError(UNSUPPORTED, "param_missing")
    thread_schema = _load_json(os.path.join(schema_dir, "v2", "ThreadStartParams.json"))
    thread = _properties(thread_schema)
    ephemeral = thread.get("ephemeral")
    if not isinstance(ephemeral, dict) or "boolean" not in json.dumps(ephemeral.get("type")) or "cwd" not in thread:
        raise CheckError(UNSUPPORTED, "param_missing")
    call_schema = _load_json(os.path.join(schema_dir, "v2", "McpServerToolCallParams.json"))
    call = _properties(call_schema)
    required = call_schema.get("required") if isinstance(call_schema, dict) else None
    if not {"server", "threadId", "tool", "arguments"} <= set(call) or not isinstance(required, list):
        raise CheckError(UNSUPPORTED, "param_missing")
    if not set(required) <= {"server", "threadId", "tool", "arguments"} or not {"server", "threadId", "tool"} <= set(required):
        raise CheckError(UNSUPPORTED, "param_missing")
    sandbox = thread_schema.get("definitions", {}).get("SandboxMode", {}) if isinstance(thread_schema, dict) else {}
    read_only = "sandbox" in thread and isinstance(sandbox, dict) and "read-only" in (sandbox.get("enum") or [])
    return Protocol(read_only_sandbox=read_only)


def parse_features(output: bytes) -> set[str]:
    names: set[str] = set()
    for line in output.decode("utf-8", "replace").splitlines():
        tokens = line.split()
        if len(tokens) >= 3 and re.fullmatch(r"[a-z0-9_.]+", tokens[0]) and "removed" not in tokens[1:-1]:
            names.add(tokens[0])
    return names


def parse_mcp_list(output: bytes) -> dict[str, bool]:
    """Reduce `codex mcp list --json` to name -> enabled. Everything else in it (commands,
    environment, URLs) is dropped here and never stored or printed."""
    try:
        entries = json.loads(output.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise CheckError(UNSUPPORTED, "mcp_list_unparseable") from None
    if not isinstance(entries, list):
        raise CheckError(UNSUPPORTED, "mcp_list_unparseable")
    servers: dict[str, bool] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise CheckError(UNSUPPORTED, "mcp_list_unparseable")
        enabled = entry.get("enabled", True)
        servers[entry["name"]] = enabled if isinstance(enabled, bool) else True
    return servers


def saved_config_digest() -> str | None:
    home = os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
    try:
        with open(os.path.join(home, "config.toml"), "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except FileNotFoundError:
        return None
    except OSError:
        return "unreadable"


# ---------------------------------------------------------------------------------------
# Report


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_code(code: str | None) -> str | None:
    if code is None:
        return None
    if code in ERROR_CODES or HTTP_CODE.fullmatch(code):
        return code
    return "internal_error"


@dataclass
class ProbeResult:
    probe: Probe
    checked_at: str
    duration_ms: int
    state: str
    error_code: str | None

    def record(self) -> dict[str, Any]:
        state = self.state if self.state in PROBE_STATES else SERVICE_ERROR
        return {
            "probe_id": self.probe.probe_id,
            "service": self.probe.service,
            "checked_at": self.checked_at,
            "duration_ms": max(0, int(self.duration_ms)),
            "state": state,
            "error_code": None if state == OK else (_safe_code(self.error_code) or "internal_error"),
        }


def build_report(
    started: str,
    duration_ms: int,
    results: list[ProbeResult],
    run_state: str | None = None,
    run_code: str | None = None,
    probe_index: int | None = None,
) -> dict[str, Any]:
    if run_state is None:
        run_state = OK if results and all(r.state == OK for r in results) else DEGRADED
    if run_state not in RUN_STATES:
        run_state, run_code = INTERNAL_ERROR, "internal_error"
    report: dict[str, Any] = {
        "report": REPORT_NAME,
        "format": REPORT_FORMAT,
        "checked_at": started,
        "duration_ms": max(0, int(duration_ms)),
        "state": run_state,
        "error_code": _safe_code(run_code),
        "probes": [r.record() for r in results],
    }
    if probe_index is not None:
        report["probe_index"] = int(probe_index)
    return report


# ---------------------------------------------------------------------------------------
# Run


def _isolation_args(selected: set[str], configured: dict[str, bool], features: set[str]) -> list[str]:
    args: list[str] = []
    for feature in ISOLATING_FEATURES:
        if feature in features:
            args += ["--disable", feature]
    for name in sorted(configured):
        if name in selected:
            continue
        if not SERVER_NAME.fullmatch(name):
            raise CheckError(UNSUPPORTED, "unsafe_server_name")
        args += ["-c", f"mcp_servers.{name}.enabled=false"]
    return args


class Runner:
    def __init__(self, manifest: Manifest, codex: str) -> None:
        self.manifest = manifest
        self.codex = codex
        self.start = time.monotonic()
        self.deadline = self.start + manifest.overall_timeout
        self.results: list[ProbeResult] = []

    def _step_deadline(self) -> float:
        return min(time.monotonic() + self.manifest.request_timeout, self.deadline)

    def _remaining(self) -> float:
        return self.deadline - time.monotonic()

    def _finish(self, probe: Probe, began: float, state: str, code: str | None) -> None:
        self.results.append(
            ProbeResult(probe, _now_iso(), int((time.monotonic() - began) * 1000), state, code)
        )

    def _fill(self, state: str, code: str) -> None:
        done = {r.probe.probe_id for r in self.results}
        for probe in self.manifest.probes:
            if probe.probe_id not in done:
                self._finish(probe, time.monotonic(), state, code)

    def run(self, workdir: str) -> tuple[str | None, str | None]:
        """Returns (run_state, run_code); (None, None) means the run completed."""
        step = min(self.manifest.request_timeout, self._remaining())
        schema_dir = os.path.join(workdir, "schema")
        rc, _ = run_cli([self.codex, "app-server", "generate-json-schema", "--out", schema_dir], step, workdir)
        if rc != 0:
            raise CheckError(UNSUPPORTED, "schema_unavailable")
        protocol = verify_protocol(schema_dir)

        rc, out = run_cli([self.codex, "features", "list"], min(self.manifest.request_timeout, self._remaining()), workdir)
        if rc != 0:
            raise CheckError(UNSUPPORTED, "features_unavailable")
        features = parse_features(out)

        rc, out = run_cli([self.codex, "mcp", "list", "--json"], min(self.manifest.request_timeout, self._remaining()), workdir)
        if rc != 0:
            raise CheckError(TRANSPORT, "mcp_list_unavailable")
        configured = parse_mcp_list(out)
        del out

        selected = {p.server for p in self.manifest.probes}
        isolation = _isolation_args(selected, configured, features)
        runnable: list[Probe] = []
        for probe in self.manifest.probes:
            if probe.server not in configured:
                self._finish(probe, time.monotonic(), TRANSPORT, "server_not_configured")
            elif not configured[probe.server]:
                self._finish(probe, time.monotonic(), TRANSPORT, "server_disabled")
            else:
                runnable.append(probe)
        if not runnable:
            return None, None

        runtime_dir = os.path.join(workdir, "cwd")
        os.mkdir(runtime_dir, 0o700)
        server = AppServer([self.codex, "app-server", *isolation, "--listen", "stdio://"], runtime_dir)
        try:
            init = server.request(
                "initialize",
                {"clientInfo": {"name": CLIENT_NAME, "title": "Connector health", "version": CLIENT_VERSION}},
                self._step_deadline(),
            )
            if not isinstance(init, dict) or not all(
                isinstance(init.get(k), str) for k in ("userAgent", "codexHome", "platformFamily", "platformOs")
            ):
                raise CheckError(UNSUPPORTED, "initialize_invalid")
            server.notify("initialized")
            params: dict[str, Any] = {"ephemeral": True, "cwd": runtime_dir}
            if protocol.read_only_sandbox:
                params["sandbox"] = "read-only"
            started = server.request("thread/start", params, self._step_deadline())
            thread = started.get("thread") if isinstance(started, dict) else None
            thread_id = thread.get("id") if isinstance(thread, dict) else None
            if not isinstance(thread_id, str) or not THREAD_ID.fullmatch(thread_id):
                raise CheckError(UNSUPPORTED, "thread_start_invalid")
            if not isinstance(thread, dict) or thread.get("ephemeral") is not True:
                raise CheckError(UNSUPPORTED, "ephemeral_not_honored")
            for probe in runnable:
                self._call(server, thread_id, probe)
        except RpcError:
            raise CheckError(UNSUPPORTED, "rpc_error") from None
        finally:
            server.close()
        return None, None

    def _call(self, server: AppServer, thread_id: str, probe: Probe) -> None:
        began = time.monotonic()
        if self._remaining() <= 0:
            self._finish(probe, began, TIMEOUT, "overall_timeout")
            return
        params = {"server": probe.server, "threadId": thread_id, "tool": probe.tool, "arguments": probe.arguments}
        try:
            result = server.request("mcpServer/tool/call", params, self._step_deadline())
        except RpcError as exc:
            failed = server.startup.get(probe.server) == "failed"
            self._finish(probe, began, *classify_rpc_error(exc.message, failed))
            return
        except CheckError as exc:
            if exc.state == TIMEOUT and self._remaining() <= 0:
                self._finish(probe, began, TIMEOUT, "overall_timeout")
                return
            if exc.state == TIMEOUT:
                self._finish(probe, began, TIMEOUT, exc.code)
                return
            raise
        state, code = classify_result(result, probe)
        self._finish(probe, began, state, code)


def _interrupt(signum: int, frame: Any) -> None:
    _INTERRUPTED.set()
    if not _CLEANING.is_set():
        raise Interrupted()


def _emit(report: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    started = _now_iso()
    clock = time.monotonic()

    def elapsed() -> int:
        return int((time.monotonic() - clock) * 1000)

    if sys.version_info < MIN_PYTHON:
        _emit(build_report(started, elapsed(), [], MANIFEST_INVALID, "python_too_old"))
        return 2

    parser = argparse.ArgumentParser(description="Read-only Codex MCP connector health check.")
    parser.add_argument("--manifest", required=True, help="private probe manifest (JSON)")
    parser.add_argument("--codex", required=True, help="absolute path to the installed codex executable")
    args = parser.parse_args(argv)

    codex = args.codex
    if not os.path.isabs(codex) or not os.path.isfile(codex) or not os.access(codex, os.X_OK):
        _emit(build_report(started, elapsed(), [], MANIFEST_INVALID, "codex_not_executable"))
        return 2
    try:
        manifest = load_manifest(args.manifest)
    except ManifestError as exc:
        _emit(build_report(started, elapsed(), [], MANIFEST_INVALID, exc.code, exc.probe_index))
        return 2

    runner = Runner(manifest, codex)
    run_state: str | None = None
    run_code: str | None = None
    exit_code = 0
    before = saved_config_digest()
    workdir = tempfile.mkdtemp(prefix="connector-health-")
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        try:
            for sig in previous:
                signal.signal(sig, _interrupt)
            run_state, run_code = runner.run(workdir)
        except CheckError as exc:
            run_state, run_code = exc.state, exc.code
            if exc.state == TIMEOUT and runner._remaining() <= 0:
                run_code = "overall_timeout"
            runner._fill(run_state, run_code)
            exit_code = 3
        except RpcError:
            run_state, run_code = UNSUPPORTED, "rpc_error"
            runner._fill(run_state, run_code)
            exit_code = 3
        except Interrupted:
            run_state, run_code = INTERRUPTED, "interrupted"
            runner._fill(NOT_RUN, "interrupted")
            exit_code = 130
        except Exception:
            run_state, run_code = INTERNAL_ERROR, "internal_error"
            runner._fill(NOT_RUN, "internal_error")
            exit_code = 3
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    if saved_config_digest() != before:
        run_state, run_code = INTERNAL_ERROR, "saved_config_changed"
        exit_code = 3
    report = build_report(started, elapsed(), runner.results, run_state, run_code)
    if exit_code == 0 and report["state"] != OK:
        exit_code = 1
    _emit(report)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
