#!/usr/bin/env python3
"""Host backstop using a private derived view of the existing owning records.

The shared Factory connector enforces structured dispatch. This hook also stops
recognized source searches and duplicate commissions before local tool execution.
Arbitrary semantic equivalents and vendor web tools without hooks remain unverified.
"""

import json
import os
from pathlib import Path
import re
import sys


def check(policy, data):
    ti = data.get("tool_input") or {}
    intent = ti.get("workIntent") or ti.get("work_intent")
    target = ti.get("sessionId")
    tool = data.get("tool_name", "")
    payload = json.dumps(ti, ensure_ascii=False).lower()
    search_tool = bool(re.search(r"search|firecrawl|web__run|browser", tool, re.I))
    shell = tool in {"Bash", "Execute", "exec_command", "shell", "local_shell"}
    commissioning = bool(
        re.search(r"post_message|create_session|start_and_watch|SendMessage", tool, re.I)
    )
    for item in policy["items"]:
        matched = any(a.lower() in payload for a in [item["id"]] + item["aliases"])
        if intent and intent.get("capabilityId") == item["id"]:
            action = intent.get("action")
            if action == "source_search" and item["sourceRecovery"] == "closed":
                return "SOURCE_RECOVERY_CLOSED", item
            if action == "replacement_build":
                return "CAPABILITY_EXISTS" if item["installed"] else "EXISTING_BUILD_OWNER", item
            if action == "continue" and not (
                item["replacementApproved"] and target == item["ownerSession"]
            ):
                return "EXISTING_OWNER_CONTINUATION", item
        if not matched:
            continue
        # Negative instructions/receipts are inspection, not a positive commission.
        sentences = re.split(
            r"[.!?\n]+",
            str(ti.get("text") or ti.get("command") or ti.get("cmd") or ti.get("query") or payload),
        )
        for sentence in sentences:
            lower = sentence.lower()
            if not any(a.lower() in lower for a in [item["id"]] + item["aliases"]):
                continue
            if re.search(r"\b(no|not|never|don't|without|closed|rejected|stop)\b", lower):
                continue
            if item["sourceRecovery"] == "closed" and (
                search_tool
                or shell
                and re.search(r"\b(curl|wget|yt-dlp|search|firecrawl|recover|hunt)\b", lower)
            ):
                return "SOURCE_RECOVERY_CLOSED", item
            if commissioning and re.search(
                r"^\s*(?:please\s+)?(?:build|commission|rebuild|create|implement)\b|"
                r"\b(?:please|you must|need you to|want you to|your task is to)\s+"
                r"(?:build|commission|rebuild|create|implement)\b",
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
    except (ValueError, OSError, TypeError, KeyError):
        print(
            "Work preflight could not read its owning-record projection. Restore it before executing work.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
