#!/usr/bin/env python3
"""Install the stable policy adapter and migrate route configs, retaining backups."""

import argparse
import datetime
import importlib.util
import json
from pathlib import Path
import os
import tempfile


def atomic(path, data):
    fd, name = tempfile.mkstemp(prefix=".headless-policy-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def install(configs, destination):
    source = Path(__file__).with_name("installed_headless_policy.py")
    spec = importlib.util.spec_from_file_location("validate_installed_policy", source)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    destination = Path(destination).absolute()
    paths = [Path(p).absolute() for p in configs]
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate_route_config")
    prepared = []
    for path in paths:
        if path.is_symlink() or path.stat().st_uid != os.geteuid():
            raise ValueError("owned_regular_route_required")
        old = path.read_bytes()
        config = json.loads(old)
        config["headless_hook"] = str(destination)
        prepared.append((path, old, (json.dumps(config, sort_keys=True) + "\n").encode()))
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.is_symlink() or destination.parent.is_symlink():
        raise ValueError("regular_policy_destination_required")
    if destination.parent.stat().st_uid != os.geteuid():
        raise ValueError("owned_policy_directory_required")
    os.chmod(destination.parent, 0o700)
    atomic(destination, source.read_bytes())
    result = []
    for path, old, new in prepared:
        if old == new:
            result.append({"config": str(path), "changed": False})
            continue
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = path.with_name(path.name + ".bak-" + stamp + "-before-stable-policy")
        with backup.open("xb") as stream:
            os.chmod(backup, 0o600)
            stream.write(old)
        if path.read_bytes() != old:
            raise ValueError("route_changed_during_migration")
        atomic(path, new)
        result.append({"config": str(path), "changed": True, "backup": str(backup)})
    return {
        "adapter": str(destination),
        "installed_hook": str(adapter.installed_hook()),
        "routes": result,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, action="append", required=True)
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path.home() / ".config/expert-partners/browser-policy/headless_route_check.py",
    )
    args = parser.parse_args()
    print(json.dumps(install(args.config, args.destination), sort_keys=True))


if __name__ == "__main__":
    main()
