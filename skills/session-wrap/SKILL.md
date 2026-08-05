---
name: session-wrap
description: "Closes out and hands off a work session in any of Allison's Claude conversations, in every project and on every surface (Claude app, Cowork, Claude Code). Produces a standalone session record artifact and a superseding continuity note, pushes both to the aura intake inbox via the Estate Brain:save_to_session_intake MCP tool, updates the lane ledger row in aura docs/estate/lanes.md, leaves a dated wrap mark on the Founder Active Work board so it shows on hq.allisongaddy.com, and fires the canon sync protocol when a rule changed. Use whenever Allison says session wrap, wrap this session, close out this session, end of session, or save this to [PROJECT], and whenever she signals she is stopping work and wants a handoff, even if she does not name the skill. One canonical copy replaces every per-project pasted SESSION WRAP block. It inherits the operating-doctrine and never overrides it."
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

# Session Wrap -- v1.1 (2026-08-05)

The one canonical session close-out. Ruled by Allison 2026-08-04 in the Strategic Advisor project. Supersedes every per-project pasted SESSION WRAP block; when this skill is live in a project, the pasted paragraph gets deleted. Lineage: Allison's Session Close Prompt doc (Drive file 1qydJ3KsiZh-VHDwMJHX0i6hEn2tRyJw7dNSApHkFNBI), the point-don't-paste ruling of 2026-08-04, and the SESSION WRAP v2 validation research of 2026-08-04 (aura intake). v1.1 amendment 2026-08-05: ledger writes bound to the shared-canonical-file-writes directive per Allison's ruling of 2026-08-04.

Design rationale, do not remove: this protocol deliberately does NOT rely on Claude's native chat memory (a compressed summary profile, not a decision log, and siloed per project) or on Project knowledge retrieval (RAG, relevant-chunk retrieval, not guaranteed recall). Git and the Founder Active Work board are the only living copies. The continuity note is fetched actively at session open, never assumed to surface on its own.

## 0. Triggers

Fires on: "SESSION WRAP", "wrap this session", "close out this session", "end of session", "save this to [PROJECT]", or any clear signal Allison is stopping work and wants a handoff. Runs all four steps in this exact order, every time. The record must be buildable from artifacts, the board, and repo state alone, never from chat scrollback (compaction may have eaten it).

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
4. Leave the dashboard wrap mark: add one dated draft item to the Founder Active Work board (org project 1) via the GraphQL `addProjectV2DraftIssue` mutation, titled `Wrap: [lane] [YYYY-MM-DD]`. Never mark a wrap by moving a single-select status field (known grouping-index inconsistency, see reference). On a surface with no GraphQL path, say plainly the mark did not land and why, and put it first in the next dispatch to a session that can. Never silently skip it.

Fallback (MCP write): if `Estate Brain:save_to_session_intake` fails after testing it live, deliver the continuity note as a downloadable .md file and say plainly that the intake push failed and why.

## 4. Confirmation and the canon promotion gate

In chat, a short plain note: the artifact gets clicked into this project's files, the exact intake paths, the ledger commit, the dashboard mark. Then the promotion gate: if any decision in the record is tagged canon-candidate, or any canon doc (Docs 00-13), doctrine, or operating rule changed this session, fire the canon sync protocol immediately. The gate is the tag in the record, never the operator's recollection.

## 5. Session open (the other half)

The standing opening prompt lives in `reference/opening-prompt.md`. Allison pastes it at the start of a new session with the lane name filled in. It fetches the latest continuity note and record via Estate Brain, checks the lane ledger row, then runs verify-before-trust: reconcile the note's claims against the live board card and repo state and flag any mismatch BEFORE doing work. A continuity note is a predecessor's interpretation, not ground truth.

## 6. Supersession and pruning

Each continuity note supersedes all prior notes for its lane; the ledger row carries current state. Session records are archive-class history under the records-stay-point-don't-paste ruling (2026-08-04): they never go stale because they never claimed to be today, and they never embed live state. The quarterly doctrine hygiene pass archives intake records older than the active window out of the active retrieval path.

## Rules

- Allison does exactly two things per cycle: click Add to Project on the record artifact at close, paste the opening prompt at open. Everything else is Claude's.
- Four steps, exact order, no step skipped, every write verified before the next.
- A wrap that cannot verify its intake paths, ledger commit, or dashboard mark says so plainly. A silent partial wrap is the failure condition.
- Nothing in this skill depends on product mechanics; anything volatile lives in the reference files, dated, verified at use time.
