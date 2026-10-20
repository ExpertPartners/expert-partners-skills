---
name: browser-automation
description: >
  Scripted browser work through the signed-in Chrome on Ember's M2, the computer set aside
  for AI browser work. Fires when a task needs a browser to get something done, above all
  GoHighLevel jobs the API cannot reach (building or editing workflows and automations,
  merging contacts, settings and UI-only screens), and also any site with no API, page
  checks, screenshots, or data pulls. Always attaches to the already signed-in Chrome,
  never opens a fresh or signed-out browser, assumes Chrome access and 1Password access
  until a real failure proves otherwise, picks the most durable and fastest path rather
  than the easiest, and closes every tab it opens. Works the same in Claude Code and Codex.
  Defers to ember-browser-routing on which machine runs browser work. It inherits the
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
skill is how any Claude Code or Codex session does real work there, especially in
GoHighLevel, where much of the work has no background API.

## Rule 1. Signed-in Chrome only

Every browser action runs in the signed-in Chrome on Ember's M2.

- Attach to the Chrome that is already running. Never launch a new browser.
- Never use `chromium.launch()`, a fresh profile, `--isolated`, incognito, headless, or a
  copied set of cookies or logins.
- If a script cannot attach, that is a problem to report, not a reason to open a
  signed-out browser.

## Rule 2. Assume access until proven otherwise

Start every task assuming Chrome is signed in and 1Password is available. Do not ask
Allison whether you have access. Try first.

Report a block only after one of these really happens.

- Attaching to Chrome fails twice in a row.
- A login screen appears and signing in with the 1Password item fails.
- MFA, CAPTCHA, or a human approval screen appears.
- 1Password returns an error for the item you need.

When blocked, leave the exact screen open on the M2, tell Allison the one thing she needs
to do and where, and pick up again when she says done.

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

- Open one tab per task in the signed-in window and keep track of it.
- Close it in a `finally` block, so it closes even when the script fails.
- Never close, reuse, or navigate a tab you did not open.
- Never close the browser or the window. Disconnect only.
- Before reporting done, compare the tab count with the count when you started.

## The setup on Ember's M2

| Item | Value |
|---|---|
| Machine | Ember's M2 only |
| Python environment | `~/.venvs/playwright` |
| Playwright | 1.56.0 (pinned) |
| Chrome connection | the debugging connection Chrome already exposes, found in `~/Library/Application Support/Google/Chrome/DevToolsActivePort` |
| Secrets | 1Password service account through the `op` command |

Run scripts with the environment's Python directly, so they work the same from Claude
Code, Codex, cron, and agents.

```bash
~/.venvs/playwright/bin/python path/to/script.py
```

Read the Chrome connection from `DevToolsActivePort` every run. The address can change when
Chrome restarts, so never hardcode it. Do not turn on a new debugging port or change
Chrome's launch settings to get one.

### Attach pattern

```python
import pathlib
from playwright.sync_api import sync_playwright

PORT_FILE = pathlib.Path.home() / "Library/Application Support/Google/Chrome/DevToolsActivePort"

def chrome_address():
    port, path = PORT_FILE.read_text().split("\n")[:2]
    return f"ws://127.0.0.1:{port}{path}"

def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(chrome_address(), timeout=30000)
        context = browser.contexts[0]  # the signed-in Chrome
        page = context.new_page()      # this task's own tab
        try:
            page.goto("https://app.gohighlevel.com/", wait_until="domcontentloaded")
            # do the work here
        finally:
            page.close()               # close only this task's tab
        # never browser.close() or context.close()

if __name__ == "__main__":
    main()
```

### Health check

Run this before the first job of a session. It opens one GHL tab, confirms the session is
signed in, and closes the tab.

```bash
~/.venvs/playwright/bin/python - <<'PY'
import pathlib
from playwright.sync_api import sync_playwright
f = pathlib.Path.home()/"Library/Application Support/Google/Chrome/DevToolsActivePort"
port, path = f.read_text().split("\n")[:2]
with sync_playwright() as p:
    ctx = p.chromium.connect_over_cdp(f"ws://127.0.0.1:{port}{path}").contexts[0]
    before = len(ctx.pages); page = ctx.new_page()
    try:
        page.goto("https://app.gohighlevel.com/", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        print("signed in:", "login" not in page.url)
    finally:
        page.close()
    print("tabs back to start:", len(ctx.pages) == before)
PY
```

### Rebuild if the environment is missing

```bash
python3 -m venv ~/.venvs/playwright
~/.venvs/playwright/bin/pip install playwright==1.56.0
```

No browser download is needed, because scripts use the signed-in Chrome. Changing the
pinned version is Allison's decision, recorded in the Decision Log, and this table changes
in the same update.

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

## Writing and keeping scripts

- A script that will run again lives in the repo that owns the job. One-time work runs from
  the session scratchpad. Never in this skills repo, never in a business brain.
- Respect site terms, keep the pace human, and never get around a CAPTCHA or bot block.
- A script goes on cron only after it has run by hand and the result was checked. Use the
  full Python path, set `PATH` in the crontab line, and stay out of the nightly pipeline
  window (2:45 AM to 6:30 AM).

## Claude Code and Codex

This skill is the same for both. It ships in the operating-doctrine plugin of the
expert-partners marketplace, which Claude Code, Claude surfaces, and Codex all load. Both run the
same scripts with the same Python on the same signed-in Chrome, and the tab-ownership rule
is what lets them share the M2 without stepping on each other.

## Reporting

Say what ran, where, and what came back, with real output. A page that loaded is not proof
the change landed. Check the result against what GHL actually shows before calling it done,
and confirm the tab count is back where it started.
