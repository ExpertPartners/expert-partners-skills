#!/usr/bin/env python3
"""Stable browser-route adapter for the user-installed Claude policy.

Resolve the installation receipt, not a cache version or marketplace checkout.
Missing, ambiguous or disabled installations fail closed. Existing route facades
can load this file without changing their runtime or protected launcher.
"""

import importlib.util
import json
from pathlib import Path
import threading

KEY = "operating-doctrine@expert-partners"
_lock = threading.RLock()
_loaded = None
_path = None


def installed_hook(home=None):
    home = Path.home() if home is None else Path(home)
    plugins = home / ".claude/plugins"
    receipt = json.loads((plugins / "installed_plugins.json").read_text())
    settings = json.loads((home / ".claude/settings.json").read_text())
    if settings.get("enabledPlugins", {}).get(KEY) is not True:
        raise RuntimeError("installed_headless_policy_disabled")
    entries = receipt.get("plugins", {}).get(KEY, [])
    entries = [e for e in entries if isinstance(e, dict) and e.get("scope") == "user"]
    if len(entries) != 1:
        raise RuntimeError("installed_headless_policy_ambiguous")
    entry = entries[0]
    root = Path(entry["installPath"])
    expected = plugins / "cache/expert-partners/operating-doctrine" / entry["version"]
    if not root.is_absolute() or root.resolve() != expected.resolve():
        raise RuntimeError("installed_headless_policy_path_invalid")
    hook = root / "hooks/headless_route_check.py"
    if not hook.is_file() or hook.resolve() == Path(__file__).resolve():
        raise RuntimeError("installed_headless_policy_missing")
    return hook


def policy():
    global _loaded, _path
    with _lock:
        path = installed_hook()
        if _loaded is None or path != _path:
            spec = importlib.util.spec_from_file_location("installed_browser_headless_policy", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not callable(getattr(module, "decide", None)):
                raise RuntimeError("installed_headless_policy_incompatible")
            _loaded, _path = module, path
        return _loaded


def decide(payload):
    return policy().decide(payload)


def refresh_due():
    return policy().refresh_due()


def start_background_refresh():
    return policy().start_background_refresh()


# Prove the installed policy is usable when the actual launcher imports us.
policy()
