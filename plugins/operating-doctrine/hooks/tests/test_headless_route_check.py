"""Tests for the headless route check hook. Each test uses its own scratch state folder.

Run from the repo root:
  python3 -m unittest discover -s plugins/operating-doctrine/hooks/tests -v
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "headless_route_check.py"

spec = importlib.util.spec_from_file_location("headless_route_check", HOOK)
hrc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hrc)

# Built at run time so no secret-shaped literal sits in the repository.
FAKE_SECRET = "sk-" + "a1b2c3d4" * 5

MAP_CSV = (
    "System,Hosts,Headless route,1Password item,Status,No-API reason\n"
    "GoHighLevel contacts,\"app.gohighlevel.com, *.leadconnectorhq.com\","
    "GHL API v2 through the n8n connector,GHL Private Integration Token,Live,\n"
    "Cloudflare,dash.cloudflare.com,Cloudflare MCP server,Cloudflare API Token,Setting up,\n"
    "Vendor portal,portal.vendor.example,,,No API,Vendor offers no API or export\n"
    "Google,google.com,Google Workspace connector,,Live,\n"
    "Google Sites editor,sites.google.com,,,No API,No API for the Sites editor\n"
    "Leaky row,leaky.example,Leaky API," + FAKE_SECRET + ",Live,\n"
)


class HookCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "state"
        self.config = Path(self.tmp.name) / "headless-route.json"
        self.env = dict(os.environ)
        self.env.pop("EP_ACCESS_MAP_SHEET_ID", None)
        self.env["EP_HEADLESS_ROUTE_DIR"] = str(self.state)
        self.env["EP_HEADLESS_ROUTE_CONFIG"] = str(self.config)
        self.old_env = {k: os.environ.get(k) for k in ("EP_HEADLESS_ROUTE_DIR", "EP_HEADLESS_ROUTE_CONFIG", "EP_ACCESS_MAP_SHEET_ID")}
        os.environ.update({k: self.env[k] for k in ("EP_HEADLESS_ROUTE_DIR", "EP_HEADLESS_ROUTE_CONFIG")})
        os.environ.pop("EP_ACCESS_MAP_SHEET_ID", None)

    def tearDown(self):
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def write_cache(self, csv_text=MAP_CSV):
        hrc.write_cache(hrc.parse_map(csv_text))

    def fresh_stamp(self):
        """A recent refresh attempt, so the hook starts no background refresh."""
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / hrc.STAMP_FILE).touch()

    def run_hook(self, url, tool="mcp__playwright-ember__browser_navigate"):
        payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"url": url}}
        result = subprocess.run(
            [sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True,
            text=True, env=self.env, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout) if result.stdout.strip() else None

    def read(self, name):
        path = self.state / name
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def assertDenied(self, output):
        self.assertIsNotNone(output, "expected a deny decision")
        specific = output["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "PreToolUse")
        self.assertEqual(specific["permissionDecision"], "deny")
        return specific["permissionDecisionReason"]


class Decisions(HookCase):
    def setUp(self):
        super().setUp()
        self.write_cache()
        self.fresh_stamp()

    def test_live_system_is_denied_with_route_and_item(self):
        reason = self.assertDenied(self.run_hook("https://app.gohighlevel.com/v2/location/abc/contacts"))
        self.assertIn("GoHighLevel contacts", reason)
        self.assertIn("GHL API v2 through the n8n connector", reason)
        self.assertIn("GHL Private Integration Token", reason)
        self.assertIn("Headless route checked, GoHighLevel contacts, live", reason)
        self.assertIn("denied", self.read(hrc.HOOK_LOG_FILE))

    def test_live_wildcard_subdomain_is_denied_for_every_navigation_tool(self):
        for tool in ("mcp__playwright-allison__browser_navigate", "mcp__claude-in-chrome__navigate",
                     "mcp__claude-in-chrome__tabs_create_mcp"):
            with self.subTest(tool=tool):
                self.assertDenied(self.run_hook("https://link.leadconnectorhq.com/x", tool))

    def test_setting_up_is_denied_and_says_the_setup_job_comes_first(self):
        reason = self.assertDenied(self.run_hook("dash.cloudflare.com/profile"))
        self.assertIn("Cloudflare", reason)
        self.assertIn("setup job comes first", reason)
        self.assertIn("Cloudflare API Token", reason)

    def test_no_api_is_allowed(self):
        self.assertIsNone(self.run_hook("https://portal.vendor.example/login"))
        self.assertEqual(self.read(hrc.UNKNOWN_HOSTS_FILE), "")

    def test_most_specific_host_wins(self):
        self.assertIsNone(self.run_hook("https://sites.google.com/edit"))
        self.assertDenied(self.run_hook("https://docs.google.com/document/d/x"))

    def test_unknown_host_is_allowed_and_logged_once(self):
        self.assertIsNone(self.run_hook("https://new-vendor.example/dashboard"))
        self.assertIsNone(self.run_hook("https://new-vendor.example/other"))
        lines = self.read(hrc.UNKNOWN_HOSTS_FILE).splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].split("\t")[1:], ["new-vendor.example", "mcp__playwright-ember__browser_navigate"])

    def test_lookalike_host_is_not_matched(self):
        self.assertIsNone(self.run_hook("https://notgoogle.com/"))
        self.assertIn("notgoogle.com", self.read(hrc.UNKNOWN_HOSTS_FILE))

    def test_non_web_targets_are_allowed_and_not_logged(self):
        for url in ("about:blank", "chrome://extensions", "http://localhost:3000", "http://127.0.0.1:8080/x", ""):
            with self.subTest(url=url):
                self.assertIsNone(self.run_hook(url))
        self.assertEqual(self.read(hrc.UNKNOWN_HOSTS_FILE), "")

    def test_secret_shaped_map_value_is_never_printed(self):
        reason = self.assertDenied(self.run_hook("https://leaky.example/"))
        self.assertNotIn(FAKE_SECRET, reason)
        self.assertIn("[withheld, not an item name]", reason)

    def test_bad_input_is_allowed(self):
        result = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True,
                                text=True, env=self.env, timeout=20)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertIn("hook-error", self.read(hrc.HOOK_LOG_FILE))


class MissingCache(HookCase):
    def test_missing_cache_is_allowed_and_logged(self):
        self.fresh_stamp()
        self.assertIsNone(self.run_hook("https://app.gohighlevel.com/"))
        self.assertIn("no-cache-allowed\tapp.gohighlevel.com", self.read(hrc.HOOK_LOG_FILE))

    def test_corrupt_cache_is_allowed_and_logged(self):
        self.fresh_stamp()
        (self.state / hrc.CACHE_FILE).write_text("{not json", encoding="utf-8")
        self.assertIsNone(self.run_hook("https://app.gohighlevel.com/"))
        log = self.read(hrc.HOOK_LOG_FILE)
        self.assertIn("cache-unreadable", log)
        self.assertIn("no-cache-allowed", log)


class Refresh(HookCase):
    def configure_fetch(self, csv_text=None, exit_code=0):
        script = Path(self.tmp.name) / "fetch.py"
        lines = ["import sys"]
        if csv_text is not None:
            lines.append(f"sys.stdout.write({csv_text!r})")
        lines.append(f"sys.exit({exit_code})")
        script.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.config.write_text(json.dumps({"fetch_command": [sys.executable, str(script)]}), encoding="utf-8")

    def test_refresh_writes_the_cache(self):
        self.configure_fetch(MAP_CSV)
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        cached = json.loads(self.read(hrc.CACHE_FILE))
        self.assertEqual(len(cached["systems"]), 6)
        self.assertEqual(cached["systems"][0]["hosts"], ["app.gohighlevel.com", "leadconnectorhq.com"])
        self.assertEqual(cached["systems"][1]["status"], "setting up")

    def test_failed_refresh_keeps_the_last_good_copy(self):
        self.write_cache()
        before = self.read(hrc.CACHE_FILE)
        self.configure_fetch(exit_code=3)
        ok, message = hrc.refresh()
        self.assertFalse(ok)
        self.assertIn("exited 3", message)
        self.assertEqual(self.read(hrc.CACHE_FILE), before)
        self.assertIn("refresh-failed", self.read(hrc.HOOK_LOG_FILE))

    def test_bad_columns_keep_the_last_good_copy(self):
        self.write_cache()
        before = self.read(hrc.CACHE_FILE)
        self.configure_fetch("<html><body>Sign in</body></html>\n")
        ok, message = hrc.refresh()
        self.assertFalse(ok)
        self.assertIn("missing the column", message)
        self.assertEqual(self.read(hrc.CACHE_FILE), before)

    def test_no_configuration_fails_without_a_cache(self):
        ok, message = hrc.refresh()
        self.assertFalse(ok)
        self.assertIn("no access map is configured", message)
        self.assertEqual(self.read(hrc.CACHE_FILE), "")

    def test_stale_stamp_starts_one_background_refresh(self):
        self.configure_fetch(MAP_CSV)
        self.assertIsNone(self.run_hook("https://app.gohighlevel.com/"))
        deadline = time.time() + 15
        while time.time() < deadline and not (self.state / hrc.CACHE_FILE).exists():
            time.sleep(0.1)
        self.assertTrue((self.state / hrc.CACHE_FILE).exists(), "background refresh did not write the cache")
        while time.time() < deadline and "refresh-ok" not in self.read(hrc.HOOK_LOG_FILE):
            time.sleep(0.1)
        self.assertDenied(self.run_hook("https://app.gohighlevel.com/"))
        self.assertEqual(self.read(hrc.HOOK_LOG_FILE).count("refresh-ok"), 1)

    def test_recent_stamp_starts_no_refresh(self):
        self.configure_fetch(MAP_CSV)
        self.fresh_stamp()
        self.assertIsNone(self.run_hook("https://app.gohighlevel.com/"))
        time.sleep(1)
        self.assertFalse((self.state / hrc.CACHE_FILE).exists())


class HooksJson(unittest.TestCase):
    def test_matcher_covers_the_browser_navigation_tools(self):
        config = json.loads((HOOK.parent / "hooks.json").read_text(encoding="utf-8"))
        group = config["hooks"]["PreToolUse"][0]
        matcher = re.compile(group["matcher"])
        for tool in ("mcp__playwright-ember__browser_navigate", "mcp__playwright-allison__browser_navigate",
                     "mcp__claude-in-chrome__navigate", "mcp__claude-in-chrome__tabs_create_mcp"):
            self.assertTrue(matcher.search(tool), tool)
        for tool in ("mcp__playwright-ember__browser_snapshot", "Bash", "WebFetch"):
            self.assertFalse(matcher.search(tool), tool)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/hooks/headless_route_check.py", group["hooks"][0]["command"])


if __name__ == "__main__":
    unittest.main()
