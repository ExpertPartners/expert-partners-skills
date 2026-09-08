---
name: pin
description: "Carry-back envelope and place-keeping baton between Allison's Claude project conversations (Claude app, CoWork) and Claude Code. Fires at first contact in a new Code session, when composing ANY report bound back to a Claude project, when a block arrives opening with CLAUDE HOME or SESSION header lines (envelope check before executing), when Allison types /pin or says \"pin\", and when she confirms a paste (\"pasted\", \"done\"). Pin fires only after her paste confirmation. SESSION labels a Claude Code session and only ever that; a block bound for a chat conversation heads its envelope CONVERSATION. A Desktop worker titles ITSELF at birth through the native session-management tool and repairs its own drift, so /rename is retired from the routine path, and a table is named once at Table Birth instead. A pin is a bookmark, never a task. It inherits the operating-doctrine and never overrides it."
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

# Pin -- v4.10 (2026-09-08)

v4.8 (ruled by Allison 2026-08-26, decision of record aura decisions/0074-naming-and-session-steward.md) rewrites naming authority again, in the opposite direction from v4.3's `/rename` demotion: Claude Code Desktop's native session-management tools let a worker set its OWN title and repair other sessions' titles, proven live 2026-08-25/26 with persistence verified on independent reread. So the worker names itself at birth, repairs its own drift, and `/rename` retires from the routine path entirely, surviving only as the last-resort repair on surfaces without those tools. The name format changes with it, from three segments to `<Table Name> - <Specific Job>` (that form is itself superseded by v4.10 under decision 0091). See section 5.

<!-- RULED-BY: aura/decisions/0088-chair-worker-boundary-and-title-parity.md date:2026-09-04 -->
v4.9 (ruled by Allison 2026-09-04 via Lock that, ruling of record aura decisions/0088-chair-worker-boundary-and-title-parity.md) draws the chair/worker boundary through this skill. The CLAUDE HOME line names the table's CHAIR, the authoritative home conversation that stays seated at the table while the worker is away and receives the carry-back. A Claude Code session is a WORKER, a temporary execution session dispatched from the table, never a chair, even though the product presents it as a session. A CONVERSATION block landing in Code is therefore refused at the wrong door and never adopted, which SUPERSEDES the v4.4 adopt-and-continue instruction in section 4 (lane-spawn v1.6 had already retired adoption on its side). Titles follow roles. The chair reads exactly the TABLE NAME, the worker reads exactly `<Table Name> - <Specific Job>` (superseded by v4.10 under decision 0091, exactly two clear words), and the section 5 birth-only limit on chair title repair is superseded by continuing chair title parity. Envelope, timing, carry-back template, and verdict rules are unchanged.

<!-- RULED-BY: aura/decisions/0091-allison-controlled-two-word-routing-names.md date:2026-09-07 -->
v4.10 (ruled by Allison 2026-09-07 via Lock that, ruling of record aura decisions/0091-allison-controlled-two-word-routing-names.md; applied 2026-09-08): two-word routing names. This SUPERSEDES the `<Table Name> - <Specific Job>` worker form in section 5 and in the v4.8 and v4.9 paragraphs above, exactly as decision 0091 supersedes it in decisions 0074 and 0088. Every new WORKER visible title is exactly two clear words identifying the job, every new TABLE NAME and every Allison-authorized Table rename is exactly two clear words, and the chair's title stays exactly the current TABLE NAME (decision 0088). Worker ownership and return identity ride in durable routing state, the lane ledger row and the CLAUDE HOME line before registrar cutover, never in the title, so the CLAUDE HOME line this skill already requires on every carry-back is the worker's proof of home. Allison may rename a Table by explicit direction, prior names stay historical aliases so old pins and packets still resolve, and workers active before 2026-09-07 finish under their admitted titles. Envelope, timing, carry-back template, and verdict rules are unchanged.

