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
WITHHELD_SAMPLE = "sk-" + "a1b2c3d4" * 5
HEX_SAMPLE = "0123456789abcdef" * 3

MAP_CSV = (
    "System,Hosts,Headless route,1Password item,Status,No-API reason\n"
    "GoHighLevel contacts,\"app.gohighlevel.com, *.leadconnectorhq.com\","
    "GHL API v2 through the n8n connector,GHL Private Integration Token,Live,\n"
    "Cloudflare,dash.cloudflare.com,Cloudflare MCP server,Cloudflare API Token,Setting up,\n"
    "Vendor portal,portal.vendor.example,,,No API,Vendor offers no API or export\n"
    "Google,google.com,Google Workspace connector,,Live,\n"
    "Google Sites editor,sites.google.com,,,No API,No API for the Sites editor\n"
    "HubSpot,app.hubspot.com,mcp__claude_ai_HubSpot__search_crm_objects,"
    "op://Engineering/hubspot-private-app/credential,Live,\n"
    "Shared app,shared.example,Shared API,Shared API key,Live,\n"
    "Shared app builder,shared.example,,,No API,Builder has no API\n"
    "Example marketing,example.com,,,No API,Static site with no API\n"
    "Example app,*.example.com,Example API,Example API key,Live (API),\n"
    "Wording,setup.example,Wording API,Wording key,Setup,\n"
)
MAP_HEADER, _, MAP_ROWS = MAP_CSV.partition("\n")
REVERSED_MAP_CSV = MAP_HEADER + "\n" + "\n".join(reversed(MAP_ROWS.strip().split("\n"))) + "\n"
# The fictional public fixture for a live row whose browser host is still unresolved.
EVIDENCE_HEADER = "System,Hosts,Headless route,1Password item,Status,No-API reason,Host evidence\n"
EVIDENCE_ROWS = (
    "Known route,example.test,Known API,,live,,verified\n"
    "Native integration,,Existing native connector,,live,,unresolved\n"
)
LEAKY_ROWS = (
    "Leaky row,leaky.example,Leaky API," + WITHHELD_SAMPLE + ",Live,\n"
    "Hex row,hex.example,Hex API," + HEX_SAMPLE + ",Live,\n"
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
        self.old_env = {
            k: os.environ.get(k)
            for k in ("EP_HEADLESS_ROUTE_DIR", "EP_HEADLESS_ROUTE_CONFIG", "EP_ACCESS_MAP_SHEET_ID")
        }
        os.environ.update(
            {k: self.env[k] for k in ("EP_HEADLESS_ROUTE_DIR", "EP_HEADLESS_ROUTE_CONFIG")}
        )
        os.environ.pop("EP_ACCESS_MAP_SHEET_ID", None)

    def tearDown(self):
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def write_cache(self, csv_text=MAP_CSV + LEAKY_ROWS):
        hrc.write_cache(hrc.parse_map(csv_text))

    def fresh_stamp(self):
        """A recent refresh attempt, so the hook starts no background refresh."""
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / hrc.STAMP_FILE).touch()

    def run_hook(
        self, url, tool="mcp__playwright-ember__browser_navigate", tool_input=None, cwd=None
    ):
        if tool_input is None:
            tool_input = {"url": url}
        payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}
        if cwd is not None:
            payload["cwd"] = cwd
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=self.env,
            timeout=20,
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

    def assertAllowed(self, output):
        """The call goes through with no permission decision, and the note carries the report line."""
        self.assertIsNotNone(output, "expected an allow note")
        specific = output["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "PreToolUse")
        self.assertNotIn("permissionDecision", specific)
        self.assertIn("Report it as: Headless route checked, ", specific["additionalContext"])
        return specific["additionalContext"]


class Decisions(HookCase):
    def setUp(self):
        super().setUp()
        self.write_cache()
        self.fresh_stamp()

    def test_live_system_is_denied_with_route_and_item(self):
        reason = self.assertDenied(
            self.run_hook("https://app.gohighlevel.com/v2/location/abc/contacts")
        )
        self.assertIn("GoHighLevel contacts", reason)
        self.assertIn("GHL API v2 through the n8n connector", reason)
        self.assertIn("GHL Private Integration Token", reason)
        self.assertIn("Headless route checked, GoHighLevel contacts, live", reason)
        self.assertIn("denied", self.read(hrc.HOOK_LOG_FILE))

    def test_live_wildcard_subdomain_is_denied_for_every_navigation_tool(self):
        for tool in (
            "mcp__playwright-allison__browser_navigate",
            "mcp__claude-in-chrome__navigate",
            "mcp__claude-in-chrome__tabs_create_mcp",
        ):
            with self.subTest(tool=tool):
                self.assertDenied(self.run_hook("https://link.leadconnectorhq.com/x", tool))

    def test_setting_up_is_allowed_because_the_browser_is_the_next_route(self):
        note = self.assertAllowed(self.run_hook("dash.cloudflare.com/profile"))
        self.assertIn("Cloudflare", note)
        self.assertIn("never a block", note)

    def test_no_api_is_allowed(self):
        note = self.assertAllowed(self.run_hook("https://portal.vendor.example/login"))
        self.assertIn(
            "Headless route checked, Vendor portal, no API, Vendor offers no API or export.", note
        )
        self.assertEqual(self.read(hrc.UNKNOWN_HOSTS_FILE), "")

    def test_most_specific_host_wins(self):
        self.assertIn(
            "Google Sites editor, no API",
            self.assertAllowed(self.run_hook("https://sites.google.com/edit")),
        )
        self.assertDenied(self.run_hook("https://docs.google.com/document/d/x"))

    def test_unknown_host_is_allowed_and_logged_once(self):
        note = self.assertAllowed(self.run_hook("https://new-vendor.example/dashboard"))
        self.assertIn("Headless route checked, new-vendor.example, not on the access map", note)
        self.assertAllowed(self.run_hook("https://new-vendor.example/other"))
        lines = self.read(hrc.UNKNOWN_HOSTS_FILE).splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            lines[0].split("\t")[1:],
            ["new-vendor.example", "mcp__playwright-ember__browser_navigate"],
        )

    def test_lookalike_host_is_not_matched(self):
        self.assertAllowed(self.run_hook("https://notgoogle.com/"))
        self.assertIn("notgoogle.com", self.read(hrc.UNKNOWN_HOSTS_FILE))

    def test_non_web_targets_are_allowed_and_not_logged(self):
        for url in (
            "about:blank",
            "chrome://extensions",
            "http://localhost:3000",
            "http://127.0.0.1:8080/x",
            "",
        ):
            with self.subTest(url=url):
                self.assertIsNone(self.run_hook(url))
        self.assertEqual(self.read(hrc.UNKNOWN_HOSTS_FILE), "")

    def test_secret_shaped_map_value_is_never_printed(self):
        reason = self.assertDenied(self.run_hook("https://leaky.example/"))
        self.assertNotIn(WITHHELD_SAMPLE, reason)
        self.assertIn("[withheld, not an item name]", reason)
        reason = self.assertDenied(self.run_hook("https://hex.example/"))
        self.assertNotIn(HEX_SAMPLE, reason)
        self.assertIn("[withheld, not an item name]", reason)

    def test_long_names_and_op_paths_are_printed(self):
        reason = self.assertDenied(self.run_hook("https://app.hubspot.com/contacts"))
        self.assertIn("Use mcp__claude_ai_HubSpot__search_crm_objects ", reason)
        self.assertIn("op://Engineering/hubspot-private-app/credential", reason)
        self.assertNotIn("withheld", reason)

    def test_equally_specific_rows_never_depend_on_row_order(self):
        for name, csv_text in (("sheet order", MAP_CSV), ("reversed", REVERSED_MAP_CSV)):
            with self.subTest(order=name):
                self.write_cache(csv_text)
                note = self.assertAllowed(self.run_hook("https://shared.example/builder"))
                self.assertIn("Shared app builder, no API, Builder has no API", note)
                self.assertIn(
                    "map-conflict\tshared.example decided by Shared app builder no api",
                    self.read(hrc.HOOK_LOG_FILE),
                )

    def test_wildcard_covers_subdomains_and_the_exact_row_covers_the_apex(self):
        for name, csv_text in (("sheet order", MAP_CSV), ("reversed", REVERSED_MAP_CSV)):
            with self.subTest(order=name):
                self.write_cache(csv_text)
                self.assertAllowed(self.run_hook("https://example.com/pricing"))
                reason = self.assertDenied(self.run_hook("https://app.example.com/"))
                self.assertIn("Example app", reason)

    def test_common_status_wordings_are_understood(self):
        self.assertIn("Example app", self.assertDenied(self.run_hook("https://app.example.com/")))
        self.assertIn("never a block", self.assertAllowed(self.run_hook("https://setup.example/")))
        self.assertEqual(
            [
                hrc.normalize_status(s)
                for s in (
                    "Live",
                    "Live - API",
                    "Setting up",
                    "Set up",
                    "In setup",
                    "No API",
                    "No-API",
                    "None",
                    "not live",
                    "",
                )
            ],
            [
                "live",
                "live",
                "setting up",
                "setting up",
                "setting up",
                "no api",
                "no api",
                "no api",
                "not live",
                "",
            ],
        )

    def test_browser_code_that_navigates_to_a_live_system_is_denied(self):
        cases = (
            (
                "mcp__playwright-ember__browser_run_code_unsafe",
                {
                    "code": "async (page) => { await page.goto('https://app.gohighlevel.com/v2/contacts'); }"
                },
            ),
            (
                "mcp__playwright-ember__browser_run_code",
                {
                    "code": "async (page) => { await page.goto(`https://app.gohighlevel.com/${id}`); }"
                },
            ),
            (
                "mcp__playwright-ember__browser_evaluate",
                {"function": "() => { window.location.href = \"https://app.gohighlevel.com/x\"; }"},
            ),
        )
        for tool, tool_input in cases:
            with self.subTest(tool=tool):
                reason = self.assertDenied(self.run_hook(None, tool, tool_input))
                self.assertIn("GoHighLevel contacts", reason)

    def test_protocol_relative_navigation_to_a_live_system_is_denied(self):
        cases = (
            (
                "mcp__playwright-ember__browser_navigate",
                {"url": "//app.gohighlevel.com/v2/contacts"},
            ),
            ("mcp__claude-in-chrome__navigate", {"url": "\\\\app.gohighlevel.com/x"}),
            (
                "mcp__playwright-ember__browser_evaluate",
                {"function": "() => { window.location.href = '//app.gohighlevel.com/x'; }"},
            ),
            (
                "mcp__playwright-ember__browser_run_code_unsafe",
                {"code": "async (page) => { await page.goto('//link.leadconnectorhq.com/x'); }"},
            ),
        )
        for tool, tool_input in cases:
            with self.subTest(tool=tool, tool_input=tool_input):
                self.assertIn(
                    "GoHighLevel contacts", self.assertDenied(self.run_hook(None, tool, tool_input))
                )

    def test_urls_are_read_the_way_browsers_read_them(self):
        # Each of these opens app.gohighlevel.com in a browser (WHATWG URL Standard), and
        # urlsplit reads none of them that way.
        urls = (
            "https:///app.gohighlevel.com/x",
            "https:app.gohighlevel.com/x",
            "https:\\\\app.gohighlevel.com/x",
            "https://app.gohighlevel.com\\@evil.example/",
            "https://user@evil.example@app.gohighlevel.com/",
            "https://app%2Egohighlevel%2Ecom/",
            "HTTPS://APP.GoHighLevel.COM.:443/",
            "https://\uff41\uff50\uff50\uff0egohighlevel\u3002com/",
            " \thttps://app.gohigh\nlevel.com/\n",
            "view-source:https://app.gohighlevel.com/",
            "/app.gohighlevel.com/x",
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(hrc.target_host(url), "app.gohighlevel.com")
                self.assertIn("GoHighLevel contacts", self.assertDenied(self.run_hook(url)))
        # The reverse: urlsplit says app.gohighlevel.com, a browser opens evil.example.
        self.assertEqual(
            hrc.target_host("https://evil.example\\@app.gohighlevel.com/"), "evil.example"
        )
        self.assertAllowed(self.run_hook("https://evil.example\\@app.gohighlevel.com/"))

    def test_escaped_strings_in_browser_code_are_read_as_javascript_reads_them(self):
        bodies = (
            "await page.goto('https:\\/\\/app.gohighlevel.com/x');",
            "await page.goto('https://app.goh\\x69ghlevel.com/');",
            "await page.goto(\"https://app.gohighlevel.com/it\\\"s\");",
            "location.href = 'https://app.gohighlevel.com\\u002fx';",
            "window.open(`https://app.gohighlevel.com\\u{2f}x`);",
        )
        for body in bodies:
            with self.subTest(code=body):
                reason = self.assertDenied(
                    self.run_hook(
                        None,
                        "mcp__playwright-ember__browser_run_code_unsafe",
                        {"code": f"async (page) => {{ {body} }}"},
                    )
                )
                self.assertIn("GoHighLevel contacts", reason)

    def test_relative_code_navigation_is_refused(self):
        bodies = (
            "location.href = '/contacts';",
            "location = 'contacts';",
            "location.assign('?page=2');",
            "window.open('#top');",
            "location.href = 'https:contacts';",
            "await page.goto(`${base}/contacts`);",
            "await page.goto(`https://${host}/contacts`);",
        )
        for body in bodies:
            with self.subTest(code=body):
                reason = self.assertDenied(
                    self.run_hook(
                        None,
                        "mcp__playwright-ember__browser_evaluate",
                        {"function": f"() => {{ {body} }}"},
                    )
                )
                self.assertIn("full https:// URL", reason)
        self.assertIn("unresolved-denied", self.read(hrc.HOOK_LOG_FILE))
        self.assertEqual(self.read(hrc.UNKNOWN_HOSTS_FILE), "")

    def test_a_live_host_is_named_before_a_relative_target(self):
        code = "() => { location.href = '/x'; window.open('https://app.gohighlevel.com/'); }"
        reason = self.assertDenied(
            self.run_hook(None, "mcp__playwright-ember__browser_evaluate", {"function": code})
        )
        self.assertIn("GHL Private Integration Token", reason)

    def test_code_in_a_file_is_checked(self):
        folder = Path(self.tmp.name) / "workspace"
        folder.mkdir()
        (folder / "job.js").write_text(
            "async (page) => { await page.goto('https://app.gohighlevel.com/'); }", encoding="utf-8"
        )
        tool = "mcp__playwright-ember__browser_run_code_unsafe"
        cases = (
            ("absolute", {"filename": str(folder / "job.js"), "code": "async (page) => {}"}, None),
            ("relative to cwd", {"filename": "job.js"}, str(folder)),
        )
        for name, tool_input, cwd in cases:
            with self.subTest(case=name):
                self.assertIn(
                    "GoHighLevel contacts",
                    self.assertDenied(self.run_hook(None, tool, tool_input, cwd=cwd)),
                )
        reason = self.assertDenied(
            self.run_hook(None, tool, {"filename": str(folder / "missing.js")})
        )
        self.assertIn("file the hook cannot open", reason)
        # browser_evaluate saves its result to filename, so that file is not read as code.
        self.assertIsNone(
            self.run_hook(
                None,
                "mcp__playwright-ember__browser_evaluate",
                {"function": "() => document.title", "filename": str(folder / "missing.js")},
            )
        )

    def test_browser_tabs_new_with_a_url_is_checked(self):
        tool = "mcp__playwright-ember__browser_tabs"
        self.assertIn(
            "GoHighLevel contacts",
            self.assertDenied(
                self.run_hook(None, tool, {"action": "new", "url": "https://app.gohighlevel.com/"})
            ),
        )
        self.assertIsNone(self.run_hook(None, tool, {"action": "new"}))
        self.assertIsNone(self.run_hook(None, tool, {"action": "list"}))

    def test_history_steps_open_no_new_site(self):
        for step in ("back", "forward"):
            with self.subTest(step=step):
                self.assertIsNone(self.run_hook(step, "mcp__claude-in-chrome__navigate"))
        self.assertEqual(self.read(hrc.UNKNOWN_HOSTS_FILE), "")

    def test_rows_with_one_status_on_one_host_name_every_route(self):
        twin_a = "Twin A,twin.example,Twin A API,Twin A key,Live,\n"
        twin_b = "Twin B,twin.example,Twin B API,Twin B key,Live,\n"
        reasons = []
        for name, csv_text in (
            ("sheet order", MAP_CSV + twin_a + twin_b),
            ("reversed", REVERSED_MAP_CSV + twin_b + twin_a),
        ):
            with self.subTest(order=name):
                self.write_cache(csv_text)
                reason = self.assertDenied(self.run_hook("https://twin.example/"))
                for part in (
                    "Twin A: Twin A API with the 1Password item Twin A key",
                    "Twin B: Twin B API with the 1Password item Twin B key",
                ):
                    self.assertIn(part, reason)
                reasons.append(reason)
        self.assertEqual(reasons[0], reasons[1])
        self.assertIn(
            "map-conflict\ttwin.example decided by Twin A, Twin B live",
            self.read(hrc.HOOK_LOG_FILE),
        )

    def test_browser_code_without_a_mapped_navigation_is_allowed(self):
        code = "async (page) => { await page.goto('https://portal.vendor.example/'); return page.title(); }"
        self.assertAllowed(
            self.run_hook(None, "mcp__playwright-ember__browser_run_code_unsafe", {"code": code})
        )
        self.assertIsNone(
            self.run_hook(
                None,
                "mcp__playwright-ember__browser_evaluate",
                {"function": "() => document.title"},
            )
        )

    def test_unrecognized_status_is_allowed_with_a_not_checked_line(self):
        self.write_cache(MAP_CSV + "Odd row,odd.example,,,Maybe later,\n")
        note = self.assertAllowed(self.run_hook("https://odd.example/"))
        self.assertIn("Headless route checked, Odd row, not checked, status not recognized", note)
        self.assertIn("unknown-status-allowed", self.read(hrc.HOOK_LOG_FILE))

    def test_every_navigated_host_gets_a_line(self):
        code = (
            "async (page) => { await page.goto('https://portal.vendor.example/');"
            " await page.goto('https://another-new.example/'); }"
        )
        note = self.assertAllowed(
            self.run_hook(None, "mcp__playwright-ember__browser_run_code_unsafe", {"code": code})
        )
        self.assertIn("Vendor portal, no API", note)
        self.assertIn("another-new.example, not on the access map", note)

    def test_bad_input_is_allowed(self):
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input="not json",
            capture_output=True,
            text=True,
            env=self.env,
            timeout=20,
        )
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertIn("hook-error", self.read(hrc.HOOK_LOG_FILE))


