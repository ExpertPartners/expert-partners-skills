---
name: "code-block-routing"
description: "Fires on Claude Code paste blocks and implementation briefs for Allison. Requires the destination surface plus the non-naming execution safeguards that still matter, including WORKTREE and MODEL AND EFFORT on a new Code worker, waiting-on state, lane ledger lifecycle, canonical version reads, and earned closeout. Decision 0107 retires mandatory Room/Table/Chair/Worker naming ceremony, exact SESSION NAME gates, title parity, two-word title rules, and naming-only bounces."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
defers-to:
  - pin
brand-scope: null
subtitle: "paste block routing and the lane ledger"
---

# Code Block Routing

## Current naming rule -- decision 0107, 2026-10-12

Human-visible routing names are optional navigation metadata. Do not require ROOM, TABLE NAME, SESSION NAME, Chair title, Worker title, title parity, two-word naming, Table Birth naming, self-titling, or rename confirmation before work proceeds. Do not bounce an otherwise executable block solely because naming metadata is missing, different, or auto-generated. Do not ask Allison to rename a chat or worker for governance.

The routing line still names the destination surface because that changes where Allison pastes. For a new Code worker, WORKTREE and MODEL AND EFFORT remain separate hard safeguards. Repository, worktree/branch, execution scope, destination capability, and return location remain the useful routing facts. Historical naming sections below are preserved for provenance and are non-operative wherever they conflict with decision 0107.


Rule authored by Allison, 2026-07-27. Every time a block is handed to Allison to paste into a Claude Code session (intake block, implementation brief, fix instruction, verification request, anything), the block must be preceded by exactly one routing line, outside the code fence.

## The Routing Line Names The Surface, Not Just The Session

Amended 2026-07-28 at Allison's instruction: "always say paste into Claude Code Ember audit, even though it seems obvious, because sometimes the names get off." Naming the surface removes the ambiguity that appears when a session's window title has drifted from its authoritative name, or when the same workstream has both a Cowork conversation and a Claude Code session.

Required format:

PASTE INTO: Claude Code

A short existing-session or new-session hint may be added when it helps Allison find the right window, but no exact session name is required and no visible title is authoritative.

Rules for the routing line:

1. Always name the destination surface.
2. Keep it one line and easy to spot.
3. Human-readable session/workstream labels are optional and never a gate.
4. Continue an existing worker when the actual task context and execution state show it is the same job. Otherwise start a new isolated worker.
5. Prefer stable native session identifiers, repo/worktree/branch, durable lane state, and exact scope over visible titles.
6. Never invent a worker as existing merely because a label sounds familiar.
7. Actual execution-scope collisions still block; title similarities or differences do not.


## Dispatch Dedupe: Read The Ledger For A Standing Owner First

Ruled by Allison 2026-08-07; born the night of 2026-08-06 when one ordered dispatch reached two lanes from two governing conversations and neither knew of the other. Door Tools Build and the Estate Brain Write Tools lane's Ledger Guard Build both built a working ledger tool. The second lane caught the collision at deploy pre-flight, when the live image and origin/main both already carried `update_lane_row`, and dropped its duplicate unmerged. Nothing was overwritten, and that was luck plus one careful pre-flight, not design. The duplicate was invisible until pre-flight because the second lane's worktree was cut from a stale remote ref.

Before dispatching ANY build, the dispatcher reads the Active lanes table in aura `docs/estate/lanes.md` for a standing owner of that tool class. Not that exact tool, that tool CLASS: door tools, ledger writers, CI watchers, board publishers, brain readers, and so on. A lane already holding the class is its owner.

The three outcomes, and there is no fourth:

1. A standing owner exists and is active. Route the work to that lane as an existing session. Do not open a second lane on the same class.
2. A standing owner exists but is complete or archived. Say so on the routing line, name the row, and dispatch fresh. The prior lane's record is the new lane's inherited state.
3. No owner exists. Dispatch fresh and write the row at dispatch, which is what makes the next dispatcher's read work. A dispatch that skips its row is what causes the next collision.

Two hard riders. Every dispatched build cuts its worktree from a freshly fetched remote ref, never from whatever the local clone happens to hold, because a stale base hides an existing implementation until pre-flight. And every build runs a pre-flight that checks the live artifact and origin/main for the thing it is about to build; finding it already there is a successful pre-flight, and the correct move is to drop the duplicate unmerged and report, exactly as the second lane did.

This rule is Rule 8 of the routing line extended from shared state to shared PURPOSE. Rule 8 stops two sessions from touching one file. This stops two sessions from building one tool.

## Worktree Isolation: Every Spawning Dispatch Names Its Worktree

First ruled by Allison 2026-08-07 as decision 9d of the Estate Brain Door Phase B record, after the 2026-08-04 incident where two sessions sharing one working tree reset each other's uncommitted edits mid-job. Uncommitted work has no undo, so this is data loss, not inconvenience.

HARDENED by Allison's ruling of 2026-08-07 afternoon (ruling of record: aura intake/2026-08-07-ruling-dispatch-blocks-must-name-worktrees.md). The rule existed but was not enforced at the dispatch chokepoint, and the Phase B session alone logged three collisions: a ledger edit that landed under a sibling's commit, a multi-branch git pull failure, and the Door Tools Build lane losing a full build to a sibling executing the same order. The requirement now lives where the violation is visible at paste time instead of discoverable at collision time.

**Every dispatch block that spawns a Claude Code session carries a `WORKTREE` line naming the isolated worktree the session works in.** Unconditional. Concurrency risk is assumed at dispatch, never assessed away with "they probably will not overlap."

Mechanics:

1. The `WORKTREE` line rides inside the block with the envelope, naming the tree and the branch (one name serves both when they match). The session's FIRST ACT is creating that worktree from a freshly fetched remote ref (`git worktree add ../worktrees/<name> -b <name>`, same fresh-ref rider as dispatch dedupe) and confirming the ABSOLUTE path in its first report. No work happens in the shared main tree.
2. **A dispatch block that spawns a Code session and arrives WITHOUT a `WORKTREE` line is malformed and bounces home, same as a block missing its routing line.** The receiving session does not execute it; it replies naming what is missing so the dispatcher reships the block whole.
3. A session NEVER writes in a repo's main working tree when another lane may hold uncommitted state in it. Check before writing: `git worktree list`, then `git status` in the main tree. Uncommitted changes belonging to someone else mean isolate, always.
4. Serializing is a legitimate answer when the work genuinely cannot split, and it is stated, never assumed: the dispatch replaces the `WORKTREE` line with an explicit serialization statement naming the order, and the second lane's row records that it waits on the first. Silence is never serialization.
5. The worktree is named in the lane's ledger row at dispatch, so the next dispatcher can see which trees are occupied.
6. This rule binds the dispatcher AND the dispatched session. The dispatcher ships the line; the session enforces it by bouncing a spawning block that lacks one, and confirms its tree's absolute path before touching anything else.
7. Continuation blocks routed to an EXISTING session inherit that session's established worktree and need not restate it. A pre-rule session with no isolated tree that receives new work isolates itself at that point and says so in its carry-back.

