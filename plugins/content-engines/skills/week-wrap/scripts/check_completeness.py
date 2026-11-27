"""Reconcile a private Week Wrap preflight with its independently read inventories."""

import json
import re
import sys
from urllib.parse import urlsplit

STATUSES = {
    "readiness": {"Covered", "Test", "Finish", "Upgrade", "Build", "Skip"},
    "decisions": {"implemented", "routed"},
    "close": {"passed"},
    "tools": {"owned"},
    "sources": {"search", "have it", "create our own"},
    "session": {"verified"},
    "package": {"ready"},
}
WEEK_TEN = set(
    "engine wheels steering gas transmission dashboard maintenance brain-walkthrough".split()
)
PACKAGE = {
    "advantage-brief",
    "run-of-show",
    "canva-chapter",
    "presenter-notes",
    "internal-video",
    "canva-video-slide",
}
IDENTITIES = ("brand_book_id", "kit_id", "deck_id", "master_notes_id")
SCREENS = {"hub", "drive-brains", "ai-department-real-work"}
REDACTIONS = {
    "client-names",
    "deal-prices",
    "private-ag-personal",
    "passwords",
    "don-private-files",
}
STORY = ["before-after", "working-screen", "who-uses-it-and-how"]


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def link(value):
    if not nonblank(value):
        return False
    try:
        url = urlsplit(value)
        return url.scheme == "https" and bool(url.hostname) and url.username is None
    except ValueError:
        return False


def linked(row, *fields):
    return all(link(row.get(field)) for field in fields)


def package_gaps(key, row):
    fields = {}
    if key == "canva-chapter":
        fields.update(dict.fromkeys((*IDENTITIES, "owner"), nonblank))
        fields.update(
            dict.fromkeys(
                ("owner_url", "brand_url", "append_route_url", "master_notes_route_url"), link
            )
        )
    elif key == "presenter-notes":
        fields.update(dict.fromkeys(("notes_write_url", "notes_read_url"), link))
    elif key == "internal-video":
        fields.update(dict.fromkeys(("avatar_id", "voice_id"), nonblank))
        fields.update(
            voice_kind=lambda v: v == "professional", capture_machine=lambda v: v == "ember-m2"
        )
        fields.update(
            dict.fromkeys(
                (
                    "avatar_voice_url",
                    "capture_route_url",
                    "sanitization_route_url",
                    "renderer_route_url",
                    "internal_hub_route_url",
                ),
                link,
            )
        )
    elif key == "canva-video-slide":
        fields.update(
            dict.fromkeys(
                ("embed_route_url", "playback_route_url", "external_exclusion_route_url"), link
            )
        )
    return [field for field, check in fields.items() if not check(row.get(field))]


def validate(payload):
    if not isinstance(payload, dict) or payload.get("route") not in ("week", "session"):
        return [{"check": "input", "gap": "route must be week or session"}]

    is_week = payload["route"] == "week"
    week = payload.get("week")
    if is_week and (type(week) is not int or week < 0):
        return [{"check": "input", "gap": "a nonnegative week number is required"}]
    checks = payload.get("checks")
    if not isinstance(checks, dict):
        return [{"check": "input", "gap": "checks must be an object"}]

    names = ("readiness", "decisions", "close", "tools", "sources") if is_week else ("session",)
    gaps = []

    for name in (*names, "package"):
        check = checks.get(name)
        inventory_url = check.get("inventory_url") if isinstance(check, dict) else None

        def gap(message, key=None, url=None):
            gaps.append(
                {
                    "check": name,
                    "key": key,
                    "gap": message,
                    "url": url if link(url) else inventory_url if link(inventory_url) else None,
                }
            )

        if not link(inventory_url):
            gap("missing linked independent inventory")
            continue
        expected = check.get("expected")
        rows = check.get("evidence")
        if (
            not isinstance(expected, list)
            or not all(nonblank(key) and key == key.strip() for key in expected)
            or len(set(expected)) != len(expected)
            or not isinstance(rows, dict)
        ):
            gap("expected keys must be nonblank and unique, with a separate evidence object")
            continue
        required = {"package": PACKAGE, "session": {"intent", "source-review"}}.get(name, set())
        if name == "close":
            if week == 10:
                required = WEEK_TEN
            if not expected:
                gap("missing week close criteria")
        if name == "readiness":
            points = {key.partition(":")[2] for key in expected}
            per_company = {
                f"{company}:{point}"
                for company in ("HQ", "EP", "AG")
                for point in points
                if point.strip()
            }
            if not per_company or set(expected) - per_company:
                gap("readiness requires valid company-specific teaching-point keys")
            required = per_company
        for key in sorted(required - set(expected)):
            gap("required key missing from inventory", key)
        for key in sorted(rows.keys() - set(expected)):
            gap("evidence key is not reconciled to the inventory", key)
        for key in expected:
            row = rows.get(key)
            if not isinstance(row, dict):
                gap("missing evidence", key)
                continue
            status = row.get("status")
            url = row.get("url")
            valid = isinstance(status, str) and status in STATUSES[name] and link(url)
            if name in ("readiness", "sources"):
                valid = valid and nonblank(row.get("reason"))
            if name == "tools" or (name == "decisions" and status == "routed"):
                valid = valid and nonblank(row.get("owner"))
            if name == "decisions":
                valid = valid and link(row.get("receipt_url"))
            if not valid:
                gap("missing or invalid disposition, required fields or evidence link", key, url)
            elif name == "package" and (missing := package_gaps(key, row)):
                gap("missing or unverified " + ", ".join(missing), key, url)
    return gaps


