#!/usr/bin/env python3
"""Session-bound browser cleanup. Never infer completion from age or inactivity."""

import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time


OWNER_RETENTION = 30 * 24 * 3600
NO_ARTIFACTS = "failed_no_artifacts_by_census"
NO_GENERATION = "failed_no_artifacts_by_generation"


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", value):
        raise ValueError("invalid_session_id")
    return value


def job_identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
        raise ValueError("invalid_job_id")
    return value


def atomic_json(path, row):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".lifecycle-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(row, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def ledger_lock(root, name="lifecycle.lock"):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(root / name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def owner_path(root, job_id):
    return Path(root) / "owners" / (job_identifier(job_id) + ".json")


def bind(root, job_id, session_id):
    """Called by the owning route or after a native browser tool response."""
    identifier(session_id)
    with ledger_lock(root):
        receipt = json.loads((Path(root) / (job_identifier(job_id) + ".json")).read_text())
        if receipt["job_id"] != job_id:
            raise ValueError("receipt_mismatch")
        if not receipt.get("control_socket"):
            # A facade from before this lifecycle has no control channel; its
            # live jobs keep the manual browser_job_finish path.
            raise ValueError("legacy_route_not_bound")
        path = owner_path(root, job_id)
        if path.exists():
            old = json.loads(path.read_text())
            if old["session_id"] != session_id:
                raise ValueError("job_already_owned_by_peer_session")
            return old
        row = {
            "job_id": job_id,
            "session_id": session_id,
            "state": "active",
            "bound_at": time.time(),
        }
        atomic_json(path, row)
        return row


def terminal(root, session_id, event):
    identifier(session_id)
    if event not in ("Stop", "SessionEnd", "Interrupt"):
        raise ValueError("not_a_terminal_event")
    marked = []
    with ledger_lock(root):
        for path in sorted((Path(root) / "owners").glob("*.json")):
            row = json.loads(path.read_text())
            if row["session_id"] == session_id:
                row.update(state="terminal", terminal_event=event, terminal_at=time.time())
                atomic_json(path, row)
                marked.append(row["job_id"])
    return marked


def control(root, receipt, request):
    """Only the exact private facade socket recorded in this receipt is used."""
    name = receipt.get("control_socket", "")
    if not isinstance(name, str) or not re.fullmatch(r"control-[0-9a-f]{16}\.sock", name):
        raise ConnectionError("legacy_route_no_control")
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(120)
        client.connect(str(Path(root) / name))
        client.sendall((json.dumps(request) + "\n").encode())
        data = b""
        while b"\n" not in data and len(data) < 65536:
            chunk = client.recv(4096)
            if not chunk:
                break
            data += chunk
        reply = json.loads(data)
        if not reply.get("ok"):
            raise RuntimeError("live_cleanup_refused")
        return reply


def census_path(root, job_id):
    return Path(root) / "census" / (job_identifier(job_id) + ".json")


def last_allocation_activity(receipt):
    """Latest moment the allocation itself could have created a page.

    Later finish attempts only refuse, so they never move this watermark."""
    moments = [
        stage[1]
        for timing in receipt.get("timings") or []
        if timing.get("tool") != "finish"
        for stage in timing.get("stages") or []
        if len(stage) > 1 and isinstance(stage[1], (int, float))
    ]
    for item in (receipt.get("connection_diagnostics") or {}).values():
        if isinstance(item, dict) and isinstance(item.get("at"), (int, float)):
            moments.append(item["at"])
    return max(moments) if moments else None


def census_eligible(receipt):
    """Only a failed allocation that never recorded any window, tab or relay claim.

    Anything with a real ID has an exact reconciliation path and stays blocking."""
    return (
        receipt.get("status") == "failed"
        and isinstance(receipt.get("allocation_failure"), dict)
        and receipt.get("metadata") is None
        and receipt.get("initial_connector") is None
        and not receipt.get("ownership_pending")
        and not receipt.get("relay_mode")
        and receipt.get("relay_pid") is None
        and not receipt.get("relay_cleanup")
        and receipt.get("window_disposition") is None
        and last_allocation_activity(receipt) is not None
    )


