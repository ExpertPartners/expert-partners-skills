#!/usr/bin/env python3
"""Install the canonical preflight hook without changing existing hooks.

The private policy input is produced from the existing Ledger, not stored in Git.
Run on each Mac after source delivery. The same installation serves every week.
"""

import argparse
import json
from pathlib import Path
import shlex
import shutil
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument(
        "--client", type=Path, help="Private existing connector endpoint and 1Password references"
    )
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text())
    assert policy["version"] == 1 and policy["source"]["revision"]
    source = Path(__file__).resolve().parent / "work-preflight.py"
    home = Path.home()
    dest = home / ".config/expert-partners/work-preflight-policy.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(policy, indent=2) + "\n")
    dest.chmod(0o600)
    if args.client:
        client = json.loads(args.client.read_text())
        assert (
            client["endpoint"].startswith("https://")
            and client["credentialItem"]
            and client["vault"]
        )
        client_dest = dest.with_name("work-preflight-client.json")
        client_dest.write_text(json.dumps(client) + "\n")
        client_dest.chmod(0o600)
    command = "/usr/bin/python3 " + shlex.quote(str(source))
    for relative, nested in [
        (".factory/hooks.json", False),
        (".codex/hooks.json", True),
        (".claude/settings.json", True),
    ]:
        path = home / relative
        data = json.loads(path.read_text()) if path.exists() else {}
        root = data.setdefault("hooks", {}) if nested else data
        hooks = root.setdefault("PreToolUse", [])
        # Replace only our own prior installation; keep every unrelated hook.
        old = json.dumps(data, sort_keys=True)
        hooks[:] = [
            h
            for h in hooks
            if not any("/work-preflight.py" in x.get("command", "") for x in h.get("hooks", []))
        ]
        hooks.insert(
            0,
            {
                "matcher": "",
                "hooks": [{"type": "command", "command": command, "timeout": 50}],
            },
        )
        if args.client:
            context_command = "/usr/bin/python3 " + shlex.quote(
                str(source.with_name("work-preflight-context.py"))
            )
            prompts = root.setdefault("UserPromptSubmit", [])
            prompts[:] = [
                h
                for h in prompts
                if not any(
                    "/work-preflight-context.py" in x.get("command", "") for x in h.get("hooks", [])
                )
            ]
            prompts.insert(
                0, {"hooks": [{"type": "command", "command": context_command, "timeout": 50}]}
            )
            ends = root.setdefault("SessionEnd", [])
            ends[:] = [
                h
                for h in ends
                if not any(
                    "/work-preflight-context.py" in x.get("command", "") for x in h.get("hooks", [])
                )
            ]
            ends.append({"hooks": [{"type": "command", "command": context_command, "timeout": 3}]})
        if json.dumps(data, sort_keys=True) != old:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                shutil.copy2(path, str(path) + ".preflight-backup-" + str(time.time_ns()))
            tmp = path.with_suffix(".preflight-tmp")
            tmp.write_text(json.dumps(data, indent=2) + "\n")
            tmp.replace(path)
        print(str(path) + " configured")
    print("Configured hooks are not proof that an already-running session loaded them.")


if __name__ == "__main__":
    main()
