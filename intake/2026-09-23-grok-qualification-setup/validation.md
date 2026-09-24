---
classification: internal
classification_owner: allison
classification_date: 2026-09-23
date: 2026-09-23
source: Grok Repo Templates - Qualification Setup artifact checks
project: expert-partners-skills
captured_at: 2026-09-23T20:48:09.432639+00:00
topic: preparation validation and explicit evidence limits
---
# Preparation validation

DRAFT / NOT RELEASED. These checks validate preparation artifacts only. No candidate turn, behavioral test, Gate A grade or acceptance decision occurred.

## Validation contract map, before this continuation's repair

| Object | Existing claim and check at reviewed head `e848326` | Required completion in this batch |
| --- | --- | --- |
| Seven withheld source pins | Fixed path order, source commit/blob, SHA-256, byte size, live checked-out bytes and URL were checked. | Exact object keys and field types; fixed repository, algorithm and commit relationships. |
| Candidate source inputs | Six inputs and mode-scoped paths were compared to values copied from withheld pins. | Exact allowlisted top-level and per-input fields, then explicit candidate expectation from permitted fields. |
| Coverage matrix | Case IDs, modes, request hashes, variant IDs, two-run lists and counts were checked. Scenario text was only tested for nonemptiness. | Exact object schemas and types; independently anchored hash of the 72 reviewed variant/scenario text pairs. |
| Aggregate receipt | Draft/NOT RUN/UNPROVEN, source commit, counts, shard list, and blank pre-run/repeat values were checked. | Exact top-level schema and types, including rejection of added result/approval claims. |
| Four receipt shards and nested rows | Shard top-level keys, nested case-run and variant keys, statuses and blank fields were checked, then rows were pooled. | Bind each filename to group, run number and its own ordered case/run identities while preserving nested exact checks. |

The map describes documentary preparation validation. It cannot establish candidate context isolation, a complete action trace, or behavioral qualification.

## Completed checks

