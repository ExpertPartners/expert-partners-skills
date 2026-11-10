#!/usr/bin/env python3
"""Install the flight controller on this Mac, or the off-host observer on the other one.

Copies the canonical code out of the repository into a runtime directory, renders the
launchd template and bootstraps it in the current GUI session. It writes no credential:
the controller resolves the Factory key from the login keychain and alert keys from
1Password at run time.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROLES = {
    "controller": {
        "label": "com.expertpartners.flight-controller",
        "template": "deploy/com.expertpartners.flight-controller.plist",
        "code": ["controller.py"],
        "interval": 900,
    },
    "observer": {
        "label": "com.expertpartners.flight-observer",
        "template": "deploy/com.expertpartners.flight-observer.plist",
        "code": ["observer.py"],
        "interval": 900,
    },
}


def run(command, check=True):
    result = subprocess.run(command, capture_output=True, timeout=120)
    if check and result.returncode != 0:
        raise SystemExit(
            f"{' '.join(command)} exited {result.returncode}: {result.stderr.decode()[:400]}"
        )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=sorted(ROLES))
    parser.add_argument("--config", required=True, help="Absolute path to the private config file")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--code-dir", default=str(Path.home() / ".factory/flight-controller"))
    parser.add_argument("--interval", type=int)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args(argv)
    role = ROLES[args.role]
    label = role["label"]
    plist = Path.home() / "Library/LaunchAgents" / (label + ".plist")
    domain = f"gui/{os.getuid()}"
    if args.uninstall:
        run(["/bin/launchctl", "bootout", f"{domain}/{label}"], check=False)
        plist.unlink(missing_ok=True)
        print(json.dumps({"uninstalled": label}))
        return 0
    if not Path(args.config).is_absolute() or not Path(args.config).exists():
        raise SystemExit("--config must be an existing absolute path")
    code_dir = Path(args.code_dir).expanduser()
    code_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name in role["code"]:
        shutil.copy2(HERE / name, code_dir / name)
        os.chmod(code_dir / name, 0o700)
    log = str(Path.home() / "Library/Logs" / (label.rsplit(".", 1)[-1] + ".log"))
    rendered = (
        (HERE / role["template"])
        .read_text()
        .replace("__PYTHON__", args.python)
        .replace("__CODE__", str(code_dir))
        .replace("__CONFIG__", args.config)
        .replace("__INTERVAL__", str(args.interval or role["interval"]))
        .replace("__LOG__", log)
    )
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(rendered)
    os.chmod(plist, 0o644)
    run(["/bin/launchctl", "bootout", f"{domain}/{label}"], check=False)
    run(["/bin/launchctl", "bootstrap", domain, str(plist)])
    run(["/bin/launchctl", "enable", f"{domain}/{label}"], check=False)
    print(
        json.dumps(
            {
                "installed": label,
                "plist": str(plist),
                "code": str(code_dir),
                "config": args.config,
                "log": log,
                "interval_seconds": args.interval or role["interval"],
                "stop": f"launchctl bootout {domain}/{label}",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
