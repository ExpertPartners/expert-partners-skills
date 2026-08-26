---
name: lane-spawn
description: "Detour hand-off protocol for Allison's Claude project conversations. Fires the moment a side task, new topic, audit, investigation, or question surfaces mid-lane that is not the current lane's job: Allison says 'new conversation for this', 'put this somewhere else', 'go audit X', or Claude itself notices work that belongs in its own lane. Instead of absorbing the detour or deferring it with 'we'll come back to this', ship a SPAWN PAIR: a lane kickoff block for a new Claude conversation, plus, when a worker is needed, a Claude Code block homed to the NEW lane, then state what the origin lane awaits and resume the origin thread in the same message. A chat kickoff opens with the conversation name as its literal first line, plain and alone, and heads its envelope CONVERSATION, never SESSION. A spawned conversation is a table, named exactly once at Table Birth per decision 0074, and a chat never gets a routine rename instruction. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
defers-to:
  - code-block-routing
  - pin
brand-scope: null
subtitle: "spawning new lanes with named homes"
---

# Lane Spawn -- v1.5 (2026-08-26)

Ruled by Allison 2026-08-03 (Aura: Strategic Advisor / Repo Walk). The problem this kills: a detour surfaces mid-lane, gets half-absorbed into the wrong conversation, derails the thread, and its state lives nowhere. The fix: every detour gets its own lane at the moment it appears, the origin lane names what it is waiting on, and the origin thread continues without a beat.

v1.1 (ruled by Allison 2026-08-03, same day, after a live misroute): every paste bound for ANY surface carries the full envelope, and a block that lands on an unexpected surface adopts itself and continues instead of interrogating Allison. See "Every paste carries the envelope" and "Landing on the wrong surface" below.

v1.2 (ruled by Allison 2026-08-07, same lane as the naming and archive rulings): the chat side of naming. A chat kickoff block now opens with the conversation name as its literal first line, plain and alone, because the app auto-titles a conversation from its first message and nothing can set that title programmatically. The block also heads its envelope with CONVERSATION, never SESSION. See "The conversation name is the first line" and "Vocabulary lock" below. The live failure that forced it: a spawn block buried the conversation name mid-block and led with mission text, so the app titled the chat off the mission and the lane was born with two names.

v1.3 (ruled by Allison 2026-08-07 afternoon, the worktree dispatch ruling; ruling of record aura intake/2026-08-07-ruling-dispatch-blocks-must-name-worktrees.md): the Code half of a spawn pair carries a `WORKTREE` line naming the isolated worktree the worker session creates and works in, per code-block-routing's Worktree Isolation. A block that spawns a Code session without one is malformed and bounces home.

v1.4 (ruled by Allison 2026-08-26, decision of record aura decisions/0074-naming-and-session-steward.md): Table Birth. A spawned conversation is a TABLE, the durable continuity anchor for its work, and it is named exactly once at birth. The kickoff block still leads with the bare name for the auto-titler, and the receiving surface now also DECLARES that name on its first substantive turn as `TABLE NAME: <exact name>`, so the declared name and the visible title are compared once, at birth, and Allison performs at most one manual title rename if they differ. The Code half changes too: the worker is named `<Table Name> - <Specific Job>` and titles ITSELF through the native session-management tool, so no launch line and no rename hand step ride along. One table, one active Code worker. See "Table Birth" and "The worker half" below.

v1.5 (ruled by Allison 2026-08-26, decision of record aura decisions/0077-room-identity-literal.md): ROOM joins Table Birth. The birth declaration is two lines, `ROOM: <exact room identity>` above `TABLE NAME: <exact permanent table name>`. The exact ROOM string comes solely from that room's own Project Instructions ROOM identity literal, never reconstructed from canon prose, ledger rows, intake records, conversation memory, or this skill (skills carry the value, they never own one). The `CONVERSATION:` envelope line's project segment is composed from that same literal. Platform honesty also lands: a chat surface cannot read its own visible title, so the birth declaration states the intended name, says plainly that visible-title parity cannot be verified from that surface, and asks Allison for the one birth-time glance and rename if the visible title differs, never claiming a title was inspected, matched, or fixed when the surface cannot know that. The live failures that forced it, 2026-08-26: a fresh Aura table declared ROOM as Aura Strategic Advisor, dropping the colon from the Project's actual visible name, because canon prose itself carries the colon-less spelling; the same day NORTH's ChatGPT Project auto-titled a table "Recommend Twilio next move" over the declared name "Twilio Account Cleanup" with no birth-time detection.

A detour is any work item that surfaces inside a lane but is not that lane's job per its kickoff. Quick verification reads (a file check, a live probe) are not detours; do those inline. Anything with its own state, its own carry-backs, or its own rulings is a detour and spawns.

## The spawn pair

When a detour fires, one message ships up to three parts, in this order.

PASTE 1 -- LANE KICKOFF (always). A fenced block Allison pastes as the FIRST message of a new conversation. Tell her, outside the block, exactly where: which Claude project, which SURFACE (a chat conversation in the Claude app or Cowork, or a Claude Code session), and the name to give it. The block contains, in this order:

