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

## Existing authenticated Chrome attachment

Use the registered `mcp__cua_ember__js` route. The standalone
`playwright_ember` launcher with `--user-data-dir .../ember-codex` starts a
separate automation profile; it does not attach to the signed-in Chrome app.
A lock on that directory is evidence about that automation process, not proof
that the authenticated browser is unavailable. Do not use `--isolated`, remove
locks, restart Chrome, copy authentication, or create another profile to bypass it.

<!-- RULED-BY: HQ Business Brain, V1 - Company Core - Decision Log, 2026-10-20 entry "Browser automation runs only in the signed-in Chrome on Ember's M2" date:2026-10-20 -->

Never open a fresh, signed-out, or separate-profile browser for any browser
work. Always use the signed-in Chrome, and assume it and 1Password are
available until a real failure proves otherwise.

Scripted, repeatable, or unattended jobs (GoHighLevel workflows, contact
merges, bulk UI work) follow [browser-automation](../browser-automation/SKILL.md).
It attaches Playwright to this same signed-in Chrome through the debugging
connection Chrome already exposes (verified live 2026-10-20), so it is the
same browser and not a second launcher. Every rule in this skill still applies
to it, including exact tab ownership, closing only its own tabs, and never
using Allison's M4.

Interactive work uses the `cua_ember` route below.

On first use, execute exactly one discovery call:

```javascript
await cua.getState();
```

Inspect the returned M2 browser/profile metadata and existing task URL. Select
that exact browser ID, never the first Chrome result. Browser IDs and profile
names are live observations, not permanent constants. If multiple profiles
match and the correct one cannot be established, stop on that ambiguity.

```javascript
let estateBrowser = await cua.getBrowser({id: verifiedBrowserId});
```

Read the returned API documentation. Name the session and create a task-owned
tab in that selected existing profile with `cua.createBrowserTab`, using a
unique `sessionName`. Preserve existing tabs, including another task's tab at
the same URL. Keep the returned tab handle and ID for every subsequent action.
Where the selected provider exposes `tab.playwright`, its locators and frame
inspection control that same authenticated tab; a second Playwright launcher
is unnecessary. Never assume a loopback listener is CDP: verify the endpoint
before configuring any attachment, and do not expose a new debugging listener.

If browser-provider enumeration fails or returns no usable target, attempt the
existing native app route before declaring browser access blocked:

```javascript
let emberChrome = await cua.getApp('com.google.Chrome');
```

Inspect fresh window, profile, URL and task ownership before input. Native app
input is not a substitute for exact tab isolation: if another task owns the
window or focus cannot be safely established, stop on that specific conflict.
Do not reset a runtime owned by another task. This fallback follows Aura
[decision 0104](https://github.com/ExpertPartners/aura/blob/main/decisions/0104-ember-native-browser-control-before-screen-sharing.md).

Treat attachment and app rendering as separate checks. First verify the
expected location/account in the authenticated browser. Then inspect the
requested app surface, including iframe content and read-only console errors.
A rendered shell with an empty workflow iframe does not prove missing login,
working workflows, or a ready workflow editor. Report each result separately;
never change cookies, extensions, credentials or business data to troubleshoot
without task authorization.

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
