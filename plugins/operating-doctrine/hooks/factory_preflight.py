#!/usr/bin/env python3
"""Inject a small routing reminder, never run a model or change settings."""

import json
import re
import sys


START_CONTEXT = (
    "Before a new actionable Factory assignment, including read-only review or "
    "explanation, invoke Skill(factory-operator) if not already loaded for this "
    "task. Await its result in a separate step before task tools, never in parallel. "
    "Small tasks need only a one-line preflight. "
    "Skip greetings, acknowledgements and status-only continuations. Preserve "
    "explicit choices including Auto. This context changes no settings."
)
TASK_CONTEXT = (
    "For a new actionable assignment (read/review/explain included), invoke "
    "Skill(factory-operator) if not loaded for this task. Await its result in a "
    "separate step before task tools, never in parallel. "
    "Small task: one-line complexity/effort, duration/resources, machine and "
    "worker count. Reuse preflight for unchanged continuations, reflight on "
    "material changes. Preserve explicit Auto/model selection. Context only, "
    "not settings or spend enforcement."
)
TRIVIAL = re.compile(
    r"(?:hi|hello|hey|thanks|thank you|ok|okay|yes|no|approved|go|continue|"
    r"done|s|q|quick update|a quick update please|status|status update|"
    r"where are we|give me a quick update|short version|the short version)",
    re.IGNORECASE,
)


def context_for(payload):
    if not isinstance(payload, dict):
        return ""
    event = payload.get("hook_event_name")
    if event == "SessionStart":
        return START_CONTEXT
    if event != "UserPromptSubmit":
        return ""
    prompt = payload.get("prompt")
    if not isinstance(prompt, str):
        return TASK_CONTEXT if payload.get("has_images") else ""
    normalized = " ".join(prompt.split()).strip(" .!?,")
    if not normalized or TRIVIAL.fullmatch(normalized):
        return TASK_CONTEXT if payload.get("has_images") else ""
    # Do not echo user text, inspect files, or evaluate the task in a hook.
    # The agent distinguishes a new assignment from an unchanged continuation.
    return TASK_CONTEXT


def main():
    try:
        raw = sys.stdin.read(1_048_577)
        if len(raw) > 1_048_576:
            return 0
        payload = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        return 0
    context = context_for(payload)
    if context:
        print(context)
    return 0


if __name__ == "__main__":
    sys.exit(main())
