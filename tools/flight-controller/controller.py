#!/usr/bin/env python3
"""Factory flight controller for Ember's M2.

Every scheduled check is ordinary code: it reads the documented Factory Sessions API,
decides from evidence, and writes durable state. No model session and no paid model
request is made by a check. The only outbound agent action is at most one nudge or one
bounded resume per session per cooldown, and only when evidence shows a recoverable
stall or a provider-reported usage reset that has already passed.
"""

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

VERSION = "1.1.0"
MARKER = "flight-controller"
USER_AGENT = "ep-flight-controller/" + VERSION
SEND_URL = "https://api.sendblue.co/api/send-message"
# Documented Sessions API statuses. Everything else is treated as unknown, never as idle.
LIVE = ("running", "pending")

FINISHED = re.compile(r"ready to archive", re.I)
HOLD = re.compile(
    r"(manual hold|on hold|holding (?:for|until)|paused by (?:the )?operator|do not resume"
    r"|do not restart|stop switch)",
    re.I,
)
FOUNDER = re.compile(
    r"(founder decision|decision for allison|waiting on allison|waiting for allison"
    r"|needs allison|need allison|awaiting founder|asked allison|question for allison)",
    re.I,
)
EXHAUSTED = re.compile(
    r"(usage limit|rate limit|rate-limit|quota (?:exceeded|exhausted|reached)"
    r"|out of (?:credits|usage)|credit balance|credits? exhausted|limit reached"
    r"|insufficient credits|no (?:remaining )?usage remaining)",
    re.I,
)
REFUSAL = re.compile(
    r"(request failed|api error|error[: ]|refused|rejected|denied|blocked by"
    r"|cannot (?:continue|proceed|complete)|unable to (?:continue|proceed|complete)"
    r"|try again|retry|resets? (?:at|in)|too many requests|\b429\b|\b529\b"
    r"|overloaded|please wait|paused until)",
    re.I,
)
RESET_AT = re.compile(r"resets?\s+(?:at|on)\s+([0-9][0-9T:\-+.Z ]{7,31})", re.I)
RESET_IN = re.compile(r"(?:try again|retry|resets?)\s+in\s+(\d{1,4})\s*(second|minute|hour)", re.I)
UNITS = {"second": 1, "minute": 60, "hour": 3600}


class ControllerError(Exception):
    """Safe to record. Raw responses and credential errors never reach state or logs."""


class ApiError(ControllerError):
    """kind is auth, http or transport. sent_unknown marks a POST that may have landed."""

    def __init__(self, kind, status=None, sent_unknown=False):
        super().__init__(f"{kind} {status if status is not None else ''}".strip())
        self.kind = kind
        self.status = status
        self.sent_unknown = sent_unknown


