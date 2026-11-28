#!/usr/bin/env python3
"""Keep existing macOS Chrome profiles usable without retaining their windows.

Credentials are read from 1Password only when the login Keychain is locked.
No cookie values, passwords, tokens, or vendor response bodies are logged.
The default operation opens no browser. This does not extend website sessions.
"""

import argparse
import ctypes
import ctypes.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from urllib.parse import urlsplit


class StateError(Exception):
    pass


class LoginKeychain:
    def __init__(self, path):
        library = ctypes.util.find_library("Security")
        if not library:
            raise StateError("macos_security_unavailable")
        self.api = ctypes.CDLL(library)
        self.api.SecKeychainOpen.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
        self.api.SecKeychainGetStatus.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        self.api.SecKeychainUnlock.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.c_bool,
        ]
        self.handle = ctypes.c_void_p()
        if self.api.SecKeychainOpen(os.fsencode(path), ctypes.byref(self.handle)):
            raise StateError("login_keychain_unavailable")

    def unlocked(self):
        status = ctypes.c_uint32()
        if self.api.SecKeychainGetStatus(self.handle, ctypes.byref(status)):
            raise StateError("keychain_status_unavailable")
        return bool(status.value & 1)

    def unlock(self, password):
        # Security.framework keeps the password out of process arguments and files.
        value = password.encode()
        if self.api.SecKeychainUnlock(self.handle, len(value), value, True):
            raise StateError("keychain_unlock_failed")
        if not self.unlocked():
            raise StateError("keychain_unlock_not_observed")


def owner_only(path):
    path = Path(path).expanduser()
    if path.is_symlink():
        raise StateError("private_file_is_symlink")
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
        raise StateError("private_file_permissions")
    return path


def credential(config):
    token = owner_only(config["service_account_token_file"]).read_text().strip()
    token = token.removeprefix("OP_SERVICE_ACCOUNT_TOKEN=")
    if not token:
        raise StateError("service_account_unavailable")
    environment = os.environ.copy()
    environment["OP_SERVICE_ACCOUNT_TOKEN"] = token
    result = subprocess.run(
        [
            config["op"],
            "item",
            "get",
            config["credential_item"],
            "--vault",
            config["credential_vault"],
            "--format=json",
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=25,
    )
    if result.returncode:
        raise StateError("credential_unavailable")
    item = json.loads(result.stdout)
    password = next(
        (field.get("value") for field in item.get("fields", []) if field.get("id") == "password"),
        None,
    )
    if not isinstance(password, str) or not password:
        raise StateError("credential_password_missing")
    return password


def ensure_keychain(config, keychain=None, get_password=credential):
    keychain = keychain or LoginKeychain(Path(config["keychain"]).expanduser())
    was_locked = not keychain.unlocked()
    if was_locked:
        keychain.unlock(get_password(config))
    return {"keychain_unlocked": True, "recovered_locked_keychain": was_locked}


def profile_arguments(config, profile, url=None):
    expected = config["profiles"].get(profile)
    if not expected or Path(profile).name != profile:
        raise StateError("profile_not_configured")
    root = Path(config["chrome_data"]).expanduser()
    preferences = json.loads((root / profile / "Preferences").read_text())
    local = json.loads((root / "Local State").read_text())
    actual = local["profile"]["info_cache"][profile].get("user_name", "")
    accounts = {a.get("email", "").casefold() for a in preferences.get("account_info", [])}
    if (
        actual.casefold() != expected.casefold()
        or expected.casefold() not in accounts
        or preferences.get("signin", {}).get("allowed") is False
    ):
        raise StateError("existing_profile_identity_mismatch")
    arguments = [
        "/usr/bin/open",
        "-n",
        "-a",
        "/Applications/Google Chrome.app",
        "--args",
        "--profile-directory=" + profile,
    ]
    if url:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise StateError("https_url_required")
        arguments.append(url)
    return arguments


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--open", dest="profile")
    parser.add_argument("--url")
    args = parser.parse_args(argv)
    try:
        config = json.loads(owner_only(args.config).read_text())
        if args.url and not args.profile:
            raise StateError("profile_required_for_url")
        # Validate identity before consulting a credential or opening a window.
        arguments = profile_arguments(config, args.profile, args.url) if args.profile else None
        result = ensure_keychain(config)
        if arguments:
            subprocess.run(arguments, check=True, capture_output=True, timeout=20)
        result["browser_open_requested"] = bool(arguments)
        print(json.dumps(result))
        return 0
    except StateError as error:
        print(json.dumps({"error": str(error)}))
    except Exception:
        # In particular, never echo subprocess args, stderr, or 1Password JSON.
        print(json.dumps({"error": "profile_state_operation_failed"}))
    return 1


if __name__ == "__main__":
    sys.exit(main())
