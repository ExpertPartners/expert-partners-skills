#!/usr/bin/env python3
"""HQ experience watcher, route HO-HQ-012 (Approved experience decision).

Modes
  watch      Every 10 minutes (launchd). Finds new Decision Log entries with
             Experience in the title, sends a five-field handoff to every
             affected Factory Workstream (find_owner + post_message), appends
             the instance to the Director Inbox, and relays receiver pickups.
  reconcile  Daily at a quiet hour (launchd). Catches any experience entry the
             watcher missed in the last 14 days, folds new non-TEST decisions
             into the Human Experience Standard, and writes the unconfirmed
             handoff list at the top of the Director Inbox for the 7:35 AM
             health check.
  baseline   Marks every current experience entry as already handled. Run once
             at install so history is not re-sent.

Secrets come from 1Password at run time (gws.py and op read) and are never
printed. Decision Log 2026-11-27, AI Experience Director established in HQ
Claude with immediate transmission.
"""

import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gws  # noqa: E402

DECISION_LOG = "1ausL1HV3ns3VMZH86jD8zjWnAKSQ3DaUfFzkiwR1qWc"
INBOX = "1gSUYfy3dEp0Ke1iIfeCtCW4riXIiZsyR0GcJlJaaicc"
STANDARD = os.environ.get("HX_STANDARD_DOC", "")
ROUTE = "HO-HQ-012"
DL_URL = f"https://docs.google.com/document/d/{DECISION_LOG}/edit"
INBOX_URL = f"https://docs.google.com/document/d/{INBOX}/edit"
FC = "https://factory-connection.expert-partners.workers.dev/api/tools/"
FC_TOKEN_REF = "op://Automation/Factory Connection - Hub API token/credential"
STATE_DIR = os.path.expanduser("~/Library/Application Support/hq-experience-watcher")
STATE = os.path.join(STATE_DIR, "state.json")
CT = ZoneInfo("America/Chicago")
MAX_RECIPIENTS = 4

HEAD = re.compile(
    r"^﻿?((January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, (20\d\d))\. (.+)$",
    re.M,
)

# Keyword routes. Every entry is checked against "Experience"; extra queries
# are added when the entry touches the named area.
TOPIC_QUERIES = [
    (re.compile(r"\b(hub|today|campus|dashboard|onboarding|rive)\b", re.I), "Hub"),
    (
        re.compile(r"\b(agreement|authority engine|coaching|speaking|client journey)\b", re.I),
        "Agreement",
    ),
    (re.compile(r"\b(creative|studio|video|voice|avatar|heygen)\b", re.I), "Creative Production"),
]


def log(*a):
    print(dt.datetime.now(CT).strftime("%Y-%m-%d %H:%M:%S %Z"), *a, flush=True)


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {"entries": {}, "dl_version": None}


def save_state(s):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE + ".tmp"
    json.dump(s, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE)


# ---------- Decision Log ----------


def entries():
    text = gws.export_text(DECISION_LOG).replace("\r", "")
    ms = list(HEAD.finditer(text))
    out = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        title = m.group(4).strip()
        heading = m.group(0).lstrip("﻿").strip()
        body = text[m.end() : end].strip()
        try:
            date = dt.datetime.strptime(m.group(1), "%B %d, %Y").date()
        except ValueError:
            date = None
        out.append(
            {
                "key": hashlib.sha1(heading.encode()).hexdigest()[:16],
                "heading": heading,
                "title": title,
                "date": date,
                "body": body,
            }
        )
    return out


def is_experience(e):
    return "experience" in e["title"].lower()


def is_test(e):
    return e["title"].startswith("TEST ")


# ---------- Factory connection ----------
_fc_token = None


