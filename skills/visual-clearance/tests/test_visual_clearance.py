"""Tests for the visual-clearance skill's deterministic helpers, pilots and guards.

Run: python3 -m unittest discover -s skills/visual-clearance/tests -p 'test_*.py' -v
Standard library only, plus PyYAML for the YAML fixture record.
"""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import clearance_rules as rules  # noqa: E402
import fit_check  # noqa: E402
import inspect_image  # noqa: E402
import evaluate_site_record  # noqa: E402
import render_cards  # noqa: E402
import validate_record  # noqa: E402

TODAY = dt.date(2026, 9, 28)
HERO = fit_check.load_profile(SKILL / "profiles" / "ag-luxury-community-hero.json")


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def build(evaluation: dict) -> dict:
    return render_cards.build(evaluation, FIXTURES / "profiles")


def actions(result: dict) -> dict:
    return {dec["candidate_id"]: dec["next_action"] for _, _, dec in result["cards"]}


def jpeg_with_exif(width: int, height: int, orientation: int = 1) -> bytes:
    """Header-only JPEG with an EXIF block: orientation, artist, date and GPS."""
    def entry(tag, typ, count, value_bytes):
        return struct.pack("<HHI", tag, typ, count) + value_bytes.ljust(4, b"\x00")

    artist = b"Fixture Artist\x00"
    date = b"2026:05:01 18:30:00\x00"
    ifd0_off = 8
    exif_off = ifd0_off + 2 + 4 * 12 + 4
    gps_off = exif_off + 2 + 1 * 12 + 4
    artist_off = gps_off + 2 + 4 * 12 + 4
    date_off = artist_off + len(artist)
    lat_off = date_off + len(date)
    lon_off = lat_off + 24
    ifd0 = struct.pack("<H", 4)
    ifd0 += entry(0x0112, 3, 1, struct.pack("<H", orientation))
    ifd0 += entry(0x013B, 2, len(artist), struct.pack("<I", artist_off))
    ifd0 += entry(0x8769, 4, 1, struct.pack("<I", exif_off))
    ifd0 += entry(0x8825, 4, 1, struct.pack("<I", gps_off))
    ifd0 += struct.pack("<I", 0)
    exif_ifd = struct.pack("<H", 1) + entry(0x9003, 2, len(date), struct.pack("<I", date_off)) + struct.pack("<I", 0)
    gps_ifd = struct.pack("<H", 4)
    gps_ifd += entry(1, 2, 2, b"N\x00")
    gps_ifd += entry(2, 5, 3, struct.pack("<I", lat_off))
    gps_ifd += entry(3, 2, 2, b"W\x00")
    gps_ifd += entry(4, 5, 3, struct.pack("<I", lon_off))
    gps_ifd += struct.pack("<I", 0)
    lat = struct.pack("<6I", 33, 1, 19, 1, 3600, 100)  # 33 deg 19 min 36.00 sec
    lon = struct.pack("<6I", 96, 1, 46, 1, 1800, 100)  # 96 deg 46 min 18.00 sec
    tiff = b"II*\x00" + struct.pack("<I", ifd0_off) + ifd0 + exif_ifd + gps_ifd + artist + date + lat + lon
    assert len(b"II*\x00" + struct.pack("<I", ifd0_off) + ifd0) == exif_off
    app1 = b"Exif\x00\x00" + tiff
    sof = b"\x08" + struct.pack(">HH", height, width) + b"\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
    return (
        b"\xff\xd8"
        + b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1
        + b"\xff\xc0" + struct.pack(">H", len(sof) + 2) + sof
        + b"\xff\xd9"
    )


