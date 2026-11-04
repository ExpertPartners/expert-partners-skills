"""Minimal stdio MCP server for the optional real Codex CLI test. Synthetic data only.

argv[1] is the mode: ok (get_me and an empty list_bases), forbidden (a 403 wrapped in a
successful MCP envelope) or marker:<path> (writes the path on start, to prove it ran).
"""

import json
import sys

MODE = sys.argv[1] if len(sys.argv) > 1 else "ok"
if MODE.startswith("marker:"):
    with open(MODE.split(":", 1)[1], "w", encoding="utf-8") as fh:
        fh.write("started\n")


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def tool_result(name):
    if MODE == "forbidden":
        body = {"status": 403, "error": {"message": "insufficient scope"}}
    elif name == "list_bases":
        body = {"bases": []}
    else:
        body = {"id": "synthetic-user", "login": "synthetic"}
    return {"content": [{"type": "text", "text": json.dumps(body)}], "isError": False}


for line in sys.stdin:
    try:
        msg = json.loads(line)
    except ValueError:
        continue
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        continue
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "synthetic", "version": "1"},
        }})
    elif method == "tools/list":
        schema = {"type": "object", "properties": {}}
        send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [
            {"name": "get_me", "description": "synthetic", "inputSchema": schema},
            {"name": "list_bases", "description": "synthetic", "inputSchema": schema},
        ]}})
    elif method == "tools/call":
        send({"jsonrpc": "2.0", "id": mid, "result": tool_result(msg["params"]["name"])})
    else:
        send({"jsonrpc": "2.0", "id": mid, "result": {}})