def fc(tool, args):
    global _fc_token
    if _fc_token is None:
        _fc_token = gws.op_read(FC_TOKEN_REF)
    req = urllib.request.Request(
        FC + tool,
        data=json.dumps(args).encode(),
        method="POST",
        headers={
            "Authorization": "Bearer " + _fc_token,
            "Content-Type": "application/json",
            "User-Agent": "hq-experience-watcher/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read()).get("result")


def affected_workstreams(e):
    text = e["title"] + " " + e["body"][:3000]
    queries = ["Experience"] + [q for rx, q in TOPIC_QUERIES if rx.search(text)]
    seen, out = set(), []
    for q in queries:
        try:
            res = fc("find_owner", {"query": q, "pages": 5}) or {}
        except Exception as ex:  # keep going, the next query may still work
            log("find_owner failed", q, type(ex).__name__)
            continue
        for m in res.get("matches", []):
            if m.get("kind") != "workstream-or-mission" or m["sessionId"] in seen:
                continue
            seen.add(m["sessionId"])
            out.append(
                {"sessionId": m["sessionId"], "title": m["title"].split("\n")[0][:80], "query": q}
            )
    return out[:MAX_RECIPIENTS]


def next_business_day(now):
    d = now + dt.timedelta(days=1)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def handoff_text(e, inst, needed_by, receiver_title):
    summary = re.sub(r"\s+", " ", e["body"])[:900]
    test = (
        " This is a TEST transmission proof, not a real decision. Confirm pickup, but change nothing in the build."
        if is_test(e)
        else ""
    )
    return (
        f"Handoff {ROUTE}, approved experience decision.{test}\n\n"
        f"What. Decision Log entry \"{e['heading']}\". {summary}\n"
        f"For. {receiver_title}, as an affected build owner, and the AI Experience Director.\n"
        f"What to do. Apply this experience decision to your live build where it touches what a person sees, and route it to the right worker. "
        f"The AI Experience Director folds it into the Human Experience Standard.\n"
        f"By when. Pick up by {needed_by.strftime('%A %B %-d, %Y')} end of day America/Chicago.\n"
        f"Source. {DL_URL}\n\n"
        f"Confirm pickup. Add this exact line immediately below instance {inst} in the Director Inbox {INBOX_URL}\n"
        f"PICKED UP {ROUTE} by {receiver_title}, <YYYY-MM-DD>, instance_id={inst}\n"
        f"If you cannot write to Drive, reply in this session with that exact line and the watcher copies it there, marked as relayed from this session.\n\n"
        f"HANDOFF INSTANCE BEGIN v2\nroute_id={ROUTE}\ninstance_id={inst}\nitem={e['heading']}\nfor={receiver_title}\n"
        f"receiver_action=Apply to live build and confirm pickup\nneeded_by={needed_by.isoformat()} 17:00 America/Chicago\nsource_link={DL_URL}\nHANDOFF INSTANCE END"
    )


# ---------- Director Inbox ----------


def _paras(doc):
    for el in doc["body"]["content"]:
        if "paragraph" in el:
            t = "".join(
                x.get("textRun", {}).get("content", "") for x in el["paragraph"]["elements"]
            )
            yield el, t


def inbox_insert_after_heading(heading, lines):
    doc = gws.get_doc(INBOX)
    idx = None
    for el, t in _paras(doc):
        if t.strip() == heading:
            idx = el["endIndex"]
    if idx is None:
        raise RuntimeError("inbox heading missing: " + heading)
    body = "".join(line + "\n" for line in lines)
    reqs = [
        {"insertText": {"location": {"index": idx}, "text": body}},
        {
            "updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": idx + len(body)},
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                "fields": "namedStyleType",
            }
        },
    ]
    r = gws.batch_update(INBOX, reqs)
    return r.get("writeControl", {}).get("requiredRevisionId")


def inbox_text():
    return gws.export_text(INBOX).replace("\r", "")


def inbox_add_pickup(inst, line):
    doc = gws.get_doc(INBOX)
    found, idx = False, None
    for el, t in _paras(doc):
        if t.strip() == f"instance_id={inst}":
            found = True
        if found and t.strip() == "HANDOFF INSTANCE END":
            idx = el["endIndex"]
            break
    if idx is None:
        raise RuntimeError("instance not in inbox: " + inst)
    gws.batch_update(INBOX, [{"insertText": {"location": {"index": idx}, "text": line + "\n"}}])


# ---------- core ----------


