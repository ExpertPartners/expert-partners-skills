#!/usr/bin/env python3
"""Install or restore the shared entry point without restarting any live client.

The existing protected bootstrap is retained byte-for-byte in an owner-only
backup. Future invocations use the facade; existing MCP processes keep running.
The skill's normal producer must build and verify the runtime before this step.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import socket
import stat
import sys
import tempfile

from chrome_job_window import existing_signed_in_profile, chrome_is_running


class InstallRefusal(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verified_runtime(root):
    root = Path(root).resolve()
    manifest = {}
    for line in (root / "checksums.sha256").read_text().splitlines():
        sha, name = line.split(None, 1)
        manifest[name.removeprefix("./")] = sha
    for name in ("browser_jobs.py", "chrome_job_window.py", "job_transport.py", "owned_pages.js"):
        relative = "scripts/" + name
        path = root / relative
        if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != manifest.get(relative):
            raise InstallRefusal("runtime_artifact_mismatch")
    return root


def atomic(path, data, mode):
    fd, temp = tempfile.mkstemp(prefix=".browser-route-", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def install(settings, runtime, destination, interpreter, identity_check=existing_signed_in_profile,
            running=chrome_is_running):
    runtime = verified_runtime(runtime)
    destination = Path(destination).absolute()
    interpreter = Path(interpreter)
    entry = Path(settings["launcher"])
    if settings["host"] != socket.gethostname() or not entry.is_absolute():
        raise InstallRefusal("assigned_host_required")
    identity_check(settings["profile"], settings["expected_account"])
    if not running():
        raise InstallRefusal("existing_browser_required")
    if not interpreter.is_absolute() or not interpreter.is_file() or not os.access(interpreter, os.X_OK):
        raise InstallRefusal("python_interpreter_required")
    if entry.is_symlink() or destination.is_symlink() or entry.stat().st_uid != os.geteuid():
        raise InstallRefusal("owned_regular_entry_required")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.parent.is_symlink() or destination.parent.stat().st_uid != os.geteuid():
        raise InstallRefusal("private_configuration_directory_required")
    os.chmod(destination.parent, 0o700)
    lock_path = Path(settings["bootstrap_lock"])
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        expected = settings["launcher_sha256"]
        backup = destination.parent / ("protected-bootstrap-" + expected[:16] + ".sh")
        config = {**settings, "launcher": str(backup)}
        config_bytes = (json.dumps(config, sort_keys=True, indent=2) + "\n").encode()
        command = [str(interpreter), str(runtime / "scripts/browser_jobs.py"), "--config", str(destination)]
        wrapper = ("#!/bin/sh\n[ \"$#\" -eq 0 ] || exit 2\nexec " + " ".join(shlex.quote(x) for x in command) + "\n").encode()
        old = entry.read_bytes()
        if old == wrapper:
            if backup.is_symlink() or destination.read_bytes() != config_bytes or digest(backup.read_bytes()) != expected:
                raise InstallRefusal("installed_route_drift")
            return {"changed": False, "entry": str(entry), "backup": str(backup)}
        if digest(old) != expected:
            raise InstallRefusal("protected_bootstrap_changed")
        if destination.exists() and destination.read_bytes() != config_bytes:
            raise InstallRefusal("configuration_conflict")
        if backup.exists():
            if backup.is_symlink() or digest(backup.read_bytes()) != expected:
                raise InstallRefusal("backup_conflict")
        else:
            atomic(backup, old, 0o700)
        original_mode = stat.S_IMODE(entry.stat().st_mode)
        rollback = {"entry": str(entry), "backup": str(backup), "original_sha256": expected,
                    "original_mode": original_mode, "installed_sha256": digest(wrapper)}
        atomic(destination, config_bytes, 0o600)
        atomic(destination.with_suffix(".rollback.json"), (json.dumps(rollback, sort_keys=True) + "\n").encode(), 0o600)
        # This is the sole activation write, after the private bootstrap/config
        # are ready. It changes future starts, never any running transport.
        atomic(entry, wrapper, 0o700)
        return {"changed": True, "entry": str(entry), "backup": str(backup)}
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def rollback(destination):
    path = Path(destination)
    config = json.loads(path.read_text())
    fd = os.open(config["bootstrap_lock"], os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        record = json.loads(path.with_suffix(".rollback.json").read_text())
        entry, backup = Path(record["entry"]), Path(record["backup"])
        if entry.is_symlink() or backup.is_symlink() or entry.stat().st_uid != os.geteuid():
            raise InstallRefusal("owned_regular_entry_required")
        if digest(entry.read_bytes()) != record["installed_sha256"] or digest(backup.read_bytes()) != record["original_sha256"]:
            raise InstallRefusal("rollback_drift")
        atomic(entry, backup.read_bytes(), record["original_mode"])
        return {"restored": True, "entry": str(entry)}
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()
    try:
        if args.rollback:
            report = rollback(args.config)
        else:
            if not all((args.settings, args.runtime, args.python)):
                raise InstallRefusal("installation_arguments_required")
            report = install(json.loads(args.settings.read_text()), args.runtime, args.config, args.python)
        print(json.dumps(report))
        return 0
    except Exception:
        # Never echo protected source, configuration contents or exception text.
        print("Browser route installation refused; verify the assigned host, signed-in profile, pinned source, producer artifact and private backup", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
