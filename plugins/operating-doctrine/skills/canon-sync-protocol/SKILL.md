---
name: canon-sync-protocol
description: "Fires automatically, every time, the moment a canon doc, doctrine rule, operating rule, Claude project rule, or rule-encoding skill is created, changed, approved, or promoted, even if nobody says sync. Claude initiates the sync without being asked. The rule lives in one Drive home (the HQ Rulebook or the owning brain), the decision goes in the Decision Log with a Replaces note, and skills reach every surface only through the marketplace plugin, never by zip. Noticing is the trigger, never being asked. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Adopted into canonical 2026-08-07 (Aura - Code Rule Fix - Both Shelves Rule lane).
# Ruling of record: aura intake/2026-08-08-ruling-canon-sync-protocol-repo-home-and-shelf-surfaces.md (2f70ea0).
# Before this adoption the skill existed ONLY as a claude.ai user-scope copy with no repo home,
# so no Code session could maintain it. That copy is a DEPLOYED COPY of this source from now on.
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
subtitle: "canon and rule changes reach every surface, automatically"
---

# Canon Sync Protocol -- v2.0 (2026-10-13)

<!-- RULED-BY: aura/decisions/0107-retire-routing-naming-ceremony.md date:2026-10-12 superseded naming text removed -->

Rule authored by Allison, 2026-07-28. Her words: this is the Ten Commandments. Any time a canon doc or a rule changes anywhere, the sync happens automatically, 100 percent of the time, and Claude initiates it. Allison never has to ask, never has to remember, and never discovers a stale copy later.

v2.0 (2026-10-13, Decision Log 2026-10-13, the clean-slate cutover). Canon has one home, Google Drive. The partnersync repo copy, the canon folder id, the Team GPT surface, and the organization skills upload shelf are retired, and this supersedes the surface lists in the v1.1 history below. Skills reach every surface only through the marketplace plugin, no zips, ever.

History, kept as written. v1.1 amendment 2026-08-07, ruled YES by Allison, both halves (ruling of record aura intake/2026-08-08-ruling-canon-sync-protocol-repo-home-and-shelf-surfaces.md, commit 2f70ea0). Half one, this skill gets a canonical home in the expert-partners-skills repo like every other rule-bearing skill, and the claude.ai user-scope copy becomes a deployed copy of it. Half two, the surface list gains the two skill shelves. The gap that forced both halves was found by the Both Shelves Rule lane and is worth stating plainly, because it is the exact failure this protocol exists to prevent: the trigger list below has always fired on a rule-encoding skill being created or overwritten, while the surface list named Drive, project knowledge, the partnersync repo, and the paused Team GPT. Not one of those is a skill shelf. The protocol caught skill changes and routed them nowhere.

## When this fires

The moment ANY of the following happens, this protocol runs, in the same response, without being asked:

- A canon doc or rule in the HQ Rulebook or a business brain is drafted, amended, approved, or promoted
- A doctrine rule, operating rule, or project instruction changes in any Claude project
- A skill that encodes a rule is created or overwritten
- Allison approves a draft that touches any of the above
- Claude notices any copy of canon is out of sync with another, even in passing

Noticing is the trigger. If a change qualifies, the checklist below starts immediately.

## Route by what changed

- **A rule or canon doc** takes surfaces 1 through 3.
- **A rule-encoding skill** takes surface 4.

A rule that lives in a doc AND in a skill travels both routes in the same pass.

## The surfaces, in order

1. **The one Drive home.** The rule lives in its owning doc, an HQ Rulebook section or the owning brain's folder. One home, point to it, never copy it. Claude writes it through the Docs connector (the service account if the connector refuses), reads it back, and gives Allison the Doc as a hyperlink whose text is the file name.

2. **The Decision Log.** When Allison decided it, add an entry at the top under today's date: what was decided, why in a sentence or two, and a Replaces note naming the older decision it supersedes, or none.

3. **Claude projects, ChatGPT and Grok.** They read Drive through their own connectors, so nothing is pushed. Check how a Claude project holds the doc: a Drive sync badge means nothing to do, and a static upload gets removed and replaced. Drive files can be pinned only into private Claude projects.

4. **Skills, through the marketplace only.** The canonical source is `expert-partners-skills`, under `plugins/<plugin>/skills/<skill>`. Change it by pull request, which Allison merges. Bump the version in BOTH `plugins/<plugin>/.claude-plugin/plugin.json` AND the repo-root `.claude-plugin/marketplace.json`, and add the CHANGELOG line. Deliver in Claude Code with `claude plugin marketplace update expert-partners` and `claude plugin update <plugin>@expert-partners`. Cowork and Claude chat sync from the organization marketplace, so confirm the synced version shows the new number. Never a zip, never an Organization library upload, never a Desktop file. A skill uploaded by hand to the Organization library never updates, so when one is found, move it into a plugin.

## Sequencing and tracking

- One tiny step at a time, per Allison's delivery protocol. Claude holds the sequence; Allison only ever sees the current step.
- Claude keeps a live checklist of the surfaces for every doc or skill in flight and states plainly which are done and which are open. No canon or rule change is reported as finished while any active surface is stale.
- If a session ends mid-sync, preserve the open surfaces, owner, named condition and stale date in the existing Chat to Code job, verified with job_status. Keep the job nonterminal; job_finish is for completed work, not a paused session. Route any return under the current HQ Rulebook section Handoffs between AIs.

## Canonical home and deployed copies

This skill practices ADR 0056 point 8 on itself. The canonical home is `expert-partners-skills plugins/operating-doctrine/skills/canon-sync-protocol/SKILL.md`. Any user-level deployed copy carries the DEPLOYED COPY header naming that home, a version stamp, and a SHA-256 checksum manifest. `tools/skill-deploy/deploy-skill.sh` is the sole producer of deployed copies. Hand-editing a deployed copy is a violation; fixes flow through canonical source.

## Never

- Never let Allison discover a stale copy. Claude surfaces the gap first.
- Never mark a canon or rule change complete with any active surface unsynced.
- Never produce a canon draft without this protocol attached to its approval.
- Never keep a second copy of a rule. One Drive home, everything else points to it.
- Never route a rule-encoding skill change through the doc surfaces alone.
- Never hand Allison a zip to upload. Skills reach claude.ai through the marketplace.
