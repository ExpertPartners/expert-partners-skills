#!/usr/bin/env python3
"""render_cards.py -- render visual-clearance candidate cards from structured data.

Part of the visual-clearance skill. Takes one evaluation file (the request,
the register check, the search log and the candidates), runs technical fit
and the clearance rules for every candidate, and renders at most five cards
ranked by next action. It never pads to five. When no candidate is
defensible it says so and names the route (permission or commission), which
is a successful result.

Nothing rendered here is sent, bought or approved. Every card is a proposal
for Allison or the authorized human.

Usage:
  render_cards.py EVALUATION.json [--profiles DIR] [--json]
Exit status: 0 rendered, 1 rule error (for example a missing visual review).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from clearance_rules import ACTION_RANK, RuleError, decide, route_when_empty, today_from  # noqa: E402
from fit_check import evaluate as fit_evaluate, load_profile  # noqa: E402

MAX_CARDS = 5
DEFAULT_PROFILES = HERE.parent / "profiles"


def build(evaluation: dict, profiles_dir: Path = DEFAULT_PROFILES) -> dict:
    request = evaluation["request"]
    today = today_from(evaluation.get("as_of"))
    profile = None
    if request.get("profile"):
        name = f"{request['profile']}.json"
        path = profiles_dir / name if (profiles_dir / name).exists() else DEFAULT_PROFILES / name
        profile = load_profile(path)
    register = evaluation.get("register_check") or {"status": "not_run"}
    if register.get("status") not in ("checked", "unreachable"):
        raise RuleError("the visual-assets register check must run (or be reported unreachable) before external sourcing")

    decisions = []
    for candidate in evaluation.get("candidates", []):
        fit = None
        dims = candidate.get("dimensions")
        if profile and dims:
            fit = fit_evaluate(dims["w"], dims["h"], profile, candidate.get("visual_review"))
        elif profile:
            fit = {"technical_fit": "FAIL", "insufficient_resolution": True, "checks": [], "pending_review": []}
        decision = decide(candidate, request, fit, today)
        decisions.append((candidate, fit, decision))

    decisions.sort(key=lambda item: (ACTION_RANK[item[2]["next_action"]], -((item[0].get("dimensions") or {}).get("w", 0))))
    defensible = [d for d in decisions if d[2]["next_action"] != "REJECT"]
    shown = decisions[:MAX_CARDS]
    return {
        "request": request,
        "register": register,
        "search_log": evaluation.get("search_log", []),
        "cards": shown,
        "screened_out": len(decisions) - len(shown),
        "defensible_count": len(defensible),
        "empty_route": None if defensible else route_when_empty(request),
    }


def _loc_line(decision: dict, candidate: dict) -> str:
    loc = decision["location"]
    evidence = (candidate.get("location") or {}).get("evidence") or []
    counted = [e for e in evidence if e.get("type") not in ("search_label", "ai_inference")]
    listed = "; ".join(f"{e['type']}: {e.get('detail') or e.get('pointer')}" for e in counted) or "none recorded"
    return f"{loc['grade']} ({listed})"


def render_markdown(result: dict) -> str:
    req = result["request"]
    lines = [
        f"## Visual Clearance: {req.get('subject')}",
        "",
        f"Use: {req.get('intended_use')} for {req.get('brand')}. Profile: {req.get('profile') or 'none'}. "
        f"Names a real place: {'yes' if req.get('represents_named_place') else 'no'}.",
        f"Register check: {result['register'].get('status')}"
        + (f", {result['register'].get('note')}" if result["register"].get("note") else "")
        + ".",
    ]
    if result["search_log"]:
        searched = ", ".join(f"{s.get('source')} ({s.get('results', '?')})" for s in result["search_log"])
        lines.append(f"Searched: {searched}.")
    lines.append("")
    if result["empty_route"]:
        route = result["empty_route"]
        lines += [
            f"{route['headline']} Recommended route: {route['recommended_action']}. {route['why']}.",
            f"Gated: {'; '.join(route['human_gates'])}. Nothing has been sent, bought or commissioned.",
            "",
        ]
    else:
        lines.append(f"{result['defensible_count']} defensible candidate(s). Nothing has been sent, bought or approved.")
        lines.append("")
    for index, (cand, fit, dec) in enumerate(result["cards"], 1):
        dims = cand.get("dimensions")
        rights = dec["rights"]
        attribution = rights["attribution_text"] if rights["attribution_required"] else "not required"
        fit_line = dec["technical_fit"]
        if fit and fit.get("crop"):
            fit_line += f" ({fit['crop']['w']}x{fit['crop']['h']} crop)"
        lines += [
            f"### Card {index}: {cand.get('subject')}",
            f"- Thumbnail: {cand.get('thumbnail') or cand.get('source_url') or 'none'}",
            f"- Source: {cand.get('source')} | Creator: {cand.get('creator') or 'unknown'}",
            f"- Source URL: {cand.get('source_url') or 'none'}",
            f"- Dimensions: {dims['w']}x{dims['h']}" if dims else "- Dimensions: unknown",
            f"- Location: {_loc_line(dec, cand)}",
            f"- Rights: {rights['state']} (basis {rights['basis']}, license {rights['license_id'] or 'none'}; {rights['caveat']})",
            f"- Exact-use clearance: {'yes, pending final approval' if dec['exact_use_cleared'] else 'no'}",
            f"- Attribution: {attribution}",
            f"- Technical fit: {fit_line}",
            f"- Risk flags: {'; '.join(dec['risk_flags']) or 'none'}",
            f"- Why: {'; '.join(dec['reasons'])}",
            f"- NEXT: {dec['next_action']}",
            f"- Gated: {'; '.join(dec['human_gates'])}",
            "",
        ]
    if result["screened_out"]:
        lines.append(f"{result['screened_out']} lower-ranked candidate(s) screened out to stay within five cards.")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("evaluation")
    parser.add_argument("--profiles", default=str(DEFAULT_PROFILES))
    parser.add_argument("--json", action="store_true", help="emit structured decisions instead of markdown")
    args = parser.parse_args(argv)
    evaluation = json.loads(Path(args.evaluation).read_text(encoding="utf-8"))
    try:
        result = build(evaluation, Path(args.profiles))
    except RuleError as exc:
        print(f"RULE ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        payload = {
            "defensible_count": result["defensible_count"],
            "empty_route": result["empty_route"],
            "screened_out": result["screened_out"],
            "cards": [dec for _, _, dec in result["cards"]],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        sys.stdout.write(render_markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
