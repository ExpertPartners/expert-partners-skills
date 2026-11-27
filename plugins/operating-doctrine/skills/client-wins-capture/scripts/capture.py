"""Plan private case capture and reconcile observed arrivals. No network or secrets."""

import hashlib
import json
import re
import sys
from datetime import datetime
from urllib.parse import urlparse


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def capture(data):
    sources = data.get("sources", [])
    source_ids = [s["id"] for s in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("duplicate source configuration")
    failed = [s["id"] for s in sources if s.get("status") != "ok" or s.get("complete") is not True]
    destinations = {}
    for destination in data.get("destinations", []):
        company = destination["company"]
        if company in destinations:
            raise ValueError("ambiguous company destination")
        destinations[company] = destination
    destination_gaps = [
        company
        for company, destination in destinations.items()
        if company not in {"EP", "AG"}
        or not destination.get("folder")
        or any(destination.get(f) is not True for f in ("verified", "private", "access_preserved"))
    ]
    observed = {}
    for file in data.get("files", []):
        observed.setdefault(file["key"], []).append(file)
    actions, blocked, excluded, missing, unchanged = [], [], [], [], []
    seen = {}
    for record in data.get("records", []):
        source, source_id = record.get("source"), record.get("id")
        key = digest([source, source_id])
        if key in seen:
            if record != seen[key]:
                raise ValueError("conflicting records for one source key")
            continue
        seen[key] = record
        if record.get("fixture") is True or re.search(
            r"\blorem ipsum\b", record.get("quote", ""), re.I
        ):
            excluded.append({"key": key, "reason": "fixture"})
            continue
        if record.get("kind") not in {"client_win", "testimonial", "review"}:
            excluded.append({"key": key, "reason": "not_client_evidence"})
            continue
        reason = None
        required = ("id", "person", "quote", "date", "url")
        if any(not isinstance(record.get(f), str) or not record[f].strip() for f in required):
            reason = "missing_attribution"
        try:
            datetime.fromisoformat(record.get("date", "").replace("Z", "+00:00"))
            url = urlparse(record.get("url", ""))
            if url.scheme != "https" or not url.netloc or url.username or url.password:
                reason = "invalid_source_link"
        except (ValueError, TypeError):
            reason = "invalid_date"
        company = record.get("company")
        destination = destinations.get(company, {})
        if source not in source_ids or source in failed:
            reason = "source_incomplete"
        elif company not in {"EP", "AG"} or not destination.get("folder"):
            reason = "destination_missing"
        elif any(
            destination.get(f) is not True for f in ("verified", "private", "access_preserved")
        ):
            reason = "destination_unsafe"
        consent = record.get("consent", "unknown")
        if consent not in {"unknown", "internal_only", "granted", "revoked"}:
            reason = "invalid_consent"
        if consent == "granted" and not record.get("consent_evidence", "").strip():
            reason = "missing_consent_evidence"
        files = observed.get(key, [])
        if len(files) > 1:
            reason = "duplicate_destination_key"
        if files and (
            files[0].get("verified") is not True
            or files[0].get("folder") != destination.get("folder")
            or not files[0].get("id")
        ):
            reason = "unverified_existing_file"
        if reason:
            blocked.append({"key": key, "reason": reason})
            continue
        case = {f: record[f] for f in required}
        case.update(
            company=company,
            source=source,
            kind=record["kind"],
            consent=consent,
            consent_evidence=record.get("consent_evidence", ""),
            visibility="permission_on_record" if consent == "granted" else "internal_only",
        )
        revision = digest(case)
        if files and files[0].get("revision") == revision:
            unchanged.append(key)
            continue
        missing.append(key)
        action = {
            "action": "update" if files else "create",
            "key": key,
            "revision": revision,
            "folder": destination["folder"],
            "case": case,
        }
        if files:
            action["file_id"] = files[0]["id"]
        actions.append(action)
    return {
        "complete": bool(sources)
        and bool(destinations)
        and not (failed or destination_gaps or blocked or missing),
        "failed_sources": failed,
        "destination_gaps": destination_gaps,
        "actions": actions,
        "blocked": blocked,
        "excluded": excluded,
        "unchanged": unchanged,
        "missing_arrivals": missing,
        "eligible": len(actions) + len(unchanged),
    }


if __name__ == "__main__":
    try:
        print(json.dumps(capture(json.load(sys.stdin)), ensure_ascii=False))
    except (ValueError, KeyError, TypeError, AttributeError):
        print(json.dumps({"complete": False, "error": "invalid_capture_input"}))
        sys.exit(1)