def tiny_png(width: int, height: int) -> bytes:
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + b"\x10\x20\x30" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class InspectImageTests(unittest.TestCase):
    def test_png_dimensions_and_hash(self):
        data = tiny_png(7, 3)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tiny.png"
            path.write_bytes(data)
            info = inspect_image.inspect(path)
        self.assertEqual(info["format"], "png")
        self.assertEqual(info["dimensions"], {"w": 7, "h": 3})
        self.assertEqual(info["sha256"], hashlib.sha256(data).hexdigest())
        self.assertFalse(info["exif_present"])

    def test_jpeg_exif_gps_date_and_orientation_swap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.jpg"
            path.write_bytes(jpeg_with_exif(4000, 3000, orientation=6))
            info = inspect_image.inspect(path)
        self.assertEqual(info["format"], "jpeg")
        self.assertEqual(info["stored_dimensions"], {"w": 4000, "h": 3000})
        self.assertEqual(info["dimensions"], {"w": 3000, "h": 4000}, "orientation 6 displays rotated")
        self.assertEqual(info["exif"]["artist"], "Fixture Artist")
        self.assertEqual(info["exif"]["datetime_original"], "2026:05:01 18:30:00")
        self.assertAlmostEqual(info["exif"]["gps"]["lat"], 33.3266667, places=5)
        self.assertAlmostEqual(info["exif"]["gps"]["lon"], -96.7716667, places=5)

    def test_cli_reports_unparseable_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "not-an-image.jpg"
            bad.write_bytes(b"hello")
            proc = subprocess.run([sys.executable, str(SCRIPTS / "inspect_image.py"), str(bad)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("error", json.loads(proc.stdout)[0])


class FitCheckTests(unittest.TestCase):
    def test_water_tower_portrait_yields_passing_landscape_crop(self):
        fit = fit_check.evaluate(3250, 4907, HERO)
        self.assertEqual(fit["crop"]["w"], 3250)
        self.assertEqual(fit["crop"]["h"], 1828)
        self.assertFalse(fit["insufficient_resolution"])
        self.assertEqual(fit["technical_fit"], "PENDING REVIEW", "visual items must be recorded before PASS")

    def test_light_farms_entrance_is_insufficient(self):
        fit = fit_check.evaluate(1893, 1262, HERO)
        self.assertEqual(fit["technical_fit"], "FAIL")
        self.assertTrue(fit["insufficient_resolution"])

    def test_mobile_slice_and_safe_zone_geometry(self):
        fit = fit_check.evaluate(6000, 3375, HERO, {"calm_center": "pass", "overlay_tolerance": "pass", "mobile_subject": "pass"})
        self.assertEqual(fit["technical_fit"], "PASS")
        self.assertEqual(fit["mobile"]["slice"]["h"], 3375)
        self.assertEqual(fit["mobile"]["slice"]["w"], 3375 * 390 // 844)
        self.assertEqual(fit["heading_safe_zone_px"], {"x": 1200, "y": 1012, "w": 3600, "h": 1350})

    def test_profile_parameterization(self):
        generic = fit_check.load_profile(FIXTURES / "profiles" / "generic-web-landscape.json")
        self.assertEqual(fit_check.evaluate(1700, 956, generic, {"on_brand_mood": "pass"})["technical_fit"], "PASS")
        self.assertEqual(fit_check.evaluate(1700, 956, HERO)["technical_fit"], "FAIL")

    def test_recorded_visual_failure_fails_fit(self):
        fit = fit_check.evaluate(6000, 3375, HERO, {"calm_center": "fail", "overlay_tolerance": "pass", "mobile_subject": "pass"})
        self.assertEqual(fit["technical_fit"], "FAIL")


class PilotTests(unittest.TestCase):
    def run_pilot(self, name: str) -> dict:
        evaluation = load_fixture(name)
        result = build(evaluation)
        expected = evaluation["expected"]
        self.assertEqual(result["defensible_count"], expected["defensible_count"])
        self.assertEqual(actions(result), expected["actions"])
        route = result["empty_route"]
        self.assertEqual(route["recommended_action"] if route else None, expected["empty_route"])
        return result

    def test_pilot_newman_village_refuses_trap_and_returns_no_candidate(self):
        result = self.run_pilot("pilot-newman-village.json")
        decisions = {dec["candidate_id"]: dec for _, _, dec in result["cards"]}
        self.assertEqual(decisions["newman-apartments"]["location"]["grade"], "REJECT")
        self.assertEqual(decisions["generic-gate"]["location"]["grade"], "UNVERIFIED")
        text = render_cards.render_markdown(result)
        self.assertIn("No defensible candidate found.", text)
        self.assertIn("COMMISSION", text)

    def test_pilot_light_farms_real_license_but_fails_hero(self):
        result = self.run_pilot("pilot-light-farms.json")
        decisions = {dec["candidate_id"]: dec for _, _, dec in result["cards"]}
        entrance = decisions["lf-entrance"]
        self.assertEqual(entrance["location"]["grade"], "PROBABLE")
        self.assertEqual(entrance["rights"]["license_id"], "CC-BY-SA-4.0")
        flags = " ".join(entrance["risk_flags"])
        self.assertIn("insufficient resolution", flags)
        self.assertIn("ShareAlike", flags)
        self.assertIn("trademark_logo", flags)
        self.assertIn("currency", flags)
        tower = decisions["lf-water-tower"]
        self.assertEqual(tower["technical_fit"], "PENDING REVIEW")
        self.assertEqual(tower["rights"]["state"], "NOT CLEARED", "the website record found a contradicting copyright owner")
        self.assertIn("license claim contradicted", " ".join(tower["reasons"]))
        self.assertFalse(tower["exact_use_cleared"])
        self.assertIn("PROBABLE is not VERIFIED", " ".join(tower["reasons"]))
        self.assertEqual(tower["rights"]["attribution_text"], "Photo: Michael.Rihani, CC-BY-SA-4.0, via Wikimedia Commons")

    def test_pilot_generic_lifestyle_allows_generic_stock(self):
        result = self.run_pilot("pilot-generic-lifestyle.json")
        decisions = {dec["candidate_id"]: dec for _, _, dec in result["cards"]}
        self.assertEqual(decisions["unsplash-terrace"]["rights"]["state"], "RIGHTS CLEAR")
        self.assertTrue(decisions["unsplash-terrace"]["exact_use_cleared"])
        self.assertFalse(decisions["adobe-terrace"]["exact_use_cleared"])
        self.assertEqual(decisions["unsplash-terrace"]["location"]["grade"], "UNVERIFIED", "location is not required when no place is named")
        self.assertIn("spending", " ".join(decisions["adobe-terrace"]["human_gates"]))

    def test_generic_stock_blocked_once_the_page_names_a_place(self):
        evaluation = load_fixture("pilot-generic-lifestyle.json")
        evaluation["request"]["represents_named_place"] = True
        evaluation["request"]["subject"] = "Starwood, Frisco TX"
        result = build(evaluation)
        self.assertEqual(result["defensible_count"], 0)
        self.assertEqual(result["empty_route"]["recommended_action"], "COMMISSION")

    def test_pilot_generated_named_place_rejected(self):
        result = self.run_pilot("pilot-generated-named-place.json")
        dec = result["cards"][0][2]
        self.assertIn("generated imagery never depicts a real named place", dec["reasons"])
        self.assertIsNotNone(dec["location"]["grade_violation"])

    def test_pilot_cleared_asset_reuse_only_within_scope(self):
        record = validate_record.load(FIXTURES / "record-cleared-light-farms.yaml")
        self.assertEqual(validate_record.validate(record), [])
        base = {"subject": "Light Farms, Celina TX", "place_key": "light-farms-celina-tx", "represents_named_place": True,
                "brand": "ag-luxury", "use_contexts": ["website"], "modifications": ["16:9 crop"]}
        fit = fit_check.evaluate(record["dimensions"]["w"], record["dimensions"]["h"], HERO,
                                 {"calm_center": "pass", "overlay_tolerance": "pass", "mobile_subject": "pass"})
        self.assertTrue(rules.check_reuse(record, base, TODAY, fit)["reusable"])
        for change, needle in (
            ({"use_contexts": ["print", "advertising"]}, "does not cover"),
            ({"brand": "ag-personal-brand"}, "outside recorded brand scope"),
            ({"place_key": "starwood-frisco-tx", "subject": "Starwood, Frisco TX"}, "not proven to be the requested place"),
        ):
            outcome = rules.check_reuse(record, {**base, **change}, TODAY, fit)
            self.assertFalse(outcome["reusable"], change)
            self.assertIn(needle, " ".join(outcome["reasons"]))
        late = rules.check_reuse(record, base, dt.date(2027, 10, 1), fit)
        self.assertFalse(late["reusable"])
        self.assertIn("re-verify", " ".join(late["reasons"]))
        small = fit_check.evaluate(1600, 900, HERO)
        self.assertFalse(rules.check_reuse(record, base, TODAY, small)["reusable"])


class GuardTests(unittest.TestCase):
    def test_unverified_cannot_silently_become_verified(self):
        graded = rules.grade_location([{"type": "search_label", "detail": "Light Farms"}], claimed="VERIFIED")
        self.assertEqual(graded["grade"], "UNVERIFIED")
        self.assertIn("grade stays UNVERIFIED", graded["grade_violation"])
        unrecorded = rules.grade_location([{"type": "landmark_match_official"}, {"type": "source_metadata"}], claimed="VERIFIED")
        self.assertEqual(unrecorded["grade"], "UNVERIFIED", "evidence without detail or pointer does not count")
        record = validate_record.load(FIXTURES / "record-cleared-light-farms.yaml")
        weak = copy.deepcopy(record)
        weak["location_evidence"] = [weak["location_evidence"][0]]
        self.assertTrue(any("VERIFIED needs" in e for e in validate_record.validate(weak)))
        relabeled = copy.deepcopy(record)
        relabeled["location_confidence"] = "UNVERIFIED"
        self.assertTrue(any("only VERIFIED may represent a named place" in e for e in validate_record.validate(relabeled)))

    def test_reachable_creator_never_substitutes_for_identity_evidence(self):
        request = {"represents_named_place": True, "use_contexts": ["advertising"], "modifications": [], "commercial": True}
        candidate = {"candidate_id": "prosper-nc", "source_class": "open_license", "creator": "Flickr Photographer",
                     "owner_contact_route": "creator", "location": {"evidence": [{"type": "search_label", "detail": "tagged Prosper"}]},
                     "rights": {"basis": "creative_commons", "license_id": "CC-BY-NC-2.0", "commercial_use": "prohibited",
                                "conditions": ["attribution", "noncommercial"], "license_evidence_pointer": "https://example.com/p"}}
        decision = rules.decide(candidate, request, None, TODAY)
        self.assertEqual(decision["next_action"], "REJECT")
        self.assertIn("UNVERIFIED imagery cannot represent a named place", decision["reasons"])
        self.assertTrue(any("commercial use" in r for r in decision["reasons"]), "the rights failure stays visible")

    def test_contradiction_rejects_even_with_strong_evidence(self):
        graded = rules.grade_location([
            {"type": "landmark_match_official", "detail": "monument matches"},
            {"type": "source_metadata", "detail": "caption"},
            {"type": "contradiction", "detail": "EXIF GPS is 40 miles away"},
        ])
        self.assertEqual(graded["grade"], "REJECT")

    def test_attribution_never_cures_a_rights_failure(self):
        request = {"represents_named_place": False, "use_contexts": ["website"], "modifications": [], "commercial": True}
        for rights, needle in (
            ({"basis": "creative_commons", "license_id": "CC-BY-NC-4.0", "commercial_use": "prohibited", "conditions": ["attribution", "noncommercial"]}, "commercial use"),
            ({"basis": "royalty_free", "license_id": "Editorial", "commercial_use": "allowed", "conditions": ["editorial_only", "attribution"], "scope_covers_use": True}, "editorial-only"),
            ({"basis": "visible_online", "conditions": ["attribution"]}, "grants no rights"),
        ):
            candidate = {"creator": "Named Creator", "source": "Somewhere",
                         "rights": {**rights, "attribution_text": "Photo: Named Creator", "license_evidence_pointer": "https://example.com/license"}}
            outcome = rules.evaluate_rights(candidate, request, TODAY)
            self.assertEqual(outcome["state"], "NOT CLEARED", rights)
            self.assertIn(needle, " ".join(outcome["failures"]))

    def test_insufficient_resolution_is_surfaced(self):
        result = build(load_fixture("pilot-light-farms.json"))
        fitness = next(dec for _, _, dec in result["cards"] if dec["candidate_id"] == "lf-fitness")
        self.assertIn("insufficient resolution for this surface", fitness["risk_flags"])
        self.assertIn("insufficient resolution", " ".join(fitness["reasons"]))
        self.assertIn("insufficient resolution", render_cards.render_markdown(result))

    def test_zero_result_output_is_permitted(self):
        evaluation = load_fixture("pilot-newman-village.json")
        evaluation["candidates"] = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.json"
            path.write_text(json.dumps(evaluation), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(SCRIPTS / "render_cards.py"), str(path)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("No defensible candidate found.", proc.stdout)
        self.assertNotIn("### Card", proc.stdout)

    def test_external_sends_and_spend_stay_gated(self):
        for name in ("pilot-newman-village.json", "pilot-light-farms.json", "pilot-generic-lifestyle.json", "pilot-generated-named-place.json"):
            result = build(load_fixture(name))
            for _, _, dec in result["cards"]:
                self.assertFalse(dec["auto_executable"])
                self.assertIn("final use approval by Allison or the authorized human", dec["human_gates"])
                if dec["next_action"] == "REQUEST PERMISSION":
                    self.assertIn("outreach is a draft only; sending requires approval", dec["human_gates"])
                if dec["next_action"] in ("LICENSE", "COMMISSION"):
                    self.assertTrue(any("spending" in g for g in dec["human_gates"]))
            if result["empty_route"]:
                self.assertFalse(result["empty_route"]["auto_executable"])
        commission = rules.route_when_empty({"represents_named_place": True})
        self.assertTrue(any("spending" in g for g in commission["human_gates"]))

    def test_scripts_have_no_send_purchase_or_network_capability(self):
        banned = re.compile(r"^\s*(import|from)\s+(smtplib|urllib|http|requests|socket|ftplib|imaplib|webbrowser)\b", re.M)
        for script in SCRIPTS.glob("*.py"):
            self.assertIsNone(banned.search(script.read_text(encoding="utf-8")), script.name)

    def test_share_alike_in_print_or_ads_is_human_gated(self):
        evaluation = load_fixture("pilot-light-farms.json")
        evaluation["request"].update({"represents_named_place": False, "use_contexts": ["print"], "profile": None})
        result = build(evaluation)
        fitness = next(dec for _, _, dec in result["cards"] if dec["candidate_id"] == "lf-fitness")
        self.assertEqual(fitness["rights"]["state"], "NEEDS HUMAN DECISION")
        self.assertTrue(any("ShareAlike adaptation" in g for g in fitness["human_gates"]))
        self.assertNotEqual(fitness["next_action"], "USE")

    def test_five_card_cap_and_no_padding(self):
        evaluation = load_fixture("pilot-generic-lifestyle.json")
        extra = []
        for index in range(6):
            clone = copy.deepcopy(evaluation["candidates"][0])
            clone["candidate_id"] = f"clone-{index}"
            extra.append(clone)
        evaluation["candidates"] += extra
        result = build(evaluation)
        self.assertEqual(len(result["cards"]), 5)
        self.assertEqual(result["screened_out"], 3)
        single = load_fixture("pilot-generated-named-place.json")
        self.assertEqual(len(build(single)["cards"]), 1, "never padded to five")

    def test_register_check_runs_before_external_sourcing(self):
        evaluation = load_fixture("pilot-light-farms.json")
        del evaluation["register_check"]
        with self.assertRaises(rules.RuleError):
            build(evaluation)
        evaluation["register_check"] = {"status": "unreachable", "note": "visual-assets register not reachable"}
        self.assertIn("unreachable", render_cards.render_markdown(build(evaluation)))

    def test_use_requires_recorded_visual_review(self):
        evaluation = load_fixture("pilot-generic-lifestyle.json")
        del evaluation["candidates"][0]["visual_review"]
        with self.assertRaises(rules.RuleError):
            build(evaluation)

    def test_mls_visibility_is_not_a_reuse_right(self):
        candidate = {"source_class": "mls_listing", "creator": "Listing Photographer",
                     "rights": {"basis": "royalty_free", "commercial_use": "allowed", "modification": "allowed",
                                "scope_covers_use": True, "license_evidence_pointer": "https://example.com/mls",
                                "mls": {"own_listing": False}}}
        outcome = rules.evaluate_rights(candidate, {"use_contexts": ["website"], "modifications": []}, TODAY)
        self.assertEqual(outcome["state"], "NOT CLEARED")
        self.assertIn("MLS visibility grants no reuse right", " ".join(outcome["failures"]))

    def test_register_privacy_and_human_approver(self):
        record = validate_record.load(FIXTURES / "record-cleared-light-farms.yaml")
        for mutate, needle in (
            (lambda r: r.update(notes="Reply from jane@example.com agreeing to terms"), "email address"),
            (lambda r: r.update(notes="call 214-555-0100 for the files"), "phone number"),
            (lambda r: r.update(notes="api_key: abc123"), "credential"),
            (lambda r: r["approval"].update(approved_by="Claude (visual-clearance skill)"), "AI surface"),
        ):
            changed = copy.deepcopy(record)
            mutate(changed)
            self.assertTrue(any(needle in e for e in validate_record.validate(changed)), needle)

    def test_validator_cli(self):
        proc = subprocess.run([sys.executable, str(SCRIPTS / "validate_record.py"), str(FIXTURES / "record-cleared-light-farms.yaml")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("VALID", proc.stdout)


class SiteRecordTests(unittest.TestCase):
    """The website's own record is read in place; nothing is copied or promoted."""

    def evaluate(self, record=None):
        record = record or load_fixture("site-record-sample.json")
        return evaluate_site_record.evaluate(record, "fixture-rev", TODAY)

    def test_each_placement_checked_with_documented_minimums(self):
        rows = {r["slug"]: r for r in self.evaluate()["candidates"]}
        labeled = rows["sample-labeled"]["placements"]
        self.assertEqual(set(labeled), {"directory", "hero", "midGuide"})
        self.assertEqual(labeled["directory"]["crop"], "900x675")
        self.assertEqual(labeled["hero"]["required"], "2134x1200")
        self.assertEqual(labeled["midGuide"]["required"], "2000x1300")
        page_only = rows["sample-page-only"]["placements"]
        self.assertEqual(page_only["hero"]["crop"], "3000x1687")
        self.assertTrue(page_only["midGuide"]["resolution_ok"], "3:2 or wider uses the whole 3:2 frame")

    def test_page_placement_is_not_identity_evidence_and_nothing_is_verified(self):
        result = self.evaluate()
        rows = {r["slug"]: r for r in result["candidates"]}
        self.assertEqual(rows["sample-page-only"]["location_grade"], "UNVERIFIED")
        self.assertEqual(rows["sample-page-only"]["next_action"], "REJECT")
        self.assertEqual(rows["sample-labeled"]["location_grade"], "PROBABLE")
        self.assertEqual(result["counts"]["verified"], 0)
        self.assertEqual(result["counts"]["exact_use_cleared"], 0)

    def test_undersized_web_derivative_asks_for_the_original(self):
        row = {r["slug"]: r for r in self.evaluate()["candidates"]}["sample-labeled"]
        self.assertEqual(row["next_action"], "REQUEST PERMISSION")
        self.assertTrue(any("original-resolution file required" in f for f in row["risk_flags"]))
        self.assertTrue(row["missing"]["resolution"])
        original = {"candidate_id": "x", "dimensions_basis": "original", "owner_contact_route": "publisher",
                    "location": {"evidence": [{"type": "source_metadata", "detail": "labeled"}]},
                    "rights": {"basis": "visible_online"}}
        fit = fit_check.evaluate(1200, 675, HERO)
        self.assertEqual(rules.decide(original, {"represents_named_place": True}, fit, TODAY)["next_action"], "REJECT")

    def test_listing_photos_are_mls_and_flag_the_home(self):
        row = {r["slug"]: r for r in self.evaluate()["candidates"]}["sample-listing"]
        self.assertTrue(row["mls"])
        self.assertEqual(row["rights_state"], "NOT CLEARED")
        self.assertTrue(any("identifiable_home" in f for f in row["risk_flags"]))
        self.assertTrue(any("not Allison's" in m for m in row["missing"]["rights"]))

    def test_owner_requirement_drift_fails_the_run(self):
        record = load_fixture("site-record-sample.json")
        record["candidates"][0]["targetCrops"]["hero"] = "16:9, at least 2400x1350"
        with self.assertRaises(evaluate_site_record.DriftError):
            self.evaluate(record)

    def test_grants_name_the_public_brand_not_the_internal_one(self):
        for row in self.evaluate()["candidates"]:
            for line in row["missing"]["rights"]:
                self.assertNotIn("AG Luxury", line)

    def test_adapter_never_writes(self):
        source = (SCRIPTS / "evaluate_site_record.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"write_text|open\([^)]*[\"'][wa]", source))

    def test_min_aspect_mode(self):
        mid = fit_check.load_profile(SKILL / "profiles" / "ag-luxury-guide-mid.json")
        wide = fit_check.evaluate(2600, 1300, mid, {"full_width_fit": "pass"})
        self.assertEqual(wide["crop"], {"x": 0, "y": 0, "w": 2600, "h": 1300})
        self.assertEqual(wide["technical_fit"], "PASS")
        narrow = fit_check.evaluate(2000, 1500, mid)
        self.assertEqual((narrow["crop"]["w"], narrow["crop"]["h"]), (2000, 1333))


if __name__ == "__main__":
    unittest.main()
