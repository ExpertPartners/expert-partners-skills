import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "plugins/content-engines/skills/week-wrap/scripts/check_completeness.py"
)
LINK = "https://example.com/evidence"
IDENTITIES = dict(brand_book_id="book", kit_id="kit", deck_id="deck", master_notes_id="notes")


def ready_package():
    fields = {
        "advantage-brief": {},
        "run-of-show": {},
        "canva-chapter": dict(
            **IDENTITIES,
            owner="Fixture owner",
            owner_url=LINK,
            brand_url=LINK,
            append_route_url=LINK,
            master_notes_route_url=LINK,
        ),
        "presenter-notes": dict(notes_write_url=LINK, notes_read_url=LINK),
        "internal-video": dict(
            avatar_id="avatar",
            voice_id="voice",
            voice_kind="professional",
            capture_machine="ember-m2",
            avatar_voice_url=LINK,
            capture_route_url=LINK,
            sanitization_route_url=LINK,
            renderer_route_url=LINK,
            internal_hub_route_url=LINK,
        ),
        "canva-video-slide": dict(
            embed_route_url=LINK,
            playback_route_url=LINK,
            external_exclusion_route_url=LINK,
        ),
    }
    return {
        "inventory_url": LINK,
        "expected": list(fields),
        "evidence": {key: dict(status="ready", url=LINK, **value) for key, value in fields.items()},
    }


def check(statuses, **fields):
    return {
        "inventory_url": LINK,
        "expected": list(statuses),
        "evidence": {
            key: {"status": status, "url": LINK, **fields} for key, status in statuses.items()
        },
    }


def valid_week():
    return {
        "route": "week",
        "week": 10,
        "checks": {
            "readiness": check(
                {"HQ:first": "Covered", "EP:first": "Test", "AG:first": "Skip"},
                reason="example reason",
            ),
            "decisions": check(
                {"day-1-a": "implemented", "day-1-b": "routed"},
                receipt_url=LINK,
                owner="Fixture owner",
            ),
            "close": check(
                dict.fromkeys(
                    [
                        "engine",
                        "wheels",
                        "steering",
                        "gas",
                        "transmission",
                        "dashboard",
                        "maintenance",
                        "brain-walkthrough",
                    ],
                    "passed",
                )
            ),
            "tools": check({"doc-maker": "owned"}, owner="Fixture owner"),
            "sources": check(
                {"p1": "search", "p2": "have it", "p3": "create our own"}, reason="example reason"
            ),
            "package": ready_package(),
        },
    }


