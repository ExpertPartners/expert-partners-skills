#!/usr/bin/env python3
"""Render private avatar bookends and join them to reviewed local footage."""

import argparse
import ast
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

PREFIX = "[HQ Internal Capability Video] "
SCREENS = {"hub", "drive-brains", "ai-department-real-work"}
REDACTIONS = {
    "client-names",
    "deal-prices",
    "private-ag-personal",
    "passwords",
    "don-private-files",
}
SEGMENTS = ("before_after", "who_uses_it_and_how")
HEX_ID = re.compile(r"[0-9a-f]{32}")
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{8,100}")
PHASES = {"pending", "processing", "waiting", "generating"}
MAX_SECONDS = 180


class RenderError(Exception):
    pass


def verified_sync(source, sha256, launch_target):
    if not source.is_absolute() or source.is_symlink() or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        return False
    source_bytes = source.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != sha256:
        return False
    result = subprocess.run(
        ["/bin/launchctl", "print", launch_target],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode or str(source) not in {
        line.strip().strip('"') for line in result.stdout.splitlines()
    }:
        return False
    tree = ast.parse(source_bytes)
    expected_loop = ast.parse("for v in videos:\n    pass").body[0]
    expected_guard = ast.parse(
        f'if (v.get("title") or "").startswith({PREFIX!r}):\n    continue'
    ).body[0]
    loops = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.For)
        and ast.dump(node.target) == ast.dump(expected_loop.target)
        and ast.dump(node.iter) == ast.dump(expected_loop.iter)
    ]
    return len(loops) == 1 and ast.dump(loops[0].body[0]) == ast.dump(expected_guard)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_link(value):
    if not isinstance(value, str):
        return False
    parts = urlparse(value)
    return (
        parts.scheme == "https"
        and bool(parts.hostname)
        and not parts.username
        and not parts.password
        and not parts.query
        and not parts.fragment
    )


def validate(spec, capture):
    if not isinstance(spec, dict) or spec.get("schema_version") != 1:
        raise RenderError("Expected a version 1 private render input.")
    chapter = spec.get("chapter_key", "")
    if not isinstance(chapter, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,79}", chapter):
        raise RenderError("Use a neutral, lowercase chapter key.")
    intent = spec.get("intent")
    if intent not in ("practice", "production") or (
        intent == "practice" and not chapter.startswith("practice-")
    ):
        raise RenderError("Practice must use a practice-prefixed chapter key.")
    if re.search(r"(?:week|w)-?0?10(?:-|$)", chapter):
        raise RenderError("Week 10 is not enabled in this standalone producer.")
    for field in ("avatar_id", "voice_id", "motion_look_id"):
        if not HEX_ID.fullmatch(str(spec.get(field, ""))):
            raise RenderError(f"Missing valid {field}.")
    if spec["motion_look_id"] == spec["avatar_id"] or spec.get("voice_kind") != "professional":
        raise RenderError("The professional voice and separate motion look are required.")
    if spec.get("internal_only") is not True:
        raise RenderError("External avatar video is not supported.")
    for segment in SEGMENTS:
        script = spec.get(segment)
        if not isinstance(script, str) or not 3 <= len(script.split()) <= 65 or len(script) > 650:
            raise RenderError(f"Use 3 to 65 words of short, reviewed narration for {segment}.")
    if not capture.is_file() or capture.suffix.lower() != ".mp4":
        raise RenderError("Provide the locally staged MP4.")
    if digest(capture) != spec.get("capture_sha256"):
        raise RenderError("The capture does not match the reviewed SHA-256.")
    if intent == "production":
        if spec.get("capture_machine") != "ember-m2" or spec.get("working_recording") is not True:
            raise RenderError("Production needs a verified Ember M2 working recording.")
        for name, entries in (("screens", SCREENS), ("redactions_verified", REDACTIONS)):
            raw = spec.get(name)
            if (
                not isinstance(raw, list)
                or any(not isinstance(item, str) for item in raw)
                or set(raw) != entries
            ):
                raise RenderError(f"Incomplete production {name} review.")
        for name in ("capture_receipt_url", "redaction_receipt_url"):
            if not safe_link(spec.get(name)):
                raise RenderError(f"Missing stable private evidence locator: {name}.")
    elif spec.get("working_recording") is not False or spec.get("capture_machine") != "synthetic":
        raise RenderError("Practice input must be synthetic and make no real-work claim.")


