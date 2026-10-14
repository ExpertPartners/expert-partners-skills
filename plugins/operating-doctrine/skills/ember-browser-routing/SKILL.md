---
name: "ember-browser-routing"
description: "Routes browser and graphical UI work for Allison's Claude Code and Codex sessions to Ember's M2. Fires whenever a task needs Chrome, PartnerSync/GoHighLevel UI, browser automation, CUA/Ember, or another graphical browser step. Allison's M4 may run Claude Code, terminal and file work, but browser control never attaches to the M4. Treat Ember's M2 as the designated available browser host; other visible tabs, recent activity or parallel sessions do not by themselves make the M2 unavailable."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "browser work on Ember's M2, never Allison's M4"
---

# Ember Browser Routing

<!-- RULED-BY: aura/intake/2026-10-08-ruling-claude-code-location-and-remove-lock-that.md date:2026-10-08 -->

## Core rule

Claude Code and Codex may run from Allison's M4/local desktop, cloud session, terminal, or file environment as appropriate.

**All browser and graphical UI control runs on Ember's M2.**

Never attach to, click, type in, navigate, foreground, or move the cursor on Allison's M4 browser or local screen.

## Browser workflow

1. Use an API/MCP when it reliably completes the task without a browser.
2. When browser/UI work is required, connect to Ember's M2 through the available Ember/CUA/browser integration.
3. Enumerate the M2 browser targets and select the exact tab/window needed for the current assignment.
4. Continue without asking Allison whether the M2 is available merely because other tabs, windows, tasks, or sessions are visible.
5. Preserve pre-existing tabs and anything owned by another session. Close only temporary tabs/windows created by the current session when no longer needed.

## Availability rule

Treat Ember's M2 as the designated browser computer and assume it is available unless the browser-control layer itself proves otherwise.

Do **not** infer that the M2 is unavailable or occupied from:

- recent browser activity;
- another open tab or window;
- another named task visible in Chrome;
- an existing Chrome session;
- another Codex or Claude session using a different tab.

Those are normal operating conditions. Select the exact target and continue.

Stop only when the browser-control tool returns a real blocker, such as:

- connector unreachable after one normal retry;
- explicit exclusive-control or lock failure;
- no browser target can be enumerated or safely selected;
- authentication, MFA, CAPTCHA, or approval requires Allison;
- exact tab selection is impossible and proceeding could interfere with another session.

When stopped for one of those reasons, report the exact blocker. **Never fall back to Allison's M4 browser.**

## Multiple sessions

Multiple sessions may coexist on Ember's M2.

- Control only the tab/window belonging to the current assignment.
- Do not close, repurpose, or navigate another session's tabs.
- Use exact tab selection when the integration supports it.
- If exact targeting genuinely cannot be established without risking another session, stop on that specific conflict rather than asking whether the whole M2 is available.

## Local-screen protection

If a control target unexpectedly resolves to Allison's M4/local screen:

1. Stop before interacting.
2. Release or ignore that target.
3. Reconnect to Ember's M2.
4. Continue there.

Never use a click on Allison's M4 as a workaround to rebind browser control.

## Human-only browser actions

If Allison must complete login, MFA, CAPTCHA, approval, or another human-only action:

- leave the exact required screen open on Ember's M2;
- tell Allison the single required action and where it is;
- do not make her hunt for the page;
- resume on the M2 afterward.

## Housekeeping

Before ending browser work:

- keep only the M2 tabs needed for continuing work;
- close temporary M2 tabs created by this session when safe;
- preserve all pre-existing or other-session tabs;
- never leave Allison's M4 browser or cursor altered.

## Dispatch wording

When a handoff needs an explicit browser line, use:

`BROWSER RULE: Browser/UI work runs on Ember's M2 only. Allison's M4 may be used for code/terminal/files but never for browser control. Assume the M2 is available; do not ask because other M2 tabs/sessions are visible. Stop only on an explicit M2 browser-control failure, auth/MFA, or a genuine tab-selection conflict, and never fall back to the M4.`
