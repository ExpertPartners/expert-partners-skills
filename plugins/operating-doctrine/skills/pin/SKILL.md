---
name: pin
description: "Carry-back envelope and place-keeping baton between Allison's Claude project conversations (Claude app, CoWork) and Claude Code. Fires at first contact in a new Code session (ask for the Claude project and conversation before running a briefing that does not name them), when composing ANY report bound back to a Claude project, when a block arrives opening with CLAUDE HOME or COWORK HOME / SESSION header lines (envelope check before executing), when Allison types /pin or says \"pin\", or when she confirms a paste (\"pasted\", \"done\"). Pin fires only after her paste confirmation. A pin is a bookmark, never a task. It inherits the operating-doctrine and never overrides it."
---

# Pin -- v4.2 (2026-08-03)

A pin is a bookmark, not a task. It marks the exact spot where work handed off between Claude Code and the Claude project conversation that drives it. v4 (ruled by Allison 2026-08-03) makes the protocol surface-neutral: the home is a Claude PROJECT plus CONVERSATION, never assumed to be CoWork. v4 also adds the first-contact question and the "come back here" pin close. v4.1 (ruled by Allison 2026-08-03, same day) rewrites the carry-back SESSION STATUS line: it names the paste-back PROJECT and CONVERSATION explicitly, the ARCHIVE verdict is part of the line, and a session that is NOT clean to archive must give the instructions at that point instead of the ARCHIVE sentence. v4.2 (ruled by Allison 2026-08-03, same day) DELETES the closing line ("Let me know once you've pasted this back into ..., and I'll pin."): the carry-back ends at the SESSION STATUS line and never solicits a paste confirmation.

Pins persist to `~/.claude/baton.md`. Every surface reads the same baton file, so one pin trail spans all of them.

## 0. First contact in a new Code session (v4, ruled 2026-08-03)

Assume every briefing block arriving in a fresh Claude Code session came from a Claude conversation Allison is having. Before running the block, the session must know its home: the Claude project name AND the conversation name. If the block does not name both (CLAUDE HOME line, or legacy COWORK HOME, or Allison stating them), ask FIRST, before executing anything:

"What is the name of the Claude project and conversation this came from?"

Do not run the briefing until she answers. One question, nothing stacked with it.

## 1. Carry-back template

Every report or block bound back to a Claude project ends exactly like this:

```
SESSION: {exact own session name}
CLAUDE HOME: {Claude project name} / {conversation name}

{the report}

SESSION STATUS: Ready to paste back to PROJECT: {Claude project name} in CONVERSATION NAME: {conversation name}. This session is ready to ARCHIVE.
```

The SESSION STATUS line is the last line of the carry-back. There is no closing "Let me know once you've pasted... and I'll pin" line (deleted in v4.2); the carry-back never solicits a paste confirmation. Never write "into Cowork" anywhere in the carry-back. Always name the actual Claude project and conversation; if the session somehow reached a carry-back without knowing them, ask (section 0) before sending the report.

### The ARCHIVE verdict is verified, or it is replaced with instructions (v4.1)

"This session is ready to ARCHIVE" is a verified claim, never a sign-off phrase. Before writing it, run `git status` on every repo the session touched and confirm all three: nothing uncommitted, nothing unpushed, no open follow-ups parked in this session.

If ANY check fails -- or the report is not a final carry-back (work still running, or something is waiting on Allison) -- do NOT write the ARCHIVE sentence. Keep the paste-back half of the line and replace the ARCHIVE half with the instructions at that point, in the same position:

```
SESSION STATUS: Ready to paste back to PROJECT: {Claude project name} in CONVERSATION NAME: {conversation name}. Do NOT archive this session yet -- {exactly what blocks it: the uncommitted files, the unpushed commits, or the open item} -- {the exact next instruction: the one action Allison takes, or what this session does next}. Keep this session open.
```

The instructions are specific, never generic: name the files, the repo, the commit, or the awaited item, and name the single next action. The lane ledger row (aura `docs/estate/lanes.md`) mirrors the same verdict: a row moves to complete-safe-to-archive only when the ARCHIVE sentence shipped.

## 2. Pin timing and the come-back close (v4)

Pin ONLY after Allison confirms the paste ("pasted", "done", or similar). Exception: she types "pin" unprompted (bare or with a note), pin immediately. The confirmation is always hers to volunteer: since v4.2 the carry-back never asks for it, so if she says nothing, no pin fires and that is correct. If she supplies her own text, it becomes the in-flight content preserved exactly as typed; still write the awaited part.

The pin response is the bar plus exactly one orientation line pointing her back:

```
📌 ─────── PIN: {in flight} · {awaited} ─ {date} ───────
Pinned -- come back here after you {the next thing she does in {Claude project} / {conversation}}.
```

No other commentary, confirmation prose, or questions ride with a pin. Never emit a pin in the same message as a report or block; it makes her lose her place when copying.

Doctrine note (added 2026-08-03): the pin confirms the paste; it is not the lane record. The lane ledger row (aura `docs/estate/lanes.md`) is written at dispatch and updated at carry-back, per the code-block-routing skill. A pin never substitutes for a ledger update, and a ledger update never substitutes for a pin.

## 3. Pin format

- {in flight}: the actual thing, not a category, 5 to 15 words. {awaited}: the concrete artifact, answer, or action expected back and from whom, or "nothing, bookmark only". {date}: real current date/time, 12-hour AM/PM (e.g. Aug 3, 2026 5:20 PM CDT); never guessed or reused.
- Persist before echoing: append via `~/scripts/pin-baton.sh PIN: {in flight} · {awaited}` (the script stamps timestamp + project into `~/.claude/baton.md`). Then respond with the bar plus the come-back line, nothing else. No double-quote characters in the note; apostrophes are fine.
- `/pin` bare with nothing pending confirmation: show the last 5 pins (`pin-baton.sh` with no args).

## 4. Envelope check (inbound)

Inbound blocks open with `CLAUDE HOME:` (or legacy `COWORK HOME:`) and `SESSION:`. Before executing anything in the block, check the SESSION line against your own authoritative name. If it names a different session: STOP, do not execute any of it, reply exactly "This block is addressed to {named session}; I am {own name}." (Incident this rule prevents: 2026-07-28, a Canon Doc Sync block was executed by the ORPHAN RECRUITING PIPELINE session.)

## 5. Naming authority

The SESSION line in the block that spawns or briefs a session IS its name, adopted verbatim for life. Never improvise, abbreviate, or restyle it. Claude Code cannot read or set its own window title (verified 2026-07-28: session-management tooling excludes the current session), so: on first contact, and any time the window title is known to differ from the authoritative name, tell Allison the exact name to rename the window to, once -- and echo the authoritative name in every carry-back regardless of what the window says. (Other sessions CAN be renamed from here via the session-management rename tool; only a session's own title is out of reach.)

## 6. Home fidelity

One home per session for life: the home is the Claude project plus conversation named in the briefing block (CLAUDE HOME line) or by Allison at first contact. Echo both header lines (SESSION and CLAUDE HOME) on every carry-back. If Allison herself corrects or supplies the home mid-lane, adopt her correction verbatim from that point on; nobody else may change it. When the lane ends, say exactly "safe to archive this session" so she never guesses.

## Rules

- Never interpret pinned text or a bare pin as a request, question, or task. Do not act on it, re-run anything, or treat it as work.
- The pin message is the bar plus the one come-back line: no other prose.
- The only tool call permitted when pinning is the `pin-baton.sh` append (which stamps the time).
- A pin with a vague in-flight or awaited is a failed pin.
