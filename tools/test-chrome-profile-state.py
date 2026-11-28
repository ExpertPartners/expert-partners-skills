#!/usr/bin/env python3
"""Regression checks for persistent profiles without persistent windows."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "plugins/operating-doctrine/skills/browser-automation/scripts/chrome_profile_state.py"
)
spec = importlib.util.spec_from_file_location("profile_state", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Tests(unittest.TestCase):
    def test_unlocked_keychain_never_reads_credential(self):
        keychain = Mock()
        keychain.unlocked.return_value = True
        password = Mock(side_effect=AssertionError("unnecessary credential read"))
        self.assertFalse(
            module.ensure_keychain({}, keychain, password)["recovered_locked_keychain"]
        )
        keychain.unlock.assert_not_called()

    def test_locked_keychain_recovers_before_browser_opens(self):
        keychain = Mock()
        keychain.unlocked.return_value = False
        password = Mock(return_value="test credential")
        self.assertTrue(module.ensure_keychain({}, keychain, password)["recovered_locked_keychain"])
        keychain.unlock.assert_called_once_with("test credential")

    def test_open_preserves_profile_without_restoring_tabs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Profile 2").mkdir()
            (root / "Profile 2/Preferences").write_text(
                json.dumps({"account_info": [{"email": "person@example.com"}]})
            )
            (root / "Local State").write_text(
                json.dumps(
                    {"profile": {"info_cache": {"Profile 2": {"user_name": "person@example.com"}}}}
                )
            )
            config = {"chrome_data": directory, "profiles": {"Profile 2": "person@example.com"}}
            arguments = module.profile_arguments(config, "Profile 2", "https://example.com/")
            self.assertIn("--profile-directory=Profile 2", arguments)
            self.assertFalse(
                any("restore" in a or "user-data-dir" in a or "incognito" in a for a in arguments)
            )
            config["profiles"]["Profile 2"] = "other@example.com"
            with self.assertRaisesRegex(module.StateError, "identity_mismatch"):
                module.profile_arguments(config, "Profile 2")

    def test_failed_secret_lookup_never_echoes_vendor_response(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            config.write_text("{}")
            config.chmod(0o600)
            output = io.StringIO()
            with (
                patch.object(
                    module, "ensure_keychain", side_effect=RuntimeError("private vendor response")
                ),
                contextlib.redirect_stdout(output),
            ):
                self.assertEqual(module.main(["--config", str(config)]), 1)
            self.assertNotIn("private vendor response", output.getvalue())
            self.assertEqual(
                json.loads(output.getvalue())["error"], "profile_state_operation_failed"
            )


if __name__ == "__main__":
    unittest.main()
