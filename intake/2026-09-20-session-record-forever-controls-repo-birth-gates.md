---
classification: internal
classification_owner: allison
classification_date: 2026-09-20
date: 2026-09-20
source: codex
topic: forever-controls-repo-birth-gates
---

# Forever Controls Step 3: canonical skills and sequencing blocker

SESSION: Forever Controls - Repo Birth Gates
Codex HOME: NORTH'S ESTATE CONTROL TOWER / Repo Tower

## Scope and current authority

This pass implements only P9 and P10 in canonical expert-partners-skills sources. Worktree: `/Users/allisongaddy/Claude/projects/worktrees/forever-controls-repo-birth-gates-20260920/expert-partners-skills`. Branch: `forever-controls/repo-birth-gates-20260920`. Fresh base: `bc44ba99489f95281029d06c7120d6e6dc578042`. Task id: `01a0c0b5-42da-7f83-a1f7-71cfc67c1909`, title set and independently read back.

Read live through Estate Brain: Manifest v1.20, `aura/intake/2026-09-20-session-record-forever-controls-topology-authority.md`, `aura/intake/2026-09-19-session-record-controls-review-lane-5-forever-controls-prefl.md`, ADR 0056 and ADR 0078. Fresh Aura reference: `874e7aa6fc56acceb23b82929ef9c1a5948b6695`. Read-only source snapshots in temporary directories avoid the extractor's unrelated absolute-path exclusion for directories named worktrees. No Aura tracked file was changed. Open skill PRs #6, #9 and #18 were checked and do not own these two skill files.

The manifest is current topology authority, not the old preflight's roster counts or unresolved dispositions. ADR 0056 and ADR 0078 remain rule authority; this pass adds no ADR or competing repository standard.

## Changes prepared

- repo-standards v1.2 reads the Entity index in Stage A, recognizes archived owners as revival candidates, requires a landed and independently read-back Entity row in Stage B, and reports missing rows as UNREGISTERED / REMEDIATION REQUIRED with row-only scope in path three.
- Readiness compares the live description and pinned default-branch identity against the row stamps using the manifest's exact whitespace, case, H1 and one-hop import rules. Missing sources are gaps, never passing stamps. The unchanged frontmatter description remains 993 characters.
- Codex's `.agents/skills` mirror is recognized as a deployed copy produced by the existing pipeline. No deployed copy or upload artifact is produced in this pass.
- new-project calls current canonical repo-standards Stage A before any bootstrap mutation. USE EXISTING REPO stops creation, and only NEW REPO JUSTIFIED can reach bootstrap and Stage B. A pending door queue never substitutes for an Entity row. `calls: [repo-standards]` records the graph relationship.
- The host bootstrap script is inspected, not changed or executed. Its S1 wording names the completed Synapse worker lane, not a Make scenario, proven by Aura `project-knowledge/planning/synapse-sprint-control-tower.md` and `project-knowledge/pending-canonical-repos.md`. The queue still exists but its existence proves neither an active automatic sync nor serving registration. The skill now distinguishes topology registration from a conditional pending door-registration handoff and avoids hand-editing the deployed intake skill.
- The fresh scan source still lacks `--stamp`. Stage B verifies command availability and uses the shipped shared parser's `sha12` and the manifest's live-source contract when integration has not landed. It does not claim the simultaneous governance-scan worker's implementation is already deployed.

## Validation before PR

| Check | Observed result |
| --- | --- |
| Description lint and fallback selftest | PASS, 41 tracked skills, 40/40 fixtures |
| Brand lint | PASS on both changed skills |
| Classification/frontmatter lint | PASS on both changed skills |
| Ruling provenance selftest | PASS, all seven fixtures |
| Ruling provenance staged diff | PASS, two skill files, zero breaches |
| Gitleaks full history | PASS, 271 commits, no leaks |
| Extractor fixture suite | PASS, 22/22 |
| Deployment contract suite | PASS, 53/53 |
| Baseline live-canon graph extraction | PASS, 56 nodes, 83 edges, 17 deployed mounts |
| Proposed graph extraction against unchanged current Aura | FAIL, exactly the two stale repo-standards mounts |
| Diff whitespace check | PASS |

## Cold behavioral cases

The skill-creator fresh-reader workflow used three independent agents with no inherited conversation. One read only the proposed repo-standards text, one read only both proposed skills, and one read only the two baseline texts. Tool facts were explicit simulated fixtures; no actual repository, Project, registration or bootstrap was created. These are behavioral instruction tests, not the excluded G5 campaign and not proof of live deployment. The two current readers passed all seven requested cases; the old-text reader passed only R1 and R4 under the new acceptance criteria, exposing the intended regression gaps.

