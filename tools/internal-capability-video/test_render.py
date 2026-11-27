import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from render import (
    PREFIX,
    REDACTIONS,
    SCREENS,
    RenderError,
    assemble,
    digest,
    ffmpeg,
    payload,
    probe,
    render,
    validate,
    verified_sync,
)


class Provider:
    def __init__(self, fail_second=False):
        self.calls = []
        self.fail_second = fail_second

    def call(self, path, body=None, token=None):
        self.calls.append((path, body, token))
        if body:
            if self.fail_second and len(self.calls) == 2:
                raise RenderError("Simulated interrupted submission")
            return {
                "video_id": "avatar_outro" if body["title"].endswith("and_how") else "avatar_intro"
            }
        return {"status": "completed", "video_url": "https://files.heygen.ai/test.mp4"}


class RendererTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.capture = self.root / "capture.mp4"
        self.capture.write_bytes(b"reviewed test fixture")
        self.spec = {
            "schema_version": 1,
            "chapter_key": "practice-composition",
            "intent": "practice",
            "avatar_id": "a" * 32,
            "voice_id": "b" * 32,
            "motion_look_id": "c" * 32,
            "voice_kind": "professional",
            "capture_sha256": digest(self.capture),
            "working_recording": False,
            "capture_machine": "synthetic",
            "internal_only": True,
            "before_after": "This is a private render check.",
            "who_uses_it_and_how": "This tests order and playback.",
        }

    def test_provider_contract(self):
        value = payload(self.spec, "before_after")
        self.assertEqual(value["title"], PREFIX + "practice-composition before_after")
        self.assertEqual(value["engine"]["reference_look_id"], "c" * 32)
        self.assertEqual(value["voice_id"], "b" * 32)
        self.assertNotIn("video_url", value)
        self.assertNotIn("callback_url", value)

    @patch("render.subprocess.run")
    def test_sync_requires_pinned_source_and_exact_first_guard(self, launchctl):
        source = self.root / "source.py"
        source.write_text(
            f'for v in videos:\n    if (v.get("title") or "").startswith({PREFIX!r}):\n        continue\n'
        )
        launchctl.return_value = SimpleNamespace(
            returncode=0, stdout=f"arguments = {{\n\t{source}\n}}"
        )
        self.assertTrue(verified_sync(source, digest(source), "gui/123/sync"))
        self.assertFalse(verified_sync(source, "0" * 64, "gui/123/sync"))
        source.write_text(source.read_text().replace("    if", "    print(v)\n    if"))
        self.assertFalse(verified_sync(source, digest(source), "gui/123/sync"))
        launchctl.return_value.stdout = "/elsewhere/source.py"
        self.assertFalse(verified_sync(source, digest(source), "gui/123/sync"))

    def test_refuses_public_week_ten_or_capture_change(self):
        for field, value in (("internal_only", False), ("chapter_key", "practice-week-10")):
            with self.subTest(field=field), self.assertRaises(RenderError):
                validate(self.spec | {field: value}, self.capture)
        self.capture.write_bytes(b"changed")
        with self.assertRaisesRegex(RenderError, "SHA-256"):
            validate(self.spec, self.capture)

    def test_production_requires_ember_screens_and_reviews(self):
        spec = self.spec | {
            "intent": "production",
            "chapter_key": "safe-operations",
            "capture_machine": "ember-m2",
            "working_recording": True,
            "screens": list(SCREENS),
            "redactions_verified": list(REDACTIONS),
            "capture_receipt_url": "https://example.com/capture",
            "redaction_receipt_url": "https://example.com/redaction",
        }
        validate(spec, self.capture)
        for field, value in (
            ("capture_machine", "allison-m4"),
            ("screens", ["hub"]),
            ("redactions_verified", []),
            ("capture_receipt_url", "https://example.com/capture?token=x"),
        ):
            with self.subTest(field=field), self.assertRaises(RenderError):
                validate(spec | {field: value}, self.capture)

    @patch("render.probe", return_value=(1.0, True))
    def test_no_provider_calls_without_sync_guard(self, _):
        provider = Provider()
        with self.assertRaisesRegex(RenderError, "sync exclusion"):
            render(self.spec, self.capture, self.root / "run", provider, lambda _: False)
        self.assertEqual(provider.calls, [])

    @patch("render.probe", return_value=(1.0, True))
    def test_resume_only_missing_submission_and_never_publish(self, _):
        provider = Provider(fail_second=True)
        work = self.root / "run"
        with self.assertRaisesRegex(RenderError, "interrupted"):
            render(self.spec, self.capture, work, provider, lambda p: p == PREFIX)
        state = json.loads((work / "state.json").read_text())
        self.assertEqual(state["video_ids"], {"before_after": "avatar_intro"})
        next_provider = Provider()
        with patch("render.get_media", side_effect=lambda _, file: file.write_bytes(b"video")):

            def merge(intro, capture, outro, output):
                self.assertEqual(
                    (intro.name, outro.name), ("before_after.mp4", "who_uses_it_and_how.mp4")
                )
                self.assertEqual(digest(capture), self.spec["capture_sha256"])
                output.write_bytes(b"final")
                return 55.3

            with patch("render.assemble", side_effect=merge):
                render(self.spec, self.capture, work, next_provider, lambda p: p == PREFIX)
        posts = [entry for entry in next_provider.calls if entry[1]]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0][2], provider.calls[1][2])
        receipt = json.loads((work / "render-receipt.json").read_text())
        self.assertEqual(receipt["stage"], "rendered_not_published")
        self.assertEqual(receipt["duration_seconds"], 55.3)
        self.assertFalse(receipt["working_recording"])
        self.assertNotIn("url", receipt)
        self.assertNotIn("hub_url", receipt)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg needed")
    def test_real_mux_keeps_order_audio_and_duration(self):
        paths = [self.root / f"{name}.mp4" for name in ("intro", "screen", "outro")]
        colors = ["red", "green", "blue"]
        for i, path in enumerate(paths):
            inputs = ["-f", "lavfi", "-i", f"color={colors[i]}:s=320x180:r=30:d=1"]
            if i != 1:
                inputs += ["-f", "lavfi", "-i", "sine=frequency=440:duration=1"]
            ffmpeg([*inputs, "-t", "1", "-c:v", "libx264", str(path)])
        final = self.root / "result.mp4"
        duration = assemble(*paths, final)
        self.assertAlmostEqual(duration, 3.0, delta=0.11)
        self.assertTrue(probe(final)[1])
        for i in range(3):
            raw = self.root / f"pixel-{i}.rgb"
            ffmpeg(
                [
                    "-ss",
                    str(i + 0.5),
                    "-i",
                    str(final),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=1:1",
                    "-pix_fmt",
                    "rgb24",
                    "-f",
                    "rawvideo",
                    str(raw),
                ]
            )
            components = raw.read_bytes()
            self.assertEqual(components.index(max(components)), i)


if __name__ == "__main__":
    unittest.main()
