#!/usr/bin/env python3
"""Host backstop using a private derived view of the existing owning records.

The shared Factory connector enforces structured dispatch. This hook also stops
recognized source searches and duplicate commissions before local tool execution.
Arbitrary semantic equivalents and vendor web tools without hooks remain unverified.
"""

import json
import importlib.util
import os
from pathlib import Path
import re
import sys


def check(policy, data):
    ti = data.get("tool_input") or {}
    if isinstance(ti, str):
        ti = {"code": ti}
    intent = ti.get("workIntent") or ti.get("work_intent")
    target = ti.get("sessionId")
    tool = data.get("tool_name", "")
    payload = json.dumps(ti, ensure_ascii=False).lower()
    search_tool = bool(
        re.search(r"search|firecrawl|web__run|browser|list_files", tool, re.I)
        or re.search(r"(?:__|\.)list_files|firecrawl|web__run", payload)
    )
    shell = tool in {
        "Bash",
        "Execute",
        "exec_command",
        "shell",
        "local_shell",
        "container.exec",
        "Script",
        "functions.exec",
        "exec",
        "shell_command",
    }
    commissioning = bool(
        re.search(r"post_message|create_session|start_and_watch|SendMessage", tool, re.I)
    )
    authority = policy.get("source", {}).get("decisionAuthority", {})
    authority_unverified = authority.get("status") != "verified"
    fallback = {
        "id": (intent or {}).get("capabilityId", "unreconciled"),
        "ownerSession": "",
        "decisionUrl": policy.get("source", {}).get("url", ""),
    }
    if intent:
        normalize = lambda value: re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
        direct = next((i for i in policy["items"] if i["id"] == intent.get("capabilityId")), None)
        outcome = normalize(intent.get("outcome", ""))
        matches = [
            i
            for i in policy["items"]
            if outcome and any(normalize(a) == outcome for a in [i["id"]] + i["aliases"])
        ]
        action = intent.get("action")
        if action in ("source_search", "replacement_build", "continue"):
            if len(matches) > 1:
                return "AMBIGUOUS_CAPABILITY_OUTCOME", fallback
            if direct and matches and matches[0]["id"] != direct["id"]:
                return "CAPABILITY_OUTCOME_CONFLICT", matches[0]
            resolved = direct or (matches[0] if matches else None)
            if not resolved:
                return "RECONCILE_FIRST", fallback
            if action == "source_search":
                if resolved["sourceRecovery"] == "closed":
                    return "SOURCE_RECOVERY_CLOSED", resolved
                if authority_unverified or resolved["sourceRecovery"] == "unverified":
                    return "SOURCE_AUTHORITY_UNVERIFIED", resolved
            if action == "replacement_build":
                return "CAPABILITY_EXISTS" if resolved[
                    "installed"
                ] else "EXISTING_BUILD_OWNER", resolved
            if action == "continue" and not (
                resolved["replacementApproved"] and target == resolved["ownerSession"]
            ):
                return "EXISTING_OWNER_CONTINUATION", resolved
    # Folder-scoped reads inspect existing work; unscoped name searches can
    # otherwise reopen closed recovery before any dispatch guard is reached.
    scoped_listing = bool("list_files" in tool and re.search(r"\bin parents\b", payload))
    if data.get("closedSearches") and search_tool and not scoped_listing:
        target = next((i for i in policy["items"] if i["id"] in data["closedSearches"]), None)
        if target:
            return "SOURCE_RECOVERY_CLOSED" if target[
                "sourceRecovery"
            ] == "closed" else "SOURCE_AUTHORITY_UNVERIFIED", target
    for item in policy["items"]:
        matched = any(a.lower() in payload for a in [item["id"]] + item["aliases"])
        if not matched:
            continue
        # Negative instructions/receipts are inspection, not a positive commission.
        sentences = re.split(
            r"[.!?\n;#]+|\b(?:and|but|then)\s+(?=(?:do not|don\x27t|never|stop|search|hunt|recover|find|locate|build(?!\s+101\b)|commission|rebuild|create|implement)\b)",
            str(ti.get("text") or ti.get("command") or ti.get("cmd") or ti.get("query") or payload),
        )
        for sentence in sentences:
            lower = sentence.lower()
            if not any(a.lower() in lower for a in [item["id"]] + item["aliases"]):
                continue
            if re.search(
                r"\b(?:do not|don't|never|stop)\s+(?:\w+\s+){0,2}(?:search|hunt|recover|find|locate|build|commission|rebuild|create|implement)\b|^\s*(?:no|closed|rejected)\b",
                lower,
            ):
                continue
            if (item["sourceRecovery"] in ("closed", "unverified") or authority_unverified) and (
                search_tool
                and not scoped_listing
                or shell
                and re.search(
                    r"\b(curl|wget|yt-dlp|search|firecrawl|recover|hunt|find|locate)\b", lower
                )
            ):
                return "SOURCE_RECOVERY_CLOSED" if item[
                    "sourceRecovery"
                ] == "closed" else "SOURCE_AUTHORITY_UNVERIFIED", item
            if commissioning and re.search(
                r"^\s*(?:please\s+)?(?:build(?!\s+101\b)|commission|rebuild|create|implement)\b|"
                r"\b(?:please|you must|need you to|want you to|your task is to)\s+"
                r"(?:build(?!\s+101\b)|commission|rebuild|create|implement)\b",
                lower,
            ):
                return "CAPABILITY_EXISTS" if item["installed"] else "EXISTING_BUILD_OWNER", item
    return None


def main():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            raise ValueError("invalid hook event")
        path = Path.home() / ".config/expert-partners/work-preflight-policy.json"
        client_path = path.with_name("work-preflight-client.json")
        name = data.get("tool_name", "")
        serialized = json.dumps(data.get("tool_input", {}))
        critical = re.search(
            r"search|firecrawl|web__run|browser|list_files|post_message|create_session|start_and_watch|SendMessage|\bfind\b|\blocate\b|\brecover\b|\bhunt\b",
            name + serialized,
            re.I,
        )
        if client_path.exists() and critical:
            spec = importlib.util.spec_from_file_location(
                "work_client", Path(__file__).with_name("work-policy-client.py")
            )
            client = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(client)
            policy = client.refresh()
            state_path = client.session_state_path(data)
            if state_path and state_path.exists():
                data.update(json.loads(state_path.read_text()))
        else:
            policy = json.loads(path.read_text())
        if policy.get("version") != 1 or not isinstance(policy.get("items"), list):
            raise ValueError("invalid derived policy")
        result = check(policy, data)
        if result:
            code, item = result
            print(
                json.dumps(
                    {
                        "code": code,
                        "capabilityId": item["id"],
                        "ownerSession": item["ownerSession"],
                        "decisionUrl": item["decisionUrl"],
                        "instruction": "Use the existing owner. Source closure is separate from implementation and testing.",
                    }
                ),
                file=sys.stderr,
            )
            return 2
        return 0
    except Exception:
        print(
            "Work preflight could not read its owning-record projection. Restore it before executing work.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