class CompletenessCLI(unittest.TestCase):
    def run_gate(self, payload, *args):
        p = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )
        return p.returncode, json.loads(p.stdout)

    def test_preflight_passes_without_existing_package(self):
        self.assertEqual(self.run_gate(valid_week()), (0, {"preflight": "passed", "gaps": []}))

    def test_every_week_criterion_blocks_missing_evidence(self):
        for section, key in [
            ("readiness", "AG:first"),
            ("decisions", "day-1-b"),
            ("close", "brain-walkthrough"),
            ("tools", "doc-maker"),
            ("sources", "p1"),
            ("package", "canva-chapter"),
        ]:
            with self.subTest(section=section):
                packet = valid_week()
                del packet["checks"][section]["evidence"][key]
                code, result = self.run_gate(packet)
                self.assertEqual(code, 1)
                self.assertEqual(
                    result["gaps"],
                    [{"check": section, "key": key, "gap": "missing evidence", "url": LINK}],
                )

    def test_cannot_hide_company_or_week_ten_close_key_by_dropping_both(self):
        data = valid_week()
        for section, key in [("readiness", "EP:first"), ("close", "dashboard")]:
            data["checks"][section]["expected"].remove(key)
            del data["checks"][section]["evidence"][key]
        code, result = self.run_gate(data)
        self.assertEqual(code, 1)
        self.assertEqual({gap["key"] for gap in result["gaps"]}, {"EP:first", "dashboard"})

    def test_dispositions_require_evidence_owner_and_reason(self):
        data = valid_week()
        for section, key, field in [
            ("readiness", "EP:first", "reason"),
            ("decisions", "day-1-a", "receipt_url"),
            ("decisions", "day-1-b", "owner"),
            ("tools", "doc-maker", "owner"),
            ("sources", "p2", "reason"),
        ]:
            data["checks"][section]["evidence"][key][field] = " "
        data["checks"]["package"]["evidence"]["canva-chapter"]["status"] = "read-only"
        code, result = self.run_gate(data)
        self.assertEqual(code, 1)
        self.assertEqual(len(result["gaps"]), 6)

    def test_attended_session_does_not_require_a_curriculum_week(self):
        data = {
            "route": "session",
            "checks": {
                "session": check({"intent": "verified", "source-review": "verified"}),
                "package": copy.deepcopy(valid_week()["checks"]["package"]),
            },
        }
        self.assertEqual(self.run_gate(data)[0], 0)
        del data["checks"]["session"]["evidence"]["intent"]
        self.assertEqual(self.run_gate(data)[0], 1)

    def test_missing_inventory_never_counts_as_empty(self):
        data = valid_week()
        data["checks"]["sources"] = check({})
        self.assertEqual(self.run_gate(data)[0], 0)
        del data["checks"]["sources"]["inventory_url"]
        self.assertEqual(self.run_gate(data)[0], 1)

    def test_week_zero_uses_its_own_close_criteria(self):
        data = valid_week()
        data["week"] = 0
        data["checks"]["close"] = check({"fixture-close": "passed"})
        self.assertEqual(self.run_gate(data)[0], 0)

    def test_malformed_inputs_fail_closed(self):
        self.assertEqual(self.run_gate(None)[0], 1)
        data = valid_week()
        data["checks"]["close"]["expected"] = [{}]
        self.assertEqual(self.run_gate(data)[0], 1)
        p = subprocess.run(
            [sys.executable, str(SCRIPT)], input="{", text=True, capture_output=True, check=False
        )
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["preflight"], "blocked")

    def test_missing_new_routes_fail_even_if_inventory_omits_them(self):
        data = valid_week()
        package = data["checks"]["package"]
        for key in ("internal-video", "canva-video-slide", "presenter-notes"):
            package["expected"].remove(key)
            del package["evidence"][key]
        self.assertEqual(
            {g["key"] for g in self.run_gate(data)[1]["gaps"]},
            {"internal-video", "canva-video-slide", "presenter-notes"},
        )

    def test_preflight_blocks_unverified_ownership_and_media_routes(self):
        for key, field, bad in [
            ("canva-chapter", "owner", None),
            ("canva-chapter", "brand_book_id", None),
            ("canva-chapter", "master_notes_route_url", None),
            ("presenter-notes", "notes_write_url", None),
            ("internal-video", "voice_kind", "stock"),
            ("internal-video", "avatar_id", None),
            ("internal-video", "capture_machine", "m4"),
            ("internal-video", "sanitization_route_url", None),
            ("internal-video", "renderer_route_url", None),
            ("canva-video-slide", "external_exclusion_route_url", None),
        ]:
            with self.subTest(key=key, missing=field):
                data = valid_week()
                data["checks"]["package"]["evidence"][key][field] = bad
                code, out = self.run_gate(data)
                self.assertEqual(code, 1)
                self.assertEqual([(g["key"], g["url"]) for g in out["gaps"]], [(key, LINK)])

    @staticmethod
    def saved():
        packet = valid_week()
        fields = {
            "advantage-brief": dict(rendered_pages=1),
            "run-of-show": dict(timing_reconciled=True),
            "canva-chapter": dict(
                **IDENTITIES,
                title="From scattered work to shared context",
                master_notes_url=LINK,
                page_ids=["opener", "internal"],
                source_week_visible=False,
                source_week_in_master_notes=True,
                prior_chapters_preserved=True,
            ),
            "presenter-notes": dict(
                pages={
                    p: dict(
                        readback_url=LINK,
                        full_read_as_is_script=True,
                        actual_canva_notes_match=True,
                    )
                    for p in ("opener", "internal")
                }
            ),
            "internal-video": dict(
                video_id="only-video",
                provider="heygen",
                intent="production",
                duration_seconds=180,
                avatar_id="avatar",
                voice_id="voice",
                capture_machine="ember-m2",
                working_recording=True,
                internal_only=True,
                chapter_video_count=1,
                screens=["hub", "drive-brains", "ai-department-real-work"],
                redactions_verified=[
                    "client-names",
                    "deal-prices",
                    "private-ag-personal",
                    "passwords",
                    "don-private-files",
                ],
                audience=["don", "team", "future-human-hires", "future-ai-hires"],
                sequence=["before-after", "working-screen", "who-uses-it-and-how"],
                hub_url=LINK,
                capture_receipt_url=LINK,
                redaction_receipt_url=LINK,
                media_playback_url=LINK,
                internal_access_receipt_url=LINK,
            ),
            "canva-video-slide": dict(
                deck_id="deck",
                page_id="internal",
                video_id="only-video",
                dedicated_slide=True,
                playback_verified=True,
                external_exclusion_verified=True,
                notes_what_and_when=True,
                playback_url=LINK,
                external_exclusion_url=LINK,
            ),
        }
        packet["completion"] = {
            "run_log_url": LINK,
            "preflight_receipt_url": LINK,
            "evidence": {k: dict(url=LINK, readback_url=LINK, **v) for k, v in fields.items()},
        }
        return packet

    def test_saved_completion_accepts_exact_duration_boundary(self):
        self.assertEqual(
            self.run_gate(self.saved(), "--saved"), (0, {"completion": "passed", "gaps": []})
        )

    def test_each_saved_artifact_and_readback_is_required(self):
        for key in self.saved()["completion"]["evidence"]:
            with self.subTest(key=key):
                data = self.saved()
                del data["completion"]["evidence"][key]["readback_url"]
                code, out = self.run_gate(data, "--saved")
                self.assertEqual(code, 1)
                self.assertEqual([g["key"] for g in out["gaps"]], [key])
        self.assertEqual(self.run_gate(valid_week(), "--saved")[0], 1)
        data = self.saved()
        del data["completion"]["preflight_receipt_url"]
        self.assertEqual(
            [g["key"] for g in self.run_gate(data, "--saved")[1]["gaps"]], ["preflight"]
        )

    def test_saved_completion_rejects_wrong_assets_or_unsafe_or_unplayable_media(self):
        for key, field, bad in [
            ("canva-chapter", "title", "Week #10"),
            ("canva-chapter", "source_week_visible", True),
            ("canva-chapter", "kit_id", "second kit"),
            ("canva-chapter", "page_ids", ["opener", "opener"]),
            ("presenter-notes", "pages", {"opener": {}}),
            ("internal-video", "duration_seconds", 180.01),
            ("internal-video", "duration_seconds", True),
            ("internal-video", "capture_machine", "m4"),
            ("internal-video", "intent", "practice"),
            ("internal-video", "voice_id", "other"),
            ("internal-video", "chapter_video_count", 2),
            ("internal-video", "screens", ["hub"]),
            ("internal-video", "redactions_verified", ["passwords"]),
            ("internal-video", "media_playback_url", None),
            ("internal-video", "internal_access_receipt_url", None),
            ("canva-video-slide", "playback_verified", False),
            ("canva-video-slide", "external_exclusion_verified", False),
            ("canva-video-slide", "notes_what_and_when", False),
            ("canva-video-slide", "video_id", "another-video"),
            ("canva-video-slide", "page_id", "outside-chapter"),
        ]:
            with self.subTest(key=key, field=field):
                data = self.saved()
                data["completion"]["evidence"][key][field] = bad
                code, out = self.run_gate(data, "--saved")
                self.assertEqual(code, 1)
                self.assertIn(key, {g["key"] for g in out["gaps"]})
