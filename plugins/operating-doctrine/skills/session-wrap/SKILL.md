---
name: session-wrap
description: "Closes out and hands off work on every surface. Produces and verifies the session record, continuity note, required durable-state updates, staged follow-ups, final memory sweep, canon-sync trigger, and evidence-based close-or-continue verdict. It also evaluates a finite mission when acceptance evidence lands."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Adopted into canonical 2026-08-05 (Skill Map Rulings lane, add-on brief note 4):
# estate-wide skill, canonical home verified as having been aura .claude/skills only,
# adopted here per the ruling 9 pattern. The aura copy is now a deployed copy,
# recorded in the extractor's DECLARED_DUPLICATES. Content copied verbatim.
tier: plugin
zone: routing
status: live
subtitle: "the one canonical session close-out"
---

# Session Wrap -- v1.21 (2026-10-24)

<!-- RULED-BY: aura/decisions/0107-retire-routing-naming-ceremony.md date:2026-10-12 superseded naming text removed -->

Current handoff and reporting authority: follow the HQ Rulebook section Handoffs between AIs. The receiving AI uses job_create or job_claim, job_status shows ownership, and this wrap files its report as a job_finish summary with a result link. Code jobs travel as GitHub issues labeled job. Section 5A's protected lines are reserved for PR #104 and require the listed post-merge follow-up; do not use them to create a second work record.

## Historical amendments, not current handoff instructions

v1.21 amendment 2026-10-24 (Decision Log 2026-10-24, Archiving is gated on the paper trail, and an orphan sweep catches what slips, Allison's words, love this whole thing, yes, let's go; live HQ Rulebook Session lifecycle section): the archive gate. A finished Claude Code or Codex session archives itself only after its report row is written in Handoffs and read back, and its incoming row is marked Done with a pointer to that report. The mail box in chat is only the bell, never the record. A session that cannot reach the Handoffs tab stays open and says so. Section 5A is amended, and a report that lives only in chat no longer counts as finished. Adds to v1.20. The live Rulebook wins wherever this skill differs.

