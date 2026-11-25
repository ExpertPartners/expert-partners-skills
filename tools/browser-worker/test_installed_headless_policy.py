"""Installed-version changes reach existing and fresh browser route facades."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "plugins/operating-doctrine/skills/browser-automation/scripts"
)


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstalledPolicyTests(unittest.TestCase):
    def fixture(self, root, version="1.0.0"):
        root = Path(root)
        plugins = root / ".claude/plugins"
        hook = (
            plugins
            / "cache/expert-partners/operating-doctrine"
            / version
            / "hooks/headless_route_check.py"
        )
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text(
            f"def decide(payload): return ('allow', {version!r})\ndef refresh_due(): return True\ndef start_background_refresh(): return 'refresh'\n"
        )
        entry = {"scope": "user", "installPath": str(hook.parents[1]), "version": version}
        receipt = {"plugins": {"operating-doctrine@expert-partners": [entry]}}
        (plugins / "installed_plugins.json").write_text(json.dumps(receipt))
        (root / ".claude/settings.json").write_text(
            json.dumps({"enabledPlugins": {"operating-doctrine@expert-partners": True}})
        )
        return hook, receipt

    def test_existing_and_fresh_import_follow_updated_install_receipt(self):
        with (
            tempfile.TemporaryDirectory() as root,
            patch("pathlib.Path.home", return_value=Path(root)),
        ):
            self.fixture(root)
            adapter = load("installed_headless_policy")
            self.assertEqual(adapter.decide({}), ("allow", "1.0.0"))
            self.fixture(root, "2.0.0")
            self.assertEqual(adapter.decide({}), ("allow", "2.0.0"))
            self.assertEqual(load("installed_headless_policy").decide({}), ("allow", "2.0.0"))
            self.assertTrue(adapter.refresh_due())
            self.assertEqual(adapter.start_background_refresh(), "refresh")

    def test_disabled_missing_ambiguous_and_wrong_path_fail_closed(self):
        for failure in ("disabled", "missing", "ambiguous", "path"):
            with (
                self.subTest(failure=failure),
                tempfile.TemporaryDirectory() as root,
                patch("pathlib.Path.home", return_value=Path(root)),
            ):
                hook, receipt = self.fixture(root)
                plugins = Path(root) / ".claude/plugins"
                if failure == "disabled":
                    (Path(root) / ".claude/settings.json").write_text("{}")
                elif failure == "missing":
                    hook.unlink()
                elif failure == "ambiguous":
                    entries = receipt["plugins"]["operating-doctrine@expert-partners"]
                    entries.append(dict(entries[0]))
                else:
                    receipt["plugins"]["operating-doctrine@expert-partners"][0]["installPath"] = (
                        str(Path(root) / "other")
                    )
                (plugins / "installed_plugins.json").write_text(json.dumps(receipt))
                with self.assertRaises(RuntimeError):
                    load("installed_headless_policy")

    def test_update_to_broken_install_does_not_keep_last_policy(self):
        with (
            tempfile.TemporaryDirectory() as root,
            patch("pathlib.Path.home", return_value=Path(root)),
        ):
            self.fixture(root)
            adapter = load("installed_headless_policy")
            (Path(root) / ".claude/plugins/installed_plugins.json").unlink()
            with self.assertRaises(FileNotFoundError):
                adapter.decide({})

    def test_migration_preserves_all_three_routes_and_backups(self):
        with (
            tempfile.TemporaryDirectory() as root,
            patch("pathlib.Path.home", return_value=Path(root)),
        ):
            self.fixture(root)
            configs = []
            originals = []
            for profile in ("ember", "allison", "don"):
                path = Path(root) / (profile + ".json")
                original = json.dumps(
                    {
                        "profile": profile,
                        "headless_hook": "/old/version/hook.py",
                        "launcher": "unchanged",
                    }
                ).encode()
                path.write_bytes(original)
                configs.append(path)
                originals.append(original)
            producer = load("install_headless_policy")
            destination = Path(root) / "stable/headless_route_check.py"
            result = producer.install(configs, destination)
            for row, original, config in zip(result["routes"], originals, configs):
                self.assertEqual(Path(row["backup"]).read_bytes(), original)
                migrated = json.loads(config.read_text())
                before = json.loads(original)
                self.assertEqual(migrated.pop("headless_hook"), str(destination))
                before.pop("headless_hook")
                self.assertEqual(migrated, before)
            self.assertEqual(
                destination.read_bytes(), (SCRIPTS / "installed_headless_policy.py").read_bytes()
            )
            self.assertFalse(
                any(r["changed"] for r in producer.install(configs, destination)["routes"])
            )


if __name__ == "__main__":
    unittest.main()