def census_attests(root, job_id, receipt):
    try:
        note = json.loads(census_path(root, job_id).read_text())
    except (OSError, ValueError):
        return None
    if (
        not census_eligible(receipt)
        or not isinstance(note, dict)
        or note.get("job_id") != job_id
        or note.get("orphans") != 0
        or not isinstance(note.get("census_at"), (int, float))
        or note["census_at"] <= last_allocation_activity(receipt)
        or note["census_at"] > time.time() + 60
    ):
        return None
    return note


def record_census(root, job_id, census_at, windows, tabs, reference):
    """Record an exact-process census that found no unmapped automation window or tab."""
    with ledger_lock(root):
        receipt = json.loads((Path(root) / (job_identifier(job_id) + ".json")).read_text())
        if not census_eligible(receipt):
            raise ValueError("receipt_has_ownership_ids_or_is_not_a_failed_allocation")
        if census_at <= last_allocation_activity(receipt):
            raise ValueError("census_predates_allocation")
        if not reference or len(reference) > 500:
            raise ValueError("census_reference_required")
        row = {
            "job_id": job_id,
            "census_at": census_at,
            "windows": windows,
            "tabs": tabs,
            "orphans": 0,
            "reference": reference,
            "recorded_at": time.time(),
        }
        atomic_json(census_path(root, job_id), row)
        return row


def sweep(config, session_id=None):
    """Terminal owner evidence is mandatory. Unknown/active receipts are untouched."""
    with ledger_lock(config["state_dir"], "sweep.lock"):
        return _sweep(config, session_id)


def valid_generation(value):
    return (
        isinstance(value, dict)
        and type(value.get("pid")) is int
        and value["pid"] > 0
        and isinstance(value.get("started"), str)
        and bool(value["started"].strip())
    )


def generation_path(root, job_id):
    return Path(root) / "generation" / (job_identifier(job_id) + ".json")


def generation_eligible(receipt):
    return (
        receipt.get("status") == "failed"
        and valid_generation(receipt.get("generation"))
        and not receipt.get("relay_mode")
        and receipt.get("relay_pid") is None
    )


def record_generation(root, job_id, reference):
    """Retire only a terminal failed job's dead-process IDs, never close current IDs."""
    from browser_jobs import chrome_generation

    with ledger_lock(root):
        receipt = json.loads((Path(root) / (job_identifier(job_id) + ".json")).read_text())
        owner = json.loads(owner_path(root, job_id).read_text())
        current = chrome_generation()
        if (
            receipt.get("job_id") != job_id
            or owner.get("job_id") != job_id
            or owner.get("state") != "terminal"
            or not generation_eligible(receipt)
            or not valid_generation(current)
            or current == receipt["generation"]
        ):
            raise ValueError("terminal_failed_dead_generation_required")
        if not reference or len(reference) > 500:
            raise ValueError("generation_reference_required")
        row = {
            "job_id": job_id,
            "status": NO_GENERATION,
            "previous_generation": receipt["generation"],
            "observed_generation": current,
            "recorded_at": time.time(),
            "reference": reference,
            "browser_close_issued": False,
        }
        atomic_json(generation_path(root, job_id), row)
        return row


def generation_attests(root, job_id, receipt):
    from browser_jobs import chrome_generation

    try:
        note = json.loads(generation_path(root, job_id).read_text())
        if (
            generation_eligible(receipt)
            and note.get("job_id") == job_id
            and note.get("status") == NO_GENERATION
            and note.get("browser_close_issued") is False
            and note.get("previous_generation") == receipt["generation"]
            and valid_generation(note.get("observed_generation"))
            and note["observed_generation"] != receipt["generation"]
            and chrome_generation() == note["observed_generation"]
        ):
            return note
    except (OSError, ValueError, AttributeError):
        pass
    return None


