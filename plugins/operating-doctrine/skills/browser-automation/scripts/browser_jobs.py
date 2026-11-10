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

from chrome_job_window import existing_signed_in_profile, chrome_is_running, verify_window_closed
from job_transport import StdioClient, Refusal
from browser_lifecycle import bind, owner_path, identifier


EXTENSION = "chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/connect.html"
STATE_JS = "const s=Buffer.constructor('return process')().__epBrowserJob;if(!s)throw Error('owned_state_missing');"
OWNED_SOURCE = Path(__file__).with_name("owned_pages.js").read_text()
SAFE_ENV = ("HOME", "USER", "LOGNAME", "PATH", "LANG", "LC_ALL", "TMPDIR")
# Silences this private MCP process's Tab capture before the vendor builds the
# response: console/page errors (and its console-*.log file), request events,
# downloads, snapshots, modal text and tab headers. The process exits at finish,
# so the job stays finish-only instead of restoring capture over revealed state.
SEAL_JS = (
    STATE_JS + "if(s.task!==page)throw Error('sealed_target_not_owned_task');"
    "const k=Object.getOwnPropertySymbols(page).find(x=>page[x]&&typeof page[x].captureSnapshot==='function');const tab=k&&page[k];"
    "if(!tab||!tab.context||typeof tab.context.tabs!=='function')throw Error('sealed_capture_unavailable');"
    "if(tab.context.sessionLog)throw Error('sealed_session_log_active');const T=Object.getPrototypeOf(tab);"
    "for(const m of ['_handleConsoleMessage','_addLogEntry','_handleRequest','_handleResponse','_handleRequestFailed','_downloadStarted','captureSnapshot','headerSnapshot'])"
    "if(typeof T[m]!=='function')throw Error('sealed_capture_unavailable');"
    "const quiet=()=>{};T._handleConsoleMessage=quiet;T._addLogEntry=quiet;T._handleRequest=quiet;T._handleResponse=quiet;T._handleRequestFailed=quiet;"
    "T._downloadStarted=async()=>{};T.captureSnapshot=async function(){return {ariaSnapshot:'',modalStates:[],events:[]};};"
    "T.headerSnapshot=async function(){return {title:'',url:'',current:this.isCurrentTab(),crashed:false,console:{total:0,errors:0,warnings:0},changed:false};};"
    "const scrub=()=>{for(const t of tab.context.tabs()){t._consoleLog?.stop();t._recentEventEntries=[];if(Array.isArray(t._requests))t._requests.length=0;}};"
    "scrub();s.sealed=true;let ok=false;"
    "try{const fn=Buffer.constructor('return ('+__SEALED_SOURCE__+')')();await fn(page);ok=true;}catch{}"
    "finally{try{await page.clearConsoleMessages();await page.clearPageErrors();}catch{}scrub();}"
    "return {sealed:ok?'ok':'error'};"
)
SEALED_OUTCOMES = {"ok": None, "error": "sealed_code_failed"}
# Static codes this route's own browser code throws; nothing else is projected.
OWNED_ERROR_CODES = frozenset(
    re.findall(r"Error\('([a-z_]+)'\)", OWNED_SOURCE + Path(__file__).read_text())
)
# Fixed Playwright and extension failure phrases (MCP 0.0.83), checked in order.
# Only the static label is kept, so page text that happens to match leaks nothing.
VENDOR_ERROR_CLASSES = (
    (
        "vendor_target_closed",
        r"Target page, context or browser has been closed|Page has been closed|Target closed",
    ),
    ("vendor_context_destroyed", r"Execution context was destroyed"),
    ("vendor_frame_detached", r"Frame was detached"),
    ("vendor_extension_disconnected", r"Extension disconnected"),
    ("vendor_transport_closed", r"Pipe has been closed"),
    ("vendor_no_open_tabs", r"No open tabs"),
    ("vendor_timeout", r"Timeout \d+ms exceeded"),
)
VENDOR_ERROR_NOTE = (
    "Browser job route: the browser tool reported an error, so this action's outcome is "
    "uncertain. Inspect the page before any retry; nothing was replayed."
)
WORKING_PAGE_LOST_NOTE = (
    "Browser job route: the working page lost its browser connection during this call, so the "
    "job is now failed. Do not replay the action. Use browser_job_finish, or browser_job_recover "
    "for a fresh working page."
)
TIMING_RECORDS = 20
GENERATION_ATTEMPTS = 30


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
    return {
        "content": [{"type": "text", "text": json.dumps(redact(value), ensure_ascii=False)}],
        "isError": error,
    }


