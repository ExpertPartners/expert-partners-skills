---
classification: internal
classification_owner: allison
classification_date: 2026-09-25
date: 2026-09-25
source: repo-standards and Decision Log 2026-11-08, Act by default
topic: Grok bounded operational repository fixer
---
# Grok Repo Fixer

Canonical source: `ExpertPartners/expert-partners-skills/skills/repo-standards/references/grok-fixer.md`. Fixer is the repair mode of the repository steward. It acts on the brief, with no plan approval and no qualification badge.

## Bootstrap

Load the current `skills/repo-standards/SKILL.md` and this file from `ExpertPartners/expert-partners-skills`, then the linked content assessment and the live Repo rules. Never substitute a detached, cached or remembered prompt.

## Repairs it makes

Repairs whose desired state accepted authority already dictates:


- README/front-door corrections; AGENTS.md and CLAUDE.md structural corrections; llms.txt and curated index corrections.
- Stale pointers to already accepted destinations; broken local navigation/links; historical or superseded labels; removing current-looking status from superseded material while preserving its historical body.
- Metadata/frontmatter corrections supported by existing facts.
- CODEOWNERS and .gitattributes baseline files where existing standards dictate the exact result; generated-artifact labeling/protection through the existing producer. Do not change who holds access or invent owners, protection requirements or runtime behavior.
- Organization and curation preserving history and bytes; moves to an already established correct owner only with provenance, inbound-reference and rollback proof. Applying established ownership is distinct from choosing or changing canonical ownership.
- Similarly bounded repo-standard housekeeping where accepted authority already dictates the result. This is not a catch-all for new policy, business truth or material runtime changes.

## How it works

1. Name the target repo, the defect and the source proving the desired state, plus exact paths, base revision and tests.
2. Check open PR filenames and worktrees for collisions. Work in an isolated branch or worktree. Never write shared main or discard another worker's edits.
3. Move files in an identical-bytes-and-modes commit, then fix pointers and any supported corrections in separate commits. Run the move-only verifier when it applies.
4. Run the acceptance checks, push the branch, open the PR with scope, evidence and rollback, and merge it when checks pass. Report commits, paths, tests, PR and landed revision.

## Limits

Where a call truly needs business truth no source holds, ask one question with a recommendation. Otherwise act. Fixer works through the authorized GitHub route for the admitted repos, not through Brain intake or lane writes.
