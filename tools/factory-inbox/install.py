#!/usr/bin/env python3
"""Install this canonical producer on the Mac owning the Drive Desktop inbox."""

import argparse
import json
import os
from pathlib import Path
import plistlib
import shlex
import shutil
import subprocess

LABEL = "com.expertpartners.factory-inbox"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--python", default="/opt/homebrew/bin/python3")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    root = Path(config["inbox_path"]).expanduser()
    if not root.is_dir():
        raise SystemExit("Wait for the existing Drive Desktop mount to expose Factory Inbox.")
    os.umask(0o077)
    home = Path.home()
    state = Path(config["state_path"]).expanduser()
    state.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).with_name("bridge.py"), state / "bridge.py")
    shutil.copy2(Path(__file__).with_name("README.md"), state / "README.md")
    if args.config.resolve() != (state / "config.json").resolve():
        shutil.copy2(args.config, state / "config.json")
    for link in (home / ".factory/Factory Inbox", home / "HQ-AI-Workspace-M4/Factory Inbox"):
        if link.is_symlink() and link.resolve() == root.resolve():
            continue
        if link.exists() or link.is_symlink():
            raise SystemExit("Preserved an existing conflicting inbox path: " + str(link))
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(root, target_is_directory=True)
    # zsh reads the Mac's existing ~/.zshenv vault bootstrap. No new token store.
    command = "exec " + " ".join(
        map(
            shlex.quote,
            [args.python, str(state / "bridge.py"), "--config", str(state / "config.json")],
        )
    )
    plist = {
        "Label": LABEL,
        "ProgramArguments": ["/bin/zsh", "-lc", command],
        "RunAtLoad": True,
        "WatchPaths": [str(root)],
        "StartInterval": 30,
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "StandardOutPath": str(state / "worker.log"),
        "StandardErrorPath": str(state / "worker-error.log"),
    }
    target = home / "Library/LaunchAgents" / (LABEL + ".plist")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(plistlib.dumps(plist))
    domain = "gui/" + str(os.getuid())
    subprocess.run(["launchctl", "bootout", domain + "/" + LABEL], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", domain, str(target)], check=True)
    print("Installed " + str(target))


if __name__ == "__main__":
    main()
