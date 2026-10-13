# Repo Standards audit record template

File as a Google Doc titled `repo-standards-audit-<repo>` in the owning brain's
home folder in Drive (HQ Business Brain if none).

```markdown
---
classification: internal
classification_owner: allison
classification_date: YYYY-MM-DD
date: YYYY-MM-DD
source: repo-standards-skill
topic: repo audit
project: <repo>
captured_at: <ISO 8601 UTC>
---
# repo-standards-audit-<repo>

Audited against aura decisions/0056-repo-baseline-standard.md, read this
session at <commit or fetch time>. One repo per pass. Grades cite evidence
read live, never memory.

| # | Point | Grade | Evidence |
|---|-------|-------|----------|
| 1 | Hardening | PASS/FAIL/N/A | <org ruleset ids in effect, secret scanning state, token classes> |
| 2 | Bot commit routing | | <scheduled workflows and their target branches> |
| 3 | Generated-artifact gates | | <.gitattributes, CODEOWNERS, banner, CI diff gate> |
| 4 | Root agent instructions | | <AGENTS.md line count, CLAUDE.md import> |
| 5 | File-size discipline | | <largest knowledge files, any past ~50KB> |
| 6 | Frontmatter metadata | | <sample coverage, ADR 0025 fields> |
| 7 | Intake compaction | | <inbox size, distillation cadence, archive rotation> |
| 8 | Deployed-copy drift control | | <version stamps, checksum manifests, producer> |
| 9 | ADR integrity | | <MADR format, numbering gaps, CI validation> |
| 10 | Retrieval readiness | | <curated index present and described> |

## Content architecture assessment

Verdict: READY / REMEDIATION REQUIRED (not a new ADR grade).
Action recommendation: ORGANIZE EXISTING REPO / none.
Scope: <authorized paths; excluded surfaces; baseline commit>.
Canon reads: <ADR 0056, 0078, metadata/handling rules, Manifest and applicable
owner decisions, each with revision or fetch time>.

For an explicit Phase Two / Repo Design Tower pass, read the digest before
design and keep the following three layers separate. A bounded design-only
report may reuse this section without claiming an audit or baseline grades.

| Evidence layer | Sources + revision / fetch time | Finding and permitted use |
| --- | --- | --- |
| Accepted Estate canon and decisions | | |
| Phase Two research evidence | <filed digest; cited sections; original only if insufficient, with escalation question> | Evidence only |
| Live target-repository evidence | <in-scope inventory, consumers; uninspected areas> | |

| Boundary | Evidence / unresolved gap |
| --- | --- |
| Durable job and Entity row | |
| Owner and current Entity type | |
| Owns | |
| Consumes by pointer | |
| Does not own | |
| Systems of record outside GitHub | |
| Human front door and correction route | |
| AI front door | |
| Curated index and producer | |
| Intake / research / sources / generated / history handling | |
| Open PRs / live workers and overlapping paths | |

### Front-door and job-coverage gaps

<Answer job, owner, trusted/current source, exclusions, correction route by
following links. Record missing operating knowledge separately from filing.
A technically compliant but unusable front door remains incomplete.>

### Content inventory and dispositions

One bounded row per assessed item; name coverage and omitted paths. Use the
source's existing kind/status terms, not the research's proposed schema.

| Path + revision | Kind / current authority + evidence | Owner / handling | Accuracy | Completeness | Usefulness | Freshness | Disposition + rule mapping | Executed / proposed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <path> | <authority assessed independently> | | | | | | <ALREADY RULED / SAFE IMPLEMENTATION OF EXISTING RULE / PROPOSED BASELINE AMENDMENT REQUIRING ALLISON; source> | |

### Conflicts and needs review

<Claims and source pointers, current status and supersession evidence, owner,
stop condition, exact resolving evidence. For sensitive material, path and
handling flag only; do not copy private contents.>

### Smallest reversible execution batch

<Paths, existing authority, permitted actions, accepted destinations,
source revision/hash, inbound consumers, pointer/alias requirements,
separate move-only and semantic commits, rollback, and gated exclusions.>

### Founder decisions required

<Exact proposed rule, why current canon does not cover it, dependent
automation, compatibility/migration impact, recommendation. Proposal only.>

### Deterministic verification plan and results

<Existing schema/lint commands, link and inbound-consumer coverage,
move-only check where applicable, generator run twice with byte and file
inventory comparison, retrieval questions with expected owning paths,
actual results and limitations. For Phase Two, include fresh-AI and
nontechnical-human prompts, routes, answers and failures. Label simulations
and unrun tests honestly. Record pilot outcomes and class-specific exceptions
before proposing any universal standard; pilot success is not adoption.
No test can replace semantic verification.>

## Fixes applied this pass
- <what, commit hash, branch, merged how>

## Flags for Allison (gated, destructive, or business-truth)
- <one named line item each, with a recommendation>

## Known open findings carried, not blocking
- <e.g. aura lane ledger breakup, its own lane per the ADR carve-out>
```