def vendor_error_class(reply):
    """Fixed label for a vendor error reply, or None. Never returns reply text."""
    text = "\n".join(b.get("text", "") for b in reply.get("content", []) if isinstance(b, dict))
    return next(
        (label for label, pattern in VENDOR_ERROR_CLASSES if re.search(pattern, text)), None
    )


def projection(reply):
    if reply.get("isError"):
        # Vendor error text can carry page content. Keep only a static code
        # this route itself throws, so receipts show why an owned step failed.
        text = "\n".join(b.get("text", "") for b in reply.get("content", []) if isinstance(b, dict))
        found = sorted(c for c in OWNED_ERROR_CODES if re.search(r"\b" + c + r"\b", text))
        label = found[0] if found else vendor_error_class(reply)
        raise Refusal("owned_operation_failed" + (":" + label if label else ""))
    blocks = reply.get("content", [])
    if len(blocks) != 1 or blocks[0].get("type") != "text":
        raise Refusal("owned_projection_shape")
    text = blocks[0]["text"]
    if not text.startswith("### Result\n"):
        raise Refusal("owned_projection_heading")
    try:
        value, _ = json.JSONDecoder().raw_decode(text[len("### Result\n") :])
    except ValueError:
        raise Refusal("owned_projection_json") from None
    if not isinstance(value, dict):
        raise Refusal("owned_projection_type")
    return value


def failed_cleanup_js(args, remove):
    """Reconcile a failed job's saved IDs from a fresh maintenance connector.

    Phase one (remove=False) only proves ownership; phase two repeats every
    check and closes the exact saved window.
    """
    return (
        STATE_JS
        + "return await s.connector.evaluate(async({old,clientName,connectorOrigin,removalIssued,pendingSince,remove})=>{"
        "const incomplete=tabs=>{const descendants=new Set(old.tabIds);let changed;do{changed=false;for(const t of tabs)if(descendants.has(t.openerTabId)&&!descendants.has(t.id)){descendants.add(t.id);changed=true;}}while(changed);return tabs.some(t=>(t.windowId===old.windowId||descendants.has(t.id))&&!old.tabIds.includes(t.id));};"
        "const self=pendingSince===null?null:(await chrome.tabs.getCurrent()).id;"
        # An interrupted call may have created a page and then closed it,
        # orphaning a popup it opened elsewhere. Chrome tab IDs only grow
        # within one browser generation, so any surviving tab born after the
        # last proven inventory, other than this maintenance connector, may be
        # that orphan. A peer's new tab is refused too, never adopted.
        "const unproven=tabs=>self!==null&&tabs.some(t=>t.id>pendingSince&&t.id!==self&&!old.tabIds.includes(t.id));"
        "const before=await chrome.tabs.query({});"
        "if(incomplete(before)||unproven(before))throw Error('uncheckpointed_page_arrival');"
        "const live=before.filter(t=>old.tabIds.includes(t.id));"
        # Every saved tab gone is explained only by a removal this route
        # already issued. Otherwise a popup may have escaped and lost its
        # opener link when its parent closed.
        "if(!live.length){if(removalIssued&&!before.some(t=>t.windowId===old.windowId))return {closed:true,count:0,alreadyClosed:true};throw Error('saved_owned_tab_missing');}"
        # The connector is an extension page that never opens popups, so its
        # absence alone cannot hide an unrecorded descendant. A missing
        # working page can, so that still refuses.
        "if(old.tabIds.some(id=>id!==old.connectorId&&!live.some(t=>t.id===id)))throw Error('saved_owned_tab_missing');"
        # The extension intentionally ungroups its tabs after disconnect.
        # When the connector survives, anchor to its exact client identity.
        "const connector=live.find(t=>t.id===old.connectorId);"
        "if(connector){const u=new URL(connector.url);if(u.protocol+'//'+u.host+u.pathname!==connectorOrigin||JSON.parse(u.searchParams.get('client')).name!==clientName)throw Error('connector_identity_changed');}"
        "const status=await chrome.runtime.sendMessage({type:'getConnectionStatus'});if(!status||!Array.isArray(status.connections))throw Error('connection_status_unavailable');"
        "const targets=await chrome.debugger.getTargets();"
        "for(const t of live){if(t.windowId!==old.windowId||(t.groupId!==old.groupId&&t.groupId!==-1)||targets.some(x=>x.tabId===t.id&&x.attached)||status.connections.some(c=>(c.connectedTabIds||[]).includes(t.id)))throw Error('ownership_changed');"
        "if(t.groupId!==-1){const g=await chrome.tabGroups.get(t.groupId);if(g.title!==old.groupTitle)throw Error('group_identity_changed');}}"
        "if(!remove)return {ready:true,count:live.length,connectorMissing:!connector};"
        "await chrome.windows.remove(old.windowId);"
        "const beforeIds=new Set(before.map(t=>t.id));"
        # Chrome can still list a removed window's tabs for a moment.
        "let after;for(let i=0;i<20;i++){after=await chrome.tabs.query({});if(!after.some(t=>old.tabIds.includes(t.id)||t.windowId===old.windowId))break;await new Promise(r=>setTimeout(r,100));}"
        "if(after.some(t=>old.tabIds.includes(t.id)||t.windowId===old.windowId||!beforeIds.has(t.id))||incomplete(after))throw Error('owned_cleanup_inventory_uncertain');"
        "return {closed:true,count:live.length,connectorMissing:!connector};},"
        + json.dumps({"pendingSince": None, **args, "remove": remove})
        + ");"
    )


