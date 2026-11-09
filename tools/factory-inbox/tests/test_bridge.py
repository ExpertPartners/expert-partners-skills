import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("bridge", Path(__file__).parents[1] / "bridge.py")
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)
SID = "11111111-2222-3333-4444-555555555555"


class FakeAPI:
    def __init__(self):
        self.calls = []
        self.published = []
        self.moved = []
        self.fail = None
        self.files_list = []
        self.texts = {}

    def factory(self, method, path, body=None):
        self.calls.append((method, path, body))
        if self.fail == path:
            raise bridge.BridgeError("transport")
        if method == "GET":
            return {"sessionId": SID, "computerId": "m4"}
        if path == "/sessions":
            return {"sessionId": SID}
        return {"messageId": "message", "status": "pending"}

    def receipt_id(self):
        return "receipt"

    def publish(self, receipt, folder, file_id, name):
        if self.fail == "publish":
            raise bridge.BridgeError("offline")
        self.published.append(name)

    def move_done(self, file_id, config):
        if self.fail == "move":
            raise bridge.BridgeError("offline")
        self.moved.append(file_id)

    def files(self, folder):
        return self.files_list

    def text(self, file):
        return self.texts[file["id"]]


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {
            "state_path": str(self.root / "state"),
            "inbox_path": str(self.root),
            "inbox_id": "inbox",
            "done_id": "done",
            "receipts_id": "receipts",
            "machines": {"M4": {"computer_id": "m4", "cwd": "/workspace"}},
        }
        self.api = FakeAPI()
        self.worker = bridge.Worker(self.config, self.api, self.root / "config.json")
        self.file = {"id": "source", "name": "test.txt", "mimeType": "text/plain"}
        self.home = patch.object(bridge.Path, "home", return_value=self.root / "home")
        self.home.start()
        self.addCleanup(self.home.stop)

    def settings(self, session=SID):
        return bridge.settings_path(session, cwd=self.root)

    def request(self, rid="test", session="new", prompt="Do this\nand this."):
        return f"Request: {rid}\nSession: {session}\nMac: M4\nPrompt:\n{prompt}\n"

    def journal(self):
        return self.root / "state/journal/test.json"

    def test_new_session_and_same_session_message(self):
        first = self.worker.process(self.file, self.request())
        self.assertEqual(first["status"], "accepted")
        self.assertEqual(first["session_id"], SID)
        self.assertTrue(first["session_link"].endswith(SID))
        self.assertEqual(self.api.calls[0][2]["sessionSettings"]["model"], "auto")
        self.worker.process(self.file, self.request("follow", SID))
        self.assertEqual(sum(path == "/sessions" for _, path, _ in self.api.calls), 1)
        self.assertEqual(
            sum(
                method == "POST" and path.endswith("/messages")
                for method, path, _ in self.api.calls
            ),
            2,
        )
        self.assertEqual(self.api.moved, ["source", "source"])

    def test_exact_duplicate_moves_without_resending(self):
        self.worker.process(self.file, self.request())
        self.worker.process({**self.file, "id": "duplicate"}, self.request())
        self.assertEqual(len(self.api.calls), 2)
        self.assertEqual(len(self.api.published), 1)
        self.assertEqual(self.api.moved, ["source", "duplicate"])

    def test_conflicting_revision_does_not_dispatch(self):
        self.worker.process(self.file, self.request())
        with self.assertRaises(bridge.BridgeError):
            self.worker.process(self.file, self.request(prompt="Changed"))
        self.assertEqual(len(self.api.calls), 2)
        self.worker.process(self.file, self.request("revision", prompt="Changed"))
        self.assertEqual(len(self.api.calls), 4)

    def test_three_submission_formats_and_partial_request(self):
        for rid, suffix, mime, line_ending in (
            ("local", ".txt", "text/plain", "\n"),
            ("drive", ".txt", "text/plain", "\n"),
            ("north", ".gdoc", bridge.DOC, "\r\n"),
        ):
            file = {"id": rid, "name": rid if suffix == ".gdoc" else rid + suffix, "mimeType": mime}
            path = self.root / (rid + suffix)
            path.write_text(json.dumps({"doc_id": rid}) if suffix == ".gdoc" else self.request(rid))
            self.api.files_list.append(file)
            self.api.texts[rid] = self.request(rid).replace("\n", line_ending)
        with patch.object(bridge.time, "time", return_value=time.time() + 10):
            self.worker.scan()
        self.assertEqual(len(self.api.moved), 3)
        self.assertEqual(len(self.api.calls), 6)
        path = self.root / "partial.txt"
        path.write_text("Request: partial")
        self.api.files_list = [{"id": "partial", "name": "partial.txt", "mimeType": "text/plain"}]
        self.api.texts["partial"] = "Request: partial"
        with patch.object(bridge.time, "time", return_value=time.time() + 10):
            self.worker.scan()
        self.assertEqual(len(self.api.calls), 6)
        self.api.texts["partial"] = self.request("partial")
        with patch.object(bridge.time, "time", return_value=time.time() + 10):
            self.worker.scan()
        self.assertEqual(len(self.api.calls), 8)

    def test_missing_headers_unknown_fields_and_directory(self):
        for text in (
            "",
            "Prompt:\nHello",
            self.request().replace("Mac: M4", "Mac: M9"),
            self.request().replace("Mac: M4", "Mac: M4\nMac: M4"),
            self.request().replace("Prompt:", "Unknown: x\nPrompt:"),
            self.request().replace("Prompt:", "Directory: relative\nPrompt:"),
            self.request(session=SID).replace("Prompt:", "Directory: /tmp\nPrompt:"),
        ):
            with self.assertRaises(bridge.BridgeError):
                bridge.parse_request(text, self.config["machines"])
        parsed = bridge.parse_request(
            self.request().replace("Prompt:", "Directory: /tmp\nPrompt:"), self.config["machines"]
        )
        self.assertEqual(parsed["Directory"], "/tmp")
        self.assertEqual(self.api.calls, [])

    def test_wrong_machine_never_sends(self):
        with patch.object(self.api, "factory", return_value={"computerId": "other"}):
            with self.assertRaises(bridge.BridgeError):
                self.worker.process(self.file, self.request(session=SID))
        self.assertFalse(self.journal().exists())

    def test_interrupted_posts_never_replay(self):
        for phase in ("creating", "sending"):
            with self.subTest(phase=phase):
                text = self.request()
                request = bridge.parse_request(text, self.config["machines"])
                digest = bridge.hashlib.sha256(
                    json.dumps(request, sort_keys=True).encode()
                ).hexdigest()
                bridge.save(self.journal(), {"digest": digest, "phase": phase})
                receipt = self.worker.process(self.file, text)
                self.assertEqual(receipt["status"], "uncertain")
                self.assertEqual(self.api.calls, [])

    def test_transport_uncertain_and_no_resend(self):
        self.api.fail = "/sessions"
        receipt = self.worker.process(self.file, self.request())
        self.assertEqual(receipt["status"], "uncertain")
        self.worker.process(self.file, self.request())
        self.assertEqual(len(self.api.calls), 1)

    def test_publish_and_move_recover_without_resending(self):
        for failure in ("publish", "move"):
            with self.subTest(failure=failure):
                text = self.request(rid=failure)
                self.api.fail = failure
                before = len(self.api.calls)
                with self.assertRaises(bridge.BridgeError):
                    self.worker.process(self.file, text)
                self.api.fail = None
                self.worker.process(self.file, text)
                self.assertEqual(len(self.api.calls), before + 2)

    def test_created_checkpoint_reuses_session(self):
        request = bridge.parse_request(self.request(), self.config["machines"])
        digest = bridge.hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        bridge.save(self.journal(), {"digest": digest, "phase": "created", "session_id": SID})
        receipt = self.worker.process(self.file, self.request())
        self.assertEqual(receipt["status"], "accepted")
        self.assertEqual(len(self.api.calls), 1)
        self.assertTrue(self.api.calls[0][1].endswith("/messages"))

    def test_symlink_and_unsynced_file_do_not_dispatch(self):
        (self.root / "unsynced.txt").write_text(self.request())
        (self.root / "linked.txt").symlink_to(self.root / "unsynced.txt")
        with patch.object(bridge.time, "time", return_value=time.time() + 10):
            self.worker.scan()
        self.assertEqual(self.api.calls, [])

    def test_close_out_rides_with_every_prompt_without_changing_the_digest(self):
        self.worker.process(self.file, self.request())
        sent = self.api.calls[1][2]["text"]
        self.assertTrue(sent.startswith("Do this\nand this."))
        for part in ("--finish", "test", "--session", SID, "Factory Inbox close-out"):
            self.assertIn(part, sent)
        first = json.loads(self.journal().read_text())["digest"]
        self.worker.process({**self.file, "id": "duplicate"}, self.request())
        self.assertEqual(json.loads(self.journal().read_text())["digest"], first)
        self.assertEqual(len(self.api.calls), 2)

    def test_acceptance_receipt_never_archives(self):
        receipt = self.worker.process(self.file, self.request())
        self.assertEqual(receipt["status"], "accepted")
        self.assertIn("archives itself once the work is done", receipt["meaning"])
        self.assertFalse(self.settings().exists())
        self.assertEqual(self.api.published, ["test.json"])

    def test_finish_publishes_completion_receipt_then_archives(self):
        self.worker.process(self.file, self.request())
        receipt = self.worker.finish("test", SID, "Wrote the file.")
        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(receipt["note"], "Wrote the file.")
        self.assertEqual(self.api.published, ["test.json", "test-completion.json"])
        stamp = json.loads(self.settings().read_text())["archivedAt"]
        state = json.loads(self.journal().read_text())
        self.assertEqual(state["phase"], "completed")
        self.assertEqual(state["archived_at"], stamp)
        self.assertEqual(
            json.loads((self.root / "state/receipts/test-completion.json").read_text())["status"],
            "completed",
        )

    def test_finish_withholds_the_archive_until_the_receipt_is_published(self):
        self.worker.process(self.file, self.request())
        self.api.fail = "publish"
        with self.assertRaises(bridge.BridgeError):
            self.worker.finish("test", SID, "note")
        self.assertFalse(self.settings().exists())
        self.api.fail = None
        self.worker.finish("test", SID, "note")
        self.assertTrue(json.loads(self.settings().read_text())["archivedAt"])

    def test_finish_is_idempotent_and_keeps_the_first_archive_time(self):
        self.worker.process(self.file, self.request())
        self.worker.finish("test", SID, "note")
        stamp = json.loads(self.settings().read_text())["archivedAt"]
        self.worker.finish("test", SID, "note again")
        self.assertEqual(json.loads(self.settings().read_text())["archivedAt"], stamp)
        self.assertEqual(self.api.published.count("test-completion.json"), 2)
        self.assertEqual(len(self.api.calls), 2)

    def test_finish_refuses_an_unknown_request_or_another_session(self):
        with self.assertRaises(bridge.BridgeError):
            self.worker.finish("test", SID, "note")
        self.worker.process(self.file, self.request())
        with self.assertRaises(bridge.BridgeError):
            self.worker.finish("test", "99999999-2222-3333-4444-555555555555", "note")
        self.assertFalse(self.settings().exists())

    def test_follow_up_reopens_an_archived_session_and_records_the_stamp(self):
        bridge.save(self.settings(), {"archivedAt": "2026-11-09T00:00:00.000Z", "model": "auto"})
        receipt = self.worker.process(self.file, self.request("follow", SID))
        self.assertEqual(receipt["status"], "accepted")
        self.assertEqual(receipt["reopened_from_archive"], "2026-11-09T00:00:00.000Z")
        self.assertTrue(self.api.calls[1][1].endswith("/messages"))
        kept = json.loads(self.settings().read_text())
        self.assertNotIn("archivedAt", kept)
        self.assertEqual(kept["model"], "auto")
        self.worker.finish("follow", SID, "done")
        self.assertTrue(json.loads(self.settings().read_text())["archivedAt"])

    def test_follow_up_to_a_live_session_touches_no_archive_state(self):
        bridge.save(self.settings(), {"model": "auto"})
        receipt = self.worker.process(self.file, self.request("follow", SID))
        self.assertIsNone(receipt["reopened_from_archive"])
        self.assertEqual(json.loads(self.settings().read_text()), {"model": "auto"})
        self.assertIsNone(bridge.reopen_session("77777777-8888-9999-aaaa-bbbbbbbbbbbb"))

    def test_archive_preserves_other_settings_and_creates_a_missing_file(self):
        bridge.save(self.settings(), {"model": "auto"})
        stamp = bridge.archive_session(SID, cwd=self.root)
        kept = json.loads(self.settings().read_text())
        self.assertEqual(kept["model"], "auto")
        self.assertEqual(kept["archivedAt"], stamp)
        fresh = "22222222-3333-4444-5555-666666666666"
        bridge.archive_session(fresh, cwd=self.root)
        self.assertTrue(json.loads(self.settings(fresh).read_text())["archivedAt"])


if __name__ == "__main__":
    unittest.main()