def payload(spec, segment):
    return {
        "type": "avatar",
        "title": PREFIX + spec["chapter_key"] + " " + segment,
        "avatar_id": spec["avatar_id"],
        "voice_id": spec["voice_id"],
        "script": spec[segment],
        "aspect_ratio": "16:9",
        "resolution": "1080p",
        "engine": {"type": "avatar_v", "reference_look_id": spec["motion_look_id"]},
        "voice_settings": {"engine_settings": {"engine_type": "heygen_voice"}},
        "motion_prompt": (
            "Speak warmly and confidently to one person. Do not wave or raise a hand in greeting. "
            "Use small, natural open handed gestures, steady eye contact, and subtle head movement."
        ),
        "caption": {"file_format": "srt", "style": "default"},
    }


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HeyGen:
    def __init__(self, secret_ref):
        if not secret_ref.startswith("op://"):
            raise RenderError("Supply a 1Password reference, never a key value.")
        run = subprocess.run(
            ["op", "read", secret_ref], capture_output=True, text=True, check=False
        )
        if run.returncode or not run.stdout.strip():
            raise RenderError("Could not resolve the HeyGen credential from 1Password.")
        self._key = run.stdout.strip()
        self._opener = build_opener(NoRedirect())

    def call(self, path, body=None, token=None):
        headers = {"X-Api-Key": self._key, "Accept": "application/json"}
        if body is not None:
            headers.update({"Content-Type": "application/json", "Idempotency-Key": token})
        request = Request(
            f"https://api.heygen.com{path}",
            headers=headers,
            data=json.dumps(body).encode() if body is not None else None,
        )
        try:
            with self._opener.open(request, timeout=30) as response:
                result = json.load(response)
        except HTTPError as error:
            raise RenderError(f"HeyGen API returned HTTP {error.code}.") from None
        except (URLError, TimeoutError):
            raise RenderError(
                "HeyGen API request did not complete. Keep the private run state."
            ) from None
        if not isinstance(result, dict) or not isinstance(result.get("data"), dict):
            raise RenderError("Unexpected HeyGen API response.")
        return result["data"]


def get_media(url, dest):
    parts = urlparse(url if isinstance(url, str) else "")
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise RenderError("HeyGen did not return an HTTPS video URL.")
    try:
        with urlopen(url, timeout=60) as response, dest.open("xb") as output:
            left = 180 * 1024 * 1024
            while chunk := response.read(1024 * 1024):
                left -= len(chunk)
                if left < 0:
                    raise RenderError("Provider output exceeded byte limit.")
                output.write(chunk)
    except (URLError, TimeoutError):
        raise RenderError("Could not download the provider video.") from None


def probe(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if result.returncode:
        raise RenderError("A media input is not a readable video.")
    value = json.loads(result.stdout)
    duration = float(value["format"]["duration"])
    streams = {row["codec_type"] for row in value["streams"]}
    if "video" not in streams or not 0 < duration <= MAX_SECONDS:
        raise RenderError("Video duration is outside (0, 180] seconds.")
    return duration, "audio" in streams


def ffmpeg(args):
    run = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *args],
        capture_output=True,
        check=False,
        timeout=240,
    )
    if run.returncode:
        raise RenderError("FFmpeg could not assemble the MP4.")


def assemble(intro, capture, outro, dest):
    inputs, filters, durations = [], [], []
    for i, path in enumerate((intro, capture, outro)):
        duration, audio = probe(path)
        durations.append(duration)
        if i != 1 and not audio:
            raise RenderError("An avatar bookend is missing its narration.")
        inputs += ["-i", str(path)]
        filters.append(
            f"[{i}:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,setpts=PTS-STARTPTS[v{i}]"
        )
        source = (
            f"[{i}:a:0]aresample=48000,aformat=channel_layouts=stereo,apad,"
            if audio
            else "anullsrc=r=48000:cl=stereo,"
        )
        filters.append(f"{source}atrim=duration={duration},asetpts=PTS-STARTPTS[a{i}]")
    if sum(durations) > MAX_SECONDS:
        raise RenderError("Combined video would exceed three minutes.")
    filters.append("[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]")
    ffmpeg(
        [
            *inputs,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-map_metadata",
            "-1",
            "-movflags",
            "+faststart",
            str(dest),
        ]
    )
    duration, audio = probe(dest)
    if not audio:
        raise RenderError("The final MP4 does not have an audio track.")
    return duration


def private_json(path, value):
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as tmp:
        temp_path = Path(tmp.name)
        try:
            json.dump(value, tmp, indent=2)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_path.replace(path)
        finally:
            temp_path.unlink(missing_ok=True)


