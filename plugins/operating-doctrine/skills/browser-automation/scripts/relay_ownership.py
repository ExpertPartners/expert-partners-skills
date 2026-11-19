"""Durable tab provenance shared by protocol-v2 brokers and cleanup workers."""

from contextlib import contextmanager
import json
import os
import sqlite3
import sys

URL_CLASSES = frozenset({"blank", "http", "https", "extension", "other"})


def valid_id(value):
    return type(value) is int and 0 < value <= 2_147_483_647


def url_class(url):
    if not isinstance(url, str):
        return None
    if url == "about:blank" or url.startswith("about:blank#"):
        return "blank"
    for prefix, value in (
        ("https://", "https"),
        ("http://", "http"),
        ("chrome-extension://", "extension"),
    ):
        if url.startswith(prefix):
            return value
    return "other"


def capture_tab(tab):
    """Project a relay tab or update without persisting a URL."""
    if not isinstance(tab, dict):
        return None
    kind = url_class(tab.get("url"))
    if not valid_id(tab.get("id")) or not valid_id(tab.get("windowId")) or kind is None:
        return None
    return {"tabId": tab["id"], "windowId": tab["windowId"], "urlClass": kind}


def authorize_crash_close(saved, observed, latest, generation, current_generation):
    """Refuse unless the caller can prove an unchanged birth claim and target.

    Call under the host-wide broker ownership lock and keep it held through the
    helper reply. The helper independently checks window, ID and URL class.
    """
    if not generation or generation != current_generation:
        return "browser_generation_changed"
    if not isinstance(saved, dict) or not isinstance(latest, dict):
        return "claim_missing"
    for record in (saved, latest):
        if (
            not valid_id(record.get("tabId"))
            or not valid_id(record.get("windowId"))
            or not isinstance(record.get("urlClass"), str)
            or record["urlClass"] not in URL_CLASSES
            or not isinstance(record.get("jobId"), str)
            or not record["jobId"]
            or not valid_id(record.get("claimOrdinal"))
        ):
            return "claim_invalid"
    if any(saved[k] != latest[k] for k in ("jobId", "claimOrdinal", "tabId")):
        return "claim_changed"
    if saved["windowId"] != latest["windowId"] or saved["urlClass"] != latest["urlClass"]:
        return "ownership_projection_changed"
    if (
        not isinstance(observed, dict)
        or not valid_id(observed.get("tabId"))
        or observed["tabId"] != saved["tabId"]
    ):
        return "tab_unobserved"
    if not valid_id(observed.get("windowId")) or observed["windowId"] != saved["windowId"]:
        return "window_changed"
    if observed.get("urlClass") != saved["urlClass"]:
        return "url_class_changed"
    return "authorized"


