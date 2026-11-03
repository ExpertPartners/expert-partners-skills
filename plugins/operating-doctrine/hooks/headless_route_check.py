#!/usr/bin/env python3
"""Headless route check, a Claude Code PreToolUse hook for browser navigation.

Refuses browser navigation to any system that already has headless access (an API, CLI,
MCP server, connector or 1Password item) and tells the session which headless route to use
instead (Decision Log 2026-11-03, Headless access comes first, and Standing yes for headless
access setup). Browser code tools are checked too, for URLs their code navigates to.

The access map is a Google Sheet owned by Keys and Sign-Ins. The hook reads only a local
cache of it, so a browser call never waits on Drive. When the cache is more than an hour
old, the hook starts one background refresh after it has printed its decision. A failed
refresh keeps the last good copy. With no copy at all, the hook allows and logs.

  status live        deny, naming the headless route and the 1Password item
  status setting up  deny, saying the setup job comes first
  status no API      allow
  host not on map    allow, and append the host to unknown-hosts.log for the nightly check

The map holds 1Password item names only. The hook never reads a secret, and it withholds
any map value that looks like one instead of printing it.

Usage:
  headless_route_check.py             hook mode, reads the PreToolUse JSON on stdin
  headless_route_check.py --refresh   refresh the cache now and print the result

Python 3.9 or later, standard library only. hooks/README.md explains the setup.
"""

from __future__ import annotations

import csv
import io
import ipaddress
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REFRESH_SECONDS = 3600
FETCH_TIMEOUT_SECONDS = 30

CACHE_FILE = "access-map.json"
STAMP_FILE = "refresh-attempt"
UNKNOWN_HOSTS_FILE = "unknown-hosts.log"
HOOK_LOG_FILE = "hook.log"

# Normalized header text -> field. The sheet may word its headers a little differently.
HEADER_FIELDS = {
    "system": "system",
    "hosts": "hosts",
    "host": "hosts",
    "domains": "hosts",
    "headless route": "route",
    "route": "route",
    "1password item": "item",
    "1password": "item",
    "status": "status",
    "no api reason": "reason",
    "reason": "reason",
}
REQUIRED_FIELDS = ("system", "hosts", "status")

LIVE = "live"
SETTING_UP = "setting up"
NO_API = "no api"

STATUS_TIE_ORDER = {NO_API: 0, SETTING_UP: 2, LIVE: 3}  # any other status ranks 1

SECRET_RE = re.compile(
    r"-----BEGIN"
    r"|\b(?:sk|pk|rk)-[A-Za-z0-9_-]{8,}"
    r"|\bgh[pousr]_[A-Za-z0-9]{20,}"
    r"|\bxox[abprs]-"
    r"|\beyJ[A-Za-z0-9_-]{10,}"
    r"|\bops_[A-Za-z0-9]"
    r"|\bAIza[A-Za-z0-9_-]{20,}"
    r"|\bya29\.[A-Za-z0-9_-]{10,}"
)
# Long runs of letters and digits with no separator. Names (MCP tool names, op:// paths,
# item slugs) break into short words at _ - / and spaces, while a key or hex token does not.
UNBROKEN_RUN_RE = re.compile(r"[A-Za-z0-9+=]{24,}")

# Navigation written into browser code: page.goto("..."), location.href = "...", and so on.
CODE_KEYS = ("code", "function", "script", "expression")
CODE_CALL_RE = re.compile(
    r"""(?:\.goto|\blocation\.assign|\blocation\.replace|\bwindow\.open)\s*\(\s*(['"`])(.+?)\1"""
)
CODE_ASSIGN_RE = re.compile(r"""\blocation(?:\.href)?\s*=\s*(['"`])(.+?)\1""")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_dir() -> Path:
    override = os.environ.get("EP_HEADLESS_ROUTE_DIR")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "expert-partners" / "headless-route"


def config_path() -> Path:
    override = os.environ.get("EP_HEADLESS_ROUTE_CONFIG")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return Path(base) / "expert-partners" / "headless-route.json"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)