| Case and fixture | Observed proposed-skill behavior | Result |
| --- | --- | --- |
| R1: propose shared content production; current content-engine Entity row and live canon already own it | USE EXISTING REPO, names content-engine and Estate, creation stops | PASS |
| R2: bootstrap and baseline pass, but only a pending queue entry exists | Refuses completed birth; requires landed Entity row, validation and independent readback | PASS |
| R3: material work, all other readiness inputs pass, no Entity row | REMEDIATION REQUIRED; UNREGISTERED; smallest scope is registering the existing repo's row, no restructure | PASS |
| R4: casual content-engine mention followed by sentence rewrite | Rewrites the sentence without invoking a repo audit | PASS |
| R5: fresh surface with only the skill, stamp integration absent | Same ADR and Entity authority reads and gate routes; direct shared-parser verification preserves registration gate; mirror is deployment only | PASS |
| N1: /new-project ContentWorkshop for content-engine's existing job | Stage A returns USE EXISTING REPO; no script, repo, home, bootstrap commit or pending entry | PASS |
| N2: /new-project ExperimentalCorpus with no owner and justified boundaries | Stage A, then bootstrap, then Stage B including Entity row on Aura main and independent readback; failed row landing keeps birth incomplete | PASS |

The N2 reader also distinguishes historical S1 wording from an active sync, keeps door-serving status separate, and refuses to treat the legacy script's DONE output as baseline proof. The R5 reader preserves direct stamp checks when scan integration has not landed. Baseline R2 allowed birth with the seven old items, R3 returned READY without a row, and baseline new-project could run the script without invoking Stage A. Baseline caveats about possibly stronger ADRs do not supply the missing explicit skill controls.

## One concrete blocker

The current skills-graph workflow checks out Aura main and runs `extract-skills-graph.mjs`. Its pass 3 treats any difference between a deployed skill's body and current canonical source as a fatal error, including legitimate version staleness. A separate later workflow step describes deployment staleness as a nonblocking notice to avoid cross-repo deadlock, but extraction has already failed before that notice can help. The existing stale-mirror fixture confirms this is enforced behavior, not a transient tool failure.

Untouched canonical sources plus fresh Aura pass. Replacing only the two proposed skill files in that verification snapshot fails on exactly:

- `aura:.agents/skills/repo-standards/SKILL.md`
- `aura:.claude/skills/repo-standards/SKILL.md`

Both diagnostics say the deployed copy is not a faithful render of `eps:skills/repo-standards/SKILL.md`; build exits 1 with two errors. Therefore P9 cannot both change canonical repo-standards and keep skills-graph green while the dispatch explicitly defers Aura redeployment. No graph output is fabricated or hand-edited, no CI check is bypassed, and the PR must not merge in this state.

Smallest safe closing move: NORTH'S ESTATE CONTROL TOWER / Repo Tower must authorize the narrow CI/deployment sequencing repair. Recommended bounded scope is to distinguish a verified prior canonical deployment from corruption during canonical graph generation, retain fatal header/identity/integrity checks, and retain the dedicated Aura deployed-copy drift gate and explicit staleness notice. That preserves the requested canonical-first rollout. This is a separate gate-behavior change, not silently included in P9/P10. An alternative coordinated mount rollout would require an explicit change to the present no-Aura-deployment boundary and a two-repo CI sequence.

## Boundary and handoff

No Aura mount, host new-project copy, standalone zip, project-builder, governance-scan implementation, G5 campaign, GHL Cleanup, recruiting harvest or Lane 6 baseline is changed. No SOP is created or revised; these are existing canonical skill implementations and validation evidence. This worker does not edit Aura's lane ledger under the explicit canonical-skills-only boundary. Home should retain the lane open, waiting on the named CI/deployment sequencing decision, stale date 2026-09-27. No merge, landed v1.2, or regenerated canonical graph is claimed.

Resume in this same task after the sequencing scope is authorized. Read this record and the draft PR, re-fetch both repositories, apply only the authorized repair, rerun CI and cold cases if behavior changed, require green checks, then independently verify merged skills and generated graph. No further skill-design decision is waiting on Allison.

## Canonical candidate hashes

- `skills/repo-standards/SKILL.md`: SHA-256 `40266d850f2a1d7aaa8617c0fbf35e55098c18911a26f7f6123e4b6201e43426`.
- `skills/new-project/SKILL.md`: SHA-256 `c6d29e72a1f6023b6cc65f07486fb7ea6b6431b7dbd18e9e6c964bed53c9af37`.


## Authorized sequencing repair, 2026-09-20

Allison authorized a narrow implementation repair in this same task and PR #30: distinguish a provable pipeline render of a prior committed canonical version from corruption, preserve fatal integrity failures, keep the canonical-first sequence and the explicit deferred deployment warning, and leave Aura's deployment gates and all excluded surfaces untouched. This is task-scoped implementation authorization, not a new ADR or a claim that a durable rule was locked.

The graph extractor now accepts a differing deployed SKILL.md only after `historical-deployment.mjs` proves the whole deployed directory against the same canonical path in the checked-out repository's first-parent history. It verifies the exact three-line pipeline header position, a real deployment date, the version or tree stamp (including historical plugin metadata when relevant), every source-file byte, the complete file set, and the exact SHA-256 manifest. Git replacement objects are disabled for proof; other branches, tags and dangling objects are not searched. Missing or shallow history fails closed when the matching version cannot be proven. Graph records carry VERIFIED STALE, awaitingRedeploy, canonical commit and blob; warnings explicitly retain Aura's redeploy debt. CI reads full history for both existing checkouts. The producer, Aura workflow and all mounts remain unchanged.

