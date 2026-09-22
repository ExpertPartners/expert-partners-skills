---
name: repo-standards
description: "Brings Estate repos to ADR 0056 and ADR 0078 readiness. Use for repo creation or proposals; explicit audits, hardening, organization, cleanup, curation, rationalizing knowledge, deciding what belongs, or preparing a repo for humans and AI; Project attachment or material reconfiguration; and material work without established readiness. Never fires on a casual repo mention. Creation proves ownership before proposing a new repo. Explicit audits assess content and fix authorized reversible gaps. Automatic readiness only evaluates and routes. Reads live canon and the Manifest Entity index, preserves source history and one-owner pointers, and stops on conflicts, unclear ownership or confidentiality, unavailable canon, or overlapping workers. Research cannot create new baseline rules. One lifecycle/audit skill, no repo-curator."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-08-07 (Repo Baseline Standard lane, ADR 0056 piece two).
tier: organization
zone: hands
status: live
subtitle: "repo birth, readiness, and evidence-led content audits"
---

# Repo Standards -- v1.4 (2026-09-22)

Every repo in the ExpertPartners organization meets the ruled baseline. This skill is the judgment layer of ADR 0056, the piece that checks what org-level rulesets cannot.

v1.1 adds the readiness gate. v1.0 ran in exactly two situations, a repo being born and a repo being audited, which meant readiness depended on Allison remembering to ask for an audit. It no longer does. A repo joining a Claude Project, a Project or repo relationship being materially reconfigured, and material work starting in a repo whose readiness nobody has established now all reach the same live evaluation, and repo creation now passes an ownership gate before it may proceed.

<!-- RULED-BY: aura/decisions/0078-claude-project-repository-setup.md date:2026-08-27 -->

<!-- RULED-BY: aura/intake/2026-09-01-repo-final-reconciliation-execution-map.md date:2026-09-01 -->

v1.2 names the topology authority. The Estate Manifest Entity index (`aura docs/estate/estate-manifest.md`, section `Entity index`, introduced in v1.20) is the one machine-readable answer to which repositories exist, each repository's durable job, owner, and disposition. Read the current manifest live, never a frozen roster or a historical census. Stage A reads the index before proposing any repo, Stage B registers the new row as part of birth, and path three reads the repo's row as its ownership input. The weekly governance scan's topology contract uses the same index. A repo without a row is `UNREGISTERED` by design. Implementation provenance: `aura intake/2026-09-20-session-record-forever-controls-topology-authority.md`; P9 and P10 specification: `aura intake/2026-09-19-session-record-controls-review-lane-5-forever-controls-prefl.md`.


v1.3 extends only the explicit audit path with knowledge architecture assessment. Read [the content assessment](references/content-architecture.md) before changing governed content, and use the [audit record](references/audit-record-template.md) to preserve evidence and proposed dispositions. The ten baseline grades, creation gate, and automatic readiness authority stay unchanged. This is implementation of existing authority plus the bounded Phase Two brief, not adoption of the research's proposed schema or governance. Provenance and unresolved amendments are recorded in `intake/2026-09-21-repo-standards-phase-two-authority-review.md` and `intake/2026-09-21-repo-standards-phase-two-founder-decisions.md` in the canonical skills repo.


