---
name: estate-memory-router
description: "The thin classifier that decides where a newly learned thing belongs, so Allison is never the Estate's detection mechanism for what deserves to survive. Sweeps at four moments that already happen -- a meaningful topic change, immediately before a dispatch, after a carry-back is accepted, and at session or table wrap -- and routes each durable candidate into a mechanism that already exists: future obligation to remember-this, evidence and working knowledge to the owning brain in Drive, founder decisions Allison has clearly made saved as made under decision 0101 and anything not yet clearly decided preserved as a candidate, deterministic operational state only where a contract already authorizes the write, repo-ownership questions to repo-standards, canon and rule changes to canon-sync-protocol. Resolves owners live, refuses duplicates, writes no secrets, and stays silent when nothing qualifies. It creates NO new memory store and NO new control plane. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-09-04 (Immediate Pain Controls campaign, issue #16).
# Canonical home is this file. It ships only through the expert-partners
# marketplace plugin. No uploaded, hand-made, or platform-only copy exists.
tier: plugin
zone: routing
status: live
subtitle: "one classifier, six existing destinations, no new store"
---

# Estate Memory Router -- v1.1 (2026-10-08)

v1.1 amendment 2026-10-08 (ruling of record aura intake/2026-10-08-ruling-claude-code-location-and-remove-lock-that.md, under decision 0101): the `Lock that` phrase gate is removed. A clear decision is saved as made. Candidates, the no-new-store rule, and every other route are unchanged.

The Estate already has strong downstream memory mechanisms. What it lacked was anything that decides, continuously and without being asked, which mechanism should receive a thing that was just learned. That decision was landing on Allison. This skill takes it off her.

Source of record: `expert-partners-skills` issue #16.

## The one rule that governs everything below

**This skill creates no new system of record and no new control plane.** It owns no store, no registry, no queue, no database, no dashboard, no daemon, no cron, no watcher, no second copy of anything. Its entire job is classification plus routing into mechanisms that already exist and already have owners. If a route's destination mechanism does not exist, the correct output is to say so, never to invent one here.

It also never opens routing-state, registrar, or Table-registry writes. Those remain closed under decision 0080 Section 24 and decision 0082's bridge clause, and nothing in this skill touches them.

## When it sweeps

Four moments, all of which already happen. The sweep is a behavior performed at an existing moment, never a background process.

1. **A meaningful topic change.** The conversation genuinely moves to a different subject, not merely a new message. What was just settled is the material at risk.
2. **Immediately before a dispatch.** Anything the receiving worker or table will need, and would otherwise have to rediscover cold, is captured before the block ships.
3. **After a carry-back is accepted.** The moment a report is read and its claims taken as good, its durable content is at risk of living only in that turn.
4. **At session or table wrap.** The final sweep, made mandatory in `session-wrap` step 3A so a wrap cannot complete while a qualifying item is uncaptured.

## The gate, before any route

Nothing is routed until it passes. An item qualifies only when a cold future worker would need it, or forgetting it would cause drift, rework, contradiction, or lost provenance.

Reject, always, and say nothing about the rejection:

- transient chatter, reactions, and thinking out loud
- ordinary brainstorming that produced no settled outcome
- anything already durably captured (duplicates)
- unsupported speculation, and predictions with no evidence behind them
- anything trivially rederivable from code, git history, or a doc that already exists
- **secrets and credential-bearing material, categorically.** Keys, tokens, passwords, and credentials never enter any destination this skill writes to. They live in 1Password only. Route the reference, never the value.

**If nothing qualifies, say nothing.** Silence is the correct and most common output. Announcing that a sweep ran and found nothing is itself the memory spam this gate exists to prevent.

## The six routes

Classify into exactly one. When an item genuinely has two natures, route each part to its own destination and say so in one line; never send the same content to two homes.

### 1. Future obligation -> `remember-this`

An action still owed, that must wait. Hand it to the `remember-this` skill, which resolves the room live and writes one Job Tracker row with a mechanical `RETURN WHEN` line in Waiting on. That skill owns the whole mechanism, including its advisor-detected gate and its duplicate refusal. This router does not restate it and does not write the row itself.

### 2. Evidence or working knowledge -> owning brain

Something a cold future worker would need in order to act without redoing the discovery: what was found, what was verified live and how, what was ruled out and why, the shape of a system as it actually is. File it as a Google Doc in the owning brain's home folder in Drive through the `intake` skill.

Knowledge with no action attached goes here, never to `remember-this`. That distinction is the one this router gets asked to make most often, and getting it backwards fills the obligation channel with reading material.