def _sweep(config, session_id=None):
    root = Path(config["state_dir"]).expanduser()
    outcomes = []
    for path in sorted((root / "owners").glob("*.json")):
        try:
            owner = json.loads(path.read_text())
            job_id = job_identifier(owner["job_id"])
            if owner["state"] != "terminal" or (session_id and owner["session_id"] != session_id):
                continue
            receipt_path = root / (job_id + ".json")
            receipt = json.loads(receipt_path.read_text())
            if receipt["status"] == "finished":
                # The receipt is the lasting record, so a long-finished owner
                # row is dropped to keep the ledger and the sweep bounded.
                if time.time() - owner["terminal_at"] > OWNER_RETENTION:
                    path.unlink(missing_ok=True)
                    outcomes.append({"job_id": job_id, "status": "owner_record_retired"})
                else:
                    outcomes.append({"job_id": job_id, "status": "already_finished"})
                continue
            generation = generation_attests(root, job_id, receipt)
            if generation:
                outcomes.append(
                    {
                        "job_id": job_id,
                        "status": NO_GENERATION,
                        "recorded_at": generation["recorded_at"],
                    }
                )
                continue
            note = census_attests(root, job_id, receipt)
            if note:
                # The receipt stays failed. Without saved IDs there is nothing
                # exact to close, and the census found nothing left to close.
                outcomes.append(
                    {"job_id": job_id, "status": NO_ARTIFACTS, "census_at": note["census_at"]}
                )
                continue
            try:
                control(
                    root,
                    receipt,
                    {"action": "finish", "job_id": job_id, "session_id": owner["session_id"]},
                )
            except (ConnectionError, FileNotFoundError):
                # No live transport can close these pages. Reuse the route's
                # exact-ID reconciliation, never a guessed window/title/age.
                from browser_jobs import Route

                route = Route(config)
                job = {**receipt, "client": None}
                try:
                    route.finish(job)
                finally:
                    route.close_control()
            outcomes.append({"job_id": job_id, "status": "finished"})
        except Exception:
            outcomes.append({"job_id": path.stem, "status": "preserved_uncertain"})
    return outcomes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--request", action="store_true")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--session")
    parser.add_argument("--record-census", metavar="JOB_ID")
    parser.add_argument("--reconcile-generation", metavar="JOB_ID")
    parser.add_argument("--census-at", type=float, help="UTC epoch seconds of the census")
    parser.add_argument("--windows", type=int)
    parser.add_argument("--tabs", type=int)
    parser.add_argument("--reference", help="where the census note is recorded")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if args.reconcile_generation:
        report = record_generation(
            Path(config["state_dir"]).expanduser(), args.reconcile_generation, args.reference
        )
    elif args.record_census:
        if None in (args.census_at, args.windows, args.tabs):
            parser.error("--record-census needs --census-at, --windows and --tabs")
        report = record_census(
            Path(config["state_dir"]).expanduser(),
            args.record_census,
            args.census_at,
            args.windows,
            args.tabs,
            args.reference,
        )
    elif args.sweep:
        report = sweep(config, args.session)
    else:
        request = json.loads(sys.stdin.read(1048576))
        session_id = identifier(request["session_id"])
        if request["action"] == "bind":
            report = bind(config["state_dir"], request["job_id"], session_id)
        elif request["action"] == "finish_session":
            terminal(config["state_dir"], session_id, request["event"])
            if request["event"] in ("SessionEnd", "Interrupt"):
                # Codex permits only three seconds for SessionEnd. Persist
                # terminal evidence first, then finish in a detached helper.
                # The nightly sweep retries if that helper is interrupted.
                log = Path(config["state_dir"]) / "session-end-cleanup.log"
                fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, "a") as output:
                    subprocess.Popen(
                        [
                            sys.executable,
                            str(Path(__file__).resolve()),
                            "--config",
                            str(args.config.resolve()),
                            "--sweep",
                            "--session",
                            session_id,
                        ],
                        stdin=subprocess.DEVNULL,
                        stdout=output,
                        stderr=output,
                        start_new_session=True,
                        close_fds=True,
                    )
                report = {"queued": True}
            else:
                report = sweep(config, session_id)
        else:
            raise ValueError("unknown_lifecycle_request")
    print(json.dumps(report))
    return (
        2
        if isinstance(report, list) and any(x["status"] == "preserved_uncertain" for x in report)
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
