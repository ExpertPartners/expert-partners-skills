#!/usr/bin/env python3
"""clearance_rules.py -- the deterministic gates of the visual-clearance skill.

Imported by render_cards.py and validate_record.py, and runnable on its own
against a request plus candidates JSON file. It encodes the rules that must
never bend to a confident-sounding search result:

  * location grades come from recorded evidence only; a claimed grade is
    never allowed to exceed what the evidence supports
  * rights bases are distinct categories and are never collapsed; a rights
    pass alone is RIGHTS CLEAR, and only a candidate that also passes identity,
    third-party and technical gates is EXACT-USE CLEARED and may be USE;
    attribution never cures a license or scope failure
  * insufficient resolution is surfaced as its own flag
  * generated imagery never depicts a real named place
  * every outward or spending action is human-gated and never auto-executes
  * zero defensible candidates is a valid, reportable outcome

This is a risk assessment on recorded evidence, not legal advice.

Usage:
  clearance_rules.py EVALUATION.json    JSON decisions on stdout
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

LOCATION_STATES = ("REJECT", "UNVERIFIED", "PROBABLE", "VERIFIED")
LOCATION_RANK = {state: rank for rank, state in enumerate(LOCATION_STATES)}

# Evidence ladder A-F from the protocol, plus the two non-evidence labels.
EVIDENCE_TYPES = {
    "source_metadata": "A",
    "embedded_gps": "B",
    "landmark_match_official": "C",
    "map_corroboration": "D",
    "independent_corroboration": "E",
    "reverse_image_earliest": "F",
}
# page_placement: an image merely appearing on a neighborhood, agent or developer page.
NON_EVIDENCE = {"search_label", "ai_inference", "page_placement"}
CONTRADICTION = "contradiction"

# Rights bases. Distinct on purpose; none of them is by itself exact-use clearance.
RIGHTS_BASES = (
    "visible_online",
    "downloadable",
    "royalty_free",
    "creative_commons",
    "public_domain",
    "free_commercial_platform",
    "paid_commercial_license",
    "written_permission",
    "owned_or_work_for_hire",
    "unknown",
)
NO_RIGHTS_BASES = {
    "visible_online": "visible online grants no rights",
    "downloadable": "downloadable describes access, not permission",
    "unknown": "no rights basis established",
}
NO_RIGHTS_SOURCES = {
    "map_imagery": "map and street-level imagery terms forbid storing or republishing it; use for viewing-only verification",
    "social_media": "platform terms license the image to the platform, not to us; treat only as a lead to the photographer",
}

NEXT_ACTIONS = ("USE", "LICENSE", "REQUEST PERMISSION", "COMMISSION", "REJECT")
ACTION_RANK = {action: rank for rank, action in enumerate(NEXT_ACTIONS)}
OUTWARD_ACTIONS = {"REQUEST PERMISSION", "LICENSE", "COMMISSION"}
AD_OR_PRINT = {"advertising", "print"}
SENSITIVE_FLAGS = {
    "people": "recognizable people need releases before advertising use",
    "trademark_logo": "logo or monument sign can imply endorsement",
    "identifiable_home": "identifiable private home raises privacy and endorsement concerns",
    "architecture": "architectural work concern needs review",
    "private_property": "private property shown",
    "artwork": "third-party artwork shown",
    "security_features": "security features visible",
}
AI_ACTORS = re.compile(r"\b(ai|claude|gpt|chatgpt|grok|perplexity|gemini|codex|skill|bot|agent|model|visual clearance)\b", re.I)
CURRENCY_YEARS = 3


class RuleError(Exception):
    pass


def today_from(value: str | None) -> dt.date:
    return dt.date.fromisoformat(value) if value else dt.date.today()


# ---------------------------------------------------------------- location


def grade_location(evidence: list[dict], claimed: str | None = None) -> dict:
    """Grade from recorded evidence. Labels and inference count for nothing."""
    counted, ignored, notes = set(), [], []
    contradicted = False
    for item in evidence or []:
        kind = item.get("type")
        recorded = bool((item.get("detail") or "").strip() or (item.get("pointer") or "").strip())
        if kind == CONTRADICTION and recorded:
            contradicted = True
        elif kind in EVIDENCE_TYPES and recorded:
            counted.add(EVIDENCE_TYPES[kind])
        elif kind in EVIDENCE_TYPES:
            ignored.append(f"{kind} has no recorded detail or pointer")
        elif kind in NON_EVIDENCE:
            ignored.append(f"{kind} is not evidence")
        else:
            ignored.append(f"unknown evidence type {kind!r}")

    if contradicted:
        grade = "REJECT"
    elif "C" in counted and counted & {"A", "D", "E"}:
        grade = "VERIFIED"
    elif counted & {"A", "B", "C", "D", "E"}:
        grade = "PROBABLE"
    else:
        grade = "UNVERIFIED"

    violation = None
    if claimed:
        if claimed not in LOCATION_RANK:
            violation = f"claimed grade {claimed!r} is not a location state"
        elif claimed != "REJECT" and LOCATION_RANK[claimed] > LOCATION_RANK[grade]:
            violation = f"claimed {claimed} but recorded evidence supports only {grade}; grade stays {grade}"
    if violation:
        notes.append(violation)
    return {
        "grade": grade,
        "evidence_classes": sorted(counted),
        "ignored": ignored,
        "grade_violation": violation,
        "notes": notes,
    }


def currency_flag(capture_date: str | None, today: dt.date) -> str | None:
    if not capture_date:
        return "currency: capture date unknown"
    try:
        year = int(str(capture_date)[:4])
    except ValueError:
        return "currency: capture date unreadable"
    if today.year - year > CURRENCY_YEARS:
        return f"currency: captured {year}, more than {CURRENCY_YEARS} years old; the place may have changed"
    return None


# ------------------------------------------------------------------ rights


def compose_attribution(candidate: dict) -> str | None:
    rights = candidate.get("rights", {})
    creator = (candidate.get("creator") or "").strip()
    license_id = (rights.get("license_id") or "").strip()
    if not creator or not license_id:
        return None
    source = (candidate.get("source") or "").strip()
    text = f"Photo: {creator}, {license_id}"
    return f"{text}, via {source}" if source else text


def evaluate_rights(candidate: dict, request: dict, today: dt.date) -> dict:
    rights = candidate.get("rights") or {}
    basis = rights.get("basis", "unknown")
    if basis not in RIGHTS_BASES:
        basis = "unknown"
    conditions = set(rights.get("conditions") or [])
    contexts = set(request.get("use_contexts") or [])
    modifying = bool(request.get("modifications"))
    commercial = request.get("commercial", True)
    failures: list[str] = []
    gates: list[str] = []

    source_class = candidate.get("source_class", "unknown")
    if basis in NO_RIGHTS_BASES:
        failures.append(NO_RIGHTS_BASES[basis])
    if source_class in NO_RIGHTS_SOURCES:
        failures.append(NO_RIGHTS_SOURCES[source_class])

    if source_class == "mls_listing":
        mls = rights.get("mls") or {}
        if not (mls.get("own_listing") and mls.get("photographer_license_covers_use")):
            failures.append("MLS visibility grants no reuse right; needs own listing plus a photographer license covering this use")
        elif not (mls.get("use_within_active_listing") or mls.get("seller_consent")):
            failures.append("MLS photo reuse outside the active listing needs seller consent and photographer license")

    commercial_use = rights.get("commercial_use", "unknown")
    if commercial and (commercial_use != "allowed" or "noncommercial" in conditions) and basis not in ("public_domain",):
        failures.append(f"commercial use is {commercial_use if 'noncommercial' not in conditions else 'prohibited (NC)'}")
    modification = rights.get("modification", "unknown")
    if modifying:
        if modification == "prohibited" or "no_derivatives" in conditions:
            failures.append("license forbids the planned crop, overlay or text (ND)")
        elif modification == "unknown" and basis != "public_domain":
            failures.append("modification rights not evidenced for the planned crop, overlay or text")
    share_alike = modification == "share_alike" or "share_alike" in conditions
    if share_alike and modifying and contexts & AD_OR_PRINT:
        gates.append("ShareAlike adaptation in advertising or print is an edge case; Allison decides")
    if commercial and "editorial_only" in conditions:
        failures.append("editorial-only license cannot support commercial use")
    if "per_design" in conditions or "no_standalone" in conditions:
        failures.append("license is tied to one design and cannot become a standalone library asset")
    if "hotlink_only" in conditions:
        failures.append("terms require hotlinking; the master file cannot be stored in the register")
    if "seat_limited" in conditions:
        gates.append("single-seat or no-DAM terms conflict with a shared library; Allison decides")

    scope = rights.get("scope_covers_use", "unknown")
    if basis not in ("public_domain", "creative_commons") and scope is not True:
        failures.append("recorded license or permission scope does not cover this exact use" if scope is False else "scope for this exact use is not evidenced")
    if scope is False and basis in ("public_domain", "creative_commons"):
        failures.append("recorded scope does not cover this exact use")
    if basis not in NO_RIGHTS_BASES and not (rights.get("license_evidence_pointer") or "").strip():
        failures.append("no durable license or permission evidence pointer")

    for conflict in rights.get("conflicts") or []:
        failures.append(f"license claim contradicted by recorded evidence: {conflict}")

    permission = rights.get("permission") or {}
    expires = permission.get("expires")
    if expires and dt.date.fromisoformat(str(expires)) < today:
        failures.append(f"permission expired {expires}")

    attribution_required = "attribution" in conditions or str(rights.get("license_id", "")).upper().startswith("CC-BY")
    attribution_text = (rights.get("attribution_text") or "").strip() or None
    if attribution_required and not attribution_text:
        attribution_text = compose_attribution(candidate)
        if not attribution_text:
            failures.append("attribution required but creator or license is unknown, so it cannot be honored")

    for flag in candidate.get("third_party_flags") or []:
        if not flag.get("resolved"):
            reason = SENSITIVE_FLAGS.get(flag.get("flag"), flag.get("flag", "third-party concern"))
            gates.append(f"{reason}; Allison decides")

    if failures:
        state = "NOT CLEARED"
    elif gates:
        state = "NEEDS HUMAN DECISION"
    else:
        state = "RIGHTS CLEAR"
    return {
        "basis": basis,
        "license_id": rights.get("license_id"),
        "state": state,
        "failures": failures,
        "gates": gates,
        "share_alike": share_alike,
        "attribution_required": attribution_required,
        "attribution_text": attribution_text if attribution_required else None,
        "caveat": "risk assessment on recorded evidence, not legal advice",
    }


# ------------------------------------------------------------- next action


def human_gates_for(action: str, rights_gates: list[str]) -> list[str]:
    gates = ["final use approval by Allison or the authorized human"]
    if action == "REQUEST PERMISSION":
        gates.append("outreach is a draft only; sending requires approval")
    if action == "LICENSE":
        gates.append("buying a license is spending and requires approval")
    if action == "COMMISSION":
        gates.append("commissioning photography is spending and requires approval")
    return gates + rights_gates


def decide(candidate: dict, request: dict, fit: dict | None, today: dt.date) -> dict:
    named = bool(request.get("represents_named_place"))
    location = grade_location(
        (candidate.get("location") or {}).get("evidence") or [],
        (candidate.get("location") or {}).get("claimed_grade"),
    )
    rights = evaluate_rights(candidate, request, today)
    flags: list[str] = []
    reasons: list[str] = []
    if location["grade_violation"]:
        flags.append(location["grade_violation"])
    stale = currency_flag(candidate.get("capture_date"), today)
    if stale:
        flags.append(stale)
    if fit and fit.get("insufficient_resolution"):
        flags.append("insufficient resolution for this surface")
    if rights["share_alike"]:
        flags.append("ShareAlike: adaptations must carry the same license")
    for flag in candidate.get("third_party_flags") or []:
        flags.append(f"third-party: {flag.get('flag')}{'' if not flag.get('resolved') else ' (resolved)'}")
    if candidate.get("source_class") == "ai_generated":
        flags.append("AI-generated imagery")

    # Observed web derivatives prove composition, not resolution. A size failure on
    # one is a missing original, not a verdict on the image.
    size_checks = {"crop_resolution", "mobile_density", "target_source"}
    failing = {c["check"] for c in (fit or {}).get("checks", []) if c.get("result") == "fail"}
    derivative_only = (
        candidate.get("dimensions_basis") == "observed_web"
        and bool(fit)
        and bool(fit.get("insufficient_resolution"))
        and failing <= size_checks
    )
    if derivative_only:
        req = fit.get("required_crop_px") or {}
        flags.append(f"original-resolution file required (observed web image too small; needs a crop of at least {req.get('w')}x{req.get('h')})")

    route = candidate.get("owner_contact_route")
    purchase = candidate.get("license_purchase") or {}
    action = None
    if candidate.get("source_class") == "ai_generated" and named:
        action, reasons = "REJECT", ["generated imagery never depicts a real named place"]
    elif location["grade"] == "REJECT":
        action, reasons = "REJECT", ["location evidence contradicts the subject"]
    elif named and location["grade"] == "UNVERIFIED":
        action, reasons = "REJECT", ["UNVERIFIED imagery cannot represent a named place"]
    elif fit and fit.get("technical_fit") == "FAIL" and not derivative_only:
        action = "REJECT"
        reasons = ["fails technical fit for this surface" + (" (insufficient resolution)" if fit.get("insufficient_resolution") else "")]
    elif rights["state"] == "NOT CLEARED":
        reasons = list(rights["failures"])
        if purchase.get("available") and purchase.get("covers_use"):
            action = "LICENSE"
        elif route:
            action = "REQUEST PERMISSION"
        else:
            action = "REJECT"
    elif named and location["grade"] == "PROBABLE":
        reasons = ["PROBABLE is not VERIFIED; a named-place page needs VERIFIED"]
        action = "REQUEST PERMISSION" if route else "REJECT"
    elif rights["state"] == "NEEDS HUMAN DECISION":
        reasons = list(rights["gates"])
        action = "REQUEST PERMISSION" if route else "REJECT"
    elif derivative_only:
        reasons = ["observed web image is below the surface minimum; the original file must be obtained and re-checked"]
        action = "REQUEST PERMISSION" if route else "REJECT"
    elif fit and fit.get("technical_fit") == "PENDING REVIEW":
        raise RuleError(
            f"candidate {candidate.get('candidate_id')!r} passes every other gate but its visual review "
            f"({', '.join(fit.get('pending_review', []))}) is not recorded; complete the review before rendering"
        )
    else:
        action, reasons = "USE", ["identity, rights and technical gates pass on recorded evidence"]

    # The action follows precedence, but every blocker stays visible on the card.
    if action != "USE":
        extra = list(rights["failures"]) + list(rights["gates"])
        if named and location["grade"] == "PROBABLE":
            extra.append("PROBABLE is not VERIFIED; a named-place page needs VERIFIED")
        if fit and fit.get("technical_fit") == "FAIL" and not derivative_only:
            extra.append("fails technical fit for this surface")
        if derivative_only:
            extra.append("request the original-resolution file with any grant")
        reasons += [item for item in extra if not any(item in r or r in item for r in reasons)]

    return {
        "candidate_id": candidate.get("candidate_id"),
        "location": location,
        "rights": rights,
        "technical_fit": (fit or {}).get("technical_fit", "NOT EVALUATED"),
        "next_action": action,
        "exact_use_cleared": action == "USE",
        "reasons": reasons,
        "risk_flags": flags,
        "human_gates": human_gates_for(action, rights["gates"]),
        "auto_executable": False,
    }


def route_when_empty(request: dict) -> dict:
    if request.get("represents_named_place"):
        if request.get("known_owner_sources"):
            action = "REQUEST PERMISSION"
            why = "official owner imagery exists but is not licensed to us; ask the owner"
        else:
            action = "COMMISSION"
            why = "no defensible existing image; commission photography under a written perpetual license"
    else:
        action = "LICENSE"
        why = "no defensible free candidate; license generic stock for this non-identity use"
    return {
        "headline": "No defensible candidate found.",
        "recommended_action": action,
        "why": why,
        "human_gates": human_gates_for(action, []),
        "auto_executable": False,
    }


# ---------------------------------------------------------- register reuse


def _norm(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def check_reuse(record: dict, request: dict, today: dt.date, fit: dict | None = None) -> dict:
    """Reuse a cleared asset only when its recorded scope covers the new request."""
    reasons: list[str] = []
    if record.get("status") != "approved":
        reasons.append(f"record status is {record.get('status')!r}, not approved")
    brands = set(record.get("brand_scope") or [])
    if request.get("brand") not in brands and "estate" not in brands:
        reasons.append(f"brand {request.get('brand')!r} is outside recorded brand scope {sorted(brands)}")
    if request.get("represents_named_place"):
        key_req, key_rec = request.get("place_key"), record.get("place_key")
        same = (key_req and key_rec and key_req == key_rec) or (
            not (key_req and key_rec) and _norm(record.get("subject")) == _norm(request.get("subject"))
        )
        if not same:
            reasons.append("recorded subject is not proven to be the requested place")
        if record.get("location_confidence") != "VERIFIED":
            reasons.append(f"location is {record.get('location_confidence')}, not VERIFIED")
    scope = record.get("permission_scope") or {}
    uses = set(scope.get("uses") or [])
    missing = set(request.get("use_contexts") or []) - uses
    if missing:
        reasons.append(f"recorded scope does not cover {sorted(missing)}")
    if request.get("modifications") and scope.get("modifications_allowed") is not True:
        reasons.append("recorded scope does not cover the planned modifications")
    expires = record.get("permission_expires")
    if expires and dt.date.fromisoformat(str(expires)) < today:
        reasons.append(f"permission expired {expires}")
    due = record.get("review_due")
    if due and dt.date.fromisoformat(str(due)) < today:
        reasons.append(f"review was due {due}; re-verify before reuse")
    for flag in record.get("third_party_flags") or []:
        if isinstance(flag, dict) and not flag.get("resolved"):
            reasons.append(f"unresolved third-party flag {flag.get('flag')}")
    license_id = str(record.get("license") or "").upper()
    if "SA" in license_id.split("-") and set(request.get("use_contexts") or []) & AD_OR_PRINT:
        reasons.append("ShareAlike asset in advertising or print needs Allison's decision, not automatic reuse")
    if fit and fit.get("technical_fit") == "FAIL":
        reasons.append("recorded asset fails technical fit for the new surface")
    return {"asset_id": record.get("asset_id"), "reusable": not reasons, "reasons": reasons}


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    data = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    today = today_from(data.get("as_of"))
    out = [decide(c, data["request"], c.get("fit"), today) for c in data.get("candidates", [])]
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