| Check | Result and scope |
| --- | --- |
| Read-only package validator | PASS. Seven exact source blobs/SHA-256 values, exact canonical requests and withheld rubric, 38 cases, 72 variants, 76 full-case receipt slots, 144 required NOT RUN judgments; no populated runtime/grade fields. |
| Receipt schema hardening | PASS. Exact top-level field set enforced on all four receipt shards. Exact key sets enforced on `pre_run_release_checks` and `repeat_comparison`, including its `status` field. Existing exact nested case-run and variant checks remain in place. |
| Negative schema probes | PASS. Six temporary-copy mutations were independently rejected for the expected schema reason: extra shard result field (`gate_a_status: PASS`), missing shard field, extra and missing pre-run check key, and extra and missing repeat-comparison key. The canonical package was not mutated. |
| Complete source/candidate pin contract | PASS. Exact top-level and per-input keys and types are required in both pin files. Candidate expectations use an explicit permitted-field allowlist. Matching unexpected metadata in both files is rejected before any candidate-boundary PASS. Commit, blob, SHA-256, byte size, URL, path, repository and algorithm checks remain. |
| Coverage and scenario integrity | PASS. Coverage and case/variant schemas and types are exact; existing case/mode/request/run bindings remain. The 72 reviewed `(variant_id, scenario)` pairs are bound to a fixed SHA-256 anchor captured from the unchanged `e848326` package: `913762fdcf90d9b3faf1782c46eeee651a9367755d856ce04c7a7e717e818f9c`. |
| Aggregate receipt and shard binding | PASS. The aggregate has exact top-level keys, fixed draft/NOT RUN/UNPROVEN states, typed counts and blank release/repeat fields. Each shard filename binds to its group, run number and ordered case/run identities; existing nested result schemas remain exact and blank. |
| Expanded regression suite | PASS. Expanded dedicated probes reject matching pin metadata, added/missing/renamed/wrong-type fields, aggregate result claims, same-group and cross-group shard swaps, altered nonempty scenarios, and broken source/path/hash/mode bindings for their intended reasons. With the retained six built-in probes, the dedicated suite currently exercises 43 negative checks (46 JSON mutations plus two CLI symlink probes). No real receipt or scenario was edited. |
| Second-round file and path integrity repair | The independent review of `414ee931` found that an extra result file, a symlinked top-level package argument, and bytecode emitted by the test loader could escape the preparation check. The validator now requires the exact 24-file package set plus its manifest, verifies every manifest-listed file hash and byte size, and rejects a symlink before path resolution, including symlinked ancestors of `--package`. The regression loader disables bytecode emission and compares package file hashes before and after testing. The fixed coverage Markdown hash also anchors its 72 scenario rows. |
| Second-round regression expansion | Five additional disposable-copy mutations cover a changed Markdown scenario, two extra result/shard files, an unmanifested narrative edit and a missing manifest entry. A CLI subprocess probe rejects a symlinked package argument. The full suite now contains 54 negative probes: six built-in plus 48 dedicated (46 JSON mutations including review_pr/source-manifest cross-checks, plus two CLI symlink probes). Each must reject for its named reason. |
| Current source check | PASS. GitHub main independently read as `3096df35aac141e1cea8d77014e0f1d1ea1dad05`; all seven input SHA-256 values match the pinned working tree and source manifest. |
| Candidate boundary | PASS for artifact content. Exactly four candidate files; no rubric, expected-answer fields, prior response or grading material. This does not prove runtime access isolation or safe transitive reads. |
| Independent semantic review | Two contained draft corrections applied: 76 slots cannot establish sufficient independent executions, so actual presentation count remains unresolved and each variant has native-run-ID/isolation fields; approval wording preserves explicit approval by an authorized approver. |
| Brand and classification | Existing `.ep/brand-lint.py` and `.ep/frontmatter-lint.py` pass on all changed Markdown. |
| Ruling provenance | Existing `.ep/ruling-provenance-lint.py --pre-commit` passes. No proposal is marked accepted or promoted to governing truth. |
| Skill description cap | Existing `.ep/skill-description-lint.py --selftest` passes, 41 skills, tightest headroom 2. No SKILL.md changed. |
| Syntax, hygiene and scope | JSON parse/Python AST, whitespace, final newline, no conflict markers, files below 50 KB and exact authorized-additions scope checked in final assembly. |
| Local relative links | Checked after this record was assembled; links resolve within the authorized worktree. The first preassembly link pass correctly reported this not-yet-created validation record and was rerun after creation. |
| Collision | 19 registered skills worktrees checked for these exact paths, no other changed-path collision. All three open skills PR file scopes were read, none overlaps. Native task inventory and complete current Aura ledger show no other current same-Table Worker. |
| Secret scan | Existing gitleaks scans prepared package and source repository history with redaction enabled. No credential extraction or candidate account inspection was needed. Prepared package scan: zero findings. Repository-history scan: 296 commits, zero findings. Hosted checks will be recorded with the PR verification receipt. |

## Reproduce package checks

From the isolated owner worktree run `python3 -B intake/2026-09-23-grok-qualification-setup/validate-package.py --repo . --negative-probes`, then `python3 -B intake/2026-09-23-grok-qualification-setup/test_validate_package.py --repo .`. The first command checks the untouched canonical package and six original negative probes; the second repeats the positive check and runs 48 dedicated probes (46 JSON mutations plus two CLI symlink checks). Both read local files and Git objects; probes write only to disposable copies. Neither contacts a model, runs a candidate, creates a registry, or tests a business repository.

Use the existing `.ep/` changed-file brand/classification/provenance gates and the repository CI workflow. The complete canonical skill/profile/case/rubric diff is empty; only the admitted preparation files change. No deployment or generated-copy test was needed because no producer or deployed source changed. No software was installed for these checks.

## Evidence limits and publication

No Gate A runtime execution, no-write trace, independent-context demonstration, Gate B acceptance, Gate C exam, Gate D eligibility, target audit, nontechnical-human acceptance, or mechanical credential-enforcement test is claimed. All source-review findings remain OPEN.

The actual Bot account's plan and enabled recording are unverified. First-party documentary feasibility is separately identified in the route assessment. User-carried onboarding reports preserve the Shell failure and native-Read retry without promoting either to a trace-backed qualification result.

The owner repository is private. The original preparation was staged in a review PR, not published to authoritative main at that capture. The own-row Aura lifecycle update subsequently landed at `58c1b4e40af15306bf1c39c9d434403a8c0e1b07`. This validation record establishes package consistency and negative-probe behavior, not publication or qualification. The live PR and Aura row carry the actual publication disposition and remaining NORTH-owned waits.
