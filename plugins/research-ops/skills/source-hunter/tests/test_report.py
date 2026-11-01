import sys
import textwrap
from pathlib import Path

from conftest import SCROLL_LINES
from discovery import DEFAULT_SCRIPT, run_video_discovery
from evidence import Hunt
from frames import recover_frames
from report import build_report, text_contains, write_report
from sweep import sweep
from test_sweep import PAGES, FakeClient

FAKE_DISCOVERY = textwrap.dedent("""
    import argparse, json, pathlib
    p = argparse.ArgumentParser()
    p.add_argument('--creator'); p.add_argument('--output', type=pathlib.Path)
    a, _ = p.parse_known_args()
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / 'summary.json').write_text(json.dumps({'candidates': 3, 'new_candidates': 2, 'new_verified_creator': 1}))
    (a.output / 'findings.md').write_text('# Video discovery\\n')
    print('done')
""")


def test_report_lists_every_route_tried(tmp_path, synthetic_video):
    hunt = Hunt(tmp_path / "evidence", name="synthetic gap hunt")
    hunt.add_wants(["copper ticket", "shadow board advisor", "a thing nobody has"])
    fake = tmp_path / "fake_video_discovery.py"
    fake.write_text(FAKE_DISCOVERY)

    routes = [recover_frames(hunt, synthetic_video["path"], 0, synthetic_video["duration"])]
    routes += sweep(hunt, ["https://example.org/blog/advisor", "https://example.org/broken"], client=FakeClient(PAGES))
    routes.append(run_video_discovery(hunt, ["--", "--creator", "Example Creator"], script=fake))
    routes.append(recover_frames(hunt, tmp_path / "missing.mp4", 10, 20))
    report = write_report(hunt).read_text()

    assert [r["number"] for r in routes] == [1, 2, 3, 4, 5]
    assert [r["status"] for r in routes] == ["found", "found", "failed", "found", "failed"]
    for route in routes:
        assert f"### Route {route['number']}, {route['route']}" in report
        assert f"Target: {route['target']}" in report
        assert f"Result: {route['status']}" in report
        for item in route["found"] + route["missing"] + route["problems"]:
            assert item in report
    assert "Routes tried: 5" in report
    assert "- copper ticket, found by route 1 (frame recovery)" in report
    assert "- shadow board advisor, found by route 2 (public page sweep)" in report
    assert "- a thing nobody has, still missing" in report
    missing_section = report.split("## Still missing", 1)[1]
    assert "a thing nobody has" in missing_section
    assert "route 5 (frame recovery" in missing_section
    assert "3 candidate video records" in report
    # Course text stays in the evidence files and is never quoted in the report.
    for line in SCROLL_LINES:
        assert line not in report
    assert (hunt.root / "report.md").exists()


def test_empty_hunt_report(tmp_path):
    report = build_report(Hunt(tmp_path / "evidence"))
    assert "No routes have been tried yet." in report
    assert "No sought items were named" in report


def test_video_discovery_output_flag_is_owned_by_source_hunter(tmp_path):
    import pytest

    from discovery import DiscoveryError

    with pytest.raises(DiscoveryError):
        run_video_discovery(Hunt(tmp_path / "evidence"), ["--creator", "x", "--output", "/tmp/elsewhere"])


def test_default_route_is_the_existing_video_discovery_cli():
    import subprocess

    assert DEFAULT_SCRIPT.name == "video_discovery.py"
    assert DEFAULT_SCRIPT.parent.parent.name == "video-discovery"
    help_text = subprocess.run([sys.executable, str(DEFAULT_SCRIPT), "--help"], capture_output=True, text=True, check=True).stdout
    assert "--output" in help_text and "--creator" in help_text


def test_text_contains_allows_small_misreads():
    assert text_contains("shadow-board-advisor", "the Shadow Board Advisor skill")
    assert text_contains("copper ticket", "Sort every copp3r ticket")
    assert not text_contains("copper ticket", "Sort every silver kettle")


def test_cli_runs_frames_end_to_end(tmp_path, synthetic_video, capsys):
    import source_hunter

    evidence = tmp_path / "evidence"
    code = source_hunter.main(["frames", "--evidence", str(evidence), "--name", "cli hunt", "--want", "amber envelope",
                               "--video", str(synthetic_video["path"]), "--start", "0", "--end", "00:00:05.9"])
    assert code == 0
    report = (evidence / "report.md").read_text()
    assert "Source hunt report, cli hunt" in report
    assert "- amber envelope, found by route 1" in report
    assert Path(evidence / "hunt.json").exists()


def test_text_contains_matches_whole_words_only():
    assert not text_contains("API", "a rapid start")
    assert not text_contains("Week 1", "Week 10 recap")
    assert text_contains("Week 1", "Notes from Week 1 recap")


FAKE_RESUMABLE = textwrap.dedent("""
    import argparse, json, pathlib
    p = argparse.ArgumentParser()
    p.add_argument('--creator'); p.add_argument('--output', type=pathlib.Path); p.add_argument('--resume', action='store_true')
    p.add_argument('--seeds')
    a, _ = p.parse_known_args()
    a.output.mkdir(parents=True, exist_ok=True)
    log = a.output / 'requests.jsonl'
    if a.resume and not log.exists():
        raise SystemExit('nothing to resume')
    with log.open('a') as f:
        f.write('{}\\n')
    new = 0 if a.seeds else 1
    (a.output / 'summary.json').write_text(json.dumps({'candidates': 2, 'new_candidates': new}))
""")


def test_video_discovery_resume_reuses_the_latest_run(tmp_path):
    hunt = Hunt(tmp_path / "evidence")
    fake = tmp_path / "fake.py"
    fake.write_text(FAKE_RESUMABLE)
    missing = run_video_discovery(hunt, ["--creator", "X", "--resume"], script=fake)
    assert missing["status"] == "failed" and "no earlier video run" in missing["problems"][0]
    first = run_video_discovery(hunt, ["--creator", "X"], script=fake)
    resumed = run_video_discovery(hunt, ["--creator", "X", "--resume"], script=fake)
    assert first["output_dir"] == resumed["output_dir"] == "videos/run-01"
    assert resumed["status"] == "found"
    assert len((hunt.root / "videos/run-01/requests.jsonl").read_text().splitlines()) == 2


def test_seed_only_video_run_is_not_found(tmp_path):
    hunt = Hunt(tmp_path / "evidence")
    fake = tmp_path / "fake.py"
    fake.write_text(FAKE_RESUMABLE)
    route = run_video_discovery(hunt, ["--creator", "X", "--seeds", "known.json"], script=fake)
    assert route["status"] == "nothing found"
    assert "beyond the seeds" in route["missing"][0]
