---
name: pin
description: "Carry-back envelope and place-keeping baton between Allison's Claude project conversations (Claude app, CoWork) and Claude Code. Fires when composing ANY report bound back to a Claude project, when a block arrives with return-routing metadata, when Allison types /pin or says \"pin\", and when she confirms a paste (\"pasted\", \"done\"). Pin fires only after her paste confirmation. A pin is a bookmark, never a task. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
defers-to:
  - code-block-routing
brand-scope: null
subtitle: "carry-back envelope and place-keeping baton"
---

# Pin

<!-- RULED-BY: aura/decisions/0107-retire-routing-naming-ceremony.md date:2026-10-12 superseded naming text removed -->

A pin is a bookmark, not a task. It marks the exact spot where work handed off between Claude Code and the Claude project conversation that drives it. v4 (ruled by Allison 2026-08-03) makes the protocol surface-neutral: the home is a Claude PROJECT plus CONVERSATION, never assumed to be CoWork, and adds the "come back here" pin close. v4.2 (ruled by Allison 2026-08-03) deletes the closing line that solicited a paste confirmation. v4.5 (re-ruled by Allison 2026-08-07 evening) has the session give its own archive verdict. v4.6 (ruled by Allison 2026-08-07, ruling of record aura intake/2026-08-07-ruling-dispatch-blocks-must-name-worktrees.md) adds the WORKTREE line to spawning blocks. v4.7 (ruled by Allison 2026-08-07, Aura / Code Rule Fix lane) adds the earned verdict line.

Pins persist to `~/.claude/baton.md`. Every surface reads the same baton file, so one pin trail spans all of them.

## 1. Carry-back template

Every report or block bound back to a Claude project ends exactly like this:

```
CLAUDE HOME: {Claude project name} / {conversation name}

{the report}

SESSION STATUS: {the standing status line, section below}
VERDICT: {RECOMMEND ARCHIVE -- all pushed, nothing pending on Allison's side | RECOMMEND HOLD OPEN, waiting on <the one named thing>}
```

The VERDICT line is the last line of the carry-back, directly after the SESSION STATUS line (v4.7). There is no closing "Let me know once you've pasted... and I'll pin" line (deleted in v4.2); the carry-back never solicits a paste confirmation. Never write "into Cowork" anywhere in the carry-back. Name the Claude project and conversation the report returns to, from the CLAUDE HOME line or durable dispatch state; ask once only if nothing names it.

### The session gives the archive verdict (v4.5, re-ruled by Allison 2026-08-07 evening)

<!-- RULED-BY: aura/intake/2026-08-07-ruling-archive-verdict-returns-to-code-sessions.md date:2026-08-07 -->
<!-- Restores and generalizes a rule Allison first ruled 2026-08-03 for this skill (pin v4.1), struck without disclosure 2026-08-07 morning, and re-ruled the same afternoon: aura/intake/2026-08-03-ruling-pin-v41-carry-back-names-verified-archive-verdict.md date:2026-08-03 status:superseded-and-restored -->

This SUPERSEDES the v4.3 no-verdict addendum and retires `SESSION STATUS: carry-back delivered, awaiting verification at home.` permanently; that line is never written again. Allison's reason, recorded: the session must tell her whether it is okay to archive, determine whether something is open, and say whether a closeout or a wrap is needed, because sessions that cannot say whether they are done pile up, and too many open sessions is the real failure.

A carry-back ends with exactly one of the four SESSION STATUS lines from `behavior-defaults.md`:

- `SESSION STATUS: Waiting on you -- [exact action].`
- `SESSION STATUS: Still working -- [what remains]. Keep this session open.`
- `SESSION STATUS: SAFE TO ARCHIVE -- [evidence in one line].`
- `SESSION STATUS: NOT safe to archive -- [what is open]; run [/session-wrap | /session-closeout | the named action].`

SAFE TO ARCHIVE is a verified claim, never a phrase. It is issued only after all three verify live in the same turn: `git status` clean and pushed on every repo the session touched; the session record, wrap, or closeout note written and pushed when doctrine requires one; and every open wait re-lodged in the lane ledger's waiting-on column with its named condition and stale date, so nothing dies with the archive. The evidence goes in the line itself.

NOT safe means the session diagnoses AND prescribes: it names exactly what is open and the single move that closes it, /session-wrap when chat-only decisions or flags are unrecorded, /session-closeout when shipped work has no handoff note on main, or the named open action otherwise. Never leave Allison to work out which.

What stays with the home conversation: the ledger flip. The archive itself is the session's own, since a finished code session wraps and archives itself without waiting for Allison (session-wrap section 5A, Decision Log 2026-10-24, Finished code sessions wrap and archive themselves), and the Steward sweeps any that cannot. Home flips the lane's row to `archived` in the Job Tracker as one motion with that archive, and no dispatch block is ever written against a row reading `archived`. Sessions born before v4.5 follow the lifecycle rule from their next response.