v1.4 makes the filed Phase Two digest a required design-evidence input for an explicit Phase Two / Repo Design Tower organization pass. Before repository design or content architecture work, follow the [Repo Design Tower sequence](references/content-architecture.md#repo-design-tower-sequence-explicit-phase-two-passes). It extends path two only, preserves the three evidence layers, and creates no new baseline rule or lifecycle mechanism.

## The one source of truth

The standard lives in ONE place, `aura decisions/0056-repo-baseline-standard.md`. Read it at the start of every run, before grading or scaffolding anything. The Project-ownership half lives in `aura decisions/0078-claude-project-repository-setup.md`. Reach both by the first path that works, the local aura checkout, the Estate Brain fetch tool (repo aura, path as given), or the GitHub contents API. If all three fail, stop and say so, do not grade from memory.

This skill never restates the ten points as its own canon. The ADR's text wins over anything written here, and if this skill and the ADR ever disagree, the ADR is right and this skill gets corrected. Points 1 through 3 are the enforcement layer (org rulesets, bot commit routing, generated-artifact gates), points 4 through 10 are the judgment layer. ADR 0078 is read the same way, as authority, never restated as local canon.

## When this fires, and when it must not

Fires on:

1. A new Estate repo being created or merely proposed. The gate runs before creation, not after.
2. An explicit repo audit, walk, harden, grade, bring-to-standard, organize, clean, curate, make-canonical, rationalize-knowledge, determine-what-belongs, or prepare-for-humans-and-AI request.
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

1. **Search live existing ownership first.** Read the Estate Manifest Entity index live before proposing any repository, then enumerate the whole org (`gh api --paginate orgs/ExpertPartners/repos`, active and archived) and reconcile the candidates against current canon. The Entity index is the one machine-readable topology authority. An archived row whose Job covers the durable job is a revival candidate, not an absence; name it in the existing-owner verdict without silently unarchiving it.
2. **Prove no existing repo can cleanly own the durable job.** Name the candidates considered and why each fails. "Nothing came to mind" is not a proof.
3. **Classify the entity or capability type** using the current Entity index schema and its enum values, never a second local taxonomy.
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
8. **Manifest Entity row registered.** Add the repo's row to the Estate Manifest Entity index in the same pass, using its current schema (Repo, Job, Owner, Entity type, Room, Scan profile, Status, Disposition, Desc sha, Identity sha, Last verified, Evidence). Commit it to aura main through the applicable reviewed path with `Push-Policy: docs`, then independently fetch the landed row. Use `aura-governance-scan.py --stamp <repo>` after verifying that command exists in current canon. If scan integration has not landed, use the shipped `tools/governance/estate_entities.py` parser's `sha12` with the live description and pinned default-branch identity, exactly as the manifest specifies; never invent a command result. Validate the row with that shared parser. A proposed row, a pending door-registration entry, or a skill's project table is not registration.

Report the birth with each item named and its evidence, including the Entity row's path, landed commit, both stamps, and verification date. Birth cannot be reported complete without the registered row. If registration cannot land, name that exact remaining gap and keep the birth incomplete.

## Path two, repo audit (walk this repo)

Fires on explicit audit and organization requests (trigger 2). One repo per pass. An explicit audit remains licensed to fix reversible gaps in the pass that found them, within existing authority. Organization starts with evidence and the smallest useful batch, never a giant folder reorganization.

Run order:

For an explicit Phase Two / Repo Design Tower pass, complete the linked sequence's input reads before designing. The dispatch bounds the work: a design-only or skill-amendment job does not authorize a target-repository content audit or edits outside its named paths. Do not report a full audit or readiness verdict for checks outside that scope.

1. Fetch ADR 0056, ADR 0078, and the current Manifest Entity row fresh, then inventory the repo live (tree, workflows, rulesets in effect, .gitattributes, CODEOWNERS, index file, intake state, largest files, frontmatter sampling). Before content changes, complete the ownership, front-door, and content assessment in [references/content-architecture.md](references/content-architecture.md), including its stop checks and authority classification. Every grade below cites evidence read this session, never memory.
2. Grade each of the ten points PASS or FAIL, one line of evidence per point. A point that does not apply (no CI exists, no intake inbox, no deployed copies) grades N/A with the reason, and N/A is declared, never silently skipped.
3. **Fix reversible gaps in the same pass.** Missing AGENTS.md, missing index, missing .gitattributes or CODEOWNERS, missing frontmatter on recent files, header banners on generated files, all get fixed and committed in the pass that found them, on a branch merged sequentially. Backup-then-proceed applies, never rewrite history to fix a finding.
4. **Flag what is gated.** Anything destructive (deleting or rewriting existing content, force operations), anything that spends money, anything that changes who or what holds access (ruleset edits, bypass actors, token scopes), and any judgment call that needs business truth goes back to Allison as a named line item with a recommendation. The audit never executes these, even when the fix is obvious. Distinguish a verified typo or navigation correction already permitted by step 3 from a rewrite that changes governed meaning; Git reversibility alone does not authorize new business truth.
5. **File the audit record.** A dated record lands in the audited repo's intake/ (or aura intake/ when the repo has none), named `YYYY-MM-DD-repo-standards-audit-<repo>.md`, carrying the per-point table, bounded content assessment, fixes applied with commit hashes, and open flags. Use [references/audit-record-template.md](references/audit-record-template.md). Report `READY` only when both the applicable baseline and usable front doors are evidenced; otherwise `REMEDIATION REQUIRED`. `ORGANIZE EXISTING REPO` is an action recommendation within that report, not a third readiness verdict or permission for gated changes.

The walk of the existing estate runs this path one repo per pass, aura first, per the ADR's sequencing (enforcement layer lands before the walk starts). The lane ledger breakup is a known open finding on aura, marked in aura's audit record and never blocking it, per the ADR carve-out.

## Path three, readiness check (Project attachment and material touch)

Fires on triggers 3, 4, and 5. This path EVALUATES AND ROUTES. It does not restructure a repo because somebody touched it. That distinction is the whole point: an explicit audit (path two) is licensed to fix; a readiness check is not.

Expected input: the repo, plus the owning Project, Table, or Room context when known. When the Project context is unknown, say so and evaluate the repo half rather than guessing an owner.

Run order:

1. **Resolve live ownership and topology** through GitHub (repo exists, visibility, archived flag, description, default branch) and the repo's Estate Manifest Entity index row (Job, entity type, owner, status, disposition). Never infer ownership from a repo name. No row means `UNREGISTERED` and `REMEDIATION REQUIRED`; the smallest safe remediation for that gap is the row itself, not a replacement repo or restructure. Use reachable owning canon to establish the proposed row's owner, or report ownership unproven rather than inventing it.
2. **Read ADR 0056 fresh**, and ADR 0078 for the Project half.
3. **Resolve the relevant Project ownership and setup evidence.** Claude Project membership and repository attachment are not enumerable by any tool the estate holds; room existence is Allison's projects page. So Project relationships are established from canonical committed records (aura `docs/estate/room-registry.md`, the lane ledger, the current topology map) and from live session or dispatch context. A Project relationship that no accessible live source supports is reported `UNPROVEN`, never invented and never assumed from a matching name.

Then verify, each with its evidence:

- **Manifest Entity row present and current.** The row exists and its description and identity stamps match the live surfaces. Read the current GitHub description and the first H1 in root `CLAUDE.md` at a pinned default-branch commit, following exactly one `@AGENTS.md` hop when that exact import appears among the first three nonempty lines. Use the manifest's `sha12` rule (collapse whitespace, trim, preserve case, first 12 lowercase SHA-256 hex characters). The scan's `DESCRIPTION DRIFT` and `IDENTITY DRIFT` findings are inputs here, checked against live evidence. A dash records an absent source, not a passing identity baseline; name missing descriptions or identity H1s as gaps. Do not refresh a stamp just to erase a mismatch: first reconcile the surface with the accepted job and owner. The Entity index is topology authority; `project-knowledge/estate-manifest.json` is observed-state machinery and the systems census is a separate inventory.
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

Drift surfacing belongs to the EXISTING weekly Aura governance scan (`aura tools/governance/aura-governance-scan.py`, ADR 0033), never to a second watcher, daemon, registry, or dashboard. Its ruled topology contract derives coverage from the Estate Manifest Entity index, never from a list of its own: an active org repo with no Entity row is an `UNREGISTERED REPO` finding; an active row for a repo that is gone or archived is an `ORPHAN POINTER`; an archived row for a live repo is a `STATUS MISMATCH`; a changed GitHub description or CLAUDE.md identity H1 produces `DESCRIPTION DRIFT` or `IDENTITY DRIFT`; a retired repo name produces `RETIRED NAME REFERENCE`; and the Estate Brain door's canonical list is cross-checked against knowledge-profile rows as `DOOR LIST MISMATCH`. Verify current scan implementation before claiming it emits these findings; a pending scan rollout does not suspend this skill's direct Entity-row and live-surface checks. The scan stays read-and-flag-only, proposes while the owning session or Allison disposes, and this skill reads its findings without building a parallel mechanism.

## Deployed copies and this skill's own hygiene

This skill practices point 8 on itself. The canonical home is `expert-partners-skills skills/repo-standards/SKILL.md`. It is homed under `skills/` and carried by no plugin, so it owes exactly one shelf, the claude.ai organization Skills upload, plus the aura deployed copy and that copy's Codex mirror at `.agents/skills/repo-standards/`. Codex discovers the mirror under `.agents/skills`, not the `.claude/skills` mount. Deployed copies (aura `.claude/skills/repo-standards/` and `.agents/skills/repo-standards/`) carry the DEPLOYED COPY header naming the canonical home, a version stamp matching the canonical version line, and a SHA-256 checksum manifest committed alongside. The deploy pipeline (`tools/skill-deploy/deploy-skill.sh`) is the sole producer of deployed copies and upload zips. Use `--to aura/.claude/skills` for the deployed copy and `--mirror-mount aura/.claude/skills --to aura/.agents/skills` for its Codex mirror, then verify both through the pipeline. Hand-editing a deployed copy is a violation, fixes flow through canonical source and redeploy.

## Boundaries

- This skill grades and scaffolds. It never edits org rulesets, never grants or widens access, never revokes tokens. Those are enforcement-layer changes and they are Allison's line items.
- Path three evaluates and routes. Only an explicit audit fixes in place, and only reversible gaps.
- It inherits the operating-doctrine and never overrides it. Verify before speaking, automation as the standard, strongest path with reasoning, no deferral language.
- It never invents standard points. Ten points, one ADR, zero local additions. Proposals for an eleventh point go to Allison as an ADR amendment, not into this skill.
- One standard, one skill. No second repo-onboarding or repo-readiness skill is ever created; this file is extended instead.
