# Source Hunter command line

Python 3.11 or newer, with ffmpeg and Tesseract installed on the machine. On macOS run `brew install ffmpeg tesseract`. On Ubuntu run `sudo apt-get install ffmpeg tesseract-ocr`. ffmpeg 5.1 or newer is preferred.

Install the Python packages in a virtual environment outside this repository. The requirements file also installs what the video-discovery skill needs, because the videos command runs it.

```bash
SKILL=/absolute/path/to/expert-partners-skills/plugins/research-ops/skills/source-hunter
python3 -m venv ~/source-hunter-venv
~/source-hunter-venv/bin/pip install -r "$SKILL/requirements-dev.txt"
~/source-hunter-venv/bin/python -m pytest "$SKILL/tests" -q
```

The tests need no network. They build a small synthetic video with ffmpeg, with known lines of text and a screen that scrolls, and check what comes back.

## Commands

Every command takes `--evidence FOLDER`. The folder must be outside any git working tree, and the command stops with exit code 2 if it is not. Optional on every command are `--name` (set once per hunt), `--want ITEM` and `--note TEXT`, each repeatable. Every command rewrites `report.md` in the folder.

`frames` reads on-screen text from a local video.

- `--video FILE`, `--start TIME`, `--end TIME`. Times are seconds, MM:SS or HH:MM:SS.
- `--crop W:H:X:Y` reads only one region, useful when a webcam or toolbar shares the screen.
- `--lang eng`, `--psm 6`, `--ocr-scale 2` and `--min-conf 40` tune Tesseract.
- `--change-fraction 0.0005` is the share of pixels that must change for a frame to count as new.
- `--keep-edge-lines` keeps lines cut by the top or bottom edge, which are dropped by default because a scroll shows them whole in another frame.

Frames are decoded straight from ffmpeg in grayscale and never written to disk in bulk. Frames that do not change are grouped, and only the last frame of each group is kept and read, so a slide that types itself out is read once it is complete. Lines from each kept frame are lined up against the end of the current screen, and only lines past the overlap are added. A different screen starts a new section. Returning to an earlier screen adds nothing.

`sweep` fetches public pages through the Firecrawl API, with the key read from `FIRECRAWL_API_KEY` when the command runs.

- `--target` is a name to search or an address to fetch, repeatable.
- `--results-per-name 5`, `--max-pages 25` and `--blocked-domain DOMAIN` bound the sweep.

Pages that answer 401, 403 or 407, send us to a login page, or show a login form are listed as missing and not saved. Each saved page starts with its address and the date it was fetched.

`videos` runs the sibling video-discovery command line, `../video-discovery/scripts/video_discovery.py`. Put its arguments after `--`. Do not pass `--output`, Source Hunter sets it to a fresh folder in the evidence folder. `--video-discovery PATH` points at another copy of that script.

`report` rewrites the report with no new route.

## Exit codes

0 when at least one route ran, 1 when every route in the command failed, 2 when the evidence folder was refused or the arguments were wrong. Failed routes are still recorded in the report.

## Limitations

OCR misreads small, low contrast or stylized text. Raise `--ocr-scale` or crop to the text region. Timestamps assume a constant frame rate. The report never quotes recovered text, so read the evidence files for wording.