def verify_saved(payload):
    """Validate private readback metadata, not vendor assets or self-written scripts."""
    gaps = validate(payload)
    if gaps:
        return gaps
    ready = payload["checks"]["package"]["evidence"]
    completion = payload.get("completion")
    if not isinstance(completion, dict):
        completion = {}
    rows = completion.get("evidence")
    rows = rows if isinstance(rows, dict) else {}
    chapter = rows.get("canva-chapter")
    chapter = chapter if isinstance(chapter, dict) else {}
    expected_pages = chapter.get("page_ids")
    page_ids = (
        set(expected_pages)
        if isinstance(expected_pages, list) and all(nonblank(p) for p in expected_pages)
        else set()
    )
    video = rows.get("internal-video")
    video = video if isinstance(video, dict) else {}
    audience = {"don", "team", "future-human-hires", "future-ai-hires"}

    def covers(value, required):
        return (
            isinstance(value, list) and all(nonblank(x) for x in value) and set(value) == required
        )

    def issue(key, message, url=None):
        gaps.append(
            {
                "check": "completion",
                "key": key,
                "gap": message,
                "url": url if link(url) else ready.get(key, {}).get("url"),
            }
        )

    if not linked(completion, "run_log_url"):
        issue("run-log", "saved private run-log receipt is missing")
    if not linked(completion, "preflight_receipt_url"):
        issue("preflight", "saved prewrite gate receipt is missing")
    for key in sorted(PACKAGE):
        row = rows.get(key)
        if not isinstance(row, dict) or not linked(row, "url", "readback_url"):
            issue(key, "saved artifact and independent readback links required")
            continue
        if key == "advantage-brief":
            ok = type(row.get("rendered_pages")) is int and row["rendered_pages"] == 1
        elif key == "run-of-show":
            ok = row.get("timing_reconciled") is True
        elif key == "canva-chapter":
            title = row.get("title")
            ok = (
                nonblank(title)
                and not re.search(r"\b(?:week|wk)[\s#-]*\d+", title, re.I)
                and row.get("source_week_visible") is False
                and (payload["route"] != "week" or row.get("source_week_in_master_notes") is True)
                and row.get("prior_chapters_preserved") is True
                and linked(row, "master_notes_url")
                and all(row.get(f) == ready[key][f] for f in IDENTITIES)
                and bool(page_ids)
                and len(page_ids) == len(expected_pages)
            )
        elif key == "presenter-notes":
            scripts = row.get("pages")
            ok = (
                isinstance(scripts, dict)
                and bool(page_ids)
                and scripts.keys() == page_ids
                and all(
                    isinstance(script, dict)
                    and linked(script, "readback_url")
                    and script.get("full_read_as_is_script") is True
                    and script.get("actual_canva_notes_match") is True
                    for script in scripts.values()
                )
            )
        elif key == "internal-video":
            duration = row.get("duration_seconds")
            ok = (
                nonblank(row.get("video_id"))
                and row.get("provider") == "heygen"
                and row.get("intent") == "production"
                and type(duration) in (int, float)
                and 0 < duration <= 180
                and row.get("capture_machine") == "ember-m2"
                and row.get("working_recording") is True
                and row.get("internal_only") is True
                and type(row.get("chapter_video_count")) is int
                and row["chapter_video_count"] == 1
                and all(row.get(f) == ready[key][f] for f in ("avatar_id", "voice_id"))
                and covers(row.get("screens"), SCREENS)
                and covers(row.get("redactions_verified"), REDACTIONS)
                and covers(row.get("audience"), audience)
                and row.get("sequence") == STORY
                and linked(
                    row,
                    "hub_url",
                    "capture_receipt_url",
                    "redaction_receipt_url",
                    "media_playback_url",
                    "internal_access_receipt_url",
                )
            )
        else:
            ok = (
                nonblank(video.get("video_id"))
                and row.get("video_id") == video["video_id"]
                and nonblank(row.get("page_id"))
                and row["page_id"] in page_ids
                and row.get("deck_id") == ready["canva-chapter"]["deck_id"]
                and row.get("dedicated_slide") is True
                and row.get("playback_verified") is True
                and row.get("external_exclusion_verified") is True
                and row.get("notes_what_and_when") is True
                and linked(row, "playback_url", "external_exclusion_url")
            )
        if not ok:
            issue(key, "saved readback does not meet the package contract", row["readback_url"])
    return gaps


def main():
    if sys.argv[1:] not in ([], ["--saved"]):
        print(json.dumps({"error": "expected no arguments or --saved"}))
        return 2
    phase = "completion" if sys.argv[1:] else "preflight"
    try:
        payload = json.load(sys.stdin)
    except (ValueError, RecursionError):
        print(json.dumps({phase: "blocked", "error": "invalid JSON"}))
        return 2
    gaps = verify_saved(payload) if phase == "completion" else validate(payload)
    print(json.dumps({phase: "blocked" if gaps else "passed", "gaps": gaps}))
    return bool(gaps)


if __name__ == "__main__":
    sys.exit(main())
