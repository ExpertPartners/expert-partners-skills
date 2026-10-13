# Wrap mechanics: Drive writes, Job Tracker, dashboard mark

Volatile mechanics live here, dated, verified at use time. Nothing in SKILL.md depends on them.

## Drive records

Session record and continuity note: a Google Doc in the owning brain's home folder, found through that brain's 00 START HERE index (Company Core [HQ-BB] when no one company owns it). Plain title, no date prefix. Create it with the Google Docs or Drive connector; if the connector refuses the write, use the service-account path (SA+DWD, impersonating allison@) for the same folder. The returned link is a write receipt, not proof: open the Doc from Drive to verify.

## Decision Log

Google Doc `1ausL1HV3ns3VMZH86jD8zjWnAKSQ3DaUfFzkiwR1qWc`, Company Core [HQ-BB]. Add each decision at the top under today's date heading (create the heading if today's is missing): `D-YYYY-MM-DD-##`, what was decided, why in one or two sentences, `Replaces:` the older decision's ID or aura decision number (or none), and a link to the full record. Re-read the Doc after the write to confirm the entry landed and nothing else changed.

## Job Tracker

Google Sheet `1FniEwCaZ89cViQxUcPkycxAmvvM47cnjRzQQyzpEk5c`. Columns A to H: Job, Room or lane, Who is doing it, Status, Waiting on, Next step, Opened, Last updated. Read the values, change only this lane's row (or append one at the bottom), then re-read to verify. After two failed writes, stop and route the row verbatim in the wrap note for home to enter.

## Dashboard wrap mark (hq.allisongaddy.com)

RETIRED 2026-08-06. Ruled by Allison in the Memory Drawer Cleanup lane, ruling of record at aura `intake/2026-08-07-ruling-wrap-marks-retired-from-session-wrap-protocol.md`, forced by the Board Walk clearing of 2026-08-07 (aura d183965, twelve marks removed, bodies preserved at `intake/2026-08-07-wrap-marks-cleared-from-board.md`). The wrap mark is out of the session-wrap protocol entirely as of SKILL.md v1.4; a wrap no longer marks the board. Everything below is kept as the mechanical record of how the mark worked, per append-and-update-never-silently-delete. Do not execute it as part of a wrap. Disposition of door tool nine `wrap_mark` is settled as of 2026-08-07, the tool has been removed from the door. Live `tools/list` returns eight tools, confirmed in the session-wrap MCP-failure eval (Finding B) and inked at aura intake/2026-08-08-ruling-eval-finding-b-mcp-and-dashboard-reference-correction.md.

The dashboard is a stateless read-only render of the Founder Active Work board (github.com/orgs/ExpertPartners/projects/1). The wrap leaves its mark ON THE BOARD, never via a second dashboard render path (one source of truth). Ruled mechanism, one dated draft item per wrap.

Preferred path, the Estate Brain door tool. `Estate Brain:wrap_mark` shipped 2026-08-07 as door tool nine (aura 8867a3e) and is the default on every surface that reaches the door, chat and Cowork included. Args: the lane name and the date. It enumerates before writing, dedupes by title, verifies by query-back with backoff, and on an inconclusive query-back it says so, states the item WAS created, returns its id, and tells the caller not to re-run. Re-running a marked lane returns Already marked and creates nothing. It never writes a Status field. No credential handling on the caller's side; the estate-brain-door App carries the organization Projects write granted 2026-08-06 and capability-verified 2026-08-07.

CORRECTION, 2026-08-07: ProjectsV2 is NOT GraphQL-only. That claim was true when this file was written and is now stale; it survived into the wrap-mark flag's premise and briefly argued for a classic PAT that the estate did not need. Verified live 2026-08-07 against api.github.com from this repo's session: `GET /orgs/ExpertPartners/projectsV2` returns the org's projects, and `POST /orgs/{org}/projectsV2/{number}/drafts` is a real endpoint on BOTH API versions 2022-11-28 and 2026-03-10 (probed with the body omitted, so both returned HTTP 422 "Invalid input: data cannot be null" citing docs.github.com/rest/projects/drafts#create-draft-item-for-organization-owned-project, and nothing was created). Independently corroborated 2026-08-06 by the Door Tools Build lane. The shipped `wrap_mark` tool uses REST, not GraphQL.

Manual fallback, only when the door is unreachable. REST, two calls:

1. Read the board to dedupe: `GET /orgs/ExpertPartners/projectsV2/1/items`
2. Create the mark: `POST /orgs/ExpertPartners/projectsV2/1/drafts` with a JSON body carrying the title and body.

Title: `Wrap: [lane] [YYYY-MM-DD]`. Body: one line pointing at the two intake paths and the ledger commit. Pointers only, no pasted state.

From Claude Code: `gh api` with the authenticated gh session. The GraphQL pair (`organization.projectV2(number:)` for the node id, then `addProjectV2DraftIssue`) still works and stays a valid fallback; it is no longer the only path. Auth needs project scope. Tokens live in 1Password only. Proven live 2026-08-05 by the Canon Doc Sync and Wrap Marks Backfill lanes (AllisonGaddy keyring identity with project scope, query-back verification per item).

Known constraint (reported 2026, community-sourced, verify before relying): `updateProjectV2ItemFieldValue` single-select changes can update the data store without updating the board-view grouping index, so a card may not visibly move columns. That is why the wrap mark is a NEW dated draft item, never a status move.

If the current surface reaches neither the door tool nor an authenticated REST or GraphQL path: say plainly the mark did not land and why, and ship the mark's dispatch block to a capable session in the same wrap turn (closeout completeness rule, SKILL.md v1.3). Never silently skip. The durable fix ordered by the shared-canonical-file-writes directive (Rule 3) shipped 2026-08-07: `update_lane_row` (tool eight, aura c64c5bb plus the Central-time fix 587b98d) and `wrap_mark` (tool nine, aura 8867a3e plus the query-back backoff fix 880beb5) both went live on the Lambda door at that point, `tools/list` briefly returned nine. `wrap_mark` has since been removed from the door, live `tools/list` returns eight. Both were caught out by their own first live run, the ledger tool on timezone and the wrap tool on board-index lag, neither reachable by unit test; proving-live is the standard for door tools.

RETIRED IN HALF, 2026-08-06 (same ruling as the section head). The ORDERED durable fix above pairs two tools, and only one half survives the ruling. The `update_lane_row` half STANDS, it serves an active wrap step and is unaffected. The `wrap_mark` half is MOOT, the protocol step it was built for no longer exists, so nothing in a wrap calls it. The tool has since been removed from the door entirely. Disposition settled as of 2026-08-07, see the corrected line above and the ruling at aura intake/2026-08-08-ruling-eval-finding-b-mcp-and-dashboard-reference-correction.md.