### 3. Founder decision or candidate durable truth -> preserved as a candidate, never promoted

Something Allison decided, leaned toward, or that reads like it should become durable truth. Preserve it as evidence in the correct existing mechanism, marked plainly as a candidate, with what was said and when.

**A clear decision is saved as made, with no phrase required** (decision 0101, which supersedes the exact-phrase gates of decisions 0060 and 0061). Allison's clear instruction, or her unambiguous confirmation of one specific proposal, is enough: route it to the Decision Log and complete the write and readback in the same response cycle. A recommendation, brainstorm, ambiguous yes, quoted text, or question is not a decision, and this router never promotes on its own recommendation or invents her approval. Preserve those as candidates. When the intended decision or its owning home is genuinely unresolved, that is one focused question for Allison under Decide Now, asked in the live conversation.

### 4. Deterministic operational state -> only where a contract already authorizes the write

Job Tracker rows, work state, and board state are machinery with their own contracts and their own guards. Write only when an existing contract explicitly authorizes that mechanical write, and then only through that contract's guarded path, never by full-file replacement. The Job Tracker is written through the Google Sheets connector, one row at a time.

Archive authority is unchanged: a worker never writes `archived` into its own row, and the home conversation owns the flip. If no contract authorizes the write, this is not a memory item, it is a request for a permission this router does not have, and it is reported rather than performed.

### 5. Repo ownership or a proposed repo -> existing repo first, then `repo-standards`

Any hint that a thing needs a home, a new provider appeared, a new Project was created, or a subject seems to want its own repo. **Existing repo first, always.** A new provider, Project, integration, or topic is never by itself a reason for a new repo. Resolve live against the HQ Rulebook and the live org, including archived repos, which are revival candidates rather than absences.

If, after that, no existing repo can cleanly own the durable job, hand it to the `repo-standards` creation gate, which proves that formally and returns USE EXISTING REPO or NEW REPO JUSTIFIED. This router never creates a repo and never proposes one directly.

### 6. Canon or rule change -> `canon-sync-protocol`

A canon doc, doctrine rule, operating rule, project rule, or rule-encoding skill was created, changed, approved, or promoted. Fire `canon-sync-protocol` immediately, in the same response, without being asked. That skill owns the surface list and the two routes; this router only notices and hands off. Noticing is the trigger.

## Owner resolution, live, every time

Before any durable write, resolve the owner from live state, never from topic similarity and never from memory of what repos exist. the HQ Rulebook, a Drive search of the owning brain, the `intake` skill's project map, and `gh api orgs/ExpertPartners/repos` when the candidate set is unclear. Name the owner in the receipt so a wrong route is visible immediately and cheap to correct.

## Receipts and failure honesty

After a verified capture, keep the interruption tiny:

```
Captured: <item> -> <owner>. Keep going.
```

One line. No routing explanation, no side discussion, no question.

If a destination is unavailable or a write cannot be verified, **never report the item as captured.** Say in the same turn what the item was, verbatim, which destination failed and the actual error, and the smallest recovery. A chat sentence is not a capture, and a false receipt is worse than none because it ends the founder's own carrying of it.

## Never

- Never create a new memory store, registry, queue, dashboard, watcher, or control plane.
- Never open a routing-state, registrar, or Table-registry write.
- Never promote a candidate into canon on your own say-so. A candidate becomes a decision only when Allison clearly decides it, and it is then saved under decision 0101.
- Never guess an owner from topic similarity.
- Never create a repo, or propose one outside the `repo-standards` gate.
- Never write a secret or credential-bearing material to any destination.
- Never write the same content to two homes.
- Never capture trivia, duplicates, or speculation, and never announce a sweep that found nothing.
- Never activate captured work. Proactive capture is allowed; proactive activation is not.
- Never use em dashes in anything this skill writes.

## Canonical home and deployed copies

This skill practices the Repo rules on itself (no hand-edited copies). The canonical home is `expert-partners-skills plugins/operating-doctrine/skills/estate-memory-router/SKILL.md`, and it reaches every surface only through the GitHub skills marketplace. Per the HQ Rulebook and the Decision Log entry "No skill exceptions" (2026-10-19), there is no uploaded, hand-made, or platform-only copy, and the old aura deployed copy and its Codex mirror are retired. An AI that cannot install from the marketplace works from the HQ Rulebook, Decision Log, and its plan in Drive. Fixes flow through this source and the marketplace, never through a copy.