v1.20 amendment 2026-10-24 (Decision Log 2026-10-24, Finished code sessions wrap and archive themselves, Allison's words, that's a big one, let's make that happen for sure; live HQ Rulebook Session lifecycle section): a finished Claude Code or Codex session runs its wrap duties on its own without waiting for Allison to say wrap, then says SAFE TO ARCHIVE and archives itself, silently. Both apps can archive their own sessions, Codex's confirmed by Codex, Session Steward on 2026-10-24, so the earlier hedge about Codex is removed. Section 0 and section 5A are amended. This replaces the wait for Allison's wrap in Decision Log 2026-10-23, Code session states are ACTIVE, WAITING, READY TO WRAP, and ARCHIVE, and in 2026-10-21, Definition of WRAP for coding sessions. Sessions still waiting on Allison or another AI stay open, and Allison only hears about a session when it is waiting on her. The live Rulebook wins wherever this skill differs.

v1.19 amendment 2026-10-22 (HQ Rulebook Session lifecycle section and Decision Log 2026-10-22, Code sessions wrap and archive themselves, never ask Allison, confirmed by Allison in this change's own session; disclosure of record intake/2026-10-22-disclosure-rulebook-sync-formatting-tabs-session-wrap.md): a finished Claude Code or Codex session wraps and archives itself where the app allows and never asks Allison whether it is ready. New section 5A. This supersedes any wording here or in session-steward that waits on Allison's agreement before a finished code session archives. The live Rulebook wins wherever this skill differs.



v1.15 amendment 2026-10-08 (ruling of record aura intake/2026-10-08-ruling-claude-code-location-and-remove-lock-that.md, under decision 0101): the `Lock that` phrase gate is removed from step 3A routing and Table Closeout Gate obligation One. A clear decision is saved as made, and the gate now verifies those saves. Every other obligation is unchanged.

v1.14 filing correction 2026-09-23 (Allison's Report Filing authorization, aura intake/2026-09-23-report-filing-batch-dispatch.md): routine session records and continuity notes stay in their approved private repository home, with publication to the authoritative branch and a verified continuation read. An intake failure is preserved in the owning repo's approved private recovery or staging location and reported as unpublished; it never creates a Desktop or Downloads copy or a manual-only handoff. This applies the owner rule at `~/.claude/rules/file-delivery.md` and does not create a second filing rule. The Table Closeout Gate and other lifecycle rulings are unchanged.

v1.12 amendment 2026-09-04 (Immediate Pain Controls campaign, source expert-partners-skills issues #15 and #16): the wrap gains its FINAL UNCAPTURED-MEMORY SWEEP, new step 3A. The failure it kills: a wrap could push a record and a continuity note and still leave a durable item alive only in the transcript, because nothing in the protocol ever asked the question "is anything here owed a home it has not been given". The sweep runs the `estate-memory-router` classifier over the closing session and routes whatever qualifies into the mechanism that already owns it, which for a future obligation is `remember-this`. Deliberately NOT a seventh Table Closeout Gate obligation: decision 0075 ruled exactly six, and adding one here would amend a ruled decision without Allison. It is a step in the canonical-push flow instead, where an unverified write already blocks the wrap. Nothing here creates a memory store, a registry, a sweeper, a daemon, or a second source of truth, and nothing here opens a registrar or routing-state write; decision 0080 Section 24 and decision 0082's bridge clause continue to bind unchanged.

v1.11 amendment 2026-09-03 (ruled by Allison 2026-09-01, the founder-load table-lifecycle amendment, ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md, source aura issue #200, with the mission contract delivered in lane-spawn v1.7 and worker terminalization in session-steward v1.3): the wrap stops waiting to be asked. Three things land. One, PROACTIVE TERMINALITY, new section 0A: a mission table evaluates its own terminality the moment acceptance evidence arrives, with no words from Allison, and either says Mission achieved and recommends closure or names the ONE blocking acceptance item. Two, NO SEQUELS, new section 4B: a table whose mission is achieved never silently extends itself over adjacent work, and a completed historical chair never decides its own future mission. Three, DURABLE LIVENESS, folded into step 3 and gate obligation three: the archive motion and the ledger flip are one lifecycle close, so a worker that has actually been archived stops advertising itself as an active wait. Scratch and standing-subject conversations are exempt from all three and are never nagged to archive because a topic ended. Nothing here creates a new closeout system, a sweeper, a registry, or a second source of truth, and nothing here opens a registrar or a routing-state write; decision 0082's bridge clause and decision 0080 Section 24 continue to bind unchanged. The live failures that forced it, all 2026-09-01 to 2026-09-03: the Shared History Bridge table stayed conversationally open and began absorbing adjacent work after its own records said its mission was accepted complete; the Final Reconciliation worker kept re-arming hourly check-ins and PR subscriptions after its substantive work was done; and lanes.md still advertised two finished workers as waiting-on-carry-back after their work closed, one of them after Allison had physically archived it.

v1.10 amendment 2026-08-31 (delivering decision 0075, ruling of record aura decisions/0075-table-closeout-gate-and-worker-only-archive-vocabulary.md, ruled by Allison 2026-08-26; implementation authorized by decision 0080 Section 28, which held this delivery defect as IMPORTANT BUT NOT BLOCKING): the Table Closeout Gate lands here, as step 4A, together with decision 0075's two-object-type scope correction and its write-capability boundary. Version numbering, closing the open thread the v1.9 note names: decision 0075 reserved v1.8 for this gate, decision 0083's amendment landed at v1.9 on 2026-08-30 while the gate was still undelivered and deliberately declined to take its number, so the gate lands at v1.10 and v1.8 stands as a reserved number that was never published. Nothing in the v1.9 amendment is altered, absorbed, or renumbered by this delivery, and decision 0083's extension of Mission achieved is consumed exactly as written. Scope correction: this skill closes two object types and never conflates them, estate tables on supported conversational surfaces close through the close-or-continue verdict and must pass the Table Closeout Gate, and Claude Code worker sessions close through decision 0070 and the Session Steward unchanged, keep SAFE TO ARCHIVE as their own vocabulary, and are never subject to the gate. SAFE TO ARCHIVE spoken about a table is void, not merely premature. Write-boundary correction: a write-capable surface performs and verifies every closeout write itself, and a read-only surface never claims those writes completed, it ships the smallest required carry-back block to the write-capable Estate surface that owns the write and the affected gate checks stay blocked until that carry-back returns verifiable evidence, which is a capability-boundary exception and never a general courier role for Allison. Behavioral delivery is proven per surface by a cold blind test before that surface may pronounce a table finished, because a repository edit a surface never receives is not implementation complete.

v1.9 amendment 2026-08-30 (ruled by Allison; ruling of record: aura decisions/0083-sequencing-without-maximalism-amendment-to-decision-0075.md; advisory of record aura intake/2026-08-30-sequencing-without-maximalism-corrected-final-advisory-super.md): the close-or-continue verdict consumes the BUILD BLOCKERS and OUTCOME BLOCKERS distinction. Every wrap's verdict reports BUILD BLOCKERS and OUTCOME BLOCKERS as two separate lines, never a single BLOCKING line, and Mission achieved requires OUTCOME BLOCKERS none plus the acceptance evidence for Allison's stated outcome (step 5 carries the governing question verbatim). Version numbering note: v1.8 is the Table Closeout Gate amendment decision 0075 ruled on 2026-08-26 and reserved for that gate's delivery, which had not landed in this file when this amendment was written (the v1.7-versus-v1.8 delivery defect decision 0080 holds as IMPORTANT BUT NOT BLOCKING, owned by its own workstream); this amendment therefore lands at v1.9 rather than taking the gate's number, and nothing here delivers, alters, or absorbs that gate.

v1.7 amendment 2026-08-26: the Session Steward joins the close loop. The verdict and closure loop are unchanged and preserve decision 0070 exactly: after mission and acceptance complete, the dispatching Control Tower owns moving the worker through this wrap and then giving Allison a plain archive-or-keep-open instruction on the earned verdict; the Steward surfaces archive candidates with evidence and never archives around this loop, and the product's own archive confirmation from Allison always stands.

## Current closeout workflow

The one canonical session close-out. Ruled by Allison 2026-08-04 in the Strategic Advisor project. Supersedes every per-project pasted SESSION WRAP block; when this skill is live in a project, the pasted paragraph gets deleted. Lineage: Allison's Session Close Prompt doc, the point-don't-paste ruling of 2026-08-04, and the SESSION WRAP v2 validation research of 2026-08-04 (aura intake). v1.1 amendment 2026-08-05: ledger writes bound to the shared-canonical-file-writes directive per Allison's ruling of 2026-08-04. v1.2 amendment 2026-08-05: closeout completeness ruled by Allison in the Strategic Advisor project (CI Watcher carry-back home lane) and proven live the same day by the Wrap Marks Backfill exercise before inking. v1.3 amendment 2026-08-07: flags ship as staged kickoffs, ruled by Allison in the Follow-Through Engine lane; ruling of record at aura intake/2026-08-07-ruling-follow-through-engine-rechartered-wraps-birth-convers.md, which supersedes pieces 1 and 2 of the same-date scoping packet. v1.4 amendment 2026-08-07: the dashboard wrap mark is retired from this protocol entirely, ruled by Allison 2026-08-06 in the Memory Drawer Cleanup lane; ruling of record at aura intake/2026-08-07-ruling-wrap-marks-retired-from-session-wrap-protocol.md, forced by the Board Walk clearing of 2026-08-07 (aura d183965, twelve marks removed, bodies preserved at intake/2026-08-07-wrap-marks-cleared-from-board.md). The board is for work, the repo is for memory; a wrap no longer marks the board. v1.5 amendment 2026-08-07: any dispatch block a wrap ships that spawns a Claude Code session carries the `WORKTREE` line, per the worktree dispatch ruling (aura intake/2026-08-07-ruling-dispatch-blocks-must-name-worktrees.md) and code-block-routing's Worktree Isolation; a spawning block without one is malformed. v1.6 amendment 2026-08-08: the close-or-continue verdict, ruled by Allison in the Command Center v2 Design lane (ruling of record aura intake/2026-08-08-ruling-session-wrap-close-or-continue-verdict.md); every wrap ends with Claude's advisory on whether the lane's mission is achieved, and an unfinished lane receives its own filled-in continuity prompt in the same wrap turn.

Design rationale, do not remove: this protocol deliberately does NOT rely on Claude's native chat memory (a compressed summary profile, not a decision log, and siloed per project) or on Project knowledge retrieval (RAG, relevant-chunk retrieval, not guaranteed recall). Git and the Founder Active Work board are the only living copies. The continuity note is fetched actively at session open, never assumed to surface on its own.

## 0. Triggers

Fires on: "SESSION WRAP", "wrap this session", "close out this session", "end of session", "save this to [PROJECT]", or any clear signal Allison is stopping work and wants a handoff. It also fires on its own under section 0A, with no words from Allison at all, and a finished Claude Code or Codex session fires it on its own under section 5A the moment its assignment is finished, without waiting for Allison to say wrap. Runs all five steps in this exact order, every time. The record must be buildable from artifacts, the board, and repo state alone, never from chat scrollback (compaction may have eaten it).

## 0A. Proactive terminality -- zero freedom

Ruled by Allison 2026-09-01. A finite mission can complete, but unless the system evaluates the landed acceptance evidence, its conversation may absorb adjacent work. **Allison must never be the person who notices that a finite mission should already be closed.**

**The trigger is acceptance evidence, not a request.** Work carrying a finite `MISSION` and `DONE WHEN` contract runs the terminality check when any of these lands:

- a worker carry-back is accepted, meaning its report has been read and its claims taken as good;
- a required PR, merge, deploy, or verification the mission named finishes;
- the last named dependency in the table's waiting-on state closes;
- any other evidence arrives that satisfies, or plainly cannot satisfy, the table's `DONE WHEN`.

**Who is exempt, and it is never a soft call.** A general-purpose conversation or standing subject carries no finite contract, is not evaluated automatically, and is **never nagged to archive merely because a topic ended**. Reaching the end of a subject is not the end of work that never had a finite mission.

**The check itself, three steps.** Read `MISSION` and `DONE WHEN` from the work's durable record, never from a recollection of what the work felt like. Compare the landed evidence against that `DONE WHEN`, and against nothing else. Then take exactly one of two branches.

**Branch one, the mission is achieved.** Run the full wrap, steps 1 through 5, including the Closeout Gate at 4A, which is what earns the verdict. The check is the trigger, never a shortcut past the gate. Then say plainly: `Mission achieved. This work can close.` Do not invent successor work merely because interesting findings exist (section 4B).

**Branch two, the mission is not achieved.** Say that plainly and **name the one real blocking acceptance or dependency item**, the specific thing whose closing would flip the verdict, with its named condition and its stale date preserved in the existing Chat to Code job. One named thing, never a list; when several are open, name the one that unblocks the rest. A vague `idle until something resumes` posture is banned outright, as is every equivalent of "we can pick this up later" (operating-doctrine, Decide Now). A wait with no named condition is not a wait, it is a ripe question hiding.

**What this never becomes.** No daemon, no sweeper, no watcher, no nudge machinery, no board card, no second registry, and no separate closeout system. The check is a behavior this skill performs at a moment that already happens, and the durable state it reads and writes is the one that already exists.

## 1. Session record (artifact) -- medium freedom on content, zero freedom on rules

Prepare the full session report for this job_finish summary, with its result link and existing job identity. Structure and required sections live in `reference/record-template.md`. Do not create a second work log. Non-negotiable rules baked into that template:

- Written for a reader with zero memory of this chat.
- Decisions in ADR shape: the decision, the context, the alternatives rejected, the consequences. Each decision tagged canon-candidate yes or no.
- Every file, asset, document, repo, base, location, scenario, or ID touched, with full paths and IDs, no shorthand and no nicknames.
- Point don't paste (Allison ruling 2026-08-04). Board cards by number and date only. Never paste card statuses, counts, or receipts. The board and the repos stay the only living copies.
- If unsure of a value, say so. Never guess.

## 2. Continuity note -- its own document, never buried in the record

Build the continuity note as its own markdown document from `reference/continuity-template.md`. It is what the next session loads first, fully standalone. It states plainly that it supersedes all prior continuity notes for its lane.

## 3. Push to canonical -- low freedom, exact order, verify each write before the next

No copy-paste on Allison's end. Tool mechanics, signatures, and the exact GraphQL live in `reference/mcp-and-dashboard.md`.

1. Save substantive deliverables in their owning home, and add one Decision Log entry per clear decision under the existing decision-save workflow. Verify each saved artifact and entry; link them in the job report rather than copying their contents into a second work record.
2. Save the continuity note the same way. Verify the link.
3. File the session report through job_finish with a summary and result link. Verify the result with job_status. Preserve unfinished work and its owner, named condition and stale date in the existing job. A failed or uncertain write leaves the reporting obligation open; inspect job_status before retrying. A surface without the required job tools reports that blocker and routes the complete return under the HQ Rulebook section Handoffs between AIs, without claiming the report is saved.
Publication and retrieval check: a returned link or chat assertion alone does not prove filing. Independently open saved deliverables, the continuity note and any Decision Log entry from their owning homes, and verify the job_finish summary through job_status. Verify the continuation path can fetch the required note without relying on this conversation. Give Allison the exact Drive links and a short summary. Routine copies of either record never go to `~/Desktop` or `~/Downloads`. Do not make Allison upload or carry the only copy.

Fallback: if the Docs connector refuses a write after a live test, use the service-account path (SA+DWD) for the same Drive folder, then verify as above. If the write stays blocked, name the failed action and its owner, leave the closeout obligation uncleared, and never substitute a Desktop or Downloads file or claim the wrap filed until read-back succeeds.

## 3A. Final uncaptured-memory sweep -- zero freedom (v1.12)

Ruled into this protocol 2026-09-04 by the Immediate Pain Controls campaign (issues #15 and #16). Allison is not the Estate's detection mechanism for what deserves to survive a session, and the wrap is the last moment anything can be caught before the transcript stops being read.

Run the `estate-memory-router` gate once over the closing session, after the canonical pushes in step 3 and before flags ship in step 4, so anything the sweep captures is already durable when the verdict is written.

What the sweep asks, exactly once, over the whole session: is there anything here a cold future worker would need, or whose loss would cause drift, rework, contradiction, or lost provenance, that has NOT been given a durable home by the record, the continuity note, the existing job, or a staged kickoff?

Route each qualifying item to its existing destination under the router's six routes. A future obligation goes to `remember-this` and gets one open issue in the owning repo carrying a mechanical `RETURN WHEN` line. Evidence and working knowledge go to the owning repo's intake. A founder decision Allison clearly made is saved as made under decision 0101 and needs no phrase. One she has not clearly made is preserved as a candidate and is never promoted on the AI's own say-so. A canon or rule change fires `canon-sync-protocol`, which step 5's promotion gate already requires.

Bounds, all load-bearing:

- **The record and the continuity note already capture most of it.** The sweep looks for what they did NOT capture, and it never duplicates them. An item already durably held is not swept again.
- **Nothing qualifying is the normal result, and it is reported in silence.** A wrap does not announce that its sweep found nothing.
- **No secrets, ever**, to any destination. Route the 1Password reference, never the value.
- **A failed or unverified sweep write is stated plainly**, exactly like a failed intake push in step 3, and never reported as captured. A false receipt ends Allison's own carrying of the item, which is worse than no capture.
- **Capture is not activation.** The sweep never starts the work, never spawns a lane on its own, and never re-scopes the closing mission. Adjacent work still routes under section 4B.

A wrap that skips this sweep is a partial wrap, the failure condition.

## 4. Flags ship as staged kickoffs -- zero freedom on the mechanism

Ruled by Allison 2026-08-07 in the Follow-Through Engine lane. The mission is unchanged, no flag ever dies in a document. The mechanism is this and only this.

Every flag in the session record's Open questions and flags section leaves the wrap as a staged kickoff block, a ready-to-paste continuity prompt that starts a new conversation to address that flag. This is the lane-spawn pattern applied at wrap time, so each block follows PASTE 1 in the lane-spawn skill: envelope lines first, the lane's one job, why it exists, the standing state it inherits, its do-not-absorb list, its first move, and its return path. Outside each block, one label, plainly, the destination (which Claude project, which surface).

Allison pulls the staged kickoffs at her own tempo. Five flags opening five conversations is fine and manageable; she ruled it. The receiving AI claims or creates the existing assignment in the Chat to Code job list, which is the work record. No reminder machinery, no nudge, no watcher, no due date, no card. None of it is built and none of it is wanted, because the lockstep march replaces it.

No flag ever gets a board card. Board cards are reserved for genuinely far-horizon items only. The Founder Active Work board holds missions and far-horizon markers, never working state. A project that looks complete on a board while ten unnoticed things sit on it is the exact failure this rule kills.

Before a flag is staged, classify it. Every flag is one of exactly two things, and there is no third.

- Ripe. Its inputs are complete, so the question comes to Allison immediately, in order, in the live conversation, and gets decided there. A ripe question is never staged and never deferred; see the Decide Now clause in the operating-doctrine. Staging a ripe question is the failure, not the safe choice.
- Waiting. It waits on a named condition, a third party, elapsed time, Allison's hands, or a running process. It stays in the existing Chat to Code job with the condition and the date it goes stale, per the No Later Commandment. A wait with no named condition is not a wait, it is a ripe question hiding.

Sequencing note so this does not fight the one-block-per-response rule in code-block-routing. A wrap's staged kickoff set is the named exception to that rule and the only one. Those blocks are a menu Allison draws from at her own tempo, not a sequence of dependent steps, which is what the one-block rule protects her from. Everything else in every other response stays at one block.

## 4A. The Closeout Gate (decision 0075) -- zero freedom

Before finite work may reach Mission achieved, the wrap runs six substantive obligations. Each clears with evidence or blocks the verdict.

One. Every clear decision Allison made in this table was saved under decision 0101 through its readback, reported as Saved and read back, Saved with the shared reader blocked, or Not saved. The obligation is her real clear decisions, never quoted source material, pasted prompts, examples, AI recommendations, or discussion of a topic. No phrase is required or checked for. This check verifies completion only and never re-litigates or reinterprets a decision.

Two. Every approved Book Moment is captured to the book repo with its required frontmatter and its USCO contribution log entry. Approved means Allison identified something as a Book Moment or directly instructed its capture, or the AI surfaced a candidate and Allison explicitly accepted it. A noticed-but-unapproved candidate may be offered once at wrap and Allison's no clears it. Book Moment capture is narrative preservation, never governance, and it never substitutes for a decision save in either direction.

Three. Finite work does not close over an execution session it still owns. Every dispatched execution session must complete decision 0070's closure loop, release its monitors, check-ins, subscriptions, scheduled wakeups, and background agents, and leave durable state truthful. Ownership is never silently transferred to permit closure. Cloud-worker registration remains mandatory where the platform requires it; a visible Worker name does not.

Four. Every durable artifact the table is actually required to maintain under current doctrine is verified and consistent with live state. For a lane-backed work table that means the session record, the continuity note, and a current Chat to Code job. For a legitimate non-lane-backed table under decision 0066, standing subject, planning, or personal reflection, that means only the artifacts that table genuinely owns, and no lane row, work-state row, or continuity note is invented solely to satisfy the gate. Raw personal or reflective material is never pushed into work-state machinery or a body-of-work repo because a table is closing. An already-written continuity note found to conflict with live state is superseded by a corrected note, never unwritten, because intake is append-only history.

Five. Every evidenced cross-surface obligation is executed, dispatched, or shipped to its concrete destination. An obligation exists only on evidence of a real dependency, an explicit promised return, accepted dispatch return criteria, a dependency in durable state, a decision or input another active task is explicitly waiting for, or continuing work requiring an owner. Absent such evidence, zero clears. Another surface finding the information interesting is not an obligation.

Six. Continuing work identifies its successor by concrete owner and destination: native task/session ID, repository and worktree/branch, issue/PR, project plus conversation when known, or an equally durable routing target. If the continuing work serves the same unfinished mission, that is Mission not achieved rather than succession.

Surface-specific and product-specific mechanics never live in this skill. They live in dated wiring and evidence records.

## 4B. Completed work never invents a sequel -- zero freedom

Once the original mission is achieved, adjacent or new work does **not** silently extend it. Completed work never decides its own future mission, however interesting the thing it just noticed.

Where new work goes: to the existing durable task that already owns the subject, if one exists. Otherwise it receives its own concrete owner and destination plus `MISSION` and `DONE WHEN` when finite, and ships as a staged kickoff under step 4. Genuinely trivial in-scope cleanup is finished in place under decision 0083 and never reopens the mission.

What is banned: rewriting or widening a `DONE WHEN` so finished work stays alive; treating a discovery as proof the mission was never complete; or absorbing a new job merely because the conversation is already open. Allison alone gives completed work a genuinely new mission.

The one honest exception. If the landed evidence shows the original mission was in fact **not** achieved, that is Mission not achieved under section 0A branch two, not a sequel. Say which of the two it is; the difference is whether the work serves the original `DONE WHEN` or a new one.

## 5. Confirmation, the canon promotion gate, and the close-or-continue verdict

In chat, a short plain note: the exact Drive links, the verified continuation retrieval, the verified job report and result link, and how many kickoffs are staged. If a publication or retrieval check failed, name the unpublished paths, blocked action, and owner instead of claiming completion. Then the promotion gate: if any decision in the record is tagged canon-candidate, or any canon doc (Docs 00-13), doctrine, or operating rule changed this session, fire the canon sync protocol immediately. The gate is the tag in the record, never the operator's recollection.

The close-or-continue verdict, ruled 2026-08-08 (ruling of record aura intake/2026-08-08-ruling-session-wrap-close-or-continue-verdict.md). Every wrap ends with Claude acting as the advisor on whether this lane keeps going. The verdict is judged against the lane's mission as stated in the session record, never against effort spent, and it is one of exactly two.

Amended 2026-08-30 (v1.9 amendment above): the verdict carries BUILD BLOCKERS and OUTCOME BLOCKERS as two separate lines, never a single BLOCKING line. BUILD BLOCKERS prevent the implementation from being built and are owned by the active worker. OUTCOME BLOCKERS prevent Allison's stated result from functioning end to end, or prevent required acceptance proof, blocking mission completion even when the build is finished.

- Mission achieved. Permitted only when all six Table Closeout Gate obligations in step 4A have cleared with evidence, AND OUTCOME BLOCKERS reads none, AND the acceptance evidence for Allison's stated outcome is named in the same verdict. The governing question, verbatim: "Can Allison now do the thing she asked to be able to do, end to end, at the promised level of reliability, with the required acceptance evidence?" No wrap declares mission completion while a required acceptance step is undone, and a finished build with an unfinished mission is Mission not achieved. Say plainly that the lane accomplished what it set out to do and can close, and recommend closure in one sentence Allison does not have to interpret, on the pattern `Mission achieved. Unless you want to give this table a genuinely new mission, you can archive it.` Do not hand out the lane's continuity prompt; a closed lane gets no continuation prompt unless Allison asks for one. Adjacent work discovered along the way routes under section 4B and never extends this table.
- Mission not achieved. Say plainly, all things have not been accomplished. List exactly what is unfinished. Then hand Allison the standing opening prompt from reference/opening-prompt.md with this lane's name filled in, ready to paste into the continuing conversation, in the same wrap turn.

This verdict covers THIS lane's own continuation. Flags that belong in other lanes still ship as staged kickoffs under step 4 and never substitute for the verdict. A wrap with no verdict is a partial wrap, the failure condition.

## 5A. Code sessions wrap and archive themselves (v1.19, amended v1.20 and v1.21)

<!-- RULED-BY: intake/2026-10-22-disclosure-rulebook-sync-formatting-tabs-session-wrap.md date:2026-10-22 -->

Source, the HQ Rulebook's Session lifecycle section, Decision Log 2026-10-24, Archiving is gated on the paper trail, and an orphan sweep catches what slips, Decision Log 2026-10-24, Finished code sessions wrap and archive themselves (2026-10-24), and Decision Log 2026-10-22, Code sessions wrap and archive themselves, never ask Allison. The live Rulebook wins wherever this section differs.

When a Claude Code or Codex session finishes, it closes itself. Finished means four things are true.

- Its outputs are saved where they belong.
- Its report row is written in the Handoffs tab and read back, meaning the session reads the row from the tab after writing it and confirms the text is there.
- Its incoming row, the Handoffs row that assigned the work, is marked Done with a pointer to that report row.
- Nothing is owed either way, no open question, no undelivered 📬 note, and nothing it still runs (session-steward section 7A).

**The archive gate.** The first two items and the second item's pointer are the gate, and the gate comes first. No archive call, and no `WRAP, safe to archive` line, before the report row is written and read back and the incoming row is marked Done with its pointer. The 📬 box in chat is only the bell, never the record. It tells Allison and HQ that a row exists, and a report that lives only in the box is not a report. A session with no incoming row, because Allison assigned the work in chat, still files its report row to the Handoffs tab for HQ, and only the incoming-row step falls away.

**A session that cannot reach the Handoffs tab stays open and says so.** If the sheet read or write fails twice, the session does not archive and does not paste the report into chat as a stand-in. It stays open, ends on `SESSION STATUS: NOT safe to archive -- cannot reach the Handoffs tab, report row not filed; waiting on the sheet connector.`, and keeps the full report text ready so the row can be filed the moment the tab answers.

Then it runs its wrap duties on its own, without waiting for Allison to say wrap, says SAFE TO ARCHIVE with its evidence, and archives itself where the app allows. It never asks Allison whether it is ready, and a session that archives itself owes her no notice. She only hears about a session that is waiting on her.

- Claude Code desktop. Call `archive_session` with `session_id` set to `self` as the very last action, after the final reply text. In Auto and Bypass permissions modes no approval card appears, and in other modes the app shows its own card (code.claude.com/docs/en/desktop, Work across sessions, checked 2026-10-22). A pinned session, a session still working, or one open on screen is refused by the app, so treat that refusal as the cannot-archive case below.
- Codex. A Codex session archives itself too, confirmed by Codex, Session Steward on 2026-10-24 (Decision Log 2026-10-24). `codex archive <SESSION>` archives a saved session by ID or name, and the app server has `thread/archive` (learn.chatgpt.com, Developer commands and App Server, checked 2026-10-22). If the call is refused, use the cannot-archive case below.
- Cloud sessions are not archived this way. They use the cannot-archive case.

If it cannot archive itself because the app refuses, and the gate above is satisfied, its last line is exactly `WRAP, safe to archive`. Claude Code, Session Steward or Codex, Session Steward sweeps those sessions on its next pass, and Star's nightly check lists them too. Those same passes also run the orphan sweep (session-steward section 10) for rows still Sent or Read whose session is archived or missing, and for pull requests or commits with no report row, so a session that archived without the gate is caught and HQ closes or restarts the row from the evidence.

Asking Allison "ready to wrap?" or "can I archive?" is the failure condition. A session that still owes something is not finished. It stays ACTIVE or WAITING under the Rulebook's Session lifecycle states and says which.

## 6. Session open (the other half)

The standing opening prompt lives in `reference/opening-prompt.md`. Allison pastes it at the start of a new session with the lane name filled in. It fetches the latest continuity note from Drive and the existing job's saved report through job_status, then runs verify-before-trust: reconcile the note's claims against the live board card and repo state and flag any mismatch BEFORE doing work. A continuity note is a predecessor's interpretation, not ground truth.

## 7. Supersession and pruning

Each continuity note supersedes all prior notes for its lane; the existing Chat to Code job carries current state. Session records are archive-class history under the records-stay-point-don't-paste ruling (2026-08-04): they never go stale because they never claimed to be today, and they never embed live state. The quarterly doctrine hygiene pass archives intake records older than the active window out of the active retrieval path.

## Rules

- Allison does not carry a record file between sessions. At open, the existing opening prompt may point the next session to the published continuity note; the agent retrieves and verifies the note itself.
- Five steps, exact order, no step skipped, every write verified before the next.
- Closeout completeness (ruled by Allison 2026-08-05, proven live the same day by the Wrap Marks Backfill exercise; amended 2026-08-07 by the staged-kickoff ruling). At wrap, every open item is classified and handled in the same wrap. Executable from this surface, execute it before the wrap confirmation. Executable only elsewhere, the wrap itself ships the dispatch block (per code-block-routing in full, including the `WORKTREE` line whenever the block spawns a Code session, v1.5) and has the receiving AI use job_create or job_claim; queued-for-later is never a terminal state for anything Claude-executable. Time-gated or evidence-gated, it stays in the existing Chat to Code job with its named condition and its stale date, never on a board card, never in a chat, and never as a wrap blocker (the 2026-08-07 recharter moved working state off the board; the v1.2 wording that sent these items to a board card is retired). Allison's hand steps are delivered ready-made with the full direct URL for her own browser, per the hand-step URL rule in code-block-routing. A wrap that leaves a Claude-executable item as a flag is a partial wrap, the failure condition; so is a wrap that leaves a flag with no staged kickoff and no owning job.
- A wrap that cannot verify its artifact links or job_finish report says so plainly. A silent partial wrap is the failure condition.
- Nothing in this skill depends on product mechanics; anything volatile lives in the reference files, dated, verified at use time.
- Proactive terminality runs when acceptance evidence lands for work carrying a finite MISSION and DONE WHEN, and never because a conversation has a particular name. A finite mission that reaches DONE WHEN and says nothing is the failure condition; so is an unsolicited wrap offered merely because a general topic ended.
- The final uncaptured-memory sweep runs at every wrap (step 3A, v1.12), routing through the estate-memory-router into mechanisms that already exist. A wrap that skips it is a partial wrap; a wrap whose sweep found nothing says nothing.
- Completed work never extends itself over adjacent work. New work routes to its concrete existing owner or receives a new durable destination.
- The Closeout Gate runs before any Mission achieved verdict. A wrap that declares Mission achieved without naming each of the six substantive obligations as cleared with evidence is partial.
- SAFE TO ARCHIVE is worker vocabulary only and is void when spoken about a table (decision 0075). A worker closes through decision 0070 and the Session Steward and is never subject to the gate; a table closes only through the close-or-continue verdict. A worker may be complete and safe to archive while its home table remains open, and a worker verdict is never imported as a table verdict. A worker is never a chair. It returns its evidence to the table's chair, the chair stays home while the worker is away, and the chair, never the worker, is what a table close is about.
