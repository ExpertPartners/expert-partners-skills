#!/usr/bin/env python3
"""Offline SSH deletion decisions. Command strings are never executed."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


HOOKS = Path(__file__).resolve().parents[1]


class SSHDeletionApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ssh-deletion-approval-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.notes = self.root / "notes"
        self.notes.mkdir()
        self.calls = self.root / "ssh-calls"
        fake = self.root / "ssh"
        fake.write_text(
            "#!/bin/sh\n"
            'printf "%s\\n" "$*" >> "$SSH_FAKE_CALLS"\n'
            '[ "$1" = "-G" ] || exit 255\n'
            'for target do :; done\n'
            'case "$target" in\n'
            '  *@*) user="${target%%@*}" ;;\n'
            '  *) user=ember ;;\n'
            'esac\n'
            'printf "user %s\\nhostname %s\\n" "$user" "${target##*@}"\n'
        )
        fake.chmod(0o700)
        self.env = os.environ.copy()
        for name in (
            "PRE_TOOL_USE_OFF", "BASH_ENV", "ENV", "GUARD_DEADLINE_SECONDS",
            "DELETION_APPROVAL_SSH_CONFIG",
        ):
            self.env.pop(name, None)
        self.env.update(
            HOME=str(self.root),
            DELETION_APPROVAL_DIR=str(self.notes),
            DELETION_APPROVAL_LOG=str(self.root / "audit.log"),
            DELETION_APPROVAL_LIB=str(HOOKS / "lib/deletion-approval-common.sh"),
            DELETION_APPROVAL_SSH_BIN=str(fake),
            SSH_FAKE_CALLS=str(self.calls),
        )

    def tearDown(self):
        if self.calls.exists():
            self.assertTrue(all(
                call.startswith("-G ") for call in self.calls.read_text().splitlines()
            ), "the fake must only receive offline configuration lookups")
        self.assertFalse(list(self.notes.glob("*.claimed.*")))

    def grant(self, path="/tmp/scratch-x", host="ember"):
        args = [
            "bash", str(HOOKS / "deletion-approval-note.sh"), "grant",
            "--target", path, "--quote", "synthetic test approval, not live authority",
            "--session", "offline SSH guard test",
        ]
        if host is not None:
            args.extend(["--host", host])
        result = subprocess.run(
            args, env=self.env, cwd=HOOKS, text=True, capture_output=True, timeout=10
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def decide(self, command, expected, missing_library=False):
        env = self.env.copy()
        if missing_library:
            env["DELETION_APPROVAL_LIB"] = str(self.root / "missing-library")
        result = subprocess.run(
            ["bash", str(HOOKS / "pre-tool-use-enforcement.sh")],
            input=json.dumps({
                "tool_name": "Bash", "tool_input": {"command": command},
                "cwd": str(self.root), "session_id": "offline-ssh-test",
            }),
            env=env, cwd=HOOKS, text=True, capture_output=True, timeout=12,
        )
        self.assertEqual(result.returncode, expected, (command, result.stderr))
        output = json.loads(result.stdout) if result.stdout else {}
        decision = output.get("hookSpecificOutput", {}).get("permissionDecision")
        self.assertEqual(decision, "deny" if expected == 2 else None)
        return output

    def test_required_delete_and_single_use(self):
        command = "ssh ember 'rm -rf /tmp/scratch-x'"
        self.decide(command, 2)
        self.grant()
        output = self.decide(command, 0)
        self.assertIn("consumed", output["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(list(self.notes.iterdir()), [])
        self.decide(command, 2)
        audit = (self.root / "audit.log").read_text()
        self.assertIn("[ALLOW]", audit)
        self.assertIn("[CONSUMED]", audit)
        self.assertIn("ember@ember:/tmp/scratch-x", audit)

    def test_host_path_and_local_notes_are_isolated(self):
        self.grant()
        for command in (
            "ssh other-mac 'rm -rf /tmp/scratch-x'",
            "ssh root@ember 'rm -rf /tmp/scratch-x'",
            "ssh ember 'rm -rf /tmp/scratch-y'",
            "ssh ember 'rm -rf /tmp/scratch-x/child'",
            "ssh ember 'rm -rf /tmp/scratch-x /tmp/unapproved'",
        ):
            with self.subTest(command=command):
                self.decide(command, 2)
                self.assertEqual(len(list(self.notes.glob("*.json"))), 1)
        self.decide("ssh ember 'rm -rf /tmp/scratch-x'", 0)
        self.grant(host=None)
        self.decide("ssh ember 'rm -rf /tmp/scratch-x'", 2)
        self.assertEqual(len(list(self.notes.glob("*.json"))), 1)

    def test_expired_note_is_not_consumed(self):
        self.grant()
        note = next(self.notes.glob("*.json"))
        data = json.loads(note.read_text())
        data["expires_epoch"] = 1
        note.write_text(json.dumps(data))
        self.decide("ssh ember 'rm -rf /tmp/scratch-x'", 2)
        self.assertTrue(note.exists())

    def test_read_only_needs_no_note_or_login_lookup(self):
        for missing in (False, True):
            for command in (
                "ssh ember 'ls ~'",
                "ssh ember 'ls ~/.trash | wc -l'",
                "ssh ember 'ls ~ # rm is only a comment'",
                "ssh ember 'mv /tmp/scratch-x /tmp/renamed-x'",
            ):
                with self.subTest(command=command, missing_library=missing):
                    # Without the parser, keep the existing conservative hold
                    # on pipes and deletion words even inside read-only text.
                    expected = 2 if missing and ("|" in command or "#" in command) else 0
                    self.decide(command, expected, missing_library=missing)
        self.assertFalse(self.calls.exists())

    def test_trash_moves_require_source_note_once(self):
        for destination in (
            "~/.Trash/", "~/.trash/", "/Users/ember/.TRASH/",
            "/Volumes/Backup/.Trashes/501/",
            "/volumes/Backup/.trashes/501/",
        ):
            with self.subTest(destination=destination):
                command = f"ssh ember 'mv /tmp/scratch-x {destination}'"
                self.decide(command, 2)
                self.grant()
                self.decide(command, 0)
                self.assertEqual(list(self.notes.iterdir()), [])
                self.decide(command, 2)

    def test_trash_destination_note_does_not_approve_source(self):
        self.grant(path="~/.Trash/scratch-x")
        self.decide("ssh ember 'mv /tmp/scratch-x ~/.Trash/scratch-x'", 2)
        self.assertEqual(len(list(self.notes.glob("*.json"))), 1)

    def test_trash_move_with_comment_is_not_approvable(self):
        self.grant()
        for command in (
            "ssh ember 'mv /tmp/scratch-x ~/.Trash # cleanup'",
            "ssh ember 'mv /tmp/scratch-x ~/.trash # cleanup'",
            "ssh ember 'mv /tmp/scratch-x ~/.Trash # ; echo done'",
        ):
            with self.subTest(command=command):
                self.decide(command, 2)
                self.assertEqual(len(list(self.notes.glob("*.json"))), 1)
        self.decide("ssh ember 'mv /tmp/scratch-x ~/.Trash'", 0)

    def test_quoted_hash_in_exact_source_is_approvable(self):
        self.grant(path="/tmp/#scratch-x")
        self.decide('ssh ember "mv \'/tmp/#scratch-x\' ~/.Trash"', 0)
        self.assertEqual(list(self.notes.iterdir()), [])

    def test_escaped_space_before_literal_hash_is_approvable(self):
        command = "ssh ember 'mv /tmp/a\\ #b ~/.Trash'"
        self.decide(command, 2)
        self.grant(path="/tmp/a #b")
        self.decide("ssh ember 'mv /tmp/a\\ #b ~/.Trash # cleanup'", 2)
        self.assertEqual(len(list(self.notes.glob("*.json"))), 1)
        self.decide(command, 0)
        self.assertEqual(list(self.notes.iterdir()), [])
        self.decide(command, 2)

    def test_trash_lookalike_names_are_ordinary_renames(self):
        for destination in (
            "~/.trash-backup", "~/.trashcan", "~/.Trashes.old",
            "/tmp/.trash-report/x",
        ):
            for prefix in ("", "env "):
                command = f"ssh ember '{prefix}mv /tmp/scratch-x {destination}'"
                for missing in (False, True):
                    with self.subTest(command=command, missing_library=missing):
                        self.decide(command, 0, missing_library=missing)
        self.assertFalse(self.calls.exists())

    def test_missing_library_blocks_trash_moves(self):
        for command in (
            "ssh ember 'mv /tmp/scratch-x ~/.trash/'",
            "ssh ember 'mv /tmp/scratch-x /Volumes/Backup/.TRASHES/501/'",
            "ssh ember 'mv /tmp/scratch-x ~/.Trash*'",
            "ssh ember 'mv /tmp/scratch-x {~/.Trash,~/.Trash}'",
            "ssh ember 'mv /tmp/scratch-x ~/.Trash${suffix}'",
        ):
            with self.subTest(command=command):
                self.decide(command, 2, missing_library=True)
        self.assertFalse(self.calls.exists())

    def test_unreadable_targets_never_spend_a_note(self):
        self.grant()
        for command in (
            "ssh ember 'rm -rf /tmp/scratch-*'",
            "ssh ember 'rm -rf /tmp/../scratch-x'",
            "ssh ember 'rm -rf scratch-x'",
            "ssh ember 'sudo rm -rf /tmp/scratch-x'",
            "ssh ember 'rm -rf /tmp/scratch-x; rm -rf /tmp/other'",
            "ssh -o Hostname=other-mac ember 'rm -rf /tmp/scratch-x'",
            "ssh ember 'mv /tmp/scratch-* ~/.trash/'",
            "ssh ember 'mv /tmp/scratch-x ~/.Trash*'",
            "ssh ember 'env mv /tmp/scratch-x ~/.Trash*'",
            "ssh ember 'mv /tmp/scratch-x {~/.Trash,~/.Trash}'",
            "ssh ember 'mv /tmp/scratch-x ~/.Trash${suffix}'",
        ):
            with self.subTest(command=command):
                self.decide(command, 2)
                self.assertEqual(len(list(self.notes.glob("*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
