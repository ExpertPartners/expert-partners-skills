---
name: repo-standards
description: "Brings every ExpertPartners repo to the ruled baseline and keeps it there. Fires on repo creation or proposal, explicit repo audit or hardening, a repo being connected to or materially reconfigured in a Claude Project, and material work starting in a repo whose readiness is not established for the current context. Never fires on a repo merely named in passing. Reads ADR 0056 (aura decisions/0056-repo-baseline-standard.md) and ADR 0078 as its source of truth and checks the ten points without restating them as its own canon. Creation runs a gate first, proving no existing repo can own the durable job, returning USE EXISTING REPO or NEW REPO JUSTIFIED with owner, boundaries, and consumers. Audit and readiness paths grade live and return READY with no structural change when compliant, else REMEDIATION REQUIRED carrying exact gaps, evidence, the correct owner, and the smallest safe scoped dispatch, never silent restructuring. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-08-07 (Repo Baseline Standard lane, ADR 0056 piece two).
tier: organization
zone: hands
status: live
subtitle: "born-to-standard repos, ten-point audits, and the readiness gate"
---

# Repo Standards -- v1.1 (2026-09-04)

Every repo in the ExpertPartners organization meets the ruled baseline. This skill is the judgment layer of ADR 0056, the piece that checks what org-level rulesets cannot.

v1.1 adds the readiness gate. v1.0 ran in exactly two situations, a repo being born and a repo being audited, which meant readiness depended on Allison remembering to ask for an audit. It no longer does. A repo joining a Claude Project, a Project or repo relationship being materially reconfigured, and material work starting in a repo whose readiness nobody has established now all reach the same live evaluation, and repo creation now passes an ownership gate before it may proceed.

<!-- RULED-BY: aura/decisions/0078-claude-project-repository-setup.md date:2026-08-27 -->

## The one source of truth

The standard lives in ONE place, `aura decisions/0056-repo-baseline-standard.md`. Read it at the start of every run, before grading or scaffolding anything. The Project-ownership half lives in `aura decisions/0078-claude-project-repository-setup.md`. Reach both by the first path that works, the local aura checkout, the Estate Brain fetch tool (repo aura, path as given), or the GitHub contents API. If all three fail, stop and say so, do not grade from memory.

This skill never restates the ten points as its own canon. The ADR's text wins over anything written here, and if this skill and the ADR ever disagree, the ADR is right and this skill gets corrected. Points 1 through 3 are the enforcement layer (org rulesets, bot commit routing, generated-artifact gates), points 4 through 10 are the judgment layer. ADR 0078 is read the same way, as authority, never restated as local canon.

## When this fires, and when it must not

Fires on:

1. A new Estate repo being created or merely proposed. The gate runs before creation, not after.
2. An explicit repo audit, walk, harden, grade, or bring-to-standard request.
3. A repo being connected or assigned to a Claude Project.
4. A Project or repo relationship being materially reconfigured, a repo swapped, an owning boundary moved, a second repo attached to a Project that already had one.
5. Material work beginning in an important repo with no readiness determination for the current context. Material means committing, restructuring, moving canonical facts, or standing up new durable content, not reading.

Does NOT fire on:

- A repo name appearing in conversation with no material repo work behind it. Naming a repo, citing a path, or reading a file is not a trigger, and hijacking that conversation is the failure this line exists to prevent.
- Ordinary edits inside a repo whose readiness this context already established. Establish once per context, not once per commit.
- Reading permissions, topology, or contents. Verification is never gated.

When trigger 5 is ambiguous, prefer one short readiness line over a full interview, and never block the work while the answer is READY.

## Path one, repo creation (the gate, then born to standard)

### Stage A, the new-repo gate

No Estate repo is proposed or created until this gate returns. Run it live, never from memory of what repos exist.

1. **Search live existing ownership first.** Enumerate the org (`gh api orgs/ExpertPartners/repos`, active and archived) and read the current topology through Estate Brain and canon. An archived repo that already owns the job is a revival candidate, not an absence.
2. **Prove no existing repo can cleanly own the durable job.** Name the candidates considered and why each fails. "Nothing came to mind" is not a proof.
3. **Classify the entity or capability type.** Brand, operating function, product or body of work, source corpus, infrastructure, application, external record, scratch.
4. **Name the durable owner**, the domain or entity that owns the facts, not the person who asked.
5. **Name the consumers**, who reads it and by what path (pointer, door, generated copy).
6. **State why independent repository existence is warranted**, in terms of the durable job, not present convenience.
7. **Check duplicate-truth risk.** Would any fact become editable in two places? If yes, the gate fails.
8. **Check the Project relationship** per ADR 0078, which Project would own it and whether that Project already has an owning repo.

