#!/usr/bin/env python3
"""Bounded native save validation, not an arbitrary-code or API security boundary."""

import importlib.util
import json
from pathlib import Path
import re
import shlex
import sys

SKILLS = {"document-formatting-standard", "deliverable-link"}
FORMATTER = str(
    Path(__file__).resolve().parents[1]
    / "skills/document-formatting-standard/scripts/format_native_doc.py"
)
MARKER = "NATIVE_DOC_VERIFIED "


def text_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(text_content(x) for x in content)
    if isinstance(content, dict):
        return text_content(content.get("text", content.get("content", "")))
    return ""


def records(path):
    result = []
    with Path(path).open() as source:
        for line in source:
            row = json.loads(line)
            message = row.get("message", {})
            # Hook context is not a user request or assistant announcement.
            if message.get("hookEventName") or str(row.get("id", "")).startswith("hook-context-"):
                continue
            result.append(message)
    return result


def is_write(name, value):
    raw = json.dumps(value)
    if name in ("Execute", "Bash"):
        command = value.get("command", "")
        return ("format_native_doc.py" in command and "--help" not in command) or (
            re.search(r"(docs\.googleapis\.com|drive/v3/files)", command)
            and re.search(r"batchUpdate|['\"](?:POST|PATCH|PUT)['\"]", command)
        )
    return bool(
        re.search(
            r"(google.*(upload_file|update_file_content)|docs.*(batch_update|create_document))$",
            name,
            re.I,
        )
        and ("document" in raw or "doc" in name.lower())
    )


def formatter_args(command):
    try:
        parts = shlex.split(command)
        if (
            len(parts) != 14
            or not re.fullmatch(r"(?:.*/)?python3(?:\.\d+)?", parts[0])
            or Path(parts[1]).resolve() != Path(FORMATTER)
            or set(parts[2::2])
            != {"--adapter", "--subject", "--document-id", "--rulebook-id", "--name", "--parent-id"}
        ):
            return None
        return dict(zip(parts[2::2], parts[3::2]))
    except ValueError:
        return None


