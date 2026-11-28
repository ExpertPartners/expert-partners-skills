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


def operation(value):
    return value.get("input") if isinstance(value.get("input"), dict) else value


def is_write(name, value):
    value = operation(value)
    if name in ("Execute", "Bash"):
        command = value.get("command", "")
        if (
            "format_native_doc.py" not in command
            and not re.search(
                r"['\"]Content-Type['\"]\s*:\s*['\"](?:text/html|application/vnd\.google-apps\.document)",
                command,
                re.I,
            )
            and not re.search(r"https://docs\.googleapis\.com/v1/documents", command)
            and re.search(r"drive/v3/files.*uploadType=media", command)
            and re.search(
                r"['\"]Content-Type['\"]\s*:\s*['\"]application/json(?:[;\"'])", command, re.I
            )
        ):
            return False
        return bool(
            ("format_native_doc.py" in command and "--help" not in command)
            or (
                (
                    re.search(r"https://docs\.googleapis\.com/v1/documents(?:/|\?|['\"])", command)
                    or (
                        re.search(r"drive/v3/files", command)
                        and re.search(
                            r"application/vnd\.google-apps\.document|text/html", command, re.I
                        )
                    )
                )
                and re.search(r"batchUpdate|['\"](?:POST|PATCH|PUT)['\"]", command)
            )
        )
    if re.search(r"google_api$", name, re.I):
        return value.get("method", "GET").upper() in ("POST", "PATCH", "PUT") and bool(
            re.match(r"https://docs\.googleapis\.com/v1/documents(?:/|\?|$)", value.get("url", ""))
        )
    if re.search(
        r"google.*(?:batch_update_document|create_document|update_document)$|docs.*(?:batch_update|create_document)$",
        name,
        re.I,
    ):
        return True
    if re.search(r"google.*(?:upload_file|update_file_content)$", name, re.I):
        mime = value.get("content_mime_type") or value.get("mime_type") or value.get("mimeType")
        meta = value.get("metadata", {})
        native = "application/vnd.google-apps.document"
        if isinstance(meta, dict) and meta.get("mimeType") == native:
            return True
        if isinstance(mime, str):
            return mime.split(";", 1)[0].strip().lower() in (native, "text/html")
        return isinstance(value.get("documentId"), str)
    return False


def response_ids(name, body):
    ids = set()
    drive = bool(re.search(r"google.*(?:upload_file|update_file_content)$", name, re.I))

    def walk(value, depth=0):
        if depth > 12:
            return
        if isinstance(value, str):
            try:
                walk(json.loads(value), depth + 1)
            except (ValueError, TypeError):
                if depth < 2:
                    for line in value.splitlines():
                        try:
                            walk(json.loads(line), depth + 1)
                        except (ValueError, TypeError):
                            pass
        elif isinstance(value, dict):
            if isinstance(value.get("status"), int) and not 200 <= value["status"] < 300:
                return
            for key in ("documentId", "id") if drive else ("documentId",):
                if isinstance(value.get(key), str) and re.fullmatch(r"[\w-]+", value[key]):
                    ids.add(value[key])
            for key in ("response", "result", "data", "file", "document", "content", "text"):
                if key in value:
                    walk(value[key], depth + 1)
        elif isinstance(value, list):
            for part in value:
                walk(part, depth + 1)

    walk(body)
    return ids


def definitive_failure(name, body):
    if not re.search(r"google_api$", name, re.I):
        return False
    try:
        result = json.loads(body)
    except (ValueError, TypeError):
        return False
    return isinstance(result, dict) and result.get("status") in (
        400,
        401,
        403,
        404,
        405,
        409,
        412,
        415,
        422,
        429,
    )


def request_ids(name, value):
    value = operation(value)
    if re.search(r"google.*(?:upload_file|update_file_content)$", name, re.I):
        target = value.get("file_id") or value.get("fileId")
    elif re.search(r"google_api$", name, re.I):
        match = re.fullmatch(
            r"https://docs\.googleapis\.com/v1/documents/([\w-]+)(?::batchUpdate)?(?:\?.*)?",
            value.get("url", ""),
        )
        target = match[1] if match else None
    elif re.search(
        r"google.*(?:batch_update_document|update_document)$|docs.*batch_update$", name, re.I
    ):
        target = value.get("document_id") or value.get("documentId")
    else:
        target = None
    return {target} if isinstance(target, str) and re.fullmatch(r"[\w-]+", target) else set()


def shell_success(name, body):
    return (
        bool(re.search(r"^exit 0\b", body))
        if name == "Execute"
        else not bool(re.search(r"^exit [1-9]\d*\b", body))
    )


def announcement(text):
    for match in re.finditer(r"\b(save|saving|update|updating|file|filing)\b", text, re.I):
        before = text[: match.start()]
        if re.search(
            r"\b(?:not|never|won['’]t|don['’]t|cannot|can['’]t)\s+(?:\w+\s+){0,2}$", before, re.I
        ):
            continue
        affirmative = match[1].lower().endswith("ing") or re.search(
            r"(?:\bwill|['’]ll)\s*$", before, re.I
        )
        if affirmative and re.search(r"\b(in|into|to)\b", text[match.end() :], re.I):
            return True
    return False


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
            args = formatter_args(value.get("command", "")) if name in ("Execute", "Bash") else None
            if is_write(name, value):
                if definitive_failure(name, body):
                    continue
                # Execute failures are results too. Do not attest a failed command.
                if name in ("Execute", "Bash") and not shell_success(name, body):
                    continue
                ids = response_ids(name, body) or request_ids(name, value)
                if args:
                    ids = {args["--document-id"]}
                writes.append((at, ids))
            if args:
                if not shell_success(name, body):
                    continue
                for line in body.splitlines():
                    if line.startswith(MARKER):
                        try:
                            receipt = json.loads(line[len(MARKER) :])
                        except (ValueError, TypeError):
                            continue
                        if (
                            isinstance(receipt, dict)
                            and receipt.get("verified") is True
                            and receipt.get("document_id") == args["--document-id"]
                            and receipt.get("name") == args["--name"]
                            and receipt.get("url")
                            == f"https://docs.google.com/document/d/{args['--document-id']}/edit"
                            and isinstance(receipt.get("parents"), list)
                            and args["--parent-id"] in receipt["parents"]
                            and all(
                                isinstance(receipt.get(k), str) and receipt[k]
                                for k in ("revision", "native_sha256", "content_sha256")
                            )
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
        elif not any(announcement(p) for _, p in prose):
            reason = "Announce the actual resolved save destination in assistant prose before the document write."
        if reason:
            return {
                "hookSpecificOutput": {
                    "hookEventName": kind,
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
    if kind == "Stop" and writes:
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
