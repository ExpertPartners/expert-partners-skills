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

<!-- RULED-BY: history in GitHub Archive date:2026-10-08 -->

## Core rule

Claude Code and Codex may run from Allison's M4/local desktop, cloud session, terminal, or file environment as appropriate.

**All browser and graphical UI control runs on Ember's M2.**

Never attach to, click, type in, navigate, foreground, or move the cursor on Allison's M4 browser or local screen.

## Headless route first

<!-- RULED-BY: HQ Business Brain, [HQ][V1.0] Decision Log, 2026-11-03 entries "Headless access comes first, and no browser is used where headless access exists" and "Standing yes for headless access setup" date:2026-11-03 -->

The rule, what setup needs no ask and its exceptions live in HQ Business Brain: the HQ
Rulebook section Use the access Allison already gave, and the Decision Log 2026-11-03
entries Headless access comes first and Standing yes for headless access setup. Read them
there before acting. They win if this section ever differs.

Before any browser work, check the system in this order and stop at the first step that
applies.

1. A connected MCP server or connector that covers the system.
2. An API or CLI with its 1Password item.
3. If neither exists yet but could, a setup job filed right away as the first job on that
   system. The Decision Log entry Standing yes for headless access setup says which setup
   goes ahead without asking.
4. Only then a browser, and only for a vendor with no API, with that reason written down.

The access map, a Google Sheet owned by Keys and Sign-Ins, records each system's hosts,
headless route, 1Password item and status. The operating-doctrine plugin's headless route
check hook refuses any browser navigation to a system marked live, naming the route and item
to use, and to a system marked setting up, because the setup job comes first. A refusal is
the answer, not a blocker. Switch to the route it names and never get around it with
another browser tool. [browser-automation](../browser-automation/SKILL.md) Rule 0 carries
the full rule.

## Browser workflow

1. Follow Headless route first above. Use a browser only when that order ends at step 4.
   The first browser preflight verifies the assigned existing profile and expected
   signed-in account. Refuse a missing, unsigned or mismatched profile without
   opening a connection or choosing a fallback. Profile metadata is not proof of a
   live website session. Verify the target application's own account before acting.
2. When browser/UI work is required, connect to Ember's M2 through the `playwright-ember` tool, the one browser route (AI Implementation SOP, section 5).
3. Enumerate the M2 browser targets and select the exact tab/window needed for the current assignment.
4. Continue without asking Allison whether the M2 is available merely because other tabs, windows, tasks, or sessions are visible.
5. Keep one working tab per task and reuse it by navigating in place. Open a second tab only when two pages must sit side by side, and close it right after. Preserve pre-existing tabs and anything owned by another session or by Allison.

## Existing authenticated Chrome attachment

The route lives in one place, the AI Implementation SOP in HQ Company Core (section 5, How
each AI connects, and How code sessions reach the M2). Read it there, never guess it from a
tool list or an old config. Verified live Nov 2, 2026 after the Nov 1 M2 rebuild:

- Claude Code and Codex use `playwright-ember`, an SSH command from the M4 to the alias
  `ember` that starts `/Users/ember/maintenance/chrome-signed-in-mcp.sh` on the M2. It
  attaches to the M2's signed-in Chrome, `Default` profile (ember@expertpartners.com),
  through the Playwright Extension, with no debugging prompt.
- `cua_ember` and the underscore `playwright_ember` launcher (`--user-data-dir
  .../ember-codex`) are retired. Both pointed at `/Users/allison` on the M2, an account that
  no longer exists, and the second one started a separate automation profile. Both are
  removed from Codex's config on the M4, so in Codex the tool name `playwright_ember` now
  means only the live route.
- Never use Claude in Chrome, the Codex browser, Chrome or computer-use plugins, or a local
  Playwright plugin. Each one drives Allison's M4 or a signed-out browser.

<!-- RULED-BY: HQ Business Brain, [HQ][V1.0] Decision Log, 2026-10-20 entry "Browser automation runs only in the signed-in Chrome on Ember's M2" date:2026-10-20 -->

Never open a fresh, signed-out, or separate-profile browser for any browser
work. Always use the signed-in Chrome, and assume it and 1Password are
available until a real failure proves otherwise.

Scripted, repeatable, or unattended jobs (GoHighLevel workflows, contact
merges, bulk UI work) follow [browser-automation](../browser-automation/SKILL.md),
which uses the same `playwright-ember` route. Every rule in this skill still applies,
including exact tab ownership, closing only your own tabs, and never using Allison's M4.

On first use, obtain the job's own persistent connection through the installed route
recorded in the SOP. Verify its host, connection, window and owned working page before
acting. A shared tool name or a tab index is not connection ownership. Retain the
transport handle and the exact working Page reference throughout the job.

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
- a sign-in that neither the 1Password fill nor single sign-on covers, a sign-up or consent screen, or MFA, CAPTCHA, or approval that requires Allison;
- exact tab selection is impossible and proceeding could interfere with another session.

When stopped for one of those reasons, report the exact blocker. **Never fall back to Allison's M4 browser.**

## Multiple sessions

Multiple sessions may coexist on Ember's M2 when the installed route proves separate
connection ownership for those consumers. A different chat, another tab or another
window alone does not prove that separation.