def fresh(receipt, args):
    spec = importlib.util.spec_from_file_location("canonical_doc_formatter", FORMATTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.recheck_receipt(module.Google(args["--adapter"], args["--subject"]), receipt)


def evidence(messages):
    calls, skills, writes, receipts, prose = {}, set(), [], [], []
    for index, message in enumerate(messages):
        content = message.get("content", [])
        if (
            message.get("role") == "user"
            and not message.get("visibility")
            and any(x.get("type") == "text" for x in content if isinstance(x, dict))
            and not any(x.get("type") == "tool_result" for x in content if isinstance(x, dict))
        ):
            writes, receipts, prose = [], [], []
        if message.get("role") == "assistant":
            spoken = text_content([x for x in content if x.get("type") == "text"])
            if spoken.strip() and not message.get("visibility"):
                prose.append((index, spoken))
        for item in content if isinstance(content, list) else []:
            if item.get("type") == "tool_use":
                calls[item["id"]] = (index, item.get("name", ""), item.get("input", {}))
            if item.get("type") != "tool_result" or item.get("is_error"):
                continue
            call = calls.get(item.get("tool_use_id"))
            if not call:
                continue
            at, name, value = call
            body = text_content(item.get("content"))
            if (
                name == "Skill"
                and 'is now active' in body
                and str(
                    Path(__file__).resolve().parents[1]
                    / "skills"
                    / str(value.get("skill", "")).split(":")[-1]
                    / "SKILL.md"
                )
                in body
            ):
                skills.add(str(value.get("skill", "")).split(":")[-1])
            args = formatter_args(value.get("command", "")) if name == "Execute" else None
            if is_write(name, value):
                # Execute failures are results too. Do not attest a failed command.
                if name == "Execute" and not re.search(r"^exit 0\b", body):
                    continue
                ids = set(re.findall(r"""["']documentId["']\s*:\s*["']([\w-]+)["']""", body))
                if args:
                    ids = {args["--document-id"]}
                writes.append((at, ids))
            if args:
                if not re.search(r"^exit 0\b", body):
                    continue
                for line in body.splitlines():
                    if line.startswith(MARKER):
                        receipt = json.loads(line[len(MARKER) :])
                        if (
                            receipt.get("verified") is True
                            and receipt.get("document_id") == args["--document-id"]
                            and receipt.get("name") == args["--name"]
                            and receipt.get("revision")
                            and receipt.get("native_sha256")
                            and receipt.get("content_sha256")
                        ):
                            receipts.append((index, receipt, args))
    return skills, writes, receipts, prose


def check(event, recheck=None):
    kind = event["hook_event_name"]
    if kind == "UserPromptSubmit":
        if re.search(
            r"\b(save|update and save|file this|capture this)\b", event.get("prompt", ""), re.I
        ):
            return {
                "hookSpecificOutput": {
                    "hookEventName": kind,
                    "additionalContext": (
                        "For a company document save, invoke Skill document-formatting-standard "
                        "and Skill deliverable-link. Read live authority, resolve the existing subject "
                        "and home, and announce the destination before writing. Keep the existing save "
                        "route. After its last content write, run the canonical native formatter at "
                        + FORMATTER
                        + " as described in the formatting skill. Deliver its verified exact-name link. "
                        "Legacy intake instructions do not replace these current procedures."
                    ),
                }
            }
        return {}
    if kind == "PreToolUse" and not is_write(event["tool_name"], event["tool_input"]):
        return {}
    messages = records(event["transcript_path"])
    skills, writes, receipts, prose = evidence(messages)
    if kind == "PreToolUse" and is_write(event["tool_name"], event["tool_input"]):
        missing = SKILLS - skills
        reason = ""
        command = event["tool_input"].get("command", "")
        if "format_native_doc.py" in command and not formatter_args(command):
            reason = "Run the canonical formatter as one standalone python3 command with its six required arguments."
        elif missing:
            reason = (
                "Before this document write, invoke the existing Skill procedures: "
                + ", ".join(sorted(missing))
            )
        elif not any(
            re.search(r"\b(sav|updat|fil)\w*.*\b(in|into|to)\b", p, re.I) for _, p in prose
        ):
            reason = "Announce the actual resolved save destination in assistant prose before the document write."
        if reason:
            return {
                "hookSpecificOutput": {
                    "hookEventName": kind,
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
    if kind == "Stop" and writes and not event.get("stop_hook_active"):
        latest = {}
        for at, ids in writes:
            if not ids:
                return {
                    "decision": "block",
                    "reason": "Native write result did not identify its documentId. Save remains unverified; retain the actual mutation response and validate that same Doc.",
                }
            for doc_id in ids:
                latest[doc_id] = max(latest.get(doc_id, -1), at)
        current = []
        for doc_id, write_at in latest.items():
            candidates = [
                (at, r, args)
                for at, r, args in receipts
                if at > write_at and r["document_id"] == doc_id
            ]
            if candidates:
                current.append(max(candidates, key=lambda x: x[0])[1:])
        if len(current) != len(latest):
            return {
                "decision": "block",
                "reason": "The native document save has no successful formatting/readback after its last write. Run "
                + FORMATTER
                + " using the existing Google adapter, live Rulebook, exact document name and parent. Do not claim a pass from text or requested styles.",
            }
        final = prose[-1][1] if prose else ""
        for receipt, args in current:
            try:
                (recheck or fresh)(receipt, args)
            except Exception:
                return {
                    "decision": "block",
                    "reason": "Final native revision/content changed or could not be read. Re-read and validate the same saved Doc before claiming completion.",
                }
            link = f"[{receipt['name']}]({receipt['url']})"
            if link not in final:
                return {
                    "decision": "block",
                    "reason": "Deliver the exact verified document-name Markdown link, not a generic caption: "
                    + link,
                }
    return {}


def main():
    try:
        print(json.dumps(check(json.load(sys.stdin))))
    except (OSError, ValueError, KeyError, TypeError):
        # A broken transcript must not silently permit a known native write.
        print(
            "Native save validation could not read its evidence; no save pass is established.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
