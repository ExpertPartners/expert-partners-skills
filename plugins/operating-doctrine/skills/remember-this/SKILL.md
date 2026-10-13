---
name: remember-this
description: "Turns a future obligation into a durable, self-resurfacing commitment so Allison stops carrying it mentally. Fires when she says remember this or clearly asks to preserve a follow-up, and fires on its own when an advisor notices an important non-blocking item that would cost real drift, rework, or lost leverage if forgotten but would hijack the current mission if pursued now. Resolves the owning room LIVE, writes ONE Job Tracker row with a mechanical RETURN WHEN condition in Waiting on, refuses duplicates, verifies the write before claiming it, and reports in one short line. Proactive capture is allowed; proactive activation is not. Distinct from saving a decision (decision 0101: a clear decision is saved as made in its owning repo), from pin (a lightweight current-position bookmark), from intake (evidence and working knowledge), and from operational state. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-09-04 (Immediate Pain Controls campaign, issue #15).
# Canonical home is this file. It is homed under skills/ and carried by no plugin,
# so it owes exactly one shelf, the claude.ai organization Skills upload, plus the
# aura deployed copy and that copy's Codex mirror.
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

A future obligation gets ONE Job Tracker row for the room that owns the work, with a literal `RETURN WHEN:` line in Waiting on, verified to exist before anyone says it was saved.

## What this is not

These four boundaries are load-bearing. Blurring any of them is the failure this skill exists to prevent.

- **Not a decision save.** A clear decision from Allison is saved as made in the Decision Log, with no phrase required and a readback in the same response cycle. Remembering an obligation is a different act. It never promotes a decision, never ratifies a recommendation, and never turns a candidate into canon. A captured item may say a decision is pending; it may never say a decision is made.
- **Not pin.** Pin is a lightweight bookmark of the current position between surfaces. It is a place-keeper for right now, it expires with the moment, and it is never durable memory.
- **Not intake.** Intake preserves evidence and working knowledge a cold future reader would need. Remember This preserves an ACTION still owed. Knowledge that has no action attached goes to intake, not here.
- **Not operational state.** Job Tracker rows, board cards, and work-state records are deterministic machinery with their own contracts. A wait that already has a home in the Job Tracker's Waiting on column with a named condition and a stale date is already remembered, and duplicating it here is memory spam.

## Trigger one, explicit

Allison says `remember this`, or clearly asks that a follow-up be preserved: "don't let me forget", "come back to this when X", "we need to do this after Y". Run the full flow below. No gate applies; she asked.

## Trigger two, advisor-detected

NORTH or Aura may capture an important non-blocking item without being asked. This is the half that removes Allison as the Estate's detection mechanism, and it is also the half that can flood her with junk, so it is gated hard.

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

Never guess a room from topic similarity. Read the HQ Rulebook and the owning brain's `00 START HERE` live to name the room or lane that owns the durable JOB, not the one the conversation happened to be near. If it spans several, pick the one that would have to act first and name the others in Next step. If nothing can own it, say so and ask where it belongs. Never park it in a row that does not own the work just to have somewhere to put it.

### 2. Refuse duplicates before writing

Read the Job Tracker values and look for the same obligation. Match on the obligation, not on wording. If a row already carries it, do NOT add a second one. Leave it as it is, or, when this moment genuinely adds new evidence, add that evidence to its Next step and say so. One obligation, one row, for its whole life.

### 3. Write it durably

Add ONE row to the Job Tracker (Google Sheet `1FniEwCaZ89cViQxUcPkycxAmvvM47cnjRzQQyzpEk5c`) through the Sheets connector. The come-back condition is written in Waiting on, as a literal `RETURN WHEN:` line, because the wake token is mechanical and a prose paraphrase does not fire:

```
Job: <the obligation, stated as the thing still owed>
Room or lane: <the owning room>
Who is doing it: Nobody yet
Status: Not started
Waiting on: RETURN WHEN: <the mechanical condition that makes this ripe>
Next step: <the first action once ripe, with the short why and the capturing session>
Opened / Last updated: <today>
```

A condition is mechanical when a reader can tell whether it has happened without judgment: a named merge, a named job closing, a named date, a named dependency resolving. "When we have time" is not a condition.

**Never write a secret.** No key, token, password, or credential-bearing material ever enters a row. Secrets live in 1Password only. If the obligation is about a credential, name the 1Password item reference and nothing else.

### 4. Verify before claiming

Re-read the sheet after writing and confirm the row and its `RETURN WHEN` text are actually present. Only a successful read-back earns the receipt. A write call that returned without error is not proof; the read is.

### 5. Report, tiny

After a verified explicit capture, one short line naming what was captured and where. After a verified proactive capture, exactly this shape and nothing more:

```
Captured for later: <item>. Keep going.
```

Do not explain the routing. Do not open a side discussion. Do not ask whether she wants to talk about it. If she asks, answer then.

## Failure honesty

If the durable write cannot be made or cannot be verified, **never say it was remembered.** Chat is not a memory store, and a false receipt is worse than no capture because she will stop carrying it herself.

Say plainly, in the same turn: what the obligation is, verbatim, so it is at least on screen; that the durable write failed and the actual error; and the smallest recovery, which is normally the exact row ready to be added once access works. Never substitute a note in conversation and call it done. Never quietly downgrade to a board card the obligation does not belong in.

## Waking

A captured obligation resurfaces two ways, both already existing, neither a new watcher:

1. **On room wake.** When work in the owning room wakes, the Job Tracker is checked for Not started rows whose `RETURN WHEN` condition has fired (operating-doctrine, bias-to-action).
2. **On the named condition.** When the named merge, lane close, date, or dependency actually lands, the surface that sees it land marks Waiting on `FIRED <date>`, and the obligation becomes ordinary ripe work under Decide Now.

No daemon, no sweeper, no cron, no queue, no dashboard, no second registry. If a wake mechanism does not already exist for a room, that is a finding to report, never a reason to build one here.

## Never

- Never capture without a live-resolved room.
- Never create a second durable entry for an obligation that already has one.
- Never route to a room that does not own the work to have a destination.
- Never promote a captured item into canon. A decision is saved only when Allison clearly decides it, under decision 0101, never because this skill captured something.
- Never write a secret into a row.
- Never claim a capture that was not read back.
- Never turn a capture into a side quest, a lane, or a re-scope of the open mission.
- Never use em dashes in anything this skill writes.

## Canonical home and deployed copies

This skill practices ADR 0056 point 8 on itself. The canonical home is `expert-partners-skills skills/remember-this/SKILL.md`. It is homed under `skills/` and carried by no plugin, so it owes exactly one shelf, the claude.ai organization Skills upload, plus the aura deployed copy at `.claude/skills/remember-this/` and that copy's Codex mirror at `.agents/skills/remember-this/`. Deployed copies carry the DEPLOYED COPY header naming the canonical home, a version stamp, and a SHA-256 checksum manifest. `tools/skill-deploy/deploy-skill.sh` is the sole producer of deployed copies and upload zips. Hand-editing a deployed copy is a violation; fixes flow through canonical source and redeploy.
