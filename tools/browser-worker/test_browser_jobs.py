"""Contract tests for job routing, concurrent calls and fail-closed recovery."""

import contextlib
import copy
import importlib.util
import json
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch

SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "plugins/operating-doctrine/skills/browser-automation/scripts"
)
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "owned_browser_job_source", SCRIPTS / "browser_jobs.py"
)
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
        route.inventory = [
            {
                "name": "browser_navigate",
                "inputSchema": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            },
            {"name": "browser_install", "inputSchema": {"type": "object", "properties": {}}},
        ]
        route.guard = SimpleNamespace(decide=lambda _: None)
        route.bootstrap = contextlib.nullcontext
        route.preflight = lambda: {"pid": 123, "started": "synthetic"}
        route.prime = lambda _: None
        route.metadata = lambda _, strict=True: {
            "connectorId": 1,
            "windowId": 1,
            "groupId": 1,
            "groupTitle": "fixture",
        }
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

    def test_owned_file_chooser_round_trip(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            names = ("browser_click", "browser_file_upload")
            route.inventory += [{"name": name} for name in names]
            metadata = route.metadata(None) | {"tabIds": [1, 2]}
            marker = b.FILE_CHOOSER_MARKER
            calls = []

            def vendor(_, req):
                calls.append(req["name"])
                if req["name"] == "browser_click":
                    return {"content": [{"type": "text", "text": marker}]}
                return {"content": []}

            jid = "a" * 32
            client = SimpleNamespace(call=vendor)
            job = {
                "job_id": jid,
                "label": "synthetic",
                "lock": threading.RLock(),
                "status": "ready",
                "client": client,
                "generation": route.preflight(),
                "metadata": metadata,
                "chooser_connector_index": 0,
            }
            route.jobs[jid] = job
            route.checkpoint = lambda job, status=None: job.update(status=status or job["status"])
            states = [
                {"snapshot": metadata.copy(), "taskId": 2, "taskIndex": 1, "pending": pending}
                for pending in (True, True, False)
            ]
            with patch.object(b, "code", side_effect=states):
                answer = route.call("browser_click", {"job_id": jid, "target": "fixture"})
                self.assertIn(marker, answer["content"][0]["text"])
                self.assertEqual(job["chooser_task_id"], 2)
                with self.assertRaises(Refusal):
                    route.call("browser_file_upload", {"job_id": "b" * 32})
                self.assertTrue(route.call("browser_navigate", {"job_id": jid})["isError"])
                route.call("browser_file_upload", {"job_id": jid, "paths": ["/tmp/proof.txt"]})
            self.assertNotIn("chooser_task_id", job)
            self.assertEqual(job["status"], "ready")
            self.assertEqual(calls.count("browser_file_upload"), 1)

    def test_chooser_refuses_wrong_or_unowned_page(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            metadata = route.metadata(None) | {"tabIds": [1, 2, 3]}
            job = {
                "client": SimpleNamespace(call=lambda *_: {}),
                "metadata": metadata,
                "chooser_connector_index": 0,
                "chooser_task_id": 2,
            }
            for task, ids in ((1, [1, 2, 3]), (3, [1, 2, 3]), (9, [1, 2, 3]), (2, [1, 2, 3, 9])):
                with (
                    self.subTest(task=task, ids=ids),
                    patch.object(
                        b,
                        "code",
                        return_value={
                            "snapshot": metadata | {"tabIds": ids},
                            "taskId": task,
                            "taskIndex": 1,
                            "pending": True,
                        },
                    ),
                ):
                    with self.assertRaisesRegex(Refusal, "chooser_page_not_owned"):
                        route.check_file_chooser(job)

    def test_v2_requires_binding_before_working_page(self):
        generation = {"pid": 123, "started": "synthetic"}
        connector = {
            "connectorId": 17,
            "windowId": 25,
            "groupId": None,
            "groupTitle": None,
            "tabIds": [17],
            "workingPage": "none",
        }
        for claims in (
            [{"tabId": 17, "windowId": 25, "urlClass": "blank"}],
            [],
            [{"tabId": 19, "windowId": 25, "urlClass": "blank"}],
        ):
            with self.subTest(claims=claims), tempfile.TemporaryDirectory() as root:
                route = self.route(root)
                route.config = {"relay_v2": {}}
                route.aqua_cleanup = lambda: SimpleNamespace(inventory=lambda: [])
                route.client = lambda *_: object()
                route.metadata = lambda *_: {**connector, "tabIds": [17, 18], "workingPage": "live"}
                broker = SimpleNamespace(
                    socket=Path(root) / "broker.sock",
                    proc=SimpleNamespace(pid=283),
                    rpc=lambda _: {"initialized": True, "claims": claims},
                )
                job = {
                    "job_id": "a" * 32,
                    "generation": generation,
                    "client_name": "test",
                    "label": "test",
                    "status": "starting",
                    "metadata": None,
                }
                with (
                    patch.object(b, "RelayBroker", return_value=broker),
                    patch.object(
                        b, "code", side_effect=[dict(connector), {"created": True}]
                    ) as code,
                ):
                    if claims and claims[0]["tabId"] == 17:
                        route.connect_relay(job, True)
                        self.assertEqual(job["status"], "ready")
                        self.assertEqual(job["metadata"]["tabIds"], [17, 18])
                        self.assertEqual(code.call_count, 2)
                    else:
                        with self.assertRaises(Refusal):
                            route.connect_relay(job, True)
                        self.assertEqual(code.call_count, 1)

    def test_legacy_path_still_runs_with_v2_dependencies_configured(self):
        for settings, version, version_checked in (
            ({"helper": "/retained/helper"}, (0, 6), False),
            ({"enabled": False}, (0, 6), False),
            ({"enabled": True}, (0, 5), True),
        ):
            with self.subTest(settings=settings, version=version):
                self.assert_connector_adoption(settings, version, version_checked)

    def assert_connector_adoption(self, settings, version, version_checked):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            route.config = {"relay_v2": settings}
            client = object()
            route.client = lambda _: client
            with (
                patch.object(
                    b,
                    "code",
                    return_value={
                        "sdk_page_count": 1,
                        "sdk_connector_count": 0,
                        "expected_url_matches": False,
                        "observed": "about_blank",
                    },
                ) as probe,
                patch.object(route, "connect_relay") as v2,
                patch.object(route, "relay_version", return_value=version) as detect,
            ):
                result = decode(route.start("legacy refusal"))
                self.assertEqual(result["allocation_failure"]["stage"], "connector_identity")
                self.assertEqual(
                    probe.call_args_list,
                    [
                        call(
                            client,
                            b.adopt_connector_js(route.jobs[result["job_id"]]["client_name"]),
                        ),
                        call(client, b.CONNECTOR_PROBE_JS),
                    ],
                )
                self.assertEqual(detect.call_count, int(version_checked))
                v2.assert_not_called()

    def test_only_explicit_opt_in_dispatches_experimental_v2(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            route.config = {"relay_v2": {"enabled": True}}
            job = {}
            with (
                patch.object(route, "connect_relay") as v2,
                patch.object(route, "relay_version", return_value=(0, 6)),
            ):
                route.connect(job)
                v2.assert_called_once_with(job, True)

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
            self.assertEqual(
                row["allocation_failure"],
                {
                    "stage": "launcher_handshake",
                    "class": "refused",
                },
            )

    def test_connector_identity_is_checkpointed_before_isolation(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            route.client = lambda _: object()
            receipt = None

            def browser_code(_, source):
                nonlocal receipt
                if "newOwnedState(page)" not in source:
                    return {
                        "connectorId": 17,
                        "windowId": 25,
                        "extra": "do not persist",
                        "sdk_page_count": 1,
                        "sdk_connector_count": 1,
                        "observed": "expected_connect_with_query",
                        "expected_url_matches": True,
                    }
                job_id = next(iter(route.jobs))
                receipt = Path(root) / (job_id + ".json")
                saved = json.loads(receipt.read_text())
                self.assertEqual(saved["initial_connector"], {"connectorId": 17, "windowId": 25})
                self.assertIsNone(saved["metadata"])
                raise Refusal("owned_operation_failed:owned_window_isolation_failed")

            with patch.object(b, "code", side_effect=browser_code):
                row = decode(route.start("fixture"))
            self.assertEqual(
                row["allocation_failure"],
                {
                    "stage": "connector_isolation",
                    "class": "owned_operation_failed:owned_window_isolation_failed",
                },
            )
            saved = json.loads(receipt.read_text())
            self.assertIsNone(saved["metadata"])
            self.assertEqual(saved["allocation_failure"], row["allocation_failure"])
            self.assertNotIn("do not persist", receipt.read_text())

    def test_allocation_failure_does_not_keep_arbitrary_exception_details(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            route.client = lambda _: object()
            with patch.object(b, "code", side_effect=OSError("private connector URL")):
                row = decode(route.start("fixture"))
            self.assertEqual(
                row["allocation_failure"],
                {
                    "stage": "connector_identity",
                    "class": "os_error",
                },
            )
            receipt = Path(root) / (row["job_id"] + ".json")
            self.assertNotIn("private connector URL", receipt.read_text())
            self.assertNotIn("initial_connector", json.loads(receipt.read_text()))

    def test_freshness_failure_records_only_safe_count_and_url_class(self):
        for count, connectors, url_class, matches in (
            (2, 1, "expected_connect_with_query", True),
            (1, 0, "other_extension_page", False),
            (3, 0, "other_page", False),
        ):
            with (
                self.subTest(count=count, observed=url_class),
                tempfile.TemporaryDirectory() as root,
            ):
                route = self.route(root)
                route.client = lambda _: object()
                projected = {
                    "sdk_page_count": count,
                    "sdk_connector_count": connectors,
                    "observed": url_class,
                    "expected_url_matches": matches,
                    "url": "https://fixture.invalid/private?token=do_not_store",
                    "connectorId": 77,
                    "windowId": 99,
                }
                with patch.object(b, "code", return_value=projected) as probe:
                    row = decode(route.start("fixture"))
                self.assertEqual(probe.call_count, 2)
                self.assertIn("adopted", probe.call_args_list[0].args[1])
                self.assertEqual(probe.call_args_list[1].args[1], b.CONNECTOR_PROBE_JS)
                self.assertEqual(
                    row["allocation_failure"]["class"], "owned_operation_failed:not_fresh_connector"
                )
                receipt = (Path(root) / (row["job_id"] + ".json")).read_text()
                saved = json.loads(receipt)
                self.assertEqual(
                    saved["connector_probe"],
                    {
                        "sdk_page_count": count,
                        "sdk_connector_count": connectors,
                        "expected_connect_url": b.EXTENSION + "?[redacted]",
                        "observed_url_class": url_class,
                        "expected_url_matches": matches,
                    },
                )
                self.assertIsNone(saved["metadata"])
                self.assertNotIn("initial_connector", saved)
                self.assertNotIn("do_not_store", receipt)

    def test_policy_denial_never_reaches_browser(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = {"job_id": "a" * 32, "lock": threading.RLock(), "status": "ready"}
            route.jobs[job["job_id"]] = job
            route.guard = SimpleNamespace(decide=lambda payload: ("deny", "Use connected API"))
            with patch.object(route, "prime") as prime:
                reply = route.call(
                    "browser_navigate",
                    {"job_id": job["job_id"], "url": "https://api-covered.example.test"},
                )
            self.assertTrue(reply["isError"])
            self.assertEqual(decode(reply)["headless_route"], "Use connected API")
            prime.assert_not_called()

    def test_canonical_lazy_refresh_is_retained(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            refreshed = []
            route.guard = SimpleNamespace(
                decide=lambda _: ("deny", "Use connected API"),
                refresh_due=lambda: True,
                start_background_refresh=lambda: refreshed.append(True),
            )
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
                time.sleep(0.08)
                with window_lock:
                    windows.append((start, time.monotonic()))
                return b.result({"worked": True})

            for handle in ("a" * 32, "b" * 32):
                route.jobs[handle] = {
                    "job_id": handle,
                    "label": "fixture",
                    "client_name": "fixture",
                    "generation": {},
                    "metadata": route.metadata(None),
                    "updated": 0,
                    "lock": threading.RLock(),
                    "status": "ready",
                    "client": SimpleNamespace(call=invoke),
                }

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
                self.assertEqual(
                    min(x[1] for x in windows) > max(x[0] for x in windows), overlapping
                )
            with patch.object(
                route.jobs[a]["client"], "call", side_effect=Refusal("transport_closed")
            ) as failed:
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
            for field, changed in (
                ("windowId", 2),
                ("groupId", 2),
                ("connectorId", 2),
                ("groupTitle", "peer"),
            ):
                route.metadata = lambda _, strict=True, field=field, changed=changed: {
                    **original,
                    field: changed,
                }
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
        checked = subprocess.run(
            ["node", "-e", source + fixture], capture_output=True, text=True, timeout=10
        )
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
        script = (
            fixture
            + "(async()=>{"
            + captured[0]
            + "})().then(()=>{assert.equal(a.closed,true);assert.equal(b.closed,false);}).catch(e=>{console.error(e);process.exitCode=1;});"
        )
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
        checked = subprocess.run(
            ["node", "-e", source + fixture], capture_output=True, text=True, timeout=10
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_connector_credential_redacted_recursively(self):
        url = b.EXTENSION + "?mcpRelayUrl=ws%3A%2F%2F127.0.0.1&token=SYNTHETIC_CANARY"
        actual = json.dumps(
            b.redact({"content": [{"text": "Welcome [link](" + url + ")"}], "nested": url})
        )
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
            own = {
                "connectorId": 1,
                "windowId": 5,
                "groupId": 7,
                "groupTitle": "fixture",
                "tabIds": [1, 10],
            }
            body = b.failed_cleanup_js(
                {
                    "old": own,
                    "clientName": "fixture",
                    "connectorOrigin": b.EXTENSION,
                    "removalIssued": False,
                },
                True,
            )
            fixture = r'''
const assert=require('node:assert/strict');
let unknownWindow=5;
let parentGone=false;
let popupLive=true;
let removed=[];
global.chrome={tabs:{query:async()=>[
  ...(parentGone?[]:[{id:1,windowId:5,groupId:-1,
    url:'chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/connect.html?client='+encodeURIComponent(JSON.stringify({name:'fixture'}))},{id:10,windowId:5,groupId:-1}]),
  ...(popupLive?[{id:11,...(parentGone?{}:{openerTabId:10}),windowId:unknownWindow,groupId:-1}]:[])],
  get:async(id)=>{if(parentGone)throw Error('missing');return {id,windowId:5,groupId:-1,
    url:'chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/connect.html?client='+encodeURIComponent(JSON.stringify({name:'fixture'}))};},
  remove:async(ids)=>{removed.push(...ids);parentGone=true;popupLive=true;}},
  windows:{remove:async(id)=>{assert.equal(id,5);removed.push(1,10);parentGone=true;popupLive=true;}},
  debugger:{getTargets:async()=>[]},runtime:{sendMessage:async()=>({connections:[]})}};
process.__epBrowserJob={connector:{evaluate:async(fn,arg)=>await fn(arg)}};
'''
            # Check both same-window and separate-window late popups, even after
            # all saved parent tabs have already disappeared.
            script = (
                fixture
                + "async function run(){"
                + body
                + "}\n"
                + "async function attempt(){const v=await run();"
                + "if(v&&v.refused){assert.deepEqual(removed,[]);throw Error(v.refused);}return v;}\n"
                + r'''
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
            )
            checked = subprocess.run(
                ["node", "-e", script], capture_output=True, text=True, timeout=10
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)

    OLD = {
        "connectorId": 1,
        "windowId": 5,
        "groupId": 7,
        "groupTitle": "fixture",
        "tabIds": [1, 10],
    }
    CONNECTOR_URL = (
        "chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/connect.html?client="
        + "%7B%22name%22%3A%22fixture%22%7D"
    )
    CLEANUP_FIXTURE = r"""
const state=__STATE__;let removed=[];
global.chrome={tabs:{query:async()=>{if(state.lag>0){state.lag--;return state.tabs.concat(state.ghost||[]);}return state.tabs;},
  getCurrent:async()=>({id:state.current||0})},
  windows:{remove:async(id)=>{removed.push(id);state.ghost=state.tabs.filter(t=>t.windowId===id);state.tabs=state.tabs.filter(t=>t.windowId!==id);state.lag=state.lagAfter||0;}},
  tabGroups:{get:async()=>({title:'fixture'})},
  debugger:{getTargets:async()=>(state.attached||[]).map(tabId=>({tabId,attached:true}))},
  runtime:{sendMessage:async()=>({connections:state.connections||[]})}};
process.__epBrowserJob={connector:{evaluate:async(fn,arg)=>await fn(arg)}};
async function attempt(){__BODY__}
attempt().then(v=>({v}),e=>({e:e.message})).then(o=>console.log(JSON.stringify({...o,removed})));
"""

    def refusal_as_error(self, out):
        # The removing phase returns pre-removal refusals instead of throwing,
        # so the caller can restore its issued-removal flag. None may remove.
        refused = out.get("v", {}).get("refused") if isinstance(out.get("v"), dict) else None
        if refused is None:
            return out
        self.assertEqual(out["removed"], [], out)
        return {**{k: v for k, v in out.items() if k != "v"}, "e": refused, "preRemoval": True}

    def failed_cleanup(self, tabs, remove=True, removal_issued=False, pending_since=None, **state):
        body = b.failed_cleanup_js(
            {
                "old": self.OLD,
                "clientName": "fixture",
                "connectorOrigin": b.EXTENSION,
                "removalIssued": removal_issued,
                "pendingSince": pending_since,
            },
            remove,
        )
        script = self.CLEANUP_FIXTURE.replace(
            "__STATE__", json.dumps({"tabs": tabs, **state})
        ).replace("__BODY__", body)
        run = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        return self.refusal_as_error(json.loads(run.stdout))

    def test_missing_connector_with_only_owned_survivor_closes_exact_window(self):
        survivor = [
            {"id": 10, "windowId": 5, "groupId": -1},
            {"id": 50, "windowId": 9, "groupId": -1},
        ]
        out = self.failed_cleanup(survivor)
        self.assertEqual(out["v"], {"closed": True, "count": 1, "connectorMissing": True})
        self.assertEqual(out["removed"], [5])
        # Chrome may list a removed window's tab briefly; the bounded poll waits it out.
        out = self.failed_cleanup(survivor, lagAfter=3)
        self.assertTrue(out["v"]["closed"])
        connector = {"id": 1, "windowId": 5, "groupId": 7, "url": self.CONNECTOR_URL}
        out = self.failed_cleanup([connector, survivor[0]])
        self.assertEqual(out["v"], {"closed": True, "count": 2, "connectorMissing": False})

    def test_hard_killed_relay_leaves_whole_ungrouped_window_closed_by_exact_id(self):
        # After a SIGKILL the extension only ungroups; every saved tab survives.
        # Peer windows, including a peer's ungrouped connector, stay untouched.
        peer_connector = {"id": 70, "windowId": 8, "groupId": -1, "url": self.CONNECTOR_URL}
        tabs = [
            {"id": 1, "windowId": 5, "groupId": -1, "url": self.CONNECTOR_URL},
            {"id": 10, "windowId": 5, "groupId": -1},
            peer_connector,
            {"id": 71, "windowId": 8, "groupId": -1},
            {"id": 80, "windowId": 9, "groupId": 3},
        ]
        out = self.failed_cleanup(tabs, connections=[{"connectedTabIds": [80]}], attached=[80])
        self.assertEqual(out["v"], {"closed": True, "count": 2, "connectorMissing": False})
        self.assertEqual(out["removed"], [5])

    def test_phase_one_proves_ownership_without_closing(self):
        out = self.failed_cleanup([{"id": 10, "windowId": 5, "groupId": -1}], remove=False)
        self.assertTrue(out["v"]["ready"])
        self.assertEqual(out["removed"], [])

    def test_extra_claimed_or_missing_work_page_is_preserved(self):
        survivor = {"id": 10, "windowId": 5, "groupId": -1}
        cases = [
            (
                [survivor, {"id": 99, "windowId": 5, "groupId": -1}],
                {},
                "uncheckpointed_page_arrival",
            ),
            (
                [survivor, {"id": 98, "windowId": 9, "groupId": -1, "openerTabId": 10}],
                {},
                "uncheckpointed_page_arrival",
            ),
            ([survivor], {"attached": [10]}, "ownership_changed"),
            ([survivor], {"connections": [{"connectedTabIds": [10]}]}, "ownership_changed"),
            ([{**survivor, "windowId": 6}], {}, "ownership_changed"),
            (
                [{"id": 1, "windowId": 5, "groupId": 7, "url": self.CONNECTOR_URL}],
                {},
                "saved_owned_tab_missing",
            ),
            ([], {}, "saved_owned_tab_missing"),
        ]
        for tabs, state, expected in cases:
            with self.subTest(expected=expected, tabs=tabs, state=state):
                out = self.failed_cleanup(tabs, **state)
                self.assertEqual(out.get("e"), expected)
                self.assertEqual(out["removed"], [])

    def test_window_already_closed_by_issued_removal_is_idempotent(self):
        out = self.failed_cleanup([{"id": 50, "windowId": 9, "groupId": -1}], removal_issued=True)
        self.assertEqual(out["v"], {"closed": True, "count": 0, "alreadyClosed": True})
        self.assertEqual(out["removed"], [])
        stray = [{"id": 99, "windowId": 5, "groupId": -1}]
        self.assertEqual(
            self.failed_cleanup(stray, removal_issued=True)["e"], "uncheckpointed_page_arrival"
        )

    def test_pending_inventory_reconciles_only_below_its_watermark(self):
        # Job 185ec5ed: post-click verification failed, the connector was gone
        # and only the saved working page survived in the saved window.
        maintenance = {"id": 200, "windowId": 20, "groupId": -1}
        peer = {"id": 50, "windowId": 9, "groupId": -1}
        survivor = {"id": 10, "windowId": 5, "groupId": -1}
        out = self.failed_cleanup([survivor, peer, maintenance], pending_since=60, current=200)
        self.assertEqual(out["v"], {"closed": True, "count": 1, "connectorMissing": True})
        self.assertEqual(out["removed"], [5])
        cases = [
            # Extra tab in the owned window.
            [survivor, {"id": 61, "windowId": 5, "groupId": -1}],
            # Popup descendant in another window.
            [survivor, {"id": 62, "windowId": 9, "groupId": -1, "openerTabId": 10}],
            # Orphan born after the watermark whose opener is already gone.
            [survivor, {"id": 63, "windowId": 9, "groupId": -1}],
        ]
        for tabs in cases:
            with self.subTest(tabs=tabs):
                out = self.failed_cleanup(tabs + [maintenance], pending_since=60, current=200)
                self.assertEqual(out.get("e"), "uncheckpointed_page_arrival")
                self.assertEqual(out["removed"], [])
        # Without a pending call the same orphan is outside this job's proof.
        out = self.failed_cleanup(cases[2] + [maintenance], current=200)
        self.assertTrue(out["v"]["closed"])

    def test_snapshot_records_the_newest_tab_watermark(self):
        source = (SCRIPTS / "owned_pages.js").read_text()
        fixture = r'''
const assert=require('node:assert/strict');
let current;const tabs=new Map();const pages=[];
function page(id){const tab={id,windowId:5,groupId:7,url:'about:blank'};tabs.set(id,tab);
  const p={id,closed:false,context:()=>context,isClosed:()=>p.closed,opener:async()=>null,url:()=>tab.url,
    evaluate:async(fn,arg)=>{current=p;return await fn(arg);}};pages.push(p);return p;}
const context={pages:()=>pages.filter(p=>!p.closed)};
global.chrome={tabs:{create:async(args)=>{page(10);const t=tabs.get(10);t.url=args.url;return t;},
  group:async({tabIds,groupId})=>{for(const id of tabIds)tabs.get(id).groupId=groupId;},
  getCurrent:async()=>tabs.get(current.id),get:async(id)=>tabs.get(id),
  query:async(q)=>[...tabs.values()].filter(t=>(q.windowId===undefined||t.windowId===q.windowId)&&(q.groupId===undefined||t.groupId===q.groupId))},
  tabGroups:{get:async()=>({title:'fixture'})}};
(async()=>{const s=await newOwnedState(page(1));s.task=await s.create();
  tabs.set(77,{id:77,windowId:9,groupId:-1}); // A peer's tab in another window.
  const m=await s.snapshot();assert.deepEqual(m.tabIds,[1,10]);assert.equal(m.newestTabId,77);
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        checked = subprocess.run(
            ["node", "-e", source + fixture], capture_output=True, text=True, timeout=10
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def full_job(self, route, status="failed"):
        job = {
            "job_id": "d" * 32,
            "label": "fixture",
            "status": status,
            "client_name": "fixture",
            "generation": route.preflight(),
            "metadata": {**self.OLD, "unboundOwnedPages": 0},
            "updated": 0,
            "ownership_pending": False,
            "client": None,
            "lock": threading.RLock(),
        }
        return job

    def test_failed_cleanup_records_removal_before_closing_and_settles_closed(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = self.full_job(route)
            route.save(job)
            receipt = Path(root) / (job["job_id"] + ".json")
            seen = []

            def fake(_, body):
                if "async({old,clientName," in body:
                    removing = '"remove": true' in body
                    seen.append(
                        (removing, json.loads(receipt.read_text()).get("window_removal_issued"))
                    )
                    return (
                        {"closed": True, "count": 1}
                        if removing
                        else {"ready": True, "count": 1, "proof": "a" * 64, "peerIds": []}
                    )
                if "maintenance_window_not_exclusive" in body:
                    return {"windowId": 77, "closed": True}
                return {"ready": True}

            with (
                patch.object(
                    route, "client", create=True, return_value=SimpleNamespace(close=lambda: None)
                ),
                patch.object(b, "code", side_effect=fake),
                patch.object(b, "verify_window_closed") as verified,
                patch.object(b.time, "sleep"),
            ):
                route.finish(job)
            self.assertEqual(seen, [(False, None), (True, True)])
            # The maintenance window proves its own closure by its page close event.
            self.assertEqual([c.args[0] for c in verified.call_args_list], [5])
            row = json.loads(receipt.read_text())
            self.assertEqual((row["status"], row["window_disposition"]), ("finished", "closed"))

    def test_retargeted_connector_with_unchanged_ids_changes_the_proof(self):
        # Tab IDs, windows and groups stay identical; only the connector URL
        # moves to another client between the proof read and the re-read.
        fixture = self.CLEANUP_FIXTURE.replace(
            "tabs:{query:async()=>{",
            "tabs:{query:async()=>{state.reads=(state.reads||0)+1;"
            "if(state.reads===state.flipAt){for(const t of state.tabs)if(t.id===1)t.url=state.flipUrl;}",
        )
        tabs = [
            {"id": 1, "windowId": 5, "groupId": 7, "url": self.CONNECTOR_URL},
            {"id": 10, "windowId": 5, "groupId": 7},
        ]
        for remove in (False, True):
            with self.subTest(remove=remove):
                body = b.failed_cleanup_js(
                    {
                        "old": self.OLD,
                        "clientName": "fixture",
                        "connectorOrigin": b.EXTENSION,
                        "removalIssued": False,
                        "pendingSince": None,
                    },
                    remove,
                )
                state = {
                    "tabs": tabs,
                    "flipAt": 2,
                    "flipUrl": self.CONNECTOR_URL.replace("fixture", "other"),
                }
                script = fixture.replace("__STATE__", json.dumps(state)).replace("__BODY__", body)
                run = subprocess.run(
                    ["node", "-e", script], capture_output=True, text=True, timeout=10
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                out = self.refusal_as_error(json.loads(run.stdout))
                self.assertEqual(out.get("e"), "cleanup_proof_changed", out)
                self.assertEqual(out["removed"], [])

    def removal_route(self, root, removing_reply):
        route = self.route(root)
        job = self.full_job(route)
        route.save(job)
        receipt = Path(root) / (job["job_id"] + ".json")
        seen = []

        def fake(_, body):
            if "async({old,clientName," in body:
                removing = '"remove": true' in body
                seen.append(
                    (removing, json.loads(receipt.read_text()).get("window_removal_issued"))
                )
                if removing:
                    return removing_reply
                return {"ready": True, "count": 1, "proof": "a" * 64, "peerIds": []}
            if "maintenance_window_not_exclusive" in body:
                return {"windowId": 77, "closed": True}
            return {"ready": True}

        return route, job, receipt, seen, fake

    def test_pre_removal_refusal_restores_the_issued_removal_flag(self):
        for reply, expected, prior in (
            ({"refused": "cleanup_proof_changed"}, "cleanup_proof_changed", None),
            ({"refused": "uncheckpointed_page_arrival"}, "uncheckpointed_page_arrival", None),
            ({"refused": "TypeError: CANARY"}, "cleanup_precheck_failed", None),
            ({"refused": "cleanup_proof_changed"}, "cleanup_proof_changed", True),
        ):
            with self.subTest(reply=reply, prior=prior), tempfile.TemporaryDirectory() as root:
                route, job, receipt, seen, fake = self.removal_route(root, reply)
                if prior:
                    job["window_removal_issued"] = True
                    route.save(job)
                with (
                    patch.object(
                        route,
                        "client",
                        create=True,
                        return_value=SimpleNamespace(close=lambda: None),
                    ),
                    patch.object(b, "code", side_effect=fake),
                    patch.object(b, "verify_window_closed"),
                    patch.object(b.time, "sleep"),
                ):
                    with self.assertRaisesRegex(Refusal, "^" + expected + "$"):
                        route.dispose_failed(job)
                # Set only for the removing call itself, then put back.
                self.assertEqual(seen, [(False, prior), (True, True)])
                row = json.loads(receipt.read_text())
                self.assertEqual(row.get("window_removal_issued"), prior)
                self.assertEqual(job.get("window_removal_issued"), prior)
                self.assertNotEqual(row.get("window_disposition"), "closed")
                self.assertNotIn("CANARY", receipt.read_text())

    def contended_route(self, root):
        import fcntl

        route, job, receipt, seen, fake = self.removal_route(root, {"closed": True, "count": 1})
        route.jobs[job["job_id"]] = job
        peer = {"fd": None, "contend": True}

        def phase_one_then_hold(client, body):
            out = fake(client, body)
            if "async({old,clientName," in body and peer["contend"] and peer["fd"] is None:
                # A peer takes receipts.lock between the phases and keeps it
                # until after the caller has returned.
                fd = os.open(Path(root) / "receipts.lock", os.O_CREAT | os.O_RDWR, 0o600)
                fcntl.flock(fd, fcntl.LOCK_EX)
                peer["fd"] = fd
                peer["receipt"] = receipt.read_bytes()
            return out

        def release():
            if peer["fd"] is not None:
                fcntl.flock(peer["fd"], fcntl.LOCK_UN)
                os.close(peer["fd"])
                peer["fd"] = None
            peer["contend"] = False

        patches = contextlib.ExitStack()
        patches.enter_context(
            patch.object(
                route, "client", create=True, return_value=SimpleNamespace(close=lambda: None)
            )
        )
        patches.enter_context(patch.object(b, "code", side_effect=phase_one_then_hold))
        patches.enter_context(patch.object(b, "verify_window_closed"))
        patches.enter_context(patch.object(b, "RECEIPTS_LOCK_TIMEOUT", 0.3))
        return route, job, receipt, seen, peer, release, patches

    def assert_contended_refusal(self, receipt, seen, peer, elapsed):
        # One bound plus slack, while the peer still holds the lock, and no
        # write at all once the peer took it.
        self.assertLess(elapsed, 0.3 + 1.0)
        self.assertEqual(seen, [(False, None)])
        self.assertEqual(receipt.read_bytes(), peer["receipt"])
        row = json.loads(receipt.read_text())
        self.assertEqual(row["status"], "failed")
        self.assertNotIn("window_removal_issued", row)
        self.assertNotIn("window_disposition", row)

    def test_real_finish_returns_after_one_bound_while_peer_holds_receipts_lock(self):
        with tempfile.TemporaryDirectory() as root:
            route, job, receipt, seen, peer, release, patches = self.contended_route(root)
            with patches:
                try:
                    started = time.monotonic()
                    with self.assertRaisesRegex(Refusal, "^receipts_lock_busy$"):
                        route.call("browser_job_finish", {"job_id": job["job_id"]})
                    elapsed = time.monotonic() - started
                    self.assertIsNotNone(peer["fd"])
                    self.assert_contended_refusal(receipt, seen, peer, elapsed)
                    self.assertNotEqual(job["status"], "finished")
                    self.assertNotIn("window_removal_issued", job)
                    self.assertEqual(
                        job["timings"][-1]["stages"][-1][0], "failed:receipts_lock_busy"
                    )
                finally:
                    release()
                # Once the peer is gone the same job retries and settles closed.
                seen.clear()
                route.call("browser_job_finish", {"job_id": job["job_id"]})
            self.assertEqual(seen, [(False, None), (True, True)])
            row = json.loads(receipt.read_text())
            self.assertEqual((row["status"], row["window_disposition"]), ("finished", "closed"))
            self.assertIs(row["ownership_pending"], False)

    def test_real_recover_returns_after_one_bound_while_peer_holds_receipts_lock(self):
        with tempfile.TemporaryDirectory() as root:
            route, job, receipt, seen, peer, release, patches = self.contended_route(root)
            route.connect = lambda _: self.fail("recover must not reconnect after a refusal")
            with patches:
                try:
                    started = time.monotonic()
                    reply = route.call("browser_job_recover", {"job_id": job["job_id"]})
                    elapsed = time.monotonic() - started
                    self.assertIsNotNone(peer["fd"])
                    self.assertTrue(reply.get("isError"), reply)
                    self.assertIn("Recovery refused", decode(reply)["error"])
                    self.assert_contended_refusal(receipt, seen, peer, elapsed)
                    self.assertEqual(job["status"], "failed")
                finally:
                    release()
                seen.clear()
                route.call("browser_job_finish", {"job_id": job["job_id"]})
            self.assertEqual(seen, [(False, None), (True, True)])
            row = json.loads(receipt.read_text())
            self.assertEqual((row["status"], row["window_disposition"]), ("finished", "closed"))

    def reconnect_route(self, root):
        import fcntl

        route, job, receipt, seen, peer, release, patches = self.contended_route(root)
        peer["contend"] = False

        def hold():
            fd = os.open(Path(root) / "receipts.lock", os.O_CREAT | os.O_RDWR, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            peer["fd"] = fd
            peer["receipt"] = receipt.read_bytes()

        return route, job, receipt, peer, hold, release, patches

    def recover_while_held(self, route, job, peer):
        started = time.monotonic()
        reply = route.call("browser_job_recover", {"job_id": job["job_id"]})
        elapsed = time.monotonic() - started
        # Returned within one bound plus slack while the peer still holds it.
        self.assertIsNotNone(peer["fd"])
        self.assertLess(elapsed, 0.3 + 1.0)
        self.assertTrue(reply.get("isError"), reply)
        self.assertIn("Recovery refused", decode(reply)["error"])
        return reply

    def test_recover_reconnect_bootstrap_contention_keeps_the_finished_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            route, job, receipt, peer, hold, release, patches = self.reconnect_route(root)
            entries = []
            real_bootstrap = route.bootstrap

            @contextlib.contextmanager
            def bootstrap():
                with real_bootstrap():
                    entries.append(True)
                    if len(entries) == 2:
                        hold()
                    yield

            route.bootstrap = bootstrap
            route.connect = lambda _: self.fail("no connection after a refused starting save")
            with patches:
                try:
                    self.recover_while_held(route, job, peer)
                    self.assertEqual(receipt.read_bytes(), peer["receipt"])
                finally:
                    release()
            row = json.loads(receipt.read_text())
            self.assertEqual((row["status"], row["window_disposition"]), ("finished", "closed"))
            # Memory agrees with disk: the old pages closed and nothing new exists.
            self.assertEqual(job["status"], "finished")
            self.assertEqual(job["metadata"], row["metadata"])
            self.assertIsNone(job["client"])
            with self.assertRaisesRegex(Refusal, "only_failed_jobs_recover"):
                route.call("browser_job_recover", {"job_id": job["job_id"]})

    def test_recover_contention_inside_new_connection_keeps_exact_ids_durable(self):
        with tempfile.TemporaryDirectory() as root:
            route, job, receipt, peer, hold, release, patches = self.reconnect_route(root)

            def connect(j):
                j["metadata"] = {**self.OLD, "unboundOwnedPages": 0}
                route.checkpoint(j, "connecting")
                hold()
                route.checkpoint(j, "ready")

            route.connect = connect
            with patches:
                try:
                    self.recover_while_held(route, job, peer)
                    self.assertEqual(receipt.read_bytes(), peer["receipt"])
                    row = json.loads(receipt.read_text())
                    # Never ready and never closed: the IDs saved before the
                    # contention remain the exact reconciliation input.
                    self.assertEqual(row["status"], "connecting")
                    self.assertEqual(row["metadata"]["windowId"], self.OLD["windowId"])
                    self.assertNotIn("window_disposition", row)
                    self.assertEqual(job["status"], "failed")
                finally:
                    release()
                route.call("browser_job_finish", {"job_id": job["job_id"]})
            row = json.loads(receipt.read_text())
            self.assertEqual((row["status"], row["window_disposition"]), ("finished", "closed"))

    def test_recover_connection_failure_under_contention_stays_unsettled(self):
        lifecycle_spec = importlib.util.spec_from_file_location(
            "lifecycle_for_recover", SCRIPTS / "browser_lifecycle.py"
        )
        lifecycle = importlib.util.module_from_spec(lifecycle_spec)
        lifecycle_spec.loader.exec_module(lifecycle)
        with tempfile.TemporaryDirectory() as root:
            route, job, receipt, peer, hold, release, patches = self.reconnect_route(root)

            def connect(j):
                hold()
                raise Refusal("connector_identity_unavailable")

            route.connect = connect
            with patches:
                try:
                    self.recover_while_held(route, job, peer)
                    self.assertEqual(receipt.read_bytes(), peer["receipt"])
                    row = json.loads(receipt.read_text())
                    # The creation outcome is unknown: neither settled nor
                    # eligible for the no-artifacts census.
                    self.assertEqual(row["status"], "starting")
                    self.assertIsNone(row["metadata"])
                    self.assertFalse(lifecycle.census_eligible(row))
                    self.assertEqual(job["status"], "failed")
                finally:
                    release()
                reply = route.call("browser_job_recover", {"job_id": job["job_id"]})
            self.assertTrue(reply.get("isError"), reply)
            row = json.loads(receipt.read_text())
            self.assertEqual(row["status"], "failed")
            self.assertNotIn("window_disposition", row)
            self.assertEqual(
                job["timings"][-1]["stages"][-1][0],
                "failed:creation_outcome_unknown_requires_reconciliation",
            )

    def test_uncontended_recover_reports_ready_without_the_old_disposition(self):
        with tempfile.TemporaryDirectory() as root:
            route, job, receipt, peer, hold, release, patches = self.reconnect_route(root)

            def connect(j):
                j["metadata"] = {**self.OLD, "windowId": 6, "unboundOwnedPages": 0}
                route.checkpoint(j, "connecting")
                route.checkpoint(j, "ready")

            route.connect = connect
            with patches:
                reply = route.call("browser_job_recover", {"job_id": job["job_id"]})
            self.assertFalse(reply.get("isError"), reply)
            self.assertTrue(decode(reply)["previous_pages_closed"])
            row = json.loads(receipt.read_text())
            self.assertEqual((row["status"], row["metadata"]["windowId"]), ("ready", 6))
            self.assertNotIn("window_disposition", row)
            self.assertNotIn("window_removal_issued", row)

    def test_destructive_call_timeout_is_bounded_and_restored(self):
        client = SimpleNamespace(timeout=120)
        observed = []
        with patch.object(b, "code", side_effect=lambda c, _: observed.append(c.timeout) or {}):
            b.bounded_code(client, "body", b.DESTRUCTIVE_CALL_TIMEOUT)
            self.assertEqual(observed, [b.DESTRUCTIVE_CALL_TIMEOUT])
            self.assertEqual(client.timeout, 120)
            with patch.object(b, "code", side_effect=RuntimeError("transport")):
                with self.assertRaises(RuntimeError):
                    b.bounded_code(client, "body", 5)
            self.assertEqual(client.timeout, 120)

    def test_diagnostic_route_binds_no_control_socket(self):
        with tempfile.TemporaryDirectory() as root:
            hook = Path(root) / "hook.py"
            hook.write_text("def decide(*_):\n    return None\n")
            state = Path(root) / "state"
            config = {"state_dir": str(state), "headless_hook": str(hook)}
            threads = threading.active_count()
            route = b.Route(config, control=False)
            self.assertIsNone(route.control_socket)
            self.assertIsNone(route.control_listener)
            self.assertEqual(list(state.glob("*.sock")), [])
            self.assertEqual(threading.active_count(), threads)
            route.close_control()
            live = b.Route(config)
            try:
                self.assertEqual(len(list(state.glob("*.sock"))), 1)
            finally:
                live.close_control()
            self.assertEqual(list(state.glob("*.sock")), [])

    def test_post_action_verify_failure_finishes_through_watermarked_reconciliation(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            route.prime = lambda _: None
            job = self.full_job(route, "ready")
            job["metadata"]["newestTabId"] = 60
            job["client"] = SimpleNamespace(
                closed=False,
                close=lambda: setattr(job["client"], "closed", True),
                call=lambda *a: b.result({"clicked": True}),
            )
            route.jobs[job["job_id"]] = job
            route.inventory.append({"name": "browser_click", "inputSchema": {"type": "object"}})
            closed_vendor = {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": "Target page, context or browser has been closed SYNTHETIC_CANARY",
                    }
                ],
            }

            def lost_connector(*_, **__):
                b.projection(closed_vendor)

            route.metadata = lost_connector
            reply = route.call("browser_click", {"job_id": job["job_id"], "ref": "e1"})
            self.assertTrue(reply["isError"])
            receipt = Path(root) / (job["job_id"] + ".json")
            row = json.loads(receipt.read_text())
            self.assertEqual((row["status"], row["ownership_pending"]), ("failed", True))
            self.assertEqual(
                row["timings"][-1]["stages"][-1][0],
                "failed:owned_operation_failed:vendor_target_closed",
            )
            sent = []

            def fake(_, body):
                if "async({old,clientName," in body:
                    sent.append(int(re.search(r'"pendingSince": (\d+)', body).group(1)))
                    return (
                        {"closed": True, "count": 1}
                        if '"remove": true' in body
                        else {"ready": True, "proof": "a" * 64, "peerIds": []}
                    )
                if "maintenance_window_not_exclusive" in body:
                    return {"windowId": 77, "closed": True}
                return {"ready": True}

            with (
                patch.object(
                    route, "client", create=True, return_value=SimpleNamespace(close=lambda: None)
                ),
                patch.object(b, "code", side_effect=fake),
                patch.object(b, "verify_window_closed"),
                patch.object(b.time, "sleep"),
            ):
                route.call("browser_job_finish", {"job_id": job["job_id"]})
            self.assertEqual(sent, [60, 60])
            row = json.loads(receipt.read_text())
            self.assertEqual(
                (row["status"], row["window_disposition"], row["ownership_pending"]),
                ("finished", "closed", False),
            )
            self.assertEqual(
                [s for s, _ in row["timings"][-1]["stages"]],
                [
                    "received",
                    "live_failed:owned_operation_failed:vendor_target_closed",
                    "reconcile_proven",
                    "finished",
                ],
            )
            self.assertNotIn("SYNTHETIC_CANARY", receipt.read_text())

    def test_pending_without_watermark_refuses_and_records_the_step(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = self.full_job(route)
            job["ownership_pending"] = True
            route.jobs[job["job_id"]] = job
            with patch.object(route, "client", create=True) as connect:
                with self.assertRaises(Refusal):
                    route.call("browser_job_finish", {"job_id": job["job_id"]})
            connect.assert_not_called()
            row = json.loads((Path(root) / (job["job_id"] + ".json")).read_text())
            self.assertEqual(row["status"], "failed")
            self.assertEqual(
                [s for s, _ in row["timings"][-1]["stages"]],
                ["received", "failed:uncheckpointed_page_creation_requires_reconciliation"],
            )

    def test_stale_facade_never_reopens_a_settled_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            settled = self.full_job(route, "finished")
            route.save(settled)
            receipt = Path(root) / (settled["job_id"] + ".json")
            before = receipt.read_text()
            stale = self.full_job(route)
            route.checkpoint(stale, "failed")
            self.assertEqual(receipt.read_text(), before)
            self.assertEqual(stale["status"], "finished")
            stale = self.full_job(route)
            closed = []
            stale["client"] = SimpleNamespace(closed=False, close=lambda: closed.append(True))
            with patch.object(route, "dispose_failed") as dispose:
                reply = route.finish(stale)
            dispose.assert_not_called()
            self.assertEqual(closed, [True])
            self.assertEqual(decode(reply)["status"], "finished")
            # Once adopted, the same handle may recover and write again.
            route.checkpoint(stale, "starting")
            self.assertEqual(json.loads(receipt.read_text())["status"], "starting")

    def test_receipt_settled_during_a_stale_write_stays_finished(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            stale = self.full_job(route)
            route.save(stale)
            receipt = Path(root) / (stale["job_id"] + ".json")
            settled = {**json.loads(receipt.read_text()), "status": "finished"}
            settled["window_disposition"] = "closed"
            with b.ledger_lock(root, "receipts.lock"):
                writer = threading.Thread(target=route.checkpoint, args=(stale, "failed"))
                writer.start()
                writer.join(0.3)
                self.assertTrue(writer.is_alive())
                # A peer settles the receipt while the stale write waits.
                receipt.write_text(json.dumps(settled))
            writer.join(5)
            self.assertEqual(json.loads(receipt.read_text()), settled)
            self.assertEqual(stale["status"], "finished")

    def test_receipt_loaded_from_disk_keeps_its_owning_facade_socket(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            route.control_socket = "control-" + "1" * 16 + ".sock"
            fresh = self.full_job(route)
            route.save(fresh)
            receipt = Path(root) / (fresh["job_id"] + ".json")
            self.assertEqual(
                json.loads(receipt.read_text())["control_socket"], route.control_socket
            )
            loaded = {**json.loads(receipt.read_text()), "client": None}
            sweeper = self.route(root)
            sweeper.control_socket = "control-" + "2" * 16 + ".sock"
            sweeper.checkpoint(loaded, "failed")
            self.assertEqual(
                json.loads(receipt.read_text())["control_socket"], route.control_socket
            )

    DIAGNOSTICS_FIXTURE = r"""
const state=__STATE__;const calls=[];
const fail=name=>{calls.push(name);throw Error('SYNTHETIC_CANARY '+name);};
global.chrome={tabs:{query:async()=>{calls.push('tabs.query');return state.tabs;}},
  runtime:{sendMessage:async(m)=>{if(state.statusFails)fail('runtime.sendMessage');calls.push('runtime.sendMessage:'+m.type);if(m.type==='getStatus')return state.sessions?{success:true,sessions:state.sessions}:undefined;return {connections:state.connections||[]};}},
  debugger:{getTargets:async()=>{if(state.targetsFail)fail('debugger.getTargets');calls.push('debugger.getTargets');return (state.attached||[]).map(tabId=>({tabId,attached:true}));}}};
process.__epBrowserJob={connector:{evaluate:async(fn,arg)=>await fn(arg)}};
async function attempt(){__BODY__}
attempt().then(v=>({v}),e=>({e:e.message})).then(o=>console.log(JSON.stringify({...o,calls})));
"""

    def diagnostics(self, reason="unknown", **state):
        body = b.connection_diagnostics_js({"connectorId": 1, "tabIds": [1, 10]}, "fixture", reason)
        script = self.DIAGNOSTICS_FIXTURE.replace("__STATE__", json.dumps(state)).replace(
            "__BODY__", body
        )
        run = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        return self.refusal_as_error(json.loads(run.stdout))

    def test_connection_diagnostics_read_only_the_owned_scope(self):
        owned = [{"id": 1, "windowId": 5, "url": self.CONNECTOR_URL}, {"id": 10, "windowId": 5}]
        peer = [{"id": 70, "windowId": 8, "url": self.CONNECTOR_URL}, {"id": 71, "windowId": 8}]
        peer_connection = {
            "id": "p",
            "clientName": "EP peer [00000000]",
            "connectedTabIds": [70, 71],
        }
        cases = [
            (
                "healthy connection",
                {
                    "tabs": owned + peer,
                    "connections": [
                        {"id": "o", "clientName": "fixture", "connectedTabIds": [1, 10]},
                        peer_connection,
                    ],
                    "attached": [1, 10, 70, 71],
                },
                "unknown",
                ("yes", "yes", {"1": "yes", "10": "yes"}, "unknown", []),
            ),
            (
                # A peer that claims an owned ID never counts as this job's connection.
                "peer claims and attaches owned ids",
                {
                    "tabs": owned + peer,
                    "connections": [{**peer_connection, "connectedTabIds": [1, 10, 70]}],
                    "attached": [70],
                },
                "all_controlled_tabs_detached",
                ("yes", "no", {"1": "no", "10": "no"}, "all_controlled_tabs_detached", []),
            ),
            (
                "connector tab gone",
                {"tabs": owned[1:] + peer, "connections": [peer_connection], "attached": [70]},
                "unknown",
                ("no", "no", {"1": "no", "10": "no"}, "connector_closed", []),
            ),
            (
                "reported reason wins over derivation",
                {"tabs": owned[1:], "connections": []},
                "user_disconnect",
                ("no", "no", {"1": "no", "10": "no"}, "user_disconnect", []),
            ),
            (
                "extension reads fail",
                {"tabs": owned, "statusFails": True, "targetsFail": True},
                "unknown",
                (
                    "yes",
                    "unknown",
                    {"1": "unknown", "10": "unknown"},
                    "unknown",
                    [
                        "diagnostics_unavailable:connection_status",
                        "diagnostics_unavailable:debugger_targets",
                    ],
                ),
            ),
        ]
        for name, state, reason, expected in cases:
            with self.subTest(name):
                out = self.diagnostics(reason, **state)
                v = out["v"]
                self.assertEqual(
                    (
                        v["connector_present"],
                        v["connection_lists_owned_tabs"],
                        v["debugger_attached"],
                        v["close_reason"],
                        v["unavailable"],
                    ),
                    expected,
                )
                self.assertEqual(
                    set(v),
                    {
                        "connector_present",
                        "connection_lists_owned_tabs",
                        "debugger_attached",
                        "close_reason",
                        "unavailable",
                    },
                )
                # Only reads; any select, attach, update or close call would throw.
                self.assertTrue(
                    set(out["calls"])
                    <= {
                        "tabs.query",
                        "runtime.sendMessage:getConnectionStatus",
                        "runtime.sendMessage:getStatus",
                        "runtime.sendMessage",
                        "debugger.getTargets",
                    }
                )
                self.assertNotIn("SYNTHETIC_CANARY", json.dumps(v))
                self.assertNotIn("connect.html", json.dumps(v))

    def test_extension_060_status_sessions_are_normalized(self):
        for ids, expected in (([1, 10], "yes"), ([70], "no"), (None, "no")):
            with self.subTest(ids=ids):
                out = self.diagnostics(
                    tabs=[{"id": 1}],
                    sessions=[{"clientName": "fixture", "tabIds": ids}],
                )
                self.assertEqual(out["v"]["connection_lists_owned_tabs"], expected)
                self.assertIn("runtime.sendMessage:getStatus", out["calls"])
                self.assertNotIn("runtime.sendMessage:getConnectionStatus", out["calls"])

    def test_connector_adoption_changes_only_one_owned_blank_page(self):
        for urls, expected in (
            (["about:blank"], True),
            ([self.CONNECTOR_URL], False),
            (["https://fixture.invalid"], False),
            (["about:blank", "about:blank"], False),
        ):
            with self.subTest(urls=urls):
                source = (
                    "const urls=" + json.dumps(urls) + ";const navigations=[];"
                    "const page={context:()=>({pages:()=>urls}),url:()=>urls[0],"
                    "goto:async u=>navigations.push(u),"
                    "evaluate:async(fn,arg)=>labels.push(arg)};const labels=[];"
                    "async function run(){"
                    + b.adopt_connector_js('EP test "quoted"')
                    + "}run().then(result=>console.log(JSON.stringify({result,navigations,labels})));"
                )
                run = subprocess.run(
                    ["node", "-e", source], capture_output=True, text=True, timeout=10
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                out = json.loads(run.stdout)
                self.assertEqual(out["result"], {"adopted": expected})
                if expected:
                    from urllib.parse import parse_qs, urlparse

                    url = urlparse(out["navigations"][0])
                    self.assertEqual(url.scheme + "://" + url.netloc + url.path, b.EXTENSION)
                    self.assertEqual(
                        parse_qs(url.query), {"client": ['{"name": "EP test \\"quoted\\""}']}
                    )
                    self.assertEqual(out["labels"], ['EP test "quoted"'])
                else:
                    self.assertEqual(out["navigations"], [])
                    self.assertEqual(out["labels"], [])

    def test_close_reason_comes_only_from_the_relay_wording(self):
        def failing(text):
            return {"isError": True, "content": [{"type": "text", "text": text}]}

        closed = "Target page, context or browser has been closed\n"
        for text, expected in (
            (
                closed + "Extension disconnected: All controlled tabs detached",
                "all_controlled_tabs_detached",
            ),
            ("Extension disconnected before initialization: User disconnected", "user_disconnect"),
            (closed + "page said User disconnected SYNTHETIC_CANARY", "unknown"),
            ("Extension disconnected: SYNTHETIC_CANARY", "unknown"),
            (closed, "unknown"),
        ):
            with self.subTest(expected=expected, text=text):
                with self.assertRaises(Refusal) as raised:
                    b.projection(failing(text))
                self.assertEqual(raised.exception.close_reason, expected)

    def diagnosed_route(self, root, collected=None, fails=None):
        route = self.route(root)
        job = self.ready_job(route, b.result({"clicked": True}))
        job["metadata"]["tabIds"] = [1, 10]
        lost = {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "Target page, context or browser has been closed\nExtension disconnected: All controlled tabs detached SYNTHETIC_CANARY",
                }
            ],
        }

        def verify(*_, **__):
            b.projection(lost)

        route.metadata = verify
        opened = []

        @contextlib.contextmanager
        def maintenance():
            opened.append(True)
            if fails:
                raise fails
            yield "maintenance"

        route.maintenance_connector = maintenance
        sent = []

        def fake(client, body):
            sent.append((client, body))
            return copy.deepcopy(collected)

        return route, job, opened, sent, fake

    def test_first_failure_records_fixed_connection_diagnostics(self):
        collected = {
            "connector_present": "yes",
            "connection_lists_owned_tabs": "no",
            "debugger_attached": {"1": "no", "10": "no", "70": "yes"},
            "close_reason": "all_controlled_tabs_detached",
            "unavailable": ["SYNTHETIC_CANARY"],
            "title": "SYNTHETIC_CANARY",
        }
        with tempfile.TemporaryDirectory() as root:
            route, job, opened, sent, fake = self.diagnosed_route(root, collected)
            with (
                patch.object(b, "code", side_effect=fake),
                patch.object(b.time, "time", return_value=1234.5),
            ):
                reply = route.call(
                    "browser_navigate", {"job_id": job["job_id"], "url": "https://example.com/"}
                )
            self.assertEqual(decode(reply)["status"], "failed")
            receipt = (Path(root) / (job["job_id"] + ".json")).read_text()
            row = json.loads(receipt)
            self.assertEqual(
                row["connection_diagnostics"],
                {
                    "first_failure": {
                        "stage": "post_call",
                        "at": 1234.5,
                        "connector_present": "yes",
                        "connection_lists_owned_tabs": "no",
                        "debugger_attached": {"1": "no", "10": "no"},
                        "close_reason": "all_controlled_tabs_detached",
                        "unavailable": [],
                    }
                },
            )
            # Diagnostics add no timing stage and do not change the outcome.
            self.assertEqual(
                [s for s, _ in row["timings"][-1]["stages"]],
                [
                    "received",
                    "tool_start",
                    "tool_end",
                    "failed:owned_operation_failed:vendor_target_closed",
                ],
            )
            self.assertEqual(row["status"], "failed")
            self.assertEqual(opened, [True])
            self.assertEqual([c for c, _ in sent], ["maintenance"])
            body = sent[0][1]
            self.assertIn('"clientName": "fixture"', body)
            self.assertIn('"tabIds": [1, 10]', body)
            self.assertNotIn("SYNTHETIC_CANARY", receipt)
            # A later failure on the same connection keeps the first snapshot.
            job["status"] = "ready"
            with patch.object(b, "code", side_effect=fake):
                route.call(
                    "browser_navigate", {"job_id": job["job_id"], "url": "https://example.com/"}
                )
            self.assertEqual(opened, [True])
            self.assertEqual(job["connection_diagnostics"]["first_failure"]["at"], 1234.5)

    def test_diagnostics_collection_failure_records_a_static_code(self):
        for fails, code in (
            (RuntimeError("SYNTHETIC_CANARY"), "collection_failed"),
            (None, "generation_changed"),
        ):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as root:
                route, job, opened, _, fake = self.diagnosed_route(root, {}, fails)
                if code == "generation_changed":
                    route.preflight = lambda: {"pid": 9, "started": "other"}
                with patch.object(b, "code", side_effect=fake):
                    reply = route.call(
                        "browser_navigate", {"job_id": job["job_id"], "url": "https://example.com/"}
                    )
                self.assertEqual(decode(reply)["status"], "failed")
                receipt = (Path(root) / (job["job_id"] + ".json")).read_text()
                snap = json.loads(receipt)["connection_diagnostics"]["first_failure"]
                self.assertEqual(snap["unavailable"], ["diagnostics_unavailable:" + code])
                self.assertEqual(
                    (
                        snap["connector_present"],
                        snap["connection_lists_owned_tabs"],
                        snap["debugger_attached"],
                    ),
                    ("unknown", "unknown", {"1": "unknown", "10": "unknown"}),
                )
                self.assertNotIn("SYNTHETIC_CANARY", receipt)
                self.assertEqual(opened, [True] if fails else [])

    def test_failed_disposal_keeps_the_detach_reason_in_reconciliation(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = self.full_job(route)
            job["client"] = SimpleNamespace(
                closed=False, close=lambda: setattr(job["client"], "closed", True)
            )
            route.jobs[job["job_id"]] = job
            lost = Refusal("owned_operation_failed:vendor_target_closed")
            lost.close_reason = "user_disconnect"
            route.dispose_live = lambda _: (_ for _ in ()).throw(lost)
            sent = []

            def fake(_, body):
                if "connection_lists_owned_tabs" in body:
                    sent.append(body)
                    return {
                        "connector_present": "no",
                        "connection_lists_owned_tabs": "no",
                        "debugger_attached": {"1": "no", "10": "unknown"},
                        "close_reason": "user_disconnect",
                        "unavailable": ["diagnostics_unavailable:debugger_targets"],
                    }
                if "async({old,clientName," in body:
                    return (
                        {"closed": True, "count": 1}
                        if '"remove": true' in body
                        else {"ready": True, "proof": "a" * 64, "peerIds": []}
                    )
                if "maintenance_window_not_exclusive" in body:
                    return {"windowId": 77, "closed": True}
                return {"ready": True}

            with (
                patch.object(
                    route, "client", create=True, return_value=SimpleNamespace(close=lambda: None)
                ),
                patch.object(b, "code", side_effect=fake),
                patch.object(b, "verify_window_closed"),
                patch.object(b.time, "sleep"),
            ):
                route.call("browser_job_finish", {"job_id": job["job_id"]})
            self.assertEqual(len(sent), 1)
            self.assertIn('"reason": "user_disconnect"', sent[0])
            row = json.loads((Path(root) / (job["job_id"] + ".json")).read_text())
            snap = row["connection_diagnostics"]["dispose_failed"]
            self.assertEqual(
                (
                    snap["stage"],
                    snap["close_reason"],
                    snap["connector_present"],
                    snap["debugger_attached"],
                    snap["unavailable"],
                ),
                (
                    "reconcile",
                    "user_disconnect",
                    "no",
                    {"1": "no", "10": "unknown"},
                    ["diagnostics_unavailable:debugger_targets"],
                ),
            )
            self.assertEqual(row["status"], "finished")
            self.assertEqual(
                [s for s, _ in row["timings"][-1]["stages"]],
                [
                    "received",
                    "live_failed:owned_operation_failed:vendor_target_closed",
                    "reconcile_proven",
                    "finished",
                ],
            )

    def test_refused_reconciliation_still_records_diagnostics_without_a_connector(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = self.full_job(route)
            job["ownership_pending"] = True
            job["connection_diagnostics"] = {
                "first_failure": {"stage": "tool", "close_reason": "all_controlled_tabs_detached"}
            }
            route.jobs[job["job_id"]] = job
            with patch.object(route, "client", create=True) as connect:
                with self.assertRaises(Refusal):
                    route.call("browser_job_finish", {"job_id": job["job_id"]})
            connect.assert_not_called()
            row = json.loads((Path(root) / (job["job_id"] + ".json")).read_text())
            snap = row["connection_diagnostics"]["dispose_failed"]
            self.assertEqual(
                (snap["stage"], snap["close_reason"], snap["unavailable"]),
                (
                    "dispose_failed",
                    "all_controlled_tabs_detached",
                    ["diagnostics_unavailable:reconciliation_refused"],
                ),
            )

    def test_downstream_error_keeps_only_a_static_owned_code(self):
        def failing(text):
            return {"isError": True, "content": [{"type": "text", "text": text}]}

        with self.assertRaises(Refusal) as known:
            b.projection(failing("### Error\nError: saved_owned_tab_missing\n at SYNTHETIC_CANARY"))
        self.assertEqual(str(known.exception), "owned_operation_failed:saved_owned_tab_missing")
        with self.assertRaises(Refusal) as unknown:
            b.projection(failing("page said SYNTHETIC_CANARY"))
        self.assertEqual(str(unknown.exception), "owned_operation_failed")

    def ready_job(self, route, reply):
        job = {
            "job_id": "e" * 32,
            "label": "fixture",
            "client_name": "fixture",
            "generation": route.preflight(),
            "metadata": route.metadata(None),
            "updated": 0,
            "lock": threading.RLock(),
            "status": "ready",
            "client": SimpleNamespace(call=lambda *a: copy.deepcopy(reply)),
        }
        route.jobs[job["job_id"]] = job
        return job

    def working_page_after(self, route, state):
        base = route.metadata(None)
        route.metadata = lambda _, strict=True: {**base, "workingPage": state}

    def test_vendor_error_that_loses_the_working_page_fails_the_job(self):
        # Job cd3aebeb: the Instagram navigate returned a vendor TargetClosedError
        # while the connector, window, group and tab IDs all survived.
        vendor = {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "### Error\nError: browserBackend.callTool: Target page, context or browser has been closed SYNTHETIC_CANARY",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = self.ready_job(route, vendor)
            self.working_page_after(route, "closed")
            reply = route.call(
                "browser_navigate", {"job_id": job["job_id"], "url": "https://www.instagram.com/"}
            )
            self.assertTrue(reply["isError"])
            texts = [b["text"] for b in reply["content"]]
            self.assertIn("SYNTHETIC_CANARY", texts[0])  # The caller still sees the vendor reply.
            self.assertEqual(texts[1:], [b.VENDOR_ERROR_NOTE, b.WORKING_PAGE_LOST_NOTE])
            receipt = (Path(root) / (job["job_id"] + ".json")).read_text()
            row = json.loads(receipt)
            self.assertEqual((row["status"], row["ownership_pending"]), ("failed", False))
            self.assertEqual(
                [s for s, _ in row["timings"][-1]["stages"]][-4:],
                [
                    "tool_end",
                    "vendor_error:vendor_target_closed",
                    "post_metadata",
                    "failed:working_page_lost",
                ],
            )
            self.assertNotIn("workingPage", row["metadata"])
            self.assertNotIn("SYNTHETIC_CANARY", receipt)
            # The failed job refuses further work, so nothing is replayed.
            route.prime = b.Route.prime.__get__(route)
            job["client"] = SimpleNamespace(call=lambda *a: self.fail("replayed"))
            again = route.call(
                "browser_navigate", {"job_id": job["job_id"], "url": "https://www.instagram.com/"}
            )
            self.assertEqual(decode(again)["status"], "failed")
            row = json.loads((Path(root) / (job["job_id"] + ".json")).read_text())
            self.assertEqual(
                row["timings"][-1]["stages"][-1][0], "failed:job_not_ready_finish_or_recover"
            )

    def test_page_lost_after_a_successful_reply_still_fails_the_job(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = self.ready_job(route, b.result({"navigated": True}))
            self.working_page_after(route, "closed")
            reply = route.call(
                "browser_navigate", {"job_id": job["job_id"], "url": "https://www.instagram.com/"}
            )
            self.assertFalse(reply.get("isError"))
            self.assertEqual(reply["content"][-1]["text"], b.WORKING_PAGE_LOST_NOTE)
            row = json.loads((Path(root) / (job["job_id"] + ".json")).read_text())
            self.assertEqual(row["status"], "failed")
            self.assertEqual(
                [s for s, _ in row["timings"][-1]["stages"]][-3:],
                ["tool_end", "post_metadata", "failed:working_page_lost"],
            )

    def test_reannounced_navigation_page_is_bound_only_after_origin_policy(self):
        candidate = {"targetId": "replacement", "origin": "https://login.example.com"}
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = self.ready_job(route, b.result({"navigated": True}))
            job["chooser_connector_index"] = 0
            self.working_page_after(route, "live")
            routed = []
            job["client"].call = lambda _, req: routed.append(req["name"]) or b.result({})
            checked = []
            route.guard.decide = lambda req: checked.append(req["tool_input"]["url"])
            with patch.object(b, "code", side_effect=[{"candidate": candidate}] * 2) as code:
                reply = route.call(
                    "browser_navigate", {"job_id": job["job_id"], "url": "https://example.com/"}
                )
            self.assertEqual(checked, ["https://example.com/", "https://login.example.com/"])
            self.assertEqual(routed, ["browser_navigate", "browser_tabs"])
            self.assertIn("was not replayed", reply["content"][-1]["text"])
            self.assertEqual(job["status"], "ready")
            self.assertIn('"targetId": "replacement"', code.call_args.args[1])
            self.assertNotIn("replacement", (Path(root) / (job["job_id"] + ".json")).read_text())

    def test_click_that_leaves_the_origin_rebinds_the_owned_tab(self):
        # Job 0b384cad: a click inside browser_run_code_unsafe sent the owned
        # tab to PayPal, Chrome swapped its target and the Page closed.
        candidate = {"targetId": "replacement", "origin": "https://www.paypal.com"}
        vendor = {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "### Error\nError: browserBackend.callTool: Target page, context or browser has been closed",
                }
            ],
        }
        for name, args in (
            ("browser_run_code_unsafe", {"code": "async (page) => page.click('#pay')"}),
            ("browser_click", {"element": "Pay", "ref": "e9"}),
        ):
            with self.subTest(tool=name), tempfile.TemporaryDirectory() as root:
                route = self.route(root)
                route.inventory.append({"name": name, "inputSchema": {"type": "object"}})
                job = self.ready_job(route, vendor)
                job["client"].call = lambda _, req, tool=name: (
                    copy.deepcopy(vendor) if req["name"] == tool else b.result({})
                )
                job["chooser_connector_index"] = 0
                # Right after the call, then after the rebind.
                states = iter(["closed", "live"])
                base = route.metadata(None)
                route.metadata = lambda _, strict=True: {**base, "workingPage": next(states)}
                checked = []
                route.guard.decide = lambda req: checked.append(req["tool_input"].get("url"))
                with patch.object(b, "code", side_effect=[{"candidate": candidate}] * 2):
                    reply = route.call(name, {"job_id": job["job_id"], **args})
                self.assertIn("https://www.paypal.com/", checked)
                self.assertEqual(reply["content"][-1]["text"], b.NAVIGATION_REBOUND_NOTE)
                self.assertEqual(job["status"], "ready")
                row = json.loads((Path(root) / (job["job_id"] + ".json")).read_text())
                stages = [s for s, _ in row["timings"][-1]["stages"]]
                self.assertIn("owned_navigation_page_rebound", stages)
                self.assertNotIn("failed:working_page_lost", stages)

    def test_click_without_a_proven_replacement_still_fails_the_job(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            route.inventory.append({"name": "browser_click", "inputSchema": {"type": "object"}})
            job = self.ready_job(route, b.result({}))
            job["chooser_connector_index"] = 0
            self.working_page_after(route, "closed")
            with patch.object(b, "code", side_effect=[{"candidate": None}]):
                reply = route.call(
                    "browser_click", {"job_id": job["job_id"], "element": "Pay", "ref": "e9"}
                )
            self.assertEqual(reply["content"][-1]["text"], b.WORKING_PAGE_LOST_NOTE)
            row = json.loads((Path(root) / (job["job_id"] + ".json")).read_text())
            self.assertEqual(row["status"], "failed")

    def test_navigation_replacement_refuses_denied_or_changed_target(self):
        candidate = {"targetId": "replacement", "origin": "https://login.example.com"}
        for outcome in ("policy", "generation", "changed"):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as root:
                route = self.route(root)
                job = self.ready_job(route, b.result({}))
                job["chooser_connector_index"] = 0
                if outcome == "policy":
                    route.guard.decide = lambda _: ("deny", "use headless")
                elif outcome == "generation":
                    route.preflight = lambda: {"pid": 456}
                with patch.object(
                    b, "code", side_effect=[{"candidate": candidate}, {"candidate": None}]
                ) as calls:
                    with self.assertRaises(Refusal):
                        route.recover_navigation_page(job)
                self.assertEqual(calls.call_count, 2 if outcome == "changed" else 1)

    def test_ordinary_vendor_error_is_labelled_and_the_job_stays_ready(self):
        vendor = {
            "isError": True,
            "content": [{"type": "text", "text": "### Error\nRef e9 not found SYNTHETIC_CANARY"}],
        }
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = self.ready_job(route, vendor)
            self.working_page_after(route, "live")
            reply = route.call(
                "browser_navigate", {"job_id": job["job_id"], "url": "https://example.com/"}
            )
            self.assertTrue(reply["isError"])
            self.assertEqual(reply["content"][-1]["text"], b.VENDOR_ERROR_NOTE)
            receipt = (Path(root) / (job["job_id"] + ".json")).read_text()
            row = json.loads(receipt)
            self.assertEqual(row["status"], "ready")
            self.assertEqual(
                [s for s, _ in row["timings"][-1]["stages"]][-3:],
                ["tool_end", "vendor_error:unclassified", "post_metadata"],
            )
            self.assertNotIn("SYNTHETIC_CANARY", receipt)

    def test_snapshot_reports_a_closed_working_page_whose_tab_survives(self):
        source = (SCRIPTS / "owned_pages.js").read_text()
        fixture = r'''
const assert=require('node:assert/strict');
let current;const tabs=new Map();const pages=[];
function page(id){const tab={id,windowId:5,groupId:7,url:'about:blank'};tabs.set(id,tab);
  const p={id,closed:false,context:()=>context,isClosed:()=>p.closed,opener:async()=>null,url:()=>tab.url,
    evaluate:async(fn,arg)=>{current=p;return await fn(arg);}};pages.push(p);return p;}
const context={pages:()=>pages.filter(p=>!p.closed)};
global.chrome={tabs:{create:async(args)=>{page(10);const t=tabs.get(10);t.url=args.url;return t;},
  group:async({tabIds,groupId})=>{for(const id of tabIds)tabs.get(id).groupId=groupId;},
  getCurrent:async()=>tabs.get(current.id),get:async(id)=>tabs.get(id),
  query:async(q)=>[...tabs.values()].filter(t=>(q.windowId===undefined||t.windowId===q.windowId)&&(q.groupId===undefined||t.groupId===q.groupId))},
  tabGroups:{get:async()=>({title:'fixture'})},
  debugger:{getTargets:async()=>[{tabId:10,type:'page',id:'replacement',attached:true}]}};
(async()=>{const s=await newOwnedState(page(1));s.task=await s.create();
  assert.equal((await s.snapshot()).workingPage,'live');
  const old=s.task;
  old.closed=true; // Debugger detached; Chrome keeps tab 10 open.
  const m=await s.snapshot();assert.equal(m.workingPage,'closed');assert.deepEqual(m.tabIds,[1,10]);
  const reattached=page(10);
  const tab=tabs.get(10);
  const info={delegate:{_targetId:'different-target'}};
  reattached._connection={toImpl:()=>info};
  tab.url='chrome://extensions/';
  assert.equal(await s.navigationReplacement(null),null);
  tab.url='https://login.example.com/';tab.status='complete';
  await assert.rejects(s.navigationReplacement(null),/unproven/);
  info.delegate._targetId='replacement';
  tab.groupId=2;
  await assert.rejects(s.navigationReplacement(null),/unproven/);
  tab.groupId=7;
  const extra=page(11);
  await assert.rejects(s.navigationReplacement(null),/unproven/);
  extra.closed=true;tabs.delete(11);
  const candidate=await s.navigationReplacement(null);
  assert.equal(s.task,old);
  assert.deepEqual(candidate,{targetId:'replacement',origin:'https://login.example.com'});
  await assert.rejects(s.navigationReplacement({...candidate,origin:'https://wrong.example.com'}),/changed/);
  assert.deepEqual(await s.navigationReplacement(candidate),candidate);
  assert.equal(s.task,reattached);
  assert.equal(s.ids.has(old),false);
  assert.deepEqual((await s.snapshot()).tabIds,[1,10]);
  s.task=null;assert.equal((await s.snapshot()).workingPage,'none');
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        checked = subprocess.run(
            ["node", "-e", source + fixture], capture_output=True, text=True, timeout=10
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_vendor_failure_class_is_a_fixed_label_without_page_text(self):
        def failing(text):
            return {"isError": True, "content": [{"type": "text", "text": text}]}

        for text, label in (
            (
                "Error: page.evaluate: Target page, context or browser has been closed",
                "vendor_target_closed",
            ),
            (
                "Execution context was destroyed, most likely because of a navigation",
                "vendor_context_destroyed",
            ),
            ("Frame was detached", "vendor_frame_detached"),
            ("Extension disconnected", "vendor_extension_disconnected"),
            ("TimeoutError: Timeout 5000ms exceeded.", "vendor_timeout"),
        ):
            with self.subTest(label=label):
                with self.assertRaises(Refusal) as caught:
                    b.projection(failing(text + " SYNTHETIC_CANARY"))
                self.assertEqual(str(caught.exception), "owned_operation_failed:" + label)
        # The route's own code still wins over a vendor phrase in the same text.
        with self.assertRaises(Refusal) as caught:
            b.projection(failing("Page has been closed\nError: saved_owned_tab_missing"))
        self.assertEqual(str(caught.exception), "owned_operation_failed:saved_owned_tab_missing")

    def test_window_closure_is_polled_briefly_without_applescript(self):
        w = sys.modules["chrome_job_window"]

        def no_subprocess(*_, **__):
            raise AssertionError("closure must not shell out to AppleScript")

        outputs = iter([[5, 6], [5, 6], [6]])
        calls = []

        def observe():
            calls.append(True)
            return next(outputs)

        with (
            patch.object(w.subprocess, "run", side_effect=no_subprocess),
            patch.object(w.time, "sleep"),
        ):
            w.verify_window_closed(5, observe)
            self.assertEqual(len(calls), 3)
            with self.assertRaises(w.InvalidLaunch):
                w.verify_window_closed(5, lambda: [5])
            for unreadable in (None, ["5"], {"ids": []}):
                with self.subTest(unreadable=unreadable):
                    with self.assertRaises(w.InvalidLaunch):
                        w.verify_window_closed(5, lambda: unreadable)

    def test_window_census_reads_chrome_windows_api(self):
        sent = []

        def fake(client, body):
            sent.append((client, body))
            return {"ids": [1, 2]}

        with patch.object(b, "code", side_effect=fake):
            self.assertEqual(b.window_ids("census"), [1, 2])
        self.assertEqual(sent[0][0], "census")
        self.assertIn("chrome.windows.getAll()", sent[0][1])

    def test_live_finish_records_removal_and_verifies_through_census(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            job = self.full_job(route, "ready")
            job["metadata"]["newestTabId"] = 10
            job["client"] = SimpleNamespace(closed=False, close=lambda: None)
            route.metadata = lambda _, strict=True: dict(job["metadata"])
            receipt = Path(root) / (job["job_id"] + ".json")
            order = []

            @contextlib.contextmanager
            def maintenance():
                order.append("census_opened")
                yield "census"

            route.maintenance_connector = maintenance

            def fake(client, body):
                if "s.closeWindow()" in body:
                    order.append(
                        ("issued", json.loads(receipt.read_text()).get("window_removal_issued"))
                    )
                    return {"scheduled": True, "shared": False, "windowId": 5}
                if "chrome.windows.getAll()" in body:
                    order.append(("census", client))
                    return {"ids": [9]}
                return {"closed": True}

            with patch.object(b, "code", side_effect=fake), patch.object(b.time, "sleep"):
                route.finish(job)
            self.assertEqual(order, [("issued", True), "census_opened", ("census", "census")])
            row = json.loads(receipt.read_text())
            self.assertEqual((row["status"], row["window_disposition"]), ("finished", "closed"))

    def test_unobserved_maintenance_closure_refuses(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            closed = []
            client = SimpleNamespace(close=lambda: closed.append(True))

            def fake(_, body):
                if "maintenance_window_not_exclusive" in body:
                    return {"windowId": 77, "closed": False}
                return {"ready": True}

            with (
                patch.object(route, "client", create=True, return_value=client),
                patch.object(b, "code", side_effect=fake),
            ):
                with self.assertRaises(Refusal) as caught:
                    with route.maintenance_connector():
                        pass
            self.assertEqual(str(caught.exception), "maintenance_window_closure_unobserved")
            self.assertEqual(closed, [True])

    def test_legacy_live_schedule_stage_counts_as_issued_removal(self):
        legacy = {
            "timings": [
                {"tool": "finish", "stages": [["received", 1], ["live_window_scheduled", 2]]}
            ]
        }
        self.assertTrue(b.removal_issued(legacy))
        self.assertTrue(b.removal_issued({"window_removal_issued": True}))
        self.assertFalse(b.removal_issued({"timings": [{"stages": [["live_pages_closed", 1]]}]}))
        self.assertFalse(b.removal_issued({}))
        # The receipt shape of jobs whose live close hung in the old verifier.
        out = self.failed_cleanup([], removal_issued=b.removal_issued(legacy))
        self.assertEqual(out["v"], {"closed": True, "count": 0, "alreadyClosed": True})

    PEER_NAME = "EP peer CANARY_LABEL [abcd1234]"
    PEER_URL = (
        "chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/connect.html?client="
        + "%7B%22name%22%3A%22EP%20peer%20CANARY_LABEL%20%5Babcd1234%5D%22%7D"
    )
    PEER = {"connectorId": 70, "windowId": 8, "tabIds": [70, 71, 75], "clientName": PEER_NAME}
    PEER_FIXTURE = r"""
const state=__STATE__;let removed=[];const hits={};
const hit=name=>{hits[name]=(hits[name]||0)+1;const m=state.mutations&&state.mutations[name+':'+hits[name]];if(!m)return;
  for(const op of m){if(op.move)state.tabs=state.tabs.map(t=>t.id===op.move?{...t,windowId:op.to}:t);
    if(op.add)state.tabs=state.tabs.concat([op.add]);if(op.sessions)state.sessions=op.sessions;}};
global.chrome={tabs:{query:async()=>{hit('query');return state.tabs.map(t=>({...t}));},getCurrent:async()=>({id:200})},
  windows:{remove:async(id)=>{removed.push(id);state.tabs=state.tabs.filter(t=>t.windowId!==id);}},
  tabGroups:{get:async()=>{hit('group');return {title:'fixture'};}},
  debugger:{getTargets:async()=>{hit('debugger');return [];}},
  runtime:{sendMessage:async(m)=>{hit('status');if(m.type==='getStatus')return state.sessions===undefined?{}:{sessions:state.sessions};return {connections:[]};}}};
process.__epBrowserJob={connector:{evaluate:async(fn,arg)=>await fn(arg)}};
async function attempt(){__BODY__}
attempt().then(v=>({v}),e=>({e:e.message})).then(o=>console.log(JSON.stringify({...o,removed,hits})));
"""

    def peer_tabs(self):
        return [
            {
                "id": 10,
                "windowId": 5,
                "groupId": -1,
                "title": "CANARY_TITLE",
                "url": "https://canary.invalid/?q=CANARY_QUERY",
            },
            {"id": 200, "windowId": 20, "groupId": -1},
            {"id": 70, "windowId": 8, "groupId": 3, "url": self.PEER_URL},
            {"id": 71, "windowId": 8, "groupId": 3, "openerTabId": 70},
            {"id": 75, "windowId": 8, "groupId": 3},
        ]

    def peer_session(self, tabs=(70, 71, 75), name=None, sid=1):
        return {"id": sid, "clientName": name or self.PEER_NAME, "tabIds": list(tabs)}

    def peer_cleanup(
        self,
        tabs=None,
        sessions="default",
        peers=None,
        remove=True,
        expected=None,
        diagnose=False,
        mutations=None,
        old=None,
    ):
        state = {"tabs": self.peer_tabs() if tabs is None else tabs, "mutations": mutations or {}}
        if sessions == "default":
            state["sessions"] = [self.peer_session()]
        elif sessions is not None:
            state["sessions"] = sessions
        body = b.failed_cleanup_js(
            {
                "old": old or self.OLD,
                "clientName": "fixture",
                "connectorOrigin": b.EXTENSION,
                "removalIssued": False,
                "pendingSince": 60,
                "peers": [self.PEER] if peers is None else peers,
                "expectedProof": expected,
            },
            remove,
            diagnose,
        )
        script = self.PEER_FIXTURE.replace("__STATE__", json.dumps(state)).replace("__BODY__", body)
        run = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        return self.refusal_as_error(json.loads(run.stdout))

    def assert_peer_blocks(self, expected="uncheckpointed_page_arrival", **kwargs):
        out = self.peer_cleanup(**kwargs)
        self.assertEqual(out.get("e"), expected, out)
        self.assertEqual(out["removed"], [])
        return out

    def test_live_ready_peer_birth_tabs_are_excused_but_never_closed(self):
        phase_one = self.peer_cleanup(remove=False)["v"]
        self.assertTrue(phase_one["ready"])
        self.assertEqual(phase_one["peerIds"], [70, 71, 75])
        self.assertRegex(phase_one["proof"], r"^[0-9a-f]{64}$")
        out = self.peer_cleanup(expected=phase_one["proof"])
        self.assertEqual(out["v"], {"closed": True, "count": 1, "connectorMissing": True})
        # Only the target's exact saved window is removed; peer tabs stay.
        self.assertEqual(out["removed"], [5])

    def test_peer_exemption_requires_every_birth_and_binding_link(self):
        tabs = self.peer_tabs()
        orphan = {"id": 63, "windowId": 8, "groupId": 3}
        cases = {
            # A target orphan in a live peer session but not in its receipt.
            "orphan_in_session_only": dict(
                tabs=tabs + [orphan], sessions=[self.peer_session((70, 71, 75, 63))]
            ),
            "moved_out_of_peer_window": dict(
                tabs=[{**t, "windowId": 9} if t["id"] == 71 else t for t in tabs]
            ),
            "duplicate_client_name": dict(
                sessions=[self.peer_session(), self.peer_session((90,), sid=2)]
            ),
            "session_lacks_connector": dict(sessions=[self.peer_session((71, 75))]),
            "connector_client_mismatch": dict(
                tabs=[{**t, "url": self.CONNECTOR_URL} if t["id"] == 70 else t for t in tabs]
            ),
            "connector_wrong_origin": dict(
                tabs=[
                    {**t, "url": "https://canary.invalid/connect.html"} if t["id"] == 70 else t
                    for t in tabs
                ]
            ),
            "other_session_claims_tab": dict(
                sessions=[
                    self.peer_session(),
                    self.peer_session((71,), name="EP other [ffff0000]", sid=2),
                ]
            ),
            "unsupported_status_schema": dict(sessions=None),
            "partial_status": dict(sessions=[{"clientName": self.PEER_NAME, "tabIds": [70, "71"]}]),
            "no_peer_receipt": dict(peers=[]),
            "overlapping_receipts": dict(peers=[self.PEER, {**self.PEER, "connectorId": 75}]),
            "foreign_opener": dict(
                tabs=[{**t, "openerTabId": 300} if t["id"] == 75 else t for t in tabs]
            ),
        }
        for name, kwargs in cases.items():
            with self.subTest(name):
                self.assert_peer_blocks(**kwargs)

    def test_target_extras_and_descendants_block_even_when_a_peer_claims_them(self):
        descendant = {"id": 72, "windowId": 8, "groupId": 3, "openerTabId": 10}
        hop = {"id": 73, "windowId": 9, "groupId": -1, "openerTabId": 72}
        extra = {"id": 74, "windowId": 5, "groupId": -1}
        claimed = {**self.PEER, "tabIds": [70, 71, 72, 73, 74, 75]}
        session = [self.peer_session((70, 71, 72, 73, 74, 75))]
        for added in ([descendant], [descendant, hop], [extra]):
            with self.subTest(added=[t["id"] for t in added]):
                self.assert_peer_blocks(
                    tabs=self.peer_tabs() + added, peers=[claimed], sessions=session
                )
        # A missing saved working tab still refuses before any exemption.
        self.assert_peer_blocks(
            expected="saved_owned_tab_missing",
            tabs=[t for t in self.peer_tabs() if t["id"] != 10],
        )

    def test_changed_proof_during_any_async_boundary_never_removes(self):
        grouped_old = {**self.OLD}
        grouped = [{**t, "groupId": 7} if t["id"] == 10 else t for t in self.peer_tabs()]
        moved_in = [{"move": 71, "to": 5}]
        drop = [{"sessions": [self.peer_session((70, 75))]}]
        stray = [{"add": {"id": 64, "windowId": 9, "groupId": -1}}]
        cases = {
            "during_debugger": dict(mutations={"debugger:1": moved_in}),
            "during_group_title": dict(tabs=grouped, old=grouped_old, mutations={"group:1": drop}),
            "new_orphan_during_debugger": dict(mutations={"debugger:1": stray}),
            # Reads: 1 initial, 2 after debugger, 3 final before remove. Each
            # read sends two getStatus messages after its tab query.
            "immediately_before_remove": dict(mutations={"status:5": drop}),
        }
        for name, kwargs in cases.items():
            with self.subTest(name):
                self.assert_peer_blocks(expected="cleanup_proof_changed", **kwargs)
        # A phase-one digest that no longer matches refuses at phase-two start.
        out = self.peer_cleanup(expected="b" * 64)
        self.assertEqual((out.get("e"), out["removed"]), ("cleanup_proof_changed", []))

    def test_change_after_last_read_is_reported_uncertain_not_success(self):
        # Chrome has no compare-and-remove. A tab moved into the target window
        # after the final read is closed with it; the post-close inventory must
        # refuse success rather than hide the foreign closure.
        out = self.peer_cleanup(mutations={"status:6": [{"move": 71, "to": 5}]})
        self.assertEqual(out.get("e"), "owned_cleanup_inventory_uncertain")
        self.assertEqual(out["removed"], [5])

    def test_diagnostic_inventory_is_content_free_and_never_removes(self):
        orphan = {"id": 63, "windowId": 9, "groupId": -1, "title": "CANARY_TITLE"}
        out = self.peer_cleanup(tabs=self.peer_tabs() + [orphan], diagnose=True)
        self.assertEqual(out["removed"], [])
        self.assertEqual(out["hits"].get("group"), None)
        projected = b.diagnostic_projection({**out["v"], "extra": "CANARY_EXTRA"})
        self.assertEqual(
            projected,
            {
                "authority": False,
                "observer": "temporary_maintenance_connector",
                "ready": False,
                "code": "uncheckpointed_page_arrival",
                "targetExtraIds": [],
                "descendantIds": [],
                "missingSavedIds": [1],
                "peerIds": [70, 71, 75],
                "unknownIds": [63],
            },
        )
        self.assertNotIn("CANARY", json.dumps(out["v"]) + json.dumps(projected))
        self.assertEqual(
            b.diagnostic_projection({"code": "CANARY_TEXT"})["code"], "diagnostic_unclassified"
        )
        many = b.diagnostic_projection({"unknownIds": list(range(100)), "peerIds": ["CANARY"]})
        self.assertEqual(
            (len(many["unknownIds"]), many["unknownIdsTruncated"], many["peerIds"]),
            (64, True, None),
        )

    def peer_receipt(self, generation, **changes):
        row = {
            "job_id": "e" * 32,
            "status": "ready",
            "client_name": self.PEER_NAME,
            "generation": generation,
            "metadata": {
                "connectorId": 70,
                "windowId": 8,
                "tabIds": [70, 71, 75],
                "unboundOwnedPages": 0,
            },
            "ownership_pending": False,
            "sealed": False,
        }
        row.update(changes)
        return row

    def test_only_live_ready_same_generation_peer_receipts_are_sources(self):
        gen = {"pid": 123, "started": "synthetic"}
        active = {"job_id": "e" * 32, "state": "active"}
        self.assertEqual(
            b.peer_proof_source(self.peer_receipt(gen), active, gen, "e" * 32),
            {
                "connectorId": 70,
                "windowId": 8,
                "tabIds": [70, 71, 75],
                "clientName": self.PEER_NAME,
            },
        )
        meta = self.peer_receipt(gen)["metadata"]
        refused = {
            "pending": (self.peer_receipt(gen, ownership_pending=True), active),
            "pending_missing": (
                {k: v for k, v in self.peer_receipt(gen).items() if k != "ownership_pending"},
                active,
            ),
            "failed": (self.peer_receipt(gen, status="failed"), active),
            "finished": (self.peer_receipt(gen, status="finished"), active),
            "terminal_owner": (self.peer_receipt(gen), {**active, "state": "terminal"}),
            "other_generation": (self.peer_receipt({"pid": 9, "started": "other"}), active),
            "relay": (self.peer_receipt(gen, relay_mode=True), active),
            "sealed": (self.peer_receipt(gen, sealed=True), active),
            "disposed": (self.peer_receipt(gen, window_disposition="closed"), active),
            "bool_id": (self.peer_receipt(gen, metadata={**meta, "windowId": True}), active),
            "connector_not_owned": (
                self.peer_receipt(gen, metadata={**meta, "tabIds": [71, 75]}),
                active,
            ),
            "duplicate_ids": (
                self.peer_receipt(gen, metadata={**meta, "tabIds": [70, 71, 71]}),
                active,
            ),
            "unbound_pages": (
                self.peer_receipt(gen, metadata={**meta, "unboundOwnedPages": 1}),
                active,
            ),
            "wrong_job": (self.peer_receipt(gen, job_id="f" * 32), active),
        }
        for name, (row, owner) in refused.items():
            with self.subTest(name):
                self.assertIsNone(b.peer_proof_source(row, owner, gen, "e" * 32))

    def write_peer(self, root, row, state="active"):
        (Path(root) / (row["job_id"] + ".json")).write_text(json.dumps(row))
        owners = Path(root) / "owners"
        owners.mkdir(exist_ok=True)
        (owners / (row["job_id"] + ".json")).write_text(
            json.dumps({"job_id": row["job_id"], "state": state, "session_id": "s"})
        )

    def test_peer_sources_read_only_this_state_dir_and_skip_unreadable(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as elsewhere:
            route = self.route(root)
            job = self.full_job(route)
            self.write_peer(elsewhere, self.peer_receipt(job["generation"]))
            self.assertEqual(route.peer_sources(job, 60), ([], []))
            self.write_peer(root, self.peer_receipt(job["generation"]))
            (Path(root) / ("c" * 32 + ".json")).write_text("{not json")
            peers, digests = route.peer_sources(job, 60)
            self.assertEqual([p["connectorId"] for p in peers], [70])
            self.assertEqual(len(digests), 1)
            # No pending call means no watermark, so no peer is consulted.
            self.assertEqual(route.peer_sources(job, None), ([], []))

    def pending_peer_route(self, root, on_phase_one=None, generations=None):
        route = self.route(root)
        job = self.full_job(route)
        job["ownership_pending"] = True
        job["metadata"]["newestTabId"] = 60
        route.save(job)
        self.write_peer(root, self.peer_receipt(job["generation"]))
        phases = []
        if generations is not None:
            sequence = iter(generations)
            route.preflight = lambda: next(sequence)

        def fake(_, body):
            if "async({old,clientName," in body:
                removing = '"remove": true' in body
                phases.append(removing)
                if removing:
                    return {"closed": True, "count": 1}
                if on_phase_one:
                    on_phase_one()
                return {"ready": True, "count": 1, "proof": "a" * 64, "peerIds": [71]}
            if "maintenance_window_not_exclusive" in body:
                return {"windowId": 77, "closed": True}
            return {"ready": True}

        return route, job, phases, fake

    def run_pending_finish(self, route, job, fake):
        with (
            patch.object(
                route, "client", create=True, return_value=SimpleNamespace(close=lambda: None)
            ),
            patch.object(b, "code", side_effect=fake),
            patch.object(b, "verify_window_closed"),
            patch.object(b.time, "sleep"),
        ):
            route.dispose_failed(job)

    def test_peer_receipt_change_between_phases_never_removes(self):
        gen = {"pid": 123, "started": "synthetic"}
        changes = {
            "new_tab": dict(
                metadata={
                    "connectorId": 70,
                    "windowId": 8,
                    "tabIds": [70, 71, 75, 76],
                    "unboundOwnedPages": 0,
                }
            ),
            "turned_failed": dict(status="failed"),
            "turned_pending": dict(ownership_pending=True),
            "same_fields_new_bytes": dict(updated=1),
        }
        for name, change in changes.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as root:
                holder = {}
                route, job, phases, fake = self.pending_peer_route(
                    root,
                    on_phase_one=lambda: self.write_peer(
                        holder["root"], self.peer_receipt(gen, **change)
                    ),
                )
                holder["root"] = root
                with self.assertRaisesRegex(Refusal, "peer_proof_changed"):
                    self.run_pending_finish(route, job, fake)
                self.assertEqual(phases, [False])
                self.assertNotIn("window_removal_issued", job)
        with tempfile.TemporaryDirectory() as root:
            route, job, phases, fake = self.pending_peer_route(
                root,
                on_phase_one=lambda: self.write_peer(
                    root, self.peer_receipt(gen), state="terminal"
                ),
            )
            with self.assertRaisesRegex(Refusal, "peer_proof_changed"):
                self.run_pending_finish(route, job, fake)
            self.assertEqual(phases, [False])

    def test_generation_is_checked_at_use_before_and_after_removal(self):
        gen = {"pid": 123, "started": "synthetic"}
        other = {"pid": 124, "started": "restarted"}
        # Calls: scope check, before phase two, after removal.
        for sequence, expected, phases in (
            ([gen, other], "browser_generation_changed_requires_reconciliation", [False]),
            ([gen, gen, other], "failed_cleanup_uncertain", [False, True]),
        ):
            with self.subTest(sequence=sequence), tempfile.TemporaryDirectory() as root:
                route, job, seen, fake = self.pending_peer_route(root, generations=sequence)
                with self.assertRaisesRegex(Refusal, expected):
                    self.run_pending_finish(route, job, fake)
                self.assertEqual(seen, phases)
                self.assertNotEqual(job.get("window_disposition"), "closed")
                self.assertTrue(job["ownership_pending"])

    def test_diagnostic_entry_point_has_no_dispose_or_receipt_side_effects(self):
        with tempfile.TemporaryDirectory() as root:
            route = self.route(root)
            route.bootstrap = contextlib.nullcontext
            job = self.full_job(route)
            job["ownership_pending"] = True
            job["metadata"]["newestTabId"] = 60
            route.save(job)
            live = SimpleNamespace(closed=False, close=lambda: self.fail("live client closed"))
            route.jobs[job["job_id"]] = {**job, "client": live, "status": "ready"}
            self.write_peer(root, self.peer_receipt(job["generation"]))
            before = {p.name: p.read_bytes() for p in Path(root).rglob("*.json")}
            bodies = []

            def fake(_, body):
                bodies.append(body)
                if "async({old,clientName," in body:
                    return {
                        "diagnostic": True,
                        "ready": False,
                        "code": "uncheckpointed_page_arrival",
                        "unknownIds": [63],
                        "peerIds": [71],
                        "targetExtraIds": [],
                        "descendantIds": [],
                        "missingSavedIds": [],
                        "label": "CANARY_LABEL",
                    }
                if "maintenance_window_not_exclusive" in body:
                    return {"windowId": 77, "closed": True}
                return {"ready": True}

            with (
                patch.object(
                    route, "client", create=True, return_value=SimpleNamespace(close=lambda: None)
                ),
                patch.object(b, "code", side_effect=fake),
                patch.object(route, "save", side_effect=AssertionError("receipt write")),
                patch.object(route, "dispose_failed", side_effect=AssertionError("dispose")),
                patch.object(route, "dispose_live", side_effect=AssertionError("dispose live")),
                patch.object(
                    route, "capture_connection_diagnostics", side_effect=AssertionError("diag")
                ),
            ):
                out = route.diagnose_failed(job["job_id"])
            self.assertEqual(
                (out["ready"], out["code"], out["unknownIds"]),
                (False, "uncheckpointed_page_arrival", [63]),
            )
            self.assertFalse(out["authority"])
            self.assertNotIn("CANARY", json.dumps(out))
            self.assertTrue(any('"diagnose": true' in body for body in bodies))
            self.assertFalse(any('"remove": true' in body for body in bodies))
            self.assertEqual({p.name: p.read_bytes() for p in Path(root).rglob("*.json")}, before)

            def boom(_, body):
                if "async({old,clientName," in body:
                    raise RuntimeError("CANARY_EXCEPTION https://canary.invalid/?token=CANARY")
                return fake(_, body)

            with (
                patch.object(
                    route, "client", create=True, return_value=SimpleNamespace(close=lambda: None)
                ),
                patch.object(b, "code", side_effect=boom),
                patch.object(route, "save", side_effect=AssertionError("receipt write")),
            ):
                out = route.diagnose_failed(job["job_id"])
            self.assertEqual(out["code"], "diagnostic_unavailable")
            self.assertNotIn("CANARY", json.dumps(out))
            with self.assertRaises(Refusal):
                route.diagnose_failed("../" + "a" * 29)
            self.assertEqual(route.diagnose_failed("a" * 32)["code"], "receipt_unreadable")

    def sealed_route(self, root):
        route = self.route(root)
        route.inventory.append(
            {
                "name": "browser_run_code_unsafe",
                "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}}},
            }
        )
        sent = []
        job = {
            "job_id": "c" * 32,
            "label": "fixture",
            "client_name": "fixture",
            "generation": {},
            "metadata": route.metadata(None),
            "updated": 0,
            "lock": threading.RLock(),
            "status": "ready",
            "client": SimpleNamespace(
                call=lambda *a: sent.append(a) or b.result({"vendor": "normal"})
            ),
        }
        route.jobs[job["job_id"]] = job
        return route, job, sent

    def test_sealed_reply_is_a_fixed_token_and_job_becomes_finish_only(self):
        source = (
            "async (page) => { console.log('SYNTHETIC_CANARY'); throw Error('SYNTHETIC_CANARY'); }"
        )
        for vendor, expected, status in (
            ({"sealed": "ok"}, {"sealed": "ok"}, "ready"),
            ({"sealed": "error"}, {"sealed": "error", "code": "sealed_code_failed"}, "ready"),
            (
                {"sealed": "SYNTHETIC_CANARY"},
                {"sealed": "error", "code": "sealed_outcome_uncertain"},
                "failed",
            ),
            (
                Refusal("owned_operation_failed"),
                {"sealed": "error", "code": "sealed_outcome_uncertain"},
                "failed",
            ),
        ):
            with tempfile.TemporaryDirectory() as root:
                route, job, sent = self.sealed_route(root)
                bodies = []

                def run(_, body, vendor=vendor):
                    bodies.append(body)
                    if isinstance(vendor, Exception):
                        raise vendor
                    return vendor

                with patch.object(b, "code", side_effect=run):
                    reply = route.call(
                        "browser_run_code_unsafe",
                        {"job_id": job["job_id"], "code": source, "sealed": True},
                    )
                self.assertEqual(json.loads(reply["content"][0]["text"]), expected)
                self.assertEqual(len(reply["content"]), 1)
                self.assertEqual(reply["isError"], expected != {"sealed": "ok"})
                self.assertEqual(job["status"], status)
                self.assertEqual(
                    sent, []
                )  # The user code never travels as an ordinary vendor call.
                self.assertIn(json.dumps(source), bodies[0])
                receipt = (Path(root) / (job["job_id"] + ".json")).read_text()
                self.assertNotIn("SYNTHETIC_CANARY", receipt)
                self.assertTrue(json.loads(receipt)["sealed"])
                with patch.object(route, "prime") as prime:
                    for name, args in (
                        ("browser_navigate", {"url": "http://127.0.0.1"}),
                        ("browser_run_code_unsafe", {"code": source, "sealed": True}),
                    ):
                        refused = route.call(name, {"job_id": job["job_id"], **args})
                        self.assertEqual(
                            decode(refused), {"sealed": "error", "code": "sealed_job_finish_only"}
                        )
                prime.assert_not_called()

    def test_sealed_arguments_are_strict_and_never_reach_the_browser(self):
        with tempfile.TemporaryDirectory() as root:
            route, job, sent = self.sealed_route(root)
            with patch.object(route, "prime") as prime, patch.object(b, "code") as execute:
                for args in (
                    {"code": "async()=>{}", "sealed": "yes"},
                    {"code": "async()=>{}", "filename": "x.js", "sealed": True},
                    {"code": " ", "sealed": True},
                    {"sealed": True},
                ):
                    reply = route.call("browser_run_code_unsafe", {"job_id": job["job_id"], **args})
                    self.assertEqual(
                        decode(reply), {"sealed": "error", "code": "sealed_arguments_invalid"}
                    )
            prime.assert_not_called()
            execute.assert_not_called()
            self.assertFalse(job.get("sealed"))

    def test_normal_run_code_is_forwarded_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            route, job, sent = self.sealed_route(root)
            for extra in ({}, {"sealed": False}):
                sent.clear()
                reply = route.call(
                    "browser_run_code_unsafe",
                    {"job_id": job["job_id"], "code": "async()=>1", **extra},
                )
                self.assertEqual(
                    sent,
                    [
                        (
                            "tools/call",
                            {
                                "name": "browser_run_code_unsafe",
                                "arguments": {"code": "async()=>1"},
                            },
                        )
                    ],
                )
                self.assertEqual(decode(reply), {"vendor": "normal"})
            self.assertFalse(job.get("sealed"))
            schema = next(
                t for t in route.tools()["tools"] if t["name"] == "browser_run_code_unsafe"
            )["inputSchema"]
            self.assertEqual(schema["properties"]["sealed"]["type"], "boolean")
            self.assertNotIn("sealed", schema["required"])

    def test_receipt_retains_stage_timestamps_without_page_content(self):
        with tempfile.TemporaryDirectory() as root:
            route, job, _ = self.sealed_route(root)
            route.prime = b.Route.prime.__get__(route)
            job["generation"] = route.preflight()
            with patch.object(b, "code", return_value={"index": 1}):
                job["client"] = SimpleNamespace(
                    call=lambda *a: b.result({"vendor": "SYNTHETIC_CANARY"})
                    if a[1]["name"] == "browser_navigate"
                    else {"content": []}
                )
                for _ in range(b.TIMING_RECORDS + 2):
                    route.call(
                        "browser_navigate",
                        {"job_id": job["job_id"], "url": "http://127.0.0.1/SYNTHETIC_CANARY"},
                    )
            row = json.loads((Path(root) / (job["job_id"] + ".json")).read_text())
            self.assertEqual(len(row["timings"]), b.TIMING_RECORDS)
            last = row["timings"][-1]
            self.assertEqual(last["tool"], "browser_navigate")
            self.assertEqual(
                [s for s, _ in last["stages"]],
                [
                    "received",
                    "prime_preflight",
                    "prime_verify",
                    "prime_own_index",
                    "prime_select",
                    "tool_start",
                    "tool_end",
                    "post_metadata",
                ],
            )
            times = [t for _, t in last["stages"]]
            self.assertEqual(times, sorted(times))
            self.assertNotIn("SYNTHETIC_CANARY", json.dumps(row))
            with patch.object(b, "code", side_effect=Refusal("response_timeout")):
                route.call("browser_navigate", {"job_id": job["job_id"], "url": "http://127.0.0.1"})
            row = json.loads((Path(root) / (job["job_id"] + ".json")).read_text())
            self.assertEqual(
                [s for s, _ in row["timings"][-1]["stages"]],
                ["received", "prime_preflight", "prime_verify", "failed:response_timeout"],
            )

    def test_seal_silences_vendor_capture_before_response_build(self):
        # Execute the shipped seal against a fake vendor Tab whose prototype owns
        # the capture methods, as in the pinned Playwright MCP bundle.
        with tempfile.TemporaryDirectory() as root:
            route, job, _ = self.sealed_route(root)
            bodies = []
            with patch.object(
                b, "code", side_effect=lambda _, body: bodies.append(body) or {"sealed": "error"}
            ):
                route.call(
                    "browser_run_code_unsafe",
                    {
                        "job_id": job["job_id"],
                        "sealed": True,
                        "code": "async (page) => { page.emit('console', 'SYNTHETIC_CANARY'); throw Error('SYNTHETIC_CANARY'); }",
                    },
                )
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
        checked = subprocess.run(
            ["node", "-e", fixture.replace("BODY", bodies[0])],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_transient_second_chrome_process_is_waited_out(self):
        # Any exec of the Chrome binary (each job's window wrapper included)
        # briefly runs a second "Google Chrome" before handing off to the
        # running browser. A peer's preflight must not fail during that window.
        def runner(sequence):
            calls = iter(sequence)

            def run(argv, **_):
                if argv[0] == "/usr/bin/pgrep":
                    return SimpleNamespace(stdout=next(calls))
                return SimpleNamespace(stdout="Thu Nov  5 16:16:24 2026\n")

            return run

        with (
            patch.object(b.subprocess, "run", side_effect=runner(["92295\n25055\n", "92295\n"])),
            patch.object(b.time, "sleep") as pause,
        ):
            self.assertEqual(
                b.chrome_generation(), {"pid": 92295, "started": "Thu Nov  5 16:16:24 2026"}
            )
        self.assertEqual(pause.call_count, 1)
        with (
            patch.object(
                b.subprocess, "run", side_effect=runner(["92295\n25055\n"] * b.GENERATION_ATTEMPTS)
            ),
            patch.object(b.time, "sleep"),
        ):
            with self.assertRaisesRegex(Refusal, "chrome_generation_ambiguous"):
                b.chrome_generation()

    CHILD = (
        "import sys,json,os,signal,subprocess\n"
        "d=sys.argv[1]\n"
        "g=subprocess.Popen([sys.executable,'-c','import time\\nwhile True: time.sleep(1)'])\n"
        "open(os.path.join(d,'grandchild'),'w').write(str(g.pid))\n"
        "def graceful(*_):\n"
        "    open(os.path.join(d,'graceful'),'w').write('1'); sys.exit(0)\n"
        "signal.signal(signal.SIGTERM,graceful)\n"
        "for line in sys.stdin:\n"
        "    q=json.loads(line); print(json.dumps({'jsonrpc':'2.0','id':q['id'],'result':{'ok':True}}),flush=True)\n"
        "graceful()\n"
    )

    @staticmethod
    def gone(pid, seconds=3):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            time.sleep(0.05)
        return False

    def test_transport_close_is_abrupt_and_reaps_the_whole_owned_group(self):
        # A graceful exit (stdin EOF or SIGTERM) lets Playwright MCP close pages
        # one by one; the close must never give it that chance.
        with tempfile.TemporaryDirectory() as d:
            client = StdioClient(
                [sys.executable, "-u", "-c", self.CHILD, d], os.environ.copy(), timeout=3
            )
            try:
                self.assertEqual(client.call("ping"), {"ok": True})
                grandchild = int(Path(d, "grandchild").read_text())
                client.close()
                self.assertFalse(Path(d, "graceful").exists())
                self.assertTrue(client.cleanup_verified)
                self.assertEqual(client.proc.returncode, -signal.SIGKILL)
                self.assertTrue(self.gone(grandchild))
                self.assertTrue(
                    client.proc.stdout.closed
                    and client.proc.stderr.closed
                    and client.proc.stdin.closed
                )
                with self.assertRaisesRegex(Refusal, "client_closed"):
                    client.call("ping")
                client.close()  # Idempotent, and never signals again.
            finally:
                client.close()

    def test_transport_close_after_child_already_exited_never_signals_others(self):
        peer = subprocess.Popen(
            [sys.executable, "-c", "import time\nwhile True: time.sleep(1)"], start_new_session=True
        )
        try:
            client = StdioClient([sys.executable, "-c", "pass"], os.environ.copy(), timeout=3)
            client.proc.wait(timeout=5)
            client.close()
            self.assertTrue(client.cleanup_verified)
            self.assertIsNone(peer.poll())
        finally:
            peer.kill()
            peer.wait()

    def test_owned_transport_reaps_child_and_never_signals_peer(self):
        script = "import sys,json\nfor line in sys.stdin:\n q=json.loads(line); print(json.dumps({'jsonrpc':'2.0','id':q['id'],'result':{'ok':True}}),flush=True)\n"
        clients = [
            StdioClient([sys.executable, "-u", "-c", script], os.environ.copy(), timeout=3)
            for _ in range(2)
        ]
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