## The Model And Effort Line: Every Spawning Dispatch Names What To Click

Ruled by Allison 2026-08-10, same enforcement shape as Worktree Isolation above: a rule that exists but is not enforced at the dispatch chokepoint is a rule nobody can rely on.

**Every dispatch block that spawns a NEW Claude Code session carries a `MODEL AND EFFORT` line, naming exactly what to select in the Claude Code model and effort picker before the block below it is pasted.** Unconditional. **A dispatch block that spawns a Code session and arrives WITHOUT a `MODEL AND EFFORT` line is malformed and bounces home, same as a block missing its `WORKTREE` line.** The receiving session does not execute it; it replies naming what is missing so the dispatcher reships the block whole.

The line's content is not this skill's to derive. It comes from the session-model-advisor skill's existing Step 3 (fetch ADR 0057 live) and Step 4 (classify the task), run against the JOB THIS DISPATCH HANDS OFF rather than against the session drafting the dispatch. **This skill carries no copy of that logic and no copy of ADR 0057's decision matrix.** If either turns up duplicated here, that is a doctrine violation, delete it and re-point to session-model-advisor.

Format, riding with the other envelope lines, above the fence:

RUN THIS SESSION AT: <model>, effort <level>

Name the level in ADR 0057's own vocabulary (`low`, `medium`, `high`, `xhigh`, `max`), verified fresh against current Claude Code documentation every time the line is written, never carried over from an earlier verification the same day. Which levels exist, and what each one means, is exactly the kind of vendor fact the doc-check standard exists to keep from going stale in a skill file.

