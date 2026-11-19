import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SOURCE = (
    Path(__file__).resolve().parents[2]
    / "plugins/operating-doctrine/skills/browser-automation/scripts/relay_ownership.py"
)
spec = importlib.util.spec_from_file_location("relay_ownership", SOURCE)
ownership = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ownership)


class RelayOwnershipTests(unittest.TestCase):
    observed = {"tabId": 17, "windowId": 14, "urlClass": "blank"}
    saved = {**observed, "jobId": "first", "claimOrdinal": 1}

    def test_never_persists_url(self):
        self.assertEqual(
            ownership.capture_tab({"id": 17, "windowId": 14, "url": "about:blank#token"}),
            self.observed,
        )

    def test_rejects_invalid_vendor_identity(self):
        self.assertIsNone(ownership.capture_tab({"id": True, "windowId": 14, "url": ""}))
        self.assertIsNone(ownership.capture_tab({"id": 17, "windowId": 14}))

    def test_exact_match(self):
        self.assertEqual(
            ownership.authorize_crash_close(self.saved, self.observed, self.saved, "g", "g"),
            "authorized",
        )

    def test_refuses_evidence_changes(self):
        cases = (
            (self.observed, {**self.saved, "jobId": "peer"}, "g", "claim_changed"),
            (self.observed, {**self.saved, "claimOrdinal": 2}, "g", "claim_changed"),
            (
                self.observed,
                {**self.saved, "urlClass": "https"},
                "g",
                "ownership_projection_changed",
            ),
            (self.observed, self.saved, "next", "browser_generation_changed"),
            (None, self.saved, "g", "tab_unobserved"),
            ({**self.observed, "tabId": 19}, self.saved, "g", "tab_unobserved"),
            ({**self.observed, "windowId": 19}, self.saved, "g", "window_changed"),
            ({**self.observed, "urlClass": "https"}, self.saved, "g", "url_class_changed"),
        )
        for observed, latest, generation, expected in cases:
            with self.subTest(expected=expected, observed=observed, latest=latest):
                self.assertEqual(
                    ownership.authorize_crash_close(self.saved, observed, latest, "g", generation),
                    expected,
                )

    def test_durable_recovery_and_replay(self):
        with TemporaryDirectory() as root:
            path = Path(root) / "claims.db"
            ledger = ownership.OwnershipLedger(path)
            saved = ledger.claim("g", "first", self.observed)
            calls = []
            inventory = lambda: [self.observed]

            def close(*args):
                calls.append(args)
                return "closed"

            self.assertEqual(ledger.recover(saved, lambda: "g", inventory, close), "claim_live")
            ledger.mark_released(saved)
            ledger = ownership.OwnershipLedger(path)
            self.assertEqual(ledger.recover(saved, lambda: "g", inventory, close), "closed")
            self.assertEqual(ledger.recover(saved, lambda: "g", inventory, close), "already_closed")
            self.assertEqual(calls, [(14, 17, "blank")])

    def test_later_released_claim_does_not_restore_old_claim(self):
        with TemporaryDirectory() as root:
            ledger = ownership.OwnershipLedger(Path(root) / "claims.db")
            saved = ledger.claim("g", "first", self.observed)
            with self.assertRaisesRegex(ValueError, "unreleased_tab_claim"):
                ledger.claim("g", "peer", self.observed)
            ledger.mark_released(saved)
            peer = ledger.claim("g", "peer", self.observed)
            ledger.mark_released(peer)
            self.assertEqual(
                ledger.recover(saved, lambda: "g", lambda: [self.observed], self.fail),
                "claim_changed",
            )

    def test_records_only_confirmed_same_window_url_class(self):
        with TemporaryDirectory() as root:
            ledger = ownership.OwnershipLedger(Path(root) / "claims.db")
            saved = ledger.claim("g", "first", self.observed)
            with self.assertRaisesRegex(ValueError, "window_changed"):
                ledger.observe(saved, {**self.observed, "windowId": 18})
            latest = ledger.observe(saved, {**self.observed, "urlClass": "https"})
            ledger.mark_released(latest)
            inventory = lambda: [{**self.observed, "urlClass": "https"}]
            self.assertEqual(
                ledger.recover(saved, lambda: "g", inventory, self.fail),
                "ownership_projection_changed",
            )
            self.assertEqual(
                ledger.recover(latest, lambda: "g", inventory, lambda *_: "closed"),
                "closed",
            )

    def test_does_not_close_after_changed_or_ambiguous_observation(self):
        with TemporaryDirectory() as root:
            ledger = ownership.OwnershipLedger(Path(root) / "claims.db")
            saved = ledger.claim("g", "first", self.observed)
            ledger.mark_released(saved)
            for rows, expected in (
                ([], "tab_unobserved"),
                ([self.observed, self.observed], "tab_ambiguous"),
                ([{**self.observed, "windowId": 15}], "window_changed"),
                ([{**self.observed, "urlClass": "https"}], "url_class_changed"),
            ):
                with self.subTest(expected=expected):
                    self.assertEqual(
                        ledger.recover(saved, lambda: "g", lambda: rows, self.fail), expected
                    )
            generations = iter(["g", "next"])
            self.assertEqual(
                ledger.recover(
                    saved, lambda: next(generations), lambda: [self.observed], self.fail
                ),
                "browser_generation_changed",
            )