Regression fixtures use the actual deployment script. The expanded extractor suite passes 38/38: three historical proof successes plus failures for modified skill bodies, altered/missing/extra reference files even with recomputed manifests, missing/altered manifests, false stamps, moved/invalid/missing headers, wrong ownership, orphaned canonicals, unrelated branch history, shallow history and symlinks. The original duplicate, orphan, header, schema and dangling-reference tests remain. The successful stale fixture separately proves the unchanged deploy-skill --verify check still rejects that old deployment. Deployment contract tests pass 53/53; all 40 upload-preflight skill sources pass without building an upload artifact. An independent read-only review of the allowance found no path for unproven or altered bytes to receive VERIFIED STALE.

The requested fresh-reader behavioral rerun read only the two proposed skills with no inherited conversation. All seven cases and the N2 failed-registration branch pass again. These remain simulated tool fixtures, not actual repository births or G5 tests. Brand, frontmatter, description selftest, provenance selftest and working-tree secrets checks pass.

Live-history proof against EPS commit 35d17e7 and fresh Aura a58a43b independently proves both unchanged repo-standards mounts against EPS canonical commit `d5eb64d6b71f209e4a998466cb6790d76314cbbb`, blob `6d0557563490ceaea358729b2b0b8dfbd8cedf52`. Their full deployed trees and manifests pass the historical comparison.

Graph generation then exposes a separate pre-existing layout restriction previously hidden behind the fatal mount mismatch: `cross-zone calls edge new-project -> repo-standards (routing -> hands): per-zone layout cannot route it`. The required calls edge and both existing skill zones remain intact. No relationship is dropped or relabeled to evade that failure. The later authorization is limited to historical-copy proof, so the live task asks for a separate, narrow cross-zone routing authorization before changing layout behavior. Until resolved, PR #30 remains draft and unmerged; no regenerated main graph is claimed.

## Authorized cross-zone layout repair, 2026-09-20

Allison subsequently authorized the narrow hierarchical build-time ELK repair in this same task and PR #30. The required semantics remain: new-project in routing, repo-standards in hands, and their real calls relationship. No skill zone, relationship type, brand parent, integrity proof or deployment gate changes. The historical-copy helper, extractor implementation and workflow are byte-identical to the authorized sequencing commit c3c59a0.

The former per-zone loop is replaced by one layered INCLUDE_CHILDREN hierarchy with the same compound zones and nested brand rooms. The established rightward flow, padding and labels remain; a fixed random seed makes identical inputs reproducible. All drawable relationships enter ELK, including calls and defers-to across zone or nested-room boundaries. Each returned edge container supplies the origin for absolute SVG coordinates. Inherits remains excluded from ELK and has null geometry. Missing or nonfinite route geometry now fails generation instead of silently disappearing. Layout still runs only at build time; the existing static SVG renderer and browser architecture are unchanged.

Validation against live Aura main `0d0f7b746d6806f6028dc25192936dbece074ce7`:

- All 47 graph tests pass: the previous 38 extractor/integrity tests remain, two extractor integrations cover cross-zone edges and dangling defers-to/inherits, and seven layout cases cover cross-zone calls/deference, intra-zone routing, all containment/labels, both brand parents and the joint room, collapsed inheritance, determinism, dangling references and missing geometry.
- All 53 deployment contract checks pass. Current-copy verification continues to reject stale copies; no deploy producer or Aura gate was modified.
- Full graph generation passes: 56 nodes, 84 edges, 29 visible calls/defers-to routes, six zone containers and seven brand rooms, 1423 by 4211 layout. Every pre-existing relationship survives, with exactly the required new-project calls repo-standards edge added. Independent checks compare all zone and brand assignments, captions, parent links, endpoint boundaries, orthogonal points, viewport bounds and route/node intersections against the baseline graph.
- Both unchanged Aura repo-standards mounts still report VERIFIED STALE with the same historical commit/blob proofs and explicit awaiting-redeploy flags.
- An isolated copy of the existing FounderCommandCenter static React SVG components rendered the generated JSON with no renderer modification. All 29 arrows render, including the cross-zone calls arrow. The full image and endpoint crop were visually inspected. No dashboard source or deployed surface was edited.
- A new independent reader, given only the two candidate skills and simulated tool fixtures, reran R1-R5 and N1-N2 plus the failed-registration branch. All pass: existing owner stops creation; justified creation orders Stage A, bootstrap, Stage B and landed row; absent row blocks birth and gives row-only readiness remediation; a casual mention triggers no audit; direct shared-parser stamps work when scan integration is absent. These are cold instruction tests, not actual repository births and not G5.
- Description/fallback, brand, classification, ruling-provenance selftests and full-history secrets checks pass. GitHub checks and protected merge remain required before any landed-completion claim.

The two earlier blockers are resolved in this candidate. The later Aura redeploy step remains an explicit Lane 5 handoff, outside this worker's scope. No excluded surface was changed. Final landed evidence belongs in the closeout note after protected merge and independent graph readback.
