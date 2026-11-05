#!/usr/bin/env python3
"""Stdio MCP facade allocating a separate existing-profile connection per job.

Runs on the browser host. Configuration names the existing protected launcher;
credentials remain inside that launcher. There is no network listener or scheduler.
"""
import argparse
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid

from chrome_job_window import existing_signed_in_profile, chrome_is_running
from job_transport import StdioClient, Refusal


EXTENSION = "chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/connect.html"
STATE_JS = "const s=Buffer.constructor('return process')().__epBrowserJob;if(!s)throw Error('owned_state_missing');"
OWNED_SOURCE = Path(__file__).with_name("owned_pages.js").read_text()
SAFE_ENV = ("HOME", "USER", "LOGNAME", "PATH", "LANG", "LC_ALL", "TMPDIR")


def redact(value):
    """The connector URL contains a credential. Never return its query to a caller."""
    if isinstance(value, str):
        return re.sub(re.escape(EXTENSION) + r"\?[^\s\]\)<>`\"']*", EXTENSION + "?[private]", value)
    if isinstance(value, list):
        return [redact(x) for x in value]
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    return value


def result(value, error=False):
    return {"content": [{"type": "text", "text": json.dumps(redact(value), ensure_ascii=False)}], "isError": error}


def projection(reply):
    if reply.get("isError"):
        raise Refusal("owned_operation_failed")
    blocks = reply.get("content", [])
    if len(blocks) != 1 or blocks[0].get("type") != "text":
        raise Refusal("owned_projection_shape")
    text = blocks[0]["text"]
    if not text.startswith("### Result\n"):
        raise Refusal("owned_projection_heading")
    try:
        value, _ = json.JSONDecoder().raw_decode(text[len("### Result\n"):])
    except ValueError:
        raise Refusal("owned_projection_json") from None
    if not isinstance(value, dict):
        raise Refusal("owned_projection_type")
    return value


def code(client, body):
    return projection(client.call("tools/call", {"name": "browser_run_code_unsafe", "arguments": {"code": "async(page)=>{" + body + "}"}}))


def chrome_generation():
    """Read only the main Chrome process identity, never its credential-bearing argv."""
    ids = subprocess.run(["/usr/bin/pgrep", "-x", "Google Chrome"], capture_output=True, text=True, timeout=3, check=False).stdout.split()
    if len(ids) != 1 or not ids[0].isdigit():
        raise Refusal("chrome_generation_ambiguous")
    stamp = subprocess.run(["/bin/ps", "-p", ids[0], "-o", "lstart="], capture_output=True, text=True, timeout=3, check=True).stdout.strip()
    if not stamp:
        raise Refusal("chrome_generation_missing")
    return {"pid": int(ids[0]), "started": stamp}


