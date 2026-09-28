#!/usr/bin/env python3
"""evaluate_site_record.py -- run Visual Clearance over an application's own photo record.

Part of the visual-clearance skill. Reads a website's existing candidate and
clearance record IN PLACE, at a pinned revision, and evaluates every candidate
for every placement it names. It never writes to the owner's repository, never
copies the record into a second register, and never changes a status there.
Output is a dated evaluation: identity grade, rights state, per-placement
technical fit (observed web dimensions kept separate from the usable crop),
one NEXT action, the specific missing evidence, and permission-request
fill-ins grouped by the owner's recorded contact route.

Supported record shape: the AG Luxury website's
docs/evidence/community-photo-candidates-2026-09-28.json (ag-luxury-site).
Placement minimums come from the record's own targetCrops; the skill's
consumer profiles must match them or the run fails with an owner-drift error.

Usage:
  evaluate_site_record.py --record FILE --revision SHA [--as-of YYYY-MM-DD]
                          [--profiles DIR] [--json]
Exit status: 0 evaluated, 2 owner-record drift or unsupported record.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from clearance_rules import ACTION_RANK, RuleError, decide  # noqa: E402
from fit_check import evaluate as fit_evaluate, load_profile  # noqa: E402

DEFAULT_PROFILES = HERE.parent / "profiles"
PLACEMENTS = {
    "directory": "ag-luxury-guide-directory",
    "hero": "ag-luxury-community-hero",
    "midGuide": "ag-luxury-guide-mid",
}
CROP_SPEC = re.compile(r"^\s*(\d+):(\d+)(\s+or wider)?,\s*at least\s+(\d+)\s*x\s*(\d+)\s*$", re.I)

# Identity mapping, conservative and recorded per candidate. Placement-only
# language is checked first: an image appearing on a page is not evidence.
PAGE_ONLY = re.compile(r"groups this photograph under|uses this image for|is served by|not independently captioned|not captioned", re.I)
CAPTIONED = re.compile(r"\b(labels?|labeled|calls this|identif(?:y|ies|ied)|places this)\b|visibly shows .*\bsign\b", re.I)


class DriftError(Exception):
    pass


def parse_crop(spec: str) -> dict:
    match = CROP_SPEC.match(spec or "")
    if not match:
        raise DriftError(f"unrecognized placement requirement {spec!r}")
    aw, ah, wider, w, h = match.groups()
    return {"aspect": (int(aw), int(ah)), "mode": "min" if wider else "exact", "min": (int(w), int(h))}


def check_profiles(record: dict, profiles: dict) -> None:
    for cand in record["candidates"]:
        for key, spec in (cand.get("targetCrops") or {}).items():
            if key not in PLACEMENTS:
                raise DriftError(f"{cand['slug']}: unknown placement {key!r}; add a profile before evaluating")
            want = parse_crop(spec)
            prof = profiles[key]
            have = {
                "aspect": (prof["aspect_ratio"]["w"], prof["aspect_ratio"]["h"]),
                "mode": prof.get("aspect_mode", "exact"),
                "min": (prof["min_crop_px"]["w"], prof["min_crop_px"]["h"]),
            }
            if want != have:
                raise DriftError(f"{cand['slug']}: owner requires {key} {spec!r} but profile {prof['profile_id']} has {have}; update the consumer profile to the owner's value")


def identity_evidence(cand: dict) -> tuple[list[dict], str]:
    text = cand.get("identityEvidence") or ""
    if PAGE_ONLY.search(text):
        return [{"type": "page_placement", "detail": text}], "page placement only"
    if CAPTIONED.search(text):
        return [{"type": "source_metadata", "detail": text, "pointer": cand.get("sourcePage")}], "caption or listing identification"
    return [{"type": "page_placement", "detail": text}], "no caption language recognized"


def is_mls(cand: dict) -> bool:
    blob = " ".join(str(cand.get(k) or "") for k in ("sourceKind", "identityEvidence", "marketingContactEvidence"))
    return cand.get("sourceKind") == "listing" or bool(re.search(r"\bMLS\b", blob))


def to_candidate(cand: dict) -> dict:
    evidence, rule = identity_evidence(cand)
    mls = is_mls(cand)
    terms = cand.get("realtorLibraryTerms") or ""
    flags = []
    if mls:
        flags.append({"flag": "identifiable_home", "resolved": False, "note": "listing photo of a private residence"})
    if re.search(r"\bsign\b", f"{cand.get('identityEvidence', '')} {cand.get('subject', '')}", re.I):
        flags.append({"flag": "trademark_logo", "resolved": False, "note": "sign visible in frame"})
    dims = cand.get("observedPixelDimensions") or {}
    return {
        "candidate_id": cand["slug"],
        "subject": f"{cand.get('title')}: {cand.get('subject')}",
        "source": cand.get("sourcePublisher"),
        "source_class": "mls_listing" if mls else "owner_permission",
        "creator": None,
        "source_url": cand.get("sourcePage"),
        "dimensions": {"w": dims.get("width"), "h": dims.get("height")},
        "dimensions_basis": "observed_web",
        "capture_date": None,
        "location": {"evidence": evidence},
        "identity_rule": rule,
        "rights": {
            "basis": "downloadable" if cand.get("realtorLibrary") and "download" in terms.lower() else "visible_online",
            "commercial_use": "unknown",
            "modification": "unknown",
            "conditions": [],
            "scope_covers_use": "unknown",
            "mls": {"own_listing": False} if mls else None,
        },
        "third_party_flags": flags,
        "owner_contact_route": "publisher" if cand.get("marketingContact") else None,
    }


def missing_evidence(cand: dict, decision: dict, fits: dict, mls: bool) -> dict:
    grade = decision["location"]["grade"]
    title = cand.get("title")
    identity = []
    if grade == "UNVERIFIED":
        identity.append(f"a caption or written owner confirmation that the frame shows {title} (A)")
        identity.append(f"a landmark or scene match against an official {title} source (C)")
    elif grade == "PROBABLE":
        identity.append(f"a landmark or scene match against an official {title} source or map view (C or D), an AI evidence task")
    rights = []
    if mls:
        rights += [
            "the listing photographer's license covering website marketing outside that listing",
            "the property owner's consent (the listing is not Allison's)",
            "a guide image that shows the community rather than one identifiable residence is the stronger path",
        ]
    else:
        rights.append("a written grant naming Allison Gaddy and agluxurytx.com for the directory card, guide hero and mid-guide image, with crop permission, credit line and duration")
        if "Not credited" in (cand.get("photographer") or ""):
            rights.append("who owns the photograph, since no photographer is credited and the publisher may not hold the rights")
    if cand.get("realtorLibraryTerms"):
        rights.append("independent-website scope beyond the Realtor resource terms, which retain ownership")
    resolution = []
    for key, fit in fits.items():
        if fit["insufficient_resolution"]:
            req = fit["required_crop_px"]
            resolution.append(f"{key}: observed {fit['source']['w']}x{fit['source']['h']} gives a {fit['crop']['w']}x{fit['crop']['h']} crop; needs at least {req['w']}x{req['h']}")
    return {"identity": identity, "rights": rights, "resolution": resolution}


def evaluate(record: dict, revision: str, as_of: dt.date, profiles_dir: Path = DEFAULT_PROFILES) -> dict:
    if "candidates" not in record or not isinstance(record["candidates"], list):
        raise DriftError("unsupported record shape: no candidates list")
    profiles = {key: load_profile(profiles_dir / f"{pid}.json") for key, pid in PLACEMENTS.items()}
    check_profiles(record, profiles)
    request = {"represents_named_place": True, "use_contexts": ["website"], "modifications": ["crop"], "commercial": True}
    rows = []
    for cand in record["candidates"]:
        candidate = to_candidate(cand)
        dims = candidate["dimensions"]
        fits, actions = {}, {}
        for key in (cand.get("targetCrops") or {}):
            fit = fit_evaluate(dims["w"], dims["h"], profiles[key])
            fits[key] = fit
            try:
                actions[key] = decide(candidate, {**request, "subject": cand.get("title")}, fit, as_of)
            except RuleError as exc:
                actions[key] = {"next_action": "REVIEW PENDING", "reasons": [str(exc)]}
        primary = min(actions.values(), key=lambda d: ACTION_RANK.get(d["next_action"], 99))
        rows.append({
            "slug": cand["slug"],
            "title": cand.get("title"),
            "publisher": cand.get("sourcePublisher"),
            "source_page": cand.get("sourcePage"),
            "contact_route_key": cand.get("marketingContact"),
            "identity_rule": candidate["identity_rule"],
            "location_grade": primary["location"]["grade"],
            "rights_state": primary["rights"]["state"],
            "rights_basis": primary["rights"]["basis"],
            "mls": candidate["source_class"] == "mls_listing",
            "observed": dims,
            "placements": {
                key: {
                    "crop": f"{fit['crop']['w']}x{fit['crop']['h']}",
                    "required": f"{fit['required_crop_px']['w']}x{fit['required_crop_px']['h']}",
                    "resolution_ok": not fit["insufficient_resolution"],
                    "next_action": actions[key]["next_action"],
                }
                for key, fit in fits.items()
            },
            "next_action": primary["next_action"],
            "exact_use_cleared": any(a.get("exact_use_cleared") for a in actions.values()),
            "risk_flags": primary.get("risk_flags", []),
            "human_gates": primary.get("human_gates", []),
            "missing": missing_evidence(cand, primary, fits, candidate["source_class"] == "mls_listing"),
        })
    groups: dict = {}
    for row in rows:
        if row["next_action"] == "REQUEST PERMISSION" and row["contact_route_key"]:
            groups.setdefault(row["contact_route_key"], []).append(row)
    return {
        "owner_record": "ExpertPartners/ag-luxury-site docs/evidence/community-photo-candidates-2026-09-28.json",
        "revision": revision,
        "as_of": as_of.isoformat(),
        "candidates": rows,
        "request_groups": [
            {"publisher": grp[0]["publisher"], "slugs": [r["slug"] for r in grp]} for grp in groups.values()
        ],
        "counts": {
            "total": len(rows),
            "verified": sum(r["location_grade"] == "VERIFIED" for r in rows),
            "probable": sum(r["location_grade"] == "PROBABLE" for r in rows),
            "unverified": sum(r["location_grade"] == "UNVERIFIED" for r in rows),
            "exact_use_cleared": sum(r["exact_use_cleared"] for r in rows),
            "by_action": {a: sum(r["next_action"] == a for r in rows) for a in sorted({r["next_action"] for r in rows})},
        },
    }


def render_markdown(result: dict) -> str:
    c = result["counts"]
    lines = [
        f"Owner record: `{result['owner_record']}` at `{result['revision']}`, evaluated {result['as_of']}.",
        f"{c['total']} candidates. Location VERIFIED {c['verified']}, PROBABLE {c['probable']}, UNVERIFIED {c['unverified']}. Exact-use cleared {c['exact_use_cleared']}. NEXT actions {c['by_action']}.",
        "",
        "| Guide | Identity | Rights | Observed | Directory 4:3 | Hero 16:9 + mobile | Mid-guide 3:2+ | NEXT |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in result["candidates"]:
        cells = []
        for key in ("directory", "hero", "midGuide"):
            p = r["placements"].get(key)
            cells.append("n/a" if not p else f"{p['crop']} {'ok' if p['resolution_ok'] else 'needs ' + p['required']}")
        rights = r["rights_state"] + (" (MLS)" if r["mls"] else "")
        lines.append(f"| {r['title']} | {r['location_grade']} | {rights} | {r['observed']['w']}x{r['observed']['h']} | {cells[0]} | {cells[1]} | {cells[2]} | {r['next_action']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--record", required=True)
    parser.add_argument("--revision", required=True, help="the owner revision actually read")
    parser.add_argument("--as-of")
    parser.add_argument("--profiles", default=str(DEFAULT_PROFILES))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    as_of = dt.date.fromisoformat(args.as_of) if args.as_of else dt.date.today()
    try:
        result = evaluate(json.loads(Path(args.record).read_text(encoding="utf-8")), args.revision, as_of, Path(args.profiles))
    except DriftError as exc:
        print(f"OWNER RECORD DRIFT: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else render_markdown(result), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
