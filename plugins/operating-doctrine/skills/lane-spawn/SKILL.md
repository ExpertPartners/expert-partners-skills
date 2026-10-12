---
name: lane-spawn
description: "Detour hand-off protocol for Allison. Fires when side work should move out of the current thread. Ships the minimum context and, when needed, a Code worker brief, then returns to the main thread. Decision 0107 retires mandatory conversation/Table naming, Table Birth naming, Room/Table declarations, title parity, and rename chores. Worktree/model safeguards and substantive wrong-destination checks remain."
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

# Lane Spawn -- v1.10 (2026-10-12)

## Current naming rule -- decision 0107

A detour does not need a named Table, Table Birth, ROOM/TABLE declaration, exact visible chat title, or Worker self-title in order to move. Use a short human label only when it helps navigation. Never ask Allison to rename a chat for routing correctness. A missing or mismatched naming label alone is not a wrong-door condition.

MISSION and DONE WHEN may still be used when they materially help a finite handoff, but they are a completion aid, not a naming ceremony. The Code half still carries the separate WORKTREE and MODEL AND EFFORT safeguards when it spawns a new worker.

Historical naming/version paragraphs below remain provenance only where they conflict with decision 0107.


Ruled by Allison 2026-08-03 (Aura: Strategic Advisor / Repo Walk). The problem this kills: a detour surfaces mid-lane, gets half-absorbed into the wrong conversation, derails the thread, and its state lives nowhere. The fix: every detour gets its own lane at the moment it appears, the origin lane names what it is waiting on, and the origin thread continues without a beat.

v1.1 (ruled by Allison 2026-08-03, same day, after a live misroute): every paste bound for ANY surface carries the full envelope, and a block that lands on an unexpected surface adopts itself and continues instead of interrogating Allison. See "Every paste carries the envelope" and "Landing on the wrong door" below. SUPERSEDED IN PART by v1.6: the envelope half stands unchanged and is load-bearing, the adopt-itself half is retired by decision 0081's chair authority law, ruling of record aura decisions/0081-chair-model-amendment-to-decision-0066.md, and replaced by inspect before adopt.

v1.2 (ruled by Allison 2026-08-07, same lane as the naming and archive rulings): the chat side of naming. A chat kickoff block now opens with the conversation name as its literal first line, plain and alone, because the app auto-titles a conversation from its first message and nothing can set that title programmatically. The block also heads its envelope with CONVERSATION, never SESSION. See "The conversation name is the first line" and "Vocabulary lock" below. The live failure that forced it: a spawn block buried the conversation name mid-block and led with mission text, so the app titled the chat off the mission and the lane was born with two names.

v1.3 (ruled by Allison 2026-08-07 afternoon, the worktree dispatch ruling; ruling of record aura intake/2026-08-07-ruling-dispatch-blocks-must-name-worktrees.md): the Code half of a spawn pair carries a `WORKTREE` line naming the isolated worktree the worker session creates and works in, per code-block-routing's Worktree Isolation. A block that spawns a Code session without one is malformed and bounces home.

v1.4 (ruled by Allison 2026-08-26, decision of record aura decisions/0074-naming-and-session-steward.md): Table Birth. A spawned conversation is a TABLE, the durable continuity anchor for its work, and it is named exactly once at birth. The kickoff block still leads with the bare name for the auto-titler, and the receiving surface now also DECLARES that name on its first substantive turn as `TABLE NAME: <exact name>`, so the declared name and the visible title are compared once, at birth, and Allison performs at most one manual title rename if they differ. The Code half changes too: the worker is named `<Table Name> - <Specific Job>` and titles ITSELF through the native session-management tool, so no launch line and no rename hand step ride along. One table, one active Code worker. See "Table Birth" and "The worker half" below. SUPERSEDED IN PART by v1.8 (ruling of record aura decisions/0088-chair-worker-boundary-and-title-parity.md). The compare-once-at-birth title check is replaced by continuing chair title parity under decision 0088. The rest of v1.4 stands. SUPERSEDED IN PART by v1.9 (decision 0091): the `<Table Name> - <Specific Job>` worker form is retired, a worker title is exactly two clear words identifying the job, and a Table is named at Birth but Allison may later rename it by explicit direction.

