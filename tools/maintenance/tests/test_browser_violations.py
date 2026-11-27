"""The M4 browser sweep closes only browsers an AI opened, never Allison's own."""

import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "janitor", Path(__file__).resolve().parents[1] / "m4-scratch-janitor.py"
)
janitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(janitor)

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HELPER = "/Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Helper.app/Contents/MacOS/Google Chrome Helper"
SAFARI = (
    "/System/Volumes/Preboot/Cryptexes/App/System/Applications/Safari.app/Contents/MacOS/Safari"
)
PW = "/Users/a/Library/Caches/ms-playwright/chromium-1200/chrome-mac/Chromium.app/Contents/MacOS/Chromium"


class BrowserViolationTests(unittest.TestCase):
    def test_allisons_chrome_and_safari_are_never_violations(self):
        table = {
            100: (1, CHROME, CHROME),
            101: (100, HELPER, HELPER + " --type=renderer"),
            200: (1, SAFARI, SAFARI),
            300: (1, "/bin/zsh", "zsh"),
            301: (300, "/Users/a/.factory/bin/droid", "droid"),
        }
        self.assertEqual(janitor.browser_violations(table), [])

    def test_browser_under_an_agent_is_closed_and_attributed(self):
        table = {
            10: (1, "/Users/a/.factory/bin/droid", "droid"),
            11: (10, "/bin/zsh", "zsh -c x"),
            12: (11, CHROME, CHROME + " --user-data-dir=/tmp/x"),
            13: (12, HELPER, HELPER),
        }
        found = janitor.browser_violations(table)
        self.assertEqual(
            [(v["pid"], v["why"], v["agent_pid"]) for v in found], [(12, "opened by droid", 10)]
        )

    def test_orphaned_automation_browsers_are_found_by_build_or_flag(self):
        table = {
            20: (1, PW, PW + " --headless"),
            30: (1, CHROME, CHROME + " --enable-automation --remote-debugging-port=0"),
            31: (30, CHROME, CHROME),
        }
        found = {v["pid"]: v["why"] for v in janitor.browser_violations(table)}
        self.assertEqual(found, {20: "automation browser build", 30: "automation flag"})


if __name__ == "__main__":
    unittest.main()