def render(spec, capture, work, provider, sync_check, poll_seconds=5, timeout=420):
    validate(spec, capture)
    capture_seconds, _ = probe(capture)
    if capture_seconds > 155:
        raise RenderError("Leave at least 25 seconds for the two avatar bookends.")
    work.mkdir(mode=0o700, exist_ok=True)
    if work.is_symlink() or work.stat().st_mode & 0o077:
        raise RenderError("Use an owner-only private run directory.")
    with os.fdopen(
        os.open(work / "render.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600), "w"
    ) as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RenderError("This private run is already active.") from None
        _render_locked(spec, capture, work, provider, sync_check, poll_seconds, timeout)


def _render_locked(spec, capture, work, provider, sync_check, poll_seconds, timeout):
    if not sync_check(PREFIX):
        raise RenderError("Legacy sync exclusion for this exact render prefix is not verified.")
    key = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    manifest = work / "state.json"
    state = (
        json.loads(manifest.read_text())
        if manifest.exists()
        else {"fingerprint": key, "video_ids": {}}
    )
    if state.get("fingerprint") != key:
        raise RenderError("Run state belongs to a different render input.")
    private_json(manifest, state)
    pending = state["video_ids"]
    for part in SEGMENTS:
        if part not in pending:
            result = provider.call(
                "/v3/videos", payload(spec, part), "hq-capability-" + key + "-" + part
            )
            vid = result.get("video_id")
            if not isinstance(vid, str) or not VIDEO_ID.fullmatch(vid):
                raise RenderError("Provider did not return a valid video ID.")
            pending[part] = vid
            private_json(manifest, state)
    if any(not VIDEO_ID.fullmatch(str(pending[part])) for part in SEGMENTS):
        raise RenderError("Invalid provider video ID in run state.")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(dir=work) as temp:
        files = {}
        while len(files) != len(SEGMENTS):
            if time.monotonic() - started > timeout:
                raise RenderError("HeyGen did not complete in time. Resume the same private run.")
            for part in SEGMENTS:
                if part in files:
                    continue
                data = provider.call("/v3/videos/" + pending[part])
                status = data.get("status")
                if status == "completed":
                    file = Path(temp) / f"{part}.mp4"
                    get_media(data.get("video_url"), file)
                    files[part] = file
                elif status not in PHASES:
                    raise RenderError("HeyGen reported a failed or unsupported render status.")
            if len(files) < len(SEGMENTS):
                time.sleep(poll_seconds)
        # Bind assembly to the exact reviewed capture even after provider polling.
        reviewed_capture = Path(temp) / "reviewed-capture.mp4"
        shutil.copyfile(capture, reviewed_capture)
        if digest(reviewed_capture) != spec["capture_sha256"]:
            raise RenderError("The capture changed after validation.")
        result = Path(temp) / "result.mp4"
        duration = assemble(files[SEGMENTS[0]], reviewed_capture, files[SEGMENTS[1]], result)
        output = work / "internal-capability.mp4"
        result.replace(output)
        final_hash = digest(output)
        private_json(
            work / "render-receipt.json",
            {
                "schema_version": 1,
                "stage": "rendered_not_published",
                "provider": "heygen",
                "intent": spec["intent"],
                "chapter_key": spec["chapter_key"],
                "video_id": "sha256:" + final_hash,
                "provider_video_ids": pending,
                "duration_seconds": duration,
                "internal_only": True,
                "avatar_id": spec["avatar_id"],
                "voice_id": spec["voice_id"],
                "capture_machine": spec["capture_machine"],
                "working_recording": spec["working_recording"],
                "sequence": ["before-after", "working-screen", "who-uses-it-and-how"],
                "sha256": final_hash,
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--secret-ref", required=True)
    parser.add_argument("--sync-source", type=Path, required=True)
    parser.add_argument("--sync-source-sha256", required=True)
    parser.add_argument("--sync-launch-target", required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if any(shutil.which(name) is None for name in ("ffmpeg", "ffprobe", "op")):
            raise RenderError("Requires FFmpeg, FFprobe and 1Password CLI.")

        def check(prefix):
            return prefix == PREFIX and verified_sync(
                args.sync_source, args.sync_source_sha256, args.sync_launch_target
            )

        spec = json.loads(args.input.read_text())
        render(spec, args.capture, args.work, HeyGen(args.secret_ref), check)
    except (RenderError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(
            1, f"{error if isinstance(error, RenderError) else 'Private run could not complete.'}\n"
        )


if __name__ == "__main__":
    main()
