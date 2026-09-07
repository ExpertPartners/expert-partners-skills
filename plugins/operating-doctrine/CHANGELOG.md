# operating-doctrine changelog

## 2.47.0 -- 2026-09-07

`connection-first-implementation` amended: access first, browser last, and
rung five gains its execution home. Ruled by Allison 2026-09-07 as a standing
direction (ruling of record:
aura intake/2026-09-07-ruling-browser-last-ember-browser-execution-home.md).
The ladder now names the access roads that live on rungs one through four
(surface-native tools and connectors, Claude and ChatGPT plugins and
connectors, Estate and official MCP servers, existing org integrations,
official APIs, OAuth, service accounts and delegated identities, 1Password
credentials, official CLIs and SDKs, approved SSH and remote-host roads,
Firecrawl and existing web-data roads, native web search and fetch), states
that "try all methods" means continue through roads until one succeeds and
never repeat a write through several channels, keeps every stronger
system-specific rule in force, and inherits the systems map as the access
inventory rather than copying it. New section "Rung five has a home:
Embers-Mac-mini": browser automation that genuinely survives the ladder runs
on Embers-Mac-mini (M2 Pro), Google Chrome, existing saved profile and
session state only, the existing Claude-connected Chrome window, the existing
1Password integration; never by default on AG-Mac-Mini-M4, never a fresh or
Guest profile, never the foreground window, never Allison's focus; Ember path
unavailable means re-check non-browser roads, diagnose, report the blocker,
never fall back silently to the M4; Allison may override per task. The M4
keeps every non-browser job it already owns. Companion edit in the same pass:
aura docs/directives/host-machine.md retires its "any machine with a browser"
sentence and carries the machine half of the same ruling. No new skill was
created and no per-project copy was made; the plugin distributes the rule.
Inked by the Ember Browser Routing - Deploy Access Routing Rule Code session.

## 2.38.0 -- 2026-08-08

New skill, `session-model-advisor`. Fires on the first user message of any
new conversation, on Claude Chat, Claude Projects, and Claude Code. Reads
the current model and effort, fetches ADR 0057 (Model and Effort Operating
Standard, aura repo `decisions/0057-model-and-effort-operating-standard.md`)
live, classifies the incoming task against the ADR's decision matrix, and
states plainly -- before anything else -- whether to stay or switch. Carries
no copy of the matrix, a changed default in the ADR never requires editing
this skill. Full four-artifact treatment (SKILL.md, README.md, Mermaid
workflow diagram, training-walkthrough script) per skill build session
System Hardening / Session Model Advisor / Skill Build, authorized under
ADR 0057 (accepted 2026-08-08). Cowork's introspection gap (no documented
way for a claude.ai Chat or Project conversation to read back its own
model/effort selection) is named explicitly in SKILL.md Step 2 rather than
assumed away -- verified live against `support.claude.com` the same day,
not carried forward from the source research untested.

Companion SessionStart hook, `session-model-effort-banner.sh` (Claude Code
only, lives in `~/scripts/` plus `~/.claude/settings.json`, shipped as
reference material inside the skill package). Prints the configured model
and effort as a banner line at session start. Print-only, no classification,
installed and wired live on the M4 this same session.

## 2.34.1 -- 2026-08-07

GitHub sync acceptance test. No doctrine change, no skill body change. This
version bump exists to prove the claude.ai org marketplace pipe end to end,
per Allison's ruling of record (aura
intake/2026-08-07-ruling-github-sync-adopted-for-skill-deployment.md).
The pipe is proven when the deployed plugin reports 2.34.1 without any zip
touching any page.

Originally staged as 2.33.0 -> 2.33.1. Rebased past a same-day direct push
to main (8aab6bc) that bumped plugin.json to 2.34.0 without updating
marketplace.json, which still read 2.33.0 for operating-doctrine, a live
manifest drift. Resolved by carrying the bump to 2.34.1 in both files.