Return exactly one:

- `USE EXISTING REPO` with the correct owner and why it owns the job. The creation path stops here.
- `NEW REPO JUSTIFIED` with owner, boundaries, consumers, and the durable reason.

Only after `NEW REPO JUSTIFIED` may stage B proceed. A gate that cannot reach live org or canon state returns neither verdict; it says which source failed and stops.

### Stage B, born to standard

Work through the checklist in order and confirm each item before reporting the repo born.

1. **Root AGENTS.md**, roughly 150 to 200 lines maximum. Lean structural overview, the repo's one job, where things live, what agents may and may not touch. Detail links out to docs, never sits inline. CLAUDE.md at the repo root is one line importing it (`@AGENTS.md`) plus anything Claude-specific that genuinely differs.
2. **Frontmatter from file one.** Every knowledge file carries the YAML frontmatter standard per ADR 0025 (date, source, topic, classification). The first file committed complies, so no retrofit debt ever accrues.
3. **Curated index.** An llms.txt-style manifest at the repo root with one described line per important file, not a bare listing. Name it per the repo's convention (llms.txt or _index equivalent) and note the regeneration path if it is generated.
4. **.gitattributes and CODEOWNERS scaffold.** Generated paths marked linguist-generated, CODEOWNERS protecting generated artifacts and decision records, both committed even if short.
5. **Org ruleset inheritance confirmed.** New repos inherit the estate default-branch and tag rulesets automatically. Confirm live (GET the repo's rules for its default branch) and record the check in the birth report. Never assume inheritance, prove it once.
6. **Intake inbox, when the repo will receive session records.** Create intake/ with the ADR 0027 convention README and note the distillation cadence owner.
7. **Project connection recorded** per ADR 0078, the owning Project named and the repo connected where that surface supports connections.

Report the birth with each item named and its evidence, then hand the repo back.

## Path two, repo audit (walk this repo)

Fires on any request to walk, harden, grade, or verify a named repo. One repo per pass, never batch grades across repos in one breath. This path keeps its v1.0 semantics unchanged: an explicit audit is licensed to fix reversible gaps in the pass that found them.

Run order:

1. Fetch ADR 0056 fresh, then inventory the repo live (tree, workflows, rulesets in effect, .gitattributes, CODEOWNERS, index file, intake state, largest files, frontmatter sampling). Every grade below cites evidence read this session, never memory.
2. Grade each of the ten points PASS or FAIL, one line of evidence per point. A point that does not apply (no CI exists, no intake inbox, no deployed copies) grades N/A with the reason, and N/A is declared, never silently skipped.
3. **Fix reversible gaps in the same pass.** Missing AGENTS.md, missing index, missing .gitattributes or CODEOWNERS, missing frontmatter on recent files, header banners on generated files, all get fixed and committed in the pass that found them, on a branch merged sequentially. Backup-then-proceed applies, never rewrite history to fix a finding.
4. **Flag what is gated.** Anything destructive (deleting or rewriting existing content, force operations), anything that spends money, anything that changes who or what holds access (ruleset edits, bypass actors, token scopes), and any judgment call that needs business truth goes back to Allison as a named line item with a recommendation. The audit never executes these, even when the fix is obvious.
5. **File the audit record.** A dated record lands in the audited repo's intake/ (or aura intake/ when the repo has none), named `YYYY-MM-DD-repo-standards-audit-<repo>.md`, carrying the per-point table, fixes applied with commit hashes, and open flags. Template at `references/audit-record-template.md`.

The walk of the existing estate runs this path one repo per pass, aura first, per the ADR's sequencing (enforcement layer lands before the walk starts). The lane ledger breakup is a known open finding on aura, marked in aura's audit record and never blocking it, per the ADR carve-out.

## Path three, readiness check (Project attachment and material touch)

Fires on triggers 3, 4, and 5. This path EVALUATES AND ROUTES. It does not restructure a repo because somebody touched it. That distinction is the whole point: an explicit audit (path two) is licensed to fix; a readiness check is not.

Expected input: the repo, plus the owning Project, Table, or Room context when known. When the Project context is unknown, say so and evaluate the repo half rather than guessing an owner.

Run order:

1. **Resolve live ownership and topology** through GitHub (repo exists, visibility, archived flag, description, default branch) and Estate Brain plus canon (registry, manifest, the owning-repo rows). Never infer ownership from a repo name.
2. **Read ADR 0056 fresh**, and ADR 0078 for the Project half.
3. **Resolve the relevant Project ownership and setup evidence.** Claude Project membership and repository attachment are not enumerable by any tool the estate holds; room existence is Allison's projects page. So Project relationships are established from canonical committed records (aura `docs/estate/room-registry.md`, the lane ledger, the current topology map) and from live session or dispatch context. A Project relationship that no accessible live source supports is reported `UNPROVEN`, never invented and never assumed from a matching name.

Then verify, each with its evidence:

- **One clear durable job.** The repo does one thing, and its own README, AGENTS.md, and GitHub description say the same thing. A description contradicting the repo's accepted canon is a gap, not a detail.
- **Owning domain or entity named.**
- **Correct canonical pointers**, out and in, and none pointing at a deleted or renamed repo.
- **ADR 0056 baseline readiness** across the ten points.
- **Project identity**, the owning Project relationship per ADR 0078, and whether the Project already has an owning repo this one would collide with.
- **No duplicate editable truth.** Any fact editable in two places fails readiness, and the existing owner is named.

Return exactly one:

`READY`

with the evidence behind it and no structural change made.

Or:

`REMEDIATION REQUIRED`

carrying, in this order:

1. **Exact gaps**, one line each, each naming the point or rule it fails.
2. **Evidence** for each gap, read live this pass.
3. **The correct owner** of the job or the fact.
4. **The smallest safe remediation scope**, the least that closes the gap, never a repo-wide restructure when one file closes it.
5. **A recommended scoped Claude Code dispatch** when the remediation is structural work, naming the repo, the branch, and the bounded change. Structural remediation is dispatched, never performed inline by this path.

An automatic readiness evaluation never silently repairs, renames, archives, consolidates, or restructures anything. When a gap is destructive to close, or needs business truth, or changes who holds access, it goes to Allison as a named line item exactly as path two step 4 requires.

## Topology drift, and who watches it

Drift surfacing belongs to the EXISTING weekly Aura governance scan (`aura tools/governance/aura-governance-scan.py`, ADR 0033), never to a second watcher, daemon, registry, or dashboard. That scan carries the repo-topology diff: an active org repo absent from its coverage list is an `UNREGISTERED REPO` finding, and a covered repo that is gone or archived in the org is an `ORPHAN POINTER` finding. It stays read-and-flag-only, and it proposes while the owning session or Allison disposes. This skill reads those findings as an input and never builds a parallel mechanism to produce them.

## Deployed copies and this skill's own hygiene

This skill practices point 8 on itself. The canonical home is `expert-partners-skills skills/repo-standards/SKILL.md`. It is homed under `skills/` and carried by no plugin, so it owes exactly one shelf, the claude.ai organization Skills upload, plus the aura deployed copy. Deployed copies (aura `.claude/skills/repo-standards/`) carry the DEPLOYED COPY header naming the canonical home, a version stamp matching the canonical version line, and a SHA-256 checksum manifest committed alongside. The deploy pipeline (`tools/skill-deploy/deploy-skill.sh`) is the sole producer of deployed copies and upload zips. Hand-editing a deployed copy is a violation, fixes flow through canonical source and redeploy.

## Boundaries

- This skill grades and scaffolds. It never edits org rulesets, never grants or widens access, never revokes tokens. Those are enforcement-layer changes and they are Allison's line items.
- Path three evaluates and routes. Only an explicit audit fixes in place, and only reversible gaps.
- It inherits the operating-doctrine and never overrides it. Verify before speaking, automation as the standard, strongest path with reasoning, no deferral language.
- It never invents standard points. Ten points, one ADR, zero local additions. Proposals for an eleventh point go to Allison as an ADR amendment, not into this skill.
- One standard, one skill. No second repo-onboarding or repo-readiness skill is ever created; this file is extended instead.
