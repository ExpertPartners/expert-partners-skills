#!/usr/bin/env python3
"""Run the existing ChatGPT gateway canary on the assigned M2 profiles.

Private runtime settings identify existing routes and proof chats. Credentials are resolved
from 1Password into the HTTP consumer only. Browser results and document bodies are never
printed or saved. The gateway derives PASS from authenticated MCP observations, not prose.
"""

import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import urllib.request


class MCP:
    def __init__(self, route):
        self.proc = subprocess.Popen(
            [route],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self.messages = queue.Queue()
        self.sequence = 0
        threading.Thread(target=self._read, daemon=True).start()
        self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ChatGPT gateway daily check", "version": "1.0"},
            },
        )
        self.proc.stdin.write(
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        )
        self.proc.stdin.flush()

    def _read(self):
        for line in self.proc.stdout:
            try:
                self.messages.put(json.loads(line))
            except ValueError:
                pass
        self.messages.put({"error": "browser_transport_closed"})

    def request(self, method, params, timeout=110):
        self.sequence += 1
        expected = self.sequence
        self.proc.stdin.write(
            json.dumps({"jsonrpc": "2.0", "id": expected, "method": method, "params": params})
            + "\n"
        )
        self.proc.stdin.flush()
        deadline = time.monotonic() + timeout
        while True:
            result = self.messages.get(timeout=max(0.1, deadline - time.monotonic()))
            if result.get("id") == expected:
                if "error" in result:
                    raise RuntimeError("browser_rpc_error")
                value = result["result"]
                if value.get("isError"):
                    raise RuntimeError("browser_operation_failed")
                return value
            if result.get("error") == "browser_transport_closed":
                raise RuntimeError("browser_transport_closed")

    def tool(self, tool_name, **args):
        return self.request("tools/call", {"name": tool_name, "arguments": args})

    def code(self, job, code):
        raw = self.tool("browser_run_code_unsafe", job_id=job, code=code)
        text = next(c["text"] for c in raw["content"] if c.get("type") == "text")
        if not text.startswith("### Result\n"):
            raise RuntimeError("browser_projection_missing")
        return json.JSONDecoder().raw_decode(text[len("### Result\n") :])[0]

    def close(self):
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.proc.terminate()


