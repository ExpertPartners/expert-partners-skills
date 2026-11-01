"""One Markdown report per hunt.

The report lists every route tried, what each found, and what is still
missing. It never quotes recovered text, because course text is confidential.
It points to the evidence files instead.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from evidence import REPORT_FILE, Hunt, now_iso
from stitch import normalize


def text_contains(want: str, text: str, threshold: float = 0.85) -> bool:
    """True when want appears in text, allowing small OCR misreads."""
    target = normalize(want)
    if not target:
        return False
    if target in normalize(text):
        return True
    size = len(target.split())
    for line in text.splitlines():
        words = normalize(line).split()
        for start in range(0, max(1, len(words) - size + 1)):
            window = " ".join(words[start:start + size])
            if window and SequenceMatcher(None, target, window, autojunk=False).ratio() >= threshold:
                return True
    return False


def where_found(hunt: Hunt, want: str, routes: list[dict]) -> list[str]:
    hits = []
    for route in routes:
        for rel in route.get("text_files") or []:
            path = hunt.root / rel
            if path.is_file() and text_contains(want, path.read_text(encoding="utf-8", errors="replace")):
                hits.append(f"route {route['number']} ({route['route']}), in {rel}")
    return hits


def build_report(hunt: Hunt) -> str:
    routes = hunt.routes()
    wants = hunt.meta.get("wants") or []
    lines = [
        f"# Source hunt report, {hunt.name}", "",
        f"Evidence folder: {hunt.root}",
        f"Hunt started: {hunt.meta.get('created_at', '')}",
        f"Report written: {now_iso()}",
        f"Routes tried: {len(routes)}", "",
        "This report lists routes and results only. It does not quote recovered course text. "
        "Read that text in the evidence files named below, and paraphrase it when you share it.", "",
        "## What we were looking for", "",
    ]
    still_missing = []
    if not wants:
        lines.append("No sought items were named for this hunt, so none can be checked off. Add them with --want.")
    for want in wants:
        hits = where_found(hunt, want, routes)
        if hits:
            lines.append(f"- {want}, found by " + "; ".join(hits))
        else:
            lines.append(f"- {want}, still missing")
            still_missing.append(f"{want}, not found by any route tried")
    lines += ["", "## Routes tried", ""]
    if not routes:
        lines.append("No routes have been tried yet.")
    for route in routes:
        lines += [f"### Route {route['number']}, {route['route']}", "",
                  f"- Target: {route.get('target', '')}",
                  f"- When: {route.get('recorded_at', '')}",
                  f"- Result: {route.get('status', 'unknown')}"]
        if route.get("method"):
            lines.append(f"- Method: {route['method']}")
        lines.append("- What it found:" if route.get("found") else "- What it found: nothing")
        lines += [f"  - {item}" for item in route.get("found") or []]
        if route.get("missing"):
            lines.append("- Still missing from this route:")
            lines += [f"  - {item}" for item in route["missing"]]
        if route.get("problems"):
            lines.append("- Problems:")
            lines += [f"  - {item}" for item in route["problems"]]
        if route.get("evidence"):
            lines.append("- Evidence files:")
            lines += [f"  - {item}" for item in route["evidence"]]
        lines.append("")
        for item in route.get("missing") or []:
            still_missing.append(f"route {route['number']} ({route['route']}, {route.get('target', '')}), {item}")
    lines += ["## Still missing", ""]
    if still_missing:
        lines += [f"- {item}" for item in still_missing]
    elif wants:
        lines.append("Nothing. Every sought item was found and no route reported a gap.")
    else:
        lines.append("No route reported a gap. No sought items were named, so this is not a full check.")
    notes = hunt.meta.get("notes") or []
    if notes:
        lines += ["", "## Notes", ""]
        lines += [f"- {n['at']}, {n['note']}" for n in notes]
    return "\n".join(lines).rstrip() + "\n"


def write_report(hunt: Hunt):
    return hunt.write_text(REPORT_FILE, build_report(hunt))
