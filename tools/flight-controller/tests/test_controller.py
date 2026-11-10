#!/usr/bin/env python3
"""Controlled fixtures for the flight controller's decisions, dedup and durability."""

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "controller", Path(__file__).parents[1] / "controller.py"
)
controller = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(controller)

SID = "07242268-2d4d-490c-8e4f-21ea2bc81597"
CHILD = "aa3b50e0-1743-4938-8b3d-be3ed4bb10ec"
MINUTE = 60_000
NOW = 1_700_000_000_000


def session(status="idle", updated=NOW, count=100, attention=None, title="Cal Week Builder"):
    return {
        "sessionId": SID,
        "title": title,
        "status": status,
        "updatedAt": updated,
        "messageCount": count,
        "attention": attention,
    }


def child(status="running", attention=None):
    return {"sessionId": CHILD, "title": "worker", "status": status, "attention": attention}


def says(text, role="assistant"):
    return [{"id": "m1", "role": role, "content": text, "createdAt": str(NOW)}]


class FakeApi:
    def __init__(self, *, parent=None, kids=(), messages=(), fail=None, post=None):
        self.parent = parent or session()
        self.kids = list(kids)
        self.msgs = list(messages)
        self.fail = fail
        self.posts = []
        self.post_error = post

    def session(self, session_id):
        if self.fail:
            raise controller.ApiError(self.fail, 503)
        return self.parent

    def children(self, session_id):
        if self.fail:
            raise controller.ApiError(self.fail, 503)
        return self.kids

    def messages(self, session_id, limit):
        if self.fail:
            raise controller.ApiError(self.fail, 503)
        return self.msgs

    def post_message(self, session_id, text):
        self.posts.append((session_id, text))
        if self.post_error:
            raise self.post_error
        return {"messageId": "msg-" + str(len(self.posts)), "status": "pending"}


class FakeAlerts:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    def send(self, text):
        if self.fail:
            raise controller.ControllerError("Alert outcome unknown; content withheld.")
        self.sent.append(text)
        return {"handle": "h" + str(len(self.sent)), "status": "QUEUED"}


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.now = NOW
        self.config = controller.with_defaults(
            {
                "sessions": [SID],
                "state_dir": self.dir.name,
                "alerts": {"op": "/bin/false", "item": "x", "vault": "y", "recipient": "+1"},
                "summary_hour": 23,
            }
        )
        self.addCleanup(self.dir.cleanup)

    def clock(self):
        return self.now

    def make(self, api, alerts=None):
        return controller.Controller(self.config, api, alerts or FakeAlerts(), clock=self.clock)


class Decisions(Base):
    def test_running_session_is_never_touched(self):
        api = FakeApi(parent=session(status="running"))
        report = self.make(api).tick()
        self.assertEqual(report["sessions"][SID]["state"], "running")
        self.assertEqual(api.posts, [])

    def test_idle_orchestrator_waiting_for_working_children_is_healthy(self):
        api = FakeApi(parent=session(updated=NOW - 300 * MINUTE), kids=[child("running")])
        report = self.make(api).tick()
        self.assertEqual(report["sessions"][SID]["state"], "waiting_on_children")
        self.assertEqual(api.posts, [])

    def test_recent_idle_is_not_a_stall(self):
        api = FakeApi(parent=session(updated=NOW - 5 * MINUTE))
        self.assertEqual(self.make(api).tick()["sessions"][SID]["state"], "idle_recent")
        self.assertEqual(api.posts, [])

    def test_stale_idle_with_no_live_children_gets_exactly_one_nudge(self):
        api = FakeApi(parent=session(updated=NOW - 90 * MINUTE), kids=[child("idle")])
        hand = self.make(api)
        first = hand.tick()
        self.assertEqual(first["sessions"][SID]["state"], "stalled")
        self.assertEqual(
            [item["result"] for item in first["actions"] if item.get("action") == "nudge"],
            ["message_accepted"],
        )
        self.assertEqual(len(api.posts), 1)
        self.assertIn(controller.MARKER, api.posts[0][1])
        self.now += 20 * MINUTE
        second = hand.tick()
        self.assertEqual(
            [item["result"] for item in second["actions"] if item.get("action") == "nudge"],
            ["suppressed_duplicate"],
        )
        self.assertEqual(len(api.posts), 1)

    def test_finished_session_is_reported_not_restarted(self):
        api = FakeApi(
            parent=session(updated=NOW - 300 * MINUTE),
            messages=says("Work is complete. Ready to archive."),
        )
        alerts = FakeAlerts()
        report = self.make(api, alerts).tick()
        self.assertEqual(report["sessions"][SID]["state"], "finished")
        self.assertEqual(api.posts, [])
        self.assertTrue(any("finished" in text for text in alerts.sent))

    def test_manual_hold_is_never_restarted(self):
        api = FakeApi(
            parent=session(updated=NOW - 600 * MINUTE),
            messages=says("Parked on manual hold until Allison returns."),
        )
        report = self.make(api).tick()
        self.assertEqual(report["sessions"][SID]["state"], "held")
        self.assertEqual(api.posts, [])

    def test_pending_founder_decision_alerts_without_sending_an_answer(self):
        api = FakeApi(
            parent=session(updated=NOW - 600 * MINUTE),
            messages=says("This is a genuine founder decision for Allison."),
        )
        alerts = FakeAlerts()
        report = self.make(api, alerts).tick()
        self.assertEqual(report["sessions"][SID]["state"], "founder_decision")
        self.assertEqual(api.posts, [])
        self.assertTrue(any("Nothing was answered on your behalf" in t for t in alerts.sent))

    def test_native_ask_user_prompt_is_not_treated_as_answerable(self):
        api = FakeApi(parent=session(attention={"kind": "ask-user", "since": NOW - MINUTE}))
        alerts = FakeAlerts()
        report = self.make(api, alerts).tick()
        self.assertEqual(report["sessions"][SID]["state"], "blocked_attention")
        self.assertEqual(api.posts, [])
        self.assertEqual(len(alerts.sent), 1)

    def test_child_waiting_on_a_prompt_holds_the_orchestrator_still(self):
        api = FakeApi(
            parent=session(updated=NOW - 600 * MINUTE),
            kids=[child("idle", attention={"kind": "permission", "since": NOW})],
        )
        report = self.make(api).tick()
        self.assertEqual(report["sessions"][SID]["state"], "child_blocked")
        self.assertEqual(api.posts, [])

    def test_unknown_status_is_not_assumed_idle(self):
        api = FakeApi(parent=session(status="archived", updated=NOW - 600 * MINUTE))
        self.assertEqual(self.make(api).tick()["sessions"][SID]["state"], "unknown")
        self.assertEqual(api.posts, [])


