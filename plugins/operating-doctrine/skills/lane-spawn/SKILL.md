---
name: lane-spawn
description: "Detour hand-off protocol for Allison. Fires when side work should move out of the current thread. Ships the minimum context and, when needed, a Code worker brief carrying its WORKTREE and MODEL AND EFFORT lines, then returns to the main thread. A block whose substantive destination is wrong (repository, execution host, capability, production or credential boundary, or an actual scope collision) is refused."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
defers-to:
  - code-block-routing
  - pin
brand-scope: null
subtitle: "spawning new lanes with durable homes"
---

# Lane Spawn

<!-- RULED-BY: aura/decisions/0107-retire-routing-naming-ceremony.md date:2026-10-12 superseded naming text removed -->

Ruled by Allison 2026-08-03 (Aura: Strategic Advisor / Repo Walk). The problem this kills: a detour surfaces mid-lane, gets half-absorbed into the wrong conversation, derails the thread, and its state lives nowhere. The fix: every detour gets its own lane at the moment it appears, the origin lane names what it is waiting on, and the origin thread continues without a beat.

v1.1 (ruled by Allison 2026-08-03, after a live misroute): every paste bound for ANY surface carries its envelope. See "Every paste carries the envelope" below.

v1.3 (ruled by Allison 2026-08-07 afternoon, the worktree dispatch ruling; ruling of record aura intake/2026-08-07-ruling-dispatch-blocks-must-name-worktrees.md): the Code half of a spawn pair carries a `WORKTREE` line naming the isolated worktree the worker session creates and works in, per code-block-routing's Worktree Isolation. A block that spawns a Code session without one is malformed and bounces home.