- **First line: the conversation name, plain and alone.** Nothing else on that line, nothing above it. See the next section for why this is first and why it is bare.
- Then the envelope: `CONVERSATION: {Claude project} / {conversation name}` and `SURFACE: {chat conversation | Claude Code session}` and, when a worker session exists or will exist, `WORKER SESSION: {exact Code session name}`.
- What this lane is: its one job, in two or three sentences.
- Why it exists: what happened in the origin lane that spawned it.
- Standing state it inherits: only the rulings and facts it needs, never the origin lane's whole queue.
- Its only jobs, and an explicit do-not-absorb list naming the origin lane and any adjacent lanes.
- First move: what to do when its first input (usually a Code carry-back) arrives.
- Return path: what short finding, if any, comes back to the origin lane, and that Allison carries it as a paste.

Shape of a chat kickoff, top of block:

```
Ember Rail Repair

CONVERSATION: Aura: Strategic Advisor / Ember Rail Repair
SURFACE: chat conversation (Claude app)
WORKER SESSION: Ember Rail Repair - Rail Diagnostic

WHAT THIS LANE IS: ...
```

The name appears twice on purpose. Line one is for the auto-titler, which reads the message and cannot be told anything. The CONVERSATION line is for the receiving Claude, which needs the project as well as the name.

