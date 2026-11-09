#!/usr/bin/env python3
"""Hermetic M4 Batch 2 guard tests. Never invokes a production execute entry.

Vendor/process, snapshot, database and estate filesystem observations are fakes.
The only mutable real files are synthetic test stores and retained legacy fixtures
under a newly created temporary directory. No cleanup/deletion is performed.
Run with the reviewed Python interpreter: python -I hooks/tests/test_m4_batch2.py.
"""
from __future__ import annotations

import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock


HOOKS = Path(__file__).resolve().parents[1]
FIXTURES = HOOKS / "tests" / "fixtures" / "m4-batch2"
KEYS = """3fac9f70aa5c9ccf 03676be6c5876144 67eb4586ca667318 705bc6b22212b352
9eac9498388ae25e 96a8727b140d6939 bce731a0395adf49 cc2145a2fe1558fa
7f312557c12f11a3 3f410cde517faec3 a3586cc356aa4ace 1ce9283feb7d83f2
8003d8991b0d346b 33664ddc0e10cefa dcf0514efa8ecddd 1bf7c3c15bf47d04
bd03aaf280724e38 f19f78a55038d137 69f9afb961c37556 705d23756ff7dacc
ffe2131771d88588 1ddbeaccabfe00a4 32026684e21afda6 1a3c4333f3a90708
67a0730928194b24 e41f203b7505f1fb ac0ed6aa23b37c1e 9dc43daea2065b57""".split()
ACTIVE = ["6583fba12287d067", "9833c18b2d85bc59"]
ACTION = "npx:" + KEYS[0]
SNAP_ACTION = "snapshot:131322"
QUOTE = "Synthetic test approval only. This fixture cannot authorize production."
REPLACEMENT = "A1111111-B222-4333-8444-555555555555"
OLD_UUID = "FCA82852-B4F7-477B-B344-49DD9FB4660B"
NODE = "/opt/homebrew/Cellar/node/25.9.0_2/bin/node"
NPM = "/opt/homebrew/lib/node_modules/npm/bin/npm-cli.js"
HOME = "/Users/allisongaddy"
TEST_ROOT = None
RUNTIME = None
CORE = None
POLICY = None


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def setUpModule():
    global TEST_ROOT, RUNTIME, CORE, POLICY
    TEST_ROOT = Path(tempfile.mkdtemp(prefix="m4-guard-hermetic-", dir="/private/tmp"))
    # Importing definitions must not execute a vendor process. Catch accidental
    # subprocess use during import, before any adapter can be supplied.
    with mock.patch.object(subprocess, "run", side_effect=AssertionError("process at module import")), \
         mock.patch.object(subprocess, "Popen", side_effect=AssertionError("process at module import")):
        RUNTIME = load_module("m4_test_runtime", HOOKS / "lib" / "m4-batch2-runtime.py")
        CORE = load_module("m4_test_executor", HOOKS / "lib" / "m4-batch2-executor.py")
    POLICY = json.loads((HOOKS / "policies" / "m4-batch2-20260923.json").read_text())


def tearDownModule():
    print("Retained hermetic evidence directory:", TEST_ROOT)


@contextlib.contextmanager
def no_processes():
    """Fake adapters are the only permissible process boundary in core tests."""
    with contextlib.ExitStack() as stack:
        for obj, name in [(subprocess, "run"), (subprocess, "Popen"), (os, "system"),
                          (os, "execv"), (os, "execve"), (os, "execvp"), (os, "execvpe"),
                          (os, "posix_spawn"), (os, "posix_spawnp")]:
            if hasattr(obj, name):
                stack.enter_context(mock.patch.object(obj, name, side_effect=AssertionError("real process forbidden")))
        yield


class ScriptedRuntime:
    """Transaction-window unit double, supplemental to real Runtime tests below."""
    def __init__(self, policy):
        self.policy = policy
        self.TargetSkip = RUNTIME.TargetSkip
        self.calls = []
        self.events = []
        self.stage_errors = {}
        self.vendor_result = {"returncode": 0, "stdout": "synthetic success", "stderr": ""}
        self.identity_value = {"path": HOME + "/.npm/_npx/" + KEYS[0], "inode": 100,
                               "exists": True, "is_dir": True, "no_symlinks": True,
                               "metadata_sha256": "a" * 64, "package_sha256": "b" * 64,
                               "lock_sha256": "c" * 64, "external_links": []}
        self.post_verified = True
        self.before_dispatch = None

    def stage(self, name):
        self.events.append(name)
        failure = self.stage_errors.get(name)
        if failure:
            raise failure

    def context_check(self):
        self.stage("context")

    def identity(self, action):
        self.stage("identity")
        RUNTIME.fixed_argv(self.policy, action)
        return copy.deepcopy(self.identity_value)

    def target_observation(self, action):
        RUNTIME.fixed_argv(self.policy, action)
        return copy.deepcopy(self.identity_value)

    def fixed_argv(self, action):
        return RUNTIME.fixed_argv(self.policy, action)

    def precheck(self, action, replacement_uuid=None, outcomes=None, proof=True):
        self.stage("precheck")
        return {"identity": self.identity(action), "protected": {"unchanged": True}, "proof": proof}

    def dispatch_check(self, action, prior, replacement_uuid=None, outcomes=None):
        self.stage("dispatch_check")
        if self.before_dispatch:
            self.before_dispatch()
        return copy.deepcopy(prior)

    def dispatch(self, action, argv):
        self.calls.append((action, list(argv)))
        self.stage("dispatch")
        if list(argv) != self.fixed_argv(action):
            raise AssertionError("unexpected vendor argv")
        return copy.deepcopy(self.vendor_result)

    def postcheck(self, action, prior, replacement_uuid=None, outcomes=None):
        self.stage("postcheck")
        return {"verified": self.post_verified, "protected": {"unchanged": True}}


