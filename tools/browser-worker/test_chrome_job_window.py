import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SOURCE = (Path(__file__).resolve().parents[2] / "plugins/operating-doctrine/skills/"
          "browser-automation/scripts/chrome_job_window.py")
spec = importlib.util.spec_from_file_location("chrome_job_window", SOURCE)
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)

CONNECTOR = ("chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/connect.html"
             "?mcpRelayUrl=ws%3A%2F%2F127.0.0.1%3A1234&token=SYNTHETIC_CANARY")


class ChromeWindowTests(unittest.TestCase):
    def profile_fixture(self, directory):
        root = Path(directory) / "profile-data"
        root.mkdir()
        metadata = {"profile": {"info_cache": {}}}
        for name in ("Default", "Profile 1"):
            (root / name).mkdir()
            metadata["profile"]["info_cache"][name] = {"user_name": "worker@example.test"}
            (root / name / "Preferences").write_text(json.dumps({"account_info": [{"email": "worker@example.test"}], "signin": {"allowed": True}}))
        (root / "Local State").write_text(json.dumps(metadata))
        return root

    def test_exact_forwarding_to_existing_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "Fake Chrome"
            binary.write_text("#!/bin/sh\nexit 0\n")
            binary.chmod(0o700)
            root = self.profile_fixture(directory)
            calls = []
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                result = wrapper.main(["--profile-directory=Profile 1", CONNECTOR],
                                      {"EP_BROWSER_EXECUTABLE": str(binary), "EP_BROWSER_EXPECTED_ACCOUNT": "worker@example.test"},
                                      lambda *args: calls.append(args), profile_root=root, running=lambda: True)
            self.assertEqual(result, 0)
            self.assertEqual(calls, [(str(binary), [str(binary), "--new-window", "--profile-directory=Profile 1", CONNECTOR])])
            self.assertEqual(out.getvalue() + err.getvalue(), "")

    def test_default_profile(self):
        self.assertEqual(wrapper.browser_arguments(["--profile-directory=Default", CONNECTOR]),
                         ["--new-window", "--profile-directory=Default", CONNECTOR])

    def test_unsigned_missing_and_wrong_profiles_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.profile_fixture(directory)
            wrapper.existing_signed_in_profile("Default", "WORKER@example.test", root)
            for name, expected in [("Profile 99", "worker@example.test"), ("Default", None),
                                   ("Default", "other@example.test")]:
                with self.subTest(name=name, expected=expected), self.assertRaises(wrapper.InvalidLaunch):
                    wrapper.existing_signed_in_profile(name, expected, root)
            local = json.loads((root / "Local State").read_text())
            local["profile"]["info_cache"]["Profile 1"]["user_name"] = ""
            (root / "Local State").write_text(json.dumps(local))
            with self.assertRaises(wrapper.InvalidLaunch):
                wrapper.existing_signed_in_profile("Profile 1", "worker@example.test", root)

    def test_profile_identity_requires_account_metadata_and_allowed_signin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.profile_fixture(directory)
            target = root / "Default/Preferences"
            for data in [{"account_info": []}, {"account_info": [{"email": "worker@example.test"}], "signin": {"allowed": False}}]:
                target.write_text(json.dumps(data))
                with self.assertRaises(wrapper.InvalidLaunch):
                    wrapper.existing_signed_in_profile("Default", "worker@example.test", root)
            target.write_text("{broken")
            with self.assertRaises(wrapper.InvalidLaunch):
                wrapper.existing_signed_in_profile("Default", "worker@example.test", root)

    def test_does_not_start_a_stopped_browser(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.profile_fixture(directory)
            called = []
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                result = wrapper.main(["--profile-directory=Default", CONNECTOR],
                                      {"EP_BROWSER_EXPECTED_ACCOUNT": "worker@example.test"},
                                      lambda *args: called.append(args), profile_root=root, running=lambda: False)
            self.assertEqual(result, 2)
            self.assertEqual(called, [])
            self.assertNotIn("SYNTHETIC_CANARY", err.getvalue())

    def test_refuses_other_origins_paths_profiles_and_browser_modes(self):
        cases = [
            ["--incognito", CONNECTOR], ["--guest", CONNECTOR],
            ["--user-data-dir=/tmp/fresh", CONNECTOR],
            ["--remote-debugging-port=9222", CONNECTOR],
            ["--profile-directory=../Default", CONNECTOR],
            ["--profile-directory=Default", "https://example.test/"],
            ["--profile-directory=Default", CONNECTOR.replace("/connect.html", "/status.html")],
            ["--profile-directory=Default", CONNECTOR.replace("mmlmfjhmonkocbjadbfplnigmagldckm", "other-extension")],
            ["--profile-directory=Default", CONNECTOR + "#extra"],
            ["--profile-directory=Default", CONNECTOR + "\n"],
            ["--profile-directory=Default", CONNECTOR, "--incognito"],
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments), self.assertRaises(wrapper.InvalidLaunch):
                wrapper.browser_arguments(arguments)

    def test_failures_never_log_connector_or_exception_details(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "fake-chrome"
            binary.write_text("#!/bin/sh\nexit 0\n")
            binary.chmod(0o700)
            root = self.profile_fixture(directory)
            def fail(*_):
                raise OSError(CONNECTOR)
            for arguments, env, execute in [
                (["--profile-directory=Default", CONNECTOR], {"EP_BROWSER_EXECUTABLE": str(binary), "EP_BROWSER_EXPECTED_ACCOUNT": "worker@example.test"}, fail),
                (["--guest", CONNECTOR], {}, fail),
                (["--profile-directory=Default", CONNECTOR], {"EP_BROWSER_EXECUTABLE": "/missing", "EP_BROWSER_EXPECTED_ACCOUNT": "worker@example.test"}, fail),
            ]:
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    self.assertEqual(wrapper.main(arguments, env, execute, profile_root=root, running=lambda: True), 2)
                self.assertNotIn("SYNTHETIC_CANARY", err.getvalue())
                self.assertNotIn("chrome-extension://", err.getvalue())


if __name__ == "__main__":
    unittest.main()
