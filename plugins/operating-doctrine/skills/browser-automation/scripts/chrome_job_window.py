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
from urllib.parse import urlsplit


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


def verify_window_closed(window_id, attempts=10, pause=0.2):
    """Chrome's scripting window ID equals its extension window ID on macOS.

    Closure lands asynchronously, so a just-removed window is polled briefly.
    """
    if type(window_id) is not int or window_id < 0:
        raise InvalidLaunch("Invalid owned window identity")
    for attempt in range(attempts):
        observed = subprocess.run(
            [
                "/usr/bin/osascript",
                "-e",
                'tell application "Google Chrome" to get id of every window',
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        ids = {int(x.strip()) for x in observed.stdout.strip().split(",") if x.strip()}
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


def main(
    arguments=None, environment=None, execute=os.execv, profile_root=None, running=chrome_is_running
):
    arguments = sys.argv[1:] if arguments is None else arguments
    environment = os.environ if environment is None else environment
    try:
        args = browser_arguments(arguments)
        directory = arguments[0].split("=", 1)[1]
        existing_signed_in_profile(
            directory, environment.get("EP_BROWSER_EXPECTED_ACCOUNT"), profile_root
        )
        if not running():
            raise InvalidLaunch("The existing Chrome process is not running")
        binary = environment.get(
            "EP_BROWSER_EXECUTABLE", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
        path = Path(binary)
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise InvalidLaunch("Existing Chrome executable is unavailable")
        execute(str(path), [str(path), *args])
        return 0
    except (InvalidLaunch, OSError):
        # OSError and argv may contain the credential-bearing connector URL.
        print(
            "Chrome job window launch refused; verify the existing signed-in profile, expected account, running browser and connector",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
