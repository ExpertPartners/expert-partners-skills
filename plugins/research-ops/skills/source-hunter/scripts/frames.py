"""Frame recovery. Read the on-screen text from a stretch of a local video.

Every frame in the window is decoded at the source frame rate with ffmpeg.
Frames that do not change are grouped into runs and only the last frame of
each run is kept, so duplicates are dropped before OCR. Kept frames are read
with Tesseract and stitched into continuous screens.
"""

from __future__ import annotations

import csv
import io
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from evidence import Hunt, slug
from stitch import Line, Screen, stitch


class FrameError(RuntimeError):
    """Frame recovery could not run."""


@dataclass
class FrameOptions:
    lang: str = "eng"
    psm: int = 6
    ocr_scale: float = 2.0
    min_conf: float = 40.0
    noise: int = 40
    change_fraction: float = 0.0005
    min_changed_pixels: int = 30
    crop: str | None = None
    keep_edge_lines: bool = False
    sheet_columns: int = 4
    sheet_rows: int = 4
    thumb_width: int = 320


def parse_time(value: str | float | int) -> float:
    """Accept seconds, MM:SS or HH:MM:SS, each with optional decimals."""
    if isinstance(value, (int, float)):
        seconds = float(value)
    else:
        parts = str(value).strip().split(":")
        if not 1 <= len(parts) <= 3 or any(p == "" for p in parts):
            raise FrameError(f"Cannot read time {value!r}. Use seconds, MM:SS or HH:MM:SS.")
        try:
            numbers = [float(p) for p in parts]
        except ValueError as exc:
            raise FrameError(f"Cannot read time {value!r}. Use seconds, MM:SS or HH:MM:SS.") from exc
        seconds = 0.0
        for number in numbers:
            seconds = seconds * 60 + number
    if seconds < 0:
        raise FrameError("Times cannot be negative.")
    return seconds


def format_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def require_tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise FrameError(f"{name} is not installed or not on PATH. Install ffmpeg and Tesseract first.")
    return found


def probe_frame_rate(video: Path) -> float:
    ffprobe = require_tool("ffprobe")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=avg_frame_rate,r_frame_rate", "-of", "json", str(video)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise FrameError(f"ffprobe could not read {video.name}: {result.stderr.strip()[-400:]}")
    streams = json.loads(result.stdout or "{}").get("streams") or []
    if not streams:
        raise FrameError(f"{video.name} has no video stream.")
    for key in ("avg_frame_rate", "r_frame_rate"):
        raw = streams[0].get(key) or "0/0"
        try:
            rate = Fraction(raw)
        except (ValueError, ZeroDivisionError):
            continue
        if rate > 0:
            return float(rate)
    raise FrameError(f"Cannot read the frame rate of {video.name}.")


SHOWINFO = re.compile(r"\bn:\s*(\d+)\s+pts:\s*\S+\s+pts_time:\s*(-?[0-9.]+)")


def _filters(options: FrameOptions, showinfo: bool = False) -> list[str]:
    chain = []
    if options.crop:
        parts = options.crop.replace("x", ":").split(":")
        if len(parts) != 4 or not all(p.isdigit() for p in parts):
            raise FrameError("Crop must be W:H:X:Y in pixels, for example 1280:600:0:120.")
        chain.append("crop=" + ":".join(parts))
    if showinfo:
        # showinfo logs each frame's real presentation time, which matters for variable frame rate recordings.
        chain.append("showinfo")
    return ["-vf", ",".join(chain)] if chain else []


def frame_times(log_text: str) -> dict[int, float]:
    """Map frame number to presentation time from showinfo log lines."""
    times = {}
    for line in log_text.splitlines():
        if "showinfo" in line:
            match = SHOWINFO.search(line)
            if match:
                times[int(match.group(1))] = float(match.group(2))
    return times