class Usage(Base):
    def test_provider_reported_reset_is_awaited_then_tried_once(self):
        api = FakeApi(
            parent=session(updated=NOW - 60 * MINUTE),
            messages=says("Request failed: usage limit reached. Resets at 2023-11-14T22:40:00Z"),
        )
        hand = self.make(api)
        waiting = [item for item in hand.tick()["actions"] if item.get("action") == "resume"]
        self.assertEqual(waiting[0]["result"], "waiting_for_reset")
        self.assertEqual(waiting[0]["basis"], "provider_reset")
        self.assertEqual(api.posts, [])
        self.now = controller.parse_reset("Resets at 2023-11-14T22:40:00Z", NOW) + 11 * MINUTE
        api.parent = session(updated=self.now - 60 * MINUTE)
        done = [item for item in hand.tick()["actions"] if item.get("action") == "resume"]
        self.assertEqual(done[0]["result"], "message_accepted")
        self.assertEqual(len(api.posts), 1)

    def test_old_exhaustion_without_a_reset_waits_conservatively(self):
        api = FakeApi(
            parent=session(updated=NOW - 600 * MINUTE),
            messages=says("Error: credit balance exhausted."),
        )
        hand = self.make(api)
        first = [item for item in hand.tick()["actions"] if item.get("action") == "resume"]
        self.assertEqual(first[0]["result"], "waiting_for_reset")
        self.assertEqual(first[0]["basis"], "conservative_wait")
        self.now += 60 * MINUTE
        still = [item for item in hand.tick()["actions"] if item.get("action") == "resume"]
        self.assertEqual(still[0]["result"], "waiting_for_reset")
        self.assertEqual(api.posts, [])
        self.now += self.config["unknown_reset_wait_minutes"] * MINUTE
        after = [item for item in hand.tick()["actions"] if item.get("action") == "resume"]
        self.assertEqual(after[0]["result"], "message_accepted")

    def test_relative_reset_is_read_from_the_provider_text(self):
        self.assertEqual(
            controller.parse_reset("rate limit; try again in 30 minutes", NOW),
            NOW + 30 * MINUTE,
        )
        self.assertIsNone(controller.parse_reset("usage limit reached", NOW))