def failure_stage(error):
    # Refusal codes are static; any other exception keeps only its class name.
    return "failed:" + (str(error) if type(error) is Refusal else type(error).__name__)


def code(client, body):
    return projection(
        client.call(
            "tools/call",
            {
                "name": "browser_run_code_unsafe",
                "arguments": {"code": "async(page)=>{" + body + "}"},
            },
        )
    )


def chrome_generation():
    """Read only the main Chrome process identity, never its credential-bearing argv."""
    for attempt in range(GENERATION_ATTEMPTS):
        ids = subprocess.run(
            ["/usr/bin/pgrep", "-x", "Google Chrome"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        ).stdout.split()
        if len(ids) == 1 and ids[0].isdigit():
            break
        # Every exec of the Chrome binary, including a peer job's window
        # wrapper, runs a short-lived second "Google Chrome" that hands off to
        # the running browser and exits. Wait that out; persistent ambiguity
        # still refuses.
        if attempt == GENERATION_ATTEMPTS - 1:
            raise Refusal("chrome_generation_ambiguous")
        time.sleep(0.1)
    stamp = subprocess.run(
        ["/bin/ps", "-p", ids[0], "-o", "lstart="],
        capture_output=True,
        text=True,
        timeout=3,
        check=True,
    ).stdout.strip()
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
        self.control_socket = "control-" + uuid.uuid4().hex[:16] + ".sock"
        self.control_listener = socket.socket(socket.AF_UNIX)
        self.control_listener.bind(str(self.root / self.control_socket))
        os.chmod(self.root / self.control_socket, 0o600)
        self.control_listener.listen(8)
        threading.Thread(target=self.serve_control, daemon=True).start()

    def serve_control(self):
        """Private same-user lifecycle channel, not another browser connection."""
        while True:
            try:
                connection, _ = self.control_listener.accept()
            except OSError:
                return
            with connection:
                try:
                    connection.settimeout(120)
                    with connection.makefile("rb") as stream:
                        request = json.loads(stream.readline(4097))
                    job = self.get(request["job_id"])
                    owner = json.loads(owner_path(self.root, job["job_id"]).read_text())
                    if (
                        request.get("action") != "finish"
                        or owner["state"] != "terminal"
                        or owner["session_id"] != request["session_id"]
                    ):
                        raise Refusal("terminal_owner_required")
                    with job["lock"]:
                        self.finish(job)
                    reply = {"ok": True, "job_id": job["job_id"]}
                except Exception:
                    reply = {"ok": False}
                try:
                    connection.sendall((json.dumps(reply) + "\n").encode())
                except OSError:
                    pass

    def close_control(self):
        listener = getattr(self, "control_listener", None)
        if listener:
            listener.close()
            (self.root / self.control_socket).unlink(missing_ok=True)

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
                    time.sleep(0.05)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def client(self, name):
        self.preflight()
        env = {k: os.environ[k] for k in SAFE_ENV if k in os.environ}
        env.update(
            npm_config_offline="true",
            npm_config_update_notifier="false",
            npm_config_audit="false",
            npm_config_fund="false",
            npm_config_logs_max="0",
            EP_BROWSER_EXPECTED_ACCOUNT=self.config["expected_account"],
        )
        wrapper = str(Path(__file__).with_name("chrome_job_window.py"))
        client = StdioClient(
            [self.config["launcher"], "--executable-path", wrapper],
            env,
            timeout=45,
            cap=16777216,
            frame_cap=12582912,
        )
        try:
            init = client.call(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": name, "version": "1.0"},
                },
            )
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
        row = {
            k: job[k]
            for k in (
                "job_id",
                "label",
                "status",
                "client_name",
                "generation",
                "metadata",
                "updated",
            )
        }
        row["ownership_pending"] = job.get("ownership_pending", False)
        row["sealed"] = job.get("sealed", False)
        # Stage names and wall times only, so a hung call shows where it stopped.
        row["timings"] = job.get("timings", [])
        row["control_socket"] = getattr(self, "control_socket", None)
        if job.get("window_disposition"):
            row["window_disposition"] = job["window_disposition"]
        if job.get("window_removal_issued"):
            row["window_removal_issued"] = True
        path = self.root / (job["job_id"] + ".json")
        if self.settled_elsewhere(job):
            # Another route (sweep or reconciliation) already settled this job.
            # A stale facade never reopens a finished receipt.
            job["status"] = "finished"
            return
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

    def settled_elsewhere(self, job):
        if job.get("receipt_owned") or job.get("status") == "finished":
            return False
        try:
            disk = json.loads((self.root / (job["job_id"] + ".json")).read_text())
        except (OSError, ValueError, KeyError):
            return False
        return disk.get("status") == "finished"

    @staticmethod
    def mark(job, stage):
        records = job.get("timings")
        if records:
            records[-1]["stages"].append([stage, round(time.time(), 3)])

    def checkpoint(self, job, status=None):
        if status:
            job["status"] = status
        if status == "finished":
            job["receipt_owned"] = True
        job["updated"] = time.time()
        self.save(job)

    def metadata(self, client, strict=True):
        return code(client, STATE_JS + "return await s.snapshot(" + json.dumps(strict) + ");")

    def connect(self, job, working=True):
        client = self.client(job["client_name"])
        job["client"] = client
        # State is in this private Node process, not the ephemeral VM globals.
        initialized = code(
            client,
            OWNED_SOURCE
            + "const p=Buffer.constructor('return process')();if(p.__epBrowserJob)throw Error('already_attempted');"
            "if(page.context().pages().length!==1||!page.url().startsWith("
            + json.dumps(EXTENSION + "?")
            + "))throw Error('not_fresh_connector');"
            "p.__epBrowserJob=await newOwnedState(page);const s=p.__epBrowserJob;return {ready:true,ownership:{...s.initial,tabIds:[...s.ids.values()],unboundOwnedPages:0}};",
        )
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
            job["metadata"].pop("workingPage", None)
            if len(job["metadata"]["tabIds"]) != 2:
                raise Refusal("owned_page_count_mismatch")
            job["ownership_pending"] = False
            self.checkpoint(job, "ready")
        return client

    def start(self, label, owner_session_id=None):
        if (
            not isinstance(label, str)
            or not 1 <= len(label.strip()) <= 80
            or any(ord(c) < 32 for c in label)
        ):
            raise Refusal("job_name_required")
        if owner_session_id is not None:
            identifier(owner_session_id)
        job_id = uuid.uuid4().hex
        job = {
            "job_id": job_id,
            "label": label.strip(),
            "status": "starting",
            "client_name": "EP " + label.strip() + " [" + job_id[:8] + "]",
            "generation": None,
            "metadata": None,
            "updated": time.time(),
            "ownership_pending": False,
            "client": None,
            "lock": threading.RLock(),
        }
        with self.lock:
            self.jobs[job_id] = job
        with job["lock"]:
            try:
                with self.bootstrap():
                    job["generation"] = self.preflight()
                    self.checkpoint(job)
                    if owner_session_id is not None:
                        bind(self.root, job_id, owner_session_id)
                    self.connect(job)
                return result(self.summary(job))
            except BaseException:
                self.checkpoint(job, "failed")
                # Caller gets the handle even if allocation failed. Never hide
                # an uncertain creation behind an automatic second attempt.
                return result(
                    {
                        **self.summary(job),
                        "error": "Allocation failed; finish or recover this exact job before replacing it.",
                    },
                    True,
                )

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
        return {
            "job_id": job["job_id"],
            "name": job["label"],
            "status": job["status"],
            "ownership": job["metadata"],
        }

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
            schema.setdefault("properties", {})["job_id"] = {
                "type": "string",
                "description": "Exact handle returned by browser_job_start for THIS task. Required on every call.",
            }
            schema.setdefault("required", []).append("job_id")
            tool["description"] = "Within the named browser job only. " + tool.get(
                "description", ""
            )
            if tool["name"] == "browser_close":
                tool["description"] = (
                    "Finish this job; close only its owned pages, connector and transport."
                )
            if tool["name"] == "browser_tabs":
                tool["description"] += (
                    " Use the same indices shown by ordinary tools' Open tabs. The Welcome connector index is protected and cannot be selected or closed."
                )
            if tool["name"] == "browser_run_code_unsafe":
                schema["properties"]["sealed"] = {
                    "type": "boolean",
                    "description": "Opt in for one secret-bearing call: pass only code. Console, events, snapshot and tab headers are not captured, the code is not echoed, and the reply is only {\"sealed\": \"ok\"} or a fixed error code. Afterwards this job only accepts browser_job_status and browser_job_finish.",
                }
        for name, description, props in (
            (
                "browser_job_start",
                "Create a separate connection and window in the verified existing signed-in profile for this task. Native hooks supply owner_session_id so Stop/SessionEnd close the entire owned window. Never reuse another task's job_id.",
                {
                    "name": {"type": "string", "minLength": 1, "maxLength": 80},
                    "owner_session_id": {
                        "type": "string",
                        "description": "Native session ID, supplied by the lifecycle hook. Never use a peer session ID.",
                    },
                },
            ),
            (
                "browser_job_status",
                "Read only this job's lifecycle and ownership receipt.",
                {"job_id": {"type": "string"}},
            ),
            (
                "browser_job_finish",
                "Close only this job's pages and connection, preserving all peers.",
                {"job_id": {"type": "string"}},
            ),
            (
                "browser_job_recover",
                "Reconcile and close the failed job's exact unclaimed pages, then allocate a new connection. Task page state is lost; no business action is replayed. Refuses uncertain ownership.",
                {"job_id": {"type": "string"}},
            ),
        ):
            inventory.append(
                {
                    "name": name,
                    "description": description,
                    "inputSchema": {
                        "type": "object",
                        "properties": props,
                        "required": [key for key in props if key != "owner_session_id"],
                        "additionalProperties": False,
                    },
                }
            )
        return {"tools": inventory}

    def policy(self, name, arguments):
        try:
            decision = self.guard.decide(
                {"tool_name": name, "tool_input": arguments, "cwd": os.getcwd()}
            )
        except Exception:
            raise Refusal("headless_policy_failed") from None
        # Preserve the canonical hook's lazy one-shot refresh. This is policy
        # maintenance on a call, not a new job scheduler or dispatch timer.
        due = getattr(self.guard, "refresh_due", None)
        refresh = getattr(self.guard, "start_background_refresh", None)
        if callable(due) and callable(refresh) and due():
            refresh()
        if decision and decision[0] == "deny":
            return result({"headless_route": decision[1]}, True), None
        return None, decision[1] if decision else None

    def prime(self, job):
        if job["status"] != "ready":
            raise Refusal("job_not_ready_finish_or_recover")
        if self.preflight() != job["generation"]:
            raise Refusal("browser_generation_changed_no_replay")
        self.mark(job, "prime_preflight")
        self.verify_connection(job)
        self.mark(job, "prime_verify")
        own = code(
            job["client"],
            STATE_JS
            + "if(!s.task||s.task.isClosed())throw Error('owned_page_closed');return {index:s.connector.context().pages().indexOf(s.task)};",
        )
        self.mark(job, "prime_own_index")
        reply = job["client"].call(
            "tools/call",
            {"name": "browser_tabs", "arguments": {"action": "select", "index": own["index"]}},
        )
        if reply.get("isError"):
            raise Refusal("owned_page_selection_failed")
        self.mark(job, "prime_select")

    def verify_connection(self, job):
        observed = self.metadata(job["client"])
        old = job["metadata"]
        if not old or any(
            observed[k] != old[k] for k in ("connectorId", "windowId", "groupId", "groupTitle")
        ):
            raise Refusal("connection_ownership_changed")
        # Liveness of the retained Playwright Page, kept out of the saved
        # ownership metadata. Chrome can detach the debugger from a tab that
        # stays open, which closes the Page without changing any tab ID.
        job["working_page"] = observed.pop("workingPage", None)
        return observed

    def tabs(self, job, args):
        action = args.get("action")
        index = args.get("index")
        if index is not None and (type(index) is not int or index < 0):
            raise Refusal("owned_tab_index_invalid")
        # Preserve vendor context indices on every result. Connector retains its
        # reserved index but can never be selected or closed through this tool.
        body = (
            STATE_JS
            + "let all=s.connector.context().pages();let tabs=all.filter(p=>p!==s.connector&&s.created.has(p));"
        )
        if action == "new":
            body += "s.task=await s.create();all=s.connector.context().pages();tabs=all.filter(p=>p!==s.connector&&s.created.has(p));"
            if args.get("url"):
                body += "await s.task.goto(" + json.dumps(args["url"]) + ");"
        elif action in ("select", "close"):
            body += (
                "const target="
                + (
                    "s.task"
                    if index is None and action == "close"
                    else "all[" + json.dumps(index) + "]"
                )
                + ";if(!target||target===s.connector||!s.created.has(target)||target.isClosed())return {error:'Owned tab index not found or protected connector'};"
            )
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
        if any(
            observed[k] != job["metadata"][k]
            for k in ("connectorId", "windowId", "groupId", "groupTitle")
        ):
            raise Refusal("connection_ownership_changed")
        self.mark(job, "live_metadata")
        code(client, STATE_JS + "await s.closeCreated();return {closed:true};")
        self.mark(job, "live_pages_closed")
        closing = code(client, STATE_JS + "return await s.closeWindow();")
        self.mark(job, "live_window_scheduled")
        time.sleep(0.4)
        if not closing.get("shared"):
            verify_window_closed(job["metadata"]["windowId"])
        job["window_disposition"] = "preserved_shared" if closing.get("shared") else "closed"
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
            except Exception as error:
                self.mark(job, "live_" + failure_stage(error))
            job["client"].close()
        old = job["metadata"]
        if not old:
            raise Refusal("creation_outcome_unknown_requires_reconciliation")
        pending_since = old.get("newestTabId") if job.get("ownership_pending") else None
        if job.get("ownership_pending") and type(pending_since) is not int:
            # No proven pre-call watermark, so an orphaned popup could escape.
            raise Refusal("uncheckpointed_page_creation_requires_reconciliation")
        if old.get("unboundOwnedPages"):
            raise Refusal("unbound_owned_pages_require_reconciliation")
        if self.preflight() != job["generation"]:
            raise Refusal("browser_generation_changed_requires_reconciliation")
        maintenance = {
            **job,
            "client_name": "EP cleanup " + uuid.uuid4().hex,
            "metadata": None,
            "client": None,
        }
        # Never save the temporary connection over the original receipt.
        client = self.client(maintenance["client_name"])
        try:
            code(
                client,
                "const p=Buffer.constructor('return process')();if(page.context().pages().length!==1||!page.url().startsWith("
                + json.dumps(EXTENSION + "?")
                + "))throw Error('not_own_connector');p.__epBrowserJob={connector:page,task:null};return {ready:true};",
            )
            args = {
                "old": old,
                "clientName": job["client_name"],
                "connectorOrigin": EXTENSION,
                "removalIssued": bool(job.get("window_removal_issued")),
                "pendingSince": pending_since,
            }
            outcome = code(client, failed_cleanup_js(args, remove=False))
            self.mark(job, "reconcile_proven")
            if outcome.get("ready") is True:
                # Recorded before removal so a retry after an interrupted close
                # can prove the vanished window was this route's own removal.
                job["window_removal_issued"] = True
                self.checkpoint(job)
                outcome = code(client, failed_cleanup_js(args, remove=True))
            if outcome.get("closed") is not True:
                raise Refusal("failed_cleanup_uncertain")
            verify_window_closed(old["windowId"])
            job["window_disposition"] = "closed"
            job["ownership_pending"] = False
        finally:
            try:
                closed = code(
                    client,
                    STATE_JS
                    + "return await s.connector.evaluate(async()=>{const t=await chrome.tabs.getCurrent();const tabs=await chrome.tabs.query({windowId:t.windowId});if(tabs.length!==1||tabs[0].id!==t.id)throw Error('maintenance_window_not_exclusive');setTimeout(()=>chrome.windows.remove(t.windowId),250);return {scheduled:true,windowId:t.windowId};});",
                )
                time.sleep(0.4)
                if "windowId" in closed:
                    verify_window_closed(closed["windowId"])
            finally:
                client.close()

    def finish(self, job):
        if job["status"] == "finished":
            return result(self.summary(job))
        if self.settled_elsewhere(job):
            # Adopt the settled receipt. This stale client's pages are already
            # gone, so only its own subprocess group is closed.
            if job.get("client") and not job["client"].closed:
                job["client"].close()
            job["status"] = "finished"
            job["receipt_owned"] = True
            return result(self.summary(job))
        job.setdefault("timings", []).append(
            {"tool": "finish", "sealed": False, "stages": [["received", round(time.time(), 3)]]}
        )
        del job["timings"][:-TIMING_RECORDS]
        try:
            with self.bootstrap():
                if job["status"] == "ready" and job["client"] and not job["client"].closed:
                    try:
                        self.dispose_live(job)
                    except Exception as error:
                        self.mark(job, "live_" + failure_stage(error))
                        self.checkpoint(job, "failed")
                        self.dispose_failed(job)
                else:
                    self.dispose_failed(job)
        except Exception as error:
            # The caller sees one generic refusal; the receipt keeps the static step.
            self.mark(job, failure_stage(error))
            self.checkpoint(job)
            raise
        self.mark(job, "finished")
        self.checkpoint(job, "finished")
        return result(self.summary(job))

    def call(self, name, arguments):
        if name == "browser_job_start":
            return self.start(arguments.get("name"), arguments.get("owner_session_id"))
        job = self.get(arguments.get("job_id"))
        sealed = (
            name == "browser_run_code_unsafe"
            and "sealed" in arguments
            and arguments["sealed"] is not False
        )
        args = {
            k: v
            for k, v in arguments.items()
            if k != "job_id" and not (k == "sealed" and name == "browser_run_code_unsafe")
        }
        with job["lock"]:
            if name == "browser_job_status":
                return result(self.summary(job))
            if name in ("browser_job_finish", "browser_close"):
                return self.finish(job)
            if job.get("sealed"):
                return result({"sealed": "error", "code": "sealed_job_finish_only"}, True)
            if sealed and (
                arguments["sealed"] is not True
                or set(args) != {"code"}
                or not isinstance(args["code"], str)
                or not args["code"].strip()
            ):
                return result({"sealed": "error", "code": "sealed_arguments_invalid"}, True)
            if name == "browser_job_recover":
                if job["status"] != "failed":
                    raise Refusal("only_failed_jobs_recover")
                try:
                    self.finish(job)
                    with self.bootstrap():
                        job.update(
                            client_name="EP " + job["label"] + " [" + uuid.uuid4().hex[:8] + "]",
                            generation=self.preflight(),
                            metadata=None,
                            client=None,
                        )
                        self.checkpoint(job, "starting")
                        self.connect(job)
                    return result(
                        {
                            **self.summary(job),
                            "previous_pages_closed": True,
                            "business_actions_replayed": False,
                            "task_state_lost": True,
                        }
                    )
                except Exception:
                    self.checkpoint(job, "failed")
                    return result(
                        {
                            **self.summary(job),
                            "error": "Recovery refused or incomplete; preserve the exact receipt and do not replay work.",
                        },
                        True,
                    )
            if name == "browser_install" or name not in {t["name"] for t in self.inventory or []}:
                raise Refusal("unknown_browser_tool")
            denied, note = self.policy(name, args)
            if denied:
                return denied
            job.setdefault("timings", []).append(
                {"tool": name, "sealed": sealed, "stages": [["received", round(time.time(), 3)]]}
            )
            del job["timings"][:-TIMING_RECORDS]
            if sealed:
                return self.sealed_call(job, args["code"])
            try:
                if name == "browser_tabs":
                    if job["status"] != "ready":
                        raise Refusal("job_not_ready")
                    if self.preflight() != job["generation"]:
                        raise Refusal("browser_generation_changed_no_replay")
                    self.verify_connection(job)
                    job["ownership_pending"] = True
                    self.mark(job, "tool_start")
                    self.checkpoint(job)
                    reply = self.tabs(job, args)
                else:
                    self.prime(job)
                    job["ownership_pending"] = True
                    self.mark(job, "tool_start")
                    self.checkpoint(job)
                    reply = job["client"].call("tools/call", {"name": name, "arguments": args})
                self.mark(job, "tool_end")
                notes = [note] if note else []
                if reply.get("isError") and name != "browser_tabs":
                    self.mark(job, "vendor_error:" + (vendor_error_class(reply) or "unclassified"))
                    notes.append(VENDOR_ERROR_NOTE)
                job["metadata"] = self.verify_connection(job)
                job["ownership_pending"] = False
                self.mark(job, "post_metadata")
                if job.get("working_page") == "closed":
                    # The tab may still be open and showing the page, but no
                    # later call can prove it is the same document. Never
                    # re-bind or replay; finish or recover closes it by exact ID.
                    self.mark(job, "failed:working_page_lost")
                    self.checkpoint(job, "failed")
                    notes.append(WORKING_PAGE_LOST_NOTE)
                else:
                    self.checkpoint(job)
                for text in notes:
                    reply.setdefault("content", []).append({"type": "text", "text": text})
                return redact(reply)
            except Exception as error:
                self.mark(job, failure_stage(error))
                self.checkpoint(job, "failed")
                return result(
                    {
                        "job_id": job["job_id"],
                        "status": "failed",
                        "error": "Operation outcome uncertain. Inspect before retrying; no automatic replay. Use finish or recover for this job.",
                    },
                    True,
                )

    def sealed_call(self, job, source):
        """Run one secret-bearing snippet. Only fixed tokens ever leave this method."""
        try:
            self.prime(job)
            job["sealed"] = True
            job["ownership_pending"] = True
            self.mark(job, "tool_start")
            self.checkpoint(job)
            outcome = code(
                job["client"], SEAL_JS.replace("__SEALED_SOURCE__", json.dumps(source))
            ).get("sealed")
            self.mark(job, "tool_end")
            if outcome not in SEALED_OUTCOMES:
                raise Refusal("sealed_outcome_unknown")
            job["metadata"] = self.verify_connection(job)
            job["ownership_pending"] = False
            self.mark(job, "post_metadata")
            self.checkpoint(job)
        except Exception as error:
            # Provider and page text can carry the secret; keep only the static code.
            self.mark(job, failure_stage(error))
            self.checkpoint(job, "failed")
            return result({"sealed": "error", "code": "sealed_outcome_uncertain"}, True)
        if SEALED_OUTCOMES[outcome]:
            return result({"sealed": "error", "code": SEALED_OUTCOMES[outcome]}, True)
        return result({"sealed": "ok"})

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
        self.close_control()


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
                value = {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "expert-partners-browser-jobs", "version": "1.0"},
                    "instructions": "Start a new browser job for each task. Pass its exact job_id to every browser tool. Finish your job before reporting. Never reuse a peer handle.",
                }
            elif method == "ping":
                value = {}
            elif method == "tools/list":
                value = route.tools()
            elif method == "tools/call":
                params = message.get("params", {})
                value = route.call(params["name"], params.get("arguments", {}))
            else:
                emit(
                    {
                        "jsonrpc": "2.0",
                        "id": message["id"],
                        "error": {"code": -32601, "message": "Method not supported"},
                    }
                )
                return
            emit({"jsonrpc": "2.0", "id": message["id"], "result": value})
        except Exception:
            # Never echo an exception: it can include a protected command or URL.
            emit(
                {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {
                        "code": -32000,
                        "message": "Browser job request refused; check the exact job, signed-in route and local ownership receipt.",
                    },
                }
            )
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
                emit(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Invalid JSON-RPC request"},
                    }
                )
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
        print(
            "Browser jobs route refused; verify its protected local configuration and signed-in browser host",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