class CoreTest(unittest.TestCase):
    def setUp(self):
        self.policy = copy.deepcopy(POLICY)
        self.policy["approval_sha256"] = hashlib.sha256(QUOTE.encode()).hexdigest()
        self.policy_digest = digest(self.policy)
        self.now = [1800000000.0]
        self.directory = Path(tempfile.mkdtemp(prefix="core-", dir=TEST_ROOT)) / "store"
        self.runtime = ScriptedRuntime(self.policy)
        self.store = CORE.SecureStore(self.directory)
        self.executor = CORE.Executor(self.policy, self.runtime, self.store, self.policy_digest,
                                      clock=lambda: self.now[0])
        self.process_guard = no_processes()
        self.process_guard.__enter__()
        self.addCleanup(self.process_guard.__exit__, None, None, None)

    def grant(self, action=ACTION, replacement=None):
        return self.executor.grant(action, QUOTE, replacement_uuid=replacement)

    def note_path(self, action=ACTION):
        return self.directory / self.store.note_name(action)

    def assert_no_dispatch(self):
        self.assertEqual(self.runtime.calls, [])

    def test_preview_creates_no_store_and_no_claim(self):
        result = self.executor.preview(ACTION)
        self.assertEqual(result["status"], "PREVIEW")
        self.assertFalse(result["consumes_note"])
        self.assertFalse(self.directory.exists())
        self.assert_no_dispatch()

    def test_grant_is_separate_preview_nonconsuming_and_success_owned_once(self):
        result = self.grant()
        self.assertEqual(result["status"], "GRANTED")
        self.assert_no_dispatch()
        before = self.note_path().read_bytes()
        self.executor.preview(ACTION)
        self.executor.preview(ACTION)
        self.assertEqual(before, self.note_path().read_bytes())
        result = self.executor.execute(ACTION)
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(len(self.runtime.calls), 1)
        self.assertTrue((self.directory / self.store.claim_name(ACTION)).exists())
        self.assertTrue((self.directory / self.store.outcome_name(ACTION)).exists())
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        with self.assertRaises(Exception):
            self.grant()
        self.assertEqual(len(self.runtime.calls), 1)

    def test_missing_note_denies(self):
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        self.assert_no_dispatch()

    def test_wrong_quote_cannot_grant(self):
        with self.assertRaises(Exception):
            self.executor.grant(ACTION, "unapproved fixture quote")
        self.assert_no_dispatch()

    def test_expired_note_denies(self):
        self.grant()
        self.now[0] += 901
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        self.assert_no_dispatch()

    def test_identity_changed_since_grant_denies(self):
        self.grant()
        self.runtime.identity_value["inode"] += 1
        result = self.executor.execute(ACTION)
        self.assertEqual(result["status"], "SKIPPED")
        self.assert_no_dispatch()

    def test_malformed_note_denies(self):
        self.grant()
        self.note_path().write_text("{not-json}")
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        self.assert_no_dispatch()

    def test_copied_note_wrong_action_denies(self):
        self.grant()
        other = "npx:" + KEYS[1]
        path = self.note_path(other)
        path.write_bytes(self.note_path().read_bytes())
        path.chmod(0o600)
        with self.assertRaises(Exception):
            self.executor.execute(other)
        self.assert_no_dispatch()

    def test_safety_refusal_before_claim_records_skip_only(self):
        self.grant()
        self.runtime.stage_errors["precheck"] = RUNTIME.TargetSkip("synthetic active consumer", self.runtime.target_observation(ACTION))
        result = self.executor.execute(ACTION)
        self.assertEqual(result["status"], "SKIPPED")
        self.assertFalse((self.directory / self.store.claim_name(ACTION)).exists())
        self.assert_no_dispatch()

    def test_dispatch_safety_change_denies_and_claim_remains_unavailable(self):
        self.grant()
        self.runtime.stage_errors["dispatch_check"] = RUNTIME.SafetyError("synthetic target changed")
        try:
            self.executor.execute(ACTION)
        except Exception:
            pass
        self.assert_no_dispatch()
        self.assertTrue((self.directory / self.store.claim_name(ACTION)).exists())
        self.runtime.stage_errors.clear()
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        self.assert_no_dispatch()

    def test_vendor_nonzero_is_terminal_without_retry(self):
        self.grant()
        self.runtime.vendor_result["returncode"] = 1
        result = self.executor.execute(ACTION)
        self.assertIn(result["status"], ["FAILED", "AMBIGUOUS"])
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        self.assertEqual(len(self.runtime.calls), 1)

    def test_spawn_uncertainty_is_terminal(self):
        self.grant()
        self.runtime.stage_errors["dispatch"] = OSError("synthetic uncertain spawn")
        result = self.executor.execute(ACTION)
        self.assertEqual(result["status"], "AMBIGUOUS")
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        self.assertEqual(len(self.runtime.calls), 1)

    def test_postcondition_false_is_not_verified(self):
        self.grant()
        self.runtime.post_verified = False
        result = self.executor.execute(ACTION)
        self.assertNotEqual(result["status"], "VERIFIED")
        self.assertEqual(len(self.runtime.calls), 1)

    def test_postcheck_exception_is_terminal(self):
        self.grant()
        self.runtime.stage_errors["postcheck"] = RUNTIME.SafetyError("synthetic protected state changed")
        result = self.executor.execute(ACTION)
        self.assertIn(result["status"], ["FAILED", "AMBIGUOUS"])
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        self.assertEqual(len(self.runtime.calls), 1)

    def test_audit_failure_before_dispatch_closed(self):
        self.grant()
        with mock.patch.object(self.store, "append_audit", side_effect=OSError("synthetic log failure")):
            with self.assertRaises(Exception):
                self.executor.execute(ACTION)
        self.assert_no_dispatch()

    def test_claim_failure_before_dispatch_closed(self):
        self.grant()
        original = self.store.create
        def fail_claim(name, obj):
            if name == self.store.claim_name(ACTION):
                raise OSError("synthetic claim failure")
            return original(name, obj)
        with mock.patch.object(self.store, "create", side_effect=fail_claim):
            with self.assertRaises(Exception):
                self.executor.execute(ACTION)
        self.assert_no_dispatch()

    def test_two_concurrent_attempts_have_one_child(self):
        self.grant()
        barrier = threading.Barrier(3)
        results = []
        def attempt():
            barrier.wait()
            try:
                other = CORE.Executor(self.policy, self.runtime, CORE.SecureStore(self.directory),
                                      self.policy_digest, clock=lambda: self.now[0])
                results.append(other.execute(ACTION))
            except Exception as exc:
                results.append(type(exc).__name__)
        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(10)
            self.assertFalse(thread.is_alive(), "concurrent transaction did not finish")
        self.assertEqual(len(self.runtime.calls), 1)
        self.assertEqual(sum(isinstance(x, dict) and x.get("status") == "VERIFIED" for x in results), 1)

    def test_note_binding_fields_and_lifetime_cannot_be_changed(self):
        changes = {"schema": 2, "note_id": "bad", "single_use": False, "task_id": "wrong-task",
                   "action": "npx:" + ACTIVE[0], "policy_sha256": "0" * 64,
                   "argv_sha256": "0" * 64, "identity_sha256": "0" * 64,
                   "approval_quote": "different quote", "approval_sha256": "0" * 64,
                   "created_epoch": self.now[0] + 1, "expires_epoch": self.now[0] + 901,
                   "ttl_seconds": 901, "replacement_uuid": REPLACEMENT}
        for index, (field, value) in enumerate(changes.items()):
            with self.subTest(field=field):
                action = "npx:" + KEYS[index]
                result = self.grant(action)
                changed = copy.deepcopy(result["note"])
                changed[field] = value
                # Keep a matching synthetic audit grant so the binding predicate,
                # not merely an audit digest mismatch, must reject this field.
                with self.store.lock():
                    self.store.append_audit("GRANT", {"action": action, "note": changed,
                                                      "note_sha256": CORE.digest(changed)})
                    with self.assertRaises(Exception):
                        self.executor._validate_note(action, self.runtime.fixed_argv(action), changed)
        self.assert_no_dispatch()

    def test_legacy_note_and_duplicate_json_fields_cannot_authorize(self):
        self.grant()
        self.note_path().write_text('{"target":"/Users/synthetic/target","expires_epoch":9999999999}')
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        for raw in ['{"schema":1,"schema":1}', '{"x":NaN}', '{"x":Infinity}']:
            with self.subTest(raw=raw), self.assertRaises(Exception):
                CORE.strict_json(raw)
        self.assert_no_dispatch()

    def test_snapshot_grant_requires_complete_durable_outcomes(self):
        with self.assertRaises(Exception):
            self.grant(SNAP_ACTION, REPLACEMENT)
        self.assert_no_dispatch()

    def test_snapshot_receipts_require_policy_binding_and_terminal_audit(self):
        with self.store.lock():
            for key in KEYS:
                action = "npx:" + key
                row = {"schema": 1, "status": "SKIPPED", "action": action, "task_id": self.policy["task_id"],
                       "policy_sha256": self.policy_digest, "reason": "synthetic refusal", "finished_epoch": self.now[0]}
                self.store.create(self.store.outcome_name(action), row)
                if key != KEYS[0]:
                    self.store.append_audit("TERMINAL", {"action": action, "status": "SKIPPED", "outcome_sha256": CORE.digest(row)})
            with self.assertRaises(Exception):
                self.executor._outcomes(SNAP_ACTION)
            first = self.store.read(self.store.outcome_name(ACTION))
            self.store.append_audit("TERMINAL", {"action": ACTION, "status": "SKIPPED", "outcome_sha256": CORE.digest(first)})
            self.assertEqual(len(self.executor._outcomes(SNAP_ACTION)), 28)
        path = self.directory / self.store.outcome_name(ACTION)
        first["policy_sha256"] = "0" * 64
        path.write_text(json.dumps(first))
        with self.store.lock():
            with self.assertRaises(Exception):
                self.executor._outcomes(SNAP_ACTION)
        self.assert_no_dispatch()

    def test_expiry_at_dispatch_is_sticky_no_child(self):
        self.grant()
        self.runtime.before_dispatch = lambda: self.now.__setitem__(0, self.now[0] + 901)
        result = self.executor.execute(ACTION)
        self.assertEqual(result["status"], "FAILED")
        self.assert_no_dispatch()
        self.assertTrue((self.directory / self.store.claim_name(ACTION)).exists())

    def test_audit_is_durable_before_vendor_call(self):
        self.grant()
        original = self.runtime.dispatch
        def assert_audit(action, argv):
            rows = self.store.audit_records()
            events = [row["event"] for row in rows]
            self.assertEqual(events, ["GRANT", "PREPARED", "CLAIMED", "DISPATCHING"])
            prepared = next(r["payload"] for r in rows if r["event"] == "PREPARED")
            self.assertEqual(prepared["argv"], argv)
            self.assertIn("note", prepared)
            self.assertIn("preconditions", prepared)
            self.assertTrue(self.store.exists(self.store.claim_name(ACTION)))
            return original(action, argv)
        with mock.patch.object(self.runtime, "dispatch", side_effect=assert_audit):
            self.assertEqual(self.executor.execute(ACTION)["status"], "VERIFIED")

    def test_crash_after_claim_before_dispatch_cannot_replay(self):
        self.grant()
        original = self.store.append_audit
        def crash(event, payload):
            if event == "CLAIMED":
                raise KeyboardInterrupt("synthetic crash after permanent claim")
            return original(event, payload)
        with mock.patch.object(self.store, "append_audit", side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                self.executor.execute(ACTION)
        self.assertTrue((self.directory / self.store.claim_name(ACTION)).exists())
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        self.assert_no_dispatch()

    def test_terminal_audit_failure_never_reports_success_or_reopens(self):
        self.grant()
        original = self.store.append_audit
        def fail_terminal(event, payload):
            if event == "TERMINAL":
                raise OSError("synthetic terminal audit unavailable")
            return original(event, payload)
        with mock.patch.object(self.store, "append_audit", side_effect=fail_terminal):
            with self.assertRaises(Exception):
                self.executor.execute(ACTION)
        self.assertEqual(len(self.runtime.calls), 1)
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        self.assertEqual(len(self.runtime.calls), 1)

    def test_lock_fsync_and_partial_audit_fail_closed(self):
        self.grant()
        with mock.patch.object(CORE.os, "fsync", side_effect=OSError("synthetic fsync failure")):
            with self.assertRaises(Exception):
                self.executor.execute(ACTION)
        self.assert_no_dispatch()
        audit = self.directory / "audit.jsonl"
        with audit.open("ab") as stream:
            stream.write(b'{"partial":')
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        self.assert_no_dispatch()

    def test_symlink_note_and_insecure_store_fail_closed(self):
        with self.store.lock():
            pass
        inert = self.directory.parent / "inert-note.json"
        inert.write_text("{}")
        inert.chmod(0o600)
        self.note_path().symlink_to(inert)
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        self.directory.chmod(0o755)
        with self.assertRaises(Exception):
            self.executor.execute(ACTION)
        self.assert_no_dispatch()

    def test_platform_denied_launch_synthetic_noninvocation_preserves_note(self):
        self.grant()
        before = {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file()}
        # This deliberately does not call execute. It documents the boundary;
        # it is not a claim about a real platform auto-review decision.
        platform_allows_launch = False
        if platform_allows_launch:
            self.executor.execute(ACTION)
        after = {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file()}
        self.assertEqual(before, after)
        self.assert_no_dispatch()

    def test_systemic_precheck_errors_are_blocking_not_successful_skips(self):
        for index, reason in enumerate(["tool identity changed", "database health regression", "recovery archive drift",
                                         "protected snapshot changed", "incomplete open-handle inventory"]):
            with self.subTest(reason=reason):
                action = "npx:" + KEYS[index]
                self.runtime.stage_errors.clear()
                self.grant(action)
                self.runtime.stage_errors["precheck"] = RUNTIME.SafetyError(reason)
                try:
                    result = self.executor.execute(action)
                except Exception:
                    result = {"status": "BLOCKED"}
                self.assertIn(result["status"], ["BLOCKED", "FAILED", "AMBIGUOUS"])
                self.assert_no_dispatch()


class FakeFS:
    """Every estate lookup is virtual; unknown paths are errors, never fallback."""
    def __init__(self, policy):
        self.policy = policy
        self.identities = {}
        self.fingerprints = {}
        self.files = dict(policy["tools"])
        self.source_tree = policy["npm_tree_sha256"]
        self.archive_rows = copy.deepcopy(policy["archives"])
        self.present = {HOME + "/.claude/pre-tool-use-enforcement-off": False}
        self.snapshot_overrides = {}
        self.snapshot_identity_overrides = {}
        self.mount_dirs = []
        for i, key in enumerate(KEYS):
            path = HOME + "/.npm/_npx/" + key
            target = policy["targets"][key]
            self.identities[path] = {"path": path, "exists": True, "is_dir": True,
                "no_symlinks": True, "inode": target["inode"],
                "top_names": ["node_modules", "package-lock.json", "package.json"],
                "metadata_sha256": target["metadata_sha256"], "package_sha256": target["package_sha256"],
                "lock_sha256": target["lock_sha256"], "external_links": []}
            self.fingerprints[path] = {"exists": True, "inode": target["inode"], "metadata_sha256": target["metadata_sha256"]}
            self.present[path] = True
        for row in policy["protected_trees"]:
            self.fingerprints[row["path"]] = copy.deepcopy(row["fingerprint"])
            self.present[row["path"]] = row["fingerprint"]["exists"]
        for i, path in enumerate([HOME + "/.npmrc", HOME + "/.npm/_cacache"]):
            self.fingerprints.setdefault(path, {"exists": True, "inode": 8000 + i, "metadata_sha256": "d" * 64})
        for path in policy["snapshot_representatives"]:
            self.snapshot_overrides[path] = True

    def identity(self, path):
        return copy.deepcopy(self.identities[str(path)])

    def fingerprint(self, path):
        return copy.deepcopy(self.fingerprints[str(path)])

    def file_hash(self, path):
        return self.files[str(path)]

    def tree_hash(self, path):
        if str(path) != "/opt/homebrew/lib/node_modules/npm":
            raise AssertionError("unexpected source tree")
        return self.source_tree

    def archives(self, root):
        if root != self.policy["archive_root"]:
            raise AssertionError("unexpected archive root")
        return copy.deepcopy(self.archive_rows)

    def exists(self, path):
        return self.present[str(path)]

    def mkdir_mount(self, path):
        if not str(path).startswith("/private/tmp/m4-batch2-restore-"):
            raise AssertionError("unexpected mount path")
        self.mount_dirs.append(str(path))

    def snapshot_path_exists(self, mount, path):
        if str(mount) not in self.mount_dirs:
            raise AssertionError("snapshot lookup without virtual mount")
        if str(path) in self.snapshot_overrides:
            return self.snapshot_overrides[str(path)]
        if str(path) in self.identities:
            return self.present[str(path)]
        raise AssertionError("unregistered snapshot path")

    def snapshot_identity(self, mount, path):
        if str(mount) not in self.mount_dirs:
            raise AssertionError("snapshot identity lookup without virtual mount")
        if str(path) in self.snapshot_identity_overrides:
            return copy.deepcopy(self.snapshot_identity_overrides[str(path)])
        return copy.deepcopy(self.identities[str(path)])

    def mark_absent(self, key):
        path = HOME + "/.npm/_npx/" + key
        self.present[path] = False
        self.fingerprints[path] = {"exists": False, "inode": None, "metadata_sha256": None}
        self.identities[path]["exists"] = False


class FakeRunner:
    """Exact read-only argv fixtures plus one recorded fake destructive route."""
    def __init__(self, policy, fs):
        self.policy = policy
        self.fs = fs
        self.calls = []
        self.vendor_calls = []
        self.failures = {}
        self.outputs = {}
        self.volumes = []
        self.mounted = None
        self.leave_mounted = False
        self.readonly = True
        self.apply_vendor_effect = True
        self.vendor_returncode = 0
        self.health = "running healthy\n"
        self.postgres = "/var/run/postgresql:5432 - accepting connections\n"
        self.ps = "1 0 /sbin/launchd\n42 1 /Applications/Synthetic.app/Contents/MacOS/Synthetic\n"
        self.lsof = "p42\ncSynthetic\nfcwd\ntDIR\nn/Users/synthetic\nf1\ntCHR\nn/dev/null\n"
        self.ps_stderr = ""
        self.lsof_stderr = ""
        self.mount_base = "/dev/disk3s1s1 on / (apfs, sealed, local, read-only)\n/dev/disk3s5 on /System/Volumes/Data (apfs, local, journaled)\n"
        data = policy["data_uuid"]
        root_ids = [x[0] for x in policy["protected_snapshots"] if x[0] != data]
        self.root_uuid = root_ids[0] if root_ids else "AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE"
        self.add_volume(data, "/System/Volumes/Data", "disk3s5")
        self.add_volume(self.root_uuid, "/", "disk3s1")
        for volume_uuid, name, snapshot_uuid in policy["protected_snapshots"]:
            volume = next((v for v in self.volumes if v["uuid"] == volume_uuid), None)
            if volume is None:
                volume = self.add_volume(volume_uuid, "/Volumes/Synthetic" + str(len(self.volumes)), "disk8s" + str(len(self.volumes)))
            volume["snapshots"].append({"SnapshotName": name, "SnapshotUUID": snapshot_uuid})
        self.data_volume()["snapshots"].append({"SnapshotName": RUNTIME.OLD_NAME, "SnapshotUUID": OLD_UUID})
        self.data_volume()["snapshots"].append({"SnapshotName": "com.apple.TimeMachine.2026-09-23-235959.local", "SnapshotUUID": REPLACEMENT})

    def add_volume(self, uuid, mount, device):
        volume = {"uuid": uuid, "mount": mount, "device": device, "snapshots": []}
        self.volumes.append(volume)
        return volume

    def data_volume(self):
        return next(v for v in self.volumes if v["mount"] == "/System/Volumes/Data")

    def result(self, stdout="", stderr="", returncode=0):
        return {"returncode": returncode, "stdout": stdout, "stderr": stderr}

    def plist(self, value):
        return self.result(plistlib.dumps(value).decode())

    def __call__(self, argv, *, timeout=60):
        args = tuple(argv)
        self.calls.append((args, timeout))
        if args in self.failures:
            value = self.failures[args]
            if isinstance(value, BaseException):
                raise value
            return self.result(returncode=value)
        if args in self.outputs:
            return copy.deepcopy(self.outputs[args])
        if args == ("/bin/ps", "-axo", "pid=,ppid=,command="):
            return self.result(self.ps, self.ps_stderr)
        if args == ("/usr/sbin/lsof", "-nP", "-Fpcfnt"):
            return self.result(self.lsof, self.lsof_stderr)
        if args == ("/usr/local/bin/docker", "inspect", "--format", "{{.State.Status}} {{.State.Health.Status}}", "supabase_db_FounderCommandCenter"):
            return self.result(self.health)
        if args == ("/usr/local/bin/docker", "exec", "supabase_db_FounderCommandCenter", "pg_isready", "-U", "postgres", "-d", "postgres"):
            return self.result(self.postgres)
        if args == ("/usr/sbin/diskutil", "apfs", "list", "-plist"):
            return self.plist({"Containers": [{"Volumes": [{"DeviceIdentifier": v["device"], "APFSVolumeUUID": v["uuid"],
                        "Roles": ["System"] if v["uuid"] == self.policy["boot_volume_uuid"] else ["Data"]} for v in self.volumes]}]})
        if len(args) == 5 and args[:3] == ("/usr/sbin/diskutil", "apfs", "listSnapshots") and args[4] == "-plist":
            volume = next(v for v in self.volumes if v["mount"] == args[3])
            return self.plist({"Snapshots": copy.deepcopy(volume["snapshots"])})
        if len(args) == 4 and args[:3] == ("/usr/sbin/diskutil", "info", "-plist"):
            volume = next(v for v in self.volumes if args[3] in (v["mount"], v["device"]))
            return self.plist({"VolumeUUID": volume["uuid"], "DeviceIdentifier": volume["device"],
                               "MountPoint": volume["mount"], "APFSContainerFree": 42000000000})
        if args == ("/usr/bin/tmutil", "listlocalsnapshots", "/System/Volumes/Data"):
            return self.result("Snapshots for disk /System/Volumes/Data:\n" + "\n".join(s["SnapshotName"] for s in self.data_volume()["snapshots"]) + "\n")
        if args == ("/sbin/mount",):
            extra = ""
            if self.mounted:
                extra = "/dev/disk3s5s99 on " + self.mounted + " (apfs, local" + (", read-only" if self.readonly else "") + ")\n"
            return self.result(self.mount_base + extra)
        if len(args) == 7 and args[:3] == ("/sbin/mount_apfs", "-o", "rdonly,nobrowse") and args[3] == "-s":
            self.mounted = args[6]
            return self.result()
        if len(args) == 2 and args[0] == "/sbin/umount":
            if args[1] != self.mounted:
                raise AssertionError("unmount mismatched virtual mount")
            if not self.leave_mounted:
                self.mounted = None
            return self.result()
        if list(args) == RUNTIME.fixed_argv(self.policy, SNAP_ACTION):
            self.vendor_calls.append(list(args))
            if self.apply_vendor_effect and not self.vendor_returncode:
                self.data_volume()["snapshots"] = [s for s in self.data_volume()["snapshots"] if s["SnapshotUUID"] != OLD_UUID]
            return self.result("synthetic snapshot vendor", returncode=self.vendor_returncode)
        if len(args) == 8 and args[:5] == (NODE, NPM, "cache", "npx", "rm"):
            if list(args) != RUNTIME.fixed_argv(self.policy, "npx:" + args[5]):
                raise AssertionError("unregistered vendor argv")
            self.vendor_calls.append(list(args))
            if self.apply_vendor_effect and not self.vendor_returncode:
                self.fs.mark_absent(args[5])
            return self.result("synthetic npx vendor", returncode=self.vendor_returncode)
        raise AssertionError("unregistered command: " + repr(args))


class RuntimeFixture:
    def __init__(self):
        self.policy = copy.deepcopy(POLICY)
        self.policy["approval_sha256"] = hashlib.sha256(QUOTE.encode()).hexdigest()
        self.fs = FakeFS(self.policy)
        self.runner = FakeRunner(self.policy, self.fs)
        self.env = {"HOME": HOME, "CODEX_THREAD_ID": self.policy["task_id"]}
        self.runtime = RUNTIME.Runtime(self.policy, runner=self.runner, fs=self.fs, env=self.env)
        self.outcomes = [{"action": "npx:" + key, "task_id": self.policy["task_id"],
                          "policy_sha256": digest(self.policy), "status": "SKIPPED",
                          "reason": "synthetic active consumer", "finished_epoch": 1700000000.0,
                          "skip_observation": copy.deepcopy(self.fs.identities[HOME + "/.npm/_npx/" + key])} for key in KEYS]

    def snapshot_precheck(self):
        return self.runtime.precheck(SNAP_ACTION, replacement_uuid=REPLACEMENT, outcomes=self.outcomes)


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.fixture = RuntimeFixture()
        self.f = self.fixture
        self.guard = no_processes()
        self.guard.__enter__()
        self.addCleanup(self.guard.__exit__, None, None, None)

    def test_exact_allowlist_and_full_argv_all_28(self):
        self.assertEqual(POLICY["npx_keys"], KEYS)
        self.assertEqual(POLICY["active_keys"], ACTIVE)
        for key in KEYS:
            with self.subTest(key=key):
                self.assertEqual(RUNTIME.fixed_argv(self.f.policy, "npx:" + key),
                    [NODE, NPM, "cache", "npx", "rm", key, "--cache", HOME + "/.npm"])
                result = self.f.runtime.precheck("npx:" + key)
                self.assertEqual(result["identity"]["path"], HOME + "/.npm/_npx/" + key)
        self.assertEqual(RUNTIME.fixed_argv(self.f.policy, SNAP_ACTION),
                         ["/usr/bin/tmutil", "deletelocalsnapshots", "2026-09-23-131322"])
        self.assertEqual(self.f.runner.vendor_calls, [])

    def test_actions_unlisted_malformed_protected_and_injected_deny(self):
        bad = [None, "", "npx:", "npx:0000000000000000", "npx:" + ACTIVE[0], "npx:" + ACTIVE[1],
               "snapshot:141244", "snapshot:*", "snapshot:2026-09-23", "snapshot:131322 extra",
               ACTION.upper(), " " + ACTION, ACTION + "\n", ACTION + " extra", ACTION + ";touch /tmp/unsafe",
               "npx:$(id)", "npx:`id`", "npx:../" + KEYS[0], "npx:*", "npx:" + KEYS[0] + "/",
               "/bin/rm", "ENV=x " + ACTION, [ACTION], {"action": ACTION}]
        for action in bad:
            with self.subTest(action=action), self.assertRaises(Exception):
                RUNTIME.fixed_argv(self.f.policy, action)
        self.assertEqual(self.f.runner.vendor_calls, [])

    def test_command_affecting_environment_denies(self):
        for name in ["NODE_OPTIONS", "NODE_PATH", "NODE_EXTRA_CA_CERTS", "NPM_CONFIG_CACHE", "npm_config_userconfig",
                     "DYLD_INSERT_LIBRARIES", "LD_PRELOAD", "PYTHONPATH", "PYTHONHOME", "DELETION_APPROVAL_LIB",
                     "M4_BATCH2_TEST", "BASH_ENV", "ENV", "PRE_TOOL_USE_OFF", "BASH_FUNC_x%%", "TZ"]:
            with self.subTest(variable=name):
                f = RuntimeFixture()
                f.env[name] = "synthetic"
                with self.assertRaises(Exception):
                    f.runtime.context_check()

    def test_wrong_context_and_disabled_guard_deny(self):
        for field in ["HOME", "CODEX_THREAD_ID"]:
            with self.subTest(field=field):
                f = RuntimeFixture()
                f.env[field] = "wrong"
                with self.assertRaises(Exception):
                    f.runtime.context_check()
        self.f.fs.present[HOME + "/.claude/pre-tool-use-enforcement-off"] = True
        with self.assertRaises(Exception):
            self.f.runtime.context_check()

    def test_tool_hash_and_npm_dependency_tree_drift_deny(self):
        for path in self.f.policy["tools"]:
            with self.subTest(path=path):
                f = RuntimeFixture()
                f.fs.files[path] = "0" * 64
                with self.assertRaises(Exception):
                    f.runtime.precheck(ACTION)
        self.f.fs.source_tree = "0" * 64
        with self.assertRaises(Exception):
            self.f.runtime.precheck(ACTION)

    def test_target_path_package_metadata_and_symlink_safety(self):
        changes = {"path": HOME + "/.npm/_npx", "exists": False, "is_dir": False, "no_symlinks": False,
                   "inode": -1, "metadata_sha256": "wrong", "package_sha256": "wrong", "lock_sha256": "wrong",
                   "top_names": ["notes", "node_modules", "package-lock.json", "package.json"],
                   "external_links": ["node_modules/escape"]}
        for field, value in changes.items():
            with self.subTest(field=field):
                f = RuntimeFixture()
                f.fs.identities[HOME + "/.npm/_npx/" + KEYS[0]][field] = value
                with self.assertRaises(Exception):
                    f.runtime.identity(ACTION)

    def test_real_localfs_rejects_dangling_symlink_target(self):
        # Only an inert synthetic symlink under the retained test directory.
        directory = Path(tempfile.mkdtemp(prefix="dangling-", dir=TEST_ROOT))
        target = directory / "dangling"
        target.symlink_to(directory / "never-created")
        fs = RUNTIME.LocalFS()
        with self.assertRaises(Exception):
            fs.identity(str(target))
        self.assertTrue(fs.exists(str(target)), "dangling target must count as present for postcheck")

    def test_process_and_open_handle_consumers_deny(self):
        target = HOME + "/.npm/_npx/" + KEYS[0]
        for kind, output in [("ps", "90 1 node " + target + "/node_modules/tool\n"),
                             ("lsof", "p90\ncnode\nfcwd\ntDIR\nn" + target + "\n"),
                             ("lsof", "p90\ncnode\nf5\ntREG\nn" + target + "/package.json\n")]:
            with self.subTest(kind=kind, output=output):
                f = RuntimeFixture()
                setattr(f.runner, kind, output)
                with self.assertRaises(Exception):
                    f.runtime.precheck(ACTION)

    def test_empty_malformed_or_inaccessible_process_inventories_deny(self):
        for kind, output in [("ps", ""), ("ps", "garbage\n"), ("ps", "1 INVALID /sbin/launchd\n"),
                             ("lsof", ""), ("lsof", "garbage\n"),
                             ("lsof", "p42\ncSynthetic\nfcwd\ntDIR\nn/Users/synthetic\np222\n"),
                             ("lsof", "p42\ncSynthetic\nfnot-valid\ntREG\nn/Users/synthetic\n")]:
            with self.subTest(kind=kind, output=output):
                f = RuntimeFixture()
                setattr(f.runner, kind, output)
                with self.assertRaises(Exception):
                    f.runtime.precheck(ACTION)
        self.f.runner.lsof_stderr = "inaccessible process information"
        with self.assertRaises(Exception):
            self.f.runtime.precheck(ACTION)

    def test_failed_readonly_commands_deny(self):
        commands = [("/bin/ps", "-axo", "pid=,ppid=,command="), ("/usr/sbin/lsof", "-nP", "-Fpcfnt"),
                    ("/usr/sbin/diskutil", "apfs", "list", "-plist"), ("/usr/bin/tmutil", "listlocalsnapshots", "/System/Volumes/Data")]
        for command in commands:
            with self.subTest(command=command):
                f = RuntimeFixture()
                f.runner.failures[command] = 1
                with self.assertRaises(Exception):
                    f.runtime.precheck(ACTION)
                self.assertEqual(f.runner.vendor_calls, [])

    def test_db_health_and_all_18_archive_rows_are_real_predicates(self):
        for index in range(18):
            with self.subTest(archive=index):
                f = RuntimeFixture()
                f.fs.archive_rows[index]["bytes"] += 1
                with self.assertRaises(Exception):
                    f.runtime.precheck(ACTION)
        for attr, value in [("health", "exited unhealthy\n"), ("postgres", "rejecting connections\n")]:
            with self.subTest(health=attr):
                f = RuntimeFixture()
                setattr(f.runner, attr, value)
                with self.assertRaises(Exception):
                    f.runtime.precheck(ACTION)

    def test_every_protected_tree_drift_denies(self):
        for row in self.f.policy["protected_trees"]:
            with self.subTest(path=row["path"]):
                f = RuntimeFixture()
                f.fs.fingerprints[row["path"]]["metadata_sha256"] = "drift"
                with self.assertRaises(Exception):
                    f.runtime.precheck(ACTION)

    def test_dispatch_rechecks_target_consumer_inventory_and_configuration(self):
        mutations = [lambda f: f.fs.identities[HOME + "/.npm/_npx/" + KEYS[0]].update(inode=-1),
                     lambda f: setattr(f.runner, "ps", "90 1 node " + HOME + "/.npm/_npx/" + KEYS[0] + "/tool\n"),
                     lambda f: f.fs.fingerprints[HOME + "/.npmrc"].update(metadata_sha256="drift"),
                     lambda f: setattr(f.runner, "mount_base", f.runner.mount_base + "synthetic new mount\n"),
                     lambda f: f.runner.add_volume("BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB", "/Volumes/New", "disk9s1")]
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                f = RuntimeFixture()
                prior = f.runtime.precheck(ACTION)
                mutation(f)
                with self.assertRaises(Exception):
                    f.runtime.dispatch_check(ACTION, prior)
                self.assertEqual(f.runner.vendor_calls, [])

    def test_positive_npx_dispatch_and_postcondition_with_actual_runtime(self):
        prior = self.f.runtime.precheck(ACTION)
        protected = copy.deepcopy(prior["protected"])
        self.f.runtime.dispatch_check(ACTION, prior)
        self.f.runtime.dispatch(ACTION, RUNTIME.fixed_argv(self.f.policy, ACTION))
        post = self.f.runtime.postcheck(ACTION, prior)
        self.assertTrue(post["verified"])
        self.assertEqual(post["protected"], protected)
        self.assertEqual(len(self.f.runner.vendor_calls), 1)
        self.assertEqual(post["retained_snapshot_yield_guarantee_bytes"], 0)

    def test_wrong_vendor_argv_cannot_reach_fake_vendor(self):
        argv = RUNTIME.fixed_argv(self.f.policy, ACTION)
        for wrong in [argv[:-3], argv + [KEYS[1]], ["/bin/sh", "-c", "echo synthetic"], argv[:-1] + ["/tmp/other"]]:
            with self.subTest(argv=wrong), self.assertRaises(Exception):
                self.f.runtime.dispatch(ACTION, wrong)
        self.assertEqual(self.f.runner.vendor_calls, [])

    def test_npx_postconditions_require_absence_and_protected_siblings(self):
        prior = self.f.runtime.precheck(ACTION)
        with self.assertRaises(Exception):
            self.f.runtime.postcheck(ACTION, prior)
        self.f.fs.mark_absent(KEYS[0])
        self.f.fs.fingerprints[HOME + "/.npm/_npx/" + KEYS[1]]["metadata_sha256"] = "drift"
        with self.assertRaises(Exception):
            self.f.runtime.postcheck(ACTION, prior)

    def test_real_runtime_and_core_complete_single_operation(self):
        directory = Path(tempfile.mkdtemp(prefix="composed-", dir=TEST_ROOT)) / "store"
        store = CORE.SecureStore(directory)
        executor = CORE.Executor(self.f.policy, self.f.runtime, store, digest(self.f.policy))
        executor.grant(ACTION, QUOTE)
        outcome = executor.execute(ACTION)
        self.assertEqual(outcome["status"], "VERIFIED")
        self.assertEqual(len(self.f.runner.vendor_calls), 1)
        with self.assertRaises(Exception):
            executor.execute(ACTION)
        self.assertEqual(len(self.f.runner.vendor_calls), 1)

    def test_systemic_real_runtime_failure_does_not_become_successful_skip(self):
        mutations = [lambda f: setattr(f.runner, "health", "exited unhealthy\n"),
                     lambda f: f.fs.archive_rows[0].update(bytes=-1),
                     lambda f: setattr(f.fs, "source_tree", "0" * 64)]
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                f = RuntimeFixture()
                directory = Path(tempfile.mkdtemp(prefix="systemic-", dir=TEST_ROOT)) / "store"
                executor = CORE.Executor(f.policy, f.runtime, CORE.SecureStore(directory), digest(f.policy))
                executor.grant(ACTION, QUOTE)
                mutation(f)
                try:
                    result = executor.execute(ACTION)
                except Exception:
                    result = {"status": "BLOCKED"}
                self.assertIn(result["status"], ["BLOCKED", "FAILED", "AMBIGUOUS"])
                self.assertEqual(f.runner.vendor_calls, [])

    def test_eligible_unchanged_consumer_and_changed_key_grants_skip_without_note(self):
        for kind in ["consumer", "changed"]:
            with self.subTest(kind=kind):
                f = RuntimeFixture()
                target = HOME + "/.npm/_npx/" + KEYS[0]
                if kind == "consumer":
                    f.runner.ps = "90 1 node " + target + "/node_modules/tool\n"
                else:
                    f.fs.identities[target]["metadata_sha256"] = "e" * 64
                    f.fs.fingerprints[target]["metadata_sha256"] = "e" * 64
                directory = Path(tempfile.mkdtemp(prefix="eligible-skip-", dir=TEST_ROOT)) / "store"
                store = CORE.SecureStore(directory)
                executor = CORE.Executor(f.policy, f.runtime, store, digest(f.policy), clock=lambda: 1700000100.0)
                result = executor.grant(ACTION, QUOTE)
                self.assertEqual(result["status"], "SKIPPED")
                self.assertEqual(result["skip_observation"], f.fs.identities[target])
                self.assertFalse((directory / store.note_name(ACTION)).exists())
                self.assertFalse((directory / store.claim_name(ACTION)).exists())
                self.assertEqual(f.runner.vendor_calls, [])
                f.outcomes[0] = result
                self.assertTrue(f.snapshot_precheck()["mount_proof"]["all_npx_outcomes_match"])

    def test_changed_key_after_grant_is_captured_skip_and_cannot_dispatch(self):
        f = self.f
        directory = Path(tempfile.mkdtemp(prefix="changed-after-grant-", dir=TEST_ROOT)) / "store"
        store = CORE.SecureStore(directory)
        executor = CORE.Executor(f.policy, f.runtime, store, digest(f.policy), clock=lambda: 1700000100.0)
        executor.grant(ACTION, QUOTE)
        target = HOME + "/.npm/_npx/" + KEYS[0]
        f.fs.identities[target]["metadata_sha256"] = "e" * 64
        f.fs.fingerprints[target]["metadata_sha256"] = "e" * 64
        result = executor.execute(ACTION)
        self.assertEqual(result["status"], "SKIPPED")
        self.assertEqual(result["skip_observation"], f.fs.identities[target])
        self.assertFalse((directory / store.claim_name(ACTION)).exists())
        self.assertEqual(f.runner.vendor_calls, [])
        f.outcomes[0] = result
        self.assertTrue(f.snapshot_precheck()["mount_proof"]["all_npx_outcomes_match"])

    def test_unavailable_inventory_is_systemic_even_if_key_metadata_changed(self):
        target = HOME + "/.npm/_npx/" + KEYS[0]
        self.f.fs.identities[target]["metadata_sha256"] = "e" * 64
        self.f.runner.lsof = "garbage\n"
        with self.assertRaises(RUNTIME.SafetyError) as caught:
            self.f.runtime.precheck(ACTION)
        self.assertNotIsInstance(caught.exception, RUNTIME.TargetSkip)

    def test_unsafe_symlink_never_becomes_eligible_skip(self):
        target = HOME + "/.npm/_npx/" + KEYS[0]
        self.f.fs.identities[target]["no_symlinks"] = False
        directory = Path(tempfile.mkdtemp(prefix="unsafe-skip-", dir=TEST_ROOT)) / "store"
        store = CORE.SecureStore(directory)
        executor = CORE.Executor(self.f.policy, self.f.runtime, store, digest(self.f.policy))
        with self.assertRaises(Exception):
            executor.grant(ACTION, QUOTE)
        self.assertFalse((directory / store.outcome_name(ACTION)).exists())
        self.assertFalse((directory / store.note_name(ACTION)).exists())
        self.assertEqual(self.f.runner.vendor_calls, [])

class LsofTypedInventoryTest(unittest.TestCase):
    """Synthetic Darwin field streams; never invokes the installed lsof."""
    blank_types = ("NPOLICY", "NEXUS", "rte", "PIPE")

    def setUp(self):
        self.f = RuntimeFixture()
        self.guard = no_processes()
        self.guard.__enter__()
        self.addCleanup(self.guard.__exit__, None, None, None)

    @staticmethod
    def stream(records, pid=42, command="Synthetic"):
        lines = ["p" + str(pid), "c" + command]
        for descriptor, kind, name in records:
            lines.extend(["f" + descriptor, "t" + kind, "n" + name])
        return "\n".join(lines) + "\n"

    def assert_systemic_denial(self, value):
        self.f.runner.lsof = value
        with self.assertRaises(RUNTIME.SafetyError) as caught:
            self.f.runtime.precheck(ACTION)
        self.assertNotIsInstance(caught.exception, RUNTIME.TargetSkip)
        self.assertEqual(self.f.runner.vendor_calls, [])

    @classmethod
    def large_stream(cls):
        groups = []
        for group in range(600):
            records = [("cwd", "DIR", "/Users/synthetic/group-" + str(group)),
                       ("twd", "DIR", "/private/tmp/synthetic-group-" + str(group)),
                       ("fp.", "REG", "/Users/synthetic/fileport-" + str(group))]
            records.extend((str(i), kind, "") for i, kind in enumerate(cls.blank_types))
            records.extend((str(i), "REG", "/Users/synthetic/group-" + str(group) + "/file-" + str(i))
                           for i in range(4, 37))
            groups.append(cls.stream(records, pid=1000 + group, command="SyntheticWorker"))
        return "".join(groups)

    def test_realistic_24000_record_typed_inventory_passes_without_vendor_call(self):
        value = self.large_stream()
        lines = value.splitlines()
        self.assertEqual(sum(line.startswith("p") for line in lines), 600)
        self.assertEqual(sum(line.startswith("f") for line in lines), 24000)
        self.assertEqual(sum(line.startswith("t") for line in lines), 24000)
        self.assertEqual(sum(line.startswith("n") for line in lines), 24000)
        self.assertIn("ffp.\ntREG\nn/Users/synthetic/fileport-", value)
        self.assertIn("ftwd\ntDIR\nn/private/tmp/synthetic-group-", value)
        for kind in self.blank_types:
            self.assertIn("t" + kind + "\nn\n", value)
        self.f.runner.lsof = value
        result = self.f.runtime.precheck(ACTION)
        self.assertTrue(result["consumers"]["open_handle_inventory_complete"])
        self.assertIn((("/usr/sbin/lsof", "-nP", "-Fpcfnt"), 90), self.f.runner.calls)
        self.assertFalse(any("-Fpcfn" in args for args, _ in self.f.runner.calls))
        self.assertEqual(self.f.runner.vendor_calls, [])

    def test_exact_observed_nonpath_types_accept_empty_name_records(self):
        for kind in self.blank_types:
            with self.subTest(kind=kind):
                self.f.runner.lsof = self.stream([("cwd", "DIR", "/Users/synthetic"), ("17", kind, "")])
                result = self.f.runtime.precheck(ACTION)
                self.assertTrue(result["consumers"]["open_handle_inventory_complete"])
        self.assertEqual(self.f.runner.vendor_calls, [])

    def test_blank_path_capable_unknown_or_nonexact_types_are_systemic_blocks(self):
        for kind in ["REG", "DIR", "CHR", "BLK", "FIFO", "LINK", "IPv4", "unix", "FUTURETYPE",
                     "npolicy", "nexus", "RTE", "pipe", ""]:
            with self.subTest(kind=kind):
                self.assert_systemic_denial(self.stream([("cwd", "DIR", "/Users/synthetic"), ("17", kind, "")]))

    def test_fileport_and_task_working_directory_descriptors_are_exact(self):
        for descriptor, kind in [("fp.", "REG"), ("twd", "DIR")]:
            with self.subTest(descriptor=descriptor):
                self.f.runner.lsof = self.stream([(descriptor, kind, "/Users/synthetic/exact-descriptor")])
                self.assertTrue(self.f.runtime.precheck(ACTION)["consumers"]["open_handle_inventory_complete"])
        for descriptor in ["fp", "fp..", "fp.extra", "p.", "twd-extra", "TWD", "", "-1", "1x"]:
            with self.subTest(invalid_descriptor=descriptor):
                self.assert_systemic_denial(self.stream([(descriptor, "REG", "/Users/synthetic/file")]))

    def test_structurally_valid_unknown_named_type_passes_and_target_still_blocks(self):
        self.f.runner.lsof = self.stream([("17", "FUTURETYPE", "/Users/synthetic/unrelated")])
        self.assertTrue(self.f.runtime.precheck(ACTION)["consumers"]["open_handle_inventory_complete"])
        target = HOME + "/.npm/_npx/" + KEYS[0]
        self.f.runner.lsof = self.stream([("17", "FUTURETYPE", target + "/package.json")])
        with self.assertRaises(RUNTIME.TargetSkip) as caught:
            self.f.runtime.precheck(ACTION)
        self.assertEqual(caught.exception.observation, self.f.fs.identities[target])
        self.assertEqual(self.f.runner.vendor_calls, [])

    def test_malformed_reordered_or_duplicate_field_tags_are_blocks(self):
        examples = [
            "cSynthetic\np42\nf1\ntREG\nn/Users/synthetic/file\n",
            "p42\nf1\ncSynthetic\ntREG\nn/Users/synthetic/file\n",
            "p42\ncSynthetic\ntREG\nf1\nn/Users/synthetic/file\n",
            "p42\ncSynthetic\nf1\nn/Users/synthetic/file\ntREG\n",
            "p42\ncSynthetic\ncAgain\nf1\ntREG\nn/Users/synthetic/file\n",
            "p42\ncSynthetic\nf1\ntREG\ntDIR\nn/Users/synthetic/file\n",
            "p42\ncSynthetic\nf1\ntREG\nn/Users/synthetic/file\nn/Users/synthetic/again\n",
            "p42\ncSynthetic\nf1\ntREG\nn/Users/synthetic/file\ncAgain\n",
            "p42\ncSynthetic\nf1\ntREG\nx/Users/synthetic/file\n",
            "p42\ncSynthetic\nf1\ntREG\nn/Users/synthetic/fi\x00le\n",
            "p42\nc\nf1\ntREG\nn/Users/synthetic/file\n",
            "p-1\ncSynthetic\nf1\ntREG\nn/Users/synthetic/file\n",
            "p\ncSynthetic\nf1\ntREG\nn/Users/synthetic/file\n",
            "p٤٢\ncSynthetic\nf1\ntREG\nn/Users/synthetic/file\n",
        ]
        for index, value in enumerate(examples):
            with self.subTest(example=index):
                self.assert_systemic_denial(value)

    def test_truncated_files_processes_and_missing_final_newline_are_blocks(self):
        valid = self.stream([("cwd", "DIR", "/Users/synthetic")])
        suffixes = ["p222\n", "p222\ncSynthetic\n", "p222\ncSynthetic\nf1\n",
                    "p222\ncSynthetic\nf1\ntREG\n", "f2\n", "f2\ntPIPE\n", "f2\ntREG\n"]
        for suffix in suffixes:
            with self.subTest(suffix=suffix):
                self.assert_systemic_denial(valid + suffix)
        self.assert_systemic_denial(valid[:-1])
        self.assert_systemic_denial(self.stream([("cwd", "DIR", "/Users/synthetic"), ("17", "PIPE", "")])[:-1])

    def test_ambiguous_filesystem_names_are_systemic_blocks(self):
        names = ["relative/path", " -- partial/path", "/Users/synthetic -- /partial/path",
                 "/Users/synthetic/(?)", "/Users/synthetic/file (?)"]
        for kind in ["REG", "DIR", "CHR", "BLK", "FIFO", "LINK"]:
            for name in names:
                with self.subTest(kind=kind, name=name):
                    self.assert_systemic_denial(self.stream([("17", kind, name)]))

    def test_target_paths_detected_after_large_stream_and_across_every_type(self):
        target = HOME + "/.npm/_npx/" + KEYS[0]
        prefix = self.large_stream()
        for kind, name in [("DIR", target), ("REG", target + "/package.json"),
                           ("REG", target + "/removed-file (deleted)"), ("NPOLICY", target),
                           ("NEXUS", target + "/file"), ("rte", target), ("PIPE", target + "/file"),
                           ("FUTURETYPE", target + "/file")]:
            with self.subTest(kind=kind, name=name):
                self.f.runner.lsof = prefix + self.stream([("17", kind, name)], pid=99999)
                with self.assertRaises(RUNTIME.TargetSkip):
                    self.f.runtime.precheck(ACTION)
                self.assertEqual(self.f.runner.vendor_calls, [])

    def test_target_consumer_cannot_hide_later_inventory_truncation(self):
        target = HOME + "/.npm/_npx/" + KEYS[0]
        self.assert_systemic_denial(self.stream([("17", "REG", target + "/package.json")]) + "p222\n")


class SnapshotTest(unittest.TestCase):
    def setUp(self):
        self.f = RuntimeFixture()
        self.guard = no_processes()
        self.guard.__enter__()
        self.addCleanup(self.guard.__exit__, None, None, None)

    def test_real_core_28_receipts_then_bound_snapshot_executes_exactly_once(self):
        directory = Path(tempfile.mkdtemp(prefix="snapshot-composed-", dir=TEST_ROOT)) / "store"
        store = CORE.SecureStore(directory)
        executor = CORE.Executor(self.f.policy, self.f.runtime, store, digest(self.f.policy), clock=lambda: 1700000100.0)
        for key in KEYS:
            action = "npx:" + key
            self.assertEqual(executor.grant(action, QUOTE)["status"], "GRANTED")
            self.assertEqual(executor.execute(action)["status"], "VERIFIED")
        self.assertEqual(len(self.f.runner.vendor_calls), 28)
        grant = executor.grant(SNAP_ACTION, QUOTE, replacement_uuid=REPLACEMENT)
        self.assertEqual(grant["note"]["replacement_uuid"], REPLACEMENT)
        self.assertEqual(grant["note"]["identity"]["uuid"], OLD_UUID)
        self.assertEqual(grant["note"]["identity"]["data_uuid"], self.f.policy["data_uuid"])
        self.assertEqual(len(self.f.runner.vendor_calls), 28)
        result = executor.execute(SNAP_ACTION)
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(len(self.f.runner.vendor_calls), 29)
        self.assertEqual(self.f.runner.vendor_calls[-1], RUNTIME.fixed_argv(self.f.policy, SNAP_ACTION))
        with self.assertRaises(Exception):
            executor.execute(SNAP_ACTION)
        self.assertEqual(len(self.f.runner.vendor_calls), 29)
        self.assertIsNone(self.f.runner.mounted)

    def test_positive_replacement_proof_preserves_141244_and_other_snapshots(self):
        prior = self.f.snapshot_precheck()
        self.assertTrue(prior["mount_proof"]["read_only"])
        self.assertTrue(prior["mount_proof"]["unmounted"])
        self.assertIsNone(self.f.runner.mounted)
        before = self.f.runtime._snapset(prior["inventory"])
        self.assertTrue(any("141244" in row[1] for row in before))
        self.f.runtime.dispatch_check(SNAP_ACTION, prior, REPLACEMENT, self.f.outcomes)
        self.f.runtime.dispatch(SNAP_ACTION, RUNTIME.fixed_argv(self.f.policy, SNAP_ACTION))
        post = self.f.runtime.postcheck(SNAP_ACTION, prior, REPLACEMENT, self.f.outcomes)
        self.assertTrue(post["verified"])
        self.assertEqual(before - {(self.f.policy["data_uuid"], RUNTIME.OLD_NAME, OLD_UUID)}, self.f.runtime._snapset(post["inventory"]))
        self.assertEqual(len(self.f.runner.vendor_calls), 1)
        self.assertEqual(post["retained_snapshot_yield_guarantee_bytes"], 0)

    def test_mixed_verified_and_explicit_skipped_outcomes(self):
        for i in [0, 2, 9]:
            self.f.outcomes[i]["status"] = "VERIFIED"
            self.f.fs.mark_absent(KEYS[i])
        self.assertTrue(self.f.snapshot_precheck()["mount_proof"]["all_npx_outcomes_match"])

    def test_old_uuid_name_data_and_protected_snapshot_changes_deny(self):
        mutations = [lambda f: f.runner.data_volume()["snapshots"][-2].update(SnapshotUUID=REPLACEMENT),
                     lambda f: f.runner.data_volume()["snapshots"][-2].update(SnapshotName="com.apple.TimeMachine.2026-09-23-131323.local"),
                     lambda f: f.runner.data_volume().update(uuid="wrong-data-uuid"),
                     lambda f: f.runner.data_volume()["snapshots"].pop(-2),
                     lambda f: next(v for v in f.runner.volumes if v["snapshots"])["snapshots"][0].update(SnapshotUUID="wrong")]
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                f = RuntimeFixture()
                mutation(f)
                with self.assertRaises(Exception):
                    f.snapshot_precheck()
                self.assertEqual(f.runner.vendor_calls, [])

    def test_replacement_identity_absence_staleness_and_volume_deny(self):
        for replacement in [None, "", OLD_UUID, "not-uuid", REPLACEMENT.lower(), "99999999-2222-4333-8444-555555555555"]:
            with self.subTest(replacement=replacement), self.assertRaises(Exception):
                self.f.runtime.precheck(SNAP_ACTION, replacement, self.f.outcomes)
        for mutation in [lambda f: f.runner.data_volume()["snapshots"][-1].update(SnapshotName="com.apple.TimeMachine.2020-01-01-000000.local"),
                         lambda f: f.runner.data_volume()["snapshots"][-1].update(SnapshotName="wrong-name"),
                         lambda f: f.runner.volumes[1]["snapshots"].append(f.runner.data_volume()["snapshots"].pop())]:
            f = RuntimeFixture()
            mutation(f)
            with self.assertRaises(Exception):
                f.snapshot_precheck()

    def test_outcomes_require_complete_distinct_current_success_or_skip(self):
        mutations = [lambda rows: rows.pop(), lambda rows: rows.append(copy.deepcopy(rows[0])),
                     lambda rows: rows[0].update(status="AMBIGUOUS"), lambda rows: rows[0].update(status="FAILED"),
                     lambda rows: rows[0].update(task_id="wrong"), lambda rows: rows[0].update(reason=""),
                     lambda rows: rows[0].update(finished_epoch=0), lambda rows: rows[0].update(action="npx:" + ACTIVE[0]),
                     lambda rows: rows[0].update(status="VERIFIED")]
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                f = RuntimeFixture()
                mutation(f.outcomes)
                with self.assertRaises(Exception):
                    f.snapshot_precheck()

    def test_verified_success_present_or_skipped_absent_in_snapshot_denies(self):
        for status, live, captured in [("VERIFIED", False, True), ("SKIPPED", True, False)]:
            with self.subTest(status=status):
                f = RuntimeFixture()
                f.outcomes[0]["status"] = status
                if not live:
                    f.fs.mark_absent(KEYS[0])
                f.fs.snapshot_overrides[HOME + "/.npm/_npx/" + KEYS[0]] = captured
                with self.assertRaises(Exception):
                    f.snapshot_precheck()
                self.assertIsNone(f.runner.mounted)

    def test_every_snapshot_representative_missing_denies(self):
        for path in self.f.policy["snapshot_representatives"]:
            with self.subTest(path=path):
                f = RuntimeFixture()
                f.fs.snapshot_overrides[path] = False
                with self.assertRaises(Exception):
                    f.snapshot_precheck()
                self.assertIsNone(f.runner.mounted)

    def test_exact_timestamp_on_another_volume_blocks_but_different_hour_does_not(self):
        volume = self.f.runner.add_volume("CCCCCCCC-DDDD-4EEE-8FFF-111111111111", "/Volumes/Other", "disk10s1")
        volume["snapshots"] = [{"SnapshotName": "com.apple.TimeMachine.2026-09-23-201010.local", "SnapshotUUID": "22222222-2222-4222-8222-222222222222"}]
        self.assertTrue(self.f.snapshot_precheck()["mount_proof"]["unmounted"])
        volume["snapshots"][0]["SnapshotName"] = RUNTIME.OLD_NAME
        with self.assertRaises(Exception):
            self.f.snapshot_precheck()
        self.assertEqual(self.f.runner.vendor_calls, [])

    def test_new_hourly_snapshot_allowed_but_change_during_dispatch_denied(self):
        self.f.runner.data_volume()["snapshots"].append({"SnapshotName": "com.apple.TimeMachine.2026-09-23-231010.local", "SnapshotUUID": "22222222-2222-4222-8222-222222222222"})
        prior = self.f.snapshot_precheck()
        self.f.runner.data_volume()["snapshots"].append({"SnapshotName": "com.apple.TimeMachine.2026-09-23-232010.local", "SnapshotUUID": "33333333-3333-4333-8333-333333333333"})
        with self.assertRaises(Exception):
            self.f.runtime.dispatch_check(SNAP_ACTION, prior, REPLACEMENT, self.f.outcomes)

    def test_mount_must_be_readonly_and_normally_unmounted(self):
        for field in ["readonly", "leave_mounted"]:
            with self.subTest(field=field):
                f = RuntimeFixture()
                setattr(f.runner, field, field == "leave_mounted")
                with self.assertRaises(Exception):
                    f.snapshot_precheck()
                self.assertEqual(f.runner.vendor_calls, [])
        mount = "/private/tmp/m4-batch2-restore-" + REPLACEMENT.lower()
        self.f.runner.failures[("/sbin/umount", mount)] = 1
        with self.assertRaises(Exception):
            self.f.snapshot_precheck()

    def test_partial_attach_then_error_must_normally_unmount_and_verify_absence(self):
        for failure in ["nonzero", "timeout"]:
            with self.subTest(failure=failure):
                f = RuntimeFixture()
                original = f.runner.__call__
                def partial(argv, *, timeout=60):
                    if argv[0] == "/sbin/mount_apfs":
                        f.runner.mounted = argv[-1]
                        f.runner.calls.append((tuple(argv), timeout))
                        if failure == "timeout":
                            raise TimeoutError("synthetic attach timeout after attach")
                        return f.runner.result(returncode=1)
                    return original(argv, timeout=timeout)
                f.runtime.runner = partial
                with self.assertRaises(Exception):
                    f.snapshot_precheck()
                self.assertIsNone(f.runner.mounted, "failed mount left replacement attached")
                self.assertTrue(any(args[0] == "/sbin/umount" for args, _ in f.runner.calls))
                self.assertEqual(f.runner.vendor_calls, [])

    def test_dispatch_requires_completed_same_invocation_proof(self):
        prior = self.f.runtime.precheck(SNAP_ACTION, REPLACEMENT, self.f.outcomes, proof=False)
        with self.assertRaises(Exception):
            self.f.runtime.dispatch_check(SNAP_ACTION, prior, REPLACEMENT, self.f.outcomes)

    def test_snapshot_postconditions_preserve_every_other_snapshot(self):
        prior = self.f.snapshot_precheck()
        with self.assertRaises(Exception):
            self.f.runtime.postcheck(SNAP_ACTION, prior, REPLACEMENT, self.f.outcomes)
        self.f.runtime.dispatch(SNAP_ACTION, RUNTIME.fixed_argv(self.f.policy, SNAP_ACTION))
        self.f.runner.data_volume()["snapshots"] = [s for s in self.f.runner.data_volume()["snapshots"] if s["SnapshotUUID"] != REPLACEMENT]
        with self.assertRaises(Exception):
            self.f.runtime.postcheck(SNAP_ACTION, prior, REPLACEMENT, self.f.outcomes)

    def test_skipped_observation_missing_live_drift_or_snapshot_mismatch_denies(self):
        for variant in ["missing", "live-drift", "snapshot-mismatch"]:
            with self.subTest(variant=variant):
                f = RuntimeFixture()
                target = HOME + "/.npm/_npx/" + KEYS[0]
                if variant == "missing":
                    f.outcomes[0].pop("skip_observation")
                elif variant == "live-drift":
                    f.fs.identities[target]["metadata_sha256"] = "e" * 64
                else:
                    captured = copy.deepcopy(f.fs.identities[target])
                    captured["metadata_sha256"] = "e" * 64
                    f.fs.snapshot_identity_overrides[target] = captured
                with self.assertRaises(Exception):
                    f.snapshot_precheck()
                self.assertEqual(f.runner.vendor_calls, [])
                self.assertIsNone(f.runner.mounted)
class EntrypointStructureTest(unittest.TestCase):
    def test_production_composition_has_no_test_selection(self):
        tree = ast.parse((HOOKS / "lib" / "m4-batch2-executor.py").read_text())
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        runtime_calls = [n for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "Runtime"]
        self.assertEqual(len(runtime_calls), 1)
        call = runtime_calls[0]
        self.assertEqual(len(call.args), 1)
        self.assertEqual(call.keywords, [])
        self.assertIsInstance(call.args[0], ast.Name)
        self.assertEqual(call.args[0].id, "policy")
        stores = [n for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "SecureStore"]
        self.assertEqual(len(stores), 1)
        self.assertEqual(ast.unparse(stores[0]), "SecureStore(STATE_DIR)")
        for node in ast.walk(main):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn("--fake", node.value)
                self.assertNotIn("--policy", node.value)
                self.assertNotIn("--store", node.value)
        self.assertNotIn("test_m4_batch2", ast.unparse(main))

    def test_pins_match_reviewed_policy_and_runtime_bytes(self):
        raw = (HOOKS / "policies" / "m4-batch2-20260923.json").read_bytes()
        self.assertEqual(CORE.POLICY_SHA256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(POLICY["runtime_sha256"], hashlib.sha256((HOOKS / "lib" / "m4-batch2-runtime.py").read_bytes()).hexdigest())

    def test_vendor_subprocess_is_array_no_shell_and_fixed_environment(self):
        tree = ast.parse((HOOKS / "lib" / "m4-batch2-runtime.py").read_text())
        runner = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "real_runner")
        calls = [n for n in ast.walk(runner) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "run"]
        self.assertEqual(len(calls), 1)
        call = calls[0]
        kwargs = {k.arg: k.value for k in call.keywords}
        self.assertEqual(ast.literal_eval(kwargs["shell"]), False)
        self.assertEqual(ast.unparse(kwargs["env"]), "CHILD_ENV")
        self.assertEqual(ast.unparse(kwargs["cwd"]), "HOME")
        self.assertEqual(ast.unparse(call.args[0]), "argv")
        self.assertNotIn("NODE_OPTIONS", RUNTIME.CHILD_ENV)
        self.assertNotIn("BASH_ENV", RUNTIME.CHILD_ENV)


class StartupBoundaryTest(unittest.TestCase):
    """Unknown-mode copies only: no production executor/adapter is reachable."""
    def test_direct_shebang_ignores_path_startup_file_and_exported_function(self):
        for script in ["pre-tool-use-enforcement.sh", "deletion-approval-note.sh"]:
            for attack in ["PATH", "BASH_ENV", "EXPORTED_FUNCTION"]:
                with self.subTest(script=script, attack=attack):
                    directory = Path(tempfile.mkdtemp(prefix="startup-", dir=TEST_ROOT))
                    candidate = directory / script
                    candidate.write_bytes((HOOKS / script).read_bytes())
                    candidate.chmod(0o700)
                    marker = directory / "startup-marker"
                    env = {"HOME": str(directory), "PATH": "/usr/bin:/bin", "M4_HERMETIC_MARKER": str(marker)}
                    if attack == "PATH":
                        shadow = directory / "bash"
                        shadow.write_text('#!/bin/sh\nprintf "shadow interpreter ran\\n" >> "$M4_HERMETIC_MARKER"\nexit 19\n')
                        shadow.chmod(0o700)
                        env["PATH"] = str(directory) + ":/usr/bin:/bin"
                    elif attack == "BASH_ENV":
                        startup = directory / "startup.sh"
                        startup.write_text('printf "startup file ran\\n" >> "$M4_HERMETIC_MARKER"\n')
                        env["BASH_ENV"] = str(startup)
                    else:
                        env["BASH_FUNC_printf%%"] = '() { builtin printf "imported function ran\\n" >> "$M4_HERMETIC_MARKER"; builtin printf "%s\\n" "$@"; }'
                    mode = "--invalid-m4-batch2-mode" if script.startswith("pre-tool") else "invalid-m4-batch2-mode"
                    result = subprocess.run([str(candidate), mode], env=env, cwd=directory,
                                            text=True, capture_output=True, timeout=10)
                    self.assertFalse(marker.exists(), "startup injection executed before mode rejection")
                    self.assertEqual(result.returncode, 2)


class PublicOutputTest(unittest.TestCase):
    """Exercise only pure emitters and the isolated main exception-handler AST."""
    approval = 'EXACT_APPROVAL_SENTINEL_7bb32f\nLiteral "quoted" second line.'
    note_marker = "FULL_NOTE_SENTINEL_91d2"
    authorization_marker = "SKIP_AUTHORIZATION_SENTINEL_273a"
    stdout_marker = "CHILD_STDOUT_SENTINEL_c60b"
    stderr_marker = "CHILD_STDERR_SENTINEL_f127"
    exception_marker = "EXCEPTION_TEXT_SENTINEL_0d17"
    markers = (approval, note_marker, authorization_marker, stdout_marker, stderr_marker, exception_marker)
    public_keys = {"status", "action", "dispatched", "approval_consumed", "claim_irreversible",
                   "consumes_note", "binding_required", "vendor_returncode"}

    def setUp(self):
        self.guard = no_processes()
        self.guard.__enter__()
        self.addCleanup(self.guard.__exit__, None, None, None)

    def capture(self, function, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = function(*args)
        return result, stdout.getvalue(), stderr.getvalue()

    def assert_private_omitted(self, stdout, stderr):
        combined = stdout + stderr
        for marker in self.markers:
            # The first-line approval marker also detects a JSON-escaped quote.
            for fragment in marker.splitlines():
                self.assertNotIn(fragment, combined)

    def sensitive_result(self, status="VERIFIED", action=ACTION):
        return {"status": status, "action": action, "dispatched": True, "approval_consumed": True,
                "claim_irreversible": True, "consumes_note": False, "binding_required": False,
                "approval_quote": self.approval,
                "note": {"approval_quote": self.approval, "private_note": self.note_marker},
                "authorization": {"approval_quote": self.approval, "secret": self.authorization_marker},
                "child": {"returncode": 0, "stdout": self.stdout_marker, "stderr": self.stderr_marker},
                "reason": self.exception_marker, "error": self.exception_marker,
                "identity": {"path": self.note_marker}, "private_extra": self.authorization_marker}

    def new_executor(self):
        policy = copy.deepcopy(POLICY)
        policy["approval_sha256"] = hashlib.sha256(self.approval.encode()).hexdigest()
        runtime = ScriptedRuntime(policy)
        runtime.vendor_result.update(stdout=self.stdout_marker, stderr=self.stderr_marker)
        directory = Path(tempfile.mkdtemp(prefix="public-boundary-", dir=TEST_ROOT)) / "store"
        store = CORE.SecureStore(directory)
        executor = CORE.Executor(policy, runtime, store, digest(policy), clock=lambda: 1700000100.0)
        return executor, runtime, store, directory

    def test_all_finite_actions_and_statuses_emit_only_allowlisted_public_fields(self):
        statuses = {"PREVIEW": 0, "GRANTED": 0, "VERIFIED": 0, "SKIPPED": 0, "FAILED": 2, "AMBIGUOUS": 2}
        for status, expected_exit in statuses.items():
            for action in ["npx:" + key for key in KEYS] + [SNAP_ACTION]:
                with self.subTest(status=status, action=action):
                    private = self.sensitive_result(status, action)
                    exit_code, stdout, stderr = self.capture(CORE.emit_public_result, private)
                    public = json.loads(stdout)
                    self.assertEqual(exit_code, expected_exit)
                    self.assertEqual(stderr, "")
                    self.assertEqual(public["status"], status)
                    self.assertEqual(public["action"], action)
                    self.assertEqual(set(public), self.public_keys)
                    self.assertEqual(public["vendor_returncode"], 0)
                    self.assert_private_omitted(stdout, stderr)

    def test_public_projection_is_fresh_and_does_not_mutate_private_receipt(self):
        private = self.sensitive_result()
        before = copy.deepcopy(private)
        projected, stdout, stderr = self.capture(CORE.public_result, private)
        self.assertEqual((stdout, stderr), ("", ""))
        self.assertIsNot(projected, private)
        projected["status"] = "FAILED"
        self.assertEqual(private, before)
        self.assertEqual(private["note"]["approval_quote"], self.approval)
        self.assertEqual(private["authorization"]["secret"], self.authorization_marker)
        self.assertNotIn("note", projected)
        self.assertNotIn("authorization", projected)
        self.assertNotIn("child", projected)

    def test_opaque_private_fields_are_never_stringified(self):
        class NoFormatting:
            def __str__(self):
                raise AssertionError("private object was formatted")
            def __repr__(self):
                raise AssertionError("private object was represented")
        private = self.sensitive_result()
        for name in ["approval_quote", "note", "authorization", "reason", "error", "identity", "private_extra"]:
            private[name] = NoFormatting()
        private["child"]["stdout"] = NoFormatting()
        private["child"]["stderr"] = NoFormatting()
        exit_code, stdout, stderr = self.capture(CORE.emit_public_result, private)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["status"], "VERIFIED")

    def test_malformed_public_fields_fail_before_any_output(self):
        variants = [None, [], self.exception_marker,
                    {"status": self.exception_marker, "action": ACTION},
                    {"status": "VERIFIED", "action": self.note_marker},
                    {"status": "VERIFIED", "action": "npx:" + ACTIVE[0]}]
        for field in ["dispatched", "approval_consumed", "claim_irreversible", "consumes_note", "binding_required"]:
            for value in [1, 0, None, self.authorization_marker, [], {}]:
                variants.append({"status": "VERIFIED", "action": ACTION, field: value})
        for value in [True, False, 0.0, None, self.stdout_marker, -256, 256, [], {}]:
            variants.append({"status": "VERIFIED", "action": ACTION, "child": {"returncode": value}})
        variants.append({"status": "VERIFIED", "action": ACTION, "child": self.stderr_marker})
        for index, private in enumerate(variants):
            with self.subTest(variant=index):
                stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    with self.assertRaises(CORE.GuardError) as caught:
                        CORE.emit_public_result(private)
                self.assertEqual((stdout.getvalue(), stderr.getvalue()), ("", ""))
                self.assert_private_omitted(str(caught.exception), "")

    def test_returncode_bounds_and_exact_bool_flags_keep_status_semantics(self):
        for code in [-255, -1, 0, 1, 255]:
            with self.subTest(returncode=code):
                private = {"status": "FAILED", "action": ACTION,
                           "dispatched": False, "approval_consumed": False, "claim_irreversible": True,
                           "child": {"returncode": code, "stdout": self.stdout_marker, "stderr": self.stderr_marker}}
                exit_code, stdout, stderr = self.capture(CORE.emit_public_result, private)
                public = json.loads(stdout)
                self.assertEqual(exit_code, 2)
                self.assertEqual(public["vendor_returncode"], code)
                self.assertIs(public["dispatched"], False)
                self.assertIs(public["approval_consumed"], False)
                self.assertIs(public["claim_irreversible"], True)
                self.assert_private_omitted(stdout, stderr)

    def test_private_grant_note_and_audit_retain_exact_quote_while_public_omits_it(self):
        executor, runtime, store, directory = self.new_executor()
        granted, stdout, stderr = self.capture(executor.grant, ACTION, self.approval)
        self.assertEqual((stdout, stderr), ("", ""))
        self.assertEqual(runtime.calls, [])
        self.assertEqual(granted["note"]["approval_quote"], self.approval)
        with store.lock():
            saved = store.read(store.note_name(ACTION))
            grant_audit = next(row for row in store.audit_records() if row["event"] == "GRANT")
        self.assertEqual(saved["approval_quote"], self.approval)
        self.assertEqual(grant_audit["payload"]["note"]["approval_quote"], self.approval)
        self.assertEqual((directory / store.note_name(ACTION)).stat().st_mode & 0o777, 0o600)
        self.assertEqual((directory / "audit.jsonl").stat().st_mode & 0o777, 0o600)
        exit_code, stdout, stderr = self.capture(CORE.emit_public_result, granted)
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout), {"status": "GRANTED", "action": ACTION})
        self.assert_private_omitted(stdout, stderr)

    def test_private_skip_authorization_remains_exact_without_public_disclosure(self):
        executor, runtime, store, directory = self.new_executor()
        runtime.stage_errors["precheck"] = RUNTIME.TargetSkip(
            self.authorization_marker, runtime.target_observation(ACTION))
        skipped, stdout, stderr = self.capture(executor.grant, ACTION, self.approval)
        self.assertEqual((stdout, stderr), ("", ""))
        self.assertEqual(skipped["status"], "SKIPPED")
        self.assertEqual(skipped["authorization"]["approval_quote"], self.approval)
        with store.lock():
            saved = store.read(store.outcome_name(ACTION))
            prepared = next(row for row in store.audit_records() if row["event"] == "SKIP_PREPARED")
        self.assertEqual(saved["authorization"]["approval_quote"], self.approval)
        self.assertEqual(prepared["payload"]["authorization"]["approval_quote"], self.approval)
        self.assertEqual(saved["reason"], self.authorization_marker)
        self.assertFalse((directory / store.note_name(ACTION)).exists())
        self.assertFalse((directory / store.claim_name(ACTION)).exists())
        exit_code, stdout, stderr = self.capture(CORE.emit_public_result, skipped)
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout)["status"], "SKIPPED")
        self.assert_private_omitted(stdout, stderr)

    def test_private_child_output_and_quote_retained_but_terminal_output_is_public(self):
        executor, runtime, store, directory = self.new_executor()
        executor.grant(ACTION, self.approval)
        outcome, stdout, stderr = self.capture(executor.execute, ACTION)
        self.assertEqual((stdout, stderr), ("", ""))
        self.assertEqual(outcome["status"], "VERIFIED")
        self.assertEqual(len(runtime.calls), 1)
        with store.lock():
            saved = store.read(store.outcome_name(ACTION))
            audit = store.audit_records()
        self.assertEqual(saved["child"]["stdout"], self.stdout_marker)
        self.assertEqual(saved["child"]["stderr"], self.stderr_marker)
        self.assertEqual(next(row for row in audit if row["event"] == "PREPARED")["payload"]["note"]["approval_quote"], self.approval)
        self.assertEqual(saved["status"], "VERIFIED")
        exit_code, stdout, stderr = self.capture(CORE.emit_public_result, outcome)
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout)["vendor_returncode"], 0)
        self.assert_private_omitted(stdout, stderr)

    def test_main_print_boundary_delegates_only_to_fixed_emitters(self):
        tree = ast.parse((HOOKS / "lib" / "m4-batch2-executor.py").read_text())
        main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
        calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)]
        self.assertFalse(any(isinstance(node.func, ast.Name) and node.func.id == "print" for node in calls))
        self.assertFalse(any(isinstance(node.func, ast.Attribute) and node.func.attr in ("write", "writelines", "dumps", "dump") for node in calls))
        public_calls = [node for node in calls if isinstance(node.func, ast.Name) and node.func.id == "emit_public_result"]
        self.assertEqual(len(public_calls), 1)
        self.assertEqual(ast.unparse(public_calls[0]), "emit_public_result(result)")
        handlers = [node for node in ast.walk(main) if isinstance(node, ast.ExceptHandler)]
        self.assertEqual(len(handlers), 1)
        handler = handlers[0]
        self.assertIsNone(handler.name, "main must not bind private exception text for output")
        self.assertEqual(ast.unparse(handler.type), "Exception")
        self.assertEqual(len(handler.body), 1)
        self.assertEqual(ast.unparse(handler.body[0]), "return emit_blocked()")

    def test_actual_main_exception_handler_never_formats_arbitrary_exception_text(self):
        # Compile only the real except handler into a capability-free fixture.
        # No production main body, trusted_read, Runtime constructor or path is
        # in this AST, so the fixture cannot reach any production operation.
        tree = ast.parse((HOOKS / "lib" / "m4-batch2-executor.py").read_text())
        main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
        handler = copy.deepcopy(next(node for node in ast.walk(main) if isinstance(node, ast.ExceptHandler)))
        function = ast.FunctionDef(name="exception_boundary", args=ast.arguments(
            posonlyargs=[], args=[ast.arg(arg="operation")], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=[ast.Try(body=[ast.Expr(value=ast.Call(func=ast.Name(id="operation", ctx=ast.Load()), args=[], keywords=[]))],
                          handlers=[handler], orelse=[], finalbody=[])], decorator_list=[])
        isolated = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
        namespace = {"emit_blocked": CORE.emit_blocked, "Exception": Exception}
        exec(compile(isolated, "<isolated-main-exception-handler>", "exec"), namespace)
        class NeverFormatError(Exception):
            def __str__(self):
                raise AssertionError("exception was formatted")
        for error in [RuntimeError(self.exception_marker), ValueError(self.exception_marker),
                      OSError(self.exception_marker), NeverFormatError(self.exception_marker)]:
            with self.subTest(error_type=type(error).__name__):
                def fail():
                    raise error
                exit_code, stdout, stderr = self.capture(namespace["exception_boundary"], fail)
                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout, "")
                self.assertEqual(json.loads(stderr), {"status": "BLOCKED", "code": "M4_GUARD_BLOCKED"})
                self.assert_private_omitted(stdout, stderr)