v1.5 (ruled by Allison 2026-08-26, decision of record aura decisions/0077-room-identity-literal.md): ROOM joins Table Birth. The birth declaration is two lines, `ROOM: <exact room identity>` above `TABLE NAME: <exact permanent table name>`. The exact ROOM string comes solely from that room's own Project Instructions ROOM identity literal, never reconstructed from canon prose, ledger rows, intake records, conversation memory, or this skill (skills carry the value, they never own one). The `CONVERSATION:` envelope line's project segment is composed from that same literal. Platform honesty also lands: a chat surface cannot read its own visible title, so the birth declaration states the intended name, says plainly that visible-title parity cannot be verified from that surface, and asks Allison for the one birth-time glance and rename if the visible title differs, never claiming a title was inspected, matched, or fixed when the surface cannot know that. The live failures that forced it, 2026-08-26: a fresh Aura table declared ROOM as Aura Strategic Advisor, dropping the colon from the Project's actual visible name, because canon prose itself carries the colon-less spelling; the same day NORTH's ChatGPT Project auto-titled a table "Recommend Twilio next move" over the declared name "Twilio Account Cleanup" with no birth-time detection. SUPERSEDED IN PART by v1.8 (ruling of record aura decisions/0088-chair-worker-boundary-and-title-parity.md). The one birth-time glance becomes continuing chair title parity, with the platform-honesty rule unchanged. SUPERSEDED IN PART by v1.9 (decision 0091): the TABLE NAME is permanent only until Allison renames it by explicit direction.

