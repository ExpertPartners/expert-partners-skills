---
name: remember-this
description: "Turns a future obligation into a durable commitment so Allison stops carrying it mentally. Fires on remember this or a clear request to preserve a follow-up, and when an advisor detects an important non-blocking item that would cause drift, rework or lost leverage if forgotten but would hijack the current mission now. Resolves the owning room live, reuses or creates one Chat to Code job with a mechanical RETURN WHEN condition, refuses duplicates, verifies it through job_status, and reports in one short line. Proactive capture is allowed; proactive activation is not. Distinct from saving a decision, pin, intake and arbitrary operational-state changes. Inherits operating-doctrine."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-09-04 (Immediate Pain Controls campaign, issue #15).
# Canonical home is this file. It ships only through the expert-partners
# marketplace plugin. No uploaded, hand-made, or platform-only copy exists.
tier: plugin
zone: brain
status: live
subtitle: "future obligations get a durable home and a wake condition"
---

# Remember This -- v1.1 (2026-10-08)

v1.1 amendment 2026-10-08 (ruling of record aura intake/2026-10-08-ruling-claude-code-location-and-remove-lock-that.md, under decision 0101): the `Lock that` phrase gate is removed. A clear decision is saved as made. Obligation capture is unchanged.

Allison must be able to say `remember this`, or say nothing at all, and trust that the thing does not evaporate. This skill is the mechanism that earns that trust. It does not store anything itself. It routes a future obligation into the durable home that already owns it and attaches the wake condition that brings it back.

Source of record: `expert-partners-skills` issue #15, whose RETURN WHEN fired 2026-08-31.

## What this is, in one line

A future obligation stays in ONE Chat to Code job for the room that owns the work, with a literal `RETURN WHEN:` condition, verified through job_status before anyone says it was saved. Code obligations travel as GitHub issues labeled job. Follow the current HQ Rulebook section Handoffs between AIs for any message to its owner.

## What this is not

These four boundaries are load-bearing. Blurring any of them is the failure this skill exists to prevent.

- **Not a decision save.** A clear decision from Allison is saved as made in the Decision Log, with no phrase required and a readback in the same response cycle. Remembering an obligation is a different act. It never promotes a decision, never ratifies a recommendation, and never turns a candidate into canon. A captured item may say a decision is pending; it may never say a decision is made.
- **Not pin.** Pin is a lightweight bookmark of the current position between surfaces. It is a place-keeper for right now, it expires with the moment, and it is never durable memory.
- **Not intake.** Intake preserves evidence and working knowledge a cold future reader would need. Remember This preserves an ACTION still owed. Knowledge that has no action attached goes to intake, not here.
- **Not arbitrary operational-state control.** Job and board state have their own contracts. A wait already held in its existing Chat to Code job with a named condition and a stale date is already remembered, and duplicating it here is memory spam.

## Trigger one, explicit

Allison says `remember this`, or clearly asks that a follow-up be preserved: "don't let me forget", "come back to this when X", "we need to do this after Y". Run the full flow below. No gate applies; she asked.

## Trigger two, advisor-detected

North or an advisor session may capture an important non-blocking item without being asked. This is the half that removes Allison as the Estate's detection mechanism, and it is also the half that can flood her with junk, so it is gated hard.

Capture proactively only when ALL FIVE are true:

1. **Forgetting it creates real future cost.** Concrete drift, rework, contradiction, lost provenance, or lost leverage. Not "this was interesting".
2. **Pursuing it now would expand or hijack the current mission.** If it is a contained finding that is a natural extension of the open work, finish it now instead (operating-doctrine, clean as you go). This skill is for what genuinely must wait.
3. **A legitimate existing owner resolves live.** Not a guess, not a topic-similarity match. See owner resolution below. No owner, no capture; say so instead.
4. **A sensible RETURN WHEN can be stated.** If no condition can be named that would ever make this ripe, it is not an obligation, it is a wish.
5. **It is more than chatter.** Not a reaction, not brainstorming, not an unsupported hunch, not a restatement of something already captured.

**Proactive capture is allowed. Proactive activation is not.** Capturing an item never authorizes starting the work, opening a side discussion, spawning a lane, or re-scoping the current mission. The capture is the whole action.

If the five gates do not all clear, say nothing. Silence is the correct output for an item that does not qualify, and a mention of "I considered capturing this" is itself the noise this gate exists to remove.

## The flow, zero freedom

### 1. Resolve the room, live

Never guess a room from topic similarity. Read the HQ Rulebook and the owning brain's `00 START HERE` live to name the room or lane that owns the durable JOB, not the one the conversation happened to be near. If it spans several, pick the one that would have to act first and name the other dependencies in that same job. If nothing can own it, say so and ask where it belongs. Never park it with an unrelated owner just to have somewhere to put it.

### 2. Refuse duplicates before writing

Check job_status for the same obligation. Match on the obligation, not on wording. If a job already carries it, do NOT add a second one. Leave it as it is, or add genuinely new evidence only through a supported nonterminal operation from the live job-tool schema. One obligation, one job, for its whole life.

### 3. Write it durably

Reuse the existing job, or use job_create only when none exists. Inspect the live tool schema; the information below is required job content, not invented parameter names. Preserve its owner, first action and literal `RETURN WHEN:` condition in that same job, through an authorized nonterminal write. Code work is a GitHub issue labeled job. Never write a second Sheet row, and never call job_finish for an obligation that still waits:

```
Obligation: <the thing still owed>
Owner: <the live-resolved room; do not invent a worker claim>
RETURN WHEN: <the mechanical condition that makes this ripe>
Next action: <the first action once ripe, with the short why and capturing session>
Evidence: <the current source or result link>
```

A condition is mechanical when a reader can tell whether it has happened without judgment: a named merge, a named job closing, a named date, a named dependency resolving. "When we have time" is not a condition.

**Never write a secret.** No key, token, password, or credential-bearing material ever enters a job. Secrets live in 1Password only. If the obligation is about a credential, name the 1Password item reference and nothing else.

### 4. Verify before claiming

Read the same job through job_status and confirm its owner, open state and literal `RETURN WHEN` text are actually present. Only a successful read-back earns the receipt. A write call that returned without error is not proof; the read is.

### 5. Report, tiny

After a verified explicit capture, one short line naming what was captured and where. After a verified proactive capture, exactly this shape and nothing more:

```
Captured for later: <item>. Keep going.
```

Do not explain the routing. Do not open a side discussion. Do not ask whether she wants to talk about it. If she asks, answer then.

## Failure honesty

If the durable write cannot be made or cannot be verified, **never say it was remembered.** Chat is not a memory store, and a false receipt is worse than no capture because she will stop carrying it herself.

Say plainly, in the same turn: what the obligation is, verbatim, so it is at least on screen; that the durable write failed and the actual error; and the smallest recovery, with the existing job identity and complete capture text ready for the authorized owner. If a required nonterminal write is unavailable, name that blocker rather than inventing a tool. Never substitute a note in conversation and call it done. Never quietly downgrade to a board card the obligation does not belong in.

## Waking

A captured obligation resurfaces two ways, both already existing, neither a new watcher:

1. **On room wake.** When work in the owning room wakes, check job_status for its existing open obligations whose `RETURN WHEN` condition has fired (operating-doctrine, bias-to-action).
2. **On the named condition.** When the named merge, lane close, date, or dependency actually lands, record the firing evidence in that same job through a schema-supported nonterminal write. The authorized receiver uses job_claim before execution, and job_finish with a summary and result link only after completion. Capture alone never activates work.

No daemon, no sweeper, no cron, no queue, no dashboard, no second registry. If a wake mechanism does not already exist for a room, that is a finding to report, never a reason to build one here.

## Never

- Never capture without a live-resolved room.
- Never create a second durable entry for an obligation that already has one.
- Never route to a room that does not own the work to have a destination.
- Never promote a captured item into canon. A decision is saved only when Allison clearly decides it, under decision 0101, never because this skill captured something.
- Never write a secret into a job.
- Never claim a capture that was not read back.
- Never turn a capture into a side quest, a lane, or a re-scope of the open mission.
- Never use em dashes in anything this skill writes.

## Canonical home and deployed copies

This skill practices the Repo rules on itself (no hand-edited copies). The canonical home is `expert-partners-skills plugins/operating-doctrine/skills/remember-this/SKILL.md`, and it reaches every surface only through the GitHub skills marketplace. Per the HQ Rulebook and the Decision Log entry "No skill exceptions" (2026-10-19), there is no uploaded, hand-made, or platform-only copy, and the old aura deployed copy and its Codex mirror are retired. Fixes flow through this source and the marketplace, never through a copy.
