# operating-doctrine changelog

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