class Route:
    def __init__(self, config):
        self.config = config
        self.root = Path(config["state_dir"]).expanduser()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        self.guard = None
        path = Path(config["headless_hook"])
        spec = importlib.util.spec_from_file_location("owned_job_headless_policy", path)
        if spec is None or spec.loader is None:
            raise Refusal("headless_policy_unavailable")
        self.guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.guard)
        if not callable(getattr(self.guard, "decide", None)):
            raise Refusal("headless_policy_incompatible")
        self.jobs = {}
        self.lock = threading.RLock()
        self.inventory = None

    def preflight(self):
        if socket.gethostname() != self.config["host"]:
            raise Refusal("wrong_browser_host")
        existing_signed_in_profile(self.config["profile"], self.config["expected_account"])
        if not chrome_is_running():
            raise Refusal("existing_chrome_not_running")
        generation = chrome_generation()
        launcher = Path(self.config["launcher"])
        if hashlib.sha256(launcher.read_bytes()).hexdigest() != self.config["launcher_sha256"]:
            raise Refusal("protected_launcher_changed")
        return generation

    @contextmanager
    def bootstrap(self):
        # Shared across every facade on this host. This serializes creation only;
        # the established jobs perform all page work in parallel.
        path = Path(self.config["bootstrap_lock"])
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        deadline = time.monotonic() + 90
        try:
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > deadline:
                        raise Refusal("bootstrap_busy_retry_not_replay")
                    time.sleep(.05)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def client(self, name):
        self.preflight()
        env = {k: os.environ[k] for k in SAFE_ENV if k in os.environ}
        env.update(npm_config_offline="true", npm_config_update_notifier="false", npm_config_audit="false", npm_config_fund="false", npm_config_logs_max="0",
                   EP_BROWSER_EXPECTED_ACCOUNT=self.config["expected_account"])
        wrapper = str(Path(__file__).with_name("chrome_job_window.py"))
        client = StdioClient([self.config["launcher"], "--executable-path", wrapper], env, timeout=45, cap=16777216, frame_cap=12582912)
        try:
            init = client.call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": name, "version": "1.0"}})
            if init.get("protocolVersion") not in ("2024-11-05", "2025-03-26", "2025-06-18"):
                raise Refusal("protocol_incompatible")
            if init.get("serverInfo", {}).get("version") != self.config["mcp_version"]:
                raise Refusal("mcp_version_changed")
            client.notify("notifications/initialized")
            return client
        except BaseException:
            client.close()
            raise

    def save(self, job):
        # No URLs, credentials, provider results or arbitrary tool inputs on disk.
        row = {k: job[k] for k in ("job_id", "label", "status", "client_name", "generation", "metadata", "updated")}
        row["ownership_pending"] = job.get("ownership_pending", False)
        path = self.root / (job["job_id"] + ".json")
        tmp = path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(row, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)

    def checkpoint(self, job, status=None):
        if status:
            job["status"] = status
        job["updated"] = time.time()
        self.save(job)

    def metadata(self, client, strict=True):
        return code(client, STATE_JS + "return await s.snapshot(" + json.dumps(strict) + ");")

    def connect(self, job, working=True):
        client = self.client(job["client_name"])
        job["client"] = client
        # State is in this private Node process, not the ephemeral VM globals.
        initialized = code(client, OWNED_SOURCE + "const p=Buffer.constructor('return process')();if(p.__epBrowserJob)throw Error('already_attempted');"
                           "if(page.context().pages().length!==1||!page.url().startsWith(" + json.dumps(EXTENSION + "?") + "))throw Error('not_fresh_connector');"
                           "p.__epBrowserJob=await newOwnedState(page);const s=p.__epBrowserJob;return {ready:true,ownership:{...s.initial,tabIds:[...s.ids.values()],unboundOwnedPages:0}};")
        if initialized.get("ready") is not True:
            raise Refusal("connector_initialization_failed")
        job["metadata"] = initialized["ownership"]
        self.checkpoint(job, "connecting")
        self.verify_connection(job)
        if working:
            job["ownership_pending"] = True
            self.checkpoint(job)
            code(client, STATE_JS + "s.task=await s.create();return {created:!s.task.isClosed()};")
            job["metadata"] = self.metadata(client)
            if len(job["metadata"]["tabIds"]) != 2:
                raise Refusal("owned_page_count_mismatch")
            job["ownership_pending"] = False
            self.checkpoint(job, "ready")
        return client

    def start(self, label):
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 80 or any(ord(c) < 32 for c in label):
            raise Refusal("job_name_required")
        job_id = uuid.uuid4().hex
        job = {"job_id": job_id, "label": label.strip(), "status": "starting", "client_name": "EP " + label.strip() + " [" + job_id[:8] + "]",
               "generation": None, "metadata": None, "updated": time.time(), "ownership_pending": False, "client": None, "lock": threading.RLock()}
        with self.lock:
            self.jobs[job_id] = job
        with job["lock"]:
            try:
                with self.bootstrap():
                    job["generation"] = self.preflight()
                    self.checkpoint(job)
                    self.connect(job)
                return result(self.summary(job))
            except BaseException:
                self.checkpoint(job, "failed")
                # Caller gets the handle even if allocation failed. Never hide
                # an uncertain creation behind an automatic second attempt.
                return result({**self.summary(job), "error": "Allocation failed; finish or recover this exact job before replacing it."}, True)

    def get(self, job_id):
        if not isinstance(job_id, str) or not re.fullmatch(r"[0-9a-f]{32}", job_id):
            raise Refusal("valid_job_id_required")
        with self.lock:
            job = self.jobs.get(job_id)
        if job is None:
            raise Refusal("unknown_job_no_shared_fallback")
        return job

    @staticmethod
    def summary(job):
        return {"job_id": job["job_id"], "name": job["label"], "status": job["status"], "ownership": job["metadata"]}

    def tools(self):
        with self.lock:
            if self.inventory is None:
                client = self.client("EP tool inventory")
                try:
                    self.inventory = client.call("tools/list")["tools"]
                finally:
                    client.close()  # tools/list does not open a Chrome connection.
        inventory = [copy.deepcopy(t) for t in self.inventory if t["name"] != "browser_install"]
        for tool in inventory:
            schema = tool["inputSchema"]
            schema.setdefault("properties", {})["job_id"] = {"type": "string", "description": "Exact handle returned by browser_job_start for THIS task. Required on every call."}
            schema.setdefault("required", []).append("job_id")
            tool["description"] = "Within the named browser job only. " + tool.get("description", "")
            if tool["name"] == "browser_close":
                tool["description"] = "Finish this job; close only its owned pages, connector and transport."
            if tool["name"] == "browser_tabs":
                tool["description"] += " Use the same indices shown by ordinary tools' Open tabs. The Welcome connector index is protected and cannot be selected or closed."
        for name, description, props in (
            ("browser_job_start", "Create a separate connection and window in the verified existing signed-in profile for this task. Never reuse another task's job_id.", {"name": {"type": "string", "minLength": 1, "maxLength": 80}}),
            ("browser_job_status", "Read only this job's lifecycle and ownership receipt.", {"job_id": {"type": "string"}}),
            ("browser_job_finish", "Close only this job's pages and connection, preserving all peers.", {"job_id": {"type": "string"}}),
            ("browser_job_recover", "Reconcile and close the failed job's exact unclaimed pages, then allocate a new connection. Task page state is lost; no business action is replayed. Refuses uncertain ownership.", {"job_id": {"type": "string"}}),
        ):
            inventory.append({"name": name, "description": description, "inputSchema": {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}})
        return {"tools": inventory}

    def policy(self, name, arguments):
        try:
            decision = self.guard.decide({"tool_name": name, "tool_input": arguments, "cwd": os.getcwd()})
        except Exception:
            raise Refusal("headless_policy_failed") from None
        if decision and decision[0] == "deny":
            return result({"headless_route": decision[1]}, True), None
        return None, decision[1] if decision else None

    def prime(self, job):
        if job["status"] != "ready":
            raise Refusal("job_not_ready_finish_or_recover")
        if self.preflight() != job["generation"]:
            raise Refusal("browser_generation_changed_no_replay")
        self.verify_connection(job)
        own = code(job["client"], STATE_JS + "if(!s.task||s.task.isClosed())throw Error('owned_page_closed');return {index:s.connector.context().pages().indexOf(s.task)};")
        reply = job["client"].call("tools/call", {"name": "browser_tabs", "arguments": {"action": "select", "index": own["index"]}})
        if reply.get("isError"):
            raise Refusal("owned_page_selection_failed")

    def verify_connection(self, job):
        observed = self.metadata(job["client"])
        old = job["metadata"]
        if not old or any(observed[k] != old[k] for k in ("connectorId", "windowId", "groupId", "groupTitle")):
            raise Refusal("connection_ownership_changed")
        return observed

    def tabs(self, job, args):
        action = args.get("action")
        index = args.get("index")
        if index is not None and (type(index) is not int or index < 0):
            raise Refusal("owned_tab_index_invalid")
        # Preserve vendor context indices on every result. Connector retains its
        # reserved index but can never be selected or closed through this tool.
        body = STATE_JS + "let all=s.connector.context().pages();let tabs=all.filter(p=>p!==s.connector&&s.created.has(p));"
        if action == "new":
            body += "s.task=await s.create();all=s.connector.context().pages();tabs=all.filter(p=>p!==s.connector&&s.created.has(p));"
            if args.get("url"):
                body += "await s.task.goto(" + json.dumps(args["url"]) + ");"
        elif action in ("select", "close"):
            body += "const target=" + ("s.task" if index is None and action == "close" else "all[" + json.dumps(index) + "]") + ";if(!target||target===s.connector||!s.created.has(target)||target.isClosed())return {error:'Owned tab index not found or protected connector'};"
            if action == "close":
                body += "await s.closePage(target);tabs=tabs.filter(p=>p!==target);if(s.task===target)s.task=tabs[0]||null;"
            else:
                body += "s.task=target;"
        elif action != "list":
            raise Refusal("owned_tab_action_invalid")
        body += "all=s.connector.context().pages();return {tabs:await Promise.all(tabs.map(async(p)=>({index:all.indexOf(p),current:p===s.task,url:p.url(),title:await p.title()})))};"
        value = code(job["client"], body)
        return result(value, "error" in value)

    def dispose_live(self, job):
        client = job["client"]
        if self.preflight() != job["generation"]:
            raise Refusal("browser_generation_changed_no_cleanup")
        observed = self.metadata(client, strict=False)
        if any(observed[k] != job["metadata"][k] for k in ("connectorId", "windowId", "groupId", "groupTitle")):
            raise Refusal("connection_ownership_changed")
        code(client, STATE_JS + "await s.closeCreated();return {closed:true};")
        code(client, STATE_JS + "return await s.connector.evaluate(async()=>{const t=await chrome.tabs.getCurrent();setTimeout(()=>chrome.tabs.remove(t.id),250);return {scheduled:true};});")
        time.sleep(.4)
        client.close()
        job["ownership_pending"] = False

    def dispose_failed(self, job):
        """Use a fresh own connector to reconcile exact unclaimed old IDs only."""
        if job["client"] and not job["client"].closed:
            # Capture any page created just before an interrupted response while
            # this exact live connection can still prove its scope.
            try:
                self.dispose_live(job)
                return
            except Exception:
                pass
            job["client"].close()
        old = job["metadata"]
        if not old:
            raise Refusal("creation_outcome_unknown_requires_reconciliation")
        if job.get("ownership_pending"):
            raise Refusal("uncheckpointed_page_creation_requires_reconciliation")
        if old.get("unboundOwnedPages"):
            raise Refusal("unbound_owned_pages_require_reconciliation")
        if self.preflight() != job["generation"]:
            raise Refusal("browser_generation_changed_requires_reconciliation")
        maintenance = {**job, "client_name": "EP cleanup " + uuid.uuid4().hex, "metadata": None, "client": None}
        # Never save the temporary connection over the original receipt.
        client = self.client(maintenance["client_name"])
        try:
            code(client, "const p=Buffer.constructor('return process')();if(page.context().pages().length!==1||!page.url().startsWith(" + json.dumps(EXTENSION + "?") + "))throw Error('not_own_connector');p.__epBrowserJob={connector:page,task:null};return {ready:true};")
            outcome = code(client, STATE_JS + "return await s.connector.evaluate(async({old,clientName,connectorOrigin})=>{"
                           "const incomplete=tabs=>{const descendants=new Set(old.tabIds);let changed;do{changed=false;for(const t of tabs)if(descendants.has(t.openerTabId)&&!descendants.has(t.id)){descendants.add(t.id);changed=true;}}while(changed);return tabs.some(t=>(t.windowId===old.windowId||descendants.has(t.id))&&!old.tabIds.includes(t.id));};"
                           "if(incomplete(await chrome.tabs.query({})))throw Error('uncheckpointed_page_arrival');"
                           "const before=await chrome.tabs.query({});"
                           "const live=[];for(const id of old.tabIds){try{live.push(await chrome.tabs.get(id));}catch{throw Error('saved_owned_tab_missing');}}"
                           # The extension intentionally ungroups its tabs after
                           # disconnect. Anchor the ungrouped case to the saved
                           # connector's exact client identity and browser epoch.
                           "const connector=live.find(t=>t.id===old.connectorId);if(!connector)throw Error('connector_identity_missing');"
                           "const u=new URL(connector.url);if(u.protocol+'//'+u.host+u.pathname!==connectorOrigin||JSON.parse(u.searchParams.get('client')).name!==clientName)throw Error('connector_identity_changed');"
                           "const status=await chrome.runtime.sendMessage({type:'getConnectionStatus'});if(!Array.isArray(status.connections))throw Error('connection_status_unavailable');"
                           "const targets=await chrome.debugger.getTargets();"
                           "for(const t of live){if(t.windowId!==old.windowId||(t.groupId!==old.groupId&&t.groupId!==-1)||targets.some(x=>x.tabId===t.id&&x.attached)||status.connections.some(c=>c.connectedTabIds.includes(t.id)))throw Error('ownership_changed');"
                           "if(t.groupId!==-1){const g=await chrome.tabGroups.get(t.groupId);if(g.title!==old.groupTitle)throw Error('group_identity_changed');}}"
                           "await chrome.tabs.remove(live.map(t=>t.id));"
                           "const beforeIds=new Set(before.map(t=>t.id));"
                           "const after=await chrome.tabs.query({});if(after.some(t=>old.tabIds.includes(t.id)||!beforeIds.has(t.id))||incomplete(after))throw Error('owned_cleanup_inventory_uncertain');"
                           "return {closed:true,count:live.length};}," + json.dumps({"old": old, "clientName": job["client_name"], "connectorOrigin": EXTENSION}) + ");")
            if outcome.get("closed") is not True:
                raise Refusal("failed_cleanup_uncertain")
        finally:
            try:
                code(client, STATE_JS + "return await s.connector.evaluate(async()=>{const t=await chrome.tabs.getCurrent();setTimeout(()=>chrome.tabs.remove(t.id),250);return {scheduled:true};});")
                time.sleep(.4)
            finally:
                client.close()

    def finish(self, job):
        if job["status"] == "finished":
            return result(self.summary(job))
        with self.bootstrap():
            if job["status"] == "ready" and job["client"] and not job["client"].closed:
                try:
                    self.dispose_live(job)
                except Exception:
                    self.checkpoint(job, "failed")
                    self.dispose_failed(job)
            else:
                self.dispose_failed(job)
        self.checkpoint(job, "finished")
        return result(self.summary(job))

    def call(self, name, arguments):
        if name == "browser_job_start":
            return self.start(arguments.get("name"))
        job = self.get(arguments.get("job_id"))
        args = {k: v for k, v in arguments.items() if k != "job_id"}
        with job["lock"]:
            if name == "browser_job_status":
                return result(self.summary(job))
            if name in ("browser_job_finish", "browser_close"):
                return self.finish(job)
            if name == "browser_job_recover":
                if job["status"] != "failed":
                    raise Refusal("only_failed_jobs_recover")
                try:
                    self.finish(job)
                    with self.bootstrap():
                        job.update(client_name="EP " + job["label"] + " [" + uuid.uuid4().hex[:8] + "]", generation=self.preflight(), metadata=None, client=None)
                        self.checkpoint(job, "starting")
                        self.connect(job)
                    return result({**self.summary(job), "previous_pages_closed": True, "business_actions_replayed": False, "task_state_lost": True})
                except Exception:
                    self.checkpoint(job, "failed")
                    return result({**self.summary(job), "error": "Recovery refused or incomplete; preserve the exact receipt and do not replay work."}, True)
            if name == "browser_install" or name not in {t["name"] for t in self.inventory or []}:
                raise Refusal("unknown_browser_tool")
            denied, note = self.policy(name, args)
            if denied:
                return denied
            try:
                if name == "browser_tabs":
                    if job["status"] != "ready":
                        raise Refusal("job_not_ready")
                    if self.preflight() != job["generation"]:
                        raise Refusal("browser_generation_changed_no_replay")
                    self.verify_connection(job)
                    job["ownership_pending"] = True
                    self.checkpoint(job)
                    reply = self.tabs(job, args)
                else:
                    self.prime(job)
                    job["ownership_pending"] = True
                    self.checkpoint(job)
                    reply = job["client"].call("tools/call", {"name": name, "arguments": args})
                job["metadata"] = self.verify_connection(job)
                job["ownership_pending"] = False
                self.checkpoint(job)
                if note:
                    reply.setdefault("content", []).append({"type": "text", "text": note})
                return redact(reply)
            except Exception:
                self.checkpoint(job, "failed")
                return result({"job_id": job["job_id"], "status": "failed", "error": "Operation outcome uncertain. Inspect before retrying; no automatic replay. Use finish or recover for this job."}, True)

    def shutdown(self):
        # EOF and normal termination dispose this facade's own jobs only.
        for job in list(self.jobs.values()):
            with job["lock"]:
                try:
                    self.finish(job)
                except Exception:
                    self.checkpoint(job, "failed")
                finally:
                    if job["client"] and not job["client"].closed:
                        job["client"].close()


