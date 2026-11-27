"""Reconcile a private Week Wrap preflight with its independently read inventories."""

import json
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
PACKAGE = {"advantage-brief", "run-of-show", "canva-chapter"}


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
    return gaps


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, RecursionError):
        print(json.dumps({"preflight": "blocked", "error": "invalid JSON"}))
        return 2
    gaps = validate(payload)
    print(json.dumps({"preflight": "blocked" if gaps else "passed", "gaps": gaps}))
    return bool(gaps)


if __name__ == "__main__":
    sys.exit(main())
