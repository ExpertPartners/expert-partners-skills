"""Read live ordered preflight through the existing authenticated connector.

Private config contains only an endpoint and 1Password references. Credentials
stay in memory. Failure never silently restores an old owning-record snapshot.
"""

import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import urllib.request


def session_state_path(event):
    session = event.get("session_id")
    if not session:
        return None
    root = Path.home() / ".config/expert-partners/work-preflight-sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root / (hashlib.sha256(session.encode()).hexdigest() + ".json")


def refresh():
    root = Path.home() / ".config/expert-partners"
    config = json.loads((root / "work-preflight-client.json").read_text())
    endpoint = config["endpoint"]
    if not endpoint.startswith("https://") or not endpoint.endswith("/api/tools/work_preflight"):
        raise ValueError("invalid connector endpoint")
    op = shutil.which("op") or "/opt/homebrew/bin/op"
    raw = subprocess.run(
        [
            op,
            "item",
            "get",
            config["credentialItem"],
            "--vault",
            config["vault"],
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=12,
    )
    item = json.loads(raw.stdout)
    token = next(f["value"] for f in item["fields"] if f["id"] == "credential")
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"workIntent": {"action": "inspect", "capabilityId": "all"}}).encode(),
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "ExpertPartners-Work-Preflight/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        result = json.load(response)["result"]
    policy = result["policy"]
    stages = [x["stage"] for x in policy["checks"]]
    if stages != ["company_tool_builder", "skills_marketplace", "gap_build_list"]:
        raise ValueError("invalid preflight source order")
    if policy["version"] != 1 or not policy["source"]["revision"] or not policy["items"]:
        raise ValueError("incomplete owning policy")
    # Runtime view only, never an assignment or tracker. Atomic to concurrent hooks.
    import os
    import tempfile

    fd, name = tempfile.mkstemp(prefix=".work-policy-", dir=root)
    try:
        with os.fdopen(fd, "w") as output:
            json.dump(policy, output)
        Path(name).replace(root / "work-preflight-policy.json")
    finally:
        Path(name).unlink(missing_ok=True)
    return policy
