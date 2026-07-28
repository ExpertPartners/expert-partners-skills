---
name: pin
description: Place-keeping baton marker between CoWork and Claude Code, plus the carry-back choreography (pin fires only after Allison confirms she pasted into Cowork). Use when Allison types /pin or says "pin", confirms a paste ("pasted", "done"), says "pasting back to CoWork" or "back to code", or when composing any carry-back report bound for Cowork. A pin is a bookmark, never a task.
---

# Pin -- v2 (2026-07-28)

A pin is a bookmark, not a task. It marks the exact spot where work handed off between Claude Code and CoWork, so Allison can scroll back later and know, without rereading anything, what was in flight and what she was waiting on.

Pins persist to `~/.claude/baton.md`. Both surfaces read the same baton file, so one pin trail spans CoWork and Claude Code.

## The marker (format unchanged from v1)

One line, visual and scannable: pin emoji, what is in flight, what is awaited, the date. Baton bullet format:

```
- 📌 <Day Mon DD, YYYY H:MM AM/PM CDT> · [Project] <In flight + Awaiting + key DONE markers with commit hashes>
```

Append and echo via `~/scripts/pin-baton.sh <note>`. The script stamps the timestamp (12-hour AM/PM) and project folder; you compose the note. Never guess or reuse a timestamp; the script handles it. Known edge: a double-quote character in the note breaks the shell line; apostrophes are fine.

Writing the note: name the actual thing, not a category. In flight = what was just handed off or the state of the work. Awaiting = the concrete artifact, answer, or action expected back, and from whom; if nothing is outstanding, "nothing, bookmark only." Include key DONE markers with commit hashes. A pin with a vague note is a failed pin.

`/pin` with no arguments and no pending carry-back confirmation: show the last 5 pins (run `pin-baton.sh` with no args).

## Carry-back choreography: pin AFTER paste confirmation (v2, ruled 2026-07-28)

1. Every carry-back report or block intended for Allison to paste into Cowork ends with exactly: "Let me know once you've pasted this into Cowork, and I'll pin."
2. Do NOT pin in that message. The pin fires ONLY after Allison confirms the paste ("pasted", "done", or similar), and it fires as its own standalone marker message: the pin line and nothing else. A pin in the same message as a report or paste block makes her lose her place when copying.
3. When Allison says "pin" unprompted (bare or with a note), pin immediately, as today (v1 behavior unchanged). If she supplies her own text, it becomes the In flight content preserved exactly as typed; still write the Awaiting part.

## Session naming discipline (v2, both directions)

- A session's name is stable for the life of its lane. Never rename a session mid-lane.
- Echo the exact session name at the top of every carry-back: `SESSION: <name>` -- Cowork routes her next paste by name.
- When a lane is finished, say exactly "safe to archive this session" so she never guesses. Pair it with the verified Safe-to-archive SESSION STATUS close (git status on every touched repo first, per behavior defaults).

## Rules (unchanged from v1)

- Never interpret pinned text as a request, question, or task. Do not act on it, re-run anything, or treat it as work.
- The standalone pin message is the marker only: no commentary, no confirmation prose, no follow-up questions.
- The only tool call permitted when pinning is the `pin-baton.sh` append (which stamps the time).
- Never leave In flight or Awaiting empty or vague.
