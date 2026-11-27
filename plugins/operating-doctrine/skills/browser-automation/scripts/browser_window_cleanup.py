#!/usr/bin/env python3
"""Native Factory, Claude and Codex hook. All browser cleanup runs on the M2."""

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time


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
        report = dispatch({"action": "finish_session", "session_id": session_id, "event": event})
        # The receipt is written before the marker goes, so a session that
        # opened browser jobs always leaves either a marker or a receipt.
        write_receipt(session_id, event, report)
        marker.unlink(missing_ok=True)
        unresolved = sorted(
            x["job_id"]
            for x in (report if isinstance(report, list) else [])
            if isinstance(x, dict) and x.get("status") == "failed_no_artifacts_by_census"
        )
        generations = sorted(
            x["job_id"]
            for x in (report if isinstance(report, list) else [])
            if isinstance(x, dict) and x.get("status") == "failed_no_artifacts_by_generation"
        )
        messages = []
        if unresolved:
            # Not clean: these receipts stay failed. They only stop blocking.
            messages.append(
                "Browser jobs "
                + ", ".join(unresolved)
                + " failed, no artifacts by census. Receipts remain failed, not finished."
            )
        if generations:
            messages.append(
                "Browser jobs "
                + ", ".join(generations)
                + " failed, old browser generation gone. No browser close issued. "
                + "Receipts remain failed, not finished."
            )
        if messages:
            return {"systemMessage": " ".join(messages)}
    return {}


def receipt_dir():
    path = Path(
        os.environ.get(
            "EP_BROWSER_LIFECYCLE_RECEIPTS", "~/.cache/expert-partners/browser-lifecycle-receipts"
        )
    ).expanduser()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def write_receipt(session_id, event, report):
    rows = [x for x in (report if isinstance(report, list) else []) if isinstance(x, dict)]
    receipt = {
        "session_id": session_id,
        "event": event,
        "at": time.time(),
        "queued": isinstance(report, dict) and bool(report.get("queued")),
        "closed": sorted(x["job_id"] for x in rows if x.get("status") == "finished"),
        "other": sorted((x["job_id"], x["status"]) for x in rows if x.get("status") != "finished"),
    }
    path = receipt_dir() / (session_id + ".json")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt))
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    return receipt


def cleanup_line(session_id):
    """Browser part of the session-wrap Cleanup done line, from evidence only."""
    if (marker_dir() / session_id).exists():
        return "browser cleanup NOT done, this session still owns browser jobs"
    try:
        receipt = json.loads((receipt_dir() / (session_id + ".json")).read_text())
    except (OSError, ValueError):
        return "browser windows closed: none opened"
    if receipt.get("queued"):
        return "browser windows: close queued at " + receipt["event"]
    text = "browser windows closed: " + str(len(receipt.get("closed", [])))
    if receipt.get("other"):
        text += ", held " + ", ".join(job + " " + status for job, status in receipt["other"])
    return text


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
    try:
        return json.loads(result.stdout)
    except ValueError:
        return None


def main():
    if sys.argv[1:2] == ["--cleanup-line"]:
        session_id = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("FACTORY_SESSION_ID", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", session_id):
            print("session id required", file=sys.stderr)
            return 2
        print(cleanup_line(session_id))
        return 0
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
