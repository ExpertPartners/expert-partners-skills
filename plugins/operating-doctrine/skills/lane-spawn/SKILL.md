---
name: lane-spawn
description: "Detour hand-off protocol for Allison's Claude project conversations. Fires the moment a side task, new topic, audit, investigation, or question surfaces mid-lane that is not the current lane's job: Allison says 'new conversation for this', 'put this somewhere else', 'go audit X', or Claude itself notices work that belongs in its own lane. Instead of absorbing the detour or deferring it with 'we'll come back to this', ship a SPAWN PAIR: a lane kickoff block for a new Claude conversation, plus (when a worker is needed) a Claude Code block homed to the NEW lane, then state what the origin lane awaits and resume the origin thread in the same message. A chat kickoff block opens with the conversation name as its literal first line, plain and alone, so the app's auto-titler lands close; chat blocks head their envelope with CONVERSATION and never SESSION, and a chat is never handed a rename instruction. It inherits the operating-doctrine and never overrides it."
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

# Lane Spawn -- v1.2 (2026-08-07)

Ruled by Allison 2026-08-03 (Aura: Strategic Advisor / Repo Walk). The problem this kills: a detour surfaces mid-lane, gets half-absorbed into the wrong conversation, derails the thread, and its state lives nowhere. The fix: every detour gets its own lane at the moment it appears, the origin lane names what it is waiting on, and the origin thread continues without a beat.

v1.1 (ruled by Allison 2026-08-03, same day, after a live misroute): every paste bound for ANY surface carries the full envelope, and a block that lands on an unexpected surface adopts itself and continues instead of interrogating Allison. See "Every paste carries the envelope" and "Landing on the wrong surface" below.

v1.2 (ruled by Allison 2026-08-07, same lane as the naming and archive rulings): the chat side of naming. A chat kickoff block now opens with the conversation name as its literal first line, plain and alone, because the app auto-titles a conversation from its first message and nothing can set that title programmatically. The block also heads its envelope with CONVERSATION, never SESSION. See "The conversation name is the first line" and "Vocabulary lock" below. The live failure that forced it: a spawn block buried the conversation name mid-block and led with mission text, so the app titled the chat off the mission and the lane was born with two names.

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
WORKER SESSION: Aura - Ember Rail Repair - Rail Diagnostic

WHAT THIS LANE IS: ...
```

The name appears twice on purpose. Line one is for the auto-titler, which reads the message and cannot be told anything. The CONVERSATION line is for the receiving Claude, which needs the project as well as the name.

PASTE 2 -- CODE BLOCK (only when a worker session is needed). Per the code-block-routing skill, with one requirement specific to spawning: its `CLAUDE HOME` names the NEW lane, never the origin lane. The carry-back must land where the work will be ruled. The Code half keeps `SESSION`, keeps its `claude -n` launch line, and keeps its first-contact self-verify instruction; none of the v1.2 chat rules touch it.

RESUME LINE (always, same message, after the blocks). One line stating what the origin lane awaits from the new lane (or 'nothing, fully detached'), then the origin lane's next step, immediately. The origin lane never closes its turn on the detour.

## The conversation name is the first line (v1.2)

Chat conversation titles cannot be set programmatically. The Claude app and Cowork auto-title a conversation from its first message, and no session, tool, or API can override that (live-verified 2026-08-03, reconfirmed by the 2026-08-07 failure below). The only lever the block-writer has is what the first message says first.

So: **the conversation name is the literal first line of the kickoff block, plain and alone.** No label in front of it, no date suffix, no mission text above it, no envelope line above it. Lead with the name and the auto-titler lands on it or close to it.

The failure this replaces, 2026-08-07: a spawn block buried the conversation name several lines down and opened with mission text instead. The app titled the chat off the mission, and the lane had two names from birth, the one the ledger recorded and the one Allison could see.

**Near-match titles are accepted, and always were.** Chat lane identity is the kickoff header line, per the standing 2026-08-03 ruling; the displayed title is cosmetic and is never authoritative. Leading with the name is a courtesy to Allison's eyes in the sidebar, not a correctness requirement. A title that reads "Ember Rail Repair Plan" when the lane is "Ember Rail Repair" is fine and is left alone.

**Claude never hands Allison a rename instruction for a chat. Ever.** Not a `/rename`, not a "please retitle this conversation," not a parenthetical suggestion. Manual chat renaming was retired as a failure condition in the 2026-08-03 ruling and this rule does not revive it. Chat lanes never get PARITY MISMATCH flags. If Allison renames a conversation herself, her name wins from that point on and the ledger follows her, same as any correction she makes to a home; she is simply never asked to.

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

The name in the kickoff block IS the lane's name for life, and it is what the lane ledger records. The displayed chat title is cosmetic and may be logged parenthetically when someone needs to find the window, never treated as identity. If Allison renames the conversation herself, her name wins from that point on; Claude never asks her to.

Code session names are a different rule with a different format (`<Project short name> - <Conversation name> - <Job name>`, set at launch via `claude -n`). See the pin skill, section 5. Do not apply the Code format to a chat conversation name.

## Ordering when Allison asks mid-detour

If a Code block already shipped before the new lane existed (the detour escalated), the kickoff block ships next, homed correctly, and it must name the already-running Code session so the carry-back address is unambiguous. Fix the home at the first opportunity; never let a worker session carry back to a lane that does not exist.

## Rules

- Never absorb a detour into the current lane, and never defer one with 'later' language. Spawn it or do it inline (verification reads only), those are the only two moves.
- One spawn pair per message. A second detour in the same turn waits for the next message.
- The kickoff block inherits facts, never work. If the origin lane's queue leaks into the new lane, the spawn failed.
- The origin lane records the spawn as a waiting-on item; the pin skill handles the paste confirmations on each surface as usual.
- Findings that change origin-lane decisions travel back as a short paste Allison carries, never assumed to be known cross-lane.
- Every paste carries the envelope (v1.1). A receiving session adopts a fully-named block on any surface and continues (v1.1).
- A chat kickoff opens with the bare conversation name; a chat block heads its envelope CONVERSATION, never SESSION; a chat never gets a rename instruction (v1.2).
