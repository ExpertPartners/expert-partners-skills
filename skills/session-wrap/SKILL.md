---
name: session-wrap
description: "Closes out and hands off a work session in any of Allison's Claude conversations, in every project and on every surface (Claude app, Cowork, Claude Code). Produces a standalone session record artifact and a superseding continuity note, pushes both to the aura intake inbox via the Estate Brain:save_to_session_intake MCP tool, updates the lane ledger row in aura docs/estate/lanes.md, ships every flag as a staged kickoff block that births its own conversation rather than a board card, and fires the canon sync protocol when a rule changed. Use whenever Allison says session wrap, wrap this session, close out this session, end of session, or save this to [PROJECT], and whenever she signals she is stopping work and wants a handoff, even if she does not name the skill. One canonical copy replaces every per-project pasted SESSION WRAP block. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Adopted into canonical 2026-08-05 (Skill Map Rulings lane, add-on brief note 4):
# estate-wide skill, canonical home verified as having been aura .claude/skills only,
# adopted here per the ruling 9 pattern. The aura copy is now a deployed copy,
# recorded in the extractor's DECLARED_DUPLICATES. Content copied verbatim.
tier: organization
zone: routing
status: live
subtitle: "the one canonical session close-out"
---

# Session Wrap -- v1.5 (2026-08-07)

The one canonical session close-out. Ruled by Allison 2026-08-04 in the Strategic Advisor project. Supersedes every per-project pasted SESSION WRAP block; when this skill is live in a project, the pasted paragraph gets deleted. Lineage: Allison's Session Close Prompt doc (Drive file 1qydJ3KsiZh-VHDwMJHX0i6hEn2tRyJw7dNSApHkFNBI), the point-don't-paste ruling of 2026-08-04, and the SESSION WRAP v2 validation research of 2026-08-04 (aura intake). v1.1 amendment 2026-08-05: ledger writes bound to the shared-canonical-file-writes directive per Allison's ruling of 2026-08-04. v1.2 amendment 2026-08-05: closeout completeness ruled by Allison in the Strategic Advisor project (CI Watcher carry-back home lane) and proven live the same day by the Wrap Marks Backfill exercise before inking. v1.3 amendment 2026-08-07: flags ship as staged kickoffs, ruled by Allison in the Follow-Through Engine lane; ruling of record at aura intake/2026-08-07-ruling-follow-through-engine-rechartered-wraps-birth-convers.md, which supersedes pieces 1 and 2 of the same-date scoping packet. v1.4 amendment 2026-08-07: the dashboard wrap mark is retired from this protocol entirely, ruled by Allison 2026-08-06 in the Memory Drawer Cleanup lane; ruling of record at aura intake/2026-08-07-ruling-wrap-marks-retired-from-session-wrap-protocol.md, forced by the Board Walk clearing of 2026-08-07 (aura d183965, twelve marks removed, bodies preserved at intake/2026-08-07-wrap-marks-cleared-from-board.md). The board is for work, the repo is for memory; a wrap no longer marks the board. v1.5 amendment 2026-08-07: any dispatch block a wrap ships that spawns a Claude Code session carries the `WORKTREE` line, per the worktree dispatch ruling (aura intake/2026-08-07-ruling-dispatch-blocks-must-name-worktrees.md) and code-block-routing's Worktree Isolation; a spawning block without one is malformed.

Design rationale, do not remove: this protocol deliberately does NOT rely on Claude's native chat memory (a compressed summary profile, not a decision log, and siloed per project) or on Project knowledge retrieval (RAG, relevant-chunk retrieval, not guaranteed recall). Git and the Founder Active Work board are the only living copies. The continuity note is fetched actively at session open, never assumed to surface on its own.

## 0. Triggers

Fires on: "SESSION WRAP", "wrap this session", "close out this session", "end of session", "save this to [PROJECT]", or any clear signal Allison is stopping work and wants a handoff. Runs all five steps in this exact order, every time. The record must be buildable from artifacts, the board, and repo state alone, never from chat scrollback (compaction may have eaten it).

## 1. Session record (artifact) -- medium freedom on content, zero freedom on rules

Build the full session record as one standalone markdown artifact titled "Session Record [PROJECT] [today's date]" so Allison can click Add to Project. Structure and required sections live in `reference/record-template.md`. Non-negotiable rules baked into that template:

- Written for a reader with zero memory of this chat.
- Decisions in ADR shape: the decision, the context, the alternatives rejected, the consequences. Each decision tagged canon-candidate yes or no.
- Every file, asset, document, repo, base, location, scenario, or ID touched, with full paths and IDs, no shorthand and no nicknames.
- Point don't paste (Allison ruling 2026-08-04). Board cards by number and date only. Never paste card statuses, counts, or receipts. The board and the repos stay the only living copies.
- If unsure of a value, say so. Never guess.

## 2. Continuity note -- its own document, never buried in the record

Build the continuity note as its own markdown document from `reference/continuity-template.md`. It is what the next session loads first, fully standalone. It states plainly that it supersedes all prior continuity notes for its lane.

## 3. Push to canonical -- low freedom, exact order, verify each write before the next

No copy-paste on Allison's end. Tool mechanics, signatures, and the exact GraphQL live in `reference/mcp-and-dashboard.md`.