GITHUB_ROW = "GitHub,github.com,gh CLI with GH_TOKEN from 1Password,GitHub PAT,Live,\n"


class FounderOverrides(HookCase):
    """The 2026-11-11 founder-authorized, path-scoped overrides. The allow cases fail on
    main before the fix; the deny cases pin the scope so no other path slips through."""

    GHL = "app.gohighlevel.com"
    SETTINGS = "https://github.com/organizations/ExpertPartners/settings"
    CHECKS = "https://github.com/ExpertPartners/expert-partners-hub/pull/86/checks"

    def setUp(self):
        super().setUp()
        self.write_cache(MAP_CSV + GITHUB_ROW + LEAKY_ROWS)
        self.fresh_stamp()

    def test_ghl_builder_forms_and_media_paths_are_allowed(self):
        cases = (
            f"https://{self.GHL}/v2/location/abc/funnels/page-builder/123",
            f"https://{self.GHL}/v2/location/abc/forms/builder/xyz",
            f"https://{self.GHL}/v2/location/abc/media-library",
            f"https://app.leadconnectorhq.com/v2/location/abc/sites/builder",
        )
        for url in cases:
            with self.subTest(url=url):
                note = self.assertAllowed(self.run_hook(url))
                self.assertIn(
                    "GoHighLevel / PartnerSync builder, no API, no create operation", note
                )
        self.assertIn("founder-override-allowed", self.read(hrc.HOOK_LOG_FILE))

    def test_ghl_builder_code_call_with_only_builder_targets_is_allowed(self):
        code = (
            "async (page) => { await page.goto('https://app.gohighlevel.com/v2/location/abc/funnels/x');"
            " await page.goto('https://app.gohighlevel.com/v2/location/abc/media-storage'); }"
        )
        note = self.assertAllowed(
            self.run_hook(None, "mcp__playwright-ember__browser_run_code_unsafe", {"code": code})
        )
        self.assertIn("GoHighLevel / PartnerSync builder", note)

    def test_ghl_contacts_and_workflows_stay_denied(self):
        for path in ("/v2/location/abc/contacts", "/v2/location/abc/workflows"):
            with self.subTest(path=path):
                reason = self.assertDenied(self.run_hook(f"https://{self.GHL}{path}"))
                self.assertIn("GoHighLevel contacts", reason)

    def test_ghl_code_call_with_any_off_scope_target_is_denied(self):
        code = (
            "async (page) => { await page.goto('https://app.gohighlevel.com/v2/location/abc/funnels/x');"
            " await page.goto('https://app.gohighlevel.com/v2/location/abc/contacts'); }"
        )
        reason = self.assertDenied(
            self.run_hook(None, "mcp__playwright-ember__browser_run_code_unsafe", {"code": code})
        )
        self.assertIn("GoHighLevel contacts", reason)

    def test_github_settings_paths_and_pr86_checks_are_allowed(self):
        cases = (
            f"{self.SETTINGS}/apps/estate-brain-door/permissions",
            f"{self.SETTINGS}/apps/estate-brain-door/permissions/",
            f"{self.SETTINGS}/installations",
            f"{self.SETTINGS}/installations/",
            self.CHECKS,
            f"{self.CHECKS}/",
        )
        for url in cases:
            with self.subTest(url=url):
                note = self.assertAllowed(self.run_hook(url))
                self.assertIn(
                    "GitHub organization settings, no API, no installation-permission endpoint",
                    note,
                )
        self.assertIn("founder-override-allowed", self.read(hrc.HOOK_LOG_FILE))

    def test_github_paths_outside_the_grant_stay_denied(self):
        cases = (
            "https://github.com/ExpertPartners/expert-partners-hub/pull/86",
            f"{self.SETTINGS}/installations/177351892",
            f"{self.SETTINGS}/apps",
            f"{self.SETTINGS}/apps/estate-brain-door",
            "https://github.com/",
            "https://github.com/apps",
            "https://github.com/login",
        )
        for url in cases:
            with self.subTest(url=url):
                self.assertIn("GitHub", self.assertDenied(self.run_hook(url)))

    def test_github_code_call_with_any_off_scope_target_is_denied(self):
        code = (
            "async (page) => { await page.goto('https://github.com/organizations/ExpertPartners/settings/"
            "apps/estate-brain-door/permissions'); await page.goto('https://github.com/organizations/"
            "ExpertPartners/settings/installations/177351892'); }"
        )
        reason = self.assertDenied(
            self.run_hook(None, "mcp__playwright-ember__browser_run_code_unsafe", {"code": code})
        )
        self.assertIn("GitHub", reason)

    def test_native_tool_name_as_text_and_example_com_stay_allowed(self):
        self.assertAllowed(self.run_hook("mcp__playwright-ember__browser_navigate"))
        note = self.assertAllowed(self.run_hook("https://example.com/pricing"))
        self.assertIn("Example marketing, no API", note)


