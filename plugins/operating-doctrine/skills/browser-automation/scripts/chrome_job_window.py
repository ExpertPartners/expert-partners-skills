#!/usr/bin/env python3
"""Open one extension connection in a new window of its existing Chrome profile.

Use this packaged executable as Playwright MCP's --executable-path on the browser host.
The existing launcher still resolves its protected profile-specific credential.
This wrapper does not implement per-job transport allocation or recovery.
"""
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit


class InvalidLaunch(ValueError):
    pass


def browser_arguments(arguments):
    """Accept only the existing-profile extension launch shape, without logging it."""
    if len(arguments) != 2 or any("\n" in x or "\r" in x or "\x00" in x for x in arguments):
        raise InvalidLaunch("Expected an explicit profile and one connector URL")
    profile, connector = arguments
    if not re.fullmatch(r"--profile-directory=(?:Default|Profile [1-9][0-9]*)", profile):
        raise InvalidLaunch("Expected an existing named profile")
    try:
        parsed = urlsplit(connector)
        valid = (parsed.scheme == "chrome-extension"
                 and parsed.netloc == "mmlmfjhmonkocbjadbfplnigmagldckm"
                 and parsed.path == "/connect.html"
                 and not parsed.fragment)
    except ValueError:
        valid = False
    if not valid:
        raise InvalidLaunch("Expected the Playwright connector URL")
    # Forward the original string byte-for-byte. Never decode or print its token.
    return ["--new-window", profile, connector]


def main(arguments=None, environment=None, execute=os.execv):
    arguments = sys.argv[1:] if arguments is None else arguments
    environment = os.environ if environment is None else environment
    try:
        args = browser_arguments(arguments)
        binary = environment.get("EP_BROWSER_EXECUTABLE", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        path = Path(binary)
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise InvalidLaunch("Existing Chrome executable is unavailable")
        execute(str(path), [str(path), *args])
        return 0
    except (InvalidLaunch, OSError):
        # OSError and argv may contain the credential-bearing connector URL.
        print("Chrome job window launch refused; check its configured profile, connector and executable", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