class Durability(Base):
    def test_api_outage_takes_no_action_and_alerts_after_the_threshold(self):
        api = FakeApi(fail="transport")
        alerts = FakeAlerts()
        hand = self.make(api, alerts)
        for _ in range(self.config["failure_alert_after"]):
            report = hand.tick()
            self.now += 15 * MINUTE
        self.assertEqual(report["sessions"][SID]["state"], "api_unavailable")
        self.assertFalse(report["api"]["ok"])
        self.assertEqual(report["consecutive_failures"], self.config["failure_alert_after"])
        self.assertEqual(len(alerts.sent), 1)
        self.assertEqual(api.posts, [])

    def test_ambiguous_send_is_reconciled_instead_of_sent_twice(self):
        error = controller.ApiError("transport", None, sent_unknown=True)
        api = FakeApi(parent=session(updated=NOW - 90 * MINUTE), post=error)
        hand = self.make(api)
        first = hand.tick()
        self.assertIn("ambiguous", [item.get("result") for item in first["actions"]])
        nonce = [
            entry["pending_nonce"]
            for entry in hand.state["ledger"].values()
            if entry.get("pending_nonce")
        ][0]
        api.post_error = None
        api.msgs = says(f"continue please [{controller.MARKER} {nonce}]", role="user")
        self.now += 120 * MINUTE
        second = hand.tick()
        self.assertIn("reconciled_pending", [item.get("result") for item in second["actions"]])
        self.assertEqual(len(api.posts), 1)

    def test_accepted_message_and_verified_progress_are_recorded_separately(self):
        api = FakeApi(parent=session(updated=NOW - 90 * MINUTE))
        hand = self.make(api)
        hand.tick()
        entry = [item for item in hand.state["ledger"].values() if item.get("accepted_at")][0]
        self.assertIsNone(entry.get("progress_verified_at"))
        self.now += 5 * MINUTE
        api.parent = session(status="running", updated=self.now, count=140)
        report = hand.tick()
        self.assertNotIn("verified", [item.get("progress") for item in report["actions"]])
        self.now += 11 * MINUTE
        api.msgs = [
            {
                "id": "r1",
                "seq": 101,
                "role": "assistant",
                "createdAt": self.now - MINUTE,
                "content": [{"type": "tool_use", "id": "t1", "name": "Execute"}],
            }
        ]
        report = hand.tick()
        key = f"{SID}|nudge|stale_since:{NOW - 90 * MINUTE}"
        self.assertIn({"key": key, "progress": "verified"}, report["actions"])
        self.assertEqual(hand.state["ledger"][key]["progress_evidence"]["tool_calls"], 1)

    def test_progress_that_never_arrives_is_marked_unverified(self):
        api = FakeApi(parent=session(updated=NOW - 90 * MINUTE))
        hand = self.make(api)
        hand.tick()
        self.now += (self.config["progress_grace_minutes"] + 5) * MINUTE
        report = hand.tick()
        self.assertIn("unverified", [item.get("progress") for item in report["actions"]])

    def test_heartbeat_is_durable_world_readable_and_carries_the_tick(self):
        hand = self.make(FakeApi(parent=session(status="running")))
        hand.tick()
        path = Path(self.dir.name) / "heartbeat.json"
        beat = json.loads(path.read_text())
        self.assertEqual(oct(os.stat(path).st_mode)[-3:], "644")
        self.assertEqual(beat["tick_seq"], 1)
        self.assertEqual(beat["last_tick_at"], NOW)
        self.assertEqual(beat["interval_seconds"], 900)
        self.assertFalse(beat["stopped"])

    def test_operator_stop_switch_blocks_every_action(self):
        api = FakeApi(parent=session(updated=NOW - 600 * MINUTE))
        hand = self.make(api)
        (Path(self.dir.name) / "STOP").write_text("{}")
        report = hand.tick()
        self.assertTrue(report["stopped"])
        self.assertEqual(report["actions"], [])
        self.assertEqual(api.posts, [])

    def test_a_missed_window_is_recorded_as_a_recovered_gap(self):
        api = FakeApi(parent=session(status="running"))
        hand = self.make(api)
        hand.tick()
        self.now += 120 * MINUTE
        report = hand.tick()
        self.assertEqual(report["gap_recovered"]["minutes"], 120.0)
        self.assertEqual(len(hand.state["gaps"]), 1)

    def test_state_survives_a_restart_of_the_process(self):
        api = FakeApi(parent=session(updated=NOW - 90 * MINUTE))
        self.make(api).tick()
        fresh = self.make(api)
        self.assertEqual(fresh.state["tick_seq"], 1)
        self.now += 20 * MINUTE
        report = fresh.tick()
        self.assertEqual(report["tick_seq"], 2)
        self.assertEqual(len(api.posts), 1)

    def test_morning_summary_is_sent_once_a_day(self):
        api = FakeApi(parent=session(status="running"))
        alerts = FakeAlerts()
        self.config["summary_hour"] = 0
        hand = self.make(api, alerts)
        hand.tick()
        summaries = [text for text in alerts.sent if "morning summary" in text]
        self.assertEqual(len(summaries), 1)
        self.now += 60 * MINUTE
        hand.tick()
        self.assertEqual(len([t for t in alerts.sent if "morning summary" in t]), 1)

    def test_a_failed_alert_does_not_stop_the_check(self):
        api = FakeApi(parent=session(attention={"kind": "ask-user", "since": NOW}))
        report = self.make(api, FakeAlerts(fail=True)).tick()
        self.assertEqual([item["result"] for item in report["alerts"]], ["failed"])
        self.assertEqual(report["sessions"][SID]["state"], "blocked_attention")