def _first_frame_size(ffmpeg: str, video: Path, start: float, options: FrameOptions, work: Path) -> tuple[int, int]:
    # Decoding one frame through the same filters gives the size after rotation and crop.
    probe_png = work / "size-probe.png"
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-i", str(video),
           "-map", "0:v:0", "-frames:v", "1", *_filters(options), str(probe_png)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not probe_png.exists():
        raise FrameError(f"ffmpeg could not decode a frame at {format_time(start)}: {result.stderr.strip()[-400:]}")
    with Image.open(probe_png) as image:
        size = image.size
    probe_png.unlink()
    return size


def iter_gray_frames(video: Path, start: float, end: float, options: FrameOptions, work: Path,
                     times: dict[int, float] | None = None):
    """Yield every decoded frame in [start, end) as a grayscale image.

    When times is given, it is filled after decoding with each frame's
    presentation time in seconds from the start of the window.
    """
    ffmpeg = require_tool("ffmpeg")
    width, height = _first_frame_size(ffmpeg, video, start, options, work)
    frame_bytes = width * height
    log_path = work / "ffmpeg-stderr.txt"
    base = [ffmpeg, "-hide_banner", "-nostats", "-loglevel", "info", "-ss", f"{start:.3f}", "-i", str(video),
            "-t", f"{end - start:.3f}", "-map", "0:v:0", "-an"]
    tail = [*_filters(options, showinfo=True), "-pix_fmt", "gray", "-f", "rawvideo", "-"]
    for sync in (["-fps_mode", "passthrough"], ["-vsync", "passthrough"]):
        yielded = 0
        with log_path.open("w") as log:
            proc = subprocess.Popen([*base, *sync, *tail], stdout=subprocess.PIPE, stderr=log)
            try:
                while True:
                    chunk = proc.stdout.read(frame_bytes)
                    if len(chunk) < frame_bytes:
                        break
                    yielded += 1
                    yield Image.frombytes("L", (width, height), chunk)
            finally:
                proc.stdout.close()
                code = proc.wait()
        message = log_path.read_text(errors="replace")
        if code == 0:
            if times is not None:
                times.update(frame_times(message))
            return
        message = "\n".join(l for l in message.splitlines() if "showinfo" not in l)
        if yielded == 0 and "fps_mode" in message:
            continue  # older ffmpeg without -fps_mode
        raise FrameError(f"ffmpeg failed while reading frames: {message.strip()[-400:]}")


def changed_pixels(a: Image.Image, b: Image.Image, noise: int) -> int:
    diff = ImageChops.difference(a, b).point(lambda v: 255 if v > noise else 0)
    return diff.histogram()[255]


