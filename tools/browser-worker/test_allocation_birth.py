"""Interrupted connector isolation retains exact birth evidence, not guessed windows."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import test_browser_jobs as jobs

SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "plugins/operating-doctrine/skills/browser-automation/scripts"
)


class BirthTests(unittest.TestCase):
    def allocation(self, route):
        job = jobs.JobTests().full_job(route)
        job.update(
            metadata=None,
            initial_connector={"connectorId": 17, "windowId": 25},
            allocation_failure={"stage": "connector_isolation", "class": "interrupted"},
        )
        route.begin_allocation_birth(job)
        return job

    def test_interrupted_isolation(self):
        source = (SCRIPTS / "owned_pages.js").read_text()
        fixture = Path(__file__).with_name("allocation_birth_fixture.cjs").read_text()
        run = subprocess.run(
            ["node", "-e", source + fixture], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["cases"], 14)

    def test_journal_identity_mismatch_never_opens_recovery_connector(self):
        for key, value in (
            ("job_id", "c" * 32),
            ("client_name", "peer"),
            ("generation", {"pid": 999, "started": "other"}),
            ("marker", "about:blank"),
            ("connectorId", 99),
            ("token", "f" * 32),
            ("stage", "invented"),
        ):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as root:
                route = jobs.JobTests().route(root)
                job = self.allocation(route)
                path, row = route.allocation_birth(job)
                row[key] = value
                jobs.b.atomic_json(path, row)
                with patch.object(route, "maintenance_connector") as maintenance:
                    with self.assertRaises(jobs.Refusal):
                        route.dispose_failed(job)
                    maintenance.assert_not_called()

    def test_old_generation_never_opens_recovery_connector(self):
        with tempfile.TemporaryDirectory() as root:
            route = jobs.JobTests().route(root)
            job = self.allocation(route)
            route.preflight = lambda: {"pid": 456, "started": "new"}
            with patch.object(route, "maintenance_connector") as maintenance:
                with self.assertRaisesRegex(jobs.Refusal, "browser_generation_changed"):
                    route.dispose_failed(job)
                maintenance.assert_not_called()

    def test_symlink_journal_never_opens_recovery_connector(self):
        with tempfile.TemporaryDirectory() as root:
            route = jobs.JobTests().route(root)
            job = self.allocation(route)
            path, _ = route.allocation_birth(job)
            other = path.with_name("other.json")
            path.rename(other)
            path.symlink_to(other)
            with self.assertRaisesRegex(jobs.Refusal, "allocation_birth_unavailable"):
                route.dispose_failed(job)

    def test_finish_records_intent_before_recovery_remove_and_stops_old_client(self):
        import contextlib

        with tempfile.TemporaryDirectory() as root:
            route = jobs.JobTests().route(root)
            job = self.allocation(route)
            stopped = []
            job["client"] = SimpleNamespace(closed=False, close=lambda: stopped.append(True))
            path, row = route.allocation_birth(job)
            row.update(
                stage="creating",
                origin={"connectorId": 17, "windowId": 25, "groupId": 3},
            )
            jobs.b.atomic_json(path, row)

            @contextlib.contextmanager
            def maintenance():
                self.assertEqual(stopped, [True])
                yield "census"

            def code(_, body):
                self.assertIn("reconcileIsolationBirth(page,", body)
                if '"remove": true' not in body:
                    return {"ids": [17, 18], "windowId": 30, "proof": "proof"}
                saved = json.loads(path.read_text())
                self.assertEqual(saved["cleanup"]["tabIds"], [17, 18])
                return {"closed": True, "windowClosed": True, "windowId": 30}

            route.maintenance_connector = maintenance
            with (
                patch.object(route, "dispose_live", side_effect=jobs.Refusal("state_missing")),
                patch.object(jobs.b, "code", side_effect=code),
            ):
                route.finish(job)
            saved = json.loads((Path(root) / (job["job_id"] + ".json")).read_text())
            self.assertEqual(saved["status"], "finished")
            self.assertEqual(saved["window_disposition"], "closed")
            self.assertTrue(json.loads(path.read_text())["disposition"]["closed"])

    def test_interrupted_maintenance_keeps_its_receipt_and_never_recurses(self):
        with tempfile.TemporaryDirectory() as root:
            route = jobs.JobTests().route(root)
            closed = []
            route.client = lambda _: SimpleNamespace(close=lambda: closed.append(True))
            with patch.object(
                jobs.b,
                "code",
                side_effect=[
                    {"adopted": True},
                    jobs.Refusal("owned_operation_failed:vendor_target_closed"),
                ],
            ) as code:
                with self.assertRaises(jobs.Refusal):
                    with route.maintenance_connector():
                        self.fail("failed allocation yielded a connection")
            self.assertEqual(code.call_count, 2)
            self.assertEqual(closed, [True])
            records = list(Path(root).glob("*.json"))
            self.assertEqual(len(records), 1)
            row = json.loads(records[0].read_text())
            self.assertEqual(row["status"], "failed")
            self.assertIsNone(row["metadata"])
            self.assertEqual(row["allocation_failure"]["stage"], "connector_isolation")
            self.assertTrue((Path(root) / "births" / (row["allocation_birth"] + ".json")).exists())


if __name__ == "__main__":
    unittest.main()
