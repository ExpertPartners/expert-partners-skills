#!/usr/bin/env python3
"""Stdio MCP facade allocating a separate existing-profile connection per job.

Runs on the browser host. Configuration names the existing protected launcher;
credentials remain inside that launcher. There is no network listener or scheduler.
"""

import argparse
import contextlib
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
from urllib.parse import quote, urlsplit
import uuid

from chrome_job_window import existing_signed_in_profile, chrome_is_running, verify_window_closed
from job_transport import StdioClient, Refusal
from browser_lifecycle import bind, ledger_lock, owner_path, identifier
from aqua_cleanup import AquaCleanup
from relay_facade import RelayBroker, generation_key, initialization_js
from relay_ownership import OwnershipLedger


EXTENSION = "chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/connect.html"
STATE_JS = "const s=Buffer.constructor('return process')().__epBrowserJob;if(!s)throw Error('owned_state_missing');"
FILE_CHOOSER_MARKER = "- [File chooser]: can be handled by browser_file_upload"
NAVIGATION_REBOUND_NOTE = (
    "Browser job route: reattached to the same owned Chrome tab. "
    "The navigation was not replayed. Take a fresh snapshot."
)
NAVIGATION_REPLACEMENT_JS = (
    STATE_JS + "if(page!==s.connector)throw Error('replacement_connector_not_owned');"
    "return {candidate:await s.navigationReplacement(__EP_EXPECTED_REPLACEMENT__)};"
)
CHOOSER_SNAPSHOT_JS = (
    STATE_JS + "if(page!==s.connector)throw Error('chooser_connector_not_owned');"
    "const snapshot=await s.snapshot();const task=s.task;"
    "if(!task||task===page||!s.created.has(task)||!s.ids.has(task)||task.isClosed())"
    "throw Error('chooser_page_not_owned');"
    "const sym=Object.getOwnPropertySymbols(task).find(k=>typeof task[k]?.modalStates==='function');"
    "if(!sym)throw Error('chooser_state_unavailable');"
    "const states=task[sym].modalStates();"
    "const chooser=states.length===1&&states[0].type==='fileChooser'&&states[0].fileChooser;"
    "if(states.length&&(!chooser||chooser.page()!==task))throw Error('chooser_page_not_owned');"
    "return {snapshot,taskId:s.ids.get(task),taskIndex:page.context().pages().indexOf(task),pending:!!chooser};"
)
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
ALLOCATION_REFUSALS = {
    "bootstrap_busy_retry_not_replay",
    "mcp_version_changed",
    "protocol_incompatible",
    "response_timeout",
    "transport_closed",
    "server_error",
    "client_closed",
    "connector_initialization_failed",
    "connector_identity_unavailable",
    "connector_identity_changed",
    "owned_page_count_mismatch",
    "owned_operation_failed",
    "owned_projection_shape",
    "owned_projection_heading",
    "owned_projection_json",
    "owned_projection_type",
}
FRESH_CONNECTOR_JS = (
    "if(page.context().pages().length!==1||!page.url().startsWith("
    + json.dumps(EXTENSION + "?")
    + "))throw Error('not_fresh_connector');"
)
CONNECTOR_PROBE_JS = (
    "const pages=page.context().pages();const url=page.url();const origin="
    + json.dumps(EXTENSION)
    + ";const matches=url.startsWith(origin+'?');"
    "const observed=matches?'expected_connect_with_query':url===origin?'expected_connect_without_query':"
    "url.startsWith('chrome-extension://')?'other_extension_page':url==='about:blank'?'about_blank':'other_page';"
    "const probe={sdk_page_count:pages.length,observed,expected_url_matches:matches,"
    "sdk_connector_count:pages.filter(p=>p.url().startsWith(origin+'?')).length};"
    "if(pages.length!==1||!matches)return probe;"
    "return {...probe,...await page.evaluate(async()=>{const t=await chrome.tabs.getCurrent();"
    "return {connectorId:t.id,windowId:t.windowId};})};"
)
CONNECTOR_URL_CLASSES = frozenset(
    {
        "expected_connect_with_query",
        "expected_connect_without_query",
        "other_extension_page",
        "about_blank",
        "other_page",
    }
)


def allocation_failure(error):
    """Never persist arbitrary exception text, browser output or launch arguments."""
    if type(error) is Refusal:
        reason = str(error)
        prefix = "owned_operation_failed:"
        if reason in ALLOCATION_REFUSALS:
            return reason
        if reason.startswith(prefix):
            label = reason[len(prefix) :]
            if label in OWNED_ERROR_CODES or label in {item[0] for item in VENDOR_ERROR_CLASSES}:
                return reason
        return "refused"
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, OSError):
        return "os_error"
    if not isinstance(error, Exception):
        return "interrupted"
    return "internal_error"


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
# Fixed reasons the Playwright extension (0.5.0) passes when it closes a relay.
# A reload or crash closes it without any reason, which stays unknown.
CLOSE_REASONS = {
    "All controlled tabs detached": "all_controlled_tabs_detached",
    "User disconnected": "user_disconnect",
}
CLOSE_REASON_LABELS = frozenset(CLOSE_REASONS.values()) | {"connector_closed", "unknown"}
DIAGNOSTIC_VALUES = ("yes", "no", "unknown")
DIAGNOSTIC_UNAVAILABLE = (
    "diagnostics_unavailable:connection_status",
    "diagnostics_unavailable:debugger_targets",
)
DIAGNOSTIC_SKIPS = frozenset(
    ("metadata_missing", "generation_changed", "reconciliation_refused", "sealed_job")
)
DIAGNOSTIC_REFUSALS = frozenset(
    (
        "creation_outcome_unknown_requires_reconciliation",
        "uncheckpointed_page_creation_requires_reconciliation",
        "unbound_owned_pages_require_reconciliation",
        "browser_generation_changed_requires_reconciliation",
        "bootstrap_busy_retry_not_replay",
        "maintenance_window_closure_unobserved",
    )
)
DIAGNOSTIC_CODES = DIAGNOSTIC_REFUSALS | {
    "receipt_unreadable",
    "diagnostic_not_applicable",
    "diagnostic_unavailable",
}


def reported_close_reason(reply):
    """Project only an explicit extension close reason, never arbitrary text."""
    text = "\n".join(b.get("text", "") for b in reply.get("content", []) if isinstance(b, dict))
    # Only the MCP relay's own wording carries a reason; page text cannot pose as one.
    found = re.search(
        r"Extension disconnected(?: before initialization)?: (" + "|".join(CLOSE_REASONS) + ")",
        text,
    )
    return CLOSE_REASONS[found.group(1)] if found else "unknown"


# Playwright Extension 0.6.0 answers getStatus with sessions; 0.5.0 answered
# getConnectionStatus with connections. Both normalize to the 0.5.0 shape.
CONNECTION_STATUS_JS = (
    "const connectionStatus=async()=>{"
    "const n=await chrome.runtime.sendMessage({type:'getStatus'}).catch(()=>null);"
    "if(n&&Array.isArray(n.sessions))return n.sessions.map(c=>({clientName:c.clientName,connectedTabIds:Array.isArray(c.tabIds)?c.tabIds:[]}));"
    "const o=await chrome.runtime.sendMessage({type:'getConnectionStatus'});"
    "if(o&&Array.isArray(o.connections))return o.connections;"
    "throw Error('connection_status_unavailable');};"
)


