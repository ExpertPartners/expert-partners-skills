"""Run the installed marketplace skill against synthetic failing storage.

Normal Codex account and CODEX_HOME are preserved. No skill is copied/installed.
Only the synthetic MCP adapter is configured for this isolated invocation.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
FIRST = "[SYN][V1.0] About Us.md"
PROMPT = """$business-brain-foundations

Exercise the actual installed marketplace skill on synthetic company SYN.
This is a controlled first-file finalization task, not real company work.
The supervising operator has read the current governing authority and approved
specification. Do not claim you performed their reads. Do not call live services,
research any website, access credentials, create local final business files, or
change account/configuration/skill files. The registered foundations_fixture MCP
is the storage adapter for Company Core [SYN-BB]. Its tool results are real events
of this fixture, not production Drive results. Use it for final saves and reopens.

The synthetic user has completed first-file clarification, accepts explicit
unknowns and approves this final first draft unchanged. Continue the installed
skill from finalizing and saving this About Us. All input below is fictional.

Name [SYN][V1.0] About Us.md

# About Us

## Positioning Statement
SYN helps fictional teams organize reusable notes. Its test customer is a
fictional team with scattered documentation.

## Mission
Make fictional documentation easier to find.

## What We Do
We organize synthetic notes. We keep their source context visible.

## What We Don't Do
We do not claim real customer outcomes.

## Key People
Example Owner, Founder, maintains the synthetic catalog.

## Values
Clarity means using explicit source labels.

At the end, report observed storage results accurately. Do not explain or
simulate what the skill would do. Execute its actual procedure.
"""


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def judge_storage(events):
    """Fixed transport assertions only; this is never a native activation verdict."""
    saves = [event for event in events if event.get("tool") == "save_file"]
    expected_names = [event.get("arguments", {}).get("name") for event in saves]
    return {
        "first_file_attempts": expected_names.count(FIRST),
        "exactly_two_same_first_file_attempts": expected_names == [FIRST, FIRST],
        "both_attempts_observed_as_errors": len(saves) == 2 and all(
            event.get("result", {}).get("isError") is True for event in saves),
        "other_file_tool_calls": [event for event in events
                                  if event.get("tool") in ("save_file", "read_file")
                                  and event.get("arguments", {}).get("name") != FIRST],
        "save_content_unchanged": len(saves) == 2 and
            saves[0].get("arguments", {}).get("content") ==
            saves[1].get("arguments", {}).get("content"),
    }


def runtime_failures(events):
    """Keep native transport/trust rejection distinct from expected storage errors."""
    failures = []
    for event in events:
        if event.get("type") in ("error", "turn.failed"):
            failures.append(event)
        item = event.get("item", {})
        if (event.get("type") == "item.completed" and
                item.get("type") == "mcp_tool_call" and item.get("error")):
            failures.append({"type": "mcp_transport_rejection", "server": item.get("server"),
                             "tool": item.get("tool"), "error": item["error"]})
    return failures


def command(codex, workspace, events, final):
    config = {
        "apps._default.enabled": False,
        "features.apps": False,
        "plugins._default.enabled": False,
        "plugins.operating-doctrine@expert-partners.enabled": True,
        "mcp_servers.foundations_fixture.command": sys.executable,
        "mcp_servers.foundations_fixture.args": [str(HERE / "server.py"), "--events", str(events)],
        "mcp_servers.foundations_fixture.startup_timeout_sec": 15,
        "mcp_servers.foundations_fixture.tool_timeout_sec": 20,
        "mcp_servers.foundations_fixture.default_tools_approval_mode": "approve",
        "model_reasoning_effort": "medium",
        "shell_environment_policy.inherit": "core",
        "shell_environment_policy.experimental_use_profile": False,
    }
    args = [str(codex), "exec", "--ignore-user-config", "--json", "--ephemeral",
            "--sandbox", "read-only", "--skip-git-repo-check", "--model", "gpt-6.1-sol",
            "--cd", str(workspace), "--output-last-message", str(final)]
    for key, value in config.items():
        # JSON primitives/arrays are also valid TOML values for these settings.
        args.extend(["-c", key + "=" + json.dumps(value)])
    return args + ["-"]


def run(codex, output, timeout):
    if not codex.is_absolute() or not codex.is_file():
        raise ValueError("--codex must name an existing absolute executable")
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    workspace = output / "workspace"
    workspace.mkdir(mode=0o700)
    events, final = output / "storage-events.jsonl", output / "final.txt"
    native, errors = output / "native-events.jsonl", output / "native-stderr.txt"
    plugins = subprocess.run([str(codex), "plugin", "list", "--marketplace", "expert-partners", "--json"],
                             capture_output=True, text=True, timeout=30, check=True)
    inventory = json.loads(plugins.stdout)
    installed = [p for p in inventory.get("installed", [])
                 if p.get("pluginId") == "operating-doctrine@expert-partners"
                 and p.get("installed") and p.get("enabled")]
    if len(installed) != 1:
        raise ValueError("existing enabled marketplace installation is required")
    plugin = installed[0]
    source = Path(plugin["source"]["path"])
    skill = source / "skills" / "business-brain-foundations" / "SKILL.md"
    expected_skill_hash = hashlib.sha256(skill.read_bytes()).hexdigest()
    args = command(codex, workspace, events, final)
    returncode = None
    timed_out = False
    # Strip inherited API credentials, retaining normal subscribed-account auth.
    env = {key: value for key, value in os.environ.items()
           if not any(marker in key.upper() for marker in ("TOKEN", "SECRET", "API_KEY", "PASSWORD"))}
    with native.open("w") as stdout, errors.open("w") as stderr:
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                   text=True, env=env, start_new_session=True)
        try:
            process.communicate(PROMPT, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        returncode = process.returncode
    storage = judge_storage(read_jsonl(events))
    parsed = read_jsonl(native)
    failures = runtime_failures(parsed)
    result = {
        "installed_plugin_version": plugin.get("version"),
        "installed_skill_sha256": expected_skill_hash,
        "installed_skill_path": str(skill),
        "codex_version": subprocess.check_output([str(codex), "--version"], text=True).strip(),
        "invocation": args, "timeout": timed_out, "returncode": returncode,
        "native_runtime_errors": failures,
        "storage_observations": storage,
        "native_activation": "requires independent inspection of native events against installed skill identity",
        "next_file_generation": "requires independent inspection of actual native events and final output",
        "verdict": "UNRUN_RUNTIME_BLOCKED" if timed_out or returncode or
                   (failures and not storage["first_file_attempts"]) else "REVIEW_REQUIRED",
        "scope": "Synthetic storage only. Transport assertions are not a native behavior pass or certification.",
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"verdict": result["verdict"], "output": str(output),
                      "returncode": returncode, "storage_attempts": storage["first_file_attempts"]}))
    return 2 if result["verdict"] == "UNRUN_RUNTIME_BLOCKED" else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    destination = args.output or Path(tempfile.mkdtemp(prefix="foundations-native-parent-")) / "run"
    raise SystemExit(run(args.codex, destination.resolve(), args.timeout))
