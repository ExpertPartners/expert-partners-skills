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