def log_event(event: str, detail: str = "") -> None:
    try:
        directory = state_dir()
        ensure_dir(directory)
        with open(directory / HOOK_LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(f"{now_iso()}\t{event}\t{one_line(detail)}\n")
    except OSError:
        pass


def one_line(value: object, limit: int = 300) -> str:
    return " ".join(str(value).split())[:limit]


def looks_like_secret(text: str) -> bool:
    if SECRET_RE.search(text):
        return True
    return any(
        sum(char.isdigit() for char in run) >= 2 and any(char.isalpha() for char in run)
        for run in UNBROKEN_RUN_RE.findall(text)
    )


def safe(value: object) -> str:
    """A map value fit to print. Anything shaped like a secret is withheld."""
    text = one_line(value, 200)
    if looks_like_secret(text):
        return "[withheld, not an item name]"
    return text


def normalize_header(header: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", header.lower()).split())


def normalize_status(status: str) -> str:
    """One of live, setting up or no api for the wordings people use, otherwise the text."""
    text = " ".join(re.sub(r"[^a-z0-9]+", " ", status.lower()).split())
    if re.match(r"(?:no api|no|none)\b", text):
        return NO_API
    if re.search(r"\b(?:setting up|set up|setup|in progress)\b", text):
        return SETTING_UP
    if re.match(r"live\b", text):
        return LIVE
    return text


def split_hosts(cell: str) -> list[str]:
    hosts = []
    for raw in re.split(r"[\s,;]+", cell or ""):
        raw = raw.strip().lower()
        if not raw:
            continue
        if "://" in raw:
            raw = urllib.parse.urlsplit(raw).hostname or ""
        raw = raw.split("/", 1)[0].split(":", 1)[0]
        wildcard = False
        while raw.startswith("*.") or raw.startswith("."):
            if raw.startswith("*."):
                wildcard, raw = True, raw[2:]
            else:
                raw = raw[1:]
        raw = raw.rstrip(".")
        if raw:
            hosts.append("*." + raw if wildcard else raw)
    return hosts


def parse_map(csv_text: str) -> list[dict]:
    """Rows of the access map as dicts with system, hosts, route, item, status, reason."""
    rows = list(csv.reader(io.StringIO(csv_text)))
    if not rows:
        raise ValueError("the access map is empty")
    columns: dict[str, int] = {}
    for index, header in enumerate(rows[0]):
        field = HEADER_FIELDS.get(normalize_header(header))
        if field and field not in columns:
            columns[field] = index
    missing = [field for field in REQUIRED_FIELDS if field not in columns]
    if missing:
        raise ValueError("the access map is missing the column(s) " + ", ".join(missing))

    def cell(row: list[str], field: str) -> str:
        index = columns.get(field)
        return row[index].strip() if index is not None and index < len(row) else ""

    systems = []
    for row in rows[1:]:
        system = cell(row, "system")
        hosts = split_hosts(cell(row, "hosts"))
        if not system or not hosts:
            continue
        systems.append({
            "system": system,
            "hosts": hosts,
            "route": cell(row, "route"),
            "item": cell(row, "item"),
            "status": normalize_status(cell(row, "status")),
            "reason": cell(row, "reason"),
        })
    if not systems:
        raise ValueError("the access map has no rows with a system and hosts")
    return systems


def unknown_statuses(systems: list[dict]) -> list[str]:
    return [safe(entry["system"]) for entry in systems if entry.get("status") not in STATUS_TIE_ORDER]


def load_cache() -> list[dict] | None:
    try:
        with open(state_dir() / CACHE_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        systems = data["systems"]
        if not isinstance(systems, list):
            raise ValueError("systems is not a list")
        return systems
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError) as error:
        log_event("cache-unreadable", type(error).__name__)
        return None


def write_cache(systems: list[dict]) -> None:
    directory = state_dir()
    ensure_dir(directory)
    payload = {"fetched_at": now_iso(), "systems": systems}
    fd, temp_path = tempfile.mkstemp(prefix=".access-map-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        os.replace(temp_path, directory / CACHE_FILE)
    except BaseException:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def load_config() -> dict:
    config: dict = {}
    path = config_path()
    if path.exists():
        with open(path, encoding="utf-8") as handle:
            config = json.load(handle)
        if not isinstance(config, dict):
            raise ValueError(f"{path} must hold a JSON object")
    if os.environ.get("EP_ACCESS_MAP_SHEET_ID"):
        config["sheet_id"] = os.environ["EP_ACCESS_MAP_SHEET_ID"]
    return config


def run_command(argv: object, what: str) -> str:
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) for part in argv):
        raise ValueError(f"{what} must be a list of strings")
    result = subprocess.run(
        argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
        timeout=FETCH_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        # stderr is left out on purpose, a token command can echo what it was handling.
        raise RuntimeError(f"{what} exited {result.returncode}")
    return result.stdout


def fetch_map_csv(config: dict) -> str:
    if config.get("fetch_command"):
        return run_command(config["fetch_command"], "fetch_command")
    sheet_id = config.get("sheet_id")
    if not sheet_id:
        raise ValueError(f"no access map is configured, set sheet_id in {config_path()}")
    url = ("https://docs.google.com/spreadsheets/d/"
           + urllib.parse.quote(str(sheet_id), safe="") + "/export?format=csv")
    if config.get("gid") not in (None, ""):
        url += "&gid=" + urllib.parse.quote(str(config["gid"]), safe="")
    request = urllib.request.Request(url)
    if config.get("token_command"):
        token = run_command(config["token_command"], "token_command").strip()
        if not token:
            raise RuntimeError("token_command printed nothing")
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8-sig")
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise RuntimeError(
                f"the sheet export answered HTTP {error.code}, so the token cannot read the sheet. "
                "It needs a Drive scope, see Setup on each machine in hooks/README.md"
            ) from None
        raise RuntimeError(f"the sheet export answered HTTP {error.code}") from None
    except urllib.error.URLError as error:
        raise RuntimeError(f"the sheet export could not be reached ({one_line(error.reason, 80)})") from None
    if "text/html" in content_type:
        raise RuntimeError(
            "the sheet export returned a sign-in or sharing page, not CSV. The token needs a Drive "
            "scope and access to the sheet, see Setup on each machine in hooks/README.md"
        )
    return body


def touch_stamp() -> None:
    directory = state_dir()
    ensure_dir(directory)
    (directory / STAMP_FILE).touch()


def refresh() -> tuple[bool, str]:
    """Fetch the map and replace the cache. A failure leaves the last good copy in place."""
    try:
        touch_stamp()
        systems = parse_map(fetch_map_csv(load_config()))
        write_cache(systems)
    except Exception as error:  # noqa: BLE001, every failure keeps the last good copy
        message = f"{type(error).__name__}: {one_line(error, 300)}"
        log_event("refresh-failed", message)
        return False, message
    message = f"{len(systems)} systems"
    unknown = unknown_statuses(systems)
    if unknown:
        message += (f", {len(unknown)} with a status that is not live, setting up or no API, so "
                    f"the browser is let through for them: {', '.join(unknown)}")
    log_event("refresh-ok", message)
    return True, message


def refresh_due() -> bool:
    try:
        age = time.time() - (state_dir() / STAMP_FILE).stat().st_mtime
    except OSError:
        return True
    return age >= REFRESH_SECONDS


def start_background_refresh() -> None:
    try:
        touch_stamp()
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--refresh"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True, close_fds=True,
        )
    except OSError as error:
        log_event("refresh-not-started", type(error).__name__)


def target_urls(tool_input: object) -> list[str]:
    """The URL a navigation tool opens, plus any URL that browser code navigates to."""
    if not isinstance(tool_input, dict):
        return []
    urls = []
    for key in ("url", "uri", "href"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            urls.append(value.strip())
            break
    for key in CODE_KEYS:
        code = tool_input.get(key)
        if isinstance(code, str):
            for pattern in (CODE_CALL_RE, CODE_ASSIGN_RE):
                urls.extend(match.group(2).strip() for match in pattern.finditer(code))
    return urls


def target_host(url: str) -> str:
    """The host a navigation goes to, or "" when it is not a web site (about:, file:, local)."""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url) or re.match(r"^[^:/]+:\d", url):
        url = "https://" + url
    try:
        parts = urllib.parse.urlsplit(url)
        host = (parts.hostname or "").rstrip(".").lower()
    except ValueError:
        return ""
    if parts.scheme not in ("http", "https") or not host:
        return ""
    if host == "localhost" or host.endswith(".localhost"):
        return ""
    try:
        if ipaddress.ip_address(host).is_loopback:
            return ""
    except ValueError:
        pass
    return host


def match_rank(host: str, pattern: str) -> tuple[int, int] | None:
    """How specifically a map host covers the target, or None when it does not.

    A longer host ranks higher. At one length the exact host beats *.host, which matches
    subdomains only, and that beats a plain parent domain.
    """
    pattern = pattern.lower()
    if pattern.startswith("*."):
        base = pattern[2:]
        return (len(base), 1) if host.endswith("." + base) else None
    if host == pattern:
        return (len(pattern), 2)
    if host.endswith("." + pattern):
        return (len(pattern), 0)
    return None


def find_system(host: str, systems: list[dict]) -> tuple[dict | None, bool]:
    """The map entry that decides the host, and whether equally specific entries disagreed.

    Equally specific entries that disagree are settled by status, never by row order. No API
    wins, because one feature with no API on a shared host needs the browser.
    """
    best: list[dict] = []
    best_rank = None
    for entry in systems:
        ranks = [rank for rank in (match_rank(host, str(p)) for p in entry.get("hosts") or []) if rank]
        if not ranks:
            continue
        rank = max(ranks)
        if best_rank is None or rank > best_rank:
            best, best_rank = [entry], rank
        elif rank == best_rank:
            best.append(entry)
    if not best:
        return None, False
    chosen = min(best, key=lambda entry: STATUS_TIE_ORDER.get(entry.get("status"), 1))
    conflict = len({entry.get("status") for entry in best}) > 1
    return chosen, conflict


def log_unknown_host(host: str, tool_name: str) -> None:
    try:
        directory = state_dir()
        ensure_dir(directory)
        path = directory / UNKNOWN_HOSTS_FILE
        if path.exists():
            with open(path, encoding="utf-8") as handle:
                if any(line.split("\t")[1:2] == [host] for line in handle):
                    return
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{now_iso()}\t{host}\t{one_line(tool_name, 120)}\n")
    except OSError:
        pass


def deny_reason(entry: dict, host: str) -> str:
    system = safe(entry.get("system", ""))
    route = safe(entry.get("route", "")) or "the headless route on the access map"
    item = safe(entry.get("item", ""))
    item_part = f"with the 1Password item {item}" if item else "(the access map lists no 1Password item)"
    if entry.get("status") == LIVE:
        return (
            f"Headless route check: {system} has headless access, so the browser is refused for "
            f"{host}. Use {route} {item_part} instead. Decision Log 2026-11-03, Headless access "
            f"comes first. Report it as: Headless route checked, {system}, live, used {route}."
        )
    return (
        f"Headless route check: headless access to {system} is being set up, so the browser is "
        f"refused for {host}. The setup job comes first. Finish or file the setup job for "
        f"{system} ({route} {item_part}), then do this work headlessly. Decision Log 2026-11-03, "
        f"Headless access comes first. Report it as: Headless route checked, {system}, setting "
        f"up, setup job first."
    )


def decide(payload: dict) -> str | None:
    """The deny reason for this tool call, or None to let it through."""
    hosts = []
    for url in target_urls(payload.get("tool_input")):
        host = target_host(url)
        if host and host not in hosts:
            hosts.append(host)
    if not hosts:
        return None
    tool_name = str(payload.get("tool_name", ""))
    systems = load_cache()
    if systems is None:
        log_event("no-cache-allowed", f"{' '.join(hosts)} {tool_name}")
        return None
    for host in hosts:
        entry, conflict = find_system(host, systems)
        if entry is None:
            log_unknown_host(host, tool_name)
            continue
        status = entry.get("status")
        if conflict:
            log_event("map-conflict", f"{host} decided by {safe(entry.get('system', ''))} {safe(status)}")
        if status in (LIVE, SETTING_UP):
            log_event("denied", f"{host} {safe(entry.get('system', ''))} {status}")
            return deny_reason(entry, host)
        if status != NO_API:
            log_event("unknown-status-allowed", f"{host} {safe(entry.get('system', ''))} {safe(status)}")
    return None


def hook_main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        if not isinstance(payload, dict):
            payload = {}
        reason = decide(payload)
    except Exception as error:  # noqa: BLE001, a broken hook must never stop a browser call
        log_event("hook-error", type(error).__name__)
        reason = None
    if reason:
        json.dump({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }, sys.stdout)
        sys.stdout.write("\n")
    sys.stdout.flush()
    # The decision is printed before the refresh starts, so the refresh can never delay it.
    if refresh_due():
        start_background_refresh()
    return 0


def main(argv: list[str]) -> int:
    if argv[1:] == ["--refresh"]:
        ok, message = refresh()
        print(("access map refreshed, " if ok else "access map refresh failed, ") + message)
        return 0 if ok else 1
    if len(argv) > 1:
        print(__doc__, file=sys.stderr)
        return 2
    return hook_main()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