PASTE 2 -- CODE BLOCK (only when a worker session is needed). Per the code-block-routing skill, with one requirement specific to spawning: its `CLAUDE HOME` names the NEW lane, never the origin lane. The carry-back must land where the work will be ruled. The Code half keeps `SESSION NAME`, keeps its first-contact self-title-and-verify instruction, and carries its `WORKTREE` line naming the isolated worktree the worker creates from a freshly fetched remote ref and confirms by absolute path at first contact (v1.3, per code-block-routing's Worktree Isolation); none of the chat rules touch it. Under v1.4 the worker name is `<Table Name> - <Specific Job>` and the worker titles itself on Desktop, so no `claude -n` launch line rides unless the target is a CLI-only launch.

RESUME LINE (always, same message, after the blocks). One line stating what the origin lane awaits from the new lane (or 'nothing, fully detached'), then the origin lane's next step, immediately. The origin lane never closes its turn on the detour.

## The conversation name is the first line (v1.2)

Chat conversation titles cannot be set programmatically. The Claude app and Cowork auto-title a conversation from its first message, and no session, tool, or API can override that (live-verified 2026-08-03, reconfirmed by the 2026-08-07 failure below). The only lever the block-writer has is what the first message says first.

So: **the conversation name is the literal first line of the kickoff block, plain and alone.** No label in front of it, no date suffix, no mission text above it, no envelope line above it. Lead with the name and the auto-titler lands on it or close to it.

The failure this replaces, 2026-08-07: a spawn block buried the conversation name several lines down and opened with mission text instead. The app titled the chat off the mission, and the lane had two names from birth, the one the ledger recorded and the one Allison could see.

**Chat lane identity is the kickoff header line**, per the standing 2026-08-03 ruling; the displayed title is not the mechanism, because it cannot be set programmatically. Leading with the name is what gives the auto-titler the right material.

**Table Birth (v1.4, decision 0074) replaces near-match acceptance for tables.** A spawned conversation is a table, and a table is named exactly once, at birth. Mechanics:

1. The kickoff block leads with the bare name (above), so the auto-titler lands on it or close.
2. On its first substantive turn, the receiving surface DECLARES identity in two lines (v1.5, decision 0077): `ROOM: <exact room identity>` then `TABLE NAME: <exact table name>`. The ROOM string comes solely from the room's own Project Instructions ROOM identity literal.
3. The surface cannot read its own visible title, so it states the intended TABLE NAME, says plainly that visible-title parity cannot be verified from that surface, and asks Allison for the ONE manual table-title rename if the visible title differs. At birth only, and never claiming a title was inspected, matched, or fixed when the surface cannot know that (v1.5, decision 0077).
4. After that the table name is stable for life, and no implementation dispatch leaves an unnamed or unconfirmed table.

What did NOT come back: routine or repeated chat rename requests stay banned, `/rename` is still never handed out for a chat in any form, and chat lanes still never get PARITY MISMATCH flags. Table Birth is a single naming act at the moment a table is created, not a maintenance loop, and it is the only point at which a table title correction is ever raised. If Allison renames a conversation herself at any time, her name wins from that point on and the ledger follows her.

**The worker half (v1.4).** A table may have many sequential Code workers over its life and never two concurrent independent ones. If the detour genuinely needs its own concurrent implementation, it needs its own table first, which is exactly what a spawn pair produces. Worker naming and self-titling live in code-block-routing, Session Naming; classification, drift repair, and the one-table-one-active-worker check live in the session-steward skill.

## Vocabulary lock: CONVERSATION for chats, SESSION for Code (v1.2)

The two surfaces get two words, and they never trade.

- A block bound for a **chat conversation** (Claude app or Cowork) heads its envelope `CONVERSATION:`. A chat block carrying a `SESSION:` line is **malformed**: rewrite it before it ships.
- A block bound for a **Claude Code session** heads its envelope `SESSION:`, per the pin skill and code-block-routing. That is unchanged.
- `WORKER SESSION:` inside a chat kickoff is correct and is not a violation. It names the Code lane the chat will receive carry-backs from; it is a pointer, not the block's own header.
- `CLAUDE HOME:` inside a Code block still names the Claude project plus conversation. That is a pointer too, and it is unchanged.

One word per surface, so a block's destination is legible from its first envelope line even when it lands somewhere unexpected.

## Every paste carries the envelope (v1.1)

A misroute in live use (2026-08-03) proved that any paste without identity lines strands the receiving session in the first-contact question. So the rule extends beyond Code blocks: EVERY paste handed to Allison that is bound for another lane or session, kickoffs, directives, envelope confirmations, carry-notes, everything, opens with lines that name the destination lane and, where known, the session. A paste that could land anywhere must be able to identify itself anywhere. The pastes are the nervous system; unlabeled pastes are how lanes fall off.

Under v1.2 a chat kickoff satisfies this with its first line (the bare conversation name) plus its `CONVERSATION:` line immediately below. The bare name does not replace the envelope; it sits above it.

## Landing on the wrong surface (v1.1)

Chat conversations and Claude Code sessions look nearly identical to a human mid-flow. Misroutes will happen. The rule for the RECEIVING session: if a block arrives that plainly names its lane and job but was written for a different surface (a chat kickoff arriving in Code, or vice versa), ADOPT it, state in one line which surface this actually is, note any capability differences that matter (Code has the repos and tools; chat has connectors), and continue the work. Do not stall on the first-contact question when the block itself answers it. The first-contact question (pin skill section 0) exists for blocks that name nothing, never as a toll booth for blocks that name everything.

Under v1.2 the envelope word is the tell: a block opening `CONVERSATION:` that arrives in Claude Code is a chat kickoff that landed on the wrong surface. Adopt it and say so; do not treat the word as an error in the block.

When Claude discovers a lane is living on a different surface than planned, it says so once, updates the lane ledger row to record the real surface, and the lane continues where it actually lives. Nobody re-pastes a lane to move it unless Allison asks.

## Naming

Claude proposes the conversation name: short, the topic, and readable in a sidebar (e.g. `Ember Audit`, `EPIC Funnel Audit`). Keep it to the words that identify the lane; date suffixes and the word "kickoff" no longer ride on the name itself under v1.2, because the name is now the line the auto-titler reads. When a lane is genuinely date-bound, the date goes in the block body, not in the name.

The name in the kickoff block IS the table's name for life, it is what the receiving surface declares as `TABLE NAME` on its first substantive turn (v1.4), and it is what the lane ledger records. Under Table Birth the visible title is compared to it once, at birth, and Allison performs at most one manual rename if they differ; after that the title is never revisited. If Allison renames the conversation herself at any point, her name wins from that point on.

Worker (Code session) names are a different rule with a different format, `<Table Name> - <Specific Job>`, self-titled at birth through the native session-management tool (decision 0074). See the pin skill, section 5, and code-block-routing, Session Naming. Do not apply the worker format to a table name, and do not put a room prefix on either by default.

## Ordering when Allison asks mid-detour

If a Code block already shipped before the new lane existed (the detour escalated), the kickoff block ships next, homed correctly, and it must name the already-running Code session so the carry-back address is unambiguous. Fix the home at the first opportunity; never let a worker session carry back to a lane that does not exist.

## Rules

- Never absorb a detour into the current lane, and never defer one with 'later' language. Spawn it or do it inline (verification reads only), those are the only two moves.
- One spawn pair per message. A second detour in the same turn waits for the next message.
- The kickoff block inherits facts, never work. If the origin lane's queue leaks into the new lane, the spawn failed.
- The origin lane records the spawn as a waiting-on item; the pin skill handles the paste confirmations on each surface as usual.
- Findings that change origin-lane decisions travel back as a short paste Allison carries, never assumed to be known cross-lane.
- Every paste carries the envelope (v1.1). A receiving session adopts a fully-named block on any surface and continues (v1.1).
- A chat kickoff opens with the bare conversation name; a chat block heads its envelope CONVERSATION, never SESSION; a chat never gets a routine rename instruction (v1.2).
- The Code half of a spawn pair carries its WORKTREE line; a spawning Code block without one is malformed and bounces home (v1.3).
- A table is named exactly once, at birth: declared as ROOM plus TABLE NAME on the first substantive turn (v1.5, decision 0077), with at most one manual title rename by Allison if the visible title is not exact (v1.4). The ROOM string comes solely from the room's own Project Instructions literal, and no surface claims title parity it cannot read (v1.5).
- A table runs many sequential workers and never two concurrent independent ones; the worker names itself `<Table Name> - <Specific Job>` through the native tool (v1.4).