class OwnershipLedger:
    """Serialize claims and recovery across facade processes.

    Historical rows are retained. A release does not restore an older claim,
    and a tab ID is never resolved across Chrome generations.
    """

    def __init__(self, path):
        fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        try:
            if os.fstat(fd).st_uid != os.getuid() or os.fstat(fd).st_mode & 0o077:
                raise PermissionError("ownership_ledger_not_private")
        finally:
            os.close(fd)
        self.path = path
        with self._transaction() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS claims (
                    claimOrdinal INTEGER PRIMARY KEY AUTOINCREMENT,
                    generation TEXT NOT NULL,
                    jobId TEXT NOT NULL,
                    tabId INTEGER NOT NULL,
                    windowId INTEGER NOT NULL,
                    urlClass TEXT NOT NULL,
                    state TEXT NOT NULL
                )"""
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS tab_history ON claims (generation, tabId, claimOrdinal)"
            )

    @contextmanager
    def _transaction(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _latest(db, generation, tab_id):
        return db.execute(
            """SELECT * FROM claims WHERE generation = ? AND tabId = ?
               ORDER BY claimOrdinal DESC LIMIT 1""",
            (generation, tab_id),
        ).fetchone()

    def claim(self, generation, job_id, tab):
        if (
            not isinstance(generation, str)
            or not generation
            or not isinstance(job_id, str)
            or not job_id
            or not isinstance(tab, dict)
            or not valid_id(tab.get("tabId"))
            or not valid_id(tab.get("windowId"))
            or not isinstance(tab.get("urlClass"), str)
            or tab["urlClass"] not in URL_CLASSES
        ):
            raise ValueError("invalid_tab_claim")
        with self._transaction() as db:
            old = self._latest(db, generation, tab["tabId"])
            if old and old["state"] == "live":
                if old["jobId"] != job_id or any(
                    old[k] != tab[k] for k in ("windowId", "urlClass")
                ):
                    raise ValueError("unreleased_tab_claim")
                return dict(old)
            cursor = db.execute(
                """INSERT INTO claims (generation, jobId, tabId, windowId, urlClass, state)
                   VALUES (?, ?, ?, ?, ?, 'live')""",
                (generation, job_id, tab["tabId"], tab["windowId"], tab["urlClass"]),
            )
            return {
                "tabId": tab["tabId"],
                "windowId": tab["windowId"],
                "urlClass": tab["urlClass"],
                "jobId": job_id,
                "generation": generation,
                "claimOrdinal": cursor.lastrowid,
                "state": "live",
            }

    def observe(self, claim, tab):
        """Checkpoint an authoritative relay observation before returning it."""
        if (
            not isinstance(tab, dict)
            or not valid_id(tab.get("tabId"))
            or tab["tabId"] != claim["tabId"]
            or not valid_id(tab.get("windowId"))
            or not isinstance(tab.get("urlClass"), str)
            or tab["urlClass"] not in URL_CLASSES
        ):
            raise ValueError("invalid_tab_observation")
        with self._transaction() as db:
            latest = self._latest(db, claim["generation"], claim["tabId"])
            if (
                not latest
                or latest["claimOrdinal"] != claim["claimOrdinal"]
                or latest["jobId"] != claim["jobId"]
                or latest["state"] != "live"
            ):
                raise ValueError("claim_not_current")
            if tab["windowId"] != latest["windowId"]:
                raise ValueError("window_changed")
            db.execute(
                "UPDATE claims SET urlClass = ? WHERE claimOrdinal = ?",
                (tab["urlClass"], claim["claimOrdinal"]),
            )
            return {**dict(latest), "urlClass": tab["urlClass"]}

    def mark_released(self, claim):
        """Record loss of relay authority without erasing historical provenance."""
        with self._transaction() as db:
            db.execute(
                """UPDATE claims SET state = 'released'
                   WHERE claimOrdinal = ? AND generation = ? AND jobId = ?
                     AND tabId = ? AND state = 'live'""",
                tuple(claim[k] for k in ("claimOrdinal", "generation", "jobId", "tabId")),
            )

    def mark_closed(self, claim):
        with self._transaction() as db:
            db.execute(
                """UPDATE claims SET state = 'closed'
                   WHERE claimOrdinal = ? AND generation = ? AND jobId = ?
                     AND tabId = ? AND state IN ('live', 'released')""",
                tuple(claim[k] for k in ("claimOrdinal", "generation", "jobId", "tabId")),
            )

    def job_claims(self, generation, job):
        with self._transaction() as db:
            return [
                dict(row)
                for row in db.execute(
                    """SELECT * FROM claims WHERE generation = ? AND jobId = ?
                       ORDER BY claimOrdinal DESC""",
                    (generation, job),
                )
            ]

    def recover(self, claim, read_generation, inventory, close):
        """Record successful exact closure at most once.

        An external effect whose receipt was lost is left unresolved, not
        inferred to have succeeded from later absence.
        """
        with self._transaction() as db:
            generation = claim["generation"]
            current = read_generation()
            if generation != current:
                return "browser_generation_changed"
            latest = self._latest(db, generation, claim["tabId"])
            if not latest:
                return "claim_missing"
            latest = dict(latest)
            if (latest["claimOrdinal"], latest["jobId"]) != (
                claim["claimOrdinal"],
                claim["jobId"],
            ):
                return "claim_changed"
            if latest["state"] != "released":
                return "already_closed" if latest["state"] == "closed" else "claim_live"
            rows = inventory()
            if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
                return "inventory_invalid"
            observed = [row for row in rows if row.get("tabId") == claim["tabId"]]
            if len(observed) > 1:
                return "tab_ambiguous"
            verdict = authorize_crash_close(
                claim, observed[0] if observed else None, latest, generation, read_generation()
            )
            if verdict != "authorized":
                return verdict
            outcome = close(claim["windowId"], claim["tabId"], claim["urlClass"])
            if outcome == "closed":
                db.execute(
                    "UPDATE claims SET state = 'closed' WHERE claimOrdinal = ?",
                    (claim["claimOrdinal"],),
                )
            return outcome


if __name__ == "__main__":
    try:
        ledger = OwnershipLedger(sys.argv[1])
        generation, job_id = sys.argv[2:4]
        op = sys.argv[4]
        data = json.loads(sys.stdin.buffer.read(8193))
        if op == "claim":
            result = ledger.claim(generation, job_id, data["tab"])
        else:
            claim = data["claim"]
            if claim.get("generation") != generation or claim.get("jobId") != job_id:
                raise ValueError("claim_context_invalid")
            if op == "observe":
                result = ledger.observe(claim, data["tab"])
            elif op == "release":
                result = ledger.mark_released(claim)
            elif op == "finish":
                result = ledger.mark_closed(claim)
            else:
                raise ValueError("ledger_command_invalid")
        print(json.dumps(result, separators=(",", ":")))
    except (IndexError, KeyError, OSError, ValueError, sqlite3.Error):
        print('{"error":"ownership_ledger_operation_failed"}')
        sys.exit(2)
