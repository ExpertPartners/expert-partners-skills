---
name: canon-sync-protocol
description: "Fires every time a canon doc, doctrine rule, operating rule, Claude project rule, or rule-encoding skill is created, changed or promoted, even if nobody says sync. The AI syncs it without being asked. The rule lives in one Drive home (the HQ Rulebook or the owning brain), the decision goes in the Decision Log with a Replaces note, and skills reach every surface only through the marketplace plugin, never by zip. Inherits operating-doctrine."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Adopted into canonical 2026-08-07 (Aura - Code Rule Fix - Both Shelves Rule lane).
# Ruling of record: history in GitHub Archive (2f70ea0).
# Before this adoption the skill existed ONLY as a claude.ai user-scope copy with no repo home,
# so no Code session could maintain it. That copy is a DEPLOYED COPY of this source from now on.
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
subtitle: "canon and rule changes reach every surface, automatically"
---

# Canon Sync Protocol, v3.0 (2026-11-08)

Any time a canon doc or a rule changes anywhere, the sync happens automatically and the AI does it. Allison never has to ask or remember. Canon has one home, Google Drive. Skills reach every surface only through the marketplace plugin, never by zip.

## When this fires

- A canon doc or rule in the HQ Rulebook or a business brain is drafted, amended or promoted.
- A doctrine rule, operating rule or project instruction changes in any Claude project.
- A skill that encodes a rule is created or overwritten.
- Any copy of canon is out of sync with another.

## Route by what changed

A rule or canon doc takes surfaces 1 through 3. A rule-encoding skill takes surface 4. A rule in a doc and a skill goes both routes in the same pass.

## The surfaces

1. The one Drive home. The rule lives in its owning doc, an HQ Rulebook section or the owning brain. Write it through the Docs connector, one home, never a copy. Link it by file name.
2. The Decision Log. When Allison decided it, add an entry at the top under today's date with what was decided, a sentence of why, and a Replaces note.
3. Claude projects, ChatGPT and Grok read Drive through their connectors, so nothing is pushed. A static upload gets removed and replaced.
4. Skills, through the marketplace only. The source is `expert-partners-skills`, under `plugins/<plugin>/skills/<skill>`. Change it by pull request, add one changeset note (`.changeset/<issue number>-<slug>.md`, format in `.changeset/README.md`), and merge when checks pass. Never hand-edit a version or CHANGELOG. After the merge the release workflow bumps the version. Deliver in Claude Code with `claude plugin marketplace update expert-partners` and `claude plugin update <plugin>@expert-partners`. Never a zip, never an Organization library upload.

## Canonical home and deployed copies

The canonical home is `plugins/operating-doctrine/skills/canon-sync-protocol/SKILL.md`. `tools/skill-deploy/deploy-skill.sh` is the sole producer of deployed copies. Fix canonical source, not deployed copies.

## Never

- Never keep a second copy of a rule.
- Never route a rule-encoding skill change through the doc surfaces alone.
- Never hand Allison a zip to upload.
