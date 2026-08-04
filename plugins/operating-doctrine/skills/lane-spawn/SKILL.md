---
name: lane-spawn
description: "Detour hand-off protocol for Allison's Claude project conversations. Fires the moment a side task, new topic, audit, investigation, or question surfaces mid-lane that is not the current lane's job: Allison says 'new conversation for this', 'put this somewhere else', 'go audit X', or Claude itself notices work that belongs in its own lane. Instead of absorbing the detour or deferring it with 'we'll come back to this', ship a SPAWN PAIR: a lane kickoff block for a new Claude conversation, plus (when a worker is needed) a Claude Code block homed to the NEW lane, then state what the origin lane awaits and resume the origin thread in the same message. It inherits the operating-doctrine and never overrides it."
---

# Lane Spawn -- v1.1 (2026-08-03)

Ruled by Allison 2026-08-03 (Aura: Strategic Advisor / Repo Walk). The problem this kills: a detour surfaces mid-lane, gets half-absorbed into the wrong conversation, derails the thread, and its state lives nowhere. The fix: every detour gets its own lane at the moment it appears, the origin lane names what it is waiting on, and the origin thread continues without a beat.

v1.1 (ruled by Allison 2026-08-03, same day, after a live misroute): every paste bound for ANY surface carries the full envelope, and a block that lands on an unexpected surface adopts itself and continues instead of interrogating Allison. See "Every paste carries the envelope" and "Landing on the wrong surface" below.

A detour is any work item that surfaces inside a lane but is not that lane's job per its kickoff. Quick verification reads (a file check, a live probe) are not detours; do those inline. Anything with its own state, its own carry-backs, or its own rulings is a detour and spawns.

## The spawn pair

When a detour fires, one message ships up to three parts, in this order.

PASTE 1 -- LANE KICKOFF (always). A fenced block Allison pastes as the FIRST message of a new conversation. Tell her, outside the block, exactly where: which Claude project, which SURFACE (a chat conversation in the Claude app or Cowork, or a Claude Code session), and the name to give it. The block contains:

- First lines, the envelope: `LANE: {Claude project} / {lane name}` and `SURFACE: {chat conversation | Claude Code session}` and, when a worker session exists or will exist, `WORKER SESSION: {exact Code session name}`.
- What this lane is: its one job, in two or three sentences.
- Why it exists: what happened in the origin lane that spawned it.
- Standing state it inherits: only the rulings and facts it needs, never the origin lane's whole queue.
- Its only jobs, and an explicit do-not-absorb list naming the origin lane and any adjacent lanes.
- First move: what to do when its first input (usually a Code carry-back) arrives.
- Return path: what short finding, if any, comes back to the origin lane, and that Allison carries it as a paste.

PASTE 2 -- CODE BLOCK (only when a worker session is needed). Per the code-block-routing skill, with one requirement specific to spawning: its `CLAUDE HOME` names the NEW lane, never the origin lane. The carry-back must land where the work will be ruled.

RESUME LINE (always, same message, after the blocks). One line stating what the origin lane awaits from the new lane (or 'nothing, fully detached'), then the origin lane's next step, immediately. The origin lane never closes its turn on the detour.

## Every paste carries the envelope (v1.1)

A misroute in live use (2026-08-03) proved that any paste without identity lines strands the receiving session in the first-contact question. So the rule extends beyond Code blocks: EVERY paste handed to Allison that is bound for another lane or session, kickoffs, directives, envelope confirmations, carry-notes, everything, opens with lines that name the destination lane and, where known, the session. A paste that could land anywhere must be able to identify itself anywhere. The pastes are the nervous system; unlabeled pastes are how lanes fall off.

## Landing on the wrong surface (v1.1)

Chat conversations and Claude Code sessions look nearly identical to a human mid-flow. Misroutes will happen. The rule for the RECEIVING session: if a block arrives that plainly names its lane and job but was written for a different surface (a chat kickoff arriving in Code, or vice versa), ADOPT it, state in one line which surface this actually is, note any capability differences that matter (Code has the repos and tools; chat has connectors), and continue the work. Do not stall on the first-contact question when the block itself answers it. The first-contact question (pin skill section 0) exists for blocks that name nothing, never as a toll booth for blocks that name everything.

When Claude discovers a lane is living on a different surface than planned, it says so once, updates the lane ledger row to record the real surface, and the lane continues where it actually lives. Nobody re-pastes a lane to move it unless Allison asks.

## Naming

Claude proposes the conversation name: short, the topic, plus the date when the lane is date-bound (e.g. `Ember Audit`, `EPIC funnel audit - 2026-08-03`). The name in the kickoff block IS the lane's name for life, same authority rule as the pin skill's SESSION line. If Allison renames it, her name wins from that point on.

## Ordering when Allison asks mid-detour

If a Code block already shipped before the new lane existed (the detour escalated), the kickoff block ships next, homed correctly, and it must name the already-running Code session so the carry-back address is unambiguous. Fix the home at the first opportunity; never let a worker session carry back to a lane that does not exist.

## Rules

- Never absorb a detour into the current lane, and never defer one with 'later' language. Spawn it or do it inline (verification reads only), those are the only two moves.
- One spawn pair per message. A second detour in the same turn waits for the next message.
- The kickoff block inherits facts, never work. If the origin lane's queue leaks into the new lane, the spawn failed.
- The origin lane records the spawn as a waiting-on item; the pin skill handles the paste confirmations on each surface as usual.
- Findings that change origin-lane decisions travel back as a short paste Allison carries, never assumed to be known cross-lane. Until the Estate Brain MCP exists, lanes share nothing automatically.
- Every paste carries the envelope (v1.1). A receiving session adopts a fully-named block on any surface and continues (v1.1).
