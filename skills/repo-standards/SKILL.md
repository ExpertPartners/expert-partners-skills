---
name: repo-standards
description: "Brings every ExpertPartners repo to the ruled baseline and keeps it there. Fires on every repo creation and every repo audit, whenever Allison or a dispatch says walk this repo, harden this repo, new repo, is this repo to standard, bring this repo to standard, grade this repo, or repo audit, and whenever the new-project skill scaffolds a repo. Reads ADR 0056 (aura decisions/0056-repo-baseline-standard.md) as its single source of truth and checks the ten points without ever restating them as its own canon. Creation path births a repo to standard (AGENTS.md with CLAUDE.md import, frontmatter from file one, curated index, .gitattributes and CODEOWNERS scaffold, org ruleset inheritance confirmed). Audit path grades a named repo pass or fail per point, fixes reversible gaps in the same pass, files a dated audit record to that repo's intake, and flags anything gated or destructive back to Allison. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-08-07 (Repo Baseline Standard lane, ADR 0056 piece two).
tier: organization
zone: hands
status: live
subtitle: "born-to-standard repos and ten-point audits"
---

# Repo Standards -- v1.0 (2026-08-07)

Every repo in the ExpertPartners organization meets the ruled baseline. This skill is the judgment layer of ADR 0056, the piece that checks what org-level rulesets cannot, and it runs in exactly two situations, a repo being born and a repo being audited.

## The one source of truth

The standard lives in ONE place, `aura decisions/0056-repo-baseline-standard.md`. Read it at the start of every run, before grading or scaffolding anything. Reach it by the first path that works, the local aura checkout, the Estate Brain fetch tool (repo aura, path decisions/0056-repo-baseline-standard.md), or the GitHub contents API. If all three fail, stop and say so, do not grade from memory.

This skill never restates the ten points as its own canon. The ADR's text wins over anything written here, and if this skill and the ADR ever disagree, the ADR is right and this skill gets corrected. Points 1 through 3 are the enforcement layer (org rulesets, bot commit routing, generated-artifact gates), points 4 through 10 are the judgment layer. The audit checks all ten, creation wires the repo so all ten hold from birth.

## Path one, repo creation (born to standard)

Fires when a new ExpertPartners repo is being created, including via the new-project skill. Work through the checklist in order and confirm each item before reporting the repo born.

1. **Root AGENTS.md**, roughly 150 to 200 lines maximum. Lean structural overview, the repo's one job, where things live, what agents may and may not touch. Detail links out to docs, never sits inline. CLAUDE.md at the repo root is one line importing it (`@AGENTS.md`) plus anything Claude-specific that genuinely differs.
2. **Frontmatter from file one.** Every knowledge file carries the YAML frontmatter standard per ADR 0025 (date, source, topic, classification). The first file committed complies, so no retrofit debt ever accrues.
3. **Curated index.** An llms.txt-style manifest at the repo root with one described line per important file, not a bare listing. Name it per the repo's convention (llms.txt or _index equivalent) and note the regeneration path if it is generated.
4. **.gitattributes and CODEOWNERS scaffold.** Generated paths marked linguist-generated, CODEOWNERS protecting generated artifacts and decision records, both committed even if short.
5. **Org ruleset inheritance confirmed.** New repos inherit the estate default-branch and tag rulesets automatically. Confirm live (GET the repo's rules for its default branch) and record the check in the birth report. Never assume inheritance, prove it once.
6. **Intake inbox, when the repo will receive session records.** Create intake/ with the ADR 0027 convention README and note the distillation cadence owner.

Report the birth with each item named and its evidence, then hand the repo back.

## Path two, repo audit (walk this repo)

Fires on any request to walk, harden, grade, or verify a named repo. One repo per pass, never batch grades across repos in one breath.

Run order:

1. Fetch ADR 0056 fresh, then inventory the repo live (tree, workflows, rulesets in effect, .gitattributes, CODEOWNERS, index file, intake state, largest files, frontmatter sampling). Every grade below cites evidence read this session, never memory.
2. Grade each of the ten points PASS or FAIL, one line of evidence per point. A point that does not apply (no CI exists, no intake inbox, no deployed copies) grades N/A with the reason, and N/A is declared, never silently skipped.
3. **Fix reversible gaps in the same pass.** Missing AGENTS.md, missing index, missing .gitattributes or CODEOWNERS, missing frontmatter on recent files, header banners on generated files, all get fixed and committed in the pass that found them, on a branch merged sequentially. Backup-then-proceed applies, never rewrite history to fix a finding.
4. **Flag what is gated.** Anything destructive (deleting or rewriting existing content, force operations), anything that spends money, anything that changes who or what holds access (ruleset edits, bypass actors, token scopes), and any judgment call that needs business truth goes back to Allison as a named line item with a recommendation. The audit never executes these, even when the fix is obvious.
5. **File the audit record.** A dated record lands in the audited repo's intake/ (or aura intake/ when the repo has none), named `YYYY-MM-DD-repo-standards-audit-<repo>.md`, carrying the per-point table, fixes applied with commit hashes, and open flags. Template at `references/audit-record-template.md`.

The walk of the existing estate runs this path one repo per pass, aura first, per the ADR's sequencing (enforcement layer lands before the walk starts). The lane ledger breakup is a known open finding on aura, marked in aura's audit record and never blocking it, per the ADR carve-out.

## Deployed copies and this skill's own hygiene

This skill practices point 8 on itself. The canonical home is `expert-partners-skills skills/repo-standards/SKILL.md`. Deployed copies (aura `.claude/skills/repo-standards/`) carry the DEPLOYED COPY header naming the canonical home, a version stamp matching the canonical version line, and a SHA-256 checksum manifest committed alongside. The deploy pipeline (`tools/skill-deploy/deploy-skill.sh`) is the sole producer of deployed copies and upload zips. Hand-editing a deployed copy is a violation, fixes flow through canonical source and redeploy.

## Boundaries

- This skill grades and scaffolds. It never edits org rulesets, never grants or widens access, never revokes tokens. Those are enforcement-layer changes and they are Allison's line items.
- It inherits the operating-doctrine and never overrides it. Verify before speaking, automation as the standard, strongest path with reasoning, no deferral language.
- It never invents standard points. Ten points, one ADR, zero local additions. Proposals for an eleventh point go to Allison as an ADR amendment, not into this skill.