1. Save the session record to the aura intake inbox via `Estate Brain:save_to_session_intake`. Verify the response returns a path.
2. Save the continuity note the same way. Verify the path.
3. Update the lane ledger row for this lane in aura `docs/estate/lanes.md` with the closeout state. Verify the commit. Every ledger write obeys the shared-canonical-file-writes directive (aura `docs/directives/shared-canonical-file-writes.md`, ruled 2026-08-04): fresh read immediately before the write, blob-SHA compare-and-swap on any contents-API write, post-write diff check that no other lane's rows changed, and after two SHA-guard bounces in one wrap stop racing and route the row verbatim through an intake handoff note for the next git-based writer to fold in. A routed row plus a plain statement is a correct wrap; a raced or unguarded write is the violation.
Fallback (MCP write): if `Estate Brain:save_to_session_intake` fails after testing it live, deliver the continuity note as a downloadable .md file and say plainly that the intake push failed and why.

## 4. Flags ship as staged kickoffs -- zero freedom on the mechanism

Ruled by Allison 2026-08-07 in the Follow-Through Engine lane. The mission is unchanged, no flag ever dies in a document. The mechanism is this and only this.

Every flag in the session record's Open questions and flags section leaves the wrap as a staged kickoff block, a ready-to-paste continuity prompt that starts a new conversation to address that flag. This is the lane-spawn pattern applied at wrap time, so each block follows PASTE 1 in the lane-spawn skill: envelope lines first, the lane's one job, why it exists, the standing state it inherits, its do-not-absorb list, its first move, and its return path. Outside each block, two labels, plainly, the destination (which Claude project, which surface) and the exact name for the new conversation.

Allison pulls the staged kickoffs at her own tempo. Five flags opening five conversations is fine and manageable; she ruled it. The open conversation IS the tracking. No reminder machinery, no nudge, no watcher, no due date, no card. None of it is built and none of it is wanted, because the lockstep march replaces it.

No flag ever gets a board card. Board cards are reserved for genuinely far-horizon items only. The Founder Active Work board holds missions and far-horizon markers, never working state. A project that looks complete on a board while ten unnoticed things sit on it is the exact failure this rule kills.

Before a flag is staged, classify it. Every flag is one of exactly two things, and there is no third.

- Ripe. Its inputs are complete, so the question comes to Allison immediately, in order, in the live conversation, and gets decided there. A ripe question is never staged and never deferred; see the Decide Now clause in the operating-doctrine. Staging a ripe question is the failure, not the safe choice.
- Waiting. It waits on a named condition, a third party, elapsed time, Allison's hands, or a running process. It goes in the lane ledger's waiting-on column with the condition and the date it goes stale, per the No Later Commandment. A wait with no named condition is not a wait, it is a ripe question hiding.

Sequencing note so this does not fight the one-block-per-response rule in code-block-routing. A wrap's staged kickoff set is the named exception to that rule and the only one. Those blocks are a menu Allison draws from at her own tempo, not a sequence of dependent steps, which is what the one-block rule protects her from. Everything else in every other response stays at one block.

## 5. Confirmation and the canon promotion gate

In chat, a short plain note: the artifact gets clicked into this project's files, the exact intake paths, the ledger commit, and how many kickoffs are staged. Then the promotion gate: if any decision in the record is tagged canon-candidate, or any canon doc (Docs 00-13), doctrine, or operating rule changed this session, fire the canon sync protocol immediately. The gate is the tag in the record, never the operator's recollection.

## 6. Session open (the other half)

The standing opening prompt lives in `reference/opening-prompt.md`. Allison pastes it at the start of a new session with the lane name filled in. It fetches the latest continuity note and record via Estate Brain, checks the lane ledger row, then runs verify-before-trust: reconcile the note's claims against the live board card and repo state and flag any mismatch BEFORE doing work. A continuity note is a predecessor's interpretation, not ground truth.

## 7. Supersession and pruning

Each continuity note supersedes all prior notes for its lane; the ledger row carries current state. Session records are archive-class history under the records-stay-point-don't-paste ruling (2026-08-04): they never go stale because they never claimed to be today, and they never embed live state. The quarterly doctrine hygiene pass archives intake records older than the active window out of the active retrieval path.

## Rules

- Allison does exactly two things per cycle: click Add to Project on the record artifact at close, paste the opening prompt at open. Everything else is Claude's.
- Five steps, exact order, no step skipped, every write verified before the next.
- Closeout completeness (ruled by Allison 2026-08-05, proven live the same day by the Wrap Marks Backfill exercise; amended 2026-08-07 by the staged-kickoff ruling). At wrap, every open item is classified and handled in the same wrap. Executable from this surface, execute it before the wrap confirmation. Executable only elsewhere, the wrap itself ships the dispatch block (per code-block-routing in full, including the `WORKTREE` line whenever the block spawns a Code session, v1.5) and writes the lane row; queued-for-later is never a terminal state for anything Claude-executable. Time-gated or evidence-gated, it lives in the lane ledger's waiting-on column with its named condition and its stale date, never on a board card, never in a chat, and never as a wrap blocker (the 2026-08-07 recharter moved working state off the board; the v1.2 wording that sent these items to a board card is retired). Allison's hand steps are delivered ready-made with the full direct URL for her own browser, per the hand-step URL rule in code-block-routing. A wrap that leaves a Claude-executable item as a flag is a partial wrap, the failure condition; so is a wrap that leaves a flag with no staged kickoff and no ledger row.
- A wrap that cannot verify its intake paths or ledger commit says so plainly. A silent partial wrap is the failure condition.
- Nothing in this skill depends on product mechanics; anything volatile lives in the reference files, dated, verified at use time.