class Monitor:
    def __init__(self, settings):
        self.settings = settings
        record = json.loads(
            subprocess.check_output(
                [
                    "op",
                    "item",
                    "get",
                    settings["token_item"],
                    "--vault",
                    settings["vault"],
                    "--format",
                    "json",
                ],
                stderr=subprocess.DEVNULL,
            )
        )
        self.token = next(f["value"] for f in record["fields"] if f["id"] == "credential")

    def api(self, path, body=None):
        req = urllib.request.Request(
            self.settings["gateway"] + "/api/health/clients" + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "User-Agent": "gateway-client-monitor",
            },
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.load(response)

    def run(self, client, refresh=False):
        cfg = self.settings["accounts"][client]
        run = self.api(f"/{client}/start", {})
        started = time.monotonic()
        mcp = None
        job = None
        closed = False
        error = None
        proof = cfg.get("conversation_id")
        try:
            mcp = MCP(cfg["route"])
            result = mcp.tool("browser_job_start", name=f"Daily ChatGPT Gateway check for {client}")
            job = json.loads(result["content"][0]["text"])["job_id"]
            mcp.code(
                job, "async(page)=>{await page.goto('https://chatgpt.com/');return {loaded:true}}"
            )
            identity = mcp.code(
                job,
                "async(page)=>await page.evaluate(async()=>{const s=await(await fetch('/api/auth/session')).json();return {email:s.user?.email}})",
            )
            if identity.get("email") != cfg["email"]:
                raise RuntimeError("wrong_chatgpt_identity")
            if refresh:
                url = (
                    "https://chatgpt.com/settings/plugins-settings/plugin_"
                    + self.settings["app_id"]
                )
                mcp.code(
                    job,
                    "async(page)=>{await page.goto(" + json.dumps(url) + ");return {loaded:true}}",
                )
                mcp.code(
                    job,
                    "async(page)=>{const b=page.locator('button').filter({hasText:'Refresh tools'});await b.first().waitFor({state:'attached'});await b.first().evaluate(x=>x.click());return {refreshed:true}}",
                )
            target = "https://chatgpt.com/c/" + proof if proof else "https://chatgpt.com/"
            mcp.code(
                job,
                "async(page)=>{await page.goto(" + json.dumps(target) + ");return {loaded:true}}",
            )
            # KV replication between the M2 and ChatGPT's egress location is eventually consistent.
            # Allow the new short-lived lease to propagate before tools execute in another region.
            while time.monotonic() - started < 70:
                time.sleep(min(10, 70 - (time.monotonic() - started)))
            denial = "ag-private" if client == "allison" else "ag-core"
            prompt = (
                "Authorized daily ChatGPT Drive Brain Gateway connection check. Use only the existing Drive brain gateway. "
                "Select the existing authenticated account from the current catalog. Include health_run_id "
                + run["id"]
                + " on EVERY gateway call. "
                "Run these in order. 1 list_scopes. 2 discover hq-core with query exactly Rulebook. "
                "3 read that current HQ Rulebook using its returned id with max_chars 1. "
                "4 decisions. 5 read the current Decision Log id returned by decisions in hq-core with max_chars 1. "
                "6 discover " + denial + " expecting 403 scope_not_allowed. "
                "7 read the same Rulebook id through ep-core expecting 403 not_in_scope. "
                "Return only the seven outcomes, versions and error codes. An expected 403 is a passing boundary check. "
                "Never create a connection, reconnect, edit settings, use another provider or invent results. "
                "If a tool is unavailable, report it plainly. This recurring check is already authorized."
            )
            mcp.code(
                job,
                "async(page)=>{await page.locator('[contenteditable=true][aria-label=\"Ask ChatGPT\"]:visible').fill("
                + json.dumps(prompt)
                + ");await page.locator('button[aria-label=\"Send\"]:visible').evaluate(x=>x.click());return {sent:true}}",
            )
            completed_at = None
            while time.monotonic() - started < 480:
                time.sleep(10)
                browser = mcp.code(
                    job,
                    "async(page)=>({running:await page.locator('button[aria-label=\"Stop\"]').count(),conversationId:page.url().split('/c/')[1]?.split('?')[0]})",
                )
                proof = browser.get("conversationId") or proof
                receipt = self.api(f"/{client}/runs/{run['id']}")
                if all(receipt["checks"].values()):
                    break
                if not browser["running"]:
                    completed_at = completed_at or time.monotonic()
                    # Missing observations may still be replicating. Never turn a model PASS into one.
                    if time.monotonic() - completed_at > 100:
                        break
        except Exception as exc:
            error = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        finally:
            if mcp:
                try:
                    if job:
                        result = mcp.tool("browser_job_finish", job_id=job)
                        closed = (
                            json.loads(result["content"][0]["text"]).get("status") == "finished"
                        )
                except Exception:
                    error = "browser_cleanup_failed"
                finally:
                    mcp.close()
        outcome = {
            "runnerError": "cleanup_failed" if not closed else "browser_error" if error else "none"
        }
        if proof:
            outcome["conversationId"] = proof
        result = self.api(f"/{client}/runs/{run['id']}/finish", outcome)
        return {"client": client, "browserClosed": closed, "runnerError": error, **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--client", choices=["all", "allison", "don"], default="all")
    parser.add_argument("--refresh-tools", action="store_true")
    args = parser.parse_args()
    settings = json.loads(args.settings.read_text())
    # This runner is installed on M2; an unattended check must never launch an M4 browser.
    if Path.home() != Path("/Users/ember"):
        raise SystemExit("Run this check on Ember's M2")
    lock = args.settings.with_suffix(".lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    monitor = Monitor(settings)
    clients = ["allison", "don"] if args.client == "all" else [args.client]
    results = []
    for client in clients:
        try:
            result = monitor.run(client, args.refresh_tools)
        except Exception as exc:
            result = {"client": client, "runnerError": type(exc).__name__}
        results.append(result)
        print(json.dumps(result), flush=True)
    raise SystemExit(
        0 if all(r.get("receipt", {}).get("ok") and r.get("browserClosed") for r in results) else 1
    )


if __name__ == "__main__":
    main()