**When a level has grown a same-looking UI sibling, name both and say which one to actually click.** Worked example, verified live 2026-08-10 against code.claude.com/docs/en/model-config: Claude Code's `/effort` picker grew an entry sitting at the strong end of the slider next to `max` for a Claude Code SETTING, not a separate or higher effort level. It sends `xhigh` plus gives Claude standing permission to orchestrate dynamic multi-agent workflows for substantive tasks, and it does not persist to `effortLevel` in settings.json the way `low`/`medium`/`high`/`xhigh` do. **Never spell that setting's name bare and contiguous in this file, in a dispatch block, or in any prose a session will read as a live prompt.** Live-confirmed 2026-08-10 (this lane's own incident, recorded in its ledger row): the bare word, typed anywhere in a message a Claude Code session receives, including inside a quoted worked example describing it, is read by the harness as the literal activation keyword and fires the real behavior, not merely describes it. Write it broken (`Ultra-code`) and point to code.claude.com/docs/en/workflows for the exact canonical spelling when someone actually needs to type it. A dispatch that means `xhigh` writes `xhigh`. A dispatch that means the orchestration behavior names it by its broken spelling, never lets the two get read as interchangeable just because they sit next to each other on the same picker, and never risks firing it by accident.

## Historical naming rules -- superseded by decision 0107

Ruled by Allison 2026-08-26, decision of record aura decisions/0074-naming-and-session-steward.md. SUPERSEDES the three-segment format of the 2026-08-07 ruling (which itself extended the 2026-08-04 lane tag rule, intake/2026-08-05-ruling-lane-tag-session-naming-rule.md). The capability ground shifted: Claude Code Desktop's native session-management tools let a session title itself and repair other sessions' titles (proven live 2026-08-25/26), so naming moved from a dispatch-side launch flag plus a manual repair path to a worker-side act at birth.

<!-- RULED-BY: aura/decisions/0091-allison-controlled-two-word-routing-names.md date:2026-09-07 -->
Amended 2026-09-07 by decision 0091 (ruled by Allison via Lock that, ruling of record aura decisions/0091-allison-controlled-two-word-routing-names.md), applied to this skill 2026-09-08. This SUPERSEDES the `<Table Name> - <Specific Job>` worker form below and its restatement under decision 0088 in mechanic 8. Every new WORKER visible session title is exactly two clear words identifying the job, no more and no fewer. Worker ownership and return identity ride in durable routing state, before registrar cutover the lane ledger row and the dispatch's CLAUDE HOME line, never encoded in the visible title. Every new TABLE NAME and every Allison-authorized Table rename is also exactly two clear words. Allison may rename an existing Table by explicit direction, the rename changes the authoritative name only, prior names stay historical aliases to the same Table and are never reused for another Table in the same ROOM, and only Allison authorizes a Table rename. Workers active before 2026-09-07 finish under their admitted titles and are never renamed mid-flight, and legacy Table and Chair names are never mass-renamed by AI. Historical text below is preserved unrewritten where it records the superseded form.

Every Claude Code worker name is exactly two clear words identifying the job:

```
<Two Word Job>
```

Superseded form, preserved for history only: `<Table Name> - <Specific Job>`. No room or table prefix; the owning table is carried in the lane ledger row and the CLAUDE HOME line, never in the title, so the room-token exception of decision 0074 is retired with the form that carried it. Job words are descriptive, never numbered merely because workers are sequential. Readable words throughout, never bare initialisms.

Examples: `Steward Build`. `Voice Tuning`. `Routing Simplification`.

Mechanics:

1. On Claude Code Desktop, the worker sets its own title at birth: its first management action is `set_session_title` with `session_id="self"` and the exact SESSION NAME from its dispatch. The tool's own success result is the birth verification (implementation detail adopted 2026-09-08, Startup Efficiency audit, no rule change); the last `custom-title` record in its own transcript is read only on a tool error, on actually observed drift, or as evidence to resolve a mismatch, never as a routine second confirmation. The native tool is searched for once; if absent, the worker reports that once and continues under the SESSION NAME line. The dispatch's SESSION NAME line stays authoritative (decision 0065, unchanged).
2. For CLI-only launches, the `claude -n "<full name>"` launch line remains the mechanism (`-n, --name` live-verified 2026-08-07 on 2.1.223); the worker reads its `custom-title` record once at first contact (the launch line wrote it and there is no tool result to trust) and self-repairs on mismatch.
3. The dispatching lane owns name consistency, and its ledger row in aura docs/estate/lanes.md records the same canonical name.
4. On mismatch or a missing title, the worker REPAIRS ITSELF through the native tool and reports the before and after. Routine `/rename` instructions to Allison are retired wherever the native tools exist; `/rename` survives only on surfaces without them. The pre-2026-08-26 claim that a session cannot rename itself (tracker #33165, #83543, #84041, #84587) is superseded by live product behavior.
5. Existing sessions are NOT cold-renamed. A pre-rule session gains its convention name the next time it is touched, via the Session Steward (evidence first, per the session-steward skill), never by sending Allison window hunting.
6. Registrar-governed worker admission (decision 0074 as amended 2026-08-30 by decision 0082, aura decisions/0082-registrar-model-amendment-to-decision-0074.md): the one-table-one-active-worker rule is replaced by admission on exact execution scope. A table may hold multiple active workers when their exact scopes do not conflict. A duplicate same-table same-title active or reserved worker is refused, and an exact execution-scope collision is refused. No work happens before an admitted registration, no ACTIVE worker record exists without confirmed external worker existence, stale never equals dead, and a scope releases only through an authorized terminal transition. Ownership is proven from lane state, dispatch, or transcript evidence, never inferred from a shared repo, branch, PR, or topic. Bridge until cutover (decision 0082, decision 0080 Section 24): the registrar does not exist yet, so until Allison rules the one cutover the installed one-active-worker practice continues to bind, a second concurrent implementation job still gets its own exactly named table first, and this pre-cutover discipline is an act a chair performs on behalf of its table rather than a repealed rule.
7. Room segment authority (decision 0077, 2026-08-26): the block-writer composes the `CLAUDE HOME` line's room segment from the dispatching room's own Project Instructions ROOM identity literal, never reconstructed from canon prose, ledger rows, or memory. The worker, which cannot read any Project's instructions, echoes the dispatched `CLAUDE HOME` line verbatim for the life of the session and never rebuilds the room segment from any other source. Amended 2026-08-30 (decision 0084, aura decisions/0084-registry-consumption-amendment-to-decision-0077.md): the table registry consumes, validates, carries, and points at that installed literal and never silently replaces it, the installed literal wins on any disagreement with the disagreement surfaced, and identity resolves through the registry so worker, lane, and execution-session identity can never override ROOM or TABLE.
8. Chair/worker title boundary (2026-09-04, decision 0088, ruling of record aura decisions/0088-chair-worker-boundary-and-title-parity.md). The worker is a temporary execution session dispatched from the table and is never the table's chair, even though the surface presents it as a session. Its carry-back returns to the table's chair, the authoritative home conversation the CLAUDE HOME line names, and that chair stays home while the worker executes. The chair's visible title is exactly the TABLE NAME and the worker's is exactly two clear words identifying the job (amended 2026-09-07 by decision 0091, ruling of record aura decisions/0091-allison-controlled-two-word-routing-names.md, superseding the `<Table Name> - <Specific Job>` form decision 0088 restated here), and no dispatch, steward action, or wrap ever retitles the chair to a worker's job or a worker to its table's name. The chair-title-equals-TABLE-NAME rule stands and consumes the two-word Table name.

## Historical: window-title rules -- superseded by decision 0107

Added 2026-07-28 after a live incident, and this is still why the parity rule exists. A Claude Code window displayed the title "Atlas bot token cleanup" while the session inside it was authoritatively "ember-audit," which it confirmed by its own envelope check. Allison nearly archived an active worker because of it. Drift is real, it is dangerous, and the cost is a live lane killed by mistake.

Amended 2026-08-07. The 2026-07-28 entry explained the drift by saying Claude Code cannot read or set its own window title. The READ half of that was superseded then: a session CAN read its own name, off its own transcript's `custom-title` record (live-verified 2026-08-07 on Claude Code 2.1.223; recipe in the pin skill, section 5).

Amended again 2026-08-26 (decision 0074). The SET half is now superseded too: on Claude Code Desktop a session CAN set its own title and other sessions' titles, through the native session-management tools, proven live 2026-08-25/26 with persistence verified on independent reread. Drift is now both detectable AND repairable by the session itself, with no human in the loop.

Consequences:

- The authoritative name is the one in the SESSION NAME line of the block that briefed the session, never the window title.
- A Desktop worker whose birth `set_session_title` call succeeded is verified by that tool result and does nothing more. A session with no successful title call of its own (a CLI launch, a pre-rule session, a continuation into an unnamed session) reads its name once at first contact; on mismatch it repairs itself through the native tool, trusts the repair's tool result, and reports the before and after. Transcript rereads are exception-only, for a tool error, actually observed drift, or evidence needed to resolve a mismatch (implementation detail adopted 2026-09-08, Startup Efficiency audit, no rule change). No `/rename` line goes to Allison where the native tools exist.
- Birth self-title is the actual fix (on Desktop, `set_session_title` self as the first management action; on CLI-only launches, `claude -n`). Exception-only self-verification is the safety net under it, never a routine second step.
- Never advise archiving or closing a session based on its window title alone. Confirm what work that session still holds first, from transcript and lane-state evidence (session-steward skill, identify before you classify).

## Historical: lane naming by surface -- superseded by decision 0107

Ruled by Allison 2026-08-03. Cowork and Claude.ai chat titles are auto-generated from conversation content and cannot be set by any session, tool, or API; live-verified 2026-08-03 when the auto-namer paraphrased a first message that opened with the exact intended lane name. Manually renaming Cowork chats to match a convention is retired as of this ruling. Manual renaming was a failure condition; the identity rule moves instead. Amended 2026-09-04 by decision 0088 (ruling of record aura decisions/0088-chair-worker-boundary-and-title-parity.md), superseding only the absolute. Retired means retired as a routine convention-matching habit. The one manual act that survives is a drift-driven repair of a chair's title to the exact TABLE NAME, at Birth, Rejoin, Reseat, or actually observed drift, because the chair title is a continuing parity invariant and a chat surface cannot repair its own.

The rule by surface:

- Cowork and Claude.ai chat lanes (tables, decisions 0066 and 0081). Amended 2026-08-30 by decisions 0081 and 0082, ruling of record aura decisions/0081-chair-model-amendment-to-decision-0066.md and aura decisions/0082-registrar-model-amendment-to-decision-0074.md: a table is the durable logical workstream and its authoritative home conversation is the chair seated at it, so canonical identity is the declared table name and never a chair's visible title or a chair's own assertion. Narrowed 2026-09-04 by decision 0088 (ruling of record aura decisions/0088-chair-worker-boundary-and-title-parity.md), superseding the broader reading that any conversation is a chair. A Claude Code worker session is never a chair. Chair authority arrives only through Birth, Rejoin, or Reseat, and a conversation holding none of those is Scratch, holds no table identity, owns no workers, and dispatches none. Table Birth is a deliberate declared act, not an automatic consequence of a first substantive turn: at deliberate Birth the chair declares `ROOM` and `TABLE NAME`; if the visible conversation title is not exactly that name, the surface hands Allison the exact required chair title, the bare TABLE NAME, and the name stands until Allison herself renames the Table by explicit direction (decision 0091, exactly two clear words, prior names kept as historical aliases to the same Table). Amended 2026-09-04 by decision 0088, superseding the birth-only limit. Chair title parity is a continuing invariant, so the exact title is handed to her again at Rejoin, at Reseat, and whenever drift is actually observed or reported, a surface that can read and set its own title maintains parity itself, and a title mismatch never changes the table's identity. Until the coordinated revision cutover of decision 0080 Section 17, ruled by Allison, the installed automatic birth-declaration wiring continues to bind as a pre-cutover act a chair performs on behalf of its table (decision 0082, bridge until cutover). No implementation dispatch leaves an unnamed or unconfirmed table. This retires the "near match is good enough" acceptance for tables. What does NOT return: routine, repeated, or unprompted chat rename requests stay banned, chat lanes still never get PARITY MISMATCH flags, and Table Birth is a single naming act, never a maintenance loop (the NAME is set at Birth and changes afterward only by Allison's explicit rename under decision 0091, never by AI and never by a drifted sidebar title, and the title mirror is repaired on observed drift, never polled). The kickoff-header-line identity rule of 2026-08-03/2026-08-07 remains the mechanism a dispatched kickoff uses to land the name (the name is still the first line, plain and alone, because titles cannot be set programmatically). Amended 2026-08-26 by decision 0077 (room identity literal): the Table Birth declaration is now TWO lines, `ROOM: <exact room identity>` above `TABLE NAME: <exact table name>` (two clear words, standing until Allison renames it, decision 0091). The exact ROOM string comes solely from that room's own Project Instructions ROOM identity literal, never reconstructed from canon prose, ledger rows, intake records, conversation memory, or any shared skill (this skill carries the ROOM value, it never owns one). Platform honesty rides with it: a chat surface cannot read its own visible title, so at birth it declares the exact intended TABLE NAME, states plainly that visible-title parity cannot be programmatically verified from that surface, and asks Allison for the glance and the exact-title rename if the visible title differs, at Birth and again on any observed or reported drift (decision 0088). No surface ever claims a title was inspected, matched, or fixed when it cannot know that.
- Claude Code sessions (workers). Exact-name parity stays enforced, and as of decision 0074 it is enforced by the worker itself: birth self-title via the native `set_session_title` tool (`session_id="self"`) whose success result is the verification, a one-time disk read only where no successful title call exists, and SELF-REPAIR on mismatch trusting the repair's tool result, transcript rereads exception-only (implementation detail adopted 2026-09-08, Startup Efficiency audit, no rule change). A PARITY MISMATCH on a Code lane resolves by the session (or the Session Steward cross-session) renaming it through the native tool, with evidence, never by handing Allison a `/rename` line where the native tools exist and never by Allison hunting windows to rename them cold. A Claude Code session is a worker, never a chair, whatever its title reads (decision 0088). Its title is exactly two clear words identifying the job (decision 0091, superseding the `<Table Name> - <Specific Job>` form), never its table's own name, and a worker whose title reads as its table's name is drift impersonating the chair, repaired to the two-word job form.

## Historical: session-name-first rule -- superseded by decision 0107

Added 2026-07-28 at Allison's instruction, rewritten 2026-08-07 under the launch-line ruling. This section governs blocks bound for Claude Code. Blocks bound for a chat conversation lead with the conversation name instead and never carry a SESSION line at all; see Chat Blocks Lead With The Conversation Name below.

The first line INSIDE every Claude Code paste block is still the session name, so the pasted prompt identifies its own lane in the transcript. Amended 2026-08-26 (decision 0074): the worker now names itself, so the in-block line is both the authority and the instruction.

**Inside the fence, the first line is the SESSION NAME header plus the self-title instruction.** Exact format:

SESSION NAME: Steward Build -- your first management action is setting this session's title to this exact name via the native session-management tool (set_session_title, session_id "self"). Search for the tool once. If it is present, its success result is your verification; if it is absent, say so once and continue under this name. Report the result, then execute the brief below.

Substitute the actual two-word worker title (decision 0091) for each block. The routing line above the fence still ships too. Outside the fence Allison reads where to paste; inside the fence the session learns what it is called and makes it so.

**For a Desktop dispatch, no launch line is needed and no rename hand step exists** (decision 0065 strengthened by 0074): the paste is the whole handoff. For a CLI-only launch the dispatch still ships `claude -n "<full name>"`, and the worker reads its `custom-title` record once at first contact, since no tool result exists to trust.

**For a NEW session the envelope also carries the `WORKTREE` line** (Worktree Isolation above): the isolated tree the session creates from a freshly fetched remote ref and works in, confirmed by absolute path in its first report. A spawning block without one is malformed and bounces home.

If the native session-management tools are unexpectedly absent at first contact, the worker reports that limitation plainly, continues under the authoritative SESSION NAME, and does not hand Allison a `/rename` line as the routine path (`/rename` survives only as the last-resort repair on surfaces without the tools). Absence is established by one tool search, never a retry loop (added 2026-09-08, Startup Efficiency audit; two workers that day spent three and four searches each on the same absent tool).

## Historical: hard naming-line enforcement -- superseded by decision 0107

<!-- RULED-BY: aura/intake/2026-08-11-ruling-naming-line-hard-enforcement.md date:2026-08-10 -->

Ruled by Allison 2026-08-10, ruling of record, aura intake/2026-08-11-ruling-naming-line-hard-enforcement.md. Same enforcement shape as Worktree Isolation and The Model And Effort Line above: a rule that exists but is not enforced at the dispatch chokepoint is a rule nobody can rely on.

Amended 2026-08-26 (decision 0074): what is hard-enforced is the NAME, not the launch flag. **A spawning block with no SESSION NAME line is malformed and bounces home, same as a block missing its `WORKTREE` or `MODEL AND EFFORT` line. The receiving session does not execute the brief, it reports what is missing so the dispatcher reships the block whole.** On Claude Code Desktop the worker fulfills the line by titling itself at birth through the native tool, so a Desktop dispatch carries no `claude -n` line and is well-formed without one. A CLI-only dispatch still ships the `claude -n` launch line, and a CLI spawning block without one is malformed as before.

Scoped to spawning (new-session) dispatch blocks only. Continuation-block behavior: a block routed to an EXISTING session never carries a launch line by design, and a drifted title there is a self-verify finding the session repairs itself through the native tool (or flags with the `/rename` line only on surfaces without the tools), then proceeds. A missing name on a spawning block is a malformed dispatch that bounces home unexecuted; a drifted title on a continuation block is repaired and worked through, never a reason to refuse the brief.

## Historical: chat-title seeding -- superseded by decision 0107

Ruled by Allison 2026-08-07, same lane as the naming and archive rulings. The section above governs blocks bound for Claude Code. This one governs blocks bound for a chat conversation in the Claude app or Cowork, and the two rules do not overlap at any point.

The live failure that forced it: a lane-spawn block buried the conversation name mid-block and opened with mission text, so the app auto-titled the chat off the mission and the lane was born carrying two names, the one in the ledger and the one Allison could see in her sidebar.

Chat conversation titles cannot be set programmatically. The app auto-titles from the first message and no session, tool, or API can override it (live-verified 2026-08-03, reconfirmed 2026-08-07). The only lever the block-writer has is what the first message says first.

**The first line inside a chat block is the conversation name, plain and alone.** No label, no date suffix, no "kickoff" word, no envelope line above it, no mission text above it. The envelope follows on the next lines. Full block anatomy lives in the lane-spawn skill, "The spawn pair."

**Vocabulary lock.** A chat block heads its envelope `CONVERSATION:`. A Code block heads its envelope `SESSION:`. A chat block carrying a `SESSION:` line is malformed and gets rewritten before it ships. `WORKER SESSION:` inside a chat kickoff is a pointer to the Code lane that will carry back, not the block's own header, and is correct. `CLAUDE HOME:` inside a Code block is the same kind of pointer, and is unchanged.

**Near-match titles are NOT accepted for a table's chair** (superseded 2026-08-26 by decision 0074's Table Birth and restated 2026-09-04 under decision 0088). Chat lane identity is still the declared table name and never the displayed title, so a mismatched title never changes identity. The chair's visible title is a navigation mirror that must read exactly the TABLE NAME, so a chat titled "Ember Rail Repair Plan" for a table named "Ember Rail Repair" is drift, and it is repaired to the exact name rather than left alone. Leading with the name in the kickoff is how the auto-titler is given the right material, and the parity rule under Lane Identity By Surface is what keeps it right afterward.

