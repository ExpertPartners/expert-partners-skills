"""Ownership and terminal evidence, not age, authorize entire-window cleanup."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "plugins/operating-doctrine/skills/browser-automation/scripts"
)
sys.path.insert(0, str(SCRIPTS))


def load(name):
    # Loaded by path: these scripts sit outside the dependency checker's local scope.
    found = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(found)
    sys.modules[name] = module
    found.loader.exec_module(module)
    return module


lifecycle = load("browser_lifecycle")
hook = load("browser_window_cleanup")
browser_jobs = load("browser_jobs")
installer = load("install_browser_lifecycle")


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.sessions = tempfile.TemporaryDirectory()
        self.addCleanup(self.sessions.cleanup)
        patcher = patch.dict(os.environ, {"EP_BROWSER_LIFECYCLE_SESSIONS": self.sessions.name})
        patcher.start()
        self.addCleanup(patcher.stop)

    def receipt(self, root, job_id="a" * 32, **fields):
        row = {
            "job_id": job_id,
            "status": "ready",
            "control_socket": "control-0000000000000000.sock",
            **fields,
        }
        lifecycle.atomic_json(Path(root) / (job_id + ".json"), row)
        return row

    def test_hook_supplies_native_session_before_creation(self):
        calls = []
        output = hook.handle(
            {
                "session_id": "native-session",
                "hook_event_name": "PreToolUse",
                "tool_name": "mcp__playwright__browser_job_start",
                "tool_input": {"name": "fixture", "owner_session_id": "wrong"},
            },
            calls.append,
        )
        self.assertEqual(
            output["hookSpecificOutput"]["updatedInput"],
            {"name": "fixture", "owner_session_id": "native-session"},
        )
        self.assertEqual(calls, [])

    def test_hook_binds_start_response_and_existing_job(self):
        calls = []
        payload = {
            "session_id": "native-session",
            "hook_event_name": "PostToolUse",
            "tool_name": "mcp__playwright__browser_job_start",
            "tool_response": {
                "content": [{"type": "text", "text": json.dumps({"job_id": "b" * 32})}]
            },
        }
        hook.handle(payload, calls.append)
        self.assertEqual(
            calls, [{"action": "bind", "session_id": "native-session", "job_id": "b" * 32}]
        )
        payload.update(
            hook_event_name="PreToolUse",
            tool_name="mcp__playwright__browser_tabs",
            tool_input={"job_id": "b" * 32},
        )
        hook.handle(payload, calls.append)
        self.assertEqual(len(calls), 1)

    def test_native_stop_and_session_end_not_idle_or_archiving(self):
        calls = []
        start = {
            "session_id": "native-session",
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__playwright__browser_job_start",
            "tool_input": {"name": "x"},
        }
        for event in ("Stop", "SessionEnd", "Notification", "SubagentStop"):
            hook.handle(start, calls.append)
            hook.handle({"session_id": "native-session", "hook_event_name": event}, calls.append)
        self.assertEqual([x["event"] for x in calls], ["Stop", "SessionEnd"])
        self.assertEqual([x["action"] for x in calls], ["finish_session", "finish_session"])

    def test_sessions_without_browser_jobs_never_reach_browser_host(self):
        calls = []
        hook.handle({"session_id": "plain-session", "hook_event_name": "Stop"}, calls.append)
        hook.handle({"session_id": "plain-session", "hook_event_name": "SessionEnd"}, calls.append)
        self.assertEqual(calls, [])

    def test_failed_stop_blocks_once_then_never_loops(self):
        env = {
            **os.environ,
            "EP_BROWSER_LIFECYCLE_SESSIONS": os.environ["EP_BROWSER_LIFECYCLE_SESSIONS"],
            "EP_BROWSER_LIFECYCLE_CONFIG": "/nonexistent/lifecycle.json",
        }
        (Path(env["EP_BROWSER_LIFECYCLE_SESSIONS"]) / "loop-session").touch()
        outputs = []
        for active in (False, True):
            run = subprocess.run(
                [sys.executable, str(SCRIPTS / "browser_window_cleanup.py")],
                text=True,
                capture_output=True,
                env=env,
                timeout=10,
                input=json.dumps(
                    {
                        "session_id": "loop-session",
                        "hook_event_name": "Stop",
                        "stop_hook_active": active,
                    }
                ),
            )
            outputs.append((run.returncode, json.loads(run.stdout)))
        self.assertEqual(outputs[0][0], 2)
        self.assertEqual(outputs[0][1]["decision"], "block")
        self.assertEqual(outputs[1][0], 0)
        self.assertNotIn("decision", outputs[1][1])

    def test_bind_failure_never_blocks_browser_call_and_legacy_jobs_stay_manual(self):
        def refuse(_):
            raise RuntimeError("legacy_route_not_bound")

        payload = {
            "session_id": "s1",
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__playwright__browser_click",
            "tool_input": {"job_id": "d" * 32},
        }
        self.assertEqual(hook.handle(payload, refuse), {})
        self.assertFalse((Path(self.sessions.name) / "s1").exists())
        with tempfile.TemporaryDirectory() as root:
            lifecycle.atomic_json(
                Path(root) / ("e" * 32 + ".json"), {"job_id": "e" * 32, "status": "ready"}
            )
            with self.assertRaisesRegex(ValueError, "legacy_route_not_bound"):
                lifecycle.bind(root, "e" * 32, "s1")

    def test_owner_binding_is_private_immutable_and_missing_owner_is_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            receipt = self.receipt(root)
            first = lifecycle.bind(root, receipt["job_id"], "session-one")
            self.assertEqual(lifecycle.bind(root, receipt["job_id"], "session-one"), first)
            with self.assertRaisesRegex(ValueError, "peer_session"):
                lifecycle.bind(root, receipt["job_id"], "session-two")
            self.assertEqual(
                lifecycle.owner_path(root, receipt["job_id"]).stat().st_mode & 0o777, 0o600
            )
            self.assertEqual(lifecycle.sweep({"state_dir": root}), [])
            with self.assertRaises(ValueError):
                lifecycle.bind(root, "../bad", "session-one")

    def test_nightly_sweep_only_terminal_owned_jobs_even_if_peer_old(self):
        with tempfile.TemporaryDirectory() as root:
            terminal = self.receipt(root, "a" * 32)
            self.receipt(root, "b" * 32, updated=1)
            unknown = self.receipt(root, "c" * 32, updated=1)
            lifecycle.bind(root, terminal["job_id"], "done-session")
            lifecycle.bind(root, "b" * 32, "active-session")
            lifecycle.terminal(root, "done-session", "Stop")
            with patch.object(lifecycle, "control", return_value={"ok": True}) as control:
                self.assertEqual(
                    lifecycle.sweep({"state_dir": root}),
                    [{"job_id": terminal["job_id"], "status": "finished"}],
                )
                self.assertEqual(control.call_count, 1)
                self.assertEqual(control.call_args.args[2]["session_id"], "done-session")
            self.assertEqual(
                json.loads((Path(root) / (unknown["job_id"] + ".json")).read_text()), unknown
            )
            with self.assertRaisesRegex(ValueError, "terminal"):
                lifecycle.terminal(root, "active-session", "idle")

    def test_finished_owner_rows_retire_without_touching_receipts(self):
        with tempfile.TemporaryDirectory() as root:
            row = self.receipt(root, status="finished")
            lifecycle.bind(root, row["job_id"], "done")
            lifecycle.terminal(root, "done", "Stop")
            self.assertEqual(lifecycle.sweep({"state_dir": root})[0]["status"], "already_finished")
            owner = lifecycle.owner_path(root, row["job_id"])
            aged = json.loads(owner.read_text())
            aged["terminal_at"] -= lifecycle.OWNER_RETENTION + 1
            lifecycle.atomic_json(owner, aged)
            self.assertEqual(
                lifecycle.sweep({"state_dir": root})[0]["status"], "owner_record_retired"
            )
            self.assertFalse(owner.exists())
            self.assertEqual(json.loads((Path(root) / (row["job_id"] + ".json")).read_text()), row)

    def test_failed_cleanup_preserves_receipt_instead_of_claiming_success(self):
        with tempfile.TemporaryDirectory() as root:
            row = self.receipt(root, ownership_pending=True)
            lifecycle.bind(root, row["job_id"], "done")
            lifecycle.terminal(root, "done", "SessionEnd")
            with patch.object(
                lifecycle, "control", side_effect=RuntimeError("live_cleanup_refused")
            ):
                report = lifecycle.sweep({"state_dir": root})
            self.assertEqual(report[0]["status"], "preserved_uncertain")
            self.assertEqual(json.loads((Path(root) / (row["job_id"] + ".json")).read_text()), row)

    def null_id_failure(self, root, job_id="f" * 32, **fields):
        return self.receipt(
            root,
            job_id,
            status="failed",
            metadata=None,
            allocation_failure={
                "stage": "connector_identity",
                "class": "owned_operation_failed:not_fresh_connector",
            },
            connection_diagnostics={"first_failure": {"stage": "allocation", "at": 1000.0}},
            timings=[{"tool": "finish", "stages": [["failed:x", 5000.0]]}],
            **fields,
        )

    def test_null_id_failure_with_census_stops_blocking_but_stays_failed(self):
        with tempfile.TemporaryDirectory() as root:
            row = self.null_id_failure(root)
            lifecycle.bind(root, row["job_id"], "done")
            lifecycle.terminal(root, "done", "Stop")
            with patch.object(
                lifecycle, "control", side_effect=RuntimeError("live_cleanup_refused")
            ) as control:
                self.assertEqual(
                    lifecycle.sweep({"state_dir": root})[0]["status"], "preserved_uncertain"
                )
                # A finish refusal after the allocation must not count as allocation time.
                lifecycle.record_census(root, row["job_id"], 2000.0, 1, 1, "handoff note")
                report = lifecycle.sweep({"state_dir": root})
                self.assertEqual(control.call_count, 1)
            self.assertEqual(
                report,
                [
                    {
                        "job_id": row["job_id"],
                        "status": lifecycle.NO_ARTIFACTS,
                        "census_at": 2000.0,
                    }
                ],
            )
            self.assertEqual(json.loads((Path(root) / (row["job_id"] + ".json")).read_text()), row)

    def test_census_never_excuses_receipts_with_ids_or_older_census(self):
        with tempfile.TemporaryDirectory() as root:
            cases = {
                "1" * 32: {"metadata": {"windowId": 5, "tabIds": [6]}},
                "2" * 32: {"initial_connector": {"connectorId": 6, "windowId": 5}},
                "3" * 32: {"ownership_pending": True},
                "4" * 32: {"relay_mode": True, "relay_pid": 99},
                "5" * 32: {"status": "ready"},
            }
            for job_id, fields in cases.items():
                row = self.null_id_failure(root, job_id)
                row.update(fields)
                lifecycle.atomic_json(Path(root) / (job_id + ".json"), row)
                with self.assertRaisesRegex(ValueError, "ownership_ids"):
                    lifecycle.record_census(root, job_id, 2000.0, 1, 1, "note")
                # A note written by hand still does not unblock it.
                lifecycle.atomic_json(
                    lifecycle.census_path(root, job_id),
                    {"job_id": job_id, "census_at": 2000.0, "orphans": 0},
                )
                lifecycle.bind(root, job_id, "done")
            old = self.null_id_failure(root, "6" * 32)
            with self.assertRaisesRegex(ValueError, "predates"):
                lifecycle.record_census(root, old["job_id"], 999.0, 1, 1, "note")
            lifecycle.atomic_json(
                lifecycle.census_path(root, old["job_id"]),
                {"job_id": old["job_id"], "census_at": 999.0, "orphans": 0},
            )
            lifecycle.bind(root, old["job_id"], "done")
            active = self.null_id_failure(root, "7" * 32)
            lifecycle.record_census(root, active["job_id"], 2000.0, 1, 1, "note")
            lifecycle.bind(root, active["job_id"], "still-running")
            lifecycle.terminal(root, "done", "Stop")
            with patch.object(lifecycle, "control", side_effect=RuntimeError("refused")):
                report = lifecycle.sweep({"state_dir": root})
            self.assertEqual(len(report), 6)
            self.assertEqual({x["status"] for x in report}, {"preserved_uncertain"})

    def test_stop_reports_census_failures_as_failed_not_clean(self):
        (Path(self.sessions.name) / "s9").touch()
        report = [
            {"job_id": "f" * 32, "status": "failed_no_artifacts_by_census", "census_at": 2.0},
            {"job_id": "a" * 32, "status": "already_finished"},
        ]
        output = hook.handle({"session_id": "s9", "hook_event_name": "Stop"}, lambda _: report)
        self.assertNotIn("decision", output)
        self.assertIn("f" * 32 + " failed, no artifacts by census", output["systemMessage"])
        self.assertIn("remain failed", output["systemMessage"])
        (Path(self.sessions.name) / "s9").touch()
        self.assertEqual(
            hook.handle({"session_id": "s9", "hook_event_name": "Stop"}, lambda _: [report[1]]), {}
        )
        (Path(self.sessions.name) / "s9").touch()
        report.append({"job_id": "b" * 32, "status": "failed_no_artifacts_by_generation"})
        mixed = hook.handle({"session_id": "s9", "hook_event_name": "Stop"}, lambda _: report)
        self.assertIn("no artifacts by census", mixed["systemMessage"])
        self.assertIn("old browser generation gone", mixed["systemMessage"])
        self.assertIn("No browser close issued", mixed["systemMessage"])

    def test_dead_generation_is_recorded_without_closing_or_rewriting_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            old = {"pid": 8222, "started": "old process"}
            current = {"pid": 49559, "started": "new process"}
            row = self.receipt(
                root,
                status="failed",
                generation=old,
                ownership_pending=True,
                metadata={"windowId": 5, "tabIds": [6]},
            )
            lifecycle.bind(root, row["job_id"], "done")
            lifecycle.terminal(root, "done", "Stop")
            with patch.object(browser_jobs, "chrome_generation", return_value=current):
                note = lifecycle.record_generation(root, row["job_id"], "test evidence")
                with patch.object(lifecycle, "control") as control:
                    report = lifecycle.sweep({"state_dir": root})
                control.assert_not_called()
            self.assertEqual(report[0]["status"], "failed_no_artifacts_by_generation")
            self.assertFalse(note["browser_close_issued"])
            self.assertEqual(note["previous_generation"], old)
            self.assertEqual(note["observed_generation"], current)
            self.assertEqual(json.loads((Path(root) / (row["job_id"] + ".json")).read_text()), row)
            # A stale note never overrides a different live generation.
            for observed in (old, {"pid": 60000, "started": "third process"}):
                with patch.object(browser_jobs, "chrome_generation", return_value=observed):
                    with patch.object(lifecycle, "control") as control:
                        self.assertEqual(
                            lifecycle.sweep({"state_dir": root})[0]["status"], "preserved_uncertain"
                        )
                    control.assert_not_called()
            for contents in ("invalid json", "[]", "{}"):
                lifecycle.generation_path(root, row["job_id"]).write_text(contents)
                with patch.object(lifecycle, "control") as control:
                    self.assertEqual(
                        lifecycle.sweep({"state_dir": root})[0]["status"], "preserved_uncertain"
                    )
                control.assert_not_called()
            lifecycle.atomic_json(lifecycle.generation_path(root, row["job_id"]), note)
            with patch.object(
                browser_jobs, "chrome_generation", side_effect=RuntimeError("ambiguous")
            ):
                with patch.object(lifecycle, "control") as control:
                    self.assertEqual(
                        lifecycle.sweep({"state_dir": root})[0]["status"], "preserved_uncertain"
                    )
                control.assert_not_called()
            self.assertEqual(json.loads((Path(root) / (row["job_id"] + ".json")).read_text()), row)
            self.assertEqual(
                json.loads(lifecycle.generation_path(root, row["job_id"]).read_text()), note
            )

    def test_generation_reconciliation_refuses_live_active_missing_and_relay(self):
        with tempfile.TemporaryDirectory() as root:
            old = {"pid": 8222, "started": "old process"}
            current = {"pid": 49559, "started": "new process"}
            for i, fields in enumerate(
                (
                    {},
                    {"status": "ready"},
                    {"generation": None},
                    {"relay_mode": True},
                    {"generation": {"pid": "8222", "started": "old"}},
                )
            ):
                row = self.receipt(root, str(i) * 32, status="failed", generation=old)
                row.update(fields)
                lifecycle.atomic_json(Path(root) / (row["job_id"] + ".json"), row)
                lifecycle.bind(root, row["job_id"], "done")
            lifecycle.terminal(root, "done", "Stop")
            with patch.object(browser_jobs, "chrome_generation", return_value=old):
                with self.assertRaises(ValueError):
                    lifecycle.record_generation(root, "0" * 32, "note")
            with patch.object(browser_jobs, "chrome_generation", return_value=current):
                for i in range(1, 5):
                    with self.assertRaises(ValueError):
                        lifecycle.record_generation(root, str(i) * 32, "note")
                active = self.receipt(root, "a" * 32, status="failed", generation=old)
                lifecycle.bind(root, active["job_id"], "active")
                with self.assertRaises(ValueError):
                    lifecycle.record_generation(root, active["job_id"], "note")
                with self.assertRaises(ValueError):
                    lifecycle.record_generation(root, "0" * 32, "")

    def test_live_private_channel_checks_terminal_session_and_serializes_finish(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as root:
            guard = Path(root) / "policy.py"
            guard.write_text("def decide(payload): return None\n")
            route = browser_jobs.Route({"state_dir": root, "headless_hook": str(guard)})
            row = self.receipt(root, control_socket=route.control_socket)
            route.jobs[row["job_id"]] = {**row, "lock": threading.RLock()}
            lifecycle.bind(root, row["job_id"], "native-session")
            calls = []
            route.finish = lambda job: calls.append(job["job_id"])
            try:
                with self.assertRaises(RuntimeError):
                    lifecycle.control(
                        root,
                        row,
                        {
                            "action": "finish",
                            "job_id": row["job_id"],
                            "session_id": "native-session",
                        },
                    )
                lifecycle.terminal(root, "native-session", "Stop")
                with self.assertRaises(RuntimeError):
                    lifecycle.control(
                        root,
                        row,
                        {"action": "finish", "job_id": row["job_id"], "session_id": "peer-session"},
                    )
                self.assertEqual(calls, [])
                lifecycle.control(
                    root,
                    row,
                    {"action": "finish", "job_id": row["job_id"], "session_id": "native-session"},
                )
                self.assertEqual(calls, [row["job_id"]])
            finally:
                route.close_control()

    def test_whole_window_close_keeps_foreign_tab_and_rechecks_before_timer(self):
        source = (SCRIPTS / "owned_pages.js").read_text()
        fixture = r'''
const assert=require('node:assert/strict');
let tabs=[{id:1,windowId:5,groupId:7}];let timers=[];let removed=[];let closedTabs=[];
global.setTimeout=(fn)=>timers.push(fn);
global.chrome={tabs:{getCurrent:async()=>tabs[0],query:async()=>tabs,remove:async id=>closedTabs.push(id)},
 tabGroups:{get:async()=>({title:'fixture'})},windows:{remove:async id=>removed.push(id)}};
const connector={context:()=>({pages:()=>[connector]}),evaluate:async(fn,arg)=>fn(arg)};
(async()=>{
 const s=await newOwnedState(connector);
 tabs.push({id:999,windowId:5,groupId:-1});
 assert.equal((await s.closeWindow()).shared,true);await timers.pop()();
 assert.deepEqual(removed,[]);assert.deepEqual(closedTabs,[1]);closedTabs=[];
 tabs.pop();await s.closeWindow();
 tabs.push({id:999,windowId:5,groupId:-1});await timers.pop()();
 assert.deepEqual(removed,[]);assert.deepEqual(closedTabs,[1]);
 tabs.pop();await s.closeWindow();await timers.pop()();
 assert.deepEqual(removed,[5]);
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        result = subprocess.run(
            ["node", "-e", source + fixture], capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_connector_born_in_occupied_window_moves_to_its_own(self):
        source = (SCRIPTS / "owned_pages.js").read_text()
        fixture = r'''
const assert=require('node:assert/strict');
let tabs=[{id:1,windowId:5,groupId:7},{id:50,windowId:5,groupId:9}];const updates=[];
global.chrome={tabs:{getCurrent:async()=>tabs[0],query:async q=>tabs.filter(t=>t.windowId===q.windowId),
  group:async({tabIds,createProperties})=>{tabs[0].groupId=8;tabs[0].windowId=createProperties.windowId;return 8;}},
 tabGroups:{get:async id=>({title:id===8?'moved':'fixture',color:'blue'}),update:async(id,p)=>updates.push([id,p])},
 windows:{create:async({tabId})=>{tabs.find(t=>t.id===tabId).windowId=6;return {id:6};}}};
const connector={context:()=>({pages:()=>[connector]}),evaluate:async(fn,arg)=>fn(arg)};
(async()=>{
 const s=await newOwnedState(connector);
 assert.equal(s.initial.windowId,6);assert.equal(s.initial.groupId,8);
 assert.deepEqual(updates,[[8,{title:'fixture',color:'blue'}]]);
 assert.equal(tabs[1].windowId,5);
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        result = subprocess.run(
            ["node", "-e", source + fixture], capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_user_hooks_survive_pins_preserve_existing_hooks_and_are_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "hooks.json"
            lifecycle.atomic_json(
                path, {"Stop": [{"hooks": [{"type": "command", "command": "existing"}]}]}
            )
            command = "/Users/ember/.local/bin/ep-browser-window-cleanup"
            installer.merge_hooks(path, command, "factory")
            installer.merge_hooks(path, command, "factory")
            doc = json.loads(path.read_text())
            self.assertEqual(len(doc["Stop"]), 2)
            self.assertEqual(doc["Stop"][0]["hooks"][0]["command"], "existing")
            self.assertEqual(doc["Stop"][1]["hooks"][0]["command"], command)
            codex = Path(root) / "codex.json"
            installer.merge_hooks(codex, command, "codex")
            self.assertEqual(
                json.loads(codex.read_text())["hooks"]["SessionEnd"][0]["hooks"][0]["timeout"], 3
            )


if __name__ == "__main__":
    unittest.main()
