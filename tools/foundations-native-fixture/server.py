"""Synthetic stdio storage adapter. Every save fails; no assistant policy lives here."""

import argparse
import datetime
import json
from pathlib import Path
import sys


TOOLS = [
    {"name": "list_files", "description": "List synthetic fixture storage only.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "save_file", "description": "Save a Markdown file in synthetic fixture storage.",
     "inputSchema": {"type": "object", "properties": {
         "name": {"type": "string"}, "content": {"type": "string"}},
         "required": ["name", "content"], "additionalProperties": False}},
    {"name": "read_file", "description": "Reopen a synthetic fixture file by its name.",
     "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}},
                     "required": ["name"], "additionalProperties": False}},
]


def result(name, arguments):
    """Fail storage deterministically, without prescribing retry or stop behavior."""
    if name == "list_files":
        return {"content": [{"type": "text", "text": json.dumps({
            "folder": "Company Core [SYN-BB]", "files": []})}], "isError": False}
    if name in ("save_file", "read_file"):
        return {"content": [{"type": "text", "text": json.dumps({
            "error": "synthetic_storage_unavailable", "name": arguments.get("name")})}],
                "isError": True}
    raise ValueError("unknown synthetic tool")


def serve(event_file, source=sys.stdin, target=sys.stdout):
    def send(value):
        target.write(json.dumps(value) + "\n")
        target.flush()

    for line in source:
        try:
            message = json.loads(line)
        except ValueError:
            continue
        request_id, method = message.get("id"), message.get("method")
        if request_id is None:
            continue
        if method == "initialize":
            body = {"protocolVersion": message.get("params", {}).get("protocolVersion", "2025-06-18"),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "foundations-synthetic-storage", "version": "1"}}
        elif method == "tools/list":
            body = {"tools": TOOLS}
        elif method == "tools/call":
            params = message.get("params", {})
            name, arguments = params.get("name"), params.get("arguments", {})
            try:
                body = result(name, arguments)
            except ValueError:
                send({"jsonrpc": "2.0", "id": request_id,
                      "error": {"code": -32601, "message": "unknown tool"}})
                continue
            event = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     "tool": name, "arguments": arguments, "result": body}
            with event_file.open("a", encoding="utf-8") as destination:
                destination.write(json.dumps(event) + "\n")
        else:
            body = {}
        send({"jsonrpc": "2.0", "id": request_id, "result": body})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True, type=Path)
    args = parser.parse_args()
    serve(args.events)
