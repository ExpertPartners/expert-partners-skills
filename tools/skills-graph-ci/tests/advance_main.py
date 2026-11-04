"""pre-push hook body for the writer tests: advance the shared remote's main from another clone
while the writer's push is in flight, so the push is rejected exactly as a real race would be.

State file (JSON): {"dev": clone dir, "producer": fake_producer.py, "count": pushes seen,
"plan": [{"files": {path: text}, "regenerate": bool, "after": {path: text}}, ...], "forever": bool}.
Each push the writer makes applies the next plan step: commit files, optionally commit freshly
generated files on top, then commit the optional after files. With forever set, every push moves
main.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    state_path = Path(sys.argv[1])
    state = json.loads(state_path.read_text())
    count = state["count"]
    state["count"] = count + 1
    state_path.write_text(json.dumps(state))
    plan = state["plan"]
    if count < len(plan):
        step = plan[count]
    elif state.get("forever"):
        step = {"files": {f"src/churn-{count}.txt": f"churn {count}\n"}, "regenerate": False}
    else:
        return 0

    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") or k.startswith("GIT_CONFIG")}
    dev = Path(state["dev"])

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(dev), *args], check=True, env=env, capture_output=True)

    git("fetch", "-q", "origin", "main")
    git("reset", "-q", "--hard", "origin/main")
    for rel, text in step["files"].items():
        (dev / rel).parent.mkdir(parents=True, exist_ok=True)
        (dev / rel).write_text(text)
    git("add", "-A")
    git("commit", "-q", "-m", f"competing main commit {count}")
    if step.get("regenerate"):
        subprocess.run([sys.executable, state["producer"]], cwd=dev, check=True, env=env)
        git("add", "-A")
        git("commit", "-q", "-m", f"competing generated commit {count}")
    if step.get("after"):
        for rel, text in step["after"].items():
            (dev / rel).parent.mkdir(parents=True, exist_ok=True)
            (dev / rel).write_text(text)
        git("add", "-A")
        git("commit", "-q", "-m", f"competing source commit {count}")
    git("push", "-q", "origin", "HEAD:main")
    return 0


if __name__ == "__main__":
    sys.exit(main())
