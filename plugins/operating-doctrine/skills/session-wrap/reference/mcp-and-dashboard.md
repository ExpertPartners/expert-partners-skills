# Wrap mechanics: Drive writes, Job Tracker, dashboard mark

Volatile mechanics live here, dated, verified at use time. Nothing in SKILL.md depends on them.

## Drive records

Session record and continuity note: a Google Doc in the owning brain's home folder, found through that brain's 00 START HERE index (Company Core [HQ-BB] when no one company owns it). Plain title, no date prefix. Create it with the Google Docs or Drive connector; if the connector refuses the write, use the service-account path (SA+DWD, impersonating allison@) for the same folder. The returned link is a write receipt, not proof: open the Doc from Drive to verify.

## Decision Log

The Decision Log Doc, in Company Core [HQ-BB], found by its title. Add each decision at the top under today's date heading (create the heading if today's is missing): what was decided, why in one or two sentences, a `Replaces:` note naming the older decision it supersedes (or none), and a link to the full record. Re-read the Doc after the write to confirm the entry landed and nothing else changed.

## Job Tracker

The Job Tracker Sheet, in Company Core [HQ-BB], found by its title. Columns A to H: Job, Room or lane, Who is doing it, Status, Waiting on, Next step, Opened, Last updated. Read the values, change only this lane's row (or append one at the bottom), then re-read to verify. After two failed writes, stop and route the row verbatim in the wrap note for home to enter.

## Dashboard wrap mark (hq.allisongaddy.com)

RETIRED 2026-08-06. Ruled by Allison in the Memory Drawer Cleanup lane, ruling of record at aura `intake/2026-08-07-ruling-wrap-marks-retired-from-session-wrap-protocol.md`, forced by the Board Walk clearing of 2026-08-07 (aura d183965, twelve marks removed, bodies preserved at `intake/2026-08-07-wrap-marks-cleared-from-board.md`). The wrap mark is out of the session-wrap protocol entirely as of SKILL.md v1.4; a wrap no longer marks the board. Everything below is kept as the mechanical record of how the mark worked, per append-and-update-never-silently-delete. Do not execute it as part of a wrap. Disposition of door tool nine `wrap_mark` is settled as of 2026-08-07, the tool has been removed from the door. Live `tools/list` returns eight tools, confirmed in the session-wrap MCP-failure eval (Finding B) and inked at aura intake/2026-08-08-ruling-eval-finding-b-mcp-and-dashboard-reference-correction.md.

The dashboard is a stateless read-only render of the Founder Active Work board (github.com/orgs/ExpertPartners/projects/1). The wrap leaves its mark ON THE BOARD, never via a second dashboard render path (one source of truth). Ruled mechanism, one dated draft item per wrap.

The mark was once written by a dedicated tool that enumerated before writing, deduped by title, and verified by query-back. That tool is gone. Use the REST fallback below if a mark is ever needed again.

CORRECTION, 2026-08-07: ProjectsV2 is NOT GraphQL-only. That claim was true when this file was written and is now stale; it survived into the wrap-mark flag's premise and briefly argued for a classic PAT that the estate did not need. Verified live 2026-08-07 against api.github.com from this repo's session: `GET /orgs/ExpertPartners/projectsV2` returns the org's projects, and `POST /orgs/{org}/projectsV2/{number}/drafts` is a real endpoint on BOTH API versions 2022-11-28 and 2026-03-10 (probed with the body omitted, so both returned HTTP 422 "Invalid input: data cannot be null" citing docs.github.com/rest/projects/drafts#create-draft-item-for-organization-owned-project, and nothing was created). Independently corroborated 2026-08-06 by the Door Tools Build lane. The retired mark writer used REST, not GraphQL.

REST path. REST, two calls:

1. Read the board to dedupe: `GET /orgs/ExpertPartners/projectsV2/1/items`
2. Create the mark: `POST /orgs/ExpertPartners/projectsV2/1/drafts` with a JSON body carrying the title and body.

Title: `Wrap: [lane] [YYYY-MM-DD]`. Body: one line pointing at the two intake paths and the ledger commit. Pointers only, no pasted state.

From Claude Code: `gh api` with the authenticated gh session. The GraphQL pair (`organization.projectV2(number:)` for the node id, then `addProjectV2DraftIssue`) still works and stays a valid fallback; it is no longer the only path. Auth needs project scope. Tokens live in 1Password only. Proven live 2026-08-05 by the Canon Doc Sync and Wrap Marks Backfill lanes (AllisonGaddy keyring identity with project scope, query-back verification per item).

Known constraint (reported 2026, community-sourced, verify before relying): `updateProjectV2ItemFieldValue` single-select changes can update the data store without updating the board-view grouping index, so a card may not visibly move columns. That is why the wrap mark is a NEW dated draft item, never a status move.

If the current surface has no authenticated REST or GraphQL path: say plainly the mark did not land and why, and ship the mark's dispatch block to a capable session in the same wrap turn (closeout completeness rule, SKILL.md v1.3). Never silently skip. The durable fix ordered by the shared-canonical-file-writes directive (Rule 3) shipped 2026-08-07 with two tools, a lane-ledger writer and a wrap-mark writer. Both were caught out by their own first live run, the ledger writer on timezone and the mark writer on board-index lag, neither reachable by unit test; proving-live is the standard for write tools.

RETIRED IN HALF, 2026-08-06 (same ruling as the section head). The ORDERED durable fix above paired two tools, and only one half survived the ruling. The lane-ledger half stood because it served an active wrap step. The wrap-mark half is MOOT, the protocol step it was built for no longer exists, so nothing in a wrap calls it, and its tool has been removed entirely. See the ruling at aura intake/2026-08-08-ruling-eval-finding-b-mcp-and-dashboard-reference-correction.md.
