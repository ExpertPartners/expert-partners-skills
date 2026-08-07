# Repo Standards audit record template

File as `intake/YYYY-MM-DD-repo-standards-audit-<repo>.md` in the audited repo
(aura intake/ when the repo has no inbox). Frontmatter per ADR 0025.

```markdown
---
classification: internal
classification_owner: allison
classification_date: YYYY-MM-DD
source: repo-standards-skill
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

## Fixes applied this pass
- <what, commit hash, branch, merged how>

## Flags for Allison (gated, destructive, or business-truth)
- <one named line item each, with a recommendation>

## Known open findings carried, not blocking
- <e.g. aura lane ledger breakup, its own lane per the ADR carve-out>
```
