"""Stand-in for the real producers in the writer tests.

Like the extractor it records the HEAD it read in generatedFrom, and like generate-feed.mjs it
refuses invalid sources (exit 2) and has a --check mode that fails on drift (exit 1). Output is
a deterministic function of src/*.txt, so a test can recompute exactly what a tree must carry.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

GRAPH = Path("tools/skill-map/skills-graph.json")
FEED = Path("tools/capability-feed/ai-workforce-feed.json")


def sources(root: Path) -> dict[str, str]:
    return {p.name: p.read_text() for p in sorted((root / "src").glob("*.txt"))}


def render(root: Path, head: str) -> tuple[str, str]:
    src = sources(root)
    graph = {"schema": "fake/v1", "generatedFrom": {"eps": head}, "nodes": [{"id": k, "text": v} for k, v in src.items()]}
    feed = {"records": [{"id": k, "length": len(v)} for k, v in src.items()]}
    return json.dumps(graph, indent=2) + "\n", json.dumps(feed, indent=2) + "\n"


def main() -> int:
    root = Path.cwd()
    for name, text in sources(root).items():
        if "INVALID" in text:
            print(f"refused: src/{name} is invalid", file=sys.stderr)
            return 2
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    graph, feed = render(root, head)
    if "--check" in sys.argv[1:]:
        if not (root / FEED).is_file() or (root / FEED).read_text() != feed:
            print("DRIFT: feed differs from its sources", file=sys.stderr)
            return 1
        return 0
    (root / GRAPH).parent.mkdir(parents=True, exist_ok=True)
    (root / FEED).parent.mkdir(parents=True, exist_ok=True)
    (root / GRAPH).write_text(graph)
    (root / FEED).write_text(feed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
