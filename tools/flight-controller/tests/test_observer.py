#!/usr/bin/env python3
"""Fixtures for the off-host observer: a dead or stopped M2 must read differently."""

import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

SPEC = importlib.util.spec_from_file_location("observer", Path(__file__).parents[1] / "observer.py")
observer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(observer)

NOW = 1_700_000_000_000
MINUTE = 60_000
CONFIG = {
    "stale_minutes": 40,
    "strikes_before_alert": 2,
    "read_command": ["/bin/echo", "x"],
    "read_timeout_seconds": 5,
}


def done(stdout, code=0):
    return subprocess.CompletedProcess(["read"], code, stdout.encode(), b"")


class Reading(unittest.TestCase):
    def test_remote_control_noise_before_the_json_is_ignored(self):
        payload = "Fetching computer info...\nConnected\n" + json.dumps({"tick_seq": 7})
        beat = observer.read_heartbeat(CONFIG, runner=lambda *a, **k: done(payload))
        self.assertEqual(beat["tick_seq"], 7)

    def test_a_failed_read_is_an_error_not_an_empty_heartbeat(self):
        with self.assertRaises(observer.ObserverError):
            observer.read_heartbeat(CONFIG, runner=lambda *a, **k: done("no such file", 1))

    def test_unparsable_output_is_an_error(self):
        with self.assertRaises(observer.ObserverError):
            observer.read_heartbeat(CONFIG, runner=lambda *a, **k: done("Connected\n"))


class Verdicts(unittest.TestCase):
    def test_fresh_heartbeat_is_ok(self):
        verdict, due = observer.evaluate(
            {"last_tick_at": NOW - 5 * MINUTE, "tick_seq": 3}, None, {}, NOW, CONFIG
        )
        self.assertEqual(verdict["level"], "ok")
        self.assertFalse(due)

    def test_operator_stop_is_not_an_outage(self):
        verdict, due = observer.evaluate(
            {"last_tick_at": NOW - 600 * MINUTE, "stopped": True}, None, {}, NOW, CONFIG
        )
        self.assertEqual(verdict["level"], "stopped")
        self.assertFalse(due)

    def test_one_stale_read_waits_and_the_second_alerts(self):
        beat = {"last_tick_at": NOW - 90 * MINUTE}
        first, due = observer.evaluate(beat, None, {"strikes": 0}, NOW, CONFIG)
        self.assertEqual((first["level"], due), ("stale", False))
        second, due = observer.evaluate(beat, None, first, NOW, CONFIG)
        self.assertEqual((second["level"], due, second["strikes"]), ("stale", True, 2))

    def test_an_unreachable_mac_alerts_after_the_same_strikes(self):
        first, due = observer.evaluate({}, "transport failed", {"strikes": 0}, NOW, CONFIG)
        self.assertEqual((first["level"], due), ("unreachable", False))
        second, due = observer.evaluate({}, "transport failed", first, NOW, CONFIG)
        self.assertTrue(due)
        self.assertEqual(second["level"], "unreachable")

    def test_recovery_clears_the_strikes(self):
        verdict, due = observer.evaluate(
            {"last_tick_at": NOW - MINUTE}, None, {"strikes": 4}, NOW, CONFIG
        )
        self.assertEqual(verdict["strikes"], 0)
        self.assertFalse(due)


if __name__ == "__main__":
    unittest.main()