def adopt_connector_js(client_name):
    """Extension 0.6.0 turns its connect tab into this client's own about:blank tab.

    Navigating that one owned tab back to the extension's connect page, without
    a relay URL or token, restores the privileged connector page the route uses
    for chrome.* census and window ownership. Any other page state is left alone
    for the freshness check to refuse.

    Without a relay URL the vendor page renders "Missing mcpRelayUrl parameter in
    URL.", which reads as a failure to anyone watching. The adopted page's body is
    replaced with a plain status line; the URL, which the ownership checks read,
    is unchanged.
    """
    url = EXTENSION + "?client=" + quote(json.dumps({"name": client_name}), safe="")
    return (
        "const pages=page.context().pages();"
        "if(pages.length!==1||page.url()!=='about:blank')return {adopted:false};"
        "await page.goto(" + json.dumps(url) + ");"
        "try{await page.evaluate((name)=>{document.title='AI browser job connection';"
        "const p=document.createElement('p');"
        "p.style.cssText='font:16px -apple-system,sans-serif;margin:40px;color:#1f2937';"
        "p.textContent='Connected. This tab belongs to the AI browser job '+name+"
        "'. It closes when the job finishes. Nothing is wrong.';"
        "document.body.replaceChildren(p);}," + json.dumps(client_name) + ");}catch{}"
        "return {adopted:true};"
    )


def connection_diagnostics_js(scope, client_name, reason="unknown"):
    """Read extension state without selecting, attaching or changing any tab."""
    return (
        STATE_JS + "return await s.connector.evaluate(async({scope,clientName,reason})=>{"
        "const tabs=await chrome.tabs.query({});"
        "const out={connector_present:tabs.some(t=>t.id===scope.connectorId)?'yes':'no',connection_lists_owned_tabs:'unknown',debugger_attached:Object.fromEntries(scope.tabIds.map(id=>[id,'unknown'])),close_reason:reason};"
        # Only the job's own connector tab closing is derivable from state.
        "if(reason==='unknown'&&out.connector_present==='no')out.close_reason='connector_closed';"
        "out.unavailable=[];"
        # Only this job's exact client and saved tab IDs are read back.
        "try{" + CONNECTION_STATUS_JS + "const connections=await connectionStatus();"
        "out.connection_lists_owned_tabs=connections.some(c=>c.clientName===clientName&&Array.isArray(c.connectedTabIds)&&c.connectedTabIds.some(id=>scope.tabIds.includes(id)))?'yes':'no';"
        "}catch{out.unavailable.push('diagnostics_unavailable:connection_status');}"
        "try{const targets=await chrome.debugger.getTargets();"
        "for(const id of scope.tabIds)out.debugger_attached[id]=targets.some(t=>t.tabId===id&&t.attached)?'yes':'no';"
        "}catch{out.unavailable.push('diagnostics_unavailable:debugger_targets');}"
        "return out;},"
        + json.dumps({"scope": scope, "clientName": client_name, "reason": reason})
        + ");"
    )


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
        error = Refusal("owned_operation_failed" + (":" + label if label else ""))
        error.close_reason = reported_close_reason(reply)
        raise error
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


