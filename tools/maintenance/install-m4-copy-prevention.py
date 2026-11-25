#!/usr/bin/env python3
"""Install the M4 copy prevention on this Mac. Idempotent; safe to rerun.

1. Writes ~/Library/LaunchAgents/com.expertpartners.m4-scratch-janitor.plist, which runs the
   janitor from the synced marketplace clone every 6 hours at background priority, and loads it.
2. Adds tools/hooks/ai-copy-guard.py as a PreToolUse hook for Factory (~/.factory/hooks.json)
   and Codex (~/.codex/hooks.json). Claude Code already runs it through
   pre-tool-use-enforcement.sh from the same marketplace clone.

Both point at the marketplace clone that plugin sync keeps current, so there is no hand copy.
"""

import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
SRC = Path(
    os.environ.get("EP_SKILLS_RUNTIME", HOME / ".claude/plugins/marketplaces/expert-partners")
)
JANITOR = SRC / "tools/maintenance/m4-scratch-janitor.py"
GUARD = SRC / "tools/hooks/ai-copy-guard.py"
LABEL = "com.expertpartners.m4-scratch-janitor"
PLIST = HOME / "Library/LaunchAgents" / f"{LABEL}.plist"
GUARD_CMD = f"/usr/bin/python3 {GUARD}"


def install_launchd():
    logs = HOME / "Library/Logs/m4-scratch-janitor"
    logs.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": LABEL,
        "ProgramArguments": ["/usr/bin/python3", str(JANITOR)],
        "StartInterval": 21600,
        "RunAtLoad": False,
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "LowPriorityBackgroundIO": True,
        "Nice": 19,
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
            "HOME": str(HOME),
        },
        "StandardOutPath": str(logs / "stdout.log"),
        "StandardErrorPath": str(logs / "stderr.log"),
    }
    new = plistlib.dumps(plist)
    if PLIST.exists() and PLIST.read_bytes() == new:
        print("launchd job already current")
    else:
        PLIST.write_bytes(new)
        uid = os.getuid()
        subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
        subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(PLIST)], check=True)
        print(f"loaded {PLIST}")


def add_hook(path, nested):
    if not path.exists():
        print(f"skip {path}: not present")
        return
    data = json.loads(path.read_text())
    root = data.setdefault("hooks", {}) if nested else data
    pre = root.setdefault("PreToolUse", [])
    if any(h.get("command") == GUARD_CMD for m in pre for h in m.get("hooks", [])):
        print(f"{path}: guard already present")
        return
    pre.insert(
        0, {"matcher": "", "hooks": [{"type": "command", "command": GUARD_CMD, "timeout": 10}]}
    )
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)
    print(f"{path}: guard added")


def main():
    for p in (JANITOR, GUARD):
        if not p.exists():
            sys.exit(f"missing {p}; run plugin sync first")
    install_launchd()
    add_hook(HOME / ".factory/hooks.json", nested=False)
    add_hook(HOME / ".codex/hooks.json", nested=True)


if __name__ == "__main__":
    main()
