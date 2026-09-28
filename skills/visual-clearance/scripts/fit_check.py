#!/usr/bin/env python3
"""fit_check.py -- parameterized technical fit for one image against one surface profile.

Part of the visual-clearance skill. Geometry only: aspect-ratio crop
feasibility, useful pixels after the crop, the center heading safe zone in
source pixels, and the mobile viewport slice with its pixel density. Visual
judgments (calm center, overlay tolerance, subject inside the mobile slice)
cannot be proven from dimensions, so they come back as review items that a
vision model or a human must record before technical fit can read PASS.

Profiles are JSON files (see ../profiles/). A brand, application or surface
supplies its own profile; the script hardcodes no brand values.

Usage:
  fit_check.py --profile PROFILE.json --width W --height H [--review REVIEW.json]
  fit_check.py --profile PROFILE.json --inspect INSPECT.json [--review REVIEW.json]
    INSPECT.json is inspect_image.py output (first entry is used).
    REVIEW.json maps review item keys to "pass" or "fail".
Exit status: 0 PASS, 1 FAIL, 3 PENDING REVIEW, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def center_crop(width: int, height: int, aspect_w: int, aspect_h: int) -> dict:
    """Largest centered crop of the requested aspect ratio."""
    if width * aspect_h >= height * aspect_w:
        crop_h = height
        crop_w = (height * aspect_w) // aspect_h
    else:
        crop_w = width
        crop_h = (width * aspect_h) // aspect_w
    return {
        "x": (width - crop_w) // 2,
        "y": (height - crop_h) // 2,
        "w": crop_w,
        "h": crop_h,
    }


def review_keys(profile: dict) -> list[str]:
    return [item.split(":", 1)[0].strip() for item in profile.get("visual_review_items", [])]


def evaluate(width: int, height: int, profile: dict, review: dict | None = None) -> dict:
    review = review or {}
    aspect = profile["aspect_ratio"]
    crop = center_crop(width, height, aspect["w"], aspect["h"])
    checks: list[dict] = []

    orientation = "landscape" if width > height else ("portrait" if height > width else "square")
    wanted = profile.get("orientation")
    # Orientation is informational: a portrait master can still yield a valid
    # landscape crop, so the crop checks below decide, not the source shape.
    checks.append({
        "check": "orientation",
        "result": "pass" if wanted in (None, orientation) else "info",
        "detail": f"source is {orientation}; profile wants {wanted}; the {aspect['w']}:{aspect['h']} crop is evaluated below",
    })

    min_crop = profile["min_crop_px"]
    crop_ok = crop["w"] >= min_crop["w"] and crop["h"] >= min_crop["h"]
    checks.append({
        "check": "crop_resolution",
        "result": "pass" if crop_ok else "fail",
        "detail": f"{aspect['w']}:{aspect['h']} crop {crop['w']}x{crop['h']} vs minimum {min_crop['w']}x{min_crop['h']}",
    })

    target = profile.get("target_source_px")
    if target:
        meets = width >= target["w"] and height >= target["h"]
        checks.append({
            "check": "target_source",
            "result": "pass" if meets else ("warn" if crop_ok else "fail"),
            "detail": f"source {width}x{height} vs approximate target {target['w']}x{target['h']}",
        })

    zone = profile["heading_safe_zone"]
    safe = {
        "x": crop["x"] + round(crop["w"] * zone["x"]),
        "y": crop["y"] + round(crop["h"] * zone["y"]),
        "w": round(crop["w"] * zone["w"]),
        "h": round(crop["h"] * zone["h"]),
    }

    mobile = profile.get("mobile")
    mobile_result = None
    if mobile:
        view = mobile["viewport"]
        slice_h = crop["h"]
        slice_w = min(crop["w"], (slice_h * view["w"]) // view["h"])
        density = slice_h / view["h"]
        mobile_result = {
            "slice": {"x": crop["x"] + (crop["w"] - slice_w) // 2, "y": crop["y"], "w": slice_w, "h": slice_h},
            "density": round(density, 3),
            "upscale_needed_at": {
                f"{d}x": round((view["h"] * d) / slice_h, 3) for d in mobile.get("report_densities", [])
            },
        }
        checks.append({
            "check": "mobile_density",
            "result": "pass" if density >= mobile.get("min_density", 1.0) else "fail",
            "detail": f"mobile {view['w']}x{view['h']} slice {slice_w}x{slice_h}, density {density:.2f} vs minimum {mobile.get('min_density', 1.0)}",
        })

    pending, failed_review = [], []
    for key in review_keys(profile):
        verdict = review.get(key)
        if verdict == "pass":
            checks.append({"check": key, "result": "pass", "detail": "visual review recorded"})
        elif verdict == "fail":
            failed_review.append(key)
            checks.append({"check": key, "result": "fail", "detail": "visual review recorded"})
        else:
            pending.append(key)

    geometric_fail = any(c["result"] == "fail" for c in checks)
    if geometric_fail or failed_review:
        verdict = "FAIL"
    elif pending:
        verdict = "PENDING REVIEW"
    else:
        verdict = "PASS"
    return {
        "profile_id": profile["profile_id"],
        "profile_version": profile.get("profile_version"),
        "source": {"w": width, "h": height},
        "crop": crop,
        "heading_safe_zone_px": safe,
        "overlay_under_review": profile.get("overlay"),
        "mobile": mobile_result,
        "checks": checks,
        "pending_review": pending,
        "technical_fit": verdict,
        "insufficient_resolution": any(
            c["check"] in ("crop_resolution", "mobile_density") and c["result"] == "fail" for c in checks
        ),
    }


def load_profile(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", required=True)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--inspect")
    parser.add_argument("--review")
    args = parser.parse_args(argv)
    if args.inspect:
        info = json.loads(Path(args.inspect).read_text(encoding="utf-8"))
        info = info[0] if isinstance(info, list) else info
        width, height = info["dimensions"]["w"], info["dimensions"]["h"]
    elif args.width and args.height:
        width, height = args.width, args.height
    else:
        parser.error("give --width and --height, or --inspect")
    review = json.loads(Path(args.review).read_text(encoding="utf-8")) if args.review else None
    result = evaluate(width, height, load_profile(args.profile), review)
    print(json.dumps(result, indent=2, sort_keys=True))
    return {"PASS": 0, "FAIL": 1, "PENDING REVIEW": 3}[result["technical_fit"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