**No routine rename instruction ever reaches Allison for a chat.** Not `/rename`, which remains a Claude Code repair only, not an unprompted "please retitle this," not a parenthetical suggestion, and never on a schedule. Manual chat renaming as a maintenance habit was retired as a failure condition by the 2026-08-03 identity ruling and stays retired. What decision 0088 requires instead (2026-09-04, superseding the never-asked absolute that stood here) is drift repair. Where only Allison can rename a chair, the surface hands her the exact required chair title, the bare TABLE NAME, at Birth, at Rejoin, at Reseat, and whenever drift is actually observed or reported, so the chair stays human-locatable. Where the surface can read and set its own title, it maintains parity itself and she is not involved. A manual visible-title rename alone, Allison's own included, never changes the TABLE NAME, the table's identity, or the ledger's record of it, and the ledger never follows a retitled sidebar (decision 0088, ruling of record aura decisions/0088-chair-worker-boundary-and-title-parity.md, superseding the her-name-wins sentence that stood here from the 2026-08-07 chat-naming rule). A differing chair title is drift, repaired back to the exact TABLE NAME. A genuinely different durable mission gets a different table by deliberate Birth, never by renaming a sidebar title.

Routing line for a chat destination follows the same shape as the Code one, surface first:

PASTE INTO: Claude app, new conversation named "Ember Rail Repair"