def serve(route):
    output_lock = threading.Lock()
    workers = set()
    workers_lock = threading.Lock()

    def emit(value):
        with output_lock:
            sys.stdout.write(json.dumps(redact(value), ensure_ascii=False) + "\n")
            sys.stdout.flush()

    def handle(message):
        try:
            method = message.get("method")
            if "id" not in message:
                return
            if method == "initialize":
                value = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "expert-partners-browser-jobs", "version": "1.0"}, "instructions": "Start a new browser job for each task. Pass its exact job_id to every browser tool. Finish your job before reporting. Never reuse a peer handle."}
            elif method == "ping":
                value = {}
            elif method == "tools/list":
                value = route.tools()
            elif method == "tools/call":
                params = message.get("params", {})
                value = route.call(params["name"], params.get("arguments", {}))
            else:
                emit({"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32601, "message": "Method not supported"}})
                return
            emit({"jsonrpc": "2.0", "id": message["id"], "result": value})
        except Exception:
            # Never echo an exception: it can include a protected command or URL.
            emit({"jsonrpc": "2.0", "id": message.get("id"), "error": {"code": -32000, "message": "Browser job request refused; check the exact job, signed-in route and local ownership receipt."}})
        finally:
            with workers_lock:
                workers.discard(threading.current_thread())

    try:
        while True:
            line = sys.stdin.buffer.readline(1048577)
            if not line:
                break
            if len(line) > 1048576:
                raise Refusal("request_too_large")
            try:
                message = json.loads(line)
                if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                    raise ValueError()
            except ValueError:
                emit({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Invalid JSON-RPC request"}})
                continue
            worker = threading.Thread(target=handle, args=(message,))
            with workers_lock:
                workers.add(worker)
            worker.start()
    finally:
        with workers_lock:
            pending = list(workers)
        for worker in pending:
            worker.join()
        route.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text())
        route = Route(config)
        def terminate(_signum, _frame):
            raise SystemExit(0)
        signal.signal(signal.SIGTERM, terminate)
        serve(route)
    except Exception:
        print("Browser jobs route refused; verify its protected local configuration and signed-in browser host", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