class MissingCache(HookCase):
    def test_missing_cache_is_allowed_and_logged(self):
        self.fresh_stamp()
        note = self.assertAllowed(self.run_hook("https://app.gohighlevel.com/"))
        self.assertIn(
            "Headless route checked, app.gohighlevel.com, not checked, no cached access map", note
        )
        self.assertIn("no-cache-allowed\tapp.gohighlevel.com", self.read(hrc.HOOK_LOG_FILE))

    def test_relative_code_navigation_without_a_cache_is_allowed_and_logged(self):
        self.fresh_stamp()
        note = self.assertAllowed(
            self.run_hook(
                None,
                "mcp__playwright-ember__browser_evaluate",
                {"function": "() => { location.href = '/contacts'; }"},
            )
        )
        self.assertIn("not checked, no cached access map", note)
        self.assertIn("no-cache-allowed\tunresolved target", self.read(hrc.HOOK_LOG_FILE))

    def test_corrupt_cache_is_allowed_and_logged(self):
        self.fresh_stamp()
        (self.state / hrc.CACHE_FILE).write_text("{not json", encoding="utf-8")
        self.assertAllowed(self.run_hook("https://app.gohighlevel.com/"))
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
        self.config.write_text(
            json.dumps({"fetch_command": [sys.executable, str(script)]}), encoding="utf-8"
        )

    def test_refresh_writes_the_cache(self):
        self.configure_fetch(MAP_CSV)
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        self.assertNotIn("not live, setting up or no API", message)
        cached = json.loads(self.read(hrc.CACHE_FILE))
        self.assertEqual(len(cached["systems"]), 11)
        self.assertEqual(
            cached["systems"][0]["hosts"], ["app.gohighlevel.com", "*.leadconnectorhq.com"]
        )
        self.assertEqual(cached["systems"][1]["status"], "setting up")

    def test_refresh_names_rows_with_an_unknown_status(self):
        self.configure_fetch(MAP_CSV + "Odd row,odd.example,,,Maybe later,\n")
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        self.assertIn("1 with a status that is not live, setting up or no API", message)
        self.assertIn("Odd row", message)

    def test_refused_sheet_export_explains_the_drive_scope(self):
        self.config.write_text(json.dumps({"sheet_id": "test-sheet"}), encoding="utf-8")
        error = hrc.urllib.error.HTTPError("https://docs.google.com/", 403, "Forbidden", {}, None)
        original = hrc.urllib.request.urlopen
        hrc.urllib.request.urlopen = lambda *args, **kwargs: (_ for _ in ()).throw(error)
        try:
            ok, message = hrc.refresh()
        finally:
            hrc.urllib.request.urlopen = original
        self.assertFalse(ok)
        self.assertIn("HTTP 403", message)
        self.assertIn("Drive scope", message)

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

    def test_incomplete_row_keeps_the_last_good_copy(self):
        self.write_cache()
        self.fresh_stamp()
        before = self.read(hrc.CACHE_FILE)
        ghl_row = MAP_ROWS.split("\n")[0]
        system, hosts, rest = (
            ghl_row.split(",", 1)[0],
            '"app.gohighlevel.com, *.leadconnectorhq.com"',
            ghl_row.rsplit('"', 1)[1],
        )
        cases = (
            ("no Hosts", "row 2 has no Hosts", system + ',""' + rest),
            ("no System", "row 2 has no System", "," + hosts + rest),
            (
                "no Status",
                "row 2 has no Status",
                system + "," + hosts + rest.replace(",Live,", ",,"),
            ),
        )
        for name, expected, row in cases:
            with self.subTest(case=name):
                self.configure_fetch(MAP_CSV.replace(ghl_row, row, 1))
                ok, message = hrc.refresh()
                self.assertFalse(ok)
                self.assertIn(expected, message)
                self.assertEqual(self.read(hrc.CACHE_FILE), before)
                self.assertDenied(self.run_hook("https://app.gohighlevel.com/v2/contacts"))

    def test_wholly_blank_rows_are_skipped(self):
        self.configure_fetch(MAP_CSV + ",,,,,\n,  ,,,,\n")
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        self.assertEqual(len(json.loads(self.read(hrc.CACHE_FILE))["systems"]), 11)

    def test_the_issue_fixture_parses(self):
        fixture = (
            "system,hosts,status\nKnown route,example.test,live\nUnresolved route,,setting up\n"
        )
        systems = hrc.parse_map(fixture)
        self.assertEqual([row["system"] for row in systems], ["Known route", "Unresolved route"])
        self.assertEqual((systems[1]["hosts"], systems[1]["status"]), ([], "setting up"))

    def test_first_install_with_unresolved_rows_caches_and_denies_known_hosts(self):
        self.fresh_stamp()
        note = self.assertAllowed(self.run_hook("https://example.test/"))
        self.assertIn("not checked, no cached access map", note)
        self.configure_fetch(
            "system,hosts,status\nKnown route,example.test,live\nUnresolved route,,setting up\n"
        )
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        self.assertIn("1 unresolved, still needing real host evidence", message)
        self.assertIn("Unresolved route", message)
        reason = self.assertDenied(self.run_hook("https://example.test/page"))
        self.assertIn("Known route", reason)
        note = self.assertAllowed(self.run_hook("https://elsewhere.example/"))
        self.assertIn("not on the access map", note)

    def test_declared_unresolved_row_is_kept_as_evidence(self):
        self.configure_fetch(MAP_CSV + "Future CRM,,,,Setting up,\n")
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        self.assertIn("1 unresolved, still needing real host evidence", message)
        self.assertIn("Future CRM", message)
        systems = json.loads(self.read(hrc.CACHE_FILE))["systems"]
        self.assertEqual(len(systems), 12)
        entry = next(row for row in systems if row["system"] == "Future CRM")
        self.assertEqual((entry["hosts"], entry["status"]), ([], "setting up"))

    def test_hostless_row_without_setting_up_still_fails(self):
        cases = (
            ("live", "NoHost Live,,,,Live,\n", "has no Hosts"),
            ("no status", "NoHost Blank,,,,\n", "has no Status"),
            ("unrecognized status", "NoHost Odd,,,,Maybe later,\n", "has no Hosts"),
        )
        for name, row, expected in cases:
            with self.subTest(case=name):
                self.configure_fetch(MAP_CSV + row)
                ok, message = hrc.refresh()
                self.assertFalse(ok)
                self.assertIn(expected, message)
                self.assertEqual(self.read(hrc.CACHE_FILE), "")

    def test_a_protected_row_losing_its_hosts_keeps_the_last_good_copy(self):
        self.write_cache()
        self.fresh_stamp()
        before = self.read(hrc.CACHE_FILE)
        ghl_row = MAP_ROWS.split("\n")[0]
        cases = (
            ("hostless", "the new map drops 2 host(s)", "GoHighLevel contacts,,,,Setting up,"),
            (
                "shrunk",
                "app.gohighlevel.com",
                'GoHighLevel contacts,*.leadconnectorhq.com,GHL API v2 through the n8n connector,GHL Private Integration Token,Live,',
            ),
        )
        for name, expected, row in cases:
            with self.subTest(case=name):
                self.configure_fetch(MAP_CSV.replace(ghl_row, row, 1))
                ok, message = hrc.refresh()
                self.assertFalse(ok)
                self.assertIn(expected, message)
                self.assertIn("mark the row no API or delete the whole row", message)
                self.assertEqual(self.read(hrc.CACHE_FILE), before)
                self.assertDenied(self.run_hook("https://app.gohighlevel.com/v2/contacts"))

    def test_marking_a_row_no_api_lifts_protection_on_purpose(self):
        self.write_cache()
        self.fresh_stamp()
        ghl_row = MAP_ROWS.split("\n")[0]
        retired = (
            'GoHighLevel contacts,"app.gohighlevel.com, *.leadconnectorhq.com",'
            ",GHL Private Integration Token,No API,Route retired"
        )
        self.configure_fetch(MAP_CSV.replace(ghl_row, retired, 1))
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        note = self.assertAllowed(self.run_hook("https://app.gohighlevel.com/v2/contacts"))
        self.assertIn("GoHighLevel contacts, no API, Route retired", note)

    def test_deleting_a_row_lifts_protection_on_purpose(self):
        self.write_cache()
        self.fresh_stamp()
        ghl_row = MAP_ROWS.split("\n")[0]
        self.configure_fetch(MAP_CSV.replace(ghl_row + "\n", "", 1))
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        note = self.assertAllowed(self.run_hook("https://app.gohighlevel.com/v2/contacts"))
        self.assertIn("not on the access map", note)

    def test_an_unresolved_row_gaining_hosts_updates_protection(self):
        self.configure_fetch(MAP_CSV + "Future CRM,,,,Setting up,\n")
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        self.assertIn("1 unresolved", message)
        self.configure_fetch(
            MAP_CSV + "Future CRM,future-crm.example,Future CRM API,Future CRM key,Live,\n"
        )
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        self.assertNotIn("unresolved", message)
        self.assertIn("Future CRM", self.assertDenied(self.run_hook("https://future-crm.example/")))

    def test_live_row_with_unresolved_host_evidence_is_kept_as_evidence(self):
        self.fresh_stamp()
        self.configure_fetch(EVIDENCE_HEADER + EVIDENCE_ROWS)
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        self.assertIn("1 unresolved, still needing real host evidence", message)
        self.assertIn("Native integration (live, Host evidence unresolved)", message)
        systems = json.loads(self.read(hrc.CACHE_FILE))["systems"]
        self.assertEqual([row["system"] for row in systems], ["Known route", "Native integration"])
        self.assertEqual(systems[0]["evidence"], "verified")
        native = systems[1]
        self.assertEqual(
            {
                key: native[key]
                for key in ("hosts", "route", "item", "status", "reason", "evidence")
            },
            {
                "hosts": [],
                "route": "Existing native connector",
                "item": "",
                "status": "live",
                "reason": "",
                "evidence": "unresolved",
            },
        )
        self.assertIn("Known route", self.assertDenied(self.run_hook("https://example.test/page")))
        note = self.assertAllowed(self.run_hook("https://native.example/"))
        self.assertIn("not on the access map", note)
        self.assertNotIn("Native integration", note)

    def test_setting_up_rows_still_declare_unresolved_with_the_host_evidence_column(self):
        self.configure_fetch(
            EVIDENCE_HEADER
            + EVIDENCE_ROWS
            + "Future CRM,,,,Setting up,,\nLater CRM,,,,Setting up,,Unresolved\n"
        )
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        self.assertIn("3 unresolved, still needing real host evidence", message)
        self.assertIn("Future CRM (setting up, no host yet)", message)
        self.assertIn("Later CRM (setting up, Host evidence unresolved)", message)

    def test_hostless_row_without_declared_unresolved_evidence_still_fails(self):
        cases = (
            ("live, Host evidence blank", "Half edit,,Some API,,live,,\n"),
            ("live, Host evidence verified", "Half edit,,Some API,,live,,verified\n"),
            ("live, another wording", "Half edit,,Some API,,live,,not resolved yet\n"),
            ("setting up, Host evidence verified", "Half edit,,Some API,,setting up,,verified\n"),
            ("no API, Host evidence unresolved", "Half edit,,,,no API,No API at all,unresolved\n"),
            (
                "unrecognized status, Host evidence unresolved",
                "Half edit,,,,Maybe later,,unresolved\n",
            ),
        )
        for name, row in cases:
            with self.subTest(case=name):
                self.configure_fetch(EVIDENCE_HEADER + EVIDENCE_ROWS + row)
                ok, message = hrc.refresh()
                self.assertFalse(ok)
                self.assertIn("row 4 has no Hosts", message)
                self.assertEqual(self.read(hrc.CACHE_FILE), "")

    def test_a_protected_row_declaring_unresolved_evidence_keeps_the_last_good_copy(self):
        self.fresh_stamp()
        self.configure_fetch(EVIDENCE_HEADER + EVIDENCE_ROWS)
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        before = self.read(hrc.CACHE_FILE)
        cases = (
            ("live", "Known route,,Known API,,live,,unresolved\n"),
            ("setting up", "Known route,,Known API,,setting up,,unresolved\n"),
        )
        for name, row in cases:
            with self.subTest(case=name):
                self.configure_fetch(EVIDENCE_HEADER + row + EVIDENCE_ROWS.split("\n", 1)[1])
                ok, message = hrc.refresh()
                self.assertFalse(ok)
                self.assertIn(
                    "the new map drops 1 host(s) the last good copy protects: example.test", message
                )
                self.assertEqual(self.read(hrc.CACHE_FILE), before)
                self.assertIn(
                    "Known route", self.assertDenied(self.run_hook("https://example.test/page"))
                )

    def test_unresolved_host_evidence_becoming_a_verified_host_updates_protection(self):
        self.fresh_stamp()
        self.configure_fetch(EVIDENCE_HEADER + EVIDENCE_ROWS)
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        self.assertAllowed(self.run_hook("https://native.example/"))
        resolved = EVIDENCE_ROWS.replace(
            "Native integration,,Existing native connector,,live,,unresolved",
            "Native integration,native.example,Existing native connector,,live,,verified",
        )
        self.configure_fetch(EVIDENCE_HEADER + resolved)
        ok, message = hrc.refresh()
        self.assertTrue(ok, message)
        self.assertNotIn("unresolved", message)
        reason = self.assertDenied(self.run_hook("https://native.example/"))
        self.assertIn("Native integration has headless access", reason)
        self.assertIn("Existing native connector", reason)

    def test_no_configuration_fails_without_a_cache(self):
        ok, message = hrc.refresh()
        self.assertFalse(ok)
        self.assertIn("no access map is configured", message)
        self.assertEqual(self.read(hrc.CACHE_FILE), "")

    def test_stale_stamp_starts_one_background_refresh(self):
        self.configure_fetch(MAP_CSV)
        self.assertAllowed(self.run_hook("https://app.gohighlevel.com/"))
        deadline = time.time() + 15
        while time.time() < deadline and not (self.state / hrc.CACHE_FILE).exists():
            time.sleep(0.1)
        self.assertTrue(
            (self.state / hrc.CACHE_FILE).exists(), "background refresh did not write the cache"
        )
        while time.time() < deadline and "refresh-ok" not in self.read(hrc.HOOK_LOG_FILE):
            time.sleep(0.1)
        self.assertDenied(self.run_hook("https://app.gohighlevel.com/"))
        self.assertEqual(self.read(hrc.HOOK_LOG_FILE).count("refresh-ok"), 1)

    def test_recent_stamp_starts_no_refresh(self):
        self.configure_fetch(MAP_CSV)
        self.fresh_stamp()
        self.assertAllowed(self.run_hook("https://app.gohighlevel.com/"))
        time.sleep(1)
        self.assertFalse((self.state / hrc.CACHE_FILE).exists())