PASTE INTO: Cowork, existing conversation "Ember Rail Repair"

## The Hand-Off Choreography: Pin Fires AFTER the Paste Confirmation

Corrected 2026-07-28 after a live miss (the pin was fired alongside the block instead of after Allison's confirmation). This section now matches the operating-doctrine pin rule exactly; if they ever seem to disagree, the operating-doctrine pin rule wins.

The order, every hand-off, every session, every project:

1. The hand-off response carries: the routing line, the paste block, and one plain-prose sentence naming what we will be waiting for once she pastes. It does NOT solicit a paste confirmation (pin v4.2, ruled 2026-08-03: nothing ever asks her to say pasted). NO pin yet.
2. Allison pastes and, if she chooses, volunteers a confirmation (pasted, done, OK, or similar). If she says nothing, no pin fires and that is correct.
3. ONLY THEN the pin fires: the pin marker (pin skill format, fresh real timestamp from TZ=America/Chicago date "+%Y-%m-%d %H:%M %Z", never guessed or reused) plus one sentence restating what we are waiting for and what happens next.

The pin is the bookmark of the moment the baton actually left her hands, which is why it cannot exist before her confirmation.

Precedence notes so the rules do not fight each other:

- The pin marker is a bookmark, not a paste block. It does NOT count against the one-block-per-response rule, and it is exempt from the nothing-fenced-but-Code rule. It is the only other thing that may ever be fenced.
- The pin skill's rule that the marker is the entire response applies only when Allison manually invokes /pin. Confirmation-triggered pins may ride in a response that also continues other work.

## The Session Gives The Archive Verdict

<!-- RULED-BY: aura/intake/2026-08-07-ruling-archive-verdict-returns-to-code-sessions.md date:2026-08-07 -->
<!-- Restores and generalizes a rule Allison first ruled 2026-07-27, struck without disclosure 2026-08-07 morning, and re-ruled the same afternoon: aura/intake/2026-07-27-ruling-code-session-close-includes-safe-to-archive.md date:2026-07-27 status:superseded-and-restored -->

Re-ruled by Allison 2026-08-07 evening in the Estate Brain Door Phase B Code session, superseding the same-date "Archive Authority Belongs To The Home Conversation" ruling. Her reason, recorded: the session must tell her whether it is okay to archive, determine whether something is open, and say whether a closeout or a wrap is needed, because sessions that cannot say whether they are done pile up, and too many open sessions is the real failure.

**`SESSION STATUS: carry-back delivered, awaiting verification at home.` is RETIRED and never written again.** Every carry-back ends with one of the four verdict lines from `behavior-defaults.md`: Waiting on you, Still working, SAFE TO ARCHIVE with evidence, or NOT safe to archive with the one closing move named.

<!-- RULED-BY: aura/intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md date:2026-09-01 -->
**SAFE TO ARCHIVE is a verified claim, never a phrase.** Issued only after all FOUR verify live in the same turn: `git status` clean and pushed on every repo the session touched; the session record, wrap, or closeout note written and pushed when doctrine requires one; every open wait re-lodged in the lane ledger's waiting-on column with its named condition and stale date, so nothing dies with the archive; and, added 2026-09-03 (ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md, delivered in session-steward v1.3 section 7A), **no monitor, check-in, subscription, scheduled wakeup, or background agent the session owns is still running**, each one released and confirmed released rather than assumed finished. The evidence rides in the line itself, and background activity is stated explicitly as NONE, never implied by omission. A worker that cannot stop something it owns names it and earns NOT safe to archive instead. Anything it does not own, an estate rail or another lane's work, is left running and said so.

**NOT safe means the session diagnoses AND prescribes.** It names exactly what is open and the single move that closes it: /session-wrap when chat-only decisions or flags are unrecorded, /session-closeout when shipped work has no handoff note on main, or the named open action otherwise. Never leave Allison to work out which close a session needs.

**What stays with the home conversation:** the archive click itself, and the ledger flip. Home may still verify a verdict's claims against commits, and a hold still names its next block ("hold it open just in case" is not a call; it is a lane leaking). When home archives, it flips that lane's row to `archived` in aura `docs/estate/lanes.md` BEFORE dispatching anything further, and no dispatch block is ever written against a session whose row reads `archived`; that lane is gone, spawn a new one.

**Default is archive.** Sessions are cheap and deterministically named, so spawn freely rather than hoarding a session because it might be useful later. A correctly named session is trivially reproducible; a stale open lane is not free, and the verdict rule exists precisely so stale open lanes stop accumulating.

Sessions born before this re-ruling follow it from their next response. No cold sweep, no retroactive rewriting of past carry-backs.

Precedence: where this and any older SESSION STATUS wording disagree (the pin skill's carry-back template, the user-global close-of-turn rule, `behavior-defaults.md`), this re-ruling wins and the older wording is corrected to match. All three were corrected in the same pass on 2026-08-07 evening (pin v4.5, behavior-defaults, user-global CLAUDE.md, doctrine repo cf5d97e).

### The Earned Verdict Line

<!-- RULED-BY: aura/intake/2026-08-07-ruling-earned-verdict-line-on-carry-backs.md date:2026-08-07 -->

Amended by Allison 2026-08-07 (Aura / Code Rule Fix lane). This amends the archive-verdict re-ruling above; it does not replace it. **Every Code session carry-back ends with the standing SESSION STATUS line PLUS one earned verdict line, and the verdict line is the carry-back's last line.** Exactly two verdicts exist:

- `VERDICT: RECOMMEND ARCHIVE -- all pushed, nothing pending on Allison's side.` Permitted ONLY when the session verifies its checklist live in the same turn: every commit pushed, the whole brief executed, nothing gated or held open, no deliverable still owed. A bare safe-to-archive with no checklist behind it stays banned.
- `VERDICT: RECOMMEND HOLD OPEN, waiting on <the one named thing>.` The verdict every other state earns. One named thing, never a list; if several things are open, name the one that unblocks the rest.

Archive authority stays with the home conversation and home's GitHub grading remains the backstop, but Allison may archive on the spot on a RECOMMEND ARCHIVE without waiting for home. The verdict line is earned, never decorative: RECOMMEND ARCHIVE with an unverified checklist is the same failure the SAFE TO ARCHIVE evidence rule exists to prevent, stated at the moment Allison actually makes the call.

### BUILD BLOCKERS and OUTCOME BLOCKERS: Two Lines, Never One

Amended 2026-08-30, ruled by Allison; ruling of record: aura decisions/0083-sequencing-without-maximalism-amendment-to-decision-0075.md (an explicit amendment to decision 0075); advisory of record aura intake/2026-08-30-sequencing-without-maximalism-corrected-final-advisory-super.md.

Every carry-back reports BUILD BLOCKERS and OUTCOME BLOCKERS as two separate lines, riding immediately before the SESSION STATUS line. No surface ever reports a single BLOCKING line, and every disposition or completion list that would have carried one carries the BUILD and OUTCOME pair instead. "None" is a valid value and is stated explicitly, never implied by omission.

- BUILD BLOCKERS prevent the implementation from being built. They are owned by the active worker.
- OUTCOME BLOCKERS prevent Allison's stated result from functioning end to end, or prevent required acceptance proof, blocking mission completion even when the build is finished. Safe, bounded, reversible, clearly-owned fixes required for the current outcome are handled in place; fixes that materially change architecture, authority, security, cost, or system-of-record ownership go to Allison before implementation.

The worker's verdict speaks only to its own surface-specific job, never to the home table's objective. A worker closes when its job is finished and successor work is durably handed off; whether the home table's mission is achieved is judged only by the home table's own closeout (the session-wrap close-or-continue verdict), never imported from a worker's verdict. A worker carry-back that pronounces on the home objective is malformed on that line, exactly as a table verdict spoken in worker vocabulary is void under decision 0075.

## The Lane Ledger: Row At Dispatch, Update At Carry-Back

Added 2026-08-03. The estate-wide lane ledger lives at `docs/estate/lanes.md` in the aura repo. It is the single file that answers "what Claude Code sessions exist, what does each belong to, and what is each waiting on" from any surface; any project reads it through its aura connection.

The habit, every hand-off:

1. At dispatch, when a paste block is handed to Allison, the issuing Cowork chat's block-writer appends or updates the lane's row in the ledger: canonical session name (the two-word worker title per decision 0091, the same string the block's SESSION NAME line carries; the owning table is recorded in the Cowork home cell, never in the title), window title as shown in the Code sessions list plus, in prose in that same cell, the stable Desktop sessionId once known (a worker that self-titles at birth reads parity-clean on its own first-contact verify; a PARITY MISMATCH resolves by self or cross-session rename through the Session Steward, never by a rename hand step), Cowork home (Claude project / table, named at Table Birth and renamed only by Allison's explicit direction under decision 0091, prior names kept as historical aliases), machine, the worktree named in the dispatch (per Worktree Isolation above, so the next dispatcher can see which trees are occupied), status, waiting-on, last-updated date. The waiting-on statement this skill already requires with every hand-off is the same text that goes in the row -- write it once, use it in both places. A dispatch that creates a CLOUD worker records the owning table and available stable identifier in the row at creation time, unconditionally (decision 0074, cloud registration): cloud sessions are invisible to local Desktop session lists, so an unregistered cloud worker is unrecoverable later.
2. At carry-back receipt, the row updates to the new status (running / waiting-on-Allison / waiting-on-carry-back / archived / owned-elsewhere). `complete-safe-to-archive` is retired as of 2026-08-07; only the home conversation writes `archived`, as one motion with its archive call.
3. Append and update rows, never delete. Completed lanes move to the ledger's Completed section rather than vanishing, so the archive decision stays visible.
4. Rule 5 applies: rows are only as certain as their evidence. A lane whose home nobody has named stays needs-Allison; never invent a home for it.

A Code session that completes its carry-back updates its own row to `waiting-on-carry-back`, with the full report, in the same push when it already has aura write access; otherwise the home updates it on receipt (root CLAUDE.md delivery protocol). It never writes `archived` into its own row: that is the home conversation's call and the home conversation's write.

<!-- RULED-BY: aura/intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md date:2026-09-01 -->
**The archive and the flip are one motion, added 2026-09-03** (ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md, on live evidence that finished workers stayed machine-visible as `waiting-on-carry-back`, one of them after Allison had physically archived the session). Home does not archive and then flip the row later; the flip completes the same close. A carry-back recommending archive says plainly that its row still reads its pre-archive status and will be flipped with the click, so the owed write is visible rather than assumed. **A row that keeps advertising an active wait for a worker known to be finished is a lie the ledger is telling**, and it is reconciled on proven evidence at the next touch of that lane under session-steward v1.3 section 7, never by a sweeper and never by leaving it for Allison to spot.

Write mechanics for the ledger file itself, added 2026-08-05 per Allison's ruling of 2026-08-04 after the second ledger regression (a stale-base full-file write erased three rows of newer state before the owning lanes healed it): every write to `docs/estate/lanes.md` obeys the shared-canonical-file-writes directive, canonical at aura `docs/directives/shared-canonical-file-writes.md`. In one breath, fresh read immediately before the write, blob-SHA compare-and-swap on any contents-API write, post-write diff check that no other lane's rows changed, git-based writers (Claude Code) preferred for this hot file, and a chat-surface writer that bounces twice on the SHA guard stops racing and routes the row verbatim through an intake handoff note for the next git-based writer to fold in. The directive also carries Allison's ordered build of the Estate Brain ledger-row tool, which retires whole-file writes once it ships.

## One Block Per Response

Added 2026-07-27 at Allison's instruction: "I can't have you giving me two at a time."

Exactly one paste block per response. Never two, never a "then once that lands" second block, never a block plus a queued follow-up block. (The pin marker is a bookmark, not a block, and does not count.)

If the work needs several steps, ship step one only, wait for the result, then ship step two. Sequencing dependencies are the assistant's job to hold, not Allison's job to keep straight while scrolling.

Prose describing what comes later is fine and brief. A second fenced paste block is not.

One named exception, added 2026-08-07 with the staged-kickoff ruling: a session wrap's staged kickoff set (session-wrap skill v1.3, step 4). Those blocks are a menu Allison draws from at her own tempo, not a sequence of dependent steps, and the dependency-sequencing burden this rule protects her from does not exist among them. Every block in the set still carries its own destination label and conversation name outside the fence. This is the only exception; it does not generalize to "several unrelated blocks are fine," and it never applies outside a wrap.

## What May Never Go Inside A Code Fence

Added 2026-07-27 after a live failure: a connector URL was placed in a code fence and Allison pasted it into a terminal, where zsh threw "no such file or directory."

In this workflow a code fence carries one meaning to Allison: paste this into Claude Code or a terminal. The only exception is the pin marker defined above. Nothing else may be fenced.

Never fence:

- URLs meant for a browser (connector endpoints, dashboards, sign-in links, docs)
- Values meant to be typed into a settings field or a web form
- Anything destined for 1Password, claude.ai settings, an admin panel, or any GUI

Write those inline in prose with the destination named first, for example: add it in claude.ai, Settings, Connectors, Add custom connector, using mcp.firecrawl.dev/v2/mcp-oauth

Fence only what a terminal or a Claude Code session will actually consume, plus the pin marker. If it is not going into a shell or a Code session and it is not a pin, it does not get a fence.

## Reading Versions From The Right Place

Added 2026-07-27 after a live failure: a doctrine version bump was specified as v2.1 based on a plugin cache mirror reading v2.0, when canonical was already at v2.2 and the correct bump was v2.3.

Never state or prescribe a version number from a plugin cache, a loaded skill copy, or any mirror. Those lag canonical. Read canonical in the repo, or have Claude Code read it and report back. If only a mirror was read, say which copy was read and that it may lag.

## Both Shelves: One Pass Serves Both Mount Surfaces

Ruled by Allison 2026-08-07. Several skills ride two mount surfaces at once, a standalone claude.ai skill copy and a copy inside the operating-doctrine plugin bundle. pin, code-block-routing, and lane-spawn all sit on both shelves today. The Deployed Copy Content Check of 2026-08-07 verified the two surfaces byte-identical, and that check is the reason the gap was visible: nothing in canon forced a future pass to serve both, so one single-shelf delivery would have opened silent drift between two copies Allison believes are the same rule.

**Any pass that touches a skill carried by the operating-doctrine plugin serves BOTH mount surfaces in that same pass.** A pass that serves one and mentions the other is not finished; it is a drift event with a note attached.

**The two shelves do not load the same way, and treating them as one delivery is the mistake this section was born correcting.** Corrected the same evening it was written, after the first delivery under it failed live: a plugin bundle zip was handed to Allison for the claude.ai Skills upload and was rejected with "Zip must contain exactly one top-level folder. Currently there are 2" and "Zip must contain exactly one SKILL.md file. Currently there are 8." The rejection was correct product behavior, not a build defect. Verified live 2026-08-07 against support.claude.com (how to create custom skills) and code.claude.com/docs/en/plugins plus /docs/en/discover-plugins.

**Shelf one, the standalone claude.ai skill. This one IS a zip upload.** The upload requires EXACTLY one top-level folder and EXACTLY one SKILL.md inside it. Build `<skill-name>/SKILL.md` and nothing else at the top level. It lands in `~/Desktop/Claude Skill Zips` per Rule 0 of `rules/file-delivery.md`, and Allison uploads it by hand because no API path exists for it.

**Shelf two, the plugin bundle. This one is NEVER a zip upload.** Plugins load from a marketplace git repository, not from an upload dialog; there is no claude.ai screen that accepts a plugin bundle zip, and a bundle can never satisfy the one-folder one-SKILL.md rule the Skills upload enforces. The estate's marketplace is the `expert-partners` entry pointing at the GitHub repo `ExpertPartners/expert-partners-skills`. Delivering this shelf means pushing to `origin/main` and bumping the version so the marketplace serves the update. Nothing goes on the Desktop for it, and handing Allison a bundle zip to upload is a category error that costs her a failed trip.

Mechanics:

1. **The plugin version bump is TWO files, not one.** `plugins/<plugin-name>/.claude-plugin/plugin.json` AND the matching entry in the repo-root `.claude-plugin/marketplace.json`. Bumping only the manifest leaves the marketplace advertising the old version, so installed copies never see the update and the shelf silently stays stale. Both numbers are read from canonical per Reading Versions From The Right Place above, never from a cache mirror, and they must agree.
2. **Content is blob-verified against `origin/main` before anything is called delivered.** Every SKILL.md hashes with `git hash-object` to the same blob SHA that `git rev-parse origin/main:<path>` reports. Build the standalone zip from `git archive origin/main`, never from a working tree, because a zip of unpushed work is a zip of something that does not exist yet.
3. **The carry-back names what each shelf actually got.** For the standalone shelf, the exact zip filename with its archive SHA and its Desktop path. For the plugin shelf, the commit on `origin/main`, both version numbers, and the fact that no upload is owed. Going quiet on either shelf is the failure this rule exists to remove.
4. The rule keys on the plugin's carrying, not on how the pass started. A pass that set out to touch only the standalone copy still owes the plugin shelf, because the plugin copy is the one that governs (skill-map standing flag, plugin copy wins).
5. Skills carried by the plugin with no standalone claude.ai copy owe only the plugin shelf, and the carry-back says so plainly rather than leaving Allison hunting for a second file that was never coming.
6. A plugin bundle zip is built ONLY when something actually consumes one: `claude --plugin-dir ./bundle.zip` for local testing, or `--plugin-url` for a hosted archive. Those are development paths. Such a zip never goes to `~/Desktop/Claude Skill Zips`, because that folder means "Allison uploads this" and she cannot.
7. **The two-file bump is VERIFIED, not remembered.** `claude plugin validate <marketplace-repo-root>` checks that every plugin manifest agrees with its enclosing marketplace entry, and `claude plugin tag` validates the same agreement before cutting a release tag. Run the validate before calling the plugin shelf delivered; a mechanical check is what turns mechanic 1 from a thing a pass can forget into a thing a pass cannot ship without.
8. **The plugin shelf is delivered by CLI, never by a hand step.** After the push, `claude plugin marketplace update <marketplace>` refreshes the catalog and `claude plugin update <plugin>@<marketplace>` moves the installed copy to the new version, reporting the exact old-to-new transition. Third-party marketplaces have auto-update OFF by default, so without these two commands an installed copy sits on the old version indefinitely while canonical moves on. Both were live-verified 2026-08-07 on Claude Code 2.1.223, taking operating-doctrine from 2.33.0 to 2.35.0 with no upload and no action from Allison. A session that pushes and stops has updated the catalog, not the shelf.

Precedence: this section is the delivery half of Reading Versions From The Right Place. That rule stops a wrong version from being SPOKEN; this one stops a right version from reaching only one shelf, and stops a right artifact from being sent to a door that does not open.

## Links Are Evidence: Never Construct A URL

Added 2026-08-04 after a live recurrence (Marketing Canon lane: a Code session emitted constructed claude.ai links in its carry-backs, was corrected at gate one, saved the rule to its own session memory, and still emitted constructed links at closeout; session memory is a notebook, this skill is the rulebook, so the rule lives here).

Every carry-back, report, or block that points at a file cites the repo path plus the commit hash, or a URL actually verified to resolve. Never construct a URL by gluing a path onto a guessed address. A session that cannot verify a URL gives the path and hash instead. This rule governs both directions of the hand-off, blocks handed to Allison and carry-backs handed home. The deliverable-link skill's every-deliverable-gets-a-link rule is satisfied by a verified link or by path plus hash, never by an invented one.

Scope widened 2026-08-07 (decision 9c of the Estate Brain Door Phase B record, wording checked against the ruling in the same pass). The rule covers EVERY URL a carry-back carries, not only the ones that point at files. The 2026-08-05 carry-back that forced the check shipped two broken claude.ai links, which were not file pointers at all. A conversation link, a dashboard link, a board link, a doc link, and a file link are all held to the same test: it resolved when you tried it, or it does not ship. Links are evidence, and evidence is the thing you actually looked at.

## The Hand-Step URL Rule: Give Her The Address, Not Directions

Ruled by Allison 2026-08-07; decision 9a of the Estate Brain Door Phase B record (aura intake/2026-08-05-session-record-estate-brain-door-phase-b-lane.md). The live proof: a manifest page a session needed Allison's eyes on sat inside a browser pane for hours, because the session handed over a navigation path instead of an address.

When a session needs Allison's hands on a web page, it hands her the full URL, complete and clickable, for her own browser. Never a navigation path. Never "go to Settings, then Connectors, then scroll to." Never a page left waiting in a Browser pane on the assumption she will find it there. The Browser pane is optional garnish, useful to the session for its own verification, never the delivery mechanism for a step that is hers.

Mechanics:

1. The URL is written inline in prose with the destination named first, never fenced (see What May Never Go Inside A Code Fence). Naming the destination and giving the full address are one act, not alternatives.
2. The URL is verified to resolve before it ships, per Links Are Evidence above. A hand step pointed at a guessed address costs her the trip.
3. Directions may ride ALONGSIDE the URL when the target is a control inside a long page ("open this, then the grant is the third row"). They never ride instead of it.
4. One hand step, one URL, named once. The Ruling Cadence in the operating-doctrine already requires hands-only actions to be named explicitly with the direct URL; this section is that requirement's mechanics.

Known session names (update this list via skill overwrite as new ones appear):

- "Ember audit": the Ember estate audit and rebuild lane, running Claude Code locally on the M2 Mac mini (Ember's Mac mini, Embers-Mac-mini.local, Mac14,12 Apple M2 Pro, login account allison). Authoritative session name is ember-audit even when the window title has drifted. Created 2026-07-28. Holds the Ember source capture that closed ADR 0031 (commit eebd88a99, 65 previously unversioned production files), the Telegram rotation to bot @Ember_HQBot 8234710582, the Slack rotation on app A0AG008U1V5, the ADR 0029 correction (OpenCLAW is NOT decommissioned; gateway 2026.5.12 runs alongside Claude Agent SDK 0.2.87 and serves Ember's Slack surface), the credential blast-radius reduction across ember_agent.py and gateway.env, and the 1Password-versus-production reconciliation. Route all Ember host, rail, credential-reconciliation, and observability work here.
- "Canon Doc Sync": the canonical lane for pushing promoted canon docs and rule changes into the partnersync repo (created 2026-07-28, first promotion commit 25126c3, Doc 00). Canon markdown lives at project-knowledge/ top level in ExpertPartners/partnersync; Doc 00 is project-knowledge/00-How-to-Use-This-Project.md. ALL future canon promotions route here as an existing session. Works together with the canon-sync-protocol skill.
- "n8n Notion Wiring": the Layer 2 build lane on the partnersync-automation-backend repo (registered 2026-07-28 from Allison's carry-back). Holds the certified error logger PS-ErrorLog-Notify-v1 (live, version 6754f1de, renaming to CORE-Error-Logger-Notify-v1), the S6-Instant gated draft PS-S6Instant-EPICActive-v1 (ARlSztdu5a5DrxqP), the local repo clone at ~/Claude/projects/partnersync-automation-backend/, and the open gates (instance-wide error-workflow designation APPROVED ON by Allison 2026-07-28, fires next session; EP location PIT plus Google Sheets OAuth for S6 certification). Route all n8n workflow build and certification work here.
- "Email Setup Handoff": the email deliverability workstream (sender config, DNS fixes, EPIC and Expert Partners email setup). Also referred to earlier as the Legacy500 Pivot to GHL Kickoff thread.
- "Firecrawl onboarding": the live Firecrawl and doctrine session on the aura repo. Holds the key rotation record (rotated 2026-07-27 to the fc-344c3 prefix key), the headersHelper fix routing op through /bin/zsh -c, the config backups, the two-lane doctrine (Claude Code uses the Bearer lane, OAuth is the CoWork and app lane), the operating-doctrine State Check amendment shipped as v2.3, and the credential-helper class audit. This is the single lane for all Firecrawl and doctrine work.
- "Firecrawl MCP OAuth": a second Firecrawl session opened 2026-07-27, read-only and idle. Superseded by "Firecrawl onboarding" and should be closed rather than reused, since its context predates the doctrine edits.

Archived lanes, do not route to these:

- "Credential Rotation" and its Cowork conversation: archived by Allison 2026-07-28 after she completed all rotations herself. Its output files survive on disk at ~/Claude/projects/PartnerSync Operations Engineer/2026-07-28-github-repo-audit-secret-scan.md and 2026-07-28-session-summary-github-audit-and-credential-consolidation.md. Credential reconciliation ownership moved to "Ember audit."