def iso(stamp):
    if not stamp:
        return "an unknown time"
    return datetime.fromtimestamp(int(stamp) / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def atomic_write(path, text, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(handle, "w") as output:
        output.write(text)
        output.flush()
        os.fsync(output.fileno())
    os.chmod(temporary, mode)
    temporary.replace(path)


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, ValueError):
        return default


def keychain_secret(account, service):
    """The Factory key stays in the login keychain, so a check needs an unlocked login."""
    try:
        result = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-a", account, "-s", service, "-w"],
            capture_output=True,
            timeout=20,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        raise ControllerError("Factory key unavailable from the login keychain.") from None
    secret = result.stdout.decode().strip()
    if not secret:
        raise ControllerError("Factory key in the login keychain is empty.")
    return secret


def op_item_fields(op, item, vault):
    """Read one 1Password item's fields at run time. No value is logged or stored."""
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
        raise ControllerError("1Password read failed; no credential output recorded.") from None
    return {(field.get("label") or ""): field.get("value") for field in fields}


def blocks(message):
    content = message.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [
            block if isinstance(block, dict) else {"type": "text", "text": str(block)}
            for block in content
        ]
    return []


def message_text(message):
    return "\n".join(
        block["text"]
        for block in blocks(message)
        if block.get("type") == "text" and isinstance(block.get("text"), str)
    )


def spoken_text(message):
    """Only words this session or a person wrote count as evidence of its own state.
    Tool output, reasoning, injected reminders, reports relayed from child sessions and
    the controller's own messages are excluded, so none of them can trigger a rule."""
    if message.get("role") not in ("assistant", "user", "system"):
        return ""
    if message.get("visibility") == "llm_only":
        return ""
    if (message.get("sender") or {}).get("kind") == "agent":
        return ""
    text = message_text(message)
    return "" if "[" + MARKER + " " in text else text


def open_tool_call(messages):
    """Name of an unanswered tool call in the newest assistant turn, or None. The API
    reports native prompts only for child sessions, so for the session itself an
    unanswered AskUser call is the evidence that it is waiting on a person."""
    answered = set()
    for message in messages:
        for block in blocks(message):
            if block.get("type") == "tool_result":
                answered.add(block.get("toolUseId") or block.get("tool_use_id"))
        if message.get("role") != "assistant":
            continue
        calls = [block for block in blocks(message) if block.get("type") == "tool_use"]
        if calls:
            pending = [
                call for call in calls if (call.get("id") or call.get("toolUseId")) not in answered
            ]
            return (pending[0].get("name") or "tool") if pending else None
        if message_text(message):
            return None
    return None


def parse_reset(text, now_ms):
    """Provider-reported reset only. An absent or unparsable reset stays unknown."""
    match = RESET_IN.search(text)
    if match:
        return now_ms + int(match.group(1)) * UNITS[match.group(2).lower()] * 1000
    match = RESET_AT.search(text)
    if match:
        raw = match.group(1).strip().rstrip(".")
        for candidate in (raw, raw.replace(" ", "T"), raw.replace("Z", "+00:00")):
            try:
                stamp = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            except ValueError:
                continue
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            return int(stamp.timestamp() * 1000)
    return None


def classify(session, children, messages, now_ms, config):
    """Evidence, not a status label, decides whether work is recoverably stalled."""
    status = session.get("status")
    stale_minutes = max(0.0, (now_ms - int(session.get("updatedAt") or 0)) / 60000.0)
    live_children = [child for child in children if child.get("status") in LIVE]
    attention = session.get("attention") or None
    blocked_children = [
        child
        for child in children
        if isinstance(child.get("attention"), dict)
        and child["attention"].get("kind") in ("ask-user", "permission")
    ]
    verdict = {
        "status": status,
        "stale_minutes": round(stale_minutes, 1),
        "children_live": len(live_children),
        "children_total": len(children),
        "blocked_children": [child["sessionId"] for child in blocked_children],
        "reset_at": None,
        "evidence": "",
    }
    if status in LIVE:
        return dict(verdict, state="running", reason="session_running")
    if status not in ("idle",):
        return dict(verdict, state="unknown", reason="unknown_status")
    if isinstance(attention, dict) and attention.get("kind") in ("ask-user", "permission"):
        # A native prompt is answered in the session itself. Posting a message does not
        # clear it, so the controller never treats a send as an answer.
        return dict(
            verdict,
            state="blocked_attention",
            reason="attention_" + str(attention.get("kind")),
            evidence="attention since " + str(attention.get("since")),
        )
    recent = messages[: config["evidence_messages"]]
    pending_call = open_tool_call(recent)
    if pending_call:
        if re.sub(r"[^a-z]", "", pending_call.lower()) == "askuser":
            return dict(
                verdict, state="blocked_attention", reason="open_ask_user", evidence=pending_call
            )
        return dict(verdict, state="tool_pending", reason="open_tool_call", evidence=pending_call)
    spoken = [(message, spoken_text(message)) for message in recent]
    spoken = [(message, words) for message, words in spoken if words]
    latest, latest_words = next(
        ((m, w) for m, w in spoken if m.get("role") in ("assistant", "system")), ({}, "")
    )
    text = "\n".join(words for _, words in spoken)
    if FINISHED.search(latest_words):
        return dict(
            verdict, state="finished", reason="completion_text", evidence="ready to archive"
        )
    if HOLD.search(text):
        return dict(verdict, state="held", reason="hold_text", evidence=HOLD.search(text).group(0))
    if FOUNDER.search(text):
        return dict(
            verdict,
            state="founder_decision",
            reason="founder_text",
            evidence=FOUNDER.search(text).group(0),
        )
    hit = EXHAUSTED.search(latest_words)
    if hit:
        # The words alone are not a refusal: a session discussing a usage limit reads exactly
        # like one that was refused by the provider. A real refusal carries a refusal cue
        # beside the phrase or a reset time, so without either this stays ordinary prose.
        said_at = int(latest.get("createdAt") or now_ms)
        reset_at = parse_reset(latest_words, said_at)
        nearby = latest_words[max(0, hit.start() - 160) : hit.end() + 160]
        if reset_at or REFUSAL.search(nearby):
            return dict(
                verdict,
                state="usage_exhausted",
                reason="usage_text",
                evidence=hit.group(0),
                evidence_at=said_at,
                reset_at=reset_at,
            )
    if blocked_children:
        return dict(verdict, state="child_blocked", reason="child_attention")
    if live_children:
        # An orchestrator waiting for working children is healthy, however long it waits.
        return dict(verdict, state="waiting_on_children", reason="children_live")
    if stale_minutes < config["stale_minutes"]:
        return dict(verdict, state="idle_recent", reason="within_stale_window")
    return dict(verdict, state="stalled", reason="idle_no_live_children_stale")


class Api:
    """Bounded reader of the documented Sessions API. GET retries, POST never does."""

    def __init__(self, base, token, *, timeout=20, retries=2, sleep=time.sleep, opener=None):
        self.base = base.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.retries = retries
        self.sleep = sleep
        self.opener = opener or urllib.request.urlopen

    def _call(self, method, path, body=None, retry=True):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        attempt = 0
        while True:
            attempt += 1
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    raw = response.read().decode()
                return json.loads(raw) if raw.strip() else {}
            except urllib.error.HTTPError as error:
                if error.code in (401, 403):
                    raise ApiError("auth", error.code) from None
                if (
                    retry
                    and error.code in (408, 429, 500, 502, 503, 504)
                    and attempt <= self.retries
                ):
                    self.sleep(min(2**attempt, 8))
                    continue
                raise ApiError("http", error.code) from None
            except (urllib.error.URLError, OSError, ValueError):
                if retry and attempt <= self.retries:
                    self.sleep(min(2**attempt, 8))
                    continue
                raise ApiError("transport", None, sent_unknown=not retry) from None

    def session(self, session_id):
        return self._call("GET", "/sessions/" + session_id)

    def children(self, session_id):
        answer = self._call(
            "GET",
            "/sessions/" + session_id + "/children?includeAttention=true&includeUsage=true",
        )
        return answer.get("sessions") or []

    def messages(self, session_id, limit):
        answer = self._call("GET", f"/sessions/{session_id}/messages?limit={int(limit)}")
        return answer.get("messages") or []

    def post_message(self, session_id, text):
        # The documented request body requires "text". Sending "content" is refused with
        # HTTP 400, which silently disabled every recovery message until 2026-11-10.
        return self._call(
            "POST", "/sessions/" + session_id + "/messages", {"text": text}, retry=False
        )


class Alerts:
    """Existing Ember notification channel. No new account, integration or recipient."""

    def __init__(self, config, *, opener=None):
        self.config = config
        self.opener = opener or urllib.request.urlopen
        self.sent = []

    def send(self, text):
        settings = self.config["alerts"]
        fields = op_item_fields(settings["op"], settings["item"], settings["vault"])
        body = json.dumps(
            {
                "number": settings["recipient"],
                "from_number": fields.get("phone"),
                "content": text[: settings.get("max_chars", 900)],
            }
        ).encode()
        request = urllib.request.Request(
            SEND_URL,
            data=body,
            method="POST",
            headers={
                "sb-api-key-id": fields["api-key-id"],
                "sb-api-secret-key": fields["api-secret-key"],
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with self.opener(request, timeout=30) as response:
                answer = json.loads(response.read().decode() or "{}")
        except urllib.error.HTTPError as error:
            raise ControllerError(f"Alert refused (HTTP {error.code}); content withheld.") from None
        except (urllib.error.URLError, OSError, ValueError):
            raise ControllerError("Alert outcome unknown; content withheld.") from None
        receipt = {
            "handle": answer.get("message_handle"),
            "status": answer.get("status"),
            "at": int(time.time() * 1000),
        }
        self.sent.append(receipt)
        return receipt


class Controller:
    def __init__(self, config, api, alerts, *, clock=None, log=None):
        self.config = config
        self.api = api
        self.alerts = alerts
        self.clock = clock or (lambda: int(time.time() * 1000))
        self.state_dir = Path(config["state_dir"]).expanduser()
        self.state_path = self.state_dir / "state.json"
        self.heartbeat_path = self.state_dir / "heartbeat.json"
        self.stop_path = self.state_dir / "STOP"
        self.log_path = Path(log or self.state_dir / "controller.log")
        self.state = load_json(
            self.state_path,
            {"tick_seq": 0, "ledger": {}, "alerts": {}, "gaps": [], "consecutive_failures": 0},
        )

    # -- durable plumbing ------------------------------------------------------
    def record(self, event):
        line = json.dumps({"at": self.clock(), **event}, sort_keys=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if self.log_path.exists() and self.log_path.stat().st_size > 4_000_000:
            self.log_path.replace(self.log_path.with_suffix(".1"))
        with open(os.open(self.log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), "a") as f:
            f.write(line + "\n")

    def save_state(self):
        atomic_write(self.state_path, json.dumps(self.state, indent=2, sort_keys=True) + "\n")

    def publish_heartbeat(self, report):
        """World-readable so an off-host reader can see liveness without any state access."""
        atomic_write(
            self.heartbeat_path, json.dumps(report, indent=2, sort_keys=True) + "\n", 0o644
        )

    def stopped(self):
        return self.stop_path.exists()

    def local_now(self):
        return datetime.fromtimestamp(self.clock() / 1000, ZoneInfo(self.config["timezone"]))

    # -- startup recovery ------------------------------------------------------
    def check_gap(self):
        now = self.clock()
        last = int(self.state.get("last_tick_at") or 0)
        interval = self.config["interval_seconds"] * 1000
        if last and now - last > 2 * interval:
            gap = {
                "missed_from": last,
                "resumed_at": now,
                "minutes": round((now - last) / 60000.0, 1),
            }
            self.state.setdefault("gaps", []).append(gap)
            self.state["gaps"] = self.state["gaps"][-20:]
            self.record({"event": "gap_recovered", **gap})
            return gap
        return None

    # -- dedup ledger ----------------------------------------------------------
    def entry(self, session_id, action, reason):
        key = f"{session_id}|{action}|{reason}"
        return key, self.state["ledger"].setdefault(key, {"count": 0})

    def sends_today(self):
        day = self.local_now().strftime("%Y-%m-%d")
        return sum(
            1
            for item in self.state["ledger"].values()
            for stamp in [item.get("accepted_at")]
            if stamp
            and datetime.fromtimestamp(stamp / 1000, ZoneInfo(self.config["timezone"])).strftime(
                "%Y-%m-%d"
            )
            == day
        )

    def reconcile(self, session_id, entry):
        """A POST whose outcome was unknown is reconciled against the session's own
        messages before anything is sent again, so one stall never gets two nudges."""
        nonce = entry.get("pending_nonce")
        if not nonce:
            return True
        try:
            messages = self.api.messages(session_id, self.config["evidence_messages"])
        except ApiError:
            return False
        landed = any(nonce in message_text(message) for message in messages)
        entry.pop("pending_nonce", None)
        if landed:
            entry["accepted_at"] = entry.get("accepted_at") or self.clock()
            entry["accepted_unconfirmed"] = True
            entry["count"] = entry.get("count", 0) + 1
            self.record({"event": "send_reconciled", "session": session_id, "landed": True})
            return False
        self.record({"event": "send_reconciled", "session": session_id, "landed": False})
        return True

    def due(self, session_id, action):
        cooldown = self.config["cooldown_minutes"] * 60000
        prefix = f"{session_id}|{action}|"
        attempts = [
            int(item.get("last_attempt_at") or 0)
            for key, item in self.state["ledger"].items()
            if key.startswith(prefix)
        ]
        return self.clock() - max(attempts or [0]) >= cooldown

    def unverified_nudge(self, session_id):
        prefix = f"{session_id}|nudge|"
        return any(
            item.get("progress_unverified_at") and not item.get("progress_verified_at")
            for key, item in self.state["ledger"].items()
            if key.startswith(prefix)
        )

    # -- actions ---------------------------------------------------------------
    def send_to_session(self, session_id, action, reason, verdict, session, dry_run):
        key, entry = self.entry(session_id, action, reason)
        if not self.reconcile(session_id, entry):
            return {"action": action, "session": session_id, "result": "reconciled_pending"}
        if entry.get("count", 0) >= 1:
            self.record({"event": "suppressed_duplicate", "key": key, "reason": reason})
            return {"action": action, "session": session_id, "result": "suppressed_duplicate"}
        if not self.due(session_id, action):
            self.record({"event": "suppressed_cooldown", "key": key, "reason": reason})
            return {"action": action, "session": session_id, "result": "suppressed_duplicate"}
        if self.sends_today() >= self.config["max_sends_per_day"]:
            return {"action": action, "session": session_id, "result": "daily_cap"}
        nonce = uuid.uuid4().hex[:12]
        text = self.compose(action, verdict, nonce)
        if dry_run:
            return {"action": action, "session": session_id, "result": "dry_run", "nonce": nonce}
        entry["pending_nonce"] = nonce
        entry["last_attempt_at"] = self.clock()
        entry["baseline"] = {
            "updatedAt": session.get("updatedAt"),
            "messageCount": session.get("messageCount"),
        }
        self.save_state()
        try:
            answer = self.api.post_message(session_id, text)
        except ApiError as error:
            if error.sent_unknown:
                self.record({"event": "send_ambiguous", "key": key})
                return {"action": action, "session": session_id, "result": "ambiguous"}
            entry.pop("pending_nonce", None)
            self.record({"event": "send_failed", "key": key, "error": str(error)})
            return {"action": action, "session": session_id, "result": "failed"}
        entry.pop("pending_nonce", None)
        entry["accepted_at"] = self.clock()
        entry["message_id"] = answer.get("messageId")
        entry["recipient_status"] = answer.get("recipientDroidStatus")
        entry["count"] = entry.get("count", 0) + 1
        entry["nonce"] = nonce
        entry.pop("progress_verified_at", None)
        self.record({"event": "message_accepted", "key": key, "message_id": entry["message_id"]})
        return {
            "action": action,
            "session": session_id,
            "result": "message_accepted",
            "message_id": entry["message_id"],
        }

    def compose(self, action, verdict, nonce):
        if action == "resume":
            head = (
                "Factory flight controller: the usage limit this session reported has passed its "
                "provider-reported reset. This is one bounded attempt to verify recovery."
            )
        else:
            head = (
                "Factory flight controller: this session has been idle "
                f"{verdict['stale_minutes']:.0f} minutes with no running children and no pending "
                "question. If work remains, continue it."
            )
        return (
            f"{head} Keep the approved scope, do not start new workstreams, and do not treat this "
            "as founder approval. If you are waiting on a genuine founder decision or are "
            f"finished, say so instead of resuming. [{MARKER} {nonce}]"
        )

    def verify_progress(self, session_id, messages):
        """An accepted message is recorded separately from actual resumed progress, which
        needs the session's own reply written after the controller's message landed."""
        results = []
        grace = self.config["progress_grace_minutes"] * 60000
        for key, entry in self.state["ledger"].items():
            if not key.startswith(session_id + "|") or not entry.get("accepted_at"):
                continue
            if entry.get("progress_verified_at") or entry.get("progress_unverified_at"):
                continue
            replies = [
                message
                for message in messages
                if message.get("role") == "assistant"
                and int(message.get("createdAt") or 0) > int(entry["accepted_at"])
            ]
            if replies:
                entry["progress_verified_at"] = self.clock()
                entry["progress_evidence"] = {
                    "replies": len(replies),
                    "tool_calls": sum(
                        1 for m in replies for b in blocks(m) if b.get("type") == "tool_use"
                    ),
                    "newest_seq": max(int(m.get("seq") or 0) for m in replies),
                }
                results.append({"key": key, "progress": "verified"})
            elif self.clock() - entry["accepted_at"] > grace:
                entry["progress_unverified_at"] = self.clock()
                results.append({"key": key, "progress": "unverified"})
        return results

    def alert(self, kind, text):
        cooldown = self.config["alert_cooldown_minutes"] * 60000
        last = self.state["alerts"].get(kind, 0)
        if self.clock() - last < cooldown:
            return {"alert": kind, "result": "suppressed_duplicate"}
        try:
            receipt = self.alerts.send(text)
        except ControllerError as error:
            self.record({"event": "alert_failed", "kind": kind, "error": str(error)})
            return {"alert": kind, "result": "failed"}
        self.state["alerts"][kind] = self.clock()
        self.record({"event": "alert_sent", "kind": kind, "handle": receipt.get("handle")})
        return {"alert": kind, "result": "sent", "handle": receipt.get("handle")}

    # -- one scheduled check ---------------------------------------------------
    def tick(self, dry_run=False):
        now = self.clock()
        gap = self.check_gap()
        self.state["tick_seq"] = int(self.state.get("tick_seq", 0)) + 1
        report = {
            "version": VERSION,
            "tick_seq": self.state["tick_seq"],
            "last_tick_at": now,
            "interval_seconds": self.config["interval_seconds"],
            "stopped": self.stopped(),
            "pid": os.getpid(),
            "sessions": {},
            "actions": [],
            "alerts": [],
            "gap_recovered": gap,
            "api": {"ok": True, "error": None},
        }
        if report["stopped"]:
            report["api"]["ok"] = None
            self.state["last_tick_at"] = now
            self.save_state()
            self.publish_heartbeat(report)
            self.record({"event": "tick_stopped", "tick": report["tick_seq"]})
            return report
        failures = []
        for session_id in self.config["sessions"]:
            try:
                session = self.api.session(session_id)
                children = self.api.children(session_id)
                messages = self.api.messages(session_id, self.config["evidence_messages"])
            except ApiError as error:
                failures.append({"session": session_id, "error": str(error), "kind": error.kind})
                report["sessions"][session_id] = {"state": "api_unavailable", "error": error.kind}
                continue
            verdict = classify(session, children, messages, now, self.config)
            verdict["title"] = session.get("title")
            report["sessions"][session_id] = verdict
            report["actions"].extend(self.verify_progress(session_id, messages))
            title = verdict.get("title") or session_id
            link = "https://app.factory.ai/sessions/" + session_id
            outcome = None
            if verdict["state"] == "stalled":
                if self.unverified_nudge(session_id):
                    # A nudge that produced no reply is not repeated; a person looks instead.
                    outcome = {
                        "action": "nudge",
                        "session": session_id,
                        "result": "held_unverified",
                    }
                    report["actions"].append(outcome)
                    report["alerts"].append(
                        self.alert(
                            "nudge_unverified:" + session_id,
                            f"Factory flight controller: {title} did not resume after one "
                            "nudge. No further nudges will be sent. " + link,
                        )
                    )
                else:
                    stall = "stale_since:" + str(session.get("updatedAt"))
                    outcome = self.send_to_session(
                        session_id, "nudge", stall, verdict, session, dry_run
                    )
                    report["actions"].append(outcome)
            elif verdict["state"] == "usage_exhausted":
                outcome = self.handle_exhausted(session_id, verdict, session, dry_run)
                report["actions"].append(outcome)
                if outcome.get("result") == "suppressed_duplicate":
                    report["alerts"].append(
                        self.alert(
                            "usage_still_exhausted:" + session_id,
                            f"Factory flight controller: {title} still reports a usage limit "
                            "after the one bounded resume. Nothing else will be sent. " + link,
                        )
                    )
                elif outcome.get("result") == "waiting_for_reset" and not verdict["children_live"]:
                    # Waiting silently for a reset is indistinguishable from a dead stall, so
                    # the wait itself is reported once per exhaustion message.
                    report["alerts"].append(
                        self.alert(
                            f"usage_parked:{session_id}:{outcome.get('ready_at')}",
                            f"Factory flight controller: {title} reported a usage limit and has "
                            f"no running children. Waiting until {iso(outcome.get('ready_at'))} "
                            f"({outcome.get('basis')}) before one bounded resume, so nothing is "
                            "watching it resume until then. " + link,
                        )
                    )
            if outcome and outcome.get("result") == "failed":
                # The recovery action itself is broken. Silence here once hid six refused
                # sends, so a person is told rather than the failure only reaching the log.
                report["alerts"].append(
                    self.alert(
                        "action_failed:" + session_id,
                        f"Factory flight controller: the {outcome.get('action')} it tried to send "
                        f"to {title} was refused by the API, so no recovery message reached it. "
                        "Check the controller, not the session. " + link,
                    )
                )
            if verdict["state"] in ("blocked_attention", "founder_decision", "child_blocked"):
                report["alerts"].append(
                    self.alert(
                        "founder_blocker:" + session_id,
                        f"Factory flight controller: {verdict.get('title') or session_id} is "
                        f"waiting on you ({verdict['reason']}). Nothing was answered on your "
                        "behalf. https://app.factory.ai/sessions/" + session_id,
                    )
                )
            if verdict["state"] == "finished":
                report["alerts"].append(
                    self.alert(
                        "finished:" + session_id,
                        f"Factory flight controller: {verdict.get('title') or session_id} reports "
                        "its work finished and ready to archive. "
                        "https://app.factory.ai/sessions/" + session_id,
                    )
                )
        if failures:
            self.state["consecutive_failures"] = int(self.state.get("consecutive_failures", 0)) + 1
            report["api"] = {"ok": False, "error": failures[0]["kind"]}
        else:
            self.state["consecutive_failures"] = 0
            self.state["last_success_at"] = now
        report["consecutive_failures"] = self.state["consecutive_failures"]
        report["last_success_at"] = self.state.get("last_success_at")
        if self.state["consecutive_failures"] >= self.config["failure_alert_after"]:
            report["alerts"].append(
                self.alert(
                    "api_failure",
                    "Factory flight controller: "
                    f"{self.state['consecutive_failures']} consecutive failed checks "
                    f"({report['api']['error']}). Factory work is not being watched right now.",
                )
            )
        summary = self.maybe_summary(report)
        if summary:
            report["alerts"].append(summary)
        self.state["last_tick_at"] = now
        self.state["last_report"] = report
        self.save_state()
        self.publish_heartbeat(report)
        self.record({"event": "tick", "tick": report["tick_seq"], "sessions": report["sessions"]})
        return report

    def handle_exhausted(self, session_id, verdict, session, dry_run):
        """An old exhaustion message is not current exhaustion. One bounded attempt per
        exhaustion message runs only after a provider-reported reset plus margin, or after
        a conservative wait from the message when the provider reported no reset at all."""
        said_at = int(verdict.get("evidence_at") or self.clock())
        key, entry = self.entry(session_id, "resume", f"usage_reset:{said_at}")
        margin = self.config["reset_margin_minutes"] * 60000
        reset_at = verdict.get("reset_at")
        if reset_at:
            ready_at = reset_at + margin
            basis = "provider_reset"
        else:
            ready_at = said_at + self.config["unknown_reset_wait_minutes"] * 60000
            basis = "conservative_wait"
        entry["ready_at"] = ready_at
        entry["basis"] = basis
        if self.clock() < ready_at:
            return {
                "action": "resume",
                "session": session_id,
                "result": "waiting_for_reset",
                "basis": basis,
                "ready_at": ready_at,
            }
        outcome = self.send_to_session(
            session_id, "resume", f"usage_reset:{said_at}", verdict, session, dry_run
        )
        outcome["basis"] = basis
        return outcome

    def maybe_summary(self, report):
        now_local = self.local_now()
        day = now_local.strftime("%Y-%m-%d")
        if self.state.get("summary_day") == day or now_local.hour < self.config["summary_hour"]:
            return None
        lines = [f"Factory flight controller morning summary {day}:"]
        for session_id, verdict in report["sessions"].items():
            lines.append(
                f"- {(verdict.get('title') or session_id)[:40]}: {verdict.get('state')} "
                f"({verdict.get('stale_minutes', '?')} min idle, "
                f"{verdict.get('children_live', 0)} live children)"
            )
        accepted = sum(int(item.get("count", 0)) for item in self.state["ledger"].values())
        verified = sum(
            1 for item in self.state["ledger"].values() if item.get("progress_verified_at")
        )
        lines.append(f"Nudges accepted {accepted}, progress verified {verified}.")
        lines.append(
            f"Checks since install {self.state['tick_seq']}, gaps {len(self.state['gaps'])}."
        )
        result = self.alert("summary:" + day, "\n".join(lines))
        if result.get("result") == "sent":
            self.state["summary_day"] = day
        return result


DEFAULTS = {
    "api_base": "https://api.factory.ai/api/v0",
    "interval_seconds": 900,
    "stale_minutes": 25,
    "cooldown_minutes": 90,
    "max_sends_per_day": 6,
    "reset_margin_minutes": 10,
    "unknown_reset_wait_minutes": 360,
    "progress_grace_minutes": 20,
    "failure_alert_after": 3,
    "alert_cooldown_minutes": 180,
    "evidence_messages": 40,
    "summary_hour": 7,
    "timezone": "America/Chicago",
    "http_timeout_seconds": 20,
    "http_retries": 2,
}


def with_defaults(config):
    merged = {**DEFAULTS, **config}
    for required in ("sessions", "state_dir", "alerts"):
        if not merged.get(required):
            raise ControllerError("Config must set " + required)
    return merged


def build(config_path):
    config = load_json(config_path, None)
    if config is None:
        raise ControllerError("Config file missing or unreadable: " + str(config_path))
    return with_defaults(config)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="~/.config/flight-controller/config.json")
    parser.add_argument("--once", action="store_true", help="Run one scheduled check (default)")
    parser.add_argument("--dry-run", action="store_true", help="Decide and log, never send")
    parser.add_argument("--status", action="store_true", help="Print the durable heartbeat")
    parser.add_argument("--stop", action="store_true", help="Operator stop switch on")
    parser.add_argument("--resume", action="store_true", help="Operator stop switch off")
    parser.add_argument("--test-alert", action="store_true", help="Send one alert end to end")
    args = parser.parse_args(argv)
    config = build(Path(args.config).expanduser())
    state_dir = Path(config["state_dir"]).expanduser()
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stop_path = state_dir / "STOP"
    if args.stop:
        atomic_write(stop_path, json.dumps({"stopped_at": int(time.time() * 1000)}) + "\n")
        print("stopped")
        return 0
    if args.resume:
        stop_path.unlink(missing_ok=True)
        print("resumed")
        return 0
    if args.status:
        print(json.dumps(load_json(state_dir / "heartbeat.json", {}), indent=2, sort_keys=True))
        return 0
    lock = os.open(state_dir / "lock", os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another check is running; this one exits without duplicating it")
        return 0
    api = Api(
        config["api_base"],
        keychain_secret(config["factory_key"]["account"], config["factory_key"]["service"]),
        timeout=config["http_timeout_seconds"],
        retries=config["http_retries"],
    )
    controller = Controller(config, api, Alerts(config))
    if args.test_alert:
        print(
            json.dumps(controller.alert("test", "Factory flight controller test alert."), indent=2)
        )
        controller.save_state()
        return 0
    report = controller.tick(dry_run=args.dry_run)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ControllerError as problem:
        print("flight-controller: " + str(problem), file=sys.stderr)
        sys.exit(1)