### The earned verdict line (v4.7, ruled by Allison 2026-08-07, Aura / Code Rule Fix lane)

<!-- RULED-BY: aura/intake/2026-08-07-ruling-earned-verdict-line-on-carry-backs.md date:2026-08-07 -->

Amends v4.5; does not replace it. The standing SESSION STATUS line stays, and every carry-back adds exactly one earned VERDICT line after it, the carry-back's true last line:

- `VERDICT: RECOMMEND ARCHIVE -- all pushed, nothing pending on Allison's side.` Permitted ONLY when the session verifies its checklist live in the same turn: every commit pushed, the whole brief executed, nothing gated or held open, no deliverable still owed. A bare safe-to-archive with no checklist behind it stays banned.
- `VERDICT: RECOMMEND HOLD OPEN, waiting on <the one named thing>.` Every other state earns this one. One named thing, never a list.

Archive authority, as of Decision Log 2026-10-24, Finished code sessions wrap and archive themselves, is the finished code session's own: it archives itself and Allison is never the gate. Home's GitHub grading remains the backstop, and Allison may still archive on the spot on a RECOMMEND ARCHIVE. Sessions born before v4.7 follow it from their next carry-back.

## 2. Pin timing and the come-back close (v4)

Pin ONLY after Allison confirms the paste ("pasted", "done", or similar). Exception: she types "pin" unprompted (bare or with a note), pin immediately. The confirmation is always hers to volunteer: since v4.2 the carry-back never asks for it, so if she says nothing, no pin fires and that is correct. If she supplies her own text, it becomes the in-flight content preserved exactly as typed; still write the awaited part.

The pin response is the bar plus exactly one orientation line pointing her back:

```
📌 ─────── PIN: {in flight} · {awaited} ─ {date} ───────
Pinned -- come back here after you {the next thing she does in {Claude project} / {conversation}}.
```

No other commentary, confirmation prose, or questions ride with a pin. Never emit a pin in the same message as a report or block; it makes her lose her place when copying.

Doctrine note (added 2026-08-03): the pin confirms the paste; it is not the lane record. The Job Tracker row (which replaced the aura lane ledger) is written at dispatch and updated at carry-back, per the code-block-routing skill. A pin never substitutes for a ledger update, and a ledger update never substitutes for a pin.

## 3. Pin format

- {in flight}: the actual thing, not a category, 5 to 15 words. {awaited}: the concrete artifact, answer, or action expected back and from whom, or "nothing, bookmark only". {date}: real current date/time, 12-hour AM/PM (e.g. Aug 3, 2026 5:20 PM CDT); never guessed or reused.
- Persist before echoing: append via `~/scripts/pin-baton.sh PIN: {in flight} · {awaited}` (the script stamps timestamp + project into `~/.claude/baton.md`). Then respond with the bar plus the come-back line, nothing else. No double-quote characters in the note; apostrophes are fine.
- `/pin` bare with nothing pending confirmation: show the last 5 pins (`pin-baton.sh` with no args).

## 4. Envelope check (inbound)

Inspect an inbound block against substantive execution state: repository, worktree/branch, exact mutable scope, execution host, production boundary, credential boundary, destination capability, and return location. A block addressed to a different repository, worktree, host, production target, credential context, or a conflicting mutable scope stops; say in one line what it is for and where it belongs. If the task genuinely requires a capability unavailable on the receiving surface, state that mismatch and route it to the correct surface.

### A spawning block also carries its WORKTREE line (v4.6)

A block that spawns a NEW Code session carries a `WORKTREE` line in its envelope, naming the isolated worktree the session creates and works in. The session creates that worktree from a freshly fetched remote ref before any other work and confirms the ABSOLUTE path in its first report. No work happens in the shared main tree. A spawning block arriving without one is malformed and bounces home, same as a block missing its routing line: do not execute it, reply naming what is missing so the dispatcher reships the block whole. Continuation blocks to an existing session inherit its established worktree and need not restate it. Full mechanics: code-block-routing, Worktree Isolation.

## 5. Home fidelity

Keep one stable return destination for the session, from the CLAUDE HOME line or durable dispatch state. Echo the CLAUDE HOME line on every carry-back. If Allison corrects or supplies the return destination mid-lane, adopt her correction from that point on.

When the lane ends, the session pronounces on archiving with evidence (v4.5, re-ruled 2026-08-07 evening; amended v4.7 same day): it ends at the SESSION STATUS line plus the earned VERDICT line per section 1, RECOMMEND ARCHIVE earned by the verified checklist or RECOMMEND HOLD OPEN naming the one wait.

## Rules

- Never interpret pinned text or a bare pin as a request, question, or task. Do not act on it, re-run anything, or treat it as work.
- The pin message is the bar plus the one come-back line: no other prose.
- The only tool call permitted when pinning is the `pin-baton.sh` append (which stamps the time).
- A pin with a vague in-flight or awaited is a failed pin.
