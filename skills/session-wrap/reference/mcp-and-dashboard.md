# Wrap mechanics: MCP writes, ledger, dashboard mark

Volatile mechanics live here, dated, verified at use time. Nothing in SKILL.md depends on them.

## Intake push

Tool, fully qualified: `Estate Brain:save_to_session_intake`
Args: `project` (canonical repo name, normally `aura`), `content` (the full markdown), `title` (slug source, e.g. `session-record-[lane]` / `continuity-[lane]`), `classification` (`internal` unless ruled otherwise, ADR 0025).
Behavior: append-only, writes `<repo>/intake/YYYY-MM-DD-<slug>.md`, never overwrites (ADR 0027). Verify: the response must return the written path. Echo the exact path in the confirmation. No path returned means the write failed, use the fallback (downloadable .md plus a plain statement of the failure).

## Lane ledger

File: aura `docs/estate/lanes.md`. Update this lane's row with the closeout state per the code-block-routing skill's ledger rules.

Preferred path as of 2026-08-07, the Estate Brain door tool `Estate Brain:update_lane_row` (door tool eight). It retires whole-file writes: fresh read every attempt, single-row edit on that fresh base, compare-and-swap on the blob SHA, bounded rebase-retry that re-reads instead of forcing, post-write re-read from origin returning the exact diff, foreign edits in the same window reported rather than hidden, and on exhaustion it writes nothing and routes the row per Rule 2. It refuses rather than guesses on ambiguous duplicates, malformed rows, resurrecting a completed lane, a new row with no named home, and no-op writes. A refusal is a correct outcome, not a failure to work around; a malformed row gets repaired by a git-based writer first, then the tool runs.

Without the door: from Claude Code, commit directly (still preferred for this hot file over any contents-API write). From Chat or Cowork with no door reach, use the GitHub connector file write (whole-file write on main, reversible under ADR 0047) under the full collision guard below.

Collision guard, mandatory (incident 2026-08-04, first live wrap): the ledger is a shared concurrent-writer file, and a whole-file write can silently revert or drop sibling rows written between your read and your write. So, in order: (1) read the ledger IMMEDIATELY before writing, never from an earlier point in the session; (2) after the write, fetch the commit's full patch and verify it contains ONLY this lane's row change; (3) any reverted or dropped sibling line gets restored in a corrective commit BEFORE the wrap continues, and the incident is named in this lane's row and in the confirmation. Never report the ledger step done on the push alone.

Directive binding, added 2026-08-05 (Allison's ruling of 2026-08-04 after the second regression incident): the shared-canonical-file-writes directive (aura `docs/directives/shared-canonical-file-writes.md`) governs every ledger write and wins if this section ever lags it. Three additions beyond the guard above. Any contents-API write MUST pass the current blob SHA (compare-and-swap) so a stale write bounces instead of landing. After two SHA-guard bounces in one wrap, the writer stops racing and routes the row verbatim through an intake handoff note for the next git-based writer to fold in, and a routed row plus a plain statement is a correct wrap. Corrective commits restore only from a FRESH read taken at repair time, never from a copy held earlier in the session, because the held copy may be missing newer healing by the owning lanes (this exact near-miss happened 2026-08-04 and only the SHA guard stopped it).

## Dashboard wrap mark (hq.allisongaddy.com)

The dashboard is a stateless read-only render of the Founder Active Work board (github.com/orgs/ExpertPartners/projects/1). The wrap leaves its mark ON THE BOARD, never via a second dashboard render path (one source of truth). Ruled mechanism, one dated draft item per wrap.

Preferred path, the Estate Brain door tool. `Estate Brain:wrap_mark` shipped 2026-08-07 as door tool nine (aura 8867a3e) and is the default on every surface that reaches the door, chat and Cowork included. Args: the lane name and the date. It enumerates before writing, dedupes by title, verifies by query-back with backoff, and on an inconclusive query-back it says so, states the item WAS created, returns its id, and tells the caller not to re-run. Re-running a marked lane returns Already marked and creates nothing. It never writes a Status field. No credential handling on the caller's side; the estate-brain-door App carries the organization Projects write granted 2026-08-06 and capability-verified 2026-08-07.

CORRECTION, 2026-08-07: ProjectsV2 is NOT GraphQL-only. That claim was true when this file was written and is now stale; it survived into the wrap-mark flag's premise and briefly argued for a classic PAT that the estate did not need. Verified live 2026-08-07 against api.github.com from this repo's session: `GET /orgs/ExpertPartners/projectsV2` returns the org's projects, and `POST /orgs/{org}/projectsV2/{number}/drafts` is a real endpoint on BOTH API versions 2022-11-28 and 2026-03-10 (probed with the body omitted, so both returned HTTP 422 "Invalid input: data cannot be null" citing docs.github.com/rest/projects/drafts#create-draft-item-for-organization-owned-project, and nothing was created). Independently corroborated 2026-08-06 by the Door Tools Build lane. The shipped `wrap_mark` tool uses REST, not GraphQL.

Manual fallback, only when the door is unreachable. REST, two calls:

1. Read the board to dedupe: `GET /orgs/ExpertPartners/projectsV2/1/items`
2. Create the mark: `POST /orgs/ExpertPartners/projectsV2/1/drafts` with a JSON body carrying the title and body.

Title: `Wrap: [lane] [YYYY-MM-DD]`. Body: one line pointing at the two intake paths and the ledger commit. Pointers only, no pasted state.

From Claude Code: `gh api` with the authenticated gh session. The GraphQL pair (`organization.projectV2(number:)` for the node id, then `addProjectV2DraftIssue`) still works and stays a valid fallback; it is no longer the only path. Auth needs project scope. Tokens live in 1Password only. Proven live 2026-08-05 by the Canon Doc Sync and Wrap Marks Backfill lanes (AllisonGaddy keyring identity with project scope, query-back verification per item).

Known constraint (reported 2026, community-sourced, verify before relying): `updateProjectV2ItemFieldValue` single-select changes can update the data store without updating the board-view grouping index, so a card may not visibly move columns. That is why the wrap mark is a NEW dated draft item, never a status move.

If the current surface reaches neither the door tool nor an authenticated REST or GraphQL path: say plainly the mark did not land and why, and ship the mark's dispatch block to a capable session in the same wrap turn (closeout completeness rule, SKILL.md v1.3). Never silently skip. The durable fix ordered by the shared-canonical-file-writes directive (Rule 3) is DELIVERED as of 2026-08-07: `update_lane_row` (tool eight, aura c64c5bb plus the Central-time fix 587b98d) and `wrap_mark` (tool nine, aura 8867a3e plus the query-back backoff fix 880beb5) are both live on the Lambda door, `tools/list` returns nine. Both were caught out by their own first live run, the ledger tool on timezone and the wrap tool on board-index lag, neither reachable by unit test; proving-live is the standard for door tools.