class Evidence(Base):
    def test_a_child_report_saying_ready_to_archive_does_not_finish_the_parent(self):
        relayed = says("Child done. Ready to archive.", role="user")
        relayed[0]["sender"] = {"kind": "agent", "sessionId": CHILD}
        api = FakeApi(parent=session(updated=NOW - 90 * MINUTE), messages=relayed)
        self.assertEqual(self.make(api).tick()["sessions"][SID]["state"], "stalled")

    def test_tool_output_is_not_read_as_usage_exhaustion(self):
        messages = [
            {
                "role": "tool",
                "content": [
                    {"type": "tool_result", "toolUseId": "t1", "content": "rate limit reached"}
                ],
            },
            {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "Read"}]},
        ]
        api = FakeApi(parent=session(updated=NOW - 90 * MINUTE), messages=messages)
        self.assertEqual(self.make(api).tick()["sessions"][SID]["state"], "stalled")

    def test_an_unanswered_ask_user_call_blocks_without_a_nudge(self):
        messages = [
            {"role": "assistant", "content": [{"type": "tool_use", "id": "q1", "name": "AskUser"}]}
        ]
        api = FakeApi(parent=session(updated=NOW - 600 * MINUTE), messages=messages)
        alerts = FakeAlerts()
        report = self.make(api, alerts).tick()
        self.assertEqual(report["sessions"][SID]["state"], "blocked_attention")
        self.assertEqual(api.posts, [])
        self.assertEqual(len(alerts.sent), 1)

    def test_an_unanswered_tool_call_is_left_alone(self):
        messages = [
            {"role": "assistant", "content": [{"type": "tool_use", "id": "x1", "name": "Execute"}]}
        ]
        api = FakeApi(parent=session(updated=NOW - 600 * MINUTE), messages=messages)
        report = self.make(api).tick()
        self.assertEqual(report["sessions"][SID]["state"], "tool_pending")
        self.assertEqual(api.posts, [])

    def test_the_controllers_own_message_is_never_evidence(self):
        api = FakeApi(parent=session(updated=NOW - 90 * MINUTE))
        hand = self.make(api)
        hand.tick()
        api.msgs = says(api.posts[0][1], role="user")
        self.assertIn("founder decision", api.posts[0][1])
        self.now += 10 * MINUTE
        self.assertEqual(hand.tick()["sessions"][SID]["state"], "stalled")

    def test_exhaustion_that_later_work_moved_past_is_not_current(self):
        messages = says("Continuing with step four now.") + says("usage limit reached")
        api = FakeApi(parent=session(updated=NOW - 90 * MINUTE), messages=messages)
        self.assertEqual(self.make(api).tick()["sessions"][SID]["state"], "stalled")

    def test_a_nudge_without_a_reply_is_not_repeated(self):
        api = FakeApi(parent=session(updated=NOW - 90 * MINUTE))
        alerts = FakeAlerts()
        hand = self.make(api, alerts)
        hand.tick()
        self.now += (self.config["progress_grace_minutes"] + 1) * MINUTE
        hand.tick()
        self.now += 200 * MINUTE
        api.parent = session(updated=self.now - 60 * MINUTE)
        report = hand.tick()
        self.assertIn("held_unverified", [item.get("result") for item in report["actions"]])
        self.assertEqual(len(api.posts), 1)
        self.assertTrue(any("did not resume" in text for text in alerts.sent))


class UsageOnce(Base):
    def test_one_bounded_resume_per_exhaustion_then_a_person_is_told(self):
        api = FakeApi(
            parent=session(updated=NOW - 60 * MINUTE),
            messages=says("usage limit reached; try again in 30 minutes"),
        )
        alerts = FakeAlerts()
        hand = self.make(api, alerts)
        self.now = NOW + 45 * MINUTE
        hand.tick()
        self.assertEqual(len(api.posts), 1)
        self.now += 200 * MINUTE
        report = hand.tick()
        self.assertIn(
            "suppressed_duplicate",
            [item.get("result") for item in report["actions"] if item.get("action") == "resume"],
        )
        self.assertEqual(len(api.posts), 1)
        self.assertTrue(any("still reports a usage limit" in text for text in alerts.sent))


if __name__ == "__main__":
    unittest.main()