class SecretShapes(unittest.TestCase):
    # Built at run time from fake parts, so no credential-shaped literal sits in the repository.
    SECRET_SAMPLES = {
        "AWS access key": "AK" + "IA" + "Q" * 8 + "7" * 8,
        "Stripe live key": "sk" + "_live_" + "a1B2" * 6,
        "Stripe test key": "rk" + "_test_" + "a1B2" * 4,
        "Stripe webhook secret": "wh" + "sec_" + "a1B2" * 6,
        "GitHub fine-grained token": "github" + "_pat_" + "a1B2" * 6,
        "GitLab token": "gl" + "pat-" + "a1B2" * 5,
        "Slack app token": "xa" + "pp-1-" + "A1" * 6,
        "Slack config token": "xo" + "xe-1-" + "a1" * 6,
        "SendGrid key": "S" + "G." + "a1B2c3" * 3 + "." + "d4E5f6" * 3,
        "Google OAuth client secret": "GOC" + "SPX-" + "a1B2" * 6,
        "npm token": "np" + "m_" + "a1B2" * 9,
        "Hugging Face token": "h" + "f_" + "a1B2" * 9,
        "credentials in a URL": "https://" + "user" + ":" + "hunter2" + "@vault.example/x",
        "password assignment": "pass" + "word=" + "letmein",
        "bearer header": "Bear" + "er " + "a1b2c3d4e5f6g7h8",
        "unknown prefix across underscores": "zz" + "_Ab3_Cd4_Ef5_Gh6_Ij7",
    }
    NAMES = (
        "GHL Private Integration Token",
        "GHL API v2 through the n8n connector",
        "mcp__claude_ai_HubSpot__search_crm_objects",
        "op://Engineering/hubspot-private-app/credential",
        "Stripe API key (restricted, read only)",
        "gh CLI with GH_TOKEN from 1Password",
        "ghl-private-integration-2026-11",
        "AWS CLI, profile ep-prod, item AWS access key",
    )

    def test_common_credential_formats_are_withheld(self):
        for name, sample in self.SECRET_SAMPLES.items():
            with self.subTest(shape=name):
                self.assertTrue(hrc.looks_like_secret(sample), name)
                self.assertEqual(hrc.safe(f"Use {sample} here"), "[withheld, not an item name]")

    def test_names_print_as_written(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                self.assertEqual(hrc.safe(name), name)


class HooksJson(unittest.TestCase):
    def test_matcher_covers_the_browser_navigation_tools(self):
        config = json.loads((HOOK.parent / "hooks.json").read_text(encoding="utf-8"))
        group = next(
            g
            for g in config["hooks"]["PreToolUse"]
            if "headless_route_check.py" in g["hooks"][0]["command"]
        )
        matcher = re.compile(group["matcher"])
        for tool in (
            "mcp__playwright-ember__browser_navigate",
            "mcp__playwright-allison__browser_navigate",
            "mcp__claude-in-chrome__navigate",
            "mcp__claude-in-chrome__tabs_create_mcp",
            "mcp__playwright-ember__browser_run_code_unsafe",
            "mcp__playwright-ember__browser_evaluate",
            "mcp__playwright-ember__browser_tabs",
        ):
            self.assertTrue(matcher.search(tool), tool)
        for tool in ("mcp__playwright-ember__browser_snapshot", "Bash", "WebFetch"):
            self.assertFalse(matcher.search(tool), tool)
        self.assertIn(
            "${CLAUDE_PLUGIN_ROOT}/hooks/headless_route_check.py", group["hooks"][0]["command"]
        )


if __name__ == "__main__":
    unittest.main()
