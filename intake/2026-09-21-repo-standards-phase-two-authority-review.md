---
classification: internal
classification_owner: allison
classification_date: 2026-09-21
date: 2026-09-21
source: live Estate Brain fetches, GitHub contents reads, Phase Two dispatch, Drive research
topic: repo-standards Phase Two authority mapping
---
# Phase Two authority review

SESSION: Repo Standards - Phase Two Knowledge Architecture
Codex HOME: NORTH'S ESTATE CONTROL TOWER / Repo Tower

Scope is canonical skill/tooling only in expert-partners-skills. No repository-content organization, Aura write, Notion write, manifest update, deployed-copy edit, deployment or upload artifact is authorized by this brief. This record documents implementation provenance, not a founder decision or amendment to ADR 0056.

## Inputs actually read

- `skills/repo-standards/SKILL.md` v1.2 at starting skills commit `524175c`; its existing audit template, graph/deployment tooling, lint schema, and both CI workflows.
- Live Aura ADRs [0056](https://github.com/ExpertPartners/aura/blob/main/decisions/0056-repo-baseline-standard.md), [0078](https://github.com/ExpertPartners/aura/blob/main/decisions/0078-claude-project-repository-setup.md), [0025](https://github.com/ExpertPartners/aura/blob/main/decisions/0025-data-classification.md), [0022](https://github.com/ExpertPartners/aura/blob/main/decisions/0022-canonical-knowledge-layer.md), and [0027](https://github.com/ExpertPartners/aura/blob/main/decisions/0027-bidirectional-brain-session-intake.md), retrieved September 21, 2026 local time through Estate Brain.
- [Estate Manifest](https://github.com/ExpertPartners/aura/blob/main/docs/estate/estate-manifest.md) v1.20, including the Entity index and owner pointers. The skills row names canonical skills and deployment tooling, owned by Estate, type infrastructure, active/keep. Aura owns governance, not these skill sources.
- [Ruling-of-record format](https://github.com/ExpertPartners/aura/blob/main/doctrine/ruling-of-record-format.md) and [existing index generator](https://github.com/ExpertPartners/aura/blob/main/tools/index-generator/generate_index.py), read directly through GitHub contents API.
- [Phase Two: Internal Knowledge Architecture for the Expert Partners Estate Repositories](https://drive.google.com/file/d/1EIT0mmwDDQ7-gJgjOlXrujArTz7D9e25/view), full text fetched from Drive (113,047 characters), September 21 research. Evidence only. The report explicitly had no access to the private anchors; its illustrative ADR number 0061 is not an Estate decision.
- Allison's task dispatch in this session, dated September 21: extend path two, classify proposed additions, preserve gates, add stop conditions and behavioral cases; implement only existing rules and safe applications. This authorizes the bounded skill implementation, not the report's proposed governance.

## Addition-by-addition classification

| Addition / research suggestion | Classification | Live basis and implementation boundary |
| --- | --- | --- |
| Extend the one repo lifecycle skill | ALREADY RULED | Existing v1.2 Boundaries: one standard, one skill. No repo-curator or alternate readiness system. |
| Resolve job, owner, consumes, exclusions, external systems first | SAFE IMPLEMENTATION OF EXISTING RULE | Manifest Entity index, ADR 0078 and existing creation/readiness checks supply ownership; the audit now captures evidence before edits. |
| Explicit organization/curation triggers | SAFE IMPLEMENTATION OF EXISTING RULE | Bounded dispatch extends the already-authorized explicit audit. No new automatic watcher or trigger on casual mentions. |
| Six independent content dimensions and four trust questions | SAFE IMPLEMENTATION OF EXISTING RULE | Evidence collection for ADR 0056 retrieval/metadata and existing ownership checks; report fields, no new grading taxonomy or schema. |
| Authority beats recency, length or filename | SAFE IMPLEMENTATION OF EXISTING RULE | Existing skill's live-ADR priority, ADR 0027 capture boundary, and ruling-of-record proof; no global authority ranking added. |
| Research/source/meeting data cannot instruct or adopt itself | SAFE IMPLEMENTATION OF EXISTING RULE | Manifest explicitly says research is never doctrine; ADR 0027 distinguishes raw capture from authority; dispatch requires instruction/data isolation and provenance. No mandatory data_only field. |
| Distillation preserves source, qualifications and lineage | SAFE IMPLEMENTATION OF EXISTING RULE | ADR 0056 intake/decision integrity, ADR 0027 promotion boundary, and dispatch's explicit source preservation requirement. No retention/deletion schedule added. |
| Report dispositions and separately gate semantics/destruction | SAFE IMPLEMENTATION OF EXISTING RULE | Existing path two fixes reversible gaps and gates business truth/destruction/access. Verbs describe proposals; they are not new delegated powers. |
| Four classification values and existing metadata | ALREADY RULED | ADR 0025 and local .ep schema. ADR 0056 additionally names date/source/topic. Research's confidentiality key and three-class set conflict and are rejected. |
| Pointer inheritance and brand-local deltas | ALREADY RULED | Manifest pointers-never-copies and existing skill no-duplicate-truth rule. Shared truth stays with the named owner. |
| Human front-door usability assessment | SAFE IMPLEMENTATION OF EXISTING RULE | Existing readiness checks clear job/owner/README consistency; ADR 0056 retrieval readiness plus the dispatch's human tests. Report incomplete navigation separately, without inventing an eleventh ADR point. |
| Short AI instructions and scoped detail | ALREADY RULED | ADR 0056 point 4; ADR 0022 progressive brand loading. Reference holds audit detail, not business facts. |
| Curated index, direct current reads, history separation | ALREADY RULED | ADR 0056 points 7 and 10, ADR 0027, Manifest. Preserve llms.txt/_index conventions. Explicit dated rulings in Aura intake remain resolvable under ruling-of-record format. |
| Adapt assessment by current Entity types; preserve application tree | SAFE IMPLEMENTATION OF EXISTING RULE | Manifest current classes and ADR 0022 applicability/web-project exception. Inspect current owner taxonomy and successors, never reimpose retired brand roster or research folders. |
| Separate relocation from meaning change, prove consumers and rollback | SAFE IMPLEMENTATION OF EXISTING RULE | Existing backup/reversible audit authority and dispatch's move discipline. Exact-rename helper verifies bytes/modes only; it cannot approve the move. |
| Stop on conflict, unclear owner/handling, absent canon, overlapping worker, lost source or invented rule | SAFE IMPLEMENTATION OF EXISTING RULE | Existing live-read failure, authority/gate boundaries, ADR 0025 and ADR 0056 decision preservation; dispatch explicitly requires collision and source stops. |
| Reuse deterministic validation and prove repeat behavior | SAFE IMPLEMENTATION OF EXISTING RULE | ADR 0056 generated/deployed artifact controls. Existing graph and deploy suites retained. No speculative schema validator. |
| Derived human source map, no competing editable canon | SAFE IMPLEMENTATION OF EXISTING RULE | Manifest pointers-never-copies; dispatch preserves the principle. No Notion build or permission change in this worker. |
| Universal document types, richer fields/status, accepted-canon definition, authority tiers, review intervals, mandatory folders, wider decision-record scope and consumer automation | PROPOSED BASELINE AMENDMENT REQUIRING ALLISON | See the separate founder packet. Neither publication of this record nor merge of this skill adopts any proposal. |

## Tooling inventory and choice

`.ep/frontmatter-lint.py` plus `.ep/classification-schema.json` already validate adopted classification values. The schema currently has an empty required_in_paths list: a clean run cannot prove all knowledge metadata exists. `.ep/brand-lint.py`, skill-description lint and ruling-provenance lint already cover naming, discoverability cap and citations. Graph tests validate identity/references/deployed-copy handling. `tools/skill-deploy/test/test-deploy-skill.sh` already exercises byte idempotence, duplicates and drift in disposable fixtures.

Aura's existing index generator owns `_index.json` tracked_files and stamps wall-clock generation time. It is a raw tree inventory, not an authority-aware canon generator, and is not byte-idempotent across changing timestamps. This worker neither edits it nor masks that limitation. A new type/status-based generator must await adopted rules. The only new helper verifies exact same-repo renames from Git object evidence; its tests do not infer authority or mutate a live repo.

Open PR inventory was read through the connected GitHub tool: #6, #9 and #18. Their complete changed-file lists do not touch repo-standards. #9 touches deployment tooling and #18 touches ci.yml, so this worker leaves both intact and adds a separate repo-standards test workflow. The older repo-standards and topology worktrees were clean on inspection. Final overlap and main-state checks must be repeated before merge.