v1.7 (ruled by Allison 2026-09-01, the founder-load table-lifecycle amendment, ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md, source aura issue #200, delivered 2026-09-03): a mission table is born carrying its own completion contract. The kickoff block and the Birth declaration each gain two lines, MISSION and DONE WHEN, so the table can later prove terminality from its own durable record instead of waiting for Allison to notice the work is over. Scratch and general-purpose conversations are exempt and carry neither line, and they are never nagged to archive merely because a topic ended. The contract is what session-wrap's terminality check reads, so a table born without it cannot self-surface completion. Pre-cutover boundary, decision 0082 and decision 0080 Section 24: this attaches to the currently installed birth-declaration wiring that still binds today, it opens no registrar, no table registry, and no routing-state write, and the deliberate Birth trigger stays exactly where decision 0082 left it. The live failure that forced it, 2026-09-01: the Shared History Bridge table's durable records said its original mission was accepted complete with no further action owed, and the chair still behaved like an open work surface and began absorbing adjacent work, because nothing it owned ever stated what finishing looked like.

<!-- RULED-BY: aura/decisions/0088-chair-worker-boundary-and-title-parity.md date:2026-09-04 -->
v1.8 (ruled by Allison 2026-09-04 via Lock that, ruling of record aura decisions/0088-chair-worker-boundary-and-title-parity.md): the chair/worker boundary and continuing title parity. A CHAIR is the authoritative home conversation where a table is seated, its return, review, routing, and continuity location. A WORKER is a temporary execution session dispatched from a table into an approved implementation engine, and a worker is NOT a chair even when its surface presents it as a conversation or session. The chair stays home at the table while the worker executes, the worker returns its evidence to the table's chair, and the worker then follows its own terminal lifecycle. Visible titles follow the role. A chair's title is exactly the TABLE NAME, a worker's title is exactly `<Table Name> - <Specific Job>` (superseded by v1.9 under decision 0091, exactly two clear words), and neither title ever creates or overrides identity. Chair title parity is a CONTINUING invariant, not a birth-only cosmetic check. Where a surface can read and set its own title it maintains parity itself, and where only Allison can rename, the surface hands her the exact required chair title at Birth, Rejoin, or Reseat and whenever drift is actually observed or reported. This SUPERSEDES the birth-only title-repair language of v1.4 and v1.5 above and narrows the v1.6 sentence that a conversation is a chair, exactly as decision 0088 narrows decisions 0081 and 0080. The deliberate Birth trigger, the registrar and admission architecture, the scope-collision rules, the wrong-door refusal, the ROOM literal, and the pre-cutover bridge are unchanged. Routine, repeated, or unprompted chat rename requests stay banned, and a drift-driven repair is not one of those.

v1.8 correction, same day, on NORTH's live review of PR 23 (same ruling of record aura decisions/0088-chair-worker-boundary-and-title-parity.md). The standing sentence that Allison's own rename of a conversation wins and the ledger follows her is SUPERSEDED in every active rule of this skill. A visible-title rename alone never changes TABLE NAME, table identity, or ledger identity. It is drift, repaired back to the exact TABLE NAME, and a genuinely different durable mission gets a different table by deliberate Birth, never by renaming a sidebar title.

<!-- RULED-BY: aura/decisions/0091-allison-controlled-two-word-routing-names.md date:2026-09-07 -->
v1.9 (ruled by Allison 2026-09-07 via Lock that, ruling of record aura decisions/0091-allison-controlled-two-word-routing-names.md; applied 2026-09-08): two-word routing names, Allison-controlled Table renames. This SUPERSEDES the `<Table Name> - <Specific Job>` worker form of v1.4 and v1.8, and the name-stable-for-life statements of v1.4 through v1.8 exactly as decision 0091 supersedes them in decisions 0074, 0081, 0082, and 0088. Every new TABLE NAME and every Allison-authorized Table rename is exactly two clear words, and so is every new WORKER visible title, which identifies the job and not the table. Worker ownership and return identity ride in durable routing state (the lane ledger row and the dispatch's CLAUDE HOME line before registrar cutover), never in the title. Allison may rename an existing Table by explicit direction, the rename changes the authoritative name only, prior names remain historical aliases to the same Table so old packets, pins, and ledger rows still resolve, and an alias is never reused for a different Table in the same ROOM. An AI surface may suggest a compliant name and never applies a durable Table rename on its own. Workers active before 2026-09-07 finish under their admitted titles, and legacy Table or Chair names are never mass-renamed by AI. Decision 0088's chair title parity stands and consumes the two-word Table name.

v1.6 (ruled by Allison 2026-08-30, ruling of record aura decisions/0081-chair-model-amendment-to-decision-0066.md, aura decisions/0082-registrar-model-amendment-to-decision-0074.md, and aura decisions/0084-registry-consumption-amendment-to-decision-0077.md, implementing decision 0080 Section 28): the chair model, the deliberate Birth trigger, inspect-before-adopt at a wrong door, and registrar concurrency. A table is the durable logical workstream and a conversation is a chair seated at it, so a spawn pair creates a table and seats its first chair. Table Birth is a deliberate declared act and never an automatic consequence of a conversation existing, so a conversation that has not performed deliberate Birth is Scratch, holds no table identity, owns no workers, and dispatches none. The v1.1 adopt-on-wrong-surface rule is RETIRED: a surface that is not a block's named destination inspects the block, refuses it, and states the correct routing, and it never adopts an inbound identity. And the one-table-one-active-worker limit is replaced by registrar-enforced scope admission, a table may hold multiple active workers whose exact execution scopes do not conflict, with duplicate same-table same-title workers and exact scope collisions refused. Bridge until cutover, per decision 0082 and decision 0080 Section 24: the registrar, the table registry, and revision enforcement do not exist yet, so until the one cutover Allison rules, the installed wiring continues to bind, automatic birth declarations and the one-active-worker practice included, understood as pre-cutover acts a chair performs on behalf of its table. No installed rule is silently repealed and no unregistered concurrency opens today. The live failure that forced the wrong-door half, 2026-08-30: this table's own authoritative birth packet was misdelivered to NORTH, and NORTH correctly refused it rather than adopting it, preserved as a positive acceptance fixture at aura intake/2026-08-30-wrong-door-refusal-example-routing-architecture-birth-packet.md, while this file's installed text still said ADOPT. NARROWED by v1.8 under decision 0088. The chair here is the authoritative home conversation seated at the table, and a worker session dispatched from the table is not a chair, however its surface presents it.

A detour is any work item that surfaces inside a lane but is not that lane's job per its kickoff. Quick verification reads (a file check, a live probe) are not detours; do those inline. Anything with its own state, its own carry-backs, or its own rulings is a detour and spawns.

## The spawn pair

When a detour fires, one message ships up to three parts, in this order.

PASTE 1 -- LANE KICKOFF (always). A fenced block Allison pastes as the FIRST message of a new conversation. Tell her, outside the block, exactly where: which Claude project, which SURFACE (a chat conversation in the Claude app or Cowork, or a Claude Code session), and the name to give it. The block contains, in this order:

- **First line: the conversation name, plain and alone.** Nothing else on that line, nothing above it. See the next section for why this is first and why it is bare.
- Then the envelope: `CONVERSATION: {Claude project} / {conversation name}` and `SURFACE: {chat conversation | Claude Code session}` and, when a worker session exists or will exist, `WORKER SESSION: {exact Code session name}`.
- Then the mission contract, two lines, whenever this lane is a mission table (v1.7): `MISSION:` what this table exists to accomplish, in one sentence, and `DONE WHEN:` the evidence that proves that mission achieved. See "The mission contract" below for what makes a good DONE WHEN and when the two lines are correctly omitted.
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
WORKER SESSION: Rail Diagnostic
MISSION: Restore the Ember briefing rail so the 8 AM briefing sends on its own.
DONE WHEN: Two consecutive briefings send unattended and land on Allison's phone, verified from delivery logs.

WHAT THIS LANE IS: ...
```

A short navigation label may appear when helpful, but the kickoff does not depend on the auto-titler or exact visible-title output. Destination capability and durable return state govern.

PASTE 2 -- CODE BLOCK (only when a worker session is needed). Per the code-block-routing skill, its durable return destination names the new lane rather than the origin lane so the carry-back lands where the work will be ruled. The Code half carries its separate `WORKTREE` and `MODEL AND EFFORT` safeguards. A human-readable worker label is optional; no session-name, self-title, or title-verification step rides as a prerequisite.

RESUME LINE (always, same message, after the blocks). One line stating what the origin lane awaits from the new lane (or 'nothing, fully detached'), then the origin lane's next step, immediately. The origin lane never closes its turn on the detour.

## Historical: conversation-name-first rule (superseded by decision 0107)

Chat conversation titles cannot be set programmatically. The Claude app and Cowork auto-title a conversation from its first message, and no session, tool, or API can override that (live-verified 2026-08-03, reconfirmed by the 2026-08-07 failure below). The only lever the block-writer has is what the first message says first.

So: **the conversation name is the literal first line of the kickoff block, plain and alone.** No label in front of it, no date suffix, no mission text above it, no envelope line above it. Lead with the name and the auto-titler lands on it or close to it.

The failure this replaces, 2026-08-07: a spawn block buried the conversation name several lines down and opened with mission text instead. The app titled the chat off the mission, and the lane had two names from birth, the one the ledger recorded and the one Allison could see.

**Chat lane identity is the kickoff header line**, per the standing 2026-08-03 ruling; the displayed title is not the mechanism, because it cannot be set programmatically. Leading with the name is what gives the auto-titler the right material.

**Table Birth (v1.4, decision 0074) replaces near-match acceptance for tables.** A spawned conversation is seated as the authoritative chair of a new table (decisions 0081 and 0088), and a table is named at birth, exactly two clear words, renamed afterward only by Allison's explicit direction (decision 0091). Mechanics:

1. The kickoff block leads with the bare name (above), so the auto-titler lands on it or close.
2. At deliberate Table Birth the receiving chair DECLARES identity in two lines (v1.5, decision 0077, trigger amended by decisions 0082 and 0084): `ROOM: <exact room identity>` then `TABLE NAME: <exact table name>`. Birth is a deliberate declared act, never an automatic consequence of a first substantive turn, and a conversation that has not performed it is Scratch. The ROOM string comes solely from the room's own Project Instructions ROOM identity literal, which the table registry consumes, validates, carries, and points at but never silently replaces, and the installed literal wins on any disagreement with the disagreement surfaced. Bridge until cutover, decision 0082: the installed automatic birth-declaration wiring continues to bind until Allison rules the cutover, as a pre-cutover act a chair performs on behalf of its table.
3. The surface cannot read its own visible title, so it states the intended TABLE NAME, says plainly that visible-title parity cannot be verified from that surface, and hands Allison the exact required chair title, the bare TABLE NAME, if the visible title differs. Chair title parity is continuing (v1.8, decision 0088). The same exact title is handed to her again at Rejoin, at Reseat, and whenever drift is actually observed or reported, never on a schedule and never as an unprompted nag, and a surface that can read and set its own title maintains parity itself. The platform-honesty rule stands, never claiming a title was inspected, matched, or fixed when the surface cannot know that (v1.5, decision 0077).
4. After that the table name stands until Allison herself renames the Table by explicit direction (decision 0091; the rename changes the authoritative name only, prior names stay historical aliases to the same Table), and no implementation dispatch leaves an unnamed or unconfirmed table. A Scratch conversation dispatches nothing and owns nothing, and no chair acquires table authority by asserting it, only through Birth, Rejoin, or Reseat (decision 0081). A worker dispatched from the table is not a chair and never acquires chair authority by executing (decision 0088).
5. A mission table's Birth declaration carries two more lines below the name (v1.7), `MISSION:` and `DONE WHEN:`, taken verbatim from the kickoff block when one shipped and composed by the chair when the table was born some other way. They are declared once, at Birth, alongside the name. A table born without them can never self-surface its own completion, which is the whole failure v1.7 exists to kill.

What did NOT come back: routine, repeated, or unprompted chat rename requests stay banned, `/rename` is still never handed out for a chat in any form, and chat lanes still never get PARITY MISMATCH flags. Table Birth is a single naming act at the moment a table is created, not a maintenance loop, and the NAME set there changes afterward only by Allison's explicit rename (decision 0091), never by AI and never by a drifted sidebar title. What v1.8 changes under decision 0088 is the title mirror, not the name. The birth-only limit on raising a chair title correction is superseded, because the visible chair title must read exactly the TABLE NAME for the chair's whole life, so the correction is raised at Birth, at Rejoin, at Reseat, and whenever drift is actually observed or reported. A title mismatch never changes the table's identity, the title is repaired back to the table. A manual visible-title rename alone, Allison's own included, never changes the TABLE NAME, the table's identity, or the ledger's record of it, so the ledger never follows a retitled sidebar. If the visible chair title differs from the TABLE NAME, that is title drift, and it is repaired back to the exact TABLE NAME under decision 0088. A genuinely different durable mission gets a different table by deliberate Birth, never by renaming a sidebar title.

## The mission contract: MISSION and DONE WHEN

A finite mission exists to accomplish a stated thing. Its durable contract records what that thing is and how anyone will know it happened. It does not depend on a Room, Table, title, Birth declaration, or any other naming ceremony.

`MISSION:` one sentence naming what this table exists to accomplish. Allison's stated outcome, not the build. "Restore the Ember briefing rail so the 8 AM briefing sends on its own," never "edit the launchd plist."

`DONE WHEN:` the acceptance evidence that proves the mission achieved. It must be something a later reader can check without asking Allison, so it names artifacts, merges, live behavior, or delivery proof. "Two consecutive briefings send unattended and land on Allison's phone, verified from delivery logs" is a DONE WHEN. "The rail works" is not, because nothing can be checked against it. When the honest completion condition is Allison's own acceptance of a deliverable, say that exactly, naming the deliverable she accepts, so the check has one real thing to look for.

Which work carries it, and which correctly does not. Record it for a finite mission with a stated outcome, whether it dispatches workers or not. A general-purpose conversation carries neither line and is exempt: it is thinking, reading, exploring, or keeping Allison company on a subject, and it is never nagged to archive merely because a topic ended. A standing subject that exists to be there rather than to finish is exempt the same way and says so plainly in place of a DONE WHEN, so the exemption is a recorded fact rather than a missing line. Absence of the contract is never treated as unfinished work.

What reads it. The session-wrap terminality check reads this contract when acceptance evidence lands and decides whether the mission is achieved. Durable work state proves completion from its own record, so Allison never has to be the one who notices the work is over.

What it is not. It is not a plan, a scope, a task list, or a success metric, and it never grows as the work goes. A mission that genuinely changed is Allison's ruling to make, and a completed table never rewrites its own DONE WHEN to keep itself alive (session-wrap v1.11, section 4B).

The contract creates no identity, registry, registrar record, or naming requirement. It is task context and completion evidence only.

**The execution half.** A temporary execution session works in an approved implementation engine and returns evidence to its durable origin. Admission is governed by exact execution scope: concurrent work proceeds when scopes do not conflict and an actual mutable-scope collision is refused. Visible labels, shared titles, or missing names do not establish a collision. Worktree, model and effort, repository/host, credential and production boundaries, and terminal lifecycle requirements remain enforced.

## Historical: CONVERSATION/SESSION naming vocabulary (superseded by decision 0107)

The two surfaces get two words, and they never trade.

- A block bound for a **chat conversation** (Claude app or Cowork) heads its envelope `CONVERSATION:`. A chat block carrying a `SESSION:` line is **malformed**: rewrite it before it ships.
- A block bound for a **Claude Code session** heads its envelope `SESSION:`, per the pin skill and code-block-routing. That is unchanged.
- `WORKER SESSION:` inside a chat kickoff is correct and is not a violation. It names the Code lane the chat will receive carry-backs from; it is a pointer, not the block's own header.
- `CLAUDE HOME:` inside a Code block still names the Claude project plus conversation. That is a pointer too, and it is unchanged.

One word per surface, so a block's destination is legible from its first envelope line even when it lands somewhere unexpected.

## Every paste carries the envelope (v1.1)

A misroute in live use (2026-08-03) proved that any paste without identity lines strands the receiving session in the first-contact question. So the rule extends beyond Code blocks: EVERY paste handed to Allison that is bound for another lane or session, kickoffs, directives, envelope confirmations, carry-notes, everything, opens with lines that name the destination lane and, where known, the session. A paste that could land anywhere must be able to identify itself anywhere. The pastes are the nervous system; unlabeled pastes are how lanes fall off.

Under v1.2 a chat kickoff satisfies this with its first line (the bare conversation name) plus its `CONVERSATION:` line immediately below. The bare name does not replace the envelope; it sits above it.

## Landing on the wrong execution surface

Chat conversations and execution surfaces can look alike mid-flow. Inspect the task's actual destination and capability requirements rather than treating its labels as authority.

Refuse only when substantive evidence proves the task belongs elsewhere: wrong repository, wrong execution host, incompatible destination capability, production or credential boundary, destructive-action gate, or an actual execution-scope collision. State that concrete mismatch and the correct destination.

A refusal remains correct when one of those substantive conditions is proven. Decision 0107 retires the older naming-only refusal fixture as governing behavior; it remains historical evidence.

`CONVERSATION`, `SESSION`, ROOM, TABLE, Chair, Worker, and visible-title text are navigation metadata. None is a refusal trigger by itself.

Recover return context from the current thread, native IDs, durable lane state, and dispatch evidence. Ask only when a required return destination cannot be recovered and the task genuinely needs one.

When only a label is stale, continue, correct the durable routing record if needed, and do not ask Allison to re-paste or rename anything.

## Historical naming rules (superseded by decision 0107)

Claude proposes the conversation name: exactly two clear words (decision 0091), the topic, readable in a sidebar (e.g. `Ember Audit`, `Funnel Audit`). Keep it to the words that identify the lane; date suffixes and the word "kickoff" no longer ride on the name itself under v1.2, because the name is now the line the auto-titler reads. When a lane is genuinely date-bound, the date goes in the block body, not in the name.

The name in the kickoff block IS the table's name, exactly two clear words, standing until Allison herself renames the Table by explicit direction (decision 0091); it is what the receiving chair declares as `TABLE NAME` at deliberate Table Birth (v1.6, decision 0082), and it is what the lane ledger records. The chair's visible title must read exactly that name for the chair's life (v1.8, decision 0088), compared at Birth and repaired again at Rejoin, at Reseat, and whenever drift is actually observed or reported, by the surface itself where it can read and set its title and by Allison, handed the exact title, where only she can. Never on a schedule and never unprompted. A manual visible-title rename alone, Allison's own included, never changes the TABLE NAME, the table's identity, or what the ledger records. A differing title is drift and is repaired back to the exact TABLE NAME. A genuinely different durable mission gets a different table by deliberate Birth, never by renaming a sidebar title (decision 0088).

Worker (Code session) names are a different rule: exactly two clear words identifying the job (decision 0091, superseding the `<Table Name> - <Specific Job>` form of decision 0074), self-titled at birth through the native session-management tool. See the pin skill, section 5, and code-block-routing, Session Naming. A Table name is also exactly two clear words, and Allison may rename a Table by explicit direction with prior names kept as historical aliases (decision 0091). Never put a room prefix on either. The two titles are the two roles (decision 0088). A chair reads exactly the TABLE NAME, a worker reads its two-word job and never its table's name, and no dispatch, wrap, or steward action ever retitles the home chair to a worker's job.

## Ordering when Allison asks mid-detour

If a Code block already shipped before the new lane existed (the detour escalated), the kickoff block ships next, homed correctly, and it must name the already-running Code session so the carry-back address is unambiguous. Fix the home at the first opportunity; never let a worker session carry back to a lane that does not exist.

## Rules

- Never absorb a true detour into the current work when it has become an independent body of work; either handle a tiny in-scope verification inline or hand off the independent job.
- Keep the handoff minimal and return to the origin thread.
- Human-visible Room/Table/Chair/Worker names are optional and never a gate under decision 0107.
- Do not require Table Birth, Rejoin, Reseat, title parity, two-word names, or manual renames.
- A substantive wrong destination such as the wrong repo, production target, or execution host is still refused. A title or Table-label mismatch by itself is not.
- A new Code worker still carries its WORKTREE and MODEL AND EFFORT safeguards.
- Actual execution-scope collisions remain protected.
- If a finite mission benefits from MISSION and DONE WHEN, include them as task context, not as identity ceremony.
