#!/usr/bin/env python3
"""Source Hunter. Recover course material we can still see but no longer have as files.

Every command takes --evidence, the private evidence folder for one hunt. The
folder must be outside any git working tree. Each command adds its routes to
the hunt and rewrites report.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from discovery import DiscoveryError, run_video_discovery  # noqa: E402
from evidence import EvidenceError, Hunt  # noqa: E402
from frames import FrameError, FrameOptions, recover_frames  # noqa: E402
from report import write_report  # noqa: E402
from sweep import sweep  # noqa: E402


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--evidence", required=True, help="Private evidence folder for this hunt, outside any git repository")
    p.add_argument("--name", help="Hunt name, set the first time the folder is used")
    p.add_argument("--want", action="append", default=[], help="Something this hunt is looking for (repeatable)")
    p.add_argument("--note", action="append", default=[], help="A paraphrased note for the report (repeatable)")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("frames", help="Read on-screen text from a stretch of a local video")
    _common(f)
    f.add_argument("--video", required=True, help="Local video file")
    f.add_argument("--start", required=True, help="Start time, seconds or HH:MM:SS")
    f.add_argument("--end", required=True, help="End time, seconds or HH:MM:SS")
    f.add_argument("--label", help="Folder label for this window")
    f.add_argument("--crop", help="Only read this region, W:H:X:Y in pixels")
    f.add_argument("--lang", default="eng", help="Tesseract language, default eng")
    f.add_argument("--psm", type=int, default=6, help="Tesseract page segmentation mode, default 6")
    f.add_argument("--ocr-scale", type=float, default=2.0, help="Upscale kept frames before OCR, default 2")
    f.add_argument("--min-conf", type=float, default=40.0, help="Drop OCR lines below this mean confidence")
    f.add_argument("--change-fraction", type=float, default=0.0005,
                   help="Share of pixels that must change to count as a new frame, default 0.0005")
    f.add_argument("--keep-edge-lines", action="store_true", help="Keep lines cut by the top or bottom edge")

    s = sub.add_parser("sweep", help="Fetch public pages that need no login, through Firecrawl")
    _common(s)
    s.add_argument("--target", action="append", required=True, help="A name to search or a URL to fetch (repeatable)")
    s.add_argument("--results-per-name", type=int, default=5)
    s.add_argument("--max-pages", type=int, default=25, help="Most pages fetched in this sweep, default 25")
    s.add_argument("--blocked-domain", action="append", default=[], help="Never fetch from this domain (repeatable)")

    v = sub.add_parser("videos", help="Run the video-discovery skill. Put its arguments after --")
    _common(v)
    v.add_argument("--video-discovery", help="Path to video_discovery.py, defaults to the sibling skill")
    v.add_argument("discovery_args", nargs=argparse.REMAINDER, help="Arguments for video_discovery.py, after --")

    r = sub.add_parser("report", help="Rewrite the hunt report")
    _common(r)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        hunt = Hunt(args.evidence, name=args.name)
    except EvidenceError as exc:
        print(f"source-hunter: {exc}", file=sys.stderr)
        return 2
    hunt.add_wants(args.want)
    hunt.add_notes(args.note)
    routes = []
    try:
        if args.command == "frames":
            options = FrameOptions(lang=args.lang, psm=args.psm, ocr_scale=args.ocr_scale, min_conf=args.min_conf,
                                   change_fraction=args.change_fraction, crop=args.crop,
                                   keep_edge_lines=args.keep_edge_lines)
            routes = [recover_frames(hunt, args.video, args.start, args.end, options, label=args.label)]
        elif args.command == "sweep":
            routes = sweep(hunt, args.target, results_per_name=args.results_per_name,
                           max_pages=args.max_pages, blocked_domains=args.blocked_domain)
        elif args.command == "videos":
            routes = [run_video_discovery(hunt, args.discovery_args, script=args.video_discovery)]
    except (EvidenceError, FrameError, DiscoveryError) as exc:
        print(f"source-hunter: {exc}", file=sys.stderr)
        write_report(hunt)
        return 2
    report = write_report(hunt)
    for route in routes:
        print(json.dumps({k: route.get(k) for k in ("number", "route", "target", "status", "found", "missing", "problems")}))
    print(f"report: {report}")
    return 1 if routes and all(r.get("status") == "failed" for r in routes) else 0


if __name__ == "__main__":
    sys.exit(main())
