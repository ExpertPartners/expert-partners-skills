"""The entry-point producer never launches a browser or changes credentials."""

import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest

SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "plugins/operating-doctrine/skills/browser-automation/scripts"
)
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "browser_route_install_source", SCRIPTS / "install_job_route.py"
)
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)


class InstallerTests(unittest.TestCase):
    def fixture(self, root):
        root = Path(root)
        runtime = root / "produced skill"
        scripts = runtime / "scripts"
        scripts.mkdir(parents=True)
        manifest = []
        for name in (
            "browser_jobs.py",
            "chrome_job_window.py",
            "job_transport.py",
            "owned_pages.js",
            "browser_lifecycle.py",
            "browser_window_cleanup.py",
            "install_browser_lifecycle.py",
        ):
            content = ("fixture " + name).encode()
            (scripts / name).write_bytes(content)
            manifest.append(hashlib.sha256(content).hexdigest() + "  ./scripts/" + name)
        (runtime / "checksums.sha256").write_text("\n".join(manifest) + "\n")
        original = b"#!/bin/sh\n# existing protected credential bootstrap, unchanged\nexit 0\n"
        entry = root / "existing launcher.sh"
        entry.write_bytes(original)
        entry.chmod(0o755)
        settings = {
            "host": socket.gethostname(),
            "profile": "Default",
            "expected_account": "worker@example.test",
            "launcher": str(entry),
            "launcher_sha256": hashlib.sha256(original).hexdigest(),
            "bootstrap_lock": str(root / "private" / "bootstrap.lock"),
            "state_dir": str(root / "private" / "receipts"),
            "headless_hook": str(root / "hook.py"),
            "mcp_version": "fixture",
        }
        return settings, runtime, root / "private" / "route.json", original

    def apply(self, settings, runtime, dest, check=lambda *_: None):
        return producer.install(
            settings, runtime, dest, sys.executable, identity_check=check, running=lambda: True
        )

    def test_activation_backs_up_exact_bootstrap_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            settings, runtime, dest, original = self.fixture(root)
            checked = []
            first = self.apply(settings, runtime, dest, lambda *args: checked.append(args))
            self.assertTrue(first["changed"])
            backup = Path(first["backup"])
            self.assertEqual(backup.read_bytes(), original)
            self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
            self.assertEqual(dest.stat().st_mode & 0o777, 0o600)
            config = json.loads(dest.read_text())
            self.assertEqual(config["launcher"], str(backup))
            self.assertEqual(config["launcher_sha256"], settings["launcher_sha256"])
            wrapper = Path(settings["launcher"]).read_text()
            self.assertIn("browser_jobs.py", wrapper)
            self.assertNotIn("protected credential", wrapper)
            self.assertFalse(self.apply(settings, runtime, dest)["changed"])
            self.assertEqual(checked, [("Default", "worker@example.test")])

    def test_upgrade_preserves_bootstrap_and_rollback(self):
        with tempfile.TemporaryDirectory() as root:
            settings, runtime, dest, original = self.fixture(root)
            self.apply(settings, runtime, dest)
            upgraded = Path(root) / "next"
            import shutil

            shutil.copytree(runtime, upgraded)
            self.assertTrue(producer.upgrade(dest, upgraded, sys.executable)["changed"])
            self.assertFalse(producer.upgrade(dest, upgraded, sys.executable)["changed"])
            producer.rollback(dest)
            self.assertEqual(Path(settings["launcher"]).read_bytes(), original)

    def test_source_or_artifact_drift_does_not_change_entry(self):
        with tempfile.TemporaryDirectory() as root:
            settings, runtime, dest, original = self.fixture(root)
            (runtime / "scripts/browser_jobs.py").write_text("changed")
            with self.assertRaises(producer.InstallRefusal):
                self.apply(settings, runtime, dest)
            self.assertEqual(Path(settings["launcher"]).read_bytes(), original)
            settings, runtime, dest, original = self.fixture(Path(root) / "second")
            settings["launcher_sha256"] = "0" * 64
            with self.assertRaises(producer.InstallRefusal):
                self.apply(settings, runtime, dest)
            self.assertEqual(Path(settings["launcher"]).read_bytes(), original)

    def test_unsigned_profile_stops_before_activation(self):
        with tempfile.TemporaryDirectory() as root:
            settings, runtime, dest, original = self.fixture(root)

            def unsigned(*_):
                raise ValueError("fixture unsigned")

            with self.assertRaises(ValueError):
                self.apply(settings, runtime, dest, unsigned)
            self.assertEqual(Path(settings["launcher"]).read_bytes(), original)
            self.assertFalse(dest.exists())

    def test_rollback_restores_exact_bytes_and_preserves_backup(self):
        with tempfile.TemporaryDirectory() as root:
            settings, runtime, dest, original = self.fixture(root)
            installed = self.apply(settings, runtime, dest)
            self.assertTrue(producer.rollback(dest)["restored"])
            self.assertEqual(Path(settings["launcher"]).read_bytes(), original)
            self.assertEqual(Path(settings["launcher"]).stat().st_mode & 0o777, 0o755)
            self.assertTrue(Path(installed["backup"]).exists())


if __name__ == "__main__":
    unittest.main()
