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
  real failure, picks the most durable and fastest path, and closes every tab it opens.
  Same setup for Claude Code, Claude desktop, Codex and Gemini CLI. Defers to
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

## Rule 1. Signed-in Chrome only, through the shared connector

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

Report a block only after one of these really happens.

- The connector fails to connect twice in a row.
- A login screen appears and signing in with the 1Password item fails.
- MFA, CAPTCHA, or a human approval screen appears.
- 1Password returns an error for the item you need.

When blocked, leave the exact screen open on the M2, tell Allison the one thing she needs
to do and where, and pick up again when she says done. If a tool or access she needs is
missing, say so and name the better tool. She may not know it exists yet.

## Rule 3. Most durable and fastest, not easiest

Choose the path that finishes the whole job reliably and quickly.

1. **API or connector when it fully covers the job.** Contacts, tags, custom fields,
   opportunities, and messages in GHL have API routes and are the most durable path for
   those. Do not split one job across tools just because one step is easier somewhere.
2. **Signed-in Chrome for everything else.** Workflow building and editing, contact
   merges, settings, and any screen without an API. GHL has no public API to create or
   edit workflows (verified 2026-10-20, still an open request on HighLevel's ideas board).
   Recheck the API for other features at the start of each new kind of job, because GHL
   keeps adding them.

Durable also means scripts that survive GHL interface changes. Use visible text, roles, and
labels to find things, not fragile CSS paths. Wait for the page to be ready instead of
using fixed sleeps. GHL draws much of its app inside iframes, so look inside frames before
deciding an element is missing.

## Rule 4. Clean up every tab

The M2 is shared by every project and agent. Leftover tabs slow it down and confuse other
sessions.

- The extension gives each connection its own tab group and shows it only those tabs, so
  cleaning up your group can never touch anyone else's work.
- Each connection starts with a "Welcome" connect tab. Navigate it to your first page so
  it becomes your work tab, rather than leaving it behind.
- Close every tab in your group before you finish. `pw-run` does this automatically. In an
  MCP session, end with `browser_tabs` close on each of your tabs. `browser_close` alone
  leaves the tab open in extension mode.
- Never close the window or the browser.

## The setup on Ember's M2

| Item | Value |
|---|---|
| Machine | Ember's M2 only |
| Chrome profile | `Default` (ember@expertpartners.com), Playwright Extension installed |
| Shared connector | `~/maintenance/chrome-signed-in-mcp.sh` (Playwright MCP 0.0.83, pinned, `--extension`) |
| Job runner | `~/maintenance/pw-run.py` (also `~/bin/pw-run`) |
| Extension tokens | 1Password, Automation vault, two items titled `Playwright MCP Extension Token`, told apart by username (ember@ and atlas@); the connector reads them by item ID |
| Python environment | `~/.venvs/playwright` (Playwright 1.56.0) for local work that needs no browser |

Every AI client on the M2 (Claude Code, Claude desktop, Codex, Gemini CLI) has two MCP
servers that run the shared connector.

- `playwright` drives the Ember browser (`Default` profile). Use it unless told otherwise.
- `playwright-atlas` drives the Atlas browser (`Profile 3`). Use it when Allison says "use
  the Atlas browser" or the job needs the logins signed in there.

Several AIs can share one browser at once, each in its own tab group. Pick the browser by
the logins the job needs, not to avoid overlap. Tab groups do not stop two AIs from
changing the same record at the same time, so give each job to one AI. The AI acts as
whoever is signed in, and changes show under that person's name.

### Running a job

Write the job as one JavaScript function that receives a Playwright `page`, then run it.

```javascript
async (page) => {
  await page.goto('https://app.gohighlevel.com/', { waitUntil: 'domcontentloaded' });
  // do the work here
  return { title: await page.title() };
}
```

```bash
pw-run path/to/job.js            # add --timeout 600 for long jobs
```

`pw-run` prints what the function returns, closes every tab from the run, and exits
non-zero on any failure, so it works the same from a chat session, an agent, or cron.

### Health check

```bash
cat > /tmp/ghl-check.js <<'JS'
async (page) => {
  await page.goto('https://app.gohighlevel.com/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(4000);
  return { signedIn: !page.url().includes('login') };
}
JS
pw-run /tmp/ghl-check.js
```

Expect `{"signedIn":true}` and `pw-run: closed 1 tab(s) from this run`.

### More than one profile

Each Chrome profile can carry its own Playwright Extension with its own token, which lets
separate AI lanes work in separate signed-in profiles (for example Atlas for Don's work).
Install the extension in that profile, save its token in 1Password under its own item name,
and launch the connector with both set (`pw-run` passes them through too). The Atlas item ID is in the `playwright-atlas` server
settings, for example `claude mcp get playwright-atlas`.

```bash
CHROME_PROFILE_DIR="Profile 3" PW_TOKEN_ITEM="<Atlas token item ID>" \
  ~/maintenance/chrome-signed-in-mcp.sh
```

### Rotating the token

Open the extension's status page in the `Default` profile, click "Generate new token",
copy it, and replace the value in the 1Password item. Copying it with its
`PLAYWRIGHT_MCP_EXTENSION_TOKEN=` label is fine, because the connector strips the label.
Never print, log, or paste the token anywhere else.

## 1Password

Use the `op` command with the service account. Read a secret at the moment it is needed,
pass it straight to the page, and never print, log, save, or commit it. If a GHL session has
expired, sign back in with the matching 1Password item before reporting anything.

## GoHighLevel guardrails

- **Right location first.** Confirm the sub-account name on screen before any change. Never
  build on Legacy Expert Partners.
- **Read before write.** Capture the current state (a screenshot plus the values you are
  about to change) before changing anything.
- **Bulk changes** follow the ghl-tag-audit-and-cleanup pattern. Run a dry run, export a
  rollback file, get Allison's approval, then run the change.
- **Cannot be undone.** Contact merges, deletes, sends, and publishing a workflow need the
  applicable founder's yes first, even when everything else here is approved.
- **Prove it worked.** After a change, read it back through the API or the screen and
  report what is actually there, with a screenshot when it helps.

## Writing and keeping jobs

- A job that will run again lives in the repo that owns the work. One-time work runs from
  the session scratchpad. Never in this skills repo, never in a business brain.
- Respect site terms, keep the pace human, and never get around a CAPTCHA or bot block.
- A job goes on cron only after it has run by hand and the result was checked. Use the full
  path to `pw-run`, set `PATH` in the crontab line, and stay out of the nightly pipeline
  window (2:45 AM to 6:30 AM).

## Every AI on the M2

This skill ships in the operating-doctrine plugin of the expert-partners marketplace, which
Claude Code, Claude surfaces, and Codex load. Gemini CLI and the Claude desktop app reach
the same browser through their `playwright` MCP server. Tab groups are what let several AIs
share the M2 at once without stepping on each other.

## Reporting

Say what ran, where, and what came back, with real output. A page that loaded is not proof
the change landed. Check the result against what GHL actually shows before calling it done,
and confirm your tab group is empty.
