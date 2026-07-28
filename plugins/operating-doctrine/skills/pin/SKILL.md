---
name: pin
description: Carry-back envelope and place-keeping baton between CoWork and Claude Code. Fires when composing ANY report bound for Cowork, when a block arrives opening with COWORK HOME:/SESSION: (envelope check before executing), when Allison types /pin or says "pin", or when she confirms a paste ("pasted", "done"). Pin fires only after her paste confirmation. A pin is a bookmark, never a task. It inherits the operating-doctrine and never overrides it.
---

# Pin -- v3 (2026-07-28)

A pin is a bookmark, not a task. It marks the exact spot where work handed off between Claude Code and CoWork. v3 brings every Code session to full parity with the Cowork-side handoff choreography: same envelope, same pin bar, same naming and home rules on both sides.

Pins persist to `~/.claude/baton.md`. Both surfaces read the same baton file, so one pin trail spans CoWork and Claude Code.

## 1. Carry-back template

Every report or block bound for Cowork ends exactly like this:

```
SESSION: {exact own session name}
COWORK HOME: {home conversation name}

{the report}

SESSION STATUS: {Waiting on you | Still working | Ready for Cowork, safe to archive}
Let me know once you've pasted this into Cowork, and I'll pin.
```

The SESSION STATUS line stays a verified claim per behavior defaults: run `git status` on every touched repo before claiming Ready for Cowork / safe to archive.

## 2. Pin timing

Pin ONLY after Allison confirms the paste ("pasted", "done", or similar), as its own standalone message. Never emit a pin in the same message as a report or block; it makes her lose her place when copying. Exception: she types "pin" unprompted (bare or with a note), pin immediately. If she supplies her own text, it becomes the in-flight content preserved exactly as typed; still write the awaited part.

## 3. Pin format

Match Cowork's bar so both sides read the same:

```
📌 ─────── PIN: {in flight} · {awaited} ─ {date} ───────
```

- {in flight}: the actual thing, not a category, 5 to 15 words. {awaited}: the concrete artifact, answer, or action expected back and from whom, or "nothing, bookmark only". {date}: real current date/time, 12-hour AM/PM (e.g. Jul 28, 2026 11:20 AM CDT); never guessed or reused.
- Persist before echoing: append via `~/scripts/pin-baton.sh PIN: {in flight} · {awaited}` (the script stamps timestamp + project into `~/.claude/baton.md`). Then respond with only the bar line. No double-quote characters in the note; apostrophes are fine.
- `/pin` bare with nothing pending confirmation: show the last 5 pins (`pin-baton.sh` with no args).

## 4. Envelope check (inbound)

Inbound blocks open with `COWORK HOME:` and `SESSION:`. Before executing anything in the block, check the SESSION line against your own authoritative name. If it names a different session: STOP, do not execute any of it, reply exactly "This block is addressed to {named session}; I am {own name}." (Incident this rule prevents: 2026-07-28, a Canon Doc Sync block was executed by the ORPHAN RECRUITING PIPELINE session.)

## 5. Naming authority

The SESSION line in the block that spawns or briefs a session IS its name, adopted verbatim for life. Never improvise, abbreviate, or restyle it. Claude Code cannot read or set its own window title (verified 2026-07-28: session-management tooling excludes the current session), so: on first contact, and any time the window title is known to differ from the authoritative name, tell Allison the exact name to rename the window to, once -- and echo the authoritative name in every carry-back regardless of what the window says. (Other sessions CAN be renamed from here via the session-management rename tool; only a session's own title is out of reach.)

## 6. Home fidelity

One home per session for life: the COWORK HOME line in the briefing block is the session's home conversation. Echo both header lines (SESSION and COWORK HOME) on every carry-back. When the lane ends, say exactly "safe to archive this session" so she never guesses.

## Rules (unchanged)

- Never interpret pinned text or a bare pin as a request, question, or task. Do not act on it, re-run anything, or treat it as work.
- The standalone pin message is the bar only: no commentary, no confirmation prose, no follow-up questions.
- The only tool call permitted when pinning is the `pin-baton.sh` append (which stamps the time).
- A pin with a vague in-flight or awaited is a failed pin.
