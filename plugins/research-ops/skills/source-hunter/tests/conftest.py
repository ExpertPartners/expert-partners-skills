import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

FPS = 10
WIDTH, HEIGHT = 640, 360
FONT_SIZE = 26
LINE_HEIGHT = 48
TOP = 20

SLIDE_ONE = [
    "Synthetic course slide one",
    "Alpha lesson covers the opening idea",
    "Bravo lesson explains the second part",
    "Charlie lesson closes the first screen",
]

SCROLL_LINES = [
    "Gather the quiet maple notes",
    "Sort every copper ticket",
    "Label the velvet folders",
    "Check the harbor schedule",
    "Sketch a lantern outline",
    "Measure the granite shelf",
    "Polish the silver kettle",
    "Water the jasmine planter",
    "Fold the crimson banner",
    "Count the walnut drawers",
    "Tune the brass trumpet",
    "Pack the cedar crate",
    "Read the coral ledger",
    "Seal the amber envelope",
]

SLIDE_TWO = [
    "Closing summary slide",
    "Review the zebra checklist tonight",
    "Bring questions to the next session",
]

SLIDE_ONE_FRAMES = 6
SCROLL_HOLD_START = 4
SCROLL_STEP_PX = 16
SCROLL_STEP_FRAMES = 2
SLIDE_TWO_FRAMES = 5


def _font():
    return ImageFont.load_default(size=FONT_SIZE)


def _slide(lines):
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    for n, line in enumerate(lines):
        draw.text((30, TOP + n * LINE_HEIGHT + 10), line, fill="black", font=_font())
    return image


def _scroll_frame(offset):
    page_height = TOP * 2 + LINE_HEIGHT * len(SCROLL_LINES)
    page = Image.new("RGB", (WIDTH, page_height), "white")
    draw = ImageDraw.Draw(page)
    for n, line in enumerate(SCROLL_LINES):
        draw.text((30, TOP + n * LINE_HEIGHT + 10), line, fill="black", font=_font())
    return page.crop((0, offset, WIDTH, offset + HEIGHT))


def build_frames():
    """Return the frame images in order and the number of distinct states."""
    frames, states = [], 0
    frames += [_slide(SLIDE_ONE)] * SLIDE_ONE_FRAMES
    states += 1
    max_offset = TOP * 2 + LINE_HEIGHT * len(SCROLL_LINES) - HEIGHT
    offsets = list(range(0, max_offset, SCROLL_STEP_PX)) + [max_offset]
    for n, offset in enumerate(offsets):
        hold = SCROLL_HOLD_START if n == 0 else SCROLL_STEP_FRAMES
        frames += [_scroll_frame(offset)] * hold
        states += 1
    frames += [_slide(SLIDE_TWO)] * SLIDE_TWO_FRAMES
    states += 1
    return frames, states


def make_video(directory: Path) -> dict:
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg, "ffmpeg is required for these tests"
    frames, states = build_frames()
    still_dir = directory / "stills"
    still_dir.mkdir(parents=True)
    for n, frame in enumerate(frames):
        frame.save(still_dir / f"{n:05d}.png")
    video = directory / "synthetic-class.mkv"
    # ffv1 is lossless and built into every ffmpeg, so repeated frames stay identical.
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FPS),
         "-i", str(still_dir / "%05d.png"), "-c:v", "ffv1", "-pix_fmt", "yuv420p", str(video)],
        check=True,
    )
    shutil.rmtree(still_dir)
    slide_two_start = (len(frames) - SLIDE_TWO_FRAMES) / FPS
    return {"path": video, "frames": len(frames), "states": states, "fps": FPS,
            "duration": len(frames) / FPS, "slide_two_start": slide_two_start}


@pytest.fixture(scope="session")
def synthetic_video(tmp_path_factory):
    return make_video(tmp_path_factory.mktemp("video"))


@pytest.fixture(scope="session")
def recovered(synthetic_video, tmp_path_factory):
    from evidence import Hunt
    from frames import recover_frames

    hunt = Hunt(tmp_path_factory.mktemp("hunt") / "evidence", name="synthetic hunt")
    route = recover_frames(hunt, synthetic_video["path"], 0, synthetic_video["duration"])
    return hunt, route
