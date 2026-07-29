---
name: "code-block-routing"
description: "Fires every time a Claude Code paste block, intake block, or implementation brief is handed to Allison, in every project and every session: routing line naming the SURFACE and the exact session (PASTE INTO: Claude Code, existing session \"Name\"), session name as the first line inside the block so the session self-identifies, a waiting-on statement with every hand-off, the pin fired only AFTER Allison confirms the paste, one paste block per response, nothing fenced that is not for a terminal or Code, versions read from canonical only."
---

# Code Block Routing

Rule authored by Allison, 2026-07-27. Every time a block is handed to Allison to paste into a Claude Code session (intake block, implementation brief, fix instruction, verification request, anything), the block must be preceded by exactly one routing line, outside the code fence.

## The Routing Line Names The Surface, Not Just The Session

Amended 2026-07-28 at Allison's instruction: "always say paste into Claude Code Ember audit, even though it seems obvious, because sometimes the names get off." Naming the surface removes the ambiguity that appears when a session's window title has drifted from its authoritative name, or when the same workstream has both a Cowork conversation and a Claude Code session.

Required format, one of:

PASTE INTO: Claude Code, existing session "Session Name"

PASTE INTO: Claude Code, new session, name it "Short Name"

The surface always appears first and is always spelled Claude Code. Never ship a routing line that names only the session. Never shorten to "paste into Ember audit" or "Routing: ember-audit."

If a block is ever bound for a surface other than Claude Code, that surface is named the same way in the same position (for example, PASTE INTO: Terminal). Blocks bound for a browser, 1Password, or any GUI are not fenced at all; see the fencing rules below.

Rules for the routing line:

1. Always present. No paste block ships without it.
2. One line, first thing above the block, easy to spot.
3. Session names stay short, plain, and human: two to four words. The assistant picks the name; Allison names the session exactly as given.
4. Route to an EXISTING session when the work continues a thread that session already holds context for (a pending brief, a prior fix, a repo it already has open). Name the session exactly as Allison named it.
5. Route to a NEW session when the work is a fresh workstream, a different repo, or would pollute an existing session's context.
6. Track known session names as they are created or mentioned, and reuse them consistently so both sides always know where a thread lives. Never invent a session name and register it as if it exists. If Allison reveals the real name, adopt her exact spelling immediately and correct the registry.
7. When it is unknown whether a coinciding session exists, say so on the routing line and default to a new session with a name: PASTE INTO: Claude Code, new session, name it "X" (or your existing session for this work if one is open).
8. Never route two concurrent sessions at the same shared state (the same repo, the same credential, the same config file). One lane per workstream. If a second session is already open on that state, say so and route everything to one of them.

## Window Titles Drift; Session Names Do Not

Added 2026-07-28 after a live incident. A Claude Code window displayed the title "Atlas bot token cleanup" while the session inside it was authoritatively "ember-audit," which it confirmed by its own envelope check. Claude Code cannot read or set its own window title, so the displayed label can drift while the session name stays fixed. Allison nearly archived an active worker because of it.

Consequences:

- The authoritative name is the one in the SESSION line of the block that briefed the session, never the window title.
- When a window title is known to differ, tell Allison the exact name to rename the window to, once, and keep using the authoritative name regardless.
- Never advise archiving or closing a session based on its window title alone. Confirm what work that session still holds first.

## Session Name Goes First Inside The Block

Added 2026-07-28 at Allison's instruction. The first line INSIDE every paste block is the session name, a colon, and a naming instruction, so the pasted prompt identifies its own lane in the transcript and the session ends up named correctly with the least Allison effort.

Live-verified 2026-07-28: Claude Code cannot rename its own session; only Allison can, by typing /rename <name> into that session's input box. So the first line instructs Code to handle naming the lightest correct way. Exact format for the first line inside the fence:

Canon Doc Sync: this is the session name. If this session is not already named "Canon Doc Sync", make your very first output a request that Allison paste /rename Canon Doc Sync into this session's input box, then execute the brief below.

(Substitute the actual session name for each block. The routing line above the fence still ships too. Outside the fence Allison reads where to paste; inside the fence the session learns what it is called.)

## The Hand-Off Choreography: Pin Fires AFTER the Paste Confirmation

