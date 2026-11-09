#!/usr/bin/env python3
"""Install stable user hooks on either Mac, and the M2-only nightly sweep."""

import argparse
import json
import os
from pathlib import Path
import plistlib
import shlex
import subprocess
import sys

from browser_lifecycle import atomic_json
from install_job_route import atomic, verified_runtime


def merge_hooks(path, command, surface):
    document = json.loads(path.read_text()) if path.exists() else {}
    if surface == "factory":
        hooks = document
        # Factory stops reading settings.json hooks once hooks.json exists.
        settings = path.with_name("settings.json")
        if not path.exists() and settings.exists():
            hooks.update(json.loads(settings.read_text()).get("hooks", {}))
    else:
        hooks = document.setdefault("hooks", {})
    for event in ("PreToolUse", "PostToolUse", "Stop", "SessionEnd"):
        groups = hooks.setdefault(event, [])
        for group in groups:
            group["hooks"] = [
                hook
                for hook in group.get("hooks", [])
                if "ep-browser-window-cleanup" not in hook.get("command", "")
            ]
        groups[:] = [group for group in groups if group.get("hooks")]
        group = {
            "hooks": [
                {
                    "type": "command",
                    "command": command,
                    "timeout": 3 if surface == "codex" and event == "SessionEnd" else 160,
                }
            ]
        }
        if event == "PreToolUse":
            group["matcher"] = "browser_"
        elif event == "PostToolUse":
            group["matcher"] = "browser_job_start$"
        groups.append(group)
    atomic_json(path, document)


def install(
    runtime,
    interpreter,
    home,
    ssh_target=None,
    remote_runtime=None,
    remote_python=None,
    route_config=None,
    load=False,
):
    runtime = verified_runtime(runtime)
    home = Path(home)
    interpreter = str(Path(interpreter).resolve())
    if not Path(interpreter).is_file() or not os.access(interpreter, os.X_OK):
        raise ValueError("python_required")
    config_dir = home / ".config/expert-partners/browser-jobs"
    config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    route_config = Path(route_config or config_dir / "route.json")
    host_runtime = Path(remote_runtime or runtime)
    command = [
        str(remote_python or interpreter),
        str(host_runtime / "scripts/browser_lifecycle.py"),
        "--config",
        str(route_config),
        "--request",
    ]
    settings = {"command": command}
    if ssh_target:
        settings["ssh_target"] = ssh_target
    atomic_json(config_dir / "lifecycle.json", settings)
    executable = home / ".local/bin/ep-browser-window-cleanup"
    executable.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # This stable path survives old pinned marketplace plugin versions.
    atomic(
        executable,
        (
            "#!/bin/sh\nexec "
            + shlex.join([interpreter, str(runtime / "scripts/browser_window_cleanup.py")])
            + "\n"
        ).encode(),
        0o700,
    )
    for surface, path in (
        ("factory", home / ".factory/hooks.json"),
        ("claude", home / ".claude/settings.json"),
        ("codex", home / ".codex/hooks.json"),
    ):
        merge_hooks(path, shlex.quote(str(executable)), surface)
    report = {
        "user_hooks": ["factory", "claude", "codex"],
        "entry": str(executable),
        "browser_host": not bool(ssh_target),
    }
    if not ssh_target:
        config = json.loads(route_config.read_text())
        log = Path(config["state_dir"]) / "nightly-cleanup.log"
        plist = home / "Library/LaunchAgents/com.expertpartners.browser-window-sweep.plist"
        plist.parent.mkdir(parents=True, exist_ok=True)
        atomic(
            plist,
            plistlib.dumps(
                {
                    "Label": "com.expertpartners.browser-window-sweep",
                    "ProgramArguments": [
                        interpreter,
                        str(runtime / "scripts/browser_lifecycle.py"),
                        "--config",
                        str(route_config),
                        "--sweep",
                    ],
                    "StartCalendarInterval": {"Hour": 2, "Minute": 35},
                    "StandardOutPath": str(log),
                    "StandardErrorPath": str(log),
                    "ProcessType": "Background",
                }
            ),
            0o600,
        )
        report["launch_agent"] = str(plist)
        if load:
            domain = "gui/" + str(os.getuid())
            subprocess.run(
                ["/bin/launchctl", "bootout", domain, str(plist)], capture_output=True, check=False
            )
            subprocess.run(
                ["/bin/launchctl", "bootstrap", domain, str(plist)], capture_output=True, check=True
            )
            report["loaded"] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--ssh-target")
    parser.add_argument("--remote-runtime", type=Path)
    parser.add_argument("--remote-python", type=Path)
    parser.add_argument("--route-config", type=Path)
    parser.add_argument("--load", action="store_true")
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                install(
                    args.runtime,
                    args.python,
                    args.home,
                    args.ssh_target,
                    args.remote_runtime,
                    args.remote_python,
                    args.route_config,
                    args.load,
                )
            )
        )
        return 0
    except Exception:
        print(
            "Browser lifecycle installation incomplete. Check produced runtime, route configuration and user hook files.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
