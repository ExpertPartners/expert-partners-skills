import contextlib
import importlib.util
import io
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
    def test_exact_forwarding_to_existing_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "Fake Chrome"
            binary.write_text("#!/bin/sh\nexit 0\n")
            binary.chmod(0o700)
            calls = []
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                result = wrapper.main(["--profile-directory=Profile 1", CONNECTOR],
                                      {"EP_BROWSER_EXECUTABLE": str(binary)},
                                      lambda *args: calls.append(args))
            self.assertEqual(result, 0)
            self.assertEqual(calls, [(str(binary), [str(binary), "--new-window", "--profile-directory=Profile 1", CONNECTOR])])
            self.assertEqual(out.getvalue() + err.getvalue(), "")

    def test_default_profile(self):
        self.assertEqual(wrapper.browser_arguments(["--profile-directory=Default", CONNECTOR]),
                         ["--new-window", "--profile-directory=Default", CONNECTOR])

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
            def fail(*_):
                raise OSError(CONNECTOR)
            for arguments, env, execute in [
                (["--profile-directory=Default", CONNECTOR], {"EP_BROWSER_EXECUTABLE": str(binary)}, fail),
                (["--guest", CONNECTOR], {}, fail),
                (["--profile-directory=Default", CONNECTOR], {"EP_BROWSER_EXECUTABLE": "/missing"}, fail),
            ]:
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    self.assertEqual(wrapper.main(arguments, env, execute), 2)
                self.assertNotIn("SYNTHETIC_CANARY", err.getvalue())
                self.assertNotIn("chrome-extension://", err.getvalue())


if __name__ == "__main__":
    unittest.main()
