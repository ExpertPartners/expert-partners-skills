"""Stand-in for the Codex CLI, driven by a JSON scenario file named in FAKE_CODEX_SCENARIO.

It answers only what connector_health.py runs: `app-server generate-json-schema --out DIR`,
`features list`, `mcp list --json` and `app-server ... --listen stdio://`. The schema it
writes mirrors the layout and shapes of the real codex-cli 0.166.0 output. Test use only.
"""

import json
import os
import signal
import subprocess
import sys
import time


def scenario():
    with open(os.environ["FAKE_CODEX_SCENARIO"], encoding="utf-8") as fh:
        return json.load(fh)


def log_invocation(sc, argv):
    path = sc.get("argv_file")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(argv) + "\n")


def union(methods):
    return {"oneOf": [{"properties": {"method": {"enum": [m]}, "params": {}}} for m in methods]}


def write_schema(out, mode):
    os.makedirs(os.path.join(out, "v1"), exist_ok=True)
    os.makedirs(os.path.join(out, "v2"), exist_ok=True)
    methods = ["initialize", "thread/start", "thread/resume", "turn/start", "mcpServer/tool/call", "config/value/write"]
    if mode == "no_tool_call":
        methods.remove("mcpServer/tool/call")
    thread_props = {
        "cwd": {"type": ["string", "null"]},
        "ephemeral": {"type": ["boolean", "null"]},
        "sandbox": {"anyOf": [{"$ref": "#/definitions/SandboxMode"}, {"type": "null"}]},
    }
    if mode == "no_ephemeral":
        del thread_props["ephemeral"]
    files = {
        "ClientRequest.json": union(methods),
        "ClientNotification.json": union(["initialized"]),
        os.path.join("v1", "InitializeParams.json"): {"properties": {"clientInfo": {}, "capabilities": {}}, "required": ["clientInfo"]},
        os.path.join("v2", "ThreadStartParams.json"): {
            "properties": thread_props,
            "definitions": {"SandboxMode": {"enum": ["read-only", "workspace-write", "danger-full-access"], "type": "string"}},
        },
        os.path.join("v2", "McpServerToolCallParams.json"): {
            "properties": {"_meta": True, "arguments": True, "server": {"type": "string"}, "threadId": {"type": "string"}, "tool": {"type": "string"}},
            "required": ["server", "threadId", "tool"],
        },
    }
    for name, body in files.items():
        with open(os.path.join(out, name), "w", encoding="utf-8") as fh:
            json.dump(body, fh)


FEATURES = [
    "apps                                     stable             true",
    "browser_use                              stable             true",
    "computer_use                             stable             true",
    "hooks                                    stable             true",
    "plugins                                  stable             true",
    "memories                                 stable             false",
    "in_app_browser                           removed            false",
    "unified_exec                             stable             true",
]


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def app_server(sc):
    if sc.get("stderr"):
        sys.stderr.write(sc["stderr"] + "\n")
        sys.stderr.flush()
    if sc.get("touch_config"):
        with open(os.path.join(os.environ["CODEX_HOME"], "config.toml"), "a", encoding="utf-8") as fh:
            fh.write("# changed\n")
    child = None
    if sc.get("spawn_child_pidfile"):
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
        with open(sc["spawn_child_pidfile"], "w", encoding="utf-8") as fh:
            fh.write(str(child.pid))
    if sc.get("stubborn"):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    with open(os.path.join(os.path.dirname(os.environ["FAKE_CODEX_SCENARIO"]), "server-pid"), "w", encoding="utf-8") as fh:
        fh.write(str(os.getpid()))
    thread_id = "01a1a405-4547-7261-96fd-9116a030db62"
    late = []
    replies = sc.get("replies_file")
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if sc.get("requests_file") and "method" in msg:
            with open(sc["requests_file"], "a", encoding="utf-8") as fh:
                fh.write(msg["method"] + "\n")
        if "method" not in msg:
            if replies:
                with open(replies, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(msg) + "\n")
            continue
        method, mid = msg["method"], msg.get("id")
        if mid is None:
            continue
        if sc.get("pre_messages"):
            sys.stdout.write("this line is not json\n")
            send({"method": "mcpServer/startupStatus/updated", "params": {"name": "github", "status": "starting"}})
            send({"id": "srv-1", "method": "mcpServer/elicitation/request", "params": {"message": "approve?"}})
            send({"id": "srv-2", "method": "item/tool/requestUserInput", "params": {}})
            send({"id": 9999, "result": {"stale": True}})
        while late:
            send({"id": late.pop(), "result": {"content": [{"type": "text", "text": sc.get("late_text", "late")}]}})
        if method == "initialize":
            if sc.get("initialize") == "bad":
                send({"id": mid, "result": {"unexpected": True}})
            else:
                send({"id": mid, "result": {"userAgent": "fake/0.0", "codexHome": os.environ.get("CODEX_HOME", "/x"), "platformFamily": "unix", "platformOs": "linux"}})
        elif method == "thread/start":
            if sc.get("record_thread_params"):
                with open(sc["record_thread_params"], "w", encoding="utf-8") as fh:
                    json.dump(msg["params"], fh)
            send({"id": mid, "result": {"thread": {"id": thread_id, "ephemeral": sc.get("thread_ephemeral", True)}}})
            for name, status in sc.get("startup", {}).items():
                send({"method": "mcpServer/startupStatus/updated", "params": {"threadId": thread_id, "name": name, "status": status}})
        elif method == "mcpServer/tool/call":
            params = msg["params"]
            key = params["server"] + "/" + params["tool"]
            plan = sc.get("calls", {}).get(key)
            if plan is None:
                send({"id": mid, "error": {"code": -32603, "message": "unknown MCP server '" + params["server"] + "'"}})
                continue
            if plan.get("exit"):
                os._exit(3)
            if plan.get("hang"):
                if plan.get("late"):
                    late.append(mid)
                continue
            if plan.get("delay"):
                time.sleep(plan["delay"])
            if "error" in plan:
                send({"id": mid, "error": plan["error"]})
            else:
                send({"id": mid, "result": plan["result"]})
        else:
            send({"id": mid, "error": {"code": -32600, "message": "unknown variant"}})
    if sc.get("stubborn"):
        while True:
            time.sleep(1)
    if child is not None:
        child.wait()


def main():
    sc = scenario()
    argv = sys.argv[1:]
    log_invocation(sc, argv)
    if sc.get("hang_cli") in argv[:2]:
        time.sleep(300)
    if argv[:2] == ["app-server", "generate-json-schema"]:
        if sc.get("schema") == "fail":
            sys.stderr.write(sc.get("stderr", "") + "\n")
            return 1
        write_schema(argv[argv.index("--out") + 1], sc.get("schema", "ok"))
        return 0
    if argv[:2] == ["features", "list"]:
        print("\n".join(sc.get("features", FEATURES)))
        return 0
    if argv[:3] == ["mcp", "list", "--json"]:
        print(json.dumps(sc.get("mcp_list", [])))
        return sc.get("mcp_list_rc", 0)
    if argv[:1] == ["app-server"] and argv[-2:] == ["--listen", "stdio://"]:
        app_server(sc)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