def failed_cleanup_js(args, remove, diagnose=False):
    """Reconcile a failed job's saved IDs from a fresh maintenance connector.

    Phase one (remove=False) only proves ownership and returns a content-free
    proof digest; phase two must observe that same digest at its start, after
    every asynchronous check and immediately before closing the exact saved
    window. Chrome has no compare-and-remove, so a change after the last read
    is caught only by the post-close inventory, which then refuses success.
    diagnose=True never removes and reports only integer IDs and static codes.
    """
    return (
        STATE_JS
        + "return await s.connector.evaluate(async({old,clientName,connectorOrigin,removalIssued,pendingSince,peers,expectedProof,remove,diagnose})=>{"
        "const exact=(t,name)=>{try{const u=new URL(t.url);return u.protocol+'//'+u.host+u.pathname===connectorOrigin&&JSON.parse(u.searchParams.get('client')).name===name;}catch{return false;}};"
        "const descendantsOf=tabs=>{const d=new Set(old.tabIds);let changed;do{changed=false;for(const t of tabs)if(d.has(t.openerTabId)&&!d.has(t.id)){d.add(t.id);changed=true;}}while(changed);return d;};"
        "const incomplete=tabs=>{const d=descendantsOf(tabs);return tabs.some(t=>(t.windowId===old.windowId||d.has(t.id))&&!old.tabIds.includes(t.id));};"
        "const self=pendingSince===null?null:(await chrome.tabs.getCurrent()).id;"
        + CONNECTION_STATUS_JS
        # Only Extension 0.6.0 sessions can bind a peer; any other or partial
        # shape leaves every newer tab unknown.
        + "const sessions=async()=>{const n=await chrome.runtime.sendMessage({type:'getStatus'}).catch(()=>null);"
        "if(!n||!Array.isArray(n.sessions)||n.sessions.some(c=>!c||typeof c.clientName!=='string'||!Array.isArray(c.tabIds)||c.tabIds.some(i=>!Number.isInteger(i))))return null;return n.sessions;};"
        # An interrupted call may have created a page and then closed it,
        # orphaning a popup it opened elsewhere. Chrome tab IDs only grow
        # within one browser generation, so any surviving tab born after the
        # last proven inventory, other than this maintenance connector, may be
        # that orphan. It is excused only when exactly one live ready peer
        # receipt recorded it as its own birth ID (receipt tabIds) and that
        # peer's exact connector and single session still hold it. Session
        # membership or a client name alone never excuses a tab, and the
        # names are same-user assertions, not a privilege boundary.
        "const newer=tabs=>self===null?[]:tabs.filter(t=>t.id>pendingSince&&t.id!==self&&!old.tabIds.includes(t.id)).map(t=>t.id);"
        "const excused=(id,tabs,list)=>{if(!list)return false;const owners=peers.filter(p=>p.tabIds.includes(id));if(owners.length!==1)return false;const p=owners[0];"
        "const t=tabs.find(x=>x.id===id),c=tabs.find(x=>x.id===p.connectorId);"
        "if(!t||!c||p.windowId===old.windowId||t.windowId!==p.windowId||c.windowId!==p.windowId||!exact(c,p.clientName))return false;"
        "if(t.openerTabId!==undefined&&!p.tabIds.includes(t.openerTabId))return false;"
        "const named=list.filter(x=>x.clientName===p.clientName);if(named.length!==1||!named[0].tabIds.includes(p.connectorId)||!named[0].tabIds.includes(id))return false;"
        "return !list.some(x=>x!==named[0]&&x.tabIds.includes(id));};"
        "const ids=a=>[...a].sort((x,y)=>x-y);"
        "const read=async()=>{const tabs=await chrome.tabs.query({});const list=self===null?null:await sessions();"
        "let status=null;try{status=await connectionStatus();}catch{}"
        "const fresh=newer(tabs);const peerIds=fresh.filter(id=>excused(id,tabs,list));"
        # Connector URLs are not hashed, so each connector's exact() verdict
        # and the derived sets are, otherwise a retargeted connector with
        # unchanged IDs would keep the same digest.
        "const own=tabs.find(t=>t.id===old.connectorId);const bits=[own?exact(own,clientName):null,peers.map(p=>{const c=tabs.find(t=>t.id===p.connectorId);return !!c&&exact(c,p.clientName);})];"
        "const unknownIds=fresh.filter(id=>!peerIds.includes(id));"
        "const key=JSON.stringify([tabs.map(t=>[t.id,t.windowId,t.groupId,t.openerTabId??null]).sort((a,b)=>a[0]-b[0]),list===null?null:list.map(x=>[x.clientName,ids(x.tabIds)]).sort(),status===null?null:status.map(x=>[x.clientName,ids(x.connectedTabIds||[])]).sort(),bits,ids(peerIds),ids(unknownIds)]);"
        "const proof=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(key))),b=>b.toString(16).padStart(2,'0')).join('');"
        "return {tabs,status,peerIds,unknownIds,proof};};"
        "const r=await read();"
        "const same=(a,b)=>JSON.stringify(ids(a))===JSON.stringify(ids(b));"
        "const stable=async()=>{const n=await read();if(n.proof!==r.proof||!same(n.peerIds,r.peerIds)||!same(n.unknownIds,r.unknownIds))throw Error('cleanup_proof_changed');};"
        "const verify=async(check)=>{const before=r.tabs;"
        # Target extras and descendants block before any peer exemption.
        "if(incomplete(before))throw Error('uncheckpointed_page_arrival');"
        "const live=before.filter(t=>old.tabIds.includes(t.id));"
        # Every saved tab gone is explained only by a removal this route
        # already issued. Otherwise a popup may have escaped and lost its
        # opener link when its parent closed.
        "if(!live.length){if(removalIssued&&!before.some(t=>t.windowId===old.windowId)){if(r.unknownIds.length)throw Error('uncheckpointed_page_arrival');return {alreadyClosed:true};}throw Error('saved_owned_tab_missing');}"
        # The connector is an extension page that never opens popups, so its
        # absence alone cannot hide an unrecorded descendant. A missing
        # working page can, so that still refuses.
        "if(old.tabIds.some(id=>id!==old.connectorId&&!live.some(t=>t.id===id)))throw Error('saved_owned_tab_missing');"
        # The extension intentionally ungroups its tabs after disconnect.
        # When the connector survives, anchor to its exact client identity.
        "const connector=live.find(t=>t.id===old.connectorId);"
        "if(connector&&!exact(connector,clientName))throw Error('connector_identity_changed');"
        "if(r.status===null)throw Error('connection_status_unavailable');"
        "const targets=await chrome.debugger.getTargets();await check();"
        "for(const t of live){if(t.windowId!==old.windowId||(t.groupId!==old.groupId&&t.groupId!==-1)||targets.some(x=>x.tabId===t.id&&x.attached)||r.status.some(c=>(c.connectedTabIds||[]).includes(t.id)))throw Error('ownership_changed');"
        "if(t.groupId!==-1){const g=await chrome.tabGroups.get(t.groupId);await check();if(g.title!==old.groupTitle)throw Error('group_identity_changed');}}"
        "if(r.unknownIds.length)throw Error('uncheckpointed_page_arrival');"
        "return {live,connector};};"
        "if(diagnose){let code=null;try{await verify(async()=>{});}catch(e){code=e.message;}"
        "const d=descendantsOf(r.tabs);const liveIds=new Set(r.tabs.map(t=>t.id));"
        "return {diagnostic:true,ready:code===null,code,"
        "targetExtraIds:ids(r.tabs.filter(t=>t.windowId===old.windowId&&!old.tabIds.includes(t.id)).map(t=>t.id)),"
        "descendantIds:ids(r.tabs.filter(t=>d.has(t.id)&&t.windowId!==old.windowId&&!old.tabIds.includes(t.id)).map(t=>t.id)),"
        "missingSavedIds:ids(old.tabIds.filter(id=>!liveIds.has(id))),peerIds:ids(r.peerIds),unknownIds:ids(r.unknownIds)};}"
        # A dry-run or phase-one digest is never authority by itself; phase
        # two must still observe exactly the same inventory.
        # In the removing phase every refusal before windows.remove is returned,
        # not thrown, so the caller knows no removal was issued and can restore
        # its issued-removal flag. Anything thrown is after removal or unknown.
        "let v;try{if(expectedProof!==null&&r.proof!==expectedProof)throw Error('cleanup_proof_changed');"
        "v=await verify(stable);if(remove&&!v.alreadyClosed)await stable();}"
        "catch(e){if(remove)return {refused:String(e&&e.message)};throw e;}"
        "if(v.alreadyClosed)return {closed:true,count:0,alreadyClosed:true};"
        "if(!remove)return {ready:true,count:v.live.length,connectorMissing:!v.connector,proof:r.proof,peerIds:ids(r.peerIds)};"
        "await chrome.windows.remove(old.windowId);"
        "const beforeIds=new Set(r.tabs.map(t=>t.id));"
        # Chrome can still list a removed window's tabs for a moment.
        "let after;for(let i=0;i<20;i++){after=await chrome.tabs.query({});if(!after.some(t=>old.tabIds.includes(t.id)||t.windowId===old.windowId))break;await new Promise(r=>setTimeout(r,100));}"
        # A tab that was not saved and vanished with the window was foreign;
        # that closure cannot be undone, but it must never read as success.
        "if(after.some(t=>old.tabIds.includes(t.id)||t.windowId===old.windowId||!beforeIds.has(t.id))||incomplete(after)||r.tabs.some(t=>!old.tabIds.includes(t.id)&&!after.some(a=>a.id===t.id)))throw Error('owned_cleanup_inventory_uncertain');"
        "return {closed:true,count:v.live.length,connectorMissing:!v.connector};},"
        + json.dumps(
            {
                "pendingSince": None,
                "peers": [],
                "expectedProof": None,
                **args,
                "remove": remove,
                "diagnose": diagnose,
            }
        )
        + ");"
    )


WINDOW_IDS_JS = (
    STATE_JS
    + "return {ids:await s.connector.evaluate(async()=>(await chrome.windows.getAll()).map(w=>w.id))};"
)


def window_ids(client):
    return code(client, WINDOW_IDS_JS).get("ids")