Corrected 2026-07-28 after a live miss (the pin was fired alongside the block instead of after Allison's confirmation). This section now matches the operating-doctrine pin rule exactly; if they ever seem to disagree, the operating-doctrine pin rule wins.

The order, every hand-off, every session, every project:

1. The hand-off response carries: the routing line, the paste block, and one plain-prose sentence naming what we will be waiting for once she pastes. It ends by telling Allison to say pasted, done, or OK when she has pasted it. NO pin yet.
2. Allison pastes and confirms (pasted, done, OK, or similar).
3. ONLY THEN the pin fires: the pin marker (pin skill format, fresh real timestamp from TZ=America/Chicago date "+%Y-%m-%d %H:%M %Z", never guessed or reused) plus one sentence restating what we are waiting for and what happens next.

The pin is the bookmark of the moment the baton actually left her hands, which is why it cannot exist before her confirmation.

Precedence notes so the rules do not fight each other:

- The pin marker is a bookmark, not a paste block. It does NOT count against the one-block-per-response rule, and it is exempt from the nothing-fenced-but-Code rule. It is the only other thing that may ever be fenced.
- The pin skill's rule that the marker is the entire response applies only when Allison manually invokes /pin. Confirmation-triggered pins may ride in a response that also continues other work.

## One Block Per Response

Added 2026-07-27 at Allison's instruction: "I can't have you giving me two at a time."

Exactly one paste block per response. Never two, never a "then once that lands" second block, never a block plus a queued follow-up block. (The pin marker is a bookmark, not a block, and does not count.)

If the work needs several steps, ship step one only, wait for the result, then ship step two. Sequencing dependencies are the assistant's job to hold, not Allison's job to keep straight while scrolling.

Prose describing what comes later is fine and brief. A second fenced paste block is not.

## What May Never Go Inside A Code Fence

Added 2026-07-27 after a live failure: a connector URL was placed in a code fence and Allison pasted it into a terminal, where zsh threw "no such file or directory."

In this workflow a code fence carries one meaning to Allison: paste this into Claude Code or a terminal. The only exception is the pin marker defined above. Nothing else may be fenced.

Never fence:

- URLs meant for a browser (connector endpoints, dashboards, sign-in links, docs)
- Values meant to be typed into a settings field or a web form
- Anything destined for 1Password, claude.ai settings, an admin panel, or any GUI

Write those inline in prose with the destination named first, for example: add it in claude.ai, Settings, Connectors, Add custom connector, using mcp.firecrawl.dev/v2/mcp-oauth

Fence only what a terminal or a Claude Code session will actually consume, plus the pin marker. If it is not going into a shell or a Code session and it is not a pin, it does not get a fence.

## Reading Versions From The Right Place

Added 2026-07-27 after a live failure: a doctrine version bump was specified as v2.1 based on a plugin cache mirror reading v2.0, when canonical was already at v2.2 and the correct bump was v2.3.

Never state or prescribe a version number from a plugin cache, a loaded skill copy, or any mirror. Those lag canonical. Read canonical in the repo, or have Claude Code read it and report back. If only a mirror was read, say which copy was read and that it may lag.

Known session names (update this list via skill overwrite as new ones appear):

- "Ember audit": the Ember estate audit and rebuild lane, running Claude Code locally on the M2 Mac mini (Ember's Mac mini, Embers-Mac-mini.local, Mac14,12 Apple M2 Pro, login account allison). Authoritative session name is ember-audit even when the window title has drifted. Created 2026-07-28. Holds the Ember source capture that closed ADR 0031 (commit eebd88a99, 65 previously unversioned production files), the Telegram rotation to bot @Ember_HQBot 8234710582, the Slack rotation on app A0AG008U1V5, the ADR 0029 correction (OpenCLAW is NOT decommissioned; gateway 2026.5.12 runs alongside Claude Agent SDK 0.2.87 and serves Ember's Slack surface), the credential blast-radius reduction across ember_agent.py and gateway.env, and the 1Password-versus-production reconciliation. Route all Ember host, rail, credential-reconciliation, and observability work here.
- "Canon Doc Sync": the canonical lane for pushing promoted canon docs and rule changes into the partnersync repo (created 2026-07-28, first promotion commit 25126c3, Doc 00). Canon markdown lives at project-knowledge/ top level in ExpertPartners/partnersync; Doc 00 is project-knowledge/00-How-to-Use-This-Project.md. ALL future canon promotions route here as an existing session. Works together with the canon-sync-protocol skill.
- "n8n Notion Wiring": the Layer 2 build lane on the partnersync-automation-backend repo (registered 2026-07-28 from Allison's carry-back). Holds the certified error logger PS-ErrorLog-Notify-v1 (live, version 6754f1de, renaming to CORE-Error-Logger-Notify-v1), the S6-Instant gated draft PS-S6Instant-EPICActive-v1 (ARlSztdu5a5DrxqP), the local repo clone at ~/Claude/projects/partnersync-automation-backend/, and the open gates (instance-wide error-workflow designation APPROVED ON by Allison 2026-07-28, fires next session; EP location PIT plus Google Sheets OAuth for S6 certification). Route all n8n workflow build and certification work here.
- "Email Setup Handoff": the email deliverability workstream (sender config, DNS fixes, EPIC and Expert Partners email setup). Also referred to earlier as the Legacy500 Pivot to GHL Kickoff thread.
- "Firecrawl onboarding": the live Firecrawl and doctrine session on the aura repo. Holds the key rotation record (rotated 2026-07-27 to the fc-344c3 prefix key), the headersHelper fix routing op through /bin/zsh -c, the config backups, the two-lane doctrine (Claude Code uses the Bearer lane, OAuth is the CoWork and app lane), the operating-doctrine State Check amendment shipped as v2.3, and the credential-helper class audit. This is the single lane for all Firecrawl and doctrine work.
- "Firecrawl MCP OAuth": a second Firecrawl session opened 2026-07-27, read-only and idle. Superseded by "Firecrawl onboarding" and should be closed rather than reused, since its context predates the doctrine edits.

Archived lanes, do not route to these:

- "Credential Rotation" and its Cowork conversation: archived by Allison 2026-07-28 after she completed all rotations herself. Its output files survive on disk at ~/Claude/projects/PartnerSync Operations Engineer/2026-07-28-github-repo-audit-secret-scan.md and 2026-07-28-session-summary-github-audit-and-credential-consolidation.md. Credential reconciliation ownership moved to "Ember audit."

