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
# Disclosure: canon-sync-protocol v1.2 proposes to supersede the v1.1 skill route (unmerged)

SESSION: Skill Lifecycle - Reconciliation Audit
CLAUDE HOME: NORTH'S ESTATE CONTROL TOWER / Skill Lifecycle

This disclosure accompanies a PROPOSED amendment to `skills/canon-sync-protocol/SKILL.md`
on the isolated branch `claude/canon-sync-protocol-v1-2-proposal-20260930`, split out of the
mixed PR 39 on 2026-09-30. Nothing here is a ruling. The amendment becomes canon only when Allison rules it with Lock That under aura
decisions 0060 and 0061. NORTH reviews and recommends. A merge alone never rules it. Until
then the v1.1 text it would supersede remains the operative minimum.

## What would be superseded

The v1.1 skill route (ruling of record aura intake/2026-08-08-ruling-canon-sync-protocol-repo-home-and-shelf-surfaces.md, commit 2f70ea0) says a rule-encoding skill has its canonical source in expert-partners-skills and mounts on one or both of two shelves.

## What would replace it, and why

1. Canonical sources sit in two repos. The skills graph on expert-partners-skills main
   lists 41 sources in this repo and 16 `aura:` sources (9 live, 1 retired, 6 designed
   and not yet canonical). The graph already carried those 16 `aura:` sources when v1.1
   was committed (59a07d0, graph at that commit: 33 eps, 16 aura), so v1.1 omitted a
   canonical home that existed at the time.
2. Five clients read thirteen distinct surface keys. Claude Code reads its personal and
   project mounts, its plugin cache, the claude.ai org plugins and the account Skills
   shelf. Codex reads its user and repo mounts, its plugin caches and a synced mirror that
   Codex Desktop's external-agent import writes. Claude Chat and Cowork share the account Skills shelf and the org plugins, but
   each client keeps its own copy, so an install proven for one client is not proof for
   another. ChatGPT/NORTH loads its own uploads. v1.1 named none of the clients, so a
   delivery proven on one was taken as proof for the rest. Evidence: aura
   intake/2026-09-24-skill-lifecycle-reconciliation/.
3. Complete means receipted. No mechanism defined release completion. The audit found
   stale, duplicate and shadowed copies loading on every local client as a result. The
   amendment names `deploy-skill.sh --receipt` as the check that decides completion.

## What is not changed

The canon-doc route (surfaces 1 through 4), the trigger list, the Team GPT pause, the
Both Shelves mechanics in code-block-routing, and the 2026-08-07 GitHub-sync ruling all
stand. The amendment adds surface keys and a completion check. It removes none. It names
the retirement of standalone uploads of plugin-carried skills as the proposed disposition
under the 2026-08-07 ruling, which still needs Allison's per-item approval.

## Status as of 2026-09-30

NORTH ruled on 2026-09-30 that this amendment is not adopted, merged, deployed or
promoted. NORTH's recommendation is to adopt it, and that recommendation is not
Allison's ruling. Under aura decisions 0060 and 0061 only Allison can make it canon, and
until she does the v1.1 text stays operative. This pull request stays open, draft and
unmerged. Nothing else changes its status.

The Codex synced-mirror row of the surface table was corrected on 2026-09-30 under a
factual correction NORTH authorized. The mirror is written by Codex Desktop's
external-agent import sync, which as observed is additive and copies what is missing
rather than reliably updating or deleting. The row keeps saying it is never a release
target.

The tooling this amendment cites, `deploy-skill.sh --audit-surfaces`, `--receipt` and
`--receipt-template`, ships in the separate hardening pull request, so that one should
merge first if this amendment is ever adopted. The AGENTS.md wording that called the
receipt check the definition of release completion is in neither pull request until then.