def removal_issued(job):
    # Receipts written before the flag was saved on the live path recorded the
    # same route-issued window removal only as this timing stage.
    return bool(job.get("window_removal_issued")) or any(
        stage[0] == "live_window_scheduled"
        for record in job.get("timings", [])
        for stage in record.get("stages", [])
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


PEER_SOURCE_LIMIT = 64
# The destructive cleanup call holds receipts.lock, which every peer's
# checkpoint also takes. Both waits are bounded so a stuck transport stalls
# peers for at most DESTRUCTIVE_CALL_TIMEOUT, and a busy lock skips cleanup.
RECEIPTS_LOCK_TIMEOUT = 10
DESTRUCTIVE_CALL_TIMEOUT = 20
PRE_REMOVAL_REFUSALS = frozenset(
    (
        "cleanup_proof_changed",
        "uncheckpointed_page_arrival",
        "saved_owned_tab_missing",
        "connector_identity_changed",
        "connection_status_unavailable",
        "ownership_changed",
        "group_identity_changed",
    )
)
HELD_RECEIPTS = threading.local()
# Set while finish or recover runs, so every receipt save on that path waits a
# bounded time. After one wait has timed out, later saves on the same path only
# try once, so the caller gets its refusal after about one bound, not several.
BOUNDED_SAVES = threading.local()


@contextmanager
def bounded_saves():
    previous = getattr(BOUNDED_SAVES, "state", None)
    BOUNDED_SAVES.state = previous or {"busy": False}
    try:
        yield
    finally:
        BOUNDED_SAVES.state = previous


def release_lock(fd):
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


@contextmanager
def bounded_receipts_lock(root, timeout=None):
    """receipts.lock with a bounded wait; this thread's own saves reuse it."""
    state = getattr(BOUNDED_SAVES, "state", None)
    if timeout is None:
        timeout = 0 if state and state["busy"] else RECEIPTS_LOCK_TIMEOUT
    fd = os.open(Path(root) / "receipts.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    if state is not None:
                        state["busy"] = True
                    raise Refusal("receipts_lock_busy") from None
                time.sleep(0.05)
    except BaseException:
        os.close(fd)
        raise
    outer = getattr(HELD_RECEIPTS, "root", None)
    HELD_RECEIPTS.root = str(root)
    try:
        yield
    finally:
        HELD_RECEIPTS.root = outer
        try:
            release_lock(fd)
        except OSError:
            # The removal outcome may be fine, but an unreleased lock is not
            # a state cleanup may report as settled.
            raise Refusal("receipts_lock_release_failed") from None


def bounded_code(client, body, timeout):
    previous = getattr(client, "timeout", None)
    if type(previous) not in (int, float):
        return code(client, body)
    client.timeout = min(previous, timeout)
    try:
        return code(client, body)
    finally:
        client.timeout = previous


DIAGNOSTIC_ID_LIMIT = 64
DIAGNOSTIC_ID_FIELDS = (
    "targetExtraIds",
    "descendantIds",
    "missingSavedIds",
    "peerIds",
    "unknownIds",
)


def peer_proof_source(row, owner, generation, job_id):
    """A peer receipt can excuse only its own birth tab IDs, and only while live.

    Anything short of a strictly shaped, ready, not pending, same-generation
    receipt with an active owner returns None, so its tabs stay unknown.
    """
    if not (isinstance(row, dict) and isinstance(owner, dict)):
        return None
    meta = row.get("metadata")
    name = row.get("client_name")
    if not (
        row.get("job_id") == job_id
        and owner.get("job_id") == job_id
        and owner.get("state") == "active"
        and row.get("status") == "ready"
        and row.get("ownership_pending") is False
        and row.get("sealed") is False
        and not row.get("relay_mode")
        and row.get("window_disposition") is None
        and row.get("generation") == generation
        and isinstance(name, str)
        and 0 < len(name) <= 512
        and isinstance(meta, dict)
        and meta.get("unboundOwnedPages") == 0
    ):
        return None
    connector, window, tabs = meta.get("connectorId"), meta.get("windowId"), meta.get("tabIds")
    if not (
        type(connector) is int
        and type(window) is int
        and connector >= 0
        and window >= 0
        and isinstance(tabs, list)
        and 0 < len(tabs) <= 256
        and all(type(t) is int and t >= 0 for t in tabs)
        and len(set(tabs)) == len(tabs)
        and connector in tabs
    ):
        return None
    return {"connectorId": connector, "windowId": window, "tabIds": tabs, "clientName": name}


def diagnostic_projection(value):
    """Whitelist integer IDs and static codes; drop everything else."""
    out = {"authority": False, "observer": "temporary_maintenance_connector"}
    code_value = value.get("code") if isinstance(value, dict) else None
    out["ready"] = isinstance(value, dict) and value.get("ready") is True and code_value is None
    if out["ready"]:
        out["code"] = None
    elif isinstance(code_value, str) and (
        code_value in OWNED_ERROR_CODES or code_value in DIAGNOSTIC_CODES
    ):
        out["code"] = code_value
    else:
        out["code"] = "diagnostic_unclassified"
    for field in DIAGNOSTIC_ID_FIELDS:
        ids = value.get(field) if isinstance(value, dict) else None
        if not (isinstance(ids, list) and all(type(i) is int and i >= 0 for i in ids)):
            out[field] = None
            continue
        out[field] = ids[:DIAGNOSTIC_ID_LIMIT]
        if len(ids) > DIAGNOSTIC_ID_LIMIT:
            out[field + "Truncated"] = True
    return out


class Route:
    def __init__(self, config, control=True):
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
        self.control_socket = self.control_listener = None
        if not control:
            # The read-only diagnostic owns no job, so it serves no finish
            # channel and leaves no socket in state_dir.
            return
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
        if listener and self.control_socket:
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

    def client(self, name, relay_socket=None):
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
        if relay_socket:
            env["EP_BROWSER_RELAY_SOCKET"] = str(relay_socket)
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
        # A receipt loaded from disk (lifecycle sweep fallback) keeps the socket of
        # the facade that owns the job, not this short-lived route's own socket.
        row["control_socket"] = job.get("control_socket") or getattr(self, "control_socket", None)
        if job.get("connection_diagnostics"):
            row["connection_diagnostics"] = job["connection_diagnostics"]
        if job.get("allocation_failure"):
            row["allocation_failure"] = job["allocation_failure"]
        if job.get("initial_connector"):
            row["initial_connector"] = job["initial_connector"]
        if job.get("connector_probe"):
            row["connector_probe"] = job["connector_probe"]
        if job.get("window_disposition"):
            row["window_disposition"] = job["window_disposition"]
        if job.get("window_removal_issued"):
            row["window_removal_issued"] = True
        if job.get("relay_mode"):
            row["relay_mode"] = True
            row["relay_pid"] = job.get("relay_pid")
            row["relay_cleanup"] = job.get("relay_cleanup", {})
        path = self.root / (job["job_id"] + ".json")
        # A stale facade never reopens a receipt another route already settled.
        # Check and replace under one host-wide lock, so a sweep or reconciliation
        # that settles the receipt between the two can never be overwritten.
        if getattr(HELD_RECEIPTS, "root", None) == str(self.root):
            guard = contextlib.nullcontext()
        elif getattr(BOUNDED_SAVES, "state", None) is not None:
            guard = bounded_receipts_lock(self.root)
        else:
            guard = ledger_lock(self.root, "receipts.lock")
        with guard:
            if self.settled_elsewhere(job):
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

    def failure_checkpoint(self, job, status=None):
        """Record a failure without waiting again on a peer-held receipts.lock.

        When the lock stays busy the receipt keeps its last durable state, which
        never claims more than happened, and the in-memory job is saved on the
        next attempt."""
        try:
            self.checkpoint(job, status)
        except Refusal as error:
            if str(error) != "receipts_lock_busy":
                raise

    def checkpoint(self, job, status=None):
        if status:
            job["status"] = status
        if status == "finished":
            job["receipt_owned"] = True
        job["updated"] = time.time()
        self.save(job)

    def refuse_before_forwarding(self, job, sealed, reason, message):
        # Only route-defined values go in the receipt, never the supplied tool
        # name, arguments or exception text. No operation was forwarded.
        job.setdefault("timings", []).append(
            {
                "tool": "pre_forward",
                "sealed": sealed,
                "stages": [["received", round(time.time(), 3)]],
            }
        )
        del job["timings"][:-TIMING_RECORDS]
        self.mark(job, "refused:" + reason)
        with bounded_saves():
            self.failure_checkpoint(job)
        return result({"code": reason, "error": message}, True)

    def metadata(self, client, strict=True):
        return code(client, STATE_JS + "return await s.snapshot(" + json.dumps(strict) + ");")

    @contextmanager
    def maintenance_connector(self):
        name = "EP cleanup " + uuid.uuid4().hex
        client = self.client(name)
        try:
            code(client, adopt_connector_js(name))
            code(
                client,
                "const p=Buffer.constructor('return process')();if(page.context().pages().length!==1||!page.url().startsWith("
                + json.dumps(EXTENSION + "?")
                + "))throw Error('not_own_connector');p.__epBrowserJob={connector:page,task:null};return {ready:true};",
            )
            yield client
        finally:
            try:
                # This connector is its window's only tab, so nothing else can
                # census its own removal. Its page close event is the proof.
                closed = code(
                    client,
                    STATE_JS + "const gone=new Promise(r=>s.connector.once('close',()=>r(true)));"
                    "const windowId=await s.connector.evaluate(async()=>{const t=await chrome.tabs.getCurrent();const tabs=await chrome.tabs.query({windowId:t.windowId});if(tabs.length!==1||tabs[0].id!==t.id)throw Error('maintenance_window_not_exclusive');setTimeout(()=>chrome.windows.remove(t.windowId),250);return t.windowId;});"
                    "const seen=await Promise.race([gone,new Promise(r=>setTimeout(()=>r(false),5000))]);"
                    "return {windowId,closed:seen};",
                )
                if closed.get("closed") is not True:
                    raise Refusal("maintenance_window_closure_unobserved")
            finally:
                client.close()

    def capture_connection_diagnostics(self, job, stage, client=None, reason="unknown", skip=None):
        """Record fixed-label connection state once per phase without changing the outcome.

        The first route-side failure and failed-job reconciliation each keep one
        snapshot. Collection is read-only and never selects, attaches or closes a tab.
        """
        key = "dispose_failed" if stage in ("dispose_failed", "reconcile") else "first_failure"
        captures = job.setdefault("connection_diagnostics", {})
        if key in captures:
            return
        if reason not in CLOSE_REASON_LABELS:
            reason = "unknown"
        if reason == "unknown":
            reason = captures.get("first_failure", {}).get("close_reason", "unknown")
        old = job.get("metadata") or {}
        tab_ids = [i for i in old.get("tabIds") or [] if type(i) is int]
        snapshot = {
            "stage": stage,
            "at": round(time.time(), 3),
            "connector_present": "unknown",
            "connection_lists_owned_tabs": "unknown",
            "debugger_attached": {str(i): "unknown" for i in tab_ids},
            "close_reason": reason,
            "unavailable": [],
        }
        captures[key] = snapshot
        try:
            if skip:
                raise Refusal(skip)
            if not tab_ids or type(old.get("connectorId")) is not int:
                raise Refusal("metadata_missing")
            scope = {"connectorId": old["connectorId"], "tabIds": tab_ids}

            def collect(connector):
                value = code(
                    connector, connection_diagnostics_js(scope, job["client_name"], reason)
                )
                for field in ("connector_present", "connection_lists_owned_tabs"):
                    if value.get(field) in DIAGNOSTIC_VALUES:
                        snapshot[field] = value[field]
                seen = value.get("debugger_attached")
                for tab_id in snapshot["debugger_attached"]:
                    if isinstance(seen, dict) and seen.get(tab_id) in DIAGNOSTIC_VALUES:
                        snapshot["debugger_attached"][tab_id] = seen[tab_id]
                if value.get("close_reason") in CLOSE_REASON_LABELS:
                    snapshot["close_reason"] = value["close_reason"]
                missing = value.get("unavailable")
                snapshot["unavailable"] = [
                    c for c in DIAGNOSTIC_UNAVAILABLE if isinstance(missing, list) and c in missing
                ]

            if client is not None:
                collect(client)
            else:
                if self.preflight() != job["generation"]:
                    raise Refusal("generation_changed")
                with self.bootstrap(), self.maintenance_connector() as connector:
                    collect(connector)
        except Exception as error:
            failed = (
                str(error)
                if type(error) is Refusal and str(error) in DIAGNOSTIC_SKIPS
                else "collection_failed"
            )
            snapshot["unavailable"] = ["diagnostics_unavailable:" + failed]

    def connect(self, job, working=True):
        relay = getattr(self, "config", {}).get("relay_v2", {})
        if relay.get("enabled") is True and self.relay_version() == (0, 6):
            return self.connect_relay(job, working)
        job["allocation_stage"] = "launcher_handshake"
        client = self.client(job["client_name"])
        job["client"] = client
        job["allocation_stage"] = "connector_identity"
        code(client, adopt_connector_js(job["client_name"]))
        observed = code(client, CONNECTOR_PROBE_JS)
        count = observed.get("sdk_page_count")
        connectors = observed.get("sdk_connector_count")
        url_class = observed.get("observed")
        matches = observed.get("expected_url_matches")
        if not (
            type(count) is int
            and type(connectors) is int
            and 0 <= connectors <= count
            and isinstance(url_class, str)
            and url_class in CONNECTOR_URL_CLASSES
            and type(matches) is bool
            and matches == (url_class == "expected_connect_with_query")
        ):
            raise Refusal("connector_identity_unavailable")
        job["connector_probe"] = {
            "sdk_page_count": count,
            "sdk_connector_count": connectors,
            "expected_connect_url": EXTENSION + "?[redacted]",
            "observed_url_class": url_class,
            "expected_url_matches": matches,
        }
        if count != 1 or not matches:
            raise Refusal("owned_operation_failed:not_fresh_connector")
        fields = ("connectorId", "windowId")
        if not all(type(observed.get(k)) is int and observed[k] >= 0 for k in fields):
            raise Refusal("connector_identity_unavailable")
        # This pre-isolation observation cannot authorize cleanup. Only the
        # existing verified metadata path supplies cleanup IDs.
        job["initial_connector"] = {k: observed[k] for k in fields}
        self.checkpoint(job)
        job["allocation_stage"] = "connector_isolation"
        # State is in this private Node process, not the ephemeral VM globals.
        initialized = code(
            client,
            OWNED_SOURCE
            + "const p=Buffer.constructor('return process')();if(p.__epBrowserJob)throw Error('already_attempted');"
            + FRESH_CONNECTOR_JS
            + "p.__epBrowserJob=await newOwnedState(page);const s=p.__epBrowserJob;return {ready:true,ownership:{...s.initial,tabIds:[...s.ids.values()],unboundOwnedPages:0}};",
        )
        if initialized.get("ready") is not True:
            raise Refusal("connector_initialization_failed")
        if initialized.get("ownership", {}).get("connectorId") != observed["connectorId"]:
            raise Refusal("connector_identity_changed")
        job["metadata"] = initialized["ownership"]
        self.checkpoint(job, "connecting")
        job["allocation_stage"] = "connector_verification"
        self.verify_connection(job)
        if working:
            job["allocation_stage"] = "working_page"
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

    def relay_version(self):
        profile = Path.home() / "Library/Application Support/Google/Chrome" / self.config["profile"]
        extension = EXTENSION.split("/")[2]
        try:
            prefs = json.loads((profile / "Secure Preferences").read_text())
            entry = prefs["extensions"]["settings"][extension]
            version = entry["manifest"]["version"]
            expected = f"{extension}/{version}_0"
            manifest = json.loads((profile / "Extensions" / expected / "manifest.json").read_text())
            if (
                entry.get("disable_reasons") != []
                or entry["path"] != expected
                or manifest["version"] != version
                or not re.fullmatch(r"0\.[56]\.\d+", version)
            ):
                raise ValueError()
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise Refusal("relay_extension_version_unverified") from error
        return tuple(map(int, version.split(".")[:2]))

    def aqua_cleanup(self):
        config = self.config["relay_v2"]
        return AquaCleanup(config["helper"], config["helper_sha256"], self.root)

    def connect_relay(self, job, working):
        # Prove the independent cleanup channel before creating a tab.
        self.aqua_cleanup().inventory()
        job["relay_mode"] = True
        broker = RelayBroker(self.root, self.config["relay_v2"], job["generation"], job["job_id"])
        job["relay_broker"] = broker
        job["relay_pid"] = broker.proc.pid
        self.checkpoint(job)
        client = self.client(job["client_name"], broker.socket)
        job["client"] = client
        job["allocation_stage"] = "connector_identity"
        observed = code(client, initialization_js(broker.socket))
        status = broker.rpc("status")
        if not status.get("initialized") or len(status.get("claims", [])) != 1:
            raise Refusal("connector_identity_unavailable")
        claim = status["claims"][0]
        if (
            observed["connectorId"] != claim["tabId"]
            or observed["windowId"] != claim["windowId"]
            or claim["urlClass"] != "blank"
        ):
            raise Refusal("connector_identity_changed")
        observed.pop("workingPage", None)
        job["metadata"] = observed
        self.checkpoint(job, "connecting")
        if working:
            job["allocation_stage"] = "working_page"
            job["ownership_pending"] = True
            self.checkpoint(job)
            code(client, STATE_JS + "s.task=await s.create();return {created:!s.task.isClosed()};")
            job["metadata"] = self.verify_connection(job)
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
            "allocation_stage": "bootstrap_lock",
            "lock": threading.RLock(),
        }
        with self.lock:
            self.jobs[job_id] = job
        with job["lock"]:
            try:
                with self.bootstrap():
                    job["allocation_stage"] = "profile_preflight"
                    job["generation"] = self.preflight()
                    self.checkpoint(job)
                    if owner_session_id is not None:
                        job["allocation_stage"] = "session_binding"
                        bind(self.root, job_id, owner_session_id)
                    job["allocation_stage"] = "launcher_handshake"
                    self.connect(job)
                return result(self.summary(job))
            except BaseException as error:
                job["allocation_failure"] = {
                    "stage": job["allocation_stage"],
                    "class": allocation_failure(error),
                }
                self.checkpoint(job, "failed")
                if isinstance(error, Exception):
                    self.capture_connection_diagnostics(
                        job, "allocation", reason=getattr(error, "close_reason", "unknown")
                    )
                self.checkpoint(job, "failed")
                # Caller gets the handle even if allocation failed. Never hide
                # an uncertain creation behind an automatic second attempt.
                return result(
                    {
                        **self.summary(job),
                        "allocation_failure": job["allocation_failure"],
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
            STATE_JS + "if(!s.task||s.task.isClosed())throw Error('owned_page_closed');"
            "const pages=s.connector.context().pages();"
            "return {index:pages.indexOf(s.task),connectorIndex:pages.indexOf(s.connector)};",
        )
        self.mark(job, "prime_own_index")
        job["chooser_connector_index"] = own.get("connectorIndex")
        self.select_private_tab(job, own["index"])
        self.mark(job, "prime_select")

    @staticmethod
    def select_private_tab(job, index):
        if type(index) is not int or index < 0:
            raise Refusal("owned_page_selection_failed")
        reply = job["client"].call(
            "tools/call",
            {"name": "browser_tabs", "arguments": {"action": "select", "index": index}},
        )
        if reply.get("isError"):
            raise Refusal("owned_page_selection_failed")

    def verify_connection(self, job):
        return self.verify_observed(job, self.metadata(job["client"]))

    def recover_navigation_page(self, job):
        """Bind only a Page the existing extension connection already reattached."""
        self.select_private_tab(job, job.get("chooser_connector_index"))

        def inspect(expected):
            return code(
                job["client"],
                NAVIGATION_REPLACEMENT_JS.replace(
                    "__EP_EXPECTED_REPLACEMENT__", json.dumps(expected)
                ),
            )["candidate"]

        candidate = inspect(None)
        if not candidate:
            return False
        origin = urlsplit(candidate["origin"])
        if (
            origin.scheme != "https"
            or not origin.hostname
            or origin.username is not None
            or origin.password is not None
            or any((origin.path, origin.query, origin.fragment))
        ):
            raise Refusal("owned_replacement_unproven")
        denied, _ = self.policy("browser_navigate", {"url": candidate["origin"] + "/"})
        if denied:
            raise Refusal("owned_replacement_policy_denied")
        if self.preflight() != job["generation"]:
            raise Refusal("browser_generation_changed_no_replay")
        if inspect(candidate) != candidate:
            raise Refusal("owned_replacement_changed")
        self.mark(job, "owned_navigation_page_rebound")
        return True

    @staticmethod
    def verify_observed(job, observed):
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

    def check_file_chooser(self, job):
        """Use the connector for strict checks while the task is modal-gated."""
        self.select_private_tab(job, job.get("chooser_connector_index"))
        state = code(job["client"], CHOOSER_SNAPSHOT_JS)
        observed = self.verify_observed(job, state["snapshot"])
        task = state["taskId"]
        old_ids = job["metadata"]["tabIds"]
        if (
            observed["tabIds"] != old_ids
            or task not in old_ids
            or task == observed["connectorId"]
            or job.get("chooser_task_id", task) != task
        ):
            raise Refusal("chooser_page_not_owned")
        return observed, state

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
        if job.get("relay_mode"):
            return self.dispose_relay_live(job)
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
        # Saved first so failed-job reconciliation can attribute a vanished
        # window to this route if the close below is interrupted.
        job["window_removal_issued"] = True
        self.checkpoint(job)
        closing = code(client, STATE_JS + "return await s.closeWindow();")
        self.mark(job, "live_window_scheduled")
        time.sleep(0.4)
        if not closing.get("shared"):
            with self.maintenance_connector() as census:
                verify_window_closed(job["metadata"]["windowId"], lambda: window_ids(census))
        job["window_disposition"] = "preserved_shared" if closing.get("shared") else "closed"
        client.close()
        job["ownership_pending"] = False

    def dispose_failed(self, job, reason="unknown"):
        """Use a fresh own connector to reconcile exact unclaimed old IDs only."""
        if job.get("relay_mode"):
            return self.dispose_relay_failed(job)
        if job["client"] and not job["client"].closed:
            # Capture any page created just before an interrupted response while
            # this exact live connection can still prove its scope.
            try:
                self.dispose_live(job)
                return
            except Exception as error:
                self.mark(job, "live_" + failure_stage(error))
                reason = getattr(error, "close_reason", reason)
            job["client"].close()
        old = job["metadata"]
        try:
            pending_since = self.reconcile_scope(job)
        except Exception:
            # Reconciliation opens no connector here, so neither do diagnostics.
            self.capture_connection_diagnostics(
                job, "dispose_failed", reason=reason, skip="reconciliation_refused"
            )
            raise
        # Never save the temporary connection over the original receipt.
        with self.maintenance_connector() as client:
            self.capture_connection_diagnostics(job, "reconcile", client=client, reason=reason)
            self.checkpoint(job)
            peers, digests = self.peer_sources(job, pending_since)
            args = {
                "old": old,
                "clientName": job["client_name"],
                "connectorOrigin": EXTENSION,
                "removalIssued": removal_issued(job),
                "pendingSince": pending_since,
                "peers": peers,
            }
            outcome = code(client, failed_cleanup_js(args, remove=False))
            self.mark(job, "reconcile_proven")
            if outcome.get("ready") is True:
                proof = outcome.get("proof")
                excused = outcome.get("peerIds")
                if not (
                    isinstance(proof, str)
                    and re.fullmatch(r"[0-9a-f]{64}", proof)
                    and isinstance(excused, list)
                    and all(type(i) is int for i in excused)
                ):
                    raise Refusal("failed_cleanup_uncertain")
                used = sorted(
                    i for i, p in enumerate(peers) if any(t in p["tabIds"] for t in excused)
                )
                if self.preflight() != job["generation"]:
                    raise Refusal("browser_generation_changed_requires_reconciliation")
                # Peers checkpoint under this lock, so the receipts that excuse
                # a tab cannot change while the destructive phase runs.
                with bounded_receipts_lock(self.root):
                    again, now = self.peer_sources(job, pending_since)
                    if again != peers or any(now[i] != digests[i] for i in used):
                        raise Refusal("peer_proof_changed")
                    # Recorded just before the removing call so a retry after an
                    # interrupted close can prove the vanished window was this
                    # route's own removal. A refusal the browser code reports
                    # before windows.remove restores the earlier value.
                    issued_before = job.get("window_removal_issued")
                    job["window_removal_issued"] = True
                    self.checkpoint(job)
                    outcome = bounded_code(
                        client,
                        failed_cleanup_js({**args, "expectedProof": proof}, remove=True),
                        DESTRUCTIVE_CALL_TIMEOUT,
                    )
                    if "refused" in outcome:
                        job["window_removal_issued"] = issued_before
                        if not issued_before:
                            job.pop("window_removal_issued", None)
                        self.checkpoint(job)
                        refused = outcome["refused"]
                        raise Refusal(
                            refused
                            if refused in PRE_REMOVAL_REFUSALS
                            else "cleanup_precheck_failed"
                        )
                    again, now = self.peer_sources(job, pending_since)
                    if outcome.get("closed") is True and (
                        again != peers or any(now[i] != digests[i] for i in used)
                    ):
                        raise Refusal("failed_cleanup_uncertain")
                if self.preflight() != job["generation"]:
                    raise Refusal("failed_cleanup_uncertain")
            if outcome.get("closed") is not True:
                raise Refusal("failed_cleanup_uncertain")
            verify_window_closed(old["windowId"], lambda: window_ids(client))
            job["window_disposition"] = "closed"
            job["ownership_pending"] = False

    def reconcile_scope(self, job):
        """Static preconditions shared by cleanup and the read-only diagnostic."""
        old = job.get("metadata")
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
        return pending_since

    def peer_sources(self, job, pending_since):
        """Live ready peer receipts in this state_dir and generation, with digests.

        Unreadable or malformed receipts are skipped as sources, which leaves
        their tabs unknown rather than excused. Too many sources excuse nothing.
        """
        if pending_since is None:
            return [], []
        peers, digests = [], []
        for path in sorted(self.root.glob("*.json")):
            peer_id = path.stem
            if peer_id == job["job_id"] or not re.fullmatch(r"[0-9a-f]{32}", peer_id):
                continue
            try:
                raw = path.read_bytes()
                owner_raw = owner_path(self.root, peer_id).read_bytes()
                source = peer_proof_source(
                    json.loads(raw), json.loads(owner_raw), job["generation"], peer_id
                )
            except (OSError, ValueError):
                continue
            if source:
                peers.append(source)
                digests.append(hashlib.sha256(raw + b"\0" + owner_raw).hexdigest())
        if len(peers) > PEER_SOURCE_LIMIT:
            return [], []
        return peers, digests

    def diagnose_failed(self, job_id):
        """Read-only proof inventory for a saved failed receipt.

        Never calls dispose_failed, never writes any receipt or owner row and
        never removes a tab or window. The only browser footprint is the
        temporary maintenance connector window, whose closure is verified.
        Constructed with control=False, it binds no control socket and starts
        no listener thread. It takes the shared bootstrap lock while observing.
        The result is not authority for a later close.
        """
        if not isinstance(job_id, str) or not re.fullmatch(r"[0-9a-f]{32}", job_id):
            raise Refusal("valid_job_id_required")
        try:
            row = json.loads((self.root / (job_id + ".json")).read_text())
            if not isinstance(row, dict) or row.get("job_id") != job_id:
                raise ValueError()
        except (OSError, ValueError):
            return diagnostic_projection({"code": "receipt_unreadable"})
        if row.get("status") != "failed" or row.get("relay_mode"):
            return diagnostic_projection({"code": "diagnostic_not_applicable"})
        job = {
            "job_id": job_id,
            "metadata": row.get("metadata"),
            "ownership_pending": row.get("ownership_pending"),
            "generation": row.get("generation"),
        }
        try:
            pending_since = self.reconcile_scope(job)
            peers, _ = self.peer_sources(job, pending_since)
            args = {
                "old": job["metadata"],
                "clientName": row.get("client_name"),
                "connectorOrigin": EXTENSION,
                "removalIssued": removal_issued(row),
                "pendingSince": pending_since,
                "peers": peers,
            }
            with self.bootstrap(), self.maintenance_connector() as client:
                value = code(client, failed_cleanup_js(args, remove=False, diagnose=True))
            if self.preflight() != job["generation"]:
                raise Refusal("browser_generation_changed_requires_reconciliation")
        except Refusal as error:
            reason = str(error)
            return diagnostic_projection(
                {"code": reason if reason in DIAGNOSTIC_REFUSALS else "diagnostic_unavailable"}
            )
        except Exception:
            return diagnostic_projection({"code": "diagnostic_unavailable"})
        return diagnostic_projection(value)

    def dispose_relay_live(self, job):
        if self.preflight() != job["generation"]:
            raise Refusal("browser_generation_changed_no_cleanup")
        broker = job["relay_broker"]
        # The relay proves current ownership at close; the separate census
        # confirms that only our recorded tabs disappeared.
        code(job["client"], STATE_JS + "await s.closeCreated();return {closed:true};")
        for claim in broker.rpc("status")["claims"]:
            broker.rpc("close", tabId=claim["tabId"])
        self.verify_relay_absent(job)
        broker.stop()
        job["client"].close()
        job["ownership_pending"] = False
        job["window_disposition"] = "owned_tabs_closed"

    def verify_relay_absent(self, job):
        generation = generation_key(job["generation"])
        ledger = OwnershipLedger(self.root / "relay-claims.sqlite3")
        claims = ledger.job_claims(generation, job["job_id"])
        seen = {row["tabId"] for row in self.aqua_cleanup().inventory()}
        if not claims or any(c["state"] != "closed" or c["tabId"] in seen for c in claims):
            raise Refusal("relay_exact_cleanup_unverified")

    def dispose_relay_failed(self, job):
        if self.preflight() != job["generation"]:
            raise Refusal("browser_generation_changed_no_cleanup")
        broker = job.get("relay_broker")
        if broker:
            broker.stop()
        if job.get("client") and not job["client"].closed:
            job["client"].close()
        pid = job.get("relay_pid")
        if type(pid) is not int or pid <= 1:
            raise Refusal("relay_process_identity_unavailable")
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise Refusal("relay_process_still_present")
        generation = generation_key(job["generation"])
        ledger = OwnershipLedger(self.root / "relay-claims.sqlite3")
        claims = ledger.job_claims(generation, job["job_id"])
        if not claims:
            raise Refusal("creation_outcome_unknown_requires_reconciliation")
        cleanup = self.aqua_cleanup()
        for claim in claims:
            ledger.mark_released(claim)
            outcome = ledger.recover(
                claim, lambda: generation_key(self.preflight()), cleanup.inventory, cleanup.close
            )
            job.setdefault("relay_cleanup", {})[str(claim["tabId"])] = outcome
            self.checkpoint(job)
        self.verify_relay_absent(job)
        job["window_disposition"] = "owned_tabs_closed"
        job["ownership_pending"] = False

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
        with bounded_saves():
            try:
                with self.bootstrap():
                    if job["status"] == "ready" and job["client"] and not job["client"].closed:
                        try:
                            self.dispose_live(job)
                        except Exception as error:
                            self.mark(job, "live_" + failure_stage(error))
                            self.failure_checkpoint(job, "failed")
                            self.dispose_failed(job, getattr(error, "close_reason", "unknown"))
                    else:
                        self.dispose_failed(job)
            except Exception as error:
                # The caller sees one generic refusal; the receipt keeps the static step.
                self.mark(job, failure_stage(error))
                self.failure_checkpoint(job)
                raise
            self.mark(job, "finished")
            self.checkpoint(job, "finished")
        return result(self.summary(job))

    def recover(self, job):
        refused = (
            "Recovery refused or incomplete; preserve the exact receipt and do not replay work."
        )
        try:
            self.finish(job)
        except Exception:
            self.failure_checkpoint(job, "failed")
            return result({**self.summary(job), "error": refused}, True)
        settled = dict(job)
        diagnostics = copy.deepcopy(job.get("connection_diagnostics"))
        try:
            # The new connection gets fresh snapshots; the old ones stay one level back.
            earlier = job.pop("connection_diagnostics", None)
            if earlier:
                earlier.pop("previous", None)
                job["connection_diagnostics"] = {"previous": earlier}
            with self.bootstrap():
                job.update(
                    client_name="EP " + job["label"] + " [" + uuid.uuid4().hex[:8] + "]",
                    generation=self.preflight(),
                    metadata=None,
                    client=None,
                )
                # The old window's disposition and issued removal describe the
                # closed allocation; carried over, they would let the new one
                # read as closed or settle a vanished window as its own removal.
                for key in (
                    "initial_connector",
                    "connector_probe",
                    "allocation_failure",
                    "window_disposition",
                    "window_removal_issued",
                ):
                    job.pop(key, None)
                try:
                    self.checkpoint(job, "starting")
                except Refusal as error:
                    if str(error) != "receipts_lock_busy":
                        raise
                    # Nothing new was created, so the job stays exactly as the
                    # finished receipt on disk says, rather than a failed job
                    # with no IDs that no route could ever reconcile.
                    job.clear()
                    job.update(settled)
                    if diagnostics is not None:
                        job["connection_diagnostics"] = diagnostics
                    return result({**self.summary(job), "error": refused}, True)
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
            self.failure_checkpoint(job, "failed")
            return result({**self.summary(job), "error": refused}, True)

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
                # Every receipt save of the whole recovery, including the new
                # connection's, waits a bounded time on a peer-held lock.
                with bounded_saves():
                    return self.recover(job)
            if self.inventory is None:
                return self.refuse_before_forwarding(
                    job,
                    sealed,
                    "tool_inventory_required",
                    "On this same browser transport, call tools/list first.",
                )
            if name == "browser_install" or name not in {t["name"] for t in self.inventory}:
                return self.refuse_before_forwarding(
                    job,
                    sealed,
                    "unknown_browser_tool",
                    "Use a browser tool advertised by tools/list.",
                )
            pending_chooser = "chooser_task_id" in job
            if pending_chooser and name != "browser_file_upload":
                return result({"error": "file_chooser_pending_use_upload_or_finish"}, True)
            try:
                denied, note = self.policy(name, args)
            except Exception:
                return self.refuse_before_forwarding(
                    job,
                    sealed,
                    "headless_policy_failed",
                    "The headless route policy could not be checked.",
                )
            if denied:
                return denied
            job.setdefault("timings", []).append(
                {"tool": name, "sealed": sealed, "stages": [["received", round(time.time(), 3)]]}
            )
            del job["timings"][:-TIMING_RECORDS]
            if sealed:
                return self.sealed_call(job, args["code"])
            capture_stage, reported = "prime", "unknown"
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
                    if pending_chooser:
                        if job["status"] != "ready" or self.preflight() != job["generation"]:
                            raise Refusal("browser_generation_changed_no_replay")
                        _, state = self.check_file_chooser(job)
                        if state["pending"] is not True:
                            raise Refusal("owned_file_chooser_missing")
                        self.select_private_tab(job, state["taskIndex"])
                    else:
                        self.prime(job)
                    job["ownership_pending"] = True
                    self.mark(job, "tool_start")
                    self.checkpoint(job)
                    capture_stage = "tool"
                    reply = job["client"].call("tools/call", {"name": name, "arguments": args})
                self.mark(job, "tool_end")
                notes = [note] if note else []
                if reply.get("isError") and name != "browser_tabs":
                    self.mark(job, "vendor_error:" + (vendor_error_class(reply) or "unclassified"))
                    notes.append(VENDOR_ERROR_NOTE)
                    reported = reported_close_reason(reply)
                capture_stage = "post_call"
                opened_chooser = (
                    name == "browser_click"
                    and not job.get("relay_mode")
                    and any(
                        FILE_CHOOSER_MARKER in block.get("text", "").splitlines()
                        for block in reply.get("content", [])
                        if block.get("type") == "text"
                    )
                )
                if opened_chooser or pending_chooser:
                    observed, state = self.check_file_chooser(job)
                    if opened_chooser and state["pending"] is not True:
                        raise Refusal("owned_file_chooser_missing")
                    if state["pending"] is True:
                        job["chooser_task_id"] = state["taskId"]
                    else:
                        job.pop("chooser_task_id", None)
                        self.select_private_tab(job, state["taskIndex"])
                    job["metadata"] = observed
                else:
                    if (
                        name == "browser_navigate"
                        and not job.get("relay_mode")
                        and type(job.get("chooser_connector_index")) is int
                        and isinstance(args.get("url"), str)
                        and args["url"].startswith("https://")
                        and self.recover_navigation_page(job)
                    ):
                        notes.append(NAVIGATION_REBOUND_NOTE)
                    job["metadata"] = self.verify_connection(job)
                    # A click or script can also leave the page for another
                    # origin. Chrome swaps the tab's target, which closes the
                    # retained Page while the tab and its IDs stay the same.
                    if (
                        job.get("working_page") == "closed"
                        and name != "browser_navigate"
                        and not job.get("relay_mode")
                        and type(job.get("chooser_connector_index")) is int
                        and self.recover_navigation_page(job)
                    ):
                        notes.append(NAVIGATION_REBOUND_NOTE)
                        job["metadata"] = self.verify_connection(job)
                job["ownership_pending"] = False
                self.mark(job, "post_metadata")
                if job.get("working_page") == "closed":
                    # No exact replacement Page was proved. Never continue or
                    # replay; finish or recover closes the tab by its saved ID.
                    self.mark(job, "failed:working_page_lost")
                    self.capture_connection_diagnostics(job, "post_call", reason=reported)
                    self.checkpoint(job, "failed")
                    notes.append(WORKING_PAGE_LOST_NOTE)
                else:
                    self.checkpoint(job)
                for text in notes:
                    reply.setdefault("content", []).append({"type": "text", "text": text})
                return redact(reply)
            except Exception as error:
                self.mark(job, failure_stage(error))
                self.capture_connection_diagnostics(
                    job, capture_stage, reason=getattr(error, "close_reason", reported)
                )
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
            self.capture_connection_diagnostics(
                job, "sealed_call", reason=getattr(error, "close_reason", "unknown")
            )
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
    parser.add_argument(
        "--diagnose-failed",
        metavar="JOB_ID",
        help="Print a read-only, content-free cleanup proof inventory and exit",
    )
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text())
        route = Route(config, control=not args.diagnose_failed)
        if args.diagnose_failed:
            try:
                print(json.dumps(route.diagnose_failed(args.diagnose_failed)))
            finally:
                route.close_control()
            return 0

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
