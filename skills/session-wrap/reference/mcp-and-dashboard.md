# Wrap mechanics: MCP writes, ledger, dashboard mark

Volatile mechanics live here, dated, verified at use time. Nothing in SKILL.md depends on them.

## Intake push

Tool, fully qualified: `Estate Brain:save_to_session_intake`
Args: `project` (canonical repo name, normally `aura`), `content` (the full markdown), `title` (slug source, e.g. `session-record-[lane]` / `continuity-[lane]`), `classification` (`internal` unless ruled otherwise, ADR 0025).
Behavior: append-only, writes `<repo>/intake/YYYY-MM-DD-<slug>.md`, never overwrites (ADR 0027). Verify: the response must return the written path. Echo the exact path in the confirmation. No path returned means the write failed, use the fallback (downloadable .md plus a plain statement of the failure).

## Lane ledger

File: aura `docs/estate/lanes.md`. Update this lane's row with the closeout state per the code-block-routing skill's ledger rules. From Claude Code, commit directly. From Chat or Cowork, use the GitHub connector file write (whole-file write on main, reversible under ADR 0047).

Collision guard, mandatory (incident 2026-08-04, first live wrap): the ledger is a shared concurrent-writer file, and a whole-file write can silently revert or drop sibling rows written between your read and your write. So, in order: (1) read the ledger IMMEDIATELY before writing, never from an earlier point in the session; (2) after the write, fetch the commit's full patch and verify it contains ONLY this lane's row change; (3) any reverted or dropped sibling line gets restored in a corrective commit BEFORE the wrap continues, and the incident is named in this lane's row and in the confirmation. Never report the ledger step done on the push alone.

Directive binding, added 2026-08-05 (Allison's ruling of 2026-08-04 after the second regression incident): the shared-canonical-file-writes directive (aura `docs/directives/shared-canonical-file-writes.md`) governs every ledger write and wins if this section ever lags it. Three additions beyond the guard above. Any contents-API write MUST pass the current blob SHA (compare-and-swap) so a stale write bounces instead of landing. After two SHA-guard bounces in one wrap, the writer stops racing and routes the row verbatim through an intake handoff note for the next git-based writer to fold in, and a routed row plus a plain statement is a correct wrap. Corrective commits restore only from a FRESH read taken at repair time, never from a copy held earlier in the session, because the held copy may be missing newer healing by the owning lanes (this exact near-miss happened 2026-08-04 and only the SHA guard stopped it).

## Dashboard wrap mark (hq.allisongaddy.com)

The dashboard is a stateless read-only render of the Founder Active Work board (github.com/orgs/ExpertPartners/projects/1). The wrap leaves its mark ON THE BOARD, never via a second dashboard render path (one source of truth). Ruled mechanism, one dated draft item per wrap.

ProjectsV2 is GraphQL-only (no REST for new Projects). Two calls:

1. Resolve the project node ID (cache it once known):
```
query { organization(login: "ExpertPartners") { projectV2(number: 1) { id } } }
```
2. Add the mark:
```
mutation($projectId: ID!, $title: String!, $body: String!) {
  addProjectV2DraftIssue(input: {projectId: $projectId, title: $title, body: $body}) {
    projectItem { id }
  }
}
```
Title: `Wrap: [lane] [YYYY-MM-DD]`. Body: one line pointing at the two intake paths and the ledger commit. Pointers only, no pasted state.

From Claude Code: `gh api graphql` with the authenticated gh session. Auth needs project scope (classic PAT or app token; fine-grained PAT support for org ProjectsV2 writes is unverified as of 2026-08-04). Tokens live in 1Password only. Proven live 2026-08-05 by the Canon Doc Sync and Wrap Marks Backfill lanes (AllisonGaddy keyring identity with project scope, query-back verification per item).

Known constraint (reported 2026, community-sourced, verify before relying): `updateProjectV2ItemFieldValue` single-select changes can update the data store without updating the board-view grouping index, so a card may not visibly move columns. That is why the wrap mark is a NEW dated draft item, never a status move.

If the current surface has no GraphQL path or no credential: say plainly the mark did not land and why, and ship the mark's dispatch block to a capable session in the same wrap turn (closeout completeness rule, SKILL.md v1.2). Never silently skip. Durable fix ORDERED (shared-canonical-file-writes directive, Rule 3): the Estate Brain ledger-row tool and the wrap-mark tool ship together in one dispatched Code build at the Phase B cutover decision; missing that dispatch at cutover is a directive violation.