A pin is a bookmark, not a task. It marks the exact spot where work handed off between Claude Code and the Claude project conversation that drives it. v4 (ruled by Allison 2026-08-03) makes the protocol surface-neutral: the home is a Claude PROJECT plus CONVERSATION, never assumed to be CoWork. v4 also adds the first-contact question and the "come back here" pin close. v4.1 (ruled by Allison 2026-08-03, same day) rewrites the carry-back SESSION STATUS line: it names the paste-back PROJECT and CONVERSATION explicitly, the ARCHIVE verdict is part of the line, and a session that is NOT clean to archive must give the instructions at that point instead of the ARCHIVE sentence. v4.2 (ruled by Allison 2026-08-03, same day) DELETES the closing line ("Let me know once you've pasted this back into ..., and I'll pin."): the carry-back ends at the SESSION STATUS line and never solicits a paste confirmation. v4.3 (ruled by Allison 2026-08-07) rewrites naming authority (section 5): sessions are named AT LAUNCH via `claude -n`, the name format is `<Project short name> - <Conversation name> - <Job name>`, and every session self-verifies its own name off disk at first contact. `/rename` is demoted to the exception repair. v4.3 also (same ruling, addendum) strips the ARCHIVE verdict out of the carry-back entirely: a session never declares itself ready to archive, the SESSION STATUS line ends at "carry-back delivered, awaiting verification at home," and archive authority moves to the home conversation. This supersedes the v4.1 ARCHIVE-verdict rule above. v4.4 (ruled by Allison 2026-08-07, same lane) adds the surface vocabulary lock: `SESSION` labels a Claude Code session and only ever that, a block bound for a chat conversation heads its envelope `CONVERSATION`, and `/rename` is a Code-only repair that is never handed out for a chat. See section 4 and section 5. v4.5 (re-ruled by Allison 2026-08-07 evening, in the Estate Brain Door Phase B Code session) brings the ARCHIVE verdict BACK and retires "carry-back delivered, awaiting verification at home" permanently: the session determines its own disposition and tells Allison plainly, SAFE TO ARCHIVE with evidence or NOT safe with the one move that closes it, because sessions that cannot say whether they are done pile up. This supersedes the v4.3 no-verdict addendum. See section 1. v4.6 (ruled by Allison 2026-08-07 afternoon, the worktree dispatch ruling; ruling of record aura intake/2026-08-07-ruling-dispatch-blocks-must-name-worktrees.md): a dispatch block that spawns a Code session also carries a `WORKTREE` line, and the session's first contact includes creating that worktree from a freshly fetched remote ref and confirming the absolute path, alongside the name self-verify. A spawning block without a WORKTREE line is malformed and bounces home, per code-block-routing's Worktree Isolation. See sections 4 and 5. v4.7 (ruled by Allison 2026-08-07, Aura / Code Rule Fix lane) adds the earned verdict line, amending the v4.5 archive verdict without replacing it: every carry-back ends with the standing SESSION STATUS line PLUS one earned verdict line, `RECOMMEND ARCHIVE -- all pushed, nothing pending on Allison's side` (permitted only when the checklist verifies: every commit pushed, the whole brief executed, nothing gated or held open, no deliverable still owed) or `RECOMMEND HOLD OPEN, waiting on <the one named thing>`. Archive authority stays with home and home's GitHub grading remains the backstop, but Allison may archive on the spot on a RECOMMEND ARCHIVE. See section 1.

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

