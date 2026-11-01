import json

from conftest import SCROLL_LINES, SLIDE_ONE, SLIDE_TWO
from stitch import normalize, similar

ALL_LINES = SLIDE_ONE + SCROLL_LINES + SLIDE_TWO


def _screens(hunt, route):
    data = json.loads((hunt.root / route["output_dir"] / "recovered.json").read_text())
    return [[line["text"] for line in screen["lines"]] for screen in data["screens"]]


def _matches(known, lines):
    return [n for n, line in enumerate(lines) if similar(known, line, 0.9)]


def test_known_lines_are_recovered(recovered):
    hunt, route = recovered
    assert route["status"] == "found", route
    every_line = [line for screen in _screens(hunt, route) for line in screen]
    missing = [known for known in ALL_LINES if not _matches(known, every_line)]
    assert missing == []
    text = (hunt.root / route["output_dir"] / "recovered-text.md").read_text()
    for known in ALL_LINES:
        assert normalize(known) in normalize(text)


def test_scrolling_screen_is_one_continuous_text(recovered):
    hunt, route = recovered
    screens = _screens(hunt, route)
    holding = [s for s in screens if _matches(SCROLL_LINES[0], s)]
    assert len(holding) == 1, screens
    scroll = holding[0]
    positions = []
    for known in SCROLL_LINES:
        hits = _matches(known, scroll)
        assert len(hits) == 1, (known, scroll)
        positions.append(hits[0])
    assert positions == sorted(positions)
    assert positions == list(range(positions[0], positions[0] + len(SCROLL_LINES)))
    assert len({normalize(line) for line in scroll}) == len(scroll)
    assert len(scroll) == len(SCROLL_LINES)
    for known in SLIDE_ONE + SLIDE_TWO:
        assert not _matches(known, scroll)


def test_duplicate_frames_are_dropped(recovered, synthetic_video):
    hunt, route = recovered
    data = json.loads((hunt.root / route["output_dir"] / "frames.json").read_text())
    assert data["frames_read"] == synthetic_video["frames"]
    assert data["frames_kept"] == synthetic_video["states"]
    assert data["duplicates_dropped"] == synthetic_video["frames"] - synthetic_video["states"]
    kept = [f for f in data["frames"] if f["kept"]]
    dropped = [f for f in data["frames"] if not f["kept"]]
    assert all("duplicate_of" in f for f in dropped)
    assert len(list((hunt.root / route["output_dir"] / "kept-frames").glob("*.png"))) == len(kept)
    assert list((hunt.root / route["output_dir"]).glob("contact-sheet-*.png"))
    assert not (hunt.root / route["output_dir"] / ".work").exists()


def test_window_reads_only_the_requested_stretch(synthetic_video, tmp_path):
    from evidence import Hunt
    from frames import recover_frames

    hunt = Hunt(tmp_path / "evidence")
    start = synthetic_video["slide_two_start"]
    route = recover_frames(hunt, synthetic_video["path"], start, synthetic_video["duration"])
    data = json.loads((hunt.root / route["output_dir"] / "frames.json").read_text())
    assert data["frames_read"] == round((synthetic_video["duration"] - start) * synthetic_video["fps"])
    assert data["frames_kept"] == 1
    lines = [line for screen in _screens(hunt, route) for line in screen]
    assert all(_matches(known, lines) for known in SLIDE_TWO)
    assert not any(_matches(known, lines) for known in SLIDE_ONE + SCROLL_LINES)


def test_missing_video_is_a_failed_route(tmp_path):
    from evidence import Hunt
    from frames import recover_frames

    hunt = Hunt(tmp_path / "evidence")
    route = recover_frames(hunt, tmp_path / "absent.mp4", "00:01:00", "00:02:00")
    assert route["status"] == "failed"
    assert "does not exist" in route["problems"][0]


def test_parse_time():
    from frames import format_time, parse_time

    assert parse_time("90") == 90
    assert parse_time("01:30") == 90
    assert parse_time("01:02:03.5") == 3723.5
    assert format_time(3723.5) == "01:02:03.500"


def test_bad_time_is_a_failed_route(tmp_path):
    from evidence import Hunt
    from frames import recover_frames

    hunt = Hunt(tmp_path / "evidence")
    route = recover_frames(hunt, tmp_path / "absent.mp4", "1:2:3:4", "10")
    assert route["status"] == "failed"
    assert "Cannot read time" in route["problems"][0]
    assert [r["number"] for r in hunt.routes()] == [1]


def test_variable_frame_rate_uses_real_frame_times(tmp_path):
    import shutil
    import subprocess

    from conftest import _slide
    from evidence import Hunt
    from frames import recover_frames

    slides = [["Opening slide held for three seconds"], ["Second slide right after it"], ["Third slide shortly after"]]
    durations = [3.0, 0.2, 0.2]
    listing = []
    for n, (lines, duration) in enumerate(zip(slides, durations)):
        _slide(lines).save(tmp_path / f"s{n}.png")
        listing += [f"file 's{n}.png'", f"duration {duration}"]
    listing.append(f"file 's{len(slides) - 1}.png'")
    (tmp_path / "list.txt").write_text("\n".join(listing) + "\n")
    video = tmp_path / "vfr.mkv"
    subprocess.run([shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(tmp_path / "list.txt"), "-fps_mode", "vfr", "-c:v", "ffv1", "-pix_fmt", "yuv420p",
                    str(video)], check=True)
    hunt = Hunt(tmp_path / "evidence")
    route = recover_frames(hunt, video, 0, 4)
    data = json.loads((hunt.root / route["output_dir"] / "recovered.json").read_text())
    starts = [round(screen["first_time"], 1) for screen in data["screens"]]
    assert starts == [0.0, 3.0, 3.2], data["screens"]