- Allocate one persistent Playwright connection and one owned Chrome window per job.
  Create the window before the extension attaches, using the existing signed-in
  profile. Do not move an attached tab out of its group to create isolation.
- Bootstrap each connection and its working page as one short owned operation. Once
  initialized, separate jobs can operate concurrently. Retain direct Page references
  through navigation instead of borrowing a shared current-tab pointer.
- Keep the connector page while the job needs its connection. Do not navigate it as
  the working page. Close the job's own working pages before its own connector and
  transport. Preserve every pre-existing connector page and every other job.
- Treat disconnect and task-tab closure as separate operations. After a failure,
  reconcile exact owned pages before starting a replacement. A new connection using
  the same client name does not adopt the old pages.
- Verify Codex, Claude Code and Ember separately after delivery. Source tests, a
  marketplace version or a successful pilot do not prove all consumers use the route.

- Control only the tab/window belonging to the current assignment.
- Do not close, repurpose, or navigate another session's tabs or Allison's.
- Use exact tab selection when the integration supports it.
- If exact targeting genuinely cannot be established without risking another session, stop on that specific conflict rather than asking whether the whole M2 is available.

The narrow existing-profile window adapter and consumer acceptance checklist are
[packaged with browser-automation](../browser-automation/references/owned-connections.md). The SOP owns
the actual installed route and its current acceptance state. Do not copy a trial
path into instructions or bypass headless-route checks through a terminal helper.

## Local-screen protection

If a control target unexpectedly resolves to Allison's M4/local screen:

1. Stop before interacting.
2. Release or ignore that target.
3. Reconnect to Ember's M2.
4. Continue there.

Never use a click on Allison's M4 as a workaround to rebind browser control.

## Human-only browser actions

<!-- RULED-BY: HQ Business Brain, [HQ][V1.0] Decision Log, 2026-11-03 entry "AI uses the sign-ins Allison set up, without waiting for her" date:2026-11-03 -->

When 1Password in Ember's Chrome on the M2 offers a saved login, or a site offers Sign in with
Google or another single sign-on for an account already signed in there, Claude Code, Ember and
any AI working for Allison go ahead, sign in and keep working without asking her. 1Password fills
the credential itself, so no AI types or sees a password. The hard stops stay. New account access
(creating an account or adding access that does not exist yet), live releases, messages outside
approved campaigns and anything irreversible still need the applicable founder's yes, which is
Allison's for her own accounts. Single sign-on counts only
for a site account that already exists. If the button leads to a sign-up page, a new consent or
permissions screen, or asks to create anything, that is new account access, so stop and ask her.
If an account chooser appears, pick only the identity already linked to that site, the one its
1Password item or saved account names. If that is not clear, stop and ask, because many sites
create an account the moment an unlinked identity signs in.

A sign-in page by itself is not human-only. Use the 1Password fill or the single sign-on button
first, and never read a password into the session's own context.

If Allison must complete a sign-in that neither the 1Password fill nor single sign-on covers, MFA, CAPTCHA, approval, or another human-only action:

- leave the exact required screen open on Ember's M2;
- tell Allison the single required action and where it is;
- do not make her hunt for the page;
- resume on the M2 afterward.

## Housekeeping

This follows the HQ Rulebook's Browser tabs stay clean section (Decision Log 2026-10-22, Browser tabs stay clean), which wins if the two ever differ.

- Keep one working tab per task and reuse it by navigating in place.
- Close a second tab right after the side-by-side step that needed it.
- Close every tab this session opened before you report or end your turn, except a recorded pending human-handoff tab, which stays open only until its return or closure condition is met.
- After a crash or reconnect, close your own leftover tabs before starting again.
- Keep a human verification handoff in the job's own owned tab, where it can be recovered and closed. Before opening a page outside the job, verify an authorized route that can close it. Without one, do not open it unless an explicit exception is recorded.
- No completed owned tab survives the report. While a human step is still pending, record the exact tab, its owning job, the return condition and when it closes.
- Never close another AI's tabs or Allison's, and preserve every pre-existing tab.
- Never leave Allison's M4 browser or cursor altered.

## Reporting

Every report from a session that used a browser carries these two lines together. A report
without them is incomplete.

```text
Headless route checked, <system>, <result>
Tabs left open, none
```

The result is one of `live, used <route>`, `setting up, setup job filed first`,
`no API, <reason>`, `not on the access map, <what you did>`, or `not checked, <why>`. The
headless route check hook hands the session the line to use, both when it refuses a call and
when it lets one through.

## Dispatch wording

When a handoff needs an explicit browser line, use:

`BROWSER RULE: Check the headless route first, and use no browser for a system with headless access. Browser/UI work runs on Ember's M2 only. Allison's M4 may be used for code/terminal/files but never for browser control. Assume the M2 is available; do not ask because other M2 tabs/sessions are visible. Stop only on an explicit M2 browser-control failure, a sign-in that neither the 1Password fill nor single sign-on covers, MFA, CAPTCHA, a sign-up or consent screen, a human approval, or a genuine tab-selection conflict, and never fall back to the M4.`
