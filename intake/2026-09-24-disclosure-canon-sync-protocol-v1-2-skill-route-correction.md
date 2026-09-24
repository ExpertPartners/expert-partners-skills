---
classification: internal
classification_owner: allison
classification_date: 2026-09-24
source: Skill Lifecycle - Reconciliation Audit worker (Claude Code, AG-Mac-Mini-M4)
project: expert-partners-skills
captured_at: 2026-09-24T19:30:00Z
record_type: supersession-disclosure
status: proposed-unmerged
---
# Disclosure: canon-sync-protocol v1.2 supersedes the v1.1 skill route (proposed, unmerged)

SESSION: Skill Lifecycle - Reconciliation Audit
CLAUDE HOME: NORTH'S ESTATE CONTROL TOWER / Skill Lifecycle

This disclosure accompanies a PROPOSED amendment to `skills/canon-sync-protocol/SKILL.md`
on the isolated branch `claude/skill-lifecycle-reconciliation-20260924`. Nothing here is
a ruling. The amendment stays unmerged and undeployed until NORTH and Allison rule on it,
and the v1.1 text it supersedes remains the operative minimum meanwhile.

## What is superseded

The v1.1 skill route (ruling of record aura intake/2026-08-08-ruling-canon-sync-protocol-repo-home-and-shelf-surfaces.md, commit 2f70ea0) says a rule-encoding skill has its canonical source in expert-partners-skills and mounts on one or both of two shelves.

## What replaces it, and why

1. Canonical homes are two repos. The skills graph on expert-partners-skills main
   (4b0f5e58) recognises 16 Aura-native canonical skills whose home is aura, beside 41
   homed here. README.md and AGENTS.md on the same main say so. v1.1 was written before
   the graph carried `aura:` sources.
2. Six surfaces, not two shelves. Verified on 2026-09-24: Claude Code mounts and plugin
   cache; Codex mounts and plugin caches; the claude.ai organization plugin marketplace
   (GitHub sync, live at operating-doctrine 2.49.0); the claude.ai account Skills shelf,
   loaded by Claude Chat and by Cowork; ChatGPT/NORTH. v1.1 named neither ChatGPT/NORTH
   nor Codex and treated Chat and Cowork as one shelf. Evidence: aura
   intake/2026-09-24-skill-lifecycle-reconciliation/ (surface-inventory.json,
   reconciliation-matrix.md, lifecycle-gap-analysis.md).
3. Complete means receipted. No mechanism defined release completion; the matrix shows 22
   canonical skills with a stale deployment and 17 with duplicate identities as a result.
   The amendment names `deploy-skill.sh --receipt` as the definition of complete.

## What is not changed

The canon-doc route (surfaces 1 through 4), the trigger list, the Team GPT pause, the
Both Shelves mechanics in code-block-routing, and the 2026-08-07 GitHub-sync ruling all
stand. The amendment adds surfaces and a completion check; it removes none.
