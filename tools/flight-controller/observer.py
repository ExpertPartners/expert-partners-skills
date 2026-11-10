#!/usr/bin/env python3
"""Off-host heartbeat observer for the Ember M2 flight controller.

A watchdog on the M2 cannot report a dead M2, so this runs on the other registered Mac
and reads the controller's world-readable heartbeat over the existing Factory Remote
Control SSH route. No new host, credential store, port or subscription is introduced.
It alerts through the same existing notification channel the controller uses.

It is deliberately dumb: read, compare timestamps, alert, remember. It never nudges a
session, never starts work and never answers a question.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

VERSION = "1.0.0"
SEND_URL = "https://api.sendblue.co/api/send-message"
USER_AGENT = "ep-flight-observer/" + VERSION


class ObserverError(Exception):
    """Safe to record. No credential or raw response text is kept."""


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, ValueError):
        return default


def atomic_write(path, text, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode), "w") as out:
        out.write(text)
        out.flush()
        os.fsync(out.fileno())
    temporary.replace(path)


def read_heartbeat(config, runner=None):
    """Existing transport only: droid computer ssh into the registered Mac, cat one file."""
    runner = runner or subprocess.run
    command = list(config["read_command"])
    try:
        result = runner(command, capture_output=True, timeout=config["read_timeout_seconds"])
    except (OSError, subprocess.SubprocessError):
        raise ObserverError("heartbeat read transport failed") from None
    if result.returncode != 0:
        raise ObserverError("heartbeat read exited " + str(result.returncode))
    payload = result.stdout.decode(errors="replace")
    start = payload.find("{")
    if start < 0:
        raise ObserverError("heartbeat read returned no JSON")
    try:
        return json.loads(payload[start:])
    except ValueError:
        raise ObserverError("heartbeat JSON unreadable") from None


def op_item_fields(op, item, vault):
    try:
        result = subprocess.run(
            [op, "item", "get", item, "--vault", vault, "--format", "json", "--reveal"],
            capture_output=True,
            timeout=40,
            check=True,
            stdin=subprocess.DEVNULL,
        )
        fields = json.loads(result.stdout.decode())["fields"]
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        raise ObserverError("1Password read failed; no credential output recorded.") from None
    return {(field.get("label") or ""): field.get("value") for field in fields}


def send_alert(config, text, opener=None):
    settings = config["alerts"]
    fields = op_item_fields(settings["op"], settings["item"], settings["vault"])
    request = urllib.request.Request(
        SEND_URL,
        data=json.dumps(
            {
                "number": settings["recipient"],
                "from_number": fields.get("phone"),
                "content": text[:900],
            }
        ).encode(),
        method="POST",
        headers={
            "sb-api-key-id": fields["api-key-id"],
            "sb-api-secret-key": fields["api-secret-key"],
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with (opener or urllib.request.urlopen)(request, timeout=30) as response:
            answer = json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as error:
        raise ObserverError(f"Alert refused (HTTP {error.code}); content withheld.") from None
    except (urllib.error.URLError, OSError, ValueError):
        raise ObserverError("Alert outcome unknown; content withheld.") from None
    return {"handle": answer.get("message_handle"), "status": answer.get("status")}


def evaluate(heartbeat, error, state, now_ms, config):
    """A deliberate operator stop is not an outage, and neither is one slow read."""
    tolerance = config["stale_minutes"] * 60000
    if error:
        strikes = int(state.get("strikes", 0)) + 1
        verdict = {"level": "unreachable", "detail": error, "strikes": strikes}
        return verdict, strikes >= config["strikes_before_alert"]
    if heartbeat.get("stopped"):
        return {"level": "stopped", "detail": "operator stop switch is on", "strikes": 0}, False
    age = now_ms - int(heartbeat.get("last_tick_at") or 0)
    if age > tolerance:
        strikes = int(state.get("strikes", 0)) + 1
        return (
            {
                "level": "stale",
                "detail": f"last check {round(age / 60000.0, 1)} minutes ago",
                "strikes": strikes,
            },
            strikes >= config["strikes_before_alert"],
        )
    return {"level": "ok", "detail": f"tick {heartbeat.get('tick_seq')}", "strikes": 0}, False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="~/.config/flight-observer/config.json")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--test-alert", action="store_true")
    args = parser.parse_args(argv)
    config = {
        "stale_minutes": 40,
        "strikes_before_alert": 2,
        "alert_cooldown_minutes": 180,
        "read_timeout_seconds": 60,
        **(load_json(Path(args.config).expanduser(), None) or {}),
    }
    for required in ("read_command", "state_dir", "alerts"):
        if not config.get(required):
            raise ObserverError("Config must set " + required)
    state_dir = Path(config["state_dir"]).expanduser()
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    state_path = state_dir / "state.json"
    state = load_json(state_path, {"strikes": 0, "alerts": {}})
    if args.status:
        print(json.dumps(state, indent=2, sort_keys=True))
        return 0
    if args.test_alert:
        print(json.dumps(send_alert(config, "Flight observer test alert from the other Mac.")))
        return 0
    now = int(time.time() * 1000)
    heartbeat, error = {}, None
    try:
        heartbeat = read_heartbeat(config)
    except ObserverError as problem:
        error = str(problem)
    verdict, due = evaluate(heartbeat, error, state, now, config)
    state["strikes"] = verdict["strikes"]
    state["last_check_at"] = now
    state["last_verdict"] = verdict
    cooldown = config["alert_cooldown_minutes"] * 60000
    key = verdict["level"]
    if due and now - int(state["alerts"].get(key, 0)) >= cooldown:
        text = (
            "Factory flight controller heartbeat alarm: "
            f"{verdict['level']} ({verdict['detail']}). Checked from the other Mac, so the M2 "
            "itself may be asleep, locked, offline or stopped."
        )
        try:
            receipt = send_alert(config, text)
            state["alerts"][key] = now
            verdict["alert"] = receipt
        except ObserverError as problem:
            verdict["alert"] = {"failed": str(problem)}
    atomic_write(state_path, json.dumps(state, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"at": now, **verdict}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ObserverError as problem:
        print("flight-observer: " + str(problem), file=sys.stderr)
        sys.exit(1)
