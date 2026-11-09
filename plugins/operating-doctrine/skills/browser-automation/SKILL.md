---
name: browser-automation
description: >
  Scripted browser work through the signed-in Chrome on Ember's M2, the computer set aside
  for AI browser work. Fires when a task needs a browser to get something done, above all
  GoHighLevel jobs the API cannot reach (building or editing workflows and automations,
  merging contacts, settings and UI-only screens), and also any site with no API, page
  checks, screenshots, or data pulls. Always works in the already signed-in Chrome through
  the shared Playwright Extension connector, which never raises Chrome's debugging prompt,
  never opens a fresh or signed-out browser, assumes Chrome and 1Password access until a
  real failure, picks the most durable and fastest path, keeps one working tab per task,
  and closes every tab it opens before it reports.
  Claude Code and Codex reach it through the playwright-ember tool. Defers to
  ember-browser-routing on which machine runs browser work. It inherits the
  operating-doctrine and never overrides it.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Approved by Allison 2026-10-20 (session on Ember's M2).
tier: plugin
zone: hands
status: live
inherits: operating-doctrine
defers-to: [ember-browser-routing, connection-first-implementation]
brand-scope: null
subtitle: "signed-in Chrome automation on Ember's M2, GHL first"
---

# Browser Automation

Allison is the CEO. AI is the implementer. Ember's M2 is a computer set aside for AI to use
the browser, and its Chrome is already signed in to the tools the business runs on. This
skill is how any AI session does real work there, especially in GoHighLevel, where much of
the work has no background API.

## Rule 0. Headless route first

<!-- RULED-BY: HQ Business Brain, [HQ][V1.0] Decision Log, 2026-11-03 entries "Headless access comes first, and no browser is used where headless access exists" and "Standing yes for headless access setup" date:2026-11-03 -->

Headless access comes first and no browser is used where headless access exists. The
newest Decision Log entry wins if this section ever differs.

Before any browser work, check the system in this order and stop at the first step that
applies.

1. **A connected MCP server or connector.** If one covers the system, use it.
2. **An API or CLI with its 1Password item.** Use it. Read the secret from 1Password at the
   moment it is needed and never print it.
3. **Set it up.** If the system could be reached headlessly but is not set up yet, set it
   up now and use it. No ask, no job to file.
4. **The browser, only for a vendor with no API.** Write down why there is no headless
   route.

The access map, a Google Sheet owned by Keys and Sign-Ins, lists each system, its hosts, its
headless route, its 1Password item and its status. The plugin's headless route check hook
(`hooks/headless_route_check.py`) checks browser navigation and `browser_tabs` new tabs
against it, and the URLs that `browser_run_code_unsafe` and `browser_evaluate` code
navigates to. It refuses a host whose system is live and names the route and item to use.
It lets a host whose system is setting up through, because the M2 browser is the next route
until the headless route is live (headless first, then the M2 browser, never a block). It lets a
vendor with no API through, and it lets an unmapped host through and logs it for Star's
nightly miss check. In browser code, write every navigation target as a full `https://`
URL, because the hook refuses a relative one it cannot resolve. It cannot see a URL held in
a variable, and a host shared with a feature that has no API stays open, so the order above
binds even when the hook lets a call through. A refusal names the route to use.
Switch to it. If the refusal is only out of date, update the hook.

## Rule 1. Signed-in Chrome only, through the shared connector

Open connections through the installed route's preflight, which checks the assigned
existing profile and signed-in account. Don't create a profile or pick another browser
to get past a failed preflight. A connector page or blank working tab is not a website
login, so check the application's own signed-in account and location as you work.

Every browser action runs in the signed-in Chrome on Ember's M2, reached through the
Playwright Extension with the shared connector below.

- Never launch a browser. No `chromium.launch()`, fresh profile, `--isolated`, incognito,
  headless, or copied cookies or logins.
- Do not attach through Chrome's remote-debugging port (`connect_over_cdp`). Chrome asks
  "Allow remote debugging?" on every new connection there, which stops unattended work.
  Use it only when the connector itself is down, and say so.
- If the connector cannot reach Chrome, that is a problem to report, not a reason to open
  a signed-out browser.

## Rule 2. Assume access until proven otherwise

Start every task assuming Chrome is signed in and 1Password is available. Do not ask
Allison whether you have access. Try first.

Report a block only after one of these really happens. A sign-in page by itself is not a
block.

- The connector fails to connect twice in a row.
- A sign-in page appears and neither the 1Password fill in Chrome nor single sign-on gets you
  in.
- MFA, CAPTCHA, or a human approval screen appears.
- A sign-up page or a new consent screen appears, which is new account access.

When blocked by a human-only screen, leave it open on the M2, tell Allison the one thing
only she can do and where, and pick up again when she says done. If a better tool exists,
use it.

## Rule 2a. Follow the trail before you ask

Allison leaves a trail. The Ember Chrome on the M2 is already signed in to the business
tools, its bookmarks bar goes straight to them, and 1Password holds every login. Asking her
about access before following that trail is the most common way AI stalls her work.

1. Follow Rule 0. Use the MCP server, connector, API or CLI when the system has one, and
   file the setup job when it could have one.
2. Otherwise open the page with the `playwright-ember` tool. You are almost always already signed
   in. Look before you assume you are not.
3. Only on a real sign-in page, use the saved login that 1Password offers in Chrome, or the
   site's Sign in with Google or other single sign-on button, then keep working. Never read a
   password into the session's own context.
4. Only if all of that truly fails, tell Allison the one thing only she can do.

<!-- RULED-BY: HQ Business Brain, [HQ][V1.0] Decision Log, 2026-11-03 entry "AI uses the sign-ins Allison set up, without waiting for her" date:2026-11-03 -->

When 1Password in Ember's Chrome on the M2 offers a saved login, or a site offers Sign in with
Google or another single sign-on for an account already signed in there, sign in and keep
working. 1Password fills the credential itself, so no AI types or sees a password. If an
account chooser appears, pick the identity already linked to that site, the one its 1Password
item or saved account names. A sign-up page or new consent screen is a human step, so leave it
open and tell Allison.

Never ask her which browser to use or whether you are signed in. Do not use the Claude in Chrome extension for this work. It
drives Allison's own Chrome on the M4. `playwright-ember` is the only browser tool that
reaches the M2.

## Rule 3. Most durable and fastest, not easiest

Choose the path that finishes the whole job reliably and quickly.

1. **Headless whenever the system has it.** Rule 0 decides. Contacts, tags, custom fields,
   opportunities, and messages in GHL have API routes, so they never go through the
   browser. Do not split one job across tools just because one step is easier somewhere.
2. **Signed-in Chrome only where no headless route exists.** Workflow building and editing,
   contact merges, settings, and any screen without an API, with that reason written in the
   report. GHL has no public API to create or edit workflows (verified 2026-10-20, still an
   open request on HighLevel's ideas board).
   Recheck the API for other features at the start of each new kind of job, because GHL
   keeps adding them.

Durable also means scripts that survive GHL interface changes. Use visible text, roles, and
labels to find things, not fragile CSS paths. Wait for the page to be ready instead of
using fixed sleeps. GHL draws much of its app inside iframes, so look inside frames before
deciding an element is missing.

## Rule 4. Browser tabs stay clean

The M2 is shared by every project and agent. Leftover tabs slow it down and confuse other
sessions. This rule follows the HQ Rulebook's Browser tabs stay clean section (Decision Log
2026-10-22, Browser tabs stay clean), which wins if the two ever differ.

- One working tab per task. Reuse it by navigating in place instead of opening a new tab
  for each page.
- Open a second tab only when you truly need two pages side by side, and close it right
  after.
- Keep the job's own "Welcome" connector page while its connection is active. Create
  and retain a separate owned working Page. Do not navigate the connector page as the
  working page or reuse another job's connector.
- Close every tab you opened before you report or end your turn, except a recorded pending human-handoff tab, which stays open only until its return or closure condition is met.
  End with `browser_tabs` close on each of your other tabs.
  `browser_close` alone leaves the tab open in extension mode.
- After a crash or reconnect, close your own leftover tabs before starting again.
- Keep a human verification handoff, such as a sign-in or MFA step, in this job's own
  owned working tab, where the job can recover and close it. Before opening any page
  outside the job, verify an authorized route that can close it. Without one, do not open
  it unless an explicit exception is recorded.
- No completed owned tab survives your report. While a human step is still pending,
  record the exact tab, its owning job, the return condition and when it closes.
- Never close another AI's tabs or Allison's. The extension gives each connection its own
  tab group and shows it only those tabs, so work only inside your own group.
- Never close the window or the browser.

## The setup on Ember's M2

The route itself lives in one place, the AI Implementation SOP in HQ Company Core
(sections 5 and 8, and How code sessions reach the M2). If this table and the SOP ever
differ, the SOP wins. Verified live Nov 2, 2026, after the Nov 1 M2 rebuild.

| Item | Value |
|---|---|
| Machine | Ember's M2 only. One Mac user, `ember`. There is no `/Users/allison` on the M2 any more |
| Chrome profile | `Default` only (ember@expertpartners.com, allison@ also added in Google), Playwright Extension installed. The Atlas profile did not come back after the rebuild |
| Shared connector | `/Users/ember/maintenance/chrome-signed-in-mcp.sh` (Playwright MCP 0.0.83, pinned, `--extension`) |
| Extension token | 1Password, Automation vault, item ID `tzqvnlgilv4evwffp27amnwxw4`. The connector reads an owner-only copy at `~/.config/ember/playwright-extension-token`, because SSH sessions cannot unlock the Keychain |
| Job runner | None since the rebuild. `pw-run` is gone |

Claude Code and Codex start on Allison's M4 and reach that Chrome through the named
`playwright-ember` route. The name does not prove that each chat received a separate
physical connection. Read the SOP for the installed per-job consumer route.

```text
command: ssh
args:    -T -o BatchMode=yes -o ConnectTimeout=8 ember /Users/ember/maintenance/chrome-signed-in-mcp.sh
```

- There is no `playwright` or `playwright-atlas` server. Any config or note naming them, a
  `/Users/allison` path, or a separate browser profile is out of date. Do not guess a route;
  read the SOP.
- Never use Claude in Chrome, the Codex browser, Chrome or computer-use plugins, or a local
  Playwright plugin. Each one drives Allison's M4 or a signed-out browser.

Concurrent jobs require distinct persistent connections, owned windows and working
pages. Create each window before extension attachment. A group color organizes the
connection's tabs but does not isolate cookies, application identity or business
records. Each record still has one editor. The AI acts as whoever is signed in, and
changes show under that person's name. Follow the full ownership and recovery steps
in [ember-browser-routing](../ember-browser-routing/SKILL.md).

### Chrome settings that keep the M2 clean

- Chrome runs with `--silent-debugger-extension-api`, which hides the "Playwright Extension
  started debugging this browser" bar. The login item
  `~/Library/LaunchAgents/com.expertpartners.chrome-ai.plist` starts Chrome that way at login.
  If Chrome must be restarted, quit it normally and reopen it with
  `open -a "Google Chrome" --args --silent-debugger-extension-api`, after noting any open
  tabs, because Chrome is not set to restore them. Confirm the flag with `ps`.
- In both profiles, Settings, Appearance, "Automatically pin new tab groups to the bookmarks
  bar" and "Show tab groups in bookmarks bar" are off, so AI tab groups never pile up on the
  bar. If buttons ever reappear, turning "Show tab groups in bookmarks bar" off clears them
  all at once.

### Running a job

Use the installed owned-connection route from the SOP. Keep its transport handle and
the exact working Page reference for this job. For a scripted job, create that Page
once from the owned context and retain it through navigation. `browser_run_code_unsafe`
receives the current Page, which may initially be the connector rather than the
working Page. Verify the exact target before acting. Use ordinary browser tools only
through this job's verified connection.

When the installed route exposes `browser_job_start`, start a new named job for
this task and pass its returned `job_id` on every browser tool call. Finish it with
`browser_job_finish` before reporting. Never borrow another task's handle. A failed
action has an uncertain outcome and is not automatically replayed. The packaged
route supplies the separate connection and window, retains the working Page and
checks headless policy internally as well as through native consumer hooks.

For one call that reveals or moves a secret, pass `sealed: true` with only `code` to
`browser_run_code_unsafe`. The route then captures no console, page errors, network
events, snapshot or tab headers, does not echo the code, and answers only
`{"sealed": "ok"}` or a fixed error code. Stage the page with ordinary read-only calls
first. After the sealed call the job accepts only `browser_job_status` and
`browser_job_finish`; confirm the result with a fresh job. Treat any sealed error as an
uncertain outcome: reconcile and stop, never repeat the call. Each job receipt keeps
stage timestamps for its recent calls, with no page content.

The existing-profile window adapter is packaged with this skill. Its
[connection procedure](references/owned-connections.md) explains its boundaries. Do not replace a failed connection or replay an uncertain tab creation until the original
owned-page disposition is known.

### Health check

Open a new tab at `https://accounts.google.com/SignOutOptions`, read the signed-in emails
with `browser_evaluate`, and close the tab. Expect `ember@expertpartners.com`, and a tab list
that ends with only the connector's Welcome tab.

### Rotating the token

Open the extension's status page in the `Default` profile, click "Generate new token",
copy it, and replace the value in the 1Password item. Copying it with its
`PLAYWRIGHT_MCP_EXTENSION_TOKEN=` label is fine, because the connector strips the label.
Never print, log, or paste the token anywhere else.

## 1Password

For a browser sign-in, use the saved login 1Password offers in Chrome or the site's single
sign-on, as Rule 2a says. Never read a password with `op` for a browser sign-in. Use the `op`
command with the service account only for secrets a script or the connector needs, such as the
extension token. Read such a secret at the moment it is needed and never print, log, save, or
commit it. If a GHL session has expired, sign back in with the 1Password fill or single sign-on
before reporting anything.

## GoHighLevel guardrails

- **Right location.** Work in the right sub-account, not Legacy Expert Partners.
- **Capture state first.** A screenshot plus the values you are about to change gives you
  a way back.
- **Bulk changes** follow the ghl-tag-audit-and-cleanup pattern, with a rollback export.
- **Contact merges, deletes, sends and workflow publishing** can't be undone, so export
  what you need first, then go ahead.
- **Say what is there.** Report what the API or screen shows after the change.

## Writing and keeping jobs

- A job that will run again lives in the repo that owns the work. One-time work runs from
  the session scratchpad. Never in this skills repo, never in a business brain.
- Respect site terms, keep the pace human, and never get around a CAPTCHA or bot block.
- There is no scheduled browser runner since the Nov 1 rebuild. A browser job that needs
  to run on a schedule is a build for the Ember Rebuild room, not a cron line.

## Every AI on the M2

This skill ships in the operating-doctrine plugin of the expert-partners marketplace, which
Claude Code, Claude surfaces, and Codex load. Claude Code and Codex reach the M2 browser
through the installed per-job `playwright-ember` route. Each job needs a distinct
retained connection and a window created before attachment. The shared skill teaches
the procedure, while the installed launcher and consumer prove its actual behavior.
Verify source publication, local delivery and real use separately.

## Reporting

Say what ran, where, and what came back, with real output and links. A page that loaded is
not proof the change landed, so look at what GHL shows.

A session that used a browser ends its report with these two lines, which the headless
route hook supplies.

```text
Headless route checked, <system>, <result>
Tabs left open, none
```

The result is one of `live, used <route>`, `setting up, setup job filed first`,
`no API, <reason>`, `not on the access map, <what you did>`, or `not checked, <why>`. For
example, `Headless route checked, GoHighLevel workflows, no API, no public workflow API`.
The headless route check hook hands the session the line to use, both when it refuses a call
and when it lets one through.
