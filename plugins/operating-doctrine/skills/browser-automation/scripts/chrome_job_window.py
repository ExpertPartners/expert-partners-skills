#!/usr/bin/env python3
"""Open one extension connection in a new window of its existing Chrome profile.

Use this packaged executable as Playwright MCP's --executable-path on the browser host.
The existing launcher still resolves its protected profile-specific credential.
This wrapper does not implement per-job transport allocation or recovery.
"""

import os
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from relay_rpc import relay_rpc


class InvalidLaunch(ValueError):
    pass


def existing_signed_in_profile(directory, expected_account, root=None):
    """Check existing identity metadata; this is not website authentication proof."""
    if not expected_account or not expected_account.strip():
        raise InvalidLaunch("Expected account is not configured")
    root = (
        (Path.home() / "Library/Application Support/Google/Chrome") if root is None else Path(root)
    )
    if not (root / directory).is_dir():
        raise InvalidLaunch("Assigned existing profile is unavailable")
    try:
        local = json.loads((root / "Local State").read_text())
        preferences = json.loads((root / directory / "Preferences").read_text())
        profile = local["profile"]["info_cache"][directory]
        primary = profile.get("user_name", "").strip().casefold()
        expected = expected_account.strip().casefold()
        accounts = {
            x.get("email", "").strip().casefold() for x in preferences.get("account_info", [])
        }
        valid = (
            primary == expected
            and expected in accounts
            and preferences.get("signin", {}).get("allowed") is not False
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise InvalidLaunch("Assigned profile identity could not be verified") from None
    if not valid:
        raise InvalidLaunch("Assigned profile does not hold the expected identity")


def chrome_is_running():
    try:
        return (
            subprocess.run(
                ["/usr/bin/pgrep", "-x", "Google Chrome"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            ).returncode
            == 0
        )
    except (OSError, subprocess.TimeoutExpired):
        return False


# A connector URL handed to a Chrome that is still starting (or to no Chrome,
# which makes the binary cold-start one) loads before the extension does and
# lands on ERR_BLOCKED_BY_CLIENT. Only hand off to a browser that has settled.
SETTLED_SECONDS = 15
SETTLE_WAIT_SECONDS = 20


def elapsed_seconds(value):
    """Parse ps etime, [[dd-]hh:]mm:ss."""
    days, _, clock = value.strip().rpartition("-")
    parts = clock.split(":")
    if (
        (days and not days.isdigit())
        or not 2 <= len(parts) <= 3
        or not all(p.isdigit() for p in parts)
    ):
        raise ValueError("Unreadable process age")
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds + int(days or 0) * 86400


def chrome_has_settled(minimum=SETTLED_SECONDS):
    """True when some main Chrome process has been up for at least minimum seconds.

    A peer job's handoff briefly runs a second short-lived main process, so any
    long-lived match counts.
    """
    try:
        ids = subprocess.run(
            ["/usr/bin/pgrep", "-x", "Google Chrome"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        ).stdout.split()
        for pid in ids:
            if not pid.isdigit():
                continue
            age = subprocess.run(
                ["/bin/ps", "-p", pid, "-o", "etime="],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            ).stdout
            if age.strip() and elapsed_seconds(age) >= minimum:
                return True
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False
    return False


def wait_for_settled_chrome(
    running, settled, wait=SETTLE_WAIT_SECONDS, sleep=time.sleep, clock=time.monotonic
):
    deadline = clock() + wait
    while True:
        if not running():
            raise InvalidLaunch("The existing Chrome process is not running")
        if settled():
            return
        if clock() >= deadline:
            raise InvalidLaunch("The existing Chrome process is still starting")
        sleep(0.5)


def verify_window_closed(window_id, observe, attempts=10, pause=0.2):
    """Poll an extension-side chrome.windows census until the exact window is gone.

    Chrome's AppleScript interface can stop answering while the browser keeps
    working, for example behind an Automation consent prompt for a parent app
    that lacks the apple-events entitlement, so it is never consulted here.
    Closure lands asynchronously, so a just-removed window is polled briefly.
    """
    if type(window_id) is not int or window_id < 0:
        raise InvalidLaunch("Invalid owned window identity")
    for attempt in range(attempts):
        ids = observe()
        if not isinstance(ids, list) or any(type(x) is not int for x in ids):
            raise InvalidLaunch("Window census was not readable")
        if window_id not in ids:
            return
        if attempt < attempts - 1:
            time.sleep(pause)
    raise InvalidLaunch("Owned window closure was not observed")


def browser_arguments(arguments):
    """Accept only the existing-profile extension launch shape, without logging it."""
    if len(arguments) != 2 or any("\n" in x or "\r" in x or "\x00" in x for x in arguments):
        raise InvalidLaunch("Expected an explicit profile and one connector URL")
    profile, connector = arguments
    if not re.fullmatch(r"--profile-directory=(?:Default|Profile [1-9][0-9]*)", profile):
        raise InvalidLaunch("Expected an existing named profile")
    try:
        parsed = urlsplit(connector)
        valid = (
            parsed.scheme == "chrome-extension"
            and parsed.netloc == "mmlmfjhmonkocbjadbfplnigmagldckm"
            and parsed.path == "/connect.html"
            and not parsed.fragment
        )
    except ValueError:
        valid = False
    if not valid:
        raise InvalidLaunch("Expected the Playwright connector URL")
    # Forward the original string byte-for-byte. Never decode or print its token.
    return ["--new-window", profile, connector]


def bridge_connector(args, socket_path):
    """Pass only the local vendor relay endpoint to the private broker."""
    parsed = urlsplit(args[-1])
    fields = parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=24)
    urls = [v for k, v in fields if k == "mcpRelayUrl"]
    if len(urls) != 1 or [v for k, v in fields if k == "protocolVersion"] != ["2"]:
        raise InvalidLaunch("Protocol-v2 relay launch required")
    endpoint = relay_rpc(socket_path, "install", url=urls[0])
    if not isinstance(endpoint, str) or not re.fullmatch(
        r"ws://127\.0\.0\.1:[1-9]\d{0,4}/extension/[0-9a-f-]{36}", endpoint
    ):
        raise InvalidLaunch("Private relay endpoint required")
    query = urlencode([(k, endpoint if k == "mcpRelayUrl" else v) for k, v in fields])
    return [*args[:-1], urlunsplit(parsed._replace(query=query))]


def main(
    arguments=None,
    environment=None,
    execute=os.execv,
    profile_root=None,
    running=chrome_is_running,
    settled=chrome_has_settled,
    settle_wait=SETTLE_WAIT_SECONDS,
):
    arguments = sys.argv[1:] if arguments is None else arguments
    environment = os.environ if environment is None else environment
    try:
        args = browser_arguments(arguments)
        directory = arguments[0].split("=", 1)[1]
        existing_signed_in_profile(
            directory, environment.get("EP_BROWSER_EXPECTED_ACCOUNT"), profile_root
        )
        binary = environment.get(
            "EP_BROWSER_EXECUTABLE", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
        path = Path(binary)
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise InvalidLaunch("Existing Chrome executable is unavailable")
        broker = environment.get("EP_BROWSER_RELAY_SOCKET")
        if broker:
            args = bridge_connector(args, broker)
        # Checked last so the gap between this check and the handoff stays minimal.
        wait_for_settled_chrome(running, settled, settle_wait)
        execute(str(path), [str(path), *args])
        return 0
    except (ValueError, OSError):
        # OSError and argv may contain the credential-bearing connector URL.
        print(
            "Chrome job window launch refused; verify the existing signed-in profile, expected account, running browser and connector",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