def send(e, state, now):
    rec = state["entries"].setdefault(e["key"], {"heading": e["heading"], "instances": {}})
    if rec.get("status") in ("sent", "baseline"):
        return
    needed_by = next_business_day(now.date())
    receivers = affected_workstreams(e)
    if not receivers:
        log("no Workstream matched", e["heading"])
    sent_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    # Director instance in the inbox (the Director is always a receiver).
    inst = rec.get("director_instance") or f"{ROUTE}-{now.strftime('%Y%m%d%H%M')}-{e['key'][:6]}"
    rec["director_instance"] = inst
    pending = []
    for r in receivers:
        if rec["instances"].get(r["sessionId"], {}).get("sent_at"):
            continue
        ri = f"{inst}-{r['sessionId'][:8]}"
        try:
            fc(
                "post_message",
                {"sessionId": r["sessionId"], "text": handoff_text(e, ri, needed_by, r["title"])},
            )
            rec["instances"][r["sessionId"]] = {
                "instance": ri,
                "title": r["title"],
                "sent_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            }
            log("sent", ri, "to", r["title"])
            save_state(state)
        except Exception as ex:
            pending.append(r["title"])
            rec["instances"][r["sessionId"]] = {
                "instance": ri,
                "title": r["title"],
                "sent_at": None,
                "error": type(ex).__name__ + " " + str(ex)[:120],
            }
            log("post_message failed", r["title"], type(ex).__name__, str(ex)[:120])
    if not rec.get("inbox_sent_at"):
        builders = (
            "; ".join(
                f"{v['title']} ({v['instance']}, {'sent ' + v['sent_at'] if v.get('sent_at') else 'NOT SENT, retrying'})"
                for v in rec["instances"].values()
            )
            or "none matched by find_owner"
        )
        lines = [
            f"{e['heading']}"
            + (" (TEST transmission proof, not a real decision)" if is_test(e) else ""),
            f"What. {re.sub(chr(10) + '+', ' ', e['body'])[:700]}",
            "For. AI Experience Director, plus the affected build owners listed below.",
            "What to do. Fold this decision into the Human Experience Standard, Creative Taste Profile and Pattern Library where it applies, then mark this instance picked up.",
            f"By when. Pick up by {needed_by.strftime('%A %B %-d, %Y')} end of day America/Chicago.",
            f"Source. {DL_URL}",
            f"Build owners sent the same handoff. {builders}",
            "HANDOFF INSTANCE BEGIN v2",
            f"route_id={ROUTE}",
            f"instance_id={inst}",
            f"item={e['heading']}",
            "for=AI Experience Director",
            "receiver_action=Fold into the Human Experience Standard and confirm pickup",
            f"needed_by={needed_by.isoformat()} 17:00 America/Chicago",
            f"source_link={DL_URL}",
            f"sent_at={sent_at}",
            "HANDOFF INSTANCE END",
        ]
        rev = inbox_insert_after_heading("Entries", lines)
        rec["inbox_sent_at"] = sent_at
        rec["inbox_revision"] = rev
        log("inbox instance", inst, "revision", rev)
        save_state(state)
    rec["status"] = "sent" if not pending else "partial"
    rec["sent_at"] = rec.get("sent_at") or sent_at


def relay_pickups(state):
    """Copy receiver pickups replied in Factory sessions into the inbox."""
    open_items = [
        (k, sid, v)
        for k, rec in state["entries"].items()
        for sid, v in rec.get("instances", {}).items()
        if v.get("sent_at") and not v.get("picked_up")
    ]
    if not open_items:
        return
    itext = inbox_text()
    for k, sid, v in open_items:
        inst = v["instance"]
        m = re.search(rf"PICKED UP {ROUTE} by [^\n]*instance_id={re.escape(inst)}", itext)
        if m:
            v["picked_up"] = m.group(0)
            continue
        try:
            msgs = (
                fc("read_messages", {"sessionId": sid, "limit": 30, "role": "assistant"}) or {}
            ).get("messages", [])
        except Exception as ex:
            log("read_messages failed", sid[:8], type(ex).__name__)
            continue
        for msg in msgs:
            mm = re.search(
                rf"PICKED UP {ROUTE} by [^\n]*instance_id={re.escape(inst)}", msg.get("text", "")
            )
            if mm:
                line = (
                    mm.group(0).strip()
                    + f" (relayed by the experience watcher from Factory session {sid}, message {msg.get('id')}, {msg.get('at')})"
                )
                # The receiver's pickup lands under the Director instance, which carries the build-owner instance ids.
                parent = state["entries"][k].get("director_instance")
                inbox_add_pickup(parent, line)
                v["picked_up"] = line
                log("pickup relayed", inst)
                break


def run_watch():
    now = dt.datetime.now(CT)
    state = load_state()
    meta = gws.api(
        f"https://www.googleapis.com/drive/v3/files/{DECISION_LOG}?fields=version,modifiedTime&supportsAllDrives=true"
    )
    if meta.get("version") != state.get("dl_version") or any(
        r.get("status") == "partial" for r in state["entries"].values()
    ):
        for e in entries():
            if is_experience(e):
                send(e, state, now)
                save_state(state)
        state["dl_version"] = meta.get("version")
    relay_pickups(state)
    state["last_watch"] = now.isoformat(timespec="seconds")
    save_state(state)


def fold_into_standard(state, new_entries):
    if not STANDARD or not new_entries:
        return 0
    doc = gws.get_doc(STANDARD)
    text = "".join(t for _, t in _paras(doc))
    heading = "Logged since the last Director pass"
    idx = None
    for el, t in _paras(doc):
        if t.strip() == heading:
            idx = el["endIndex"]
    added = 0
    for e in new_entries:
        if e["heading"] in text:
            continue
        para = (
            f"Approved standard. {re.sub(chr(10) + '+', ' ', e['body'])[:1200]} "
            f"Source. {e['heading']}. Added automatically by the daily reconciliation, pending the AI Experience Director's pattern write-up.\n"
        )
        if idx is None:
            end = doc["body"]["content"][-1]["endIndex"] - 1
            block = heading + "\n"
            gws.batch_update(
                STANDARD,
                [
                    {"insertText": {"location": {"index": end}, "text": block}},
                    {
                        "updateParagraphStyle": {
                            "range": {"startIndex": end, "endIndex": end + len(block)},
                            "paragraphStyle": {"namedStyleType": "HEADING_2"},
                            "fields": "namedStyleType",
                        }
                    },
                ],
            )
            idx = end + len(block)
        gws.batch_update(
            STANDARD,
            [
                {"insertText": {"location": {"index": idx}, "text": para}},
                {
                    "updateParagraphStyle": {
                        "range": {"startIndex": idx, "endIndex": idx + len(para)},
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        "fields": "namedStyleType",
                    }
                },
            ],
        )
        idx += len(para)
        state["entries"][e["key"]]["folded"] = True
        added += 1
    return added


def unconfirmed_section(state, now):
    rows = []
    for rec in state["entries"].values():
        for v in rec.get("instances", {}).values():
            if not v.get("sent_at") or v.get("picked_up"):
                continue
            sent = dt.datetime.fromisoformat(v["sent_at"]).astimezone(CT)
            due = sent + dt.timedelta(days=1)
            while due.weekday() >= 5:
                due += dt.timedelta(days=1)
            if now > due:
                rows.append(
                    f"UNCONFIRMED {v['instance']} to {v['title']}, sent {sent.strftime('%Y-%m-%d %H:%M %Z')}, item {rec['heading']}"
                )
    itext = inbox_text()
    for rec in state["entries"].values():
        inst = rec.get("director_instance")
        if (
            inst
            and rec.get("inbox_sent_at")
            and not re.search(rf"PICKED UP {ROUTE} by [^\n]*instance_id={re.escape(inst)}", itext)
        ):
            sent = dt.datetime.fromisoformat(rec["inbox_sent_at"]).astimezone(CT)
            if (now - sent).days >= 1:
                rows.append(
                    f"UNCONFIRMED {inst} to AI Experience Director, sent {sent.strftime('%Y-%m-%d %H:%M %Z')}, item {rec['heading']}"
                )
    return rows


def run_reconcile():
    now = dt.datetime.now(CT)
    state = load_state()
    es = entries()
    cutoff = now.date() - dt.timedelta(days=14)
    missed, fresh = 0, []
    for e in es:
        if not is_experience(e) or (e["date"] and e["date"] < cutoff):
            continue
        rec = state["entries"].get(e["key"])
        if not rec or rec.get("status") not in ("sent", "baseline"):
            send(e, state, now)
            save_state(state)
            missed += 1
        if (
            not is_test(e)
            and not state["entries"][e["key"]].get("folded")
            and state["entries"][e["key"]].get("status") != "baseline"
        ):
            fresh.append(e)
    relay_pickups(state)
    folded = fold_into_standard(state, fresh)
    rows = unconfirmed_section(state, now)
    summary = (
        f"Daily reconciliation {now.strftime('%Y-%m-%d %H:%M %Z')}. Missed entries sent now {missed}. "
        f"Decisions folded into the Standard {folded}. Unconfirmed handoffs older than one business day {len(rows)}."
    )
    inbox_insert_after_heading("Entries", [summary] + (rows or ["No unconfirmed handoffs."]))
    state["last_reconcile"] = now.isoformat(timespec="seconds")
    save_state(state)
    log(summary)


def run_baseline():
    state = load_state()
    n = 0
    for e in entries():
        if is_experience(e) and e["key"] not in state["entries"]:
            state["entries"][e["key"]] = {
                "heading": e["heading"],
                "status": "baseline",
                "instances": {},
            }
            n += 1
    state["dl_version"] = None
    save_state(state)
    log("baseline marked", n)


if __name__ == "__main__":
    import fcntl

    mode = sys.argv[1] if len(sys.argv) > 1 else "watch"
    os.makedirs(STATE_DIR, exist_ok=True)
    # One run at a time. A second run (overlapping schedule, manual run or a
    # reload mid-run) exits quietly instead of sending duplicates.
    lock = open(os.path.join(STATE_DIR, "run.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("another run holds the lock, skipping", mode)
        sys.exit(0)
    try:
        {"watch": run_watch, "reconcile": run_reconcile, "baseline": run_baseline}[mode]()
    except urllib.error.HTTPError as ex:
        log("HTTP error", ex.code, ex.url.split("?")[0][:120])
        sys.exit(1)