def ocr_lines(image_path: Path, options: FrameOptions, work: Path) -> list[Line]:
    """Read text lines with Tesseract, dropping low confidence lines and lines cut by the frame edge."""
    tesseract = require_tool("tesseract")
    with Image.open(image_path) as image:
        if options.ocr_scale and options.ocr_scale != 1:
            size = (round(image.width * options.ocr_scale), round(image.height * options.ocr_scale))
            image = image.resize(size, Image.LANCZOS)
        scaled = work / "ocr-input.png"
        image.save(scaled)
        height = image.height
    result = subprocess.run(
        [tesseract, str(scaled), "stdout", "-l", options.lang, "--psm", str(options.psm), "tsv"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise FrameError(f"Tesseract failed: {result.stderr.strip()[-400:]}")
    rows = csv.DictReader(io.StringIO(result.stdout), delimiter="\t", quoting=csv.QUOTE_NONE)
    grouped: dict[tuple, dict] = {}
    for row in rows:
        word = (row.get("text") or "").strip()
        try:
            conf = float(row.get("conf") or -1)
        except ValueError:
            conf = -1
        if row.get("level") != "5" or not word or conf < 0:
            continue
        key = (int(row["block_num"]), int(row["par_num"]), int(row["line_num"]))
        top, bottom = int(row["top"]), int(row["top"]) + int(row["height"])
        entry = grouped.setdefault(key, {"words": [], "confs": [], "top": top, "bottom": bottom})
        entry["words"].append(word)
        entry["confs"].append(conf)
        entry["top"] = min(entry["top"], top)
        entry["bottom"] = max(entry["bottom"], bottom)
    edge = max(2, round(2 * (options.ocr_scale or 1)))
    lines = []
    for entry in grouped.values():
        text = " ".join(entry["words"])
        conf = sum(entry["confs"]) / len(entry["confs"])
        if conf < options.min_conf or sum(ch.isalnum() for ch in text) < 2:
            continue
        if not options.keep_edge_lines and (entry["top"] <= edge or entry["bottom"] >= height - edge):
            continue
        lines.append((entry["top"], Line(text=text, conf=round(conf, 1))))
    lines.sort(key=lambda pair: pair[0])
    return [line for _, line in lines]


def _contact_sheets(hunt: Hunt, out_dir: Path, kept: list[dict], options: FrameOptions) -> list[Path]:
    sheets = []
    per_sheet = options.sheet_columns * options.sheet_rows
    font = ImageFont.load_default()
    for sheet_number, offset in enumerate(range(0, len(kept), per_sheet), start=1):
        batch = kept[offset: offset + per_sheet]
        thumbs = []
        for record in batch:
            with Image.open(hunt.root / record["image"]) as image:
                ratio = options.thumb_width / image.width
                thumbs.append((image.convert("RGB").resize((options.thumb_width, max(1, round(image.height * ratio)))), record))
        cell_h = max(t.height for t, _ in thumbs) + 18
        rows = (len(thumbs) + options.sheet_columns - 1) // options.sheet_columns
        sheet = Image.new("RGB", (options.sheet_columns * (options.thumb_width + 8) + 8, rows * (cell_h + 8) + 8), "white")
        draw = ImageDraw.Draw(sheet)
        for n, (thumb, record) in enumerate(thumbs):
            x = 8 + (n % options.sheet_columns) * (options.thumb_width + 8)
            y = 8 + (n // options.sheet_columns) * (cell_h + 8)
            sheet.paste(thumb, (x, y))
            draw.text((x, y + thumb.height + 3), f"frame {record['index']}  {format_time(record['time'])}", fill="black", font=font)
        path = out_dir / f"contact-sheet-{sheet_number:02d}.png"
        sheet.save(path)
        sheets.append(path)
    return sheets


def _recovered_markdown(video_name: str, start: float, end: float, screens: list[Screen]) -> str:
    out = [f"# Recovered on-screen text", "",
           f"Video file: {video_name}", f"Window: {format_time(start)} to {format_time(end)}",
           "Confidential course text. Keep this file in the private evidence folder.", ""]
    if not screens:
        out.append("No text was recovered in this window.")
    for number, screen in enumerate(screens, start=1):
        out += [f"## Screen {number}, {format_time(screen.first_time)} to {format_time(screen.last_time)}", ""]
        out += [line.text for line in screen.lines]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def recover_frames(hunt: Hunt, video: str | Path, start: str | float, end: str | float,
                   options: FrameOptions | None = None, label: str | None = None) -> dict:
    """Run frame recovery and record it as one route of the hunt."""
    options = options or FrameOptions()
    video = Path(video).expanduser()
    route = {"route": "frame recovery", "target": f"{video.name}, {start} to {end}"}
    work = None
    try:
        start_s, end_s = parse_time(start), parse_time(end)
        route["target"] = f"{video.name}, {format_time(start_s)} to {format_time(end_s)}"
        if not video.is_file():
            raise FrameError(f"The video file {video} does not exist. Download it locally first.")
        if end_s <= start_s:
            raise FrameError("The end time must be after the start time.")
        for tool in ("ffmpeg", "ffprobe", "tesseract"):
            require_tool(tool)
        fps = probe_frame_rate(video)
        out_dir = hunt.fresh_dir("frames/" + slug(label or f"{video.stem}-{int(start_s)}-{int(end_s)}"))
        kept_dir = out_dir / "kept-frames"
        kept_dir.mkdir()
        work = out_dir / ".work"
        work.mkdir()

        records: list[dict] = []
        kept: list[dict] = []
        run_start = previous = None
        run_members: list[int] = []

        def close_run():
            if previous is None:
                return
            last_index = run_members[-1]
            record = records[last_index]
            image_path = kept_dir / f"frame-{last_index:06d}.png"
            previous[1].save(image_path)
            record["kept"] = True
            record["image"] = hunt.rel(image_path)
            for member in run_members[:-1]:
                records[member]["duplicate_of"] = last_index
            kept.append(record)

        pts: dict[int, float] = {}
        for index, image in enumerate(iter_gray_frames(video, start_s, end_s, options, work, pts)):
            records.append({"index": index, "time": round(start_s + index / fps, 3), "kept": False})
            if run_start is not None:
                threshold = max(options.min_changed_pixels, options.change_fraction * image.width * image.height)
                if changed_pixels(run_start, image, options.noise) > threshold:
                    close_run()
                    run_start, run_members = None, []
            if run_start is None:
                run_start = image
            run_members.append(index)
            previous = (index, image)
        close_run()

        if not records:
            raise FrameError("No frames were decoded in that window. Check the times against the video length.")
        if len(pts) == len(records):
            for record in records:
                record["time"] = round(start_s + pts[record["index"]], 3)
        for record in kept:
            members = [r for r in records if r.get("duplicate_of") == record["index"]]
            record["first_seen"] = members[0]["time"] if members else record["time"]

        frames_for_stitch = []
        for record in kept:
            lines = ocr_lines(hunt.root / record["image"], options, work)
            record["lines"] = [{"text": l.text, "conf": l.conf} for l in lines]
            frames_for_stitch.append((record["index"], record["first_seen"], record["time"], lines))
        screens = stitch(frames_for_stitch)

        sheets = _contact_sheets(hunt, out_dir, kept, options)
        recovered_md = hunt.write_text(out_dir / "recovered-text.md", _recovered_markdown(video.name, start_s, end_s, screens))
        hunt.write_json(out_dir / "recovered.json", {
            "video": video.name, "start": start_s, "end": end_s, "frame_rate": fps,
            "screens": [s.to_dict() for s in screens],
        })
        hunt.write_json(out_dir / "frames.json", {
            "video": video.name, "start": start_s, "end": end_s, "frame_rate": fps,
            "frames_read": len(records), "frames_kept": len(kept),
            "duplicates_dropped": len(records) - len(kept),
            "options": options.__dict__, "frames": records,
        })
        line_count = sum(len(s.lines) for s in screens)
        route.update(
            status="found" if line_count else "nothing found",
            found=[
                f"{len(records)} frames read at {fps:g} frames per second",
                f"{len(records) - len(kept)} duplicate frames dropped, {len(kept)} distinct frames kept",
                f"{line_count} lines of text recovered across {len(screens)} screens",
                f"{len(sheets)} contact sheets saved",
            ],
            missing=[] if line_count else ["No readable on-screen text in this window"],
            evidence=[hunt.rel(recovered_md), hunt.rel(out_dir / "recovered.json"), hunt.rel(out_dir / "frames.json"),
                      *[hunt.rel(p) for p in sheets]],
            text_files=[hunt.rel(recovered_md)],
            counts={"frames_read": len(records), "frames_kept": len(kept),
                    "duplicates_dropped": len(records) - len(kept), "screens": len(screens), "lines": line_count},
            output_dir=hunt.rel(out_dir),
        )
    except FrameError as exc:
        route.update(status="failed", problems=[str(exc)], missing=["On-screen text for this window"])
    finally:
        if work is not None:
            shutil.rmtree(work, ignore_errors=True)
    return hunt.record_route(route)