v1.7 (ruled by Allison 2026-09-01, ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md, source aura issue #200): a finite mission carries its own completion contract, MISSION and DONE WHEN, so it can later prove it is finished from its own durable record instead of waiting for Allison to notice the work is over. The live failure that forced it, 2026-09-01: the Shared History Bridge work's durable records said its mission was accepted complete, and its conversation still behaved like an open work surface and began absorbing adjacent work, because nothing it owned ever stated what finishing looked like.

A detour is any work item that surfaces inside a lane but is not that lane's job per its kickoff. Quick verification reads (a file check, a live probe) are not detours; do those inline. Anything with its own state, its own carry-backs, or its own rulings is a detour and spawns.

## The spawn pair

When a detour fires, one message ships up to three parts, in this order.

PASTE 1 -- LANE KICKOFF (always). A fenced block Allison pastes as the FIRST message of a new conversation. Tell her, outside the block, exactly where: which Claude project and which SURFACE (a chat conversation in the Claude app or Cowork, or a Claude Code session). The block contains, in this order:

- The envelope: `DESTINATION: {Claude project}, {chat conversation | Claude Code session}`.
- The mission contract, two lines, whenever this lane is a finite mission (v1.7): `MISSION:` what this work exists to accomplish, in one sentence, and `DONE WHEN:` the evidence that proves that mission achieved. See "The mission contract" below for what makes a good DONE WHEN and when the two lines are correctly omitted.
- What this lane is: its one job, in two or three sentences.
- Why it exists: what happened in the origin lane that spawned it.
- Standing state it inherits: only the rulings and facts it needs, never the origin lane's whole queue.
- Its only jobs, and an explicit do-not-absorb list naming the origin lane and any adjacent lanes.
- First move: what to do when its first input (usually a Code carry-back) arrives.
- Return path: what short finding, if any, comes back to the origin lane, and that Allison carries it as a paste.

Shape of a chat kickoff, top of block:

```
DESTINATION: Aura: Strategic Advisor, chat conversation (Claude app)
MISSION: Restore the Ember briefing rail so the 8 AM briefing sends on its own.
DONE WHEN: Two consecutive briefings send unattended and land on Allison's phone, verified from delivery logs.

WHAT THIS LANE IS: ...
```

PASTE 2 -- CODE BLOCK (only when a worker session is needed). Per the code-block-routing skill, its `CLAUDE HOME` line names the new lane rather than the origin lane, so the carry-back lands where the work will be ruled. The Code half carries its `WORKTREE` and `MODEL AND EFFORT` lines.

RESUME LINE (always, same message, after the blocks). One line stating what the origin lane awaits from the new lane (or 'nothing, fully detached'), then the origin lane's next step, immediately. The origin lane never closes its turn on the detour.

## The mission contract: MISSION and DONE WHEN

A finite mission exists to accomplish a stated thing. Its durable contract records what that thing is and how anyone will know it happened.

`MISSION:` one sentence naming what this work exists to accomplish. Allison's stated outcome, not the build. "Restore the Ember briefing rail so the 8 AM briefing sends on its own," never "edit the launchd plist."

`DONE WHEN:` the acceptance evidence that proves the mission achieved. It must be something a later reader can check without asking Allison, so it names artifacts, merges, live behavior, or delivery proof. "Two consecutive briefings send unattended and land on Allison's phone, verified from delivery logs" is a DONE WHEN. "The rail works" is not, because nothing can be checked against it. When the honest completion condition is Allison's own acceptance of a deliverable, say that exactly, naming the deliverable she accepts, so the check has one real thing to look for.

Which work carries it, and which correctly does not. Record it for a finite mission with a stated outcome, whether it dispatches workers or not. A general-purpose conversation carries neither line and is exempt: it is thinking, reading, exploring, or keeping Allison company on a subject, and it is never nagged to archive merely because a topic ended. A standing subject that exists to be there rather than to finish is exempt the same way and says so plainly in place of a DONE WHEN, so the exemption is a recorded fact rather than a missing line. Absence of the contract is never treated as unfinished work.

What reads it. The session-wrap terminality check reads this contract when acceptance evidence lands and decides whether the mission is achieved. Durable work state proves completion from its own record, so Allison never has to be the one who notices the work is over.

What it is not. It is not a plan, a scope, a task list, or a success metric, and it never grows as the work goes. A mission that genuinely changed is Allison's ruling to make, and completed work never rewrites its own DONE WHEN to keep itself alive (session-wrap v1.11, section 4B).

**The execution half.** A temporary execution session works in an approved implementation engine and returns evidence to its durable origin. Admission is governed by exact execution scope: concurrent work proceeds when scopes do not conflict and an actual mutable-scope collision is refused. Worktree, model and effort, repository/host, credential and production boundaries, and terminal lifecycle requirements remain enforced.

## Every paste carries the envelope (v1.1)

A misroute in live use (2026-08-03) proved that a paste with no destination strands the work. So the rule extends beyond Code blocks: EVERY paste handed to Allison that is bound for another lane or session, kickoffs, directives, carry-notes, everything, opens with lines that name its destination. The pastes are the nervous system; unlabeled pastes are how lanes fall off.

## Landing on the wrong execution surface

Chat conversations and execution surfaces can look alike mid-flow. Inspect the task's actual destination and capability requirements.

Refuse only when substantive evidence proves the task belongs elsewhere: wrong repository, wrong execution host, incompatible destination capability, production or credential boundary, destructive-action gate, or an actual execution-scope collision. State that concrete mismatch and the correct destination.

## Ordering when Allison asks mid-detour

If a Code block already shipped before the new lane existed (the detour escalated), the kickoff block ships next, homed correctly, and it must point at the already-running Code session so the carry-back address is unambiguous. Fix the home at the first opportunity; never let a worker session carry back to a lane that does not exist.

## Rules

- Never absorb a true detour into the current work when it has become an independent body of work; either handle a tiny in-scope verification inline or hand off the independent job.
- Keep the handoff minimal and return to the origin thread.
- A substantive wrong destination such as the wrong repo, production target, or execution host is refused.
- A new Code worker carries its WORKTREE and MODEL AND EFFORT lines.
- Actual execution-scope collisions are refused.
- A finite mission carries MISSION and DONE WHEN as task context.