SESSION STATUS: {the standing status line, section below}
VERDICT: {RECOMMEND ARCHIVE -- all pushed, nothing pending on Allison's side | RECOMMEND HOLD OPEN, waiting on <the one named thing>}
```

The VERDICT line is the last line of the carry-back, directly after the SESSION STATUS line (v4.7). There is no closing "Let me know once you've pasted... and I'll pin" line (deleted in v4.2); the carry-back never solicits a paste confirmation. Never write "into Cowork" anywhere in the carry-back. Always name the actual Claude project and conversation; if the session somehow reached a carry-back without knowing them, ask (section 0) before sending the report.

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

What stays with the home conversation: the actual archive click, and the ledger flip. Home flips the lane's row to `archived` in aura `docs/estate/lanes.md` as one motion with the archive, and no dispatch block is ever written against a row reading `archived`. Sessions are cheap and deterministically named, so spawn freely. Sessions born before v4.5 follow it from their next response.

### The earned verdict line (v4.7, ruled by Allison 2026-08-07, Aura / Code Rule Fix lane)

<!-- RULED-BY: aura/intake/2026-08-07-ruling-earned-verdict-line-on-carry-backs.md date:2026-08-07 -->

Amends v4.5; does not replace it. The standing SESSION STATUS line stays, and every carry-back adds exactly one earned VERDICT line after it, the carry-back's true last line:

- `VERDICT: RECOMMEND ARCHIVE -- all pushed, nothing pending on Allison's side.` Permitted ONLY when the session verifies its checklist live in the same turn: every commit pushed, the whole brief executed, nothing gated or held open, no deliverable still owed. A bare safe-to-archive with no checklist behind it stays banned.
- `VERDICT: RECOMMEND HOLD OPEN, waiting on <the one named thing>.` Every other state earns this one. One named thing, never a list.

Archive authority stays with the home conversation and home's GitHub grading remains the backstop, but Allison may archive on the spot on a RECOMMEND ARCHIVE without waiting for home. Sessions born before v4.7 follow it from their next carry-back.

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

Inbound blocks open with `CLAUDE HOME:` (or legacy `COWORK HOME:`) and `SESSION:`. Before executing anything in the block, check the SESSION line against your own authoritative name, read off disk per the self-verification recipe in section 5. If it names a different session: STOP, do not execute any of it, reply exactly "This block is addressed to {named session}; I am {own name}." (Incident this rule prevents: 2026-07-28, a Canon Doc Sync block was executed by the ORPHAN RECRUITING PIPELINE session.)

### SESSION means Claude Code, always (v4.4, ruled 2026-08-07)

`SESSION` labels a Claude Code session and only ever that. A block bound for a chat conversation in the Claude app or Cowork heads its envelope `CONVERSATION:` instead, and it opens with the bare conversation name on the line above that (lane-spawn skill, "The conversation name is the first line"). A chat block carrying a `SESSION:` line is malformed.

What that means for the inbound check here (amended v4.9 under decision 0088, superseding the v4.4 adopt-and-continue instruction). A block arriving in Claude Code whose envelope reads `CONVERSATION:` is a chat kickoff at the wrong door, a packet that births or seats a table's CHAIR, and a Claude Code session is a WORKER that can never be a chair. Do not adopt it and do not declare Birth from it. Inspect it, refuse it, and state the correct routing plainly, naming the room and table it belongs to and that it wants a chat conversation, per lane-spawn's "Landing on the wrong door (v1.6, inspect before adopt)". The STOP above is for a block addressed to a DIFFERENT lane's work, and the refusal here is for a block that named a chair's surface and landed on a worker's. The one narrow exception stays lane-spawn's. A block that correctly names THIS session's room and table and only mislabels the surface is a surface correction inside a correct identity, noted once in the ledger row, never an adoption.

`WORKER SESSION:` inside a chat kickoff and `CLAUDE HOME:` inside a Code block are pointers to the other surface, not envelope headers, and neither one violates the lock.

### A spawning block also carries its WORKTREE line (v4.6)

A block that spawns a NEW Code session carries a `WORKTREE` line in its envelope, naming the isolated worktree the session creates and works in. A spawning block arriving without one is malformed and bounces home, same as a block missing its routing line: do not execute it, reply naming what is missing so the dispatcher reships the block whole. Continuation blocks to an existing session inherit its established worktree and need not restate it. Full mechanics: code-block-routing, Worktree Isolation.

Judgment the check requires (v4.3, amended v4.8): a name mismatch is not automatically a misaddressed block. A session the harness auto-titled, or one launched without a name, will read a title that differs from a briefing genuinely meant for it. Distinguish the two: a block addressed to a DIFFERENT lane's work stops cold; a block that is plainly this lane's own continuation, arriving at a session never named to convention, proceeds and REPAIRS ITS OWN TITLE through the native tool alongside the work (v4.8), reporting the before and after rather than handing Allison anything. When it is genuinely ambiguous, ask before executing.

## 5. Naming authority (v4.8, ruled by Allison 2026-08-26; supersedes v4.3)

The SESSION NAME line in the block that spawns or briefs a session IS its name, adopted verbatim for life. Never improvise, abbreviate, or restyle it. Everything below is how that name gets onto the session and how the session proves it carries the right one.

### The name format

Exactly two clear words identifying the job. Decision 0091 (ruled 2026-09-07), superseding the `<Table Name> - <Specific Job>` form of decision 0074 and its restatement in decision 0088, which is preserved below for history only.

The table is the durable workstream and continuity anchor (decision 0066 as amended by decision 0081). Its authoritative home conversation is the chair, and the worker this name titles is never that chair (decision 0088). No room or table prefix. Worker ownership and return identity ride in durable routing state, before registrar cutover the lane ledger row and the dispatched CLAUDE HOME line, never in the visible title (decision 0091). Job words are descriptive; never numbered merely because a table has run several workers in sequence.

Example: `Steward Build`. Superseded example, history only: `Naming Claude Chats & Code Sessions - Steward Build`.

The worker title is its two-word job, the chair's title is exactly the TABLE NAME (itself two clear words for every new or renamed Table under decision 0091), and neither is ever given the other's form (decision 0088). A worker is never the chair of its table.

This SUPERSEDES the three-segment `<Project short name> - <Conversation name> - <Job name>` format of the 2026-08-07 ruling, which in turn extended the 2026-08-04 lane tag rule. What survives from both: readable words throughout, the job name as the trailing segment, and the requirement that the name identify its lane on sight with no ledger lookup. Under decision 0091 (v4.10) the lane-on-sight requirement is retired for workers: the title identifies the job, and the owning table is read from the lane ledger row or the CLAUDE HOME line.

One table, one active worker (decision 0074): a table runs many sequential workers over its life and never two concurrent independent ones. A second concurrent implementation job needs its own exactly named table first. Amended 2026-08-30 by decision 0082 (ruling of record aura decisions/0082-registrar-model-amendment-to-decision-0074.md): registrar scope admission replaces the count, and the bridge until cutover keeps the installed one-active-worker practice binding until Allison rules the one cutover. Ownership is proven from lane state, dispatch, or transcript evidence, never inferred from a shared repo, branch, PR, or topic.

### The worker names itself at birth

On Claude Code Desktop, the worker's FIRST management action is titling itself:

```
set_session_title(session_id="self", title="<Two Word Job>")
```

Then an independent verification read (the tool's own confirmation plus a reread of the last `custom-title` record in its own transcript). Amended 2026-09-08 (Startup Efficiency audit, implementation detail, no rule change): the tool's own success result is the birth verification, the transcript reread is for a tool error or a later drift check, and the search for the tool itself is made once, with absence reported plainly and the session continuing under the SESSION NAME line, never a retry loop. Live-verified 2026-08-25 and again 2026-08-26: a session renamed itself with no Allison and no `/rename`, one Desktop session renamed another, and both changes persisted on independent reread.

For CLI-only launches the dispatch still ships `claude -n "<full name>"` (`-n, --name` live-verified 2026-08-07 on Claude Code 2.1.223, and a headless run wrote the exact string to the session's `custom-title` record). Either way the worker self-verifies at first contact.

Birth self-titling is the whole point. A session born correctly named never needs a repair, and Allison never touches a window title.

### First-contact self-verification

A session reads its OWN name off disk and compares it to the SESSION line in its briefing. No human is in that loop. The name lives in the session transcript:

```
~/.claude/projects/<url-encoded-cwd>/<session-id>.jsonl
```

The encoded cwd is the absolute working directory with every `/` replaced by `-` (the leading `-` is kept). The name is the `customTitle` field of the record whose `type` is `custom-title`; take the LAST such record, because the harness rewrites it when it auto-titles.

```bash
python3 -c "
import json,sys
p=sys.argv[1]; t=None
for line in open(p):
    try: o=json.loads(line)
    except: continue
    if o.get('type')=='custom-title': t=o['customTitle']
print(t)
" ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl
```

Verified live 2026-08-07 on Claude Code 2.1.223. This supersedes the read half of the old claim that a session cannot read its own title; a session can, and must, and reports the result in its first response.

Report the comparison plainly at first contact: the name read off disk, the name in the briefing, and match or mismatch. On mismatch the session repairs itself in the same turn (v4.8) and reports the before and after; on a Desktop session the `get_session` metadata read is an equally valid independent check and does not replace this one.

First contact has a second half when the briefing spawned the session (v4.6): create the worktree the briefing's `WORKTREE` line names, from a freshly fetched remote ref, before any other work, and confirm the ABSOLUTE path in the same first report. No work happens in the shared main tree. Mechanics and the malformed-block bounce live in code-block-routing, Worktree Isolation.

### A session CAN rename itself (v4.8, supersedes the v4.3 set-half claim)

The set half of the old claim is superseded by live product behavior on Claude Code Desktop. The native session-management tool accepts `session_id="self"`, and it also renames OTHER sessions by their stable `local_<uuid>` sessionId. Both proven live 2026-08-25 and 2026-08-26, persistence confirmed by independent reread in each case.

What the v4.3 tracker citations (#33165, #83543, #84041, #84587) recorded remains historically accurate for the harness surface and the period they were checked. They no longer describe the Desktop capability, and no doctrine file may cite them to claim a session cannot name itself.

### Self-repair is the routine; /rename is the last resort

On mismatch or a missing title, the worker repairs ITSELF through the native tool and reports the before and after in its first response. Nothing goes to Allison. The Session Steward does the same across sessions, on evidence, per the session-steward skill.

An explicit rename overwrites even a hand-set title, so a rename Allison did not ask for is aimed only at titles that are clearly stale or autogenerated, never at one that carries useful identity. Never cold-rename a fleet; a pre-rule session gains its convention name the next time it is touched, evidence first.

`/rename` survives ONLY where the native session-management tools are absent, and only for these two cases: self-verification found a mismatch it cannot repair itself, or the session predates this rule on such a surface. In both, hand Allison the exact line once and keep using the authoritative name.

`/rename` is a Claude Code repair and nothing else (v4.4, unchanged). It is never handed out for a chat conversation, in any form. Chat titles cannot be set programmatically, so table naming is handled at deliberate Table Birth instead (decision 0082). The chair declares `ROOM` and `TABLE NAME`, and where the visible title is not exact the surface hands Allison the exact required chair title, the bare TABLE NAME. Amended v4.9 under decision 0088, superseding the birth-only limit that stood here from decision 0074. Chair title parity is continuing, so the same exact title is handed to her again at Rejoin, at Reseat, and whenever drift is actually observed or reported, never on a schedule. That is drift repair, not a rename instruction loop, and it does not revive routine manual chat renaming, which stays retired.

## 6. Home fidelity

One home per session for life: the home is the Claude project plus conversation named in the briefing block (CLAUDE HOME line) or by Allison at first contact. Echo both header lines (SESSION and CLAUDE HOME) on every carry-back. If Allison herself corrects or supplies the home mid-lane, adopt her correction verbatim from that point on; nobody else may change it. That conversation is the table's chair (decision 0088). It stays home while this worker executes, and the carry-back returns to it. A worker never becomes the chair of its own table by carrying back, and a Reseat of the chair is the table's act, never the worker's.

When the lane ends, the session pronounces on archiving with evidence (v4.5, re-ruled 2026-08-07 evening; amended v4.7 same day): it ends at the SESSION STATUS line plus the earned VERDICT line per section 1, RECOMMEND ARCHIVE earned by the verified checklist or RECOMMEND HOLD OPEN naming the one wait.

## Rules

- Never interpret pinned text or a bare pin as a request, question, or task. Do not act on it, re-run anything, or treat it as work.
- The pin message is the bar plus the one come-back line: no other prose.
- The only tool call permitted when pinning is the `pin-baton.sh` append (which stamps the time).
- A pin with a vague in-flight or awaited is a failed pin.