class LegacyTest(unittest.TestCase):
    """Run only stdin preflight; a synthetic library never deletes even notes."""
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="legacy-", dir=TEST_ROOT))
        self.home = self.directory / "home"
        self.home.mkdir()
        self.library = self.directory / "synthetic-library.sh"
        self.marker = self.directory / "consumed-marker"
        self.library.write_text('''normalize_target() { printf '%s' "$1"; }
extract_rm_paths() { printf '%s\\n' "$SYNTHETIC_TARGET"; }
find_approval_note() {
  [[ "${SYNTHETIC_APPROVED:-}" == 1 && ! -f "$SYNTHETIC_MARKER" ]] || return 1
  printf '%s' "$SYNTHETIC_NOTE"
}
consume_approval_note() { printf '%s\\n' "$1" >> "$SYNTHETIC_MARKER"; }
da_build_index() { return 0; }
''')
        self.env = {"HOME": str(self.home), "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
                    "DELETION_APPROVAL_LIB": str(self.library), "SYNTHETIC_TARGET": "/Users/synthetic/target",
                    "SYNTHETIC_MARKER": str(self.marker), "SYNTHETIC_NOTE": str(self.directory / "synthetic-note.json")}

    def invoke(self, path, command=None, tool="Bash", file_path=None, extra_env=None):
        payload = {"session_id": "synthetic", "hook_event_name": "PreToolUse", "cwd": str(self.directory),
                   "permission_mode": "default", "tool_name": tool,
                   "tool_input": {"command": command} if tool == "Bash" else {"file_path": file_path}}
        env = dict(self.env)
        env.update(extra_env or {})
        result = subprocess.run(["/bin/bash", str(path)], input=json.dumps(payload), text=True,
                                capture_output=True, env=env, cwd=self.directory, timeout=15)
        return result.returncode, result.stdout, result.stderr

    def compare(self, **kwargs):
        original = self.invoke(FIXTURES / "original-pre-tool-use-enforcement.sh", **kwargs)
        current = self.invoke(HOOKS / "pre-tool-use-enforcement.sh", **kwargs)
        self.assertEqual(current, original)
        return current

    def test_ordinary_source_suffix_and_common_library_unchanged(self):
        original = (FIXTURES / "original-pre-tool-use-enforcement.sh").read_bytes()
        current = (HOOKS / "pre-tool-use-enforcement.sh").read_bytes()
        # The approved prefix and the quoted-path parser repair are the only
        # permitted differences from the legacy hook body.
        suffix = original[original.index(b"set -uo pipefail"):]
        old_rm = b"  RM_CMD=$(printf '%s' \"$CMD\" | grep -oE '(^|[;|&[:space:]])\\s*rm\\s+[^;|&]*' | head -1 || true)\n"
        new_rm = (
            b"  # Preserve quoted separators in a standalone rm command. The approval\n"
            b"  # parser rejects unquoted separators before it can consume any note.\n"
            b"  if [[ \"$CMD\" =~ ^[[:space:]]*rm[[:space:]]+ ]]; then\n"
            b"    RM_CMD=\"$CMD\"\n"
            b"  else\n"
            b"    RM_CMD=$(printf '%s' \"$CMD\" | grep -oE '(^|[;|&[:space:]])\\s*rm\\s+[^;|&]*' | head -1 || true)\n"
            b"  fi\n"
        )
        self.assertEqual(current.count(new_rm), 1)
        # Reviewed 2026-10-25 fail-closed repair (Handoffs row "Finish AI HQ
        # folder before checking 181 empty parent folders", step 4). Each piece
        # is stripped by exact bytes, so anything else that moves still fails.
        fc_start = current.index(b"# -------------------------------------------------------------------------\n# FAIL CLOSED (added 2026-10-25")
        fc_end_marker = b'  || guard_refuse "the hook input is not a JSON object with a tool_name."\n\n'
        fc_end = current.index(fc_end_marker) + len(fc_end_marker)
        current = current[:fc_start] + current[fc_end:]
        index_call = (
            b"  # One pass over the notes directory for the whole command. Built here in the\n"
            b"  # main shell, not inside the $(find_approval_note) subshell, so the index is\n"
            b"  # reused for every target instead of re-reading every note once per target.\n"
            b"  da_build_index || return 1\n\n"
        )
        self.assertEqual(current.count(index_call), 1)
        current = current.replace(index_call, b"")
        # Reviewed 2026-10-25 literal-glob-name change, one call site.
        self.assertEqual(current.count(b'normalize_target "$tok" "$cwd" literal'), 1)
        current = current.replace(b'normalize_target "$tok" "$cwd" literal', b'normalize_target "$tok" "$cwd"')
        self.assertEqual(current.count(b"  GUARD_CLEAN_EXIT=1\n  exit 0\n}"), 2)
        current = current.replace(b"  GUARD_CLEAN_EXIT=1\n  exit 0\n}", b"  exit 0\n}")
        self.assertTrue(current.endswith(b"GUARD_CLEAN_EXIT=1\nexit 0\n"))
        current = current[:-len(b"GUARD_CLEAN_EXIT=1\nexit 0\n")] + b"exit 0\n"
        self.assertTrue(current.replace(new_rm, old_rm).endswith(suffix),
                        "legacy no-argument body changed outside quoted-path repair")
        old_lib = (FIXTURES / "original-deletion-approval-common.sh").read_bytes()
        current_lib = (HOOKS / "lib" / "deletion-approval-common.sh").read_bytes()
        parser_start = b"extract_rm_paths() {"
        parser_end = b"\n# -------------------------------------------------------------------------"
        old_prefix, old_parser = old_lib.split(parser_start, 1)
        new_prefix, new_parser = current_lib.split(parser_start, 1)
        # Reviewed 2026-10-25 literal-glob-name change to normalize_target. Each
        # piece is reverted by exact bytes before the strict prefix comparison.
        literal_edits = [
            (b"# normalize_target <raw-token> <cwd> [literal]\n", b"# normalize_target <raw-token> <cwd>\n"),
            (b"normalize_target() {\n  local tok=\"$1\" cwd=\"${2:-}\" mode=\"${3:-}\"\n", b"normalize_target() {\n  local tok=\"$1\" cwd=\"${2:-}\"\n"),
            (b"  case \"$tok\" in\n    *..*) return 1 ;;\n  esac\n  if [[ \"$mode\" != \"literal\" ]]; then\n    case \"$tok\" in\n      *\\**|*\\?*|*\\[*|*\\]*) return 1 ;;\n    esac\n  fi\n",
             b"  case \"$tok\" in\n    *..*) return 1 ;;\n    *\\**|*\\?*|*\\[*|*\\]*) return 1 ;;\n  esac\n"),
        ]
        for edited, original in literal_edits:
            self.assertEqual(new_prefix.count(edited), 1, edited)
            new_prefix = new_prefix.replace(edited, original)
        doc_start = b"#     exact target, and a glob is not one exact target"
        doc_end = b"# Deliberately LEXICAL only"
        self.assertIn(doc_start, new_prefix)
        new_doc = new_prefix[new_prefix.index(doc_start):new_prefix.index(doc_end)]
        old_doc = old_prefix[old_prefix.index(doc_start):old_prefix.index(doc_end)]
        self.assertTrue(new_doc.startswith(old_doc.split(b"\n")[0]))
        new_prefix = new_prefix[:new_prefix.index(doc_start)] + old_prefix[old_prefix.index(doc_start):old_prefix.index(doc_end)] + new_prefix[new_prefix.index(doc_end):]
        self.assertEqual(new_prefix, old_prefix)
        lookup_start = b"# find_approval_note <normalized-target>"
        lookup_end = b"# consume_approval_note <note-file> <context>"
        def without_lookup(text):
            return text[:text.index(lookup_start)] + text[text.index(lookup_end):]
        # The note lookup was rewritten on 2026-10-25 to read the notes once
        # (da_build_index) instead of two jq runs per note per target.
        self.assertEqual(without_lookup(new_parser.split(parser_end, 1)[1]),
                         without_lookup(old_parser.split(parser_end, 1)[1]),
                         "common library changed outside the rm path parser and the reviewed note lookup")
        original_grant = (FIXTURES / "original-deletion-approval-note.sh").read_bytes()
        current_grant = (HOOKS / "deletion-approval-note.sh").read_bytes()
        old_usage = b"  sed -n '9,20p' \"$0\" | sed 's/^# \\{0,1\\}//'\n"
        repaired_usage = (
            b"  # Stable comment boundaries retain the original help despite the M4 prefix.\n"
            b"  sed -n '/^#   approved delete got done by going AROUND it/,/^# A note is written ONLY when Allison has given an explicit deletion approval/p' \"$0\" | sed 's/^# \\{0,1\\}//'\n"
        )
        self.assertEqual(current_grant.count(repaired_usage), 1)
        current_grant = current_grant.replace(repaired_usage, old_usage, 1)
        # Reviewed 2026-10-25 literal-glob-name change, two call sites.
        for edited, original in [
            (b'norm=$(normalize_target "$target" "$PWD" literal) || die "target is not approvable (path traversal or empty): $target"',
             b'norm=$(normalize_target "$target" "$PWD") || die "target is not approvable (path traversal, a glob, or empty): $target"'),
            (b'norm=$(normalize_target "$target" "$PWD" literal) || die "not a normalizable target: $target"',
             b'norm=$(normalize_target "$target" "$PWD") || die "not a normalizable target: $target"')]:
            self.assertEqual(current_grant.count(edited), 1, edited)
            current_grant = current_grant.replace(edited, original)
        start = original_grant.index(b"set -")
        self.assertTrue(current_grant.endswith(original_grant[start:]), "legacy grant body changed beyond exact reviewed help repair")

    def test_denial_floors_and_harmless_input_unchanged(self):
        cases = [("rm -rf /Users/synthetic/target", 2), ("git push --force origin main", 2),
                 ("git push --force-with-lease origin main", 2), ("git config user.email bad@example.test", 2),
                 ("ls -la /Users/synthetic", 0), ("git config --get user.email", 0),
                 ("npm publish", 0), ("sudo synthetic-command", 0)]
        for command, status in cases:
            with self.subTest(command=command):
                result = self.compare(command=command)
                self.assertEqual(result[0], status)

    def test_config_and_identity_advisories_unchanged(self):
        for path in ["/Users/synthetic/.claude/settings.json", "/Users/synthetic/.claude/settings.local.json",
                     "/Users/synthetic/.zshrc"]:
            with self.subTest(path=path):
                result = self.compare(tool="Write", file_path=path)
                self.assertEqual(result[0], 0)
                self.assertIn("additionalContext", result[1])
        self.compare(command="git reset --hard synthetic-ref")

    def test_legacy_kill_switch_unchanged(self):
        result = self.compare(command="rm -rf /Users/synthetic/target", extra_env={"PRE_TOOL_USE_OFF": "1"})
        self.assertEqual(result[0], 0)

    def test_legacy_grant_no_argument_usage_unchanged(self):
        results = []
        for path in [FIXTURES / "original-deletion-approval-note.sh", HOOKS / "deletion-approval-note.sh"]:
            result = subprocess.run(["/bin/bash", str(path)], text=True, capture_output=True,
                                    env=self.env, cwd=self.directory, timeout=15)
            results.append((result.returncode, result.stdout, result.stderr))
        self.assertEqual(results[1], results[0])

    def test_legacy_allow_is_preflight_only_and_single_use_with_synthetic_library(self):
        for index, path in enumerate([FIXTURES / "original-pre-tool-use-enforcement.sh", HOOKS / "pre-tool-use-enforcement.sh"]):
            marker = str(self.directory / ("consumed-" + str(index)))
            env = {"SYNTHETIC_APPROVED": "1", "SYNTHETIC_MARKER": marker}
            first = self.invoke(path, command="rm -rf /Users/synthetic/target", extra_env=env)
            second = self.invoke(path, command="rm -rf /Users/synthetic/target", extra_env=env)
            self.assertEqual(first[0], 0)
            self.assertIn("additionalContext", first[1])
            self.assertNotIn('"permissionDecision"', first[1])
            self.assertEqual(second[0], 2)
            self.assertEqual(Path(marker).read_text().count("synthetic-note.json"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
