"""Unlisted video discovery through the existing video-discovery skill.

This only calls that skill's command line. Its output goes to a fresh folder
inside the hunt's evidence folder.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evidence import Hunt

DEFAULT_SCRIPT = Path(__file__).resolve().parents[2] / "video-discovery" / "scripts" / "video_discovery.py"

SUMMARY_FIELDS = (
    ("candidates", "candidate video records"),
    ("new_candidates", "additional candidates beyond the seeds"),
    ("new_verified_creator", "additional records with verified creator ownership"),
    ("viewable_samples", "viewable samples"),
)


class DiscoveryError(RuntimeError):
    """The video-discovery call was not allowed."""


def _arg_value(args: list[str], flag: str) -> str | None:
    for n, arg in enumerate(args):
        if arg == flag and n + 1 < len(args):
            return args[n + 1]
        if arg.startswith(flag + "="):
            return arg.split("=", 1)[1]
    return None


def run_video_discovery(hunt: Hunt, args: list[str], script: str | Path | None = None,
                        python: str = sys.executable, timeout: float | None = None) -> dict:
    """Run video_discovery.py with args, writing its output inside the hunt."""
    args = list(args)
    if args and args[0] == "--":
        args = args[1:]
    if any(a == "--output" or a.startswith("--output=") for a in args):
        raise DiscoveryError("Do not pass --output. Source Hunter puts video-discovery output in the evidence folder.")
    script = Path(script or DEFAULT_SCRIPT)
    target = _arg_value(args, "--creator") or " ".join(args) or "no arguments"
    route = {"route": "unlisted video discovery", "target": target}
    if not script.is_file():
        route.update(status="failed", problems=[f"video-discovery command not found at {script}"],
                     missing=["Unlisted videos for this target"])
        return hunt.record_route(route)
    out_dir = hunt.fresh_dir("videos/run")
    cmd = [python, str(script), *args, "--output", str(out_dir)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = None, exc.stdout or "", f"timed out after {timeout} seconds"
        stdout = stdout.decode() if isinstance(stdout, bytes) else stdout
    console = hunt.write_text(out_dir / "source-hunter-console.txt",
                              f"exit code: {code}\n\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\n")
    summary_path = out_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    found = [f"{summary[key]} {label}" for key, label in SUMMARY_FIELDS if key in summary]
    evidence = [hunt.rel(p) for p in (out_dir / "findings.md", out_dir / "catalog.json", summary_path) if p.exists()]
    evidence.append(hunt.rel(console))
    if code == 0:
        status = "found" if summary.get("candidates") else "nothing found"
        missing = [] if summary.get("candidates") else ["No candidate videos were found"]
        problems = []
    else:
        status = "failed"
        missing = ["Unlisted videos for this target"]
        last = (stderr or "").strip().splitlines()
        problems = [f"video-discovery exited with code {code}" + (f", {last[-1][:300]}" if last else "")]
    route.update(status=status, found=found, missing=missing, problems=problems, evidence=evidence,
                 text_files=[e for e in evidence if e.endswith("findings.md")], output_dir=hunt.rel(out_dir),
                 counts={k: summary[k] for k, _ in SUMMARY_FIELDS if k in summary})
    return hunt.record_route(route)
