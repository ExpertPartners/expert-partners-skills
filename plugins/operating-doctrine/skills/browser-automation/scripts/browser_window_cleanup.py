#!/usr/bin/env python3
"""Native Factory, Claude and Codex hook. All browser cleanup runs on the M2."""

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


def job_ids(value):
    if isinstance(value, str):
        try:
            yield from job_ids(json.loads(value))
        except ValueError:
            pass
    elif isinstance(value, list):
        for item in value:
            yield from job_ids(item)
    elif isinstance(value, dict):
        job_id = value.get("job_id")
        if isinstance(job_id, str) and re.fullmatch(r"[0-9a-f]{32}", job_id):
            yield job_id
        for key in ("content", "text", "result", "tool_response"):
            if key in value:
                yield from job_ids(value[key])


def handle(payload, dispatch):
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", session_id):
        return {}
    event = payload.get("hook_event_name")
    name = payload.get("tool_name", "")
    args = payload.get("tool_input") or {}
    marker = marker_dir() / session_id
    if event == "PreToolUse" and name.endswith("browser_job_start"):
        marker.touch(mode=0o600)
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": {**args, "owner_session_id": session_id},
            }
        }
    if event in ("PreToolUse", "PostToolUse") and "browser_" in name:
        ids = set(job_ids(args))
        if event == "PostToolUse" and name.endswith("browser_job_start"):
            ids.update(job_ids(payload.get("tool_response")))
        if ids and (not marker.exists() or name.endswith("browser_job_start")):
            bound = False
            for job_id in ids:
                # A failed bind must never block the browser call itself.
                try:
                    dispatch({"action": "bind", "session_id": session_id, "job_id": job_id})
                    bound = True
                except Exception:
                    pass
            if bound:
                marker.touch(mode=0o600)
    elif event in ("Stop", "SessionEnd", "Interrupt") and marker.exists():
        # Sessions that never started a browser job never reach the M2, so an
        # unreachable browser host cannot hold up ordinary turns.
        dispatch({"action": "finish_session", "session_id": session_id, "event": event})
        marker.unlink(missing_ok=True)
    return {}


def marker_dir():
    path = Path(
        os.environ.get(
            "EP_BROWSER_LIFECYCLE_SESSIONS", "~/.cache/expert-partners/browser-lifecycle-sessions"
        )
    ).expanduser()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def dispatch(request):
    path = Path(
        os.environ.get(
            "EP_BROWSER_LIFECYCLE_CONFIG", "~/.config/expert-partners/browser-jobs/lifecycle.json"
        )
    ).expanduser()
    settings = json.loads(path.read_text())
    command = settings["command"]
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ValueError("invalid_lifecycle_command")
    # The M4 config uses ssh with a single quoted remote command. No browser
    # executable runs on the caller and no hook payload is put into shell code.
    if settings.get("ssh_target"):
        command = [
            "/usr/bin/ssh",
            "-T",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            settings["ssh_target"],
            shlex.join(command),
        ]
    result = subprocess.run(
        command, input=json.dumps(request), text=True, capture_output=True, timeout=150
    )
    if result.returncode:
        raise RuntimeError("browser_cleanup_incomplete")


def main():
    payload = {}
    try:
        payload = json.loads(sys.stdin.read(1048576))
        print(json.dumps(handle(payload, dispatch)))
        return 0
    except Exception:
        # Do not echo tool input, command argv or remote output.
        message = "Owned browser window cleanup incomplete. Preserve unknown and active jobs; reconcile this session's exact receipts before reporting clean."
        if payload.get("hook_event_name") == "Stop" and not payload.get("stop_hook_active"):
            print(json.dumps({"decision": "block", "reason": message}))
        elif payload.get("hook_event_name") == "Stop":
            # A second block would loop the turn; the nightly sweep retries.
            print(json.dumps({"systemMessage": message}))
            return 0
        else:
            print(message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
