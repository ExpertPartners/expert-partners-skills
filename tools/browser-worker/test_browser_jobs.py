"""Contract tests for job routing, concurrent calls and fail-closed recovery."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins/operating-doctrine/skills/browser-automation/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("owned_browser_job_source", SCRIPTS / "browser_jobs.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
StdioClient, Refusal = b.StdioClient, b.Refusal


def decode(reply):
    return json.loads(reply["content"][0]["text"])


class JobTests(unittest.TestCase):
    def route(self, root):
        route = b.Route.__new__(b.Route)
        route.root = Path(root)
        route.lock = threading.RLock()
        route.jobs = {}
        route.inventory = [{"name": "browser_navigate", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
                           {"name": "browser_install", "inputSchema": {"type": "object", "properties": {}}}]
        route.guard = SimpleNamespace(decide=lambda _: None)
        route.bootstrap = contextlib.nullcontext
        route.preflight = lambda: {"pid": 123, "started": "synthetic"}
        route.prime = lambda _: None
        route.metadata = lambda _, strict=True: {"connectorId": 1, "windowId": 1, "groupId": 1, "groupTitle": "fixture"}
        return route

    def test_required_handle_and_no_shared_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            tools = route.tools()["tools"]
            self.assertNotIn("browser_install", [t["name"] for t in tools])
            navigate = next(t for t in tools if t["name"] == "browser_navigate")
            self.assertIn("job_id", navigate["inputSchema"]["required"])
            for args in ({}, {"job_id": "f" * 32}, {"job_id": "../foreign"}):
                with self.assertRaises(Refusal):
                    route.call("browser_navigate", args)

    def test_start_failure_returns_owned_handle_without_retry(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            with patch.object(route, "connect", side_effect=Refusal("fixture_failure")) as connect:
                reply = route.start("fixture")
            self.assertTrue(reply["isError"])
            row = decode(reply)
            self.assertEqual(row["status"], "failed")
            self.assertEqual(connect.call_count, 1)
            self.assertIn(row["job_id"], route.jobs)
            receipt = Path(root) / (row["job_id"] + ".json")
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("client", json.loads(receipt.read_text()))

    def test_policy_denial_never_reaches_browser(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = {"job_id": "a" * 32, "lock": threading.RLock(), "status": "ready"}
            route.jobs[job["job_id"]] = job
            route.guard = SimpleNamespace(decide=lambda payload: ("deny", "Use connected API"))
            with patch.object(route, "prime") as prime:
                reply = route.call("browser_navigate", {"job_id": job["job_id"], "url": "https://api-covered.example.test"})
            self.assertTrue(reply["isError"])
            self.assertEqual(decode(reply)["headless_route"], "Use connected API")
            prime.assert_not_called()

    def test_canonical_lazy_refresh_is_retained(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            refreshed = []
            route.guard = SimpleNamespace(decide=lambda _: ("deny", "Use connected API"),
                                          refresh_due=lambda: True,
                                          start_background_refresh=lambda: refreshed.append(True))
            denied, _ = route.policy("browser_navigate", {"url": "https://covered.example.test"})
            self.assertTrue(denied["isError"])
            self.assertEqual(refreshed, [True])

    def test_distinct_jobs_overlap_same_job_serializes_and_no_replay(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            windows = []
            window_lock = threading.Lock()

            def invoke(*_):
                start = time.monotonic()
                time.sleep(.08)
                with window_lock:
                    windows.append((start, time.monotonic()))
                return b.result({"worked": True})

            for handle in ("a" * 32, "b" * 32):
                route.jobs[handle] = {"job_id": handle, "label": "fixture", "client_name": "fixture", "generation": {}, "metadata": route.metadata(None), "updated": 0,
                                      "lock": threading.RLock(), "status": "ready", "client": SimpleNamespace(call=invoke)}

            def call(j):
                route.call("browser_navigate", {"job_id": j, "url": "http://127.0.0.1"})

            a, peer = route.jobs
            for handles, overlapping in (((a, peer), True), ((a, a), False)):
                windows.clear()
                threads = [threading.Thread(target=call, args=(j,)) for j in handles]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                self.assertEqual(min(x[1] for x in windows) > max(x[0] for x in windows), overlapping)
            with patch.object(route.jobs[a]["client"], "call", side_effect=Refusal("transport_closed")) as failed:
                reply = route.call("browser_navigate", {"job_id": a, "url": "http://127.0.0.1"})
            self.assertTrue(reply["isError"])
            self.assertEqual(failed.call_count, 1)
            self.assertEqual(route.jobs[a]["status"], "failed")
            self.assertEqual(route.jobs[peer]["status"], "ready")

    def test_changed_connection_is_never_adopted_or_closed(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            original = route.metadata(None)
            job = {"client": object(), "generation": route.preflight(), "metadata": original.copy()}
            for field, changed in (("windowId", 2), ("groupId", 2), ("connectorId", 2), ("groupTitle", "peer")):
                route.metadata = lambda _, strict=True, field=field, changed=changed: {**original, field: changed}
                with patch.object(b, "code") as execute:
                    with self.assertRaises(Refusal):
                        route.dispose_live(job)
                execute.assert_not_called()
                self.assertEqual(job["metadata"], original)

    def test_foreign_group_arrival_is_refused_and_never_closed(self):
        # Execute the shipped JS against actual fake Page references, rather than
        # mocking away the provenance check that protects cleanup.
        source = (SCRIPTS / "owned_pages.js").read_text()
        fixture = r'''
const assert = require('node:assert/strict');
let current;
const tabs = new Map();
const pages = [];
function page(id, opener = null) {
  const tab = {id, windowId: 5, groupId: 7, url: 'about:blank'};
  tabs.set(id, tab);
  const p = {closed:false, context:()=>context, isClosed:()=>p.closed,
    opener:async()=>opener, url:()=>tab.url, title:async()=>String(id),
    goto:async(url)=>{tab.url=url;},
    evaluate:async(fn,arg)=>{current=p;return await fn(arg);},
    close:async()=>{p.closed=true;tabs.delete(id);}};
  p.id=id;
  pages.push(p);
  return p;
}
const context = {pages:()=>pages.filter(p=>!p.closed),newPage:async()=>page(10)};
global.chrome = {tabs:{create:async(args)=>{page(10);const t=tabs.get(10);t.url=args.url;return t;},
  group:async({tabIds,groupId})=>{for(const id of tabIds)tabs.get(id).groupId=groupId;},
  getCurrent:async()=>tabs.get(current.id),get:async(id)=>{
  if(!tabs.has(id))throw Error('missing');return tabs.get(id);},
  query:async(q)=>[...tabs.values()].filter(t=>(q.windowId===undefined||t.windowId===q.windowId)&&(q.groupId===undefined||t.groupId===q.groupId)),
  remove:async(ids)=>{for(const id of ids){tabs.delete(id);for(const p of pages)if(p.id===id)p.closed=true;}}},
  tabGroups:{get:async()=>({title:'fixture'})}};
(async()=>{
  const connector=page(1);
  const s=await newOwnedState(connector);
  s.task=await s.create();
  assert.deepEqual((await s.snapshot()).tabIds,[1,10]);
  const foreign=page(999); // Same window and group, no owned opener.
  await assert.rejects(()=>s.snapshot(),/unproven_page_arrival/);
  assert.deepEqual((await s.snapshot(false)).tabIds,[1,10]);
  // Detach/reattach can replace the SDK Page without closing its Chrome tab.
  // Exact proven ID cleanup must still close that tab, not the foreign arrival.
  s.task.closed=true;
  const reattached=page(10);
  await s.closeCreated();
  assert.equal(s.task.closed,true);
  assert.equal(reattached.closed,true);
  assert.equal(foreign.closed,false);
  assert.equal(connector.closed,false);
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        checked = subprocess.run(["node", "-e", source + fixture], capture_output=True, text=True, timeout=10)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_tab_indices_agree_with_vendor_responses(self):
        route = b.Route.__new__(b.Route)
        # The same literal body sent to the vendor executes against its actual
        # context order: connector=0, A=1, B=2. Closing advertised A index1 must
        # never close B through a filtered reindex.
        captured = []
        with patch.object(b, "code", side_effect=lambda _, body: captured.append(body) or {}):
            route.tabs({"client": None}, {"action": "close", "index": 1})
        fixture = r'''
const assert = require('node:assert/strict');
const a={closed:false,isClosed:()=>false,close:async()=>{a.closed=true;},url:()=>'',title:async()=>''};
const b={closed:false,isClosed:()=>false,close:async()=>{b.closed=true;},url:()=>'',title:async()=>''};
const connector={context:()=>({pages:()=>[connector,...(a.closed?[]:[a]),b]})};
process.__epBrowserJob={connector,task:a,created:new Set([connector,a,b]),closePage:async(p)=>await p.close()};
'''
        script = fixture + "(async()=>{" + captured[0] + "})().then(()=>{assert.equal(a.closed,true);assert.equal(b.closed,false);}).catch(e=>{console.error(e);process.exitCode=1;});"
        checked = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=10)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_live_cleanup_refuses_a_popup_born_during_parent_close(self):
        source = (SCRIPTS / "owned_pages.js").read_text()
        fixture = r'''
const assert=require('node:assert/strict');
let current;
const tabs=new Map();
const pages=[];
function page(id){
  const tab={id,windowId:5,groupId:7,url:'about:blank'};tabs.set(id,tab);
  const p={id,closed:false,context:()=>context,isClosed:()=>p.closed,opener:async()=>null,
    url:()=>tab.url,goto:async(u)=>{tab.url=u;},evaluate:async(fn,arg)=>{current=p;return await fn(arg);},
    close:async()=>{p.closed=true;tabs.delete(id);if(id===10)tabs.set(11,{id:11,openerTabId:10,windowId:6,groupId:-1});}};
  pages.push(p);return p;
}
const context={pages:()=>pages.filter(p=>!p.closed),newPage:async()=>page(10)};
global.chrome={tabs:{create:async(args)=>{page(10);const t=tabs.get(10);t.url=args.url;return t;},
  group:async({tabIds,groupId})=>{for(const id of tabIds)tabs.get(id).groupId=groupId;},
  getCurrent:async()=>tabs.get(current.id),get:async(id)=>{
  if(!tabs.has(id))throw Error('missing');return tabs.get(id);},
  query:async(q)=>[...tabs.values()].filter(t=>(q.windowId===undefined||t.windowId===q.windowId)&&(q.groupId===undefined||t.groupId===q.groupId)),
  remove:async(ids)=>{for(const id of ids){tabs.delete(id);if(id===10)tabs.set(11,{id:11,windowId:6,groupId:-1});}}},tabGroups:{get:async()=>({title:'fixture'})}};
(async()=>{
  const s=await newOwnedState(page(1));s.task=await s.create();
  await assert.rejects(()=>s.closeCreated(),/owned_page_close_inventory_uncertain/);
  assert.equal(tabs.has(11),true); // Never silently adopt or delete the late popup.
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        checked = subprocess.run(["node", "-e", source + fixture], capture_output=True, text=True, timeout=10)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_owned_pages_suppress_the_1password_inline_menu(self):
        # The 1Password inline menu iframe detaches the extension debugger on
        # Google sign-in pages, so every owned page must get the guard first.
        source = (SCRIPTS / "owned_pages.js").read_text()
        fixture = r'''
const assert=require('node:assert/strict');
let current;
const tabs=new Map();
const pages=[];
function page(id){
  const tab={id,windowId:5,groupId:7,url:'about:blank'};tabs.set(id,tab);
  const p={id,closed:false,inits:[],context:()=>context,isClosed:()=>p.closed,opener:async()=>null,
    url:()=>tab.url,evaluate:async(fn,arg)=>{current=p;return await fn(arg);},
    addInitScript:async(fn)=>{p.inits.push(fn);}};
  pages.push(p);return p;
}
const context={pages:()=>pages.filter(p=>!p.closed),newPage:async()=>page(10)};
global.chrome={tabs:{create:async(args)=>{page(10);const t=tabs.get(10);t.url=args.url;return t;},
  group:async({tabIds,groupId})=>{for(const id of tabIds)tabs.get(id).groupId=groupId;},
  getCurrent:async()=>tabs.get(current.id),get:async(id)=>tabs.get(id),
  query:async()=>[]},tabGroups:{get:async()=>({title:'fixture'})}};
(async()=>{
  const connector=page(1);
  const s=await newOwnedState(connector);
  const task=await s.create();
  assert.equal(connector.inits.length,0);
  assert.equal(task.inits.length,1);
  const registry=new Map();
  global.HTMLElement=class{remove(){this.removed=true;}};
  global.customElements={get:(t)=>registry.get(t),define:(t,c)=>registry.set(t,c)};
  task.inits[0]();
  task.inits[0](); // A second run on the same document must not throw.
  for (const tag of ['com-1password-uso','com-1password-button','com-1password-menu','com-1password-notification']) {
    const el=new (registry.get(tag))();el.connectedCallback();
    assert.equal(el.removed,true,tag);
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        checked = subprocess.run(["node", "-e", source + fixture], capture_output=True, text=True, timeout=10)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_connector_credential_redacted_recursively(self):
        url = b.EXTENSION + "?mcpRelayUrl=ws%3A%2F%2F127.0.0.1&token=SYNTHETIC_CANARY"
        actual = json.dumps(b.redact({"content": [{"text": "Welcome [link](" + url + ")"}], "nested": url}))
        self.assertNotIn("SYNTHETIC_CANARY", actual)
        self.assertNotIn("mcpRelayUrl", actual)

    def test_uncheckpointed_inventory_never_claims_failed_cleanup(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = {"client": None, "metadata": route.metadata(None), "ownership_pending": True}
            with patch.object(route, "client", create=True) as connect:
                with self.assertRaisesRegex(Refusal, "uncheckpointed"):
                    route.dispose_failed(job)
            connect.assert_not_called()

    def test_late_popup_refuses_disconnected_cleanup_in_any_window(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            own = {"connectorId": 1, "windowId": 5, "groupId": 7, "groupTitle": "fixture", "tabIds": [1, 10]}
            job = {"client": None, "metadata": own, "generation": route.preflight(), "client_name": "fixture", "ownership_pending": False}
            captured = []

            def capture(_, body):
                if "async({old,clientName,connectorOrigin})" in body:
                    captured.append(body)
                return {"closed": True}

            with patch.object(route, "client", create=True, return_value=SimpleNamespace(close=lambda: None)), patch.object(b, "code", side_effect=capture), patch.object(b.time, "sleep"):
                route.dispose_failed(job)
            self.assertEqual(len(captured), 1)
            fixture = r'''
const assert=require('node:assert/strict');
let unknownWindow=5;
let parentGone=false;
let popupLive=true;
let removed=[];
global.chrome={tabs:{query:async()=>[
  ...(parentGone?[]:[{id:1,windowId:5,groupId:-1},{id:10,windowId:5,groupId:-1}]),
  ...(popupLive?[{id:11,...(parentGone?{}:{openerTabId:10}),windowId:unknownWindow,groupId:-1}]:[])],
  get:async(id)=>{if(parentGone)throw Error('missing');return {id,windowId:5,groupId:-1,
    url:'chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/connect.html?client='+encodeURIComponent(JSON.stringify({name:'fixture'}))};},
  remove:async(ids)=>{removed.push(...ids);parentGone=true;popupLive=true;}},
  debugger:{getTargets:async()=>[]},runtime:{sendMessage:async()=>({connections:[]})}};
process.__epBrowserJob={connector:{evaluate:async(fn,arg)=>await fn(arg)}};
'''
            body = captured[0]
            # Check both same-window and separate-window late popups, even after
            # all saved parent tabs have already disappeared.
            script = fixture + "async function attempt(){" + body + "}\n" + r'''
(async()=>{for(const w of [5,6])for(const gone of [false,true]){
  unknownWindow=w;parentGone=gone;removed=[];
  await assert.rejects(()=>attempt(),/uncheckpointed_page_arrival|saved_owned_tab_missing/);
  assert.deepEqual(removed,[]);
}
  unknownWindow=6;parentGone=false;popupLive=false;removed=[];
  await assert.rejects(()=>attempt(),/owned_cleanup_inventory_uncertain/);
  assert.deepEqual(removed,[1,10]);
  assert.equal(popupLive,true); // Late popup is preserved and completion refused.
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
            checked = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=10)
            self.assertEqual(checked.returncode, 0, checked.stderr)

    def sealed_route(self, root):
        route = self.route(root)
        route.inventory.append({"name": "browser_run_code_unsafe", "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}}}})
        sent = []
        job = {"job_id": "c" * 32, "label": "fixture", "client_name": "fixture", "generation": {}, "metadata": route.metadata(None), "updated": 0,
               "lock": threading.RLock(), "status": "ready", "client": SimpleNamespace(call=lambda *a: sent.append(a) or b.result({"vendor": "normal"}))}
        route.jobs[job["job_id"]] = job
        return route, job, sent

    def test_sealed_reply_is_a_fixed_token_and_job_becomes_finish_only(self):
        source = "async (page) => { console.log('SYNTHETIC_CANARY'); throw Error('SYNTHETIC_CANARY'); }"
        for vendor, expected, status in (({"sealed": "ok"}, {"sealed": "ok"}, "ready"),
                                         ({"sealed": "error"}, {"sealed": "error", "code": "sealed_code_failed"}, "ready"),
                                         ({"sealed": "SYNTHETIC_CANARY"}, {"sealed": "error", "code": "sealed_outcome_uncertain"}, "failed"),
                                         (Refusal("owned_operation_failed"), {"sealed": "error", "code": "sealed_outcome_uncertain"}, "failed")):
            with tempfile.TemporaryDirectory() as root:
                route, job, sent = self.sealed_route(root)
                bodies = []

                def run(_, body, vendor=vendor):
                    bodies.append(body)
                    if isinstance(vendor, Exception):
                        raise vendor
                    return vendor
                with patch.object(b, "code", side_effect=run):
                    reply = route.call("browser_run_code_unsafe", {"job_id": job["job_id"], "code": source, "sealed": True})
                self.assertEqual(json.loads(reply["content"][0]["text"]), expected)
                self.assertEqual(len(reply["content"]), 1)
                self.assertEqual(reply["isError"], expected != {"sealed": "ok"})
                self.assertEqual(job["status"], status)
                self.assertEqual(sent, [])  # The user code never travels as an ordinary vendor call.
                self.assertIn(json.dumps(source), bodies[0])
                receipt = (Path(root) / (job["job_id"] + ".json")).read_text()
                self.assertNotIn("SYNTHETIC_CANARY", receipt)
                self.assertTrue(json.loads(receipt)["sealed"])
                with patch.object(route, "prime") as prime:
                    for name, args in (("browser_navigate", {"url": "http://127.0.0.1"}), ("browser_run_code_unsafe", {"code": source, "sealed": True})):
                        refused = route.call(name, {"job_id": job["job_id"], **args})
                        self.assertEqual(decode(refused), {"sealed": "error", "code": "sealed_job_finish_only"})
                prime.assert_not_called()

    def test_sealed_arguments_are_strict_and_never_reach_the_browser(self):
        with tempfile.TemporaryDirectory() as root:
            route, job, sent = self.sealed_route(root)
            with patch.object(route, "prime") as prime, patch.object(b, "code") as execute:
                for args in ({"code": "async()=>{}", "sealed": "yes"}, {"code": "async()=>{}", "filename": "x.js", "sealed": True}, {"code": " ", "sealed": True}, {"sealed": True}):
                    reply = route.call("browser_run_code_unsafe", {"job_id": job["job_id"], **args})
                    self.assertEqual(decode(reply), {"sealed": "error", "code": "sealed_arguments_invalid"})
            prime.assert_not_called()
            execute.assert_not_called()
            self.assertFalse(job.get("sealed"))

    def test_normal_run_code_is_forwarded_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            route, job, sent = self.sealed_route(root)
            for extra in ({}, {"sealed": False}):
                sent.clear()
                reply = route.call("browser_run_code_unsafe", {"job_id": job["job_id"], "code": "async()=>1", **extra})
                self.assertEqual(sent, [("tools/call", {"name": "browser_run_code_unsafe", "arguments": {"code": "async()=>1"}})])
                self.assertEqual(decode(reply), {"vendor": "normal"})
            self.assertFalse(job.get("sealed"))
            schema = next(t for t in route.tools()["tools"] if t["name"] == "browser_run_code_unsafe")["inputSchema"]
            self.assertEqual(schema["properties"]["sealed"]["type"], "boolean")
            self.assertNotIn("sealed", schema["required"])

    def test_receipt_retains_stage_timestamps_without_page_content(self):
        with tempfile.TemporaryDirectory() as root:
            route, job, _ = self.sealed_route(root)
            route.prime = b.Route.prime.__get__(route)
            job["generation"] = route.preflight()
            with patch.object(b, "code", return_value={"index": 1}):
                job["client"] = SimpleNamespace(call=lambda *a: b.result({"vendor": "SYNTHETIC_CANARY"}) if a[1]["name"] == "browser_navigate" else {"content": []})
                for _ in range(b.TIMING_RECORDS + 2):
                    route.call("browser_navigate", {"job_id": job["job_id"], "url": "http://127.0.0.1/SYNTHETIC_CANARY"})
            row = json.loads((Path(root) / (job["job_id"] + ".json")).read_text())
            self.assertEqual(len(row["timings"]), b.TIMING_RECORDS)
            last = row["timings"][-1]
            self.assertEqual(last["tool"], "browser_navigate")
            self.assertEqual([s for s, _ in last["stages"]], ["received", "prime_preflight", "prime_verify", "prime_own_index", "prime_select", "tool_start", "tool_end", "post_metadata"])
            times = [t for _, t in last["stages"]]
            self.assertEqual(times, sorted(times))
            self.assertNotIn("SYNTHETIC_CANARY", json.dumps(row))
            with patch.object(b, "code", side_effect=Refusal("response_timeout")):
                route.call("browser_navigate", {"job_id": job["job_id"], "url": "http://127.0.0.1"})
            row = json.loads((Path(root) / (job["job_id"] + ".json")).read_text())
            self.assertEqual([s for s, _ in row["timings"][-1]["stages"]], ["received", "prime_preflight", "prime_verify", "failed"])

    def test_seal_silences_vendor_capture_before_response_build(self):
        # Execute the shipped seal against a fake vendor Tab whose prototype owns
        # the capture methods, as in the pinned Playwright MCP bundle.
        with tempfile.TemporaryDirectory() as root:
            route, job, _ = self.sealed_route(root)
            bodies = []
            with patch.object(b, "code", side_effect=lambda _, body: bodies.append(body) or {"sealed": "error"}):
                route.call("browser_run_code_unsafe", {"job_id": job["job_id"], "sealed": True,
                                                       "code": "async (page) => { page.emit('console', 'SYNTHETIC_CANARY'); throw Error('SYNTHETIC_CANARY'); }"})
        fixture = r'''
const assert=require('node:assert/strict');
const written=[];let cleared=0;
class Tab{constructor(page){this.page=page;this.context=ctx;this._consoleLog={stopped:false,stop(){this.stopped=true;}};this._recentEventEntries=[{type:'console'}];this._requests=[1];page[sym]=this;}
  _handleConsoleMessage(m){written.push(m);} _addLogEntry(e){this._recentEventEntries.push(e);} _handleRequest(r){this._requests.push(r);}
  _handleResponse(){} _handleRequestFailed(){} async _downloadStarted(){written.push('download');}
  async captureSnapshot(){return {ariaSnapshot:'SYNTHETIC_CANARY',modalStates:[{description:'SYNTHETIC_CANARY'}],events:[]};}
  async headerSnapshot(){return {title:'SYNTHETIC_CANARY',url:'http://x/SYNTHETIC_CANARY',changed:true};} isCurrentTab(){return true;}}
const sym=Symbol('tabSymbol');const tabs=[];const ctx={tabs:()=>tabs,sessionLog:undefined};
const page={emit(kind,m){tabs[0]._handleConsoleMessage(m);tabs[0]._addLogEntry({m});},clearConsoleMessages:async()=>{cleared++;},clearPageErrors:async()=>{cleared++;}};
tabs.push(new Tab(page));
process.__epBrowserJob={task:page};
(async()=>{
  const out=await (async(page)=>{BODY})(page);
  assert.deepEqual(out,{sealed:'error'});
  assert.deepEqual(written,[]);
  assert.equal(tabs[0]._consoleLog.stopped,true);
  assert.deepEqual(tabs[0]._recentEventEntries,[]);
  assert.equal(tabs[0]._requests.length,0);
  assert.equal(cleared,2);
  const later=new Tab({});later._handleConsoleMessage('SYNTHETIC_CANARY');await later._downloadStarted();
  assert.deepEqual(written,[]);
  assert.equal(JSON.stringify(await later.captureSnapshot()).includes('SYNTHETIC_CANARY'),false);
  assert.equal(JSON.stringify(await later.headerSnapshot()).includes('SYNTHETIC_CANARY'),false);
  process.__epBrowserJob={task:{}};
  await assert.rejects(()=>(async(page)=>{BODY})(page),/sealed_target_not_owned_task/);
  ctx.sessionLog={};process.__epBrowserJob={task:page};
  await assert.rejects(()=>(async(page)=>{BODY})(page),/sealed_session_log_active/);
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        checked = subprocess.run(["node", "-e", fixture.replace("BODY", bodies[0])], capture_output=True, text=True, timeout=10)
        self.assertEqual(checked.returncode, 0, checked.stderr)
    def test_owned_transport_reaps_child_and_never_signals_peer(self):
        script = "import sys,json\nfor line in sys.stdin:\n q=json.loads(line); print(json.dumps({'jsonrpc':'2.0','id':q['id'],'result':{'ok':True}}),flush=True)\n"
        clients = [StdioClient([sys.executable, "-u", "-c", script], os.environ.copy(), timeout=3) for _ in range(2)]
        try:
            self.assertEqual(clients[0].call("ping"), {"ok": True})
            clients[0].close()
            self.assertTrue(clients[0].cleanup_verified)
            self.assertEqual(clients[1].call("ping"), {"ok": True})
        finally:
            for client in clients:
                client.close()


if __name__ == "__main__":
    unittest.main()
