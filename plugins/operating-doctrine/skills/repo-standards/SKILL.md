---
name: repo-standards
description: "Brings Estate repos to the Repo rules and Project ownership readiness. Use for repo creation or proposals; explicit audits, hardening, organization, cleanup, curation, rationalizing knowledge, deciding what belongs, or preparing a repo for humans and AI; Project attachment or material reconfiguration; and material work without established readiness. Never fires on a casual repo mention. Creation proves ownership before proposing a new repo. Explicit audits assess content and fix gaps. Automatic readiness evaluates and routes. Reads live canon and the GitHub Archive Index, preserves source history and one-owner pointers. Research cannot create new baseline rules. One lifecycle/audit skill, no repo-curator."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-08-07 (Repo Baseline Standard lane, ADR 0056 piece two).
tier: plugin
zone: hands
status: live
subtitle: "repo birth, readiness, and evidence-led content audits"
---

# Repo Standards

Every repo in the ExpertPartners organization meets the ruled baseline. This skill is the judgment layer of the Repo rules, the piece that checks what org-level rulesets cannot.

The readiness evaluation runs when a repo is born, audited, joined to a Claude Project, materially reconfigured, or about to get material work with no readiness established. Repo creation passes the ownership gate first.

The GitHub Archive Index sheet is the one answer to which repositories exist, what each holds, and its pile. Read it live, never a frozen roster. Stage A reads it before proposing a repo, Stage B adds the new repo's row, and path three reads the repo's row as its ownership input. A repo without a row is `UNREGISTERED`. The earlier Manifest Entity index from the retired aura repo is history in GitHub Archive.

Explicit audits add knowledge architecture assessment. Read [the content assessment](references/content-architecture.md) before changing governed content, follow its [Repo Design Tower sequence](references/content-architecture.md#repo-design-tower-sequence-explicit-phase-two-passes) for Phase Two passes, and use the [audit record](references/audit-record-template.md) for evidence.

## Grok repository profiles

For Grok repository work, load the [Repo Auditor](references/grok-auditor.md) or [Repo Fixer](references/grok-fixer.md). Unspecified mode defaults to Auditor, which is read-only. Fixer repairs low-risk reversible gaps (see its delegated repair classes), opens a PR and merges it when checks pass. Neither creates a repo. Qualification gates A to D and badges are retired. Run the behavioral cases in [tests/behavioral-rubric.md](tests/behavioral-rubric.md) when you change the profiles.

## The one source of truth

The standard lives in ONE place, the Repo rules section of the HQ Rulebook. Read it at the start of every run. The Project-ownership half is the Project ownership section of the same Rulebook. If it cannot be read, fix access and retry rather than grading from memory.

Factory work uses the native assignment, not a GitHub issue, Hub record or Chat to Code queue. Check current Workstream, branch/worktree and PR evidence for collisions. Factory owns company development execution.

This skill never restates the ten points as its own canon. The Rulebook's text wins, and this skill gets corrected if they differ. Points 1 through 3 are the enforcement layer (org rulesets, bot commit routing, generated-artifact gates), points 4 through 10 are the judgment layer.

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
- Reading permissions, topology, or contents.

When trigger 5 is ambiguous, prefer one short readiness line over a full interview.

## Path one, repo creation (the gate, then born to standard)

### Stage A, the new-repo gate

Run the gate live, never from memory of what repos exist.

1. **Search live existing ownership first.** Read the GitHub Archive Index sheet live before proposing any repository, then enumerate the whole org (`gh api --paginate orgs/ExpertPartners/repos`, active and archived) and reconcile the candidates against current canon. The sheet is the one topology authority. An archived or locked row whose What it holds covers the durable job is a revival candidate, not an absence; name it in the existing-owner verdict without silently unarchiving it.
2. **Prove no existing repo and folder can cleanly own the durable job.** Name the candidates considered and why each fails. "Nothing came to mind" is not a proof. Fewer repositories is a placement preference, never permission to mix unrelated owners or duplicate editable truth.
3. **Classify the entity or capability type** using the words already in the Archive Index sheet, never a second local taxonomy.
4. **Name the durable owner**, the domain or entity that owns the facts, not the person who asked.
5. **Name the consumers**, who reads it and by what path (pointer, door, generated copy).
6. **State why independent repository existence is warranted**, in terms of the durable job, not present convenience.
7. **Check duplicate-truth risk.** Would any fact become editable in two places? If yes, the gate fails.
8. **Check the Project relationship** per Project ownership, which Project would own it and whether that Project already has an owning repo.

Return exactly one:

- `USE EXISTING REPO` with the correct owner and why it owns the job. The creation path stops here.
- `NEW REPO JUSTIFIED` with owner, boundaries, consumers, and a documented technical or ownership reason for independent existence.

Only after `NEW REPO JUSTIFIED` may stage B proceed. A gate that cannot reach live org or canon state returns neither verdict. It says which source failed and the AI fixes the access and reruns.

### Stage B, born to standard

Work through the checklist in order.

1. **Root AGENTS.md**, roughly 150 to 200 lines maximum. Lean structural overview, the repo's one job, where things live, what agents may and may not touch. Detail links out to docs, never sits inline. CLAUDE.md at the repo root is one line importing it (`@AGENTS.md`) plus anything Claude-specific that genuinely differs.
2. **Frontmatter from file one.** Every knowledge file carries the YAML frontmatter standard per ADR 0025 (date, source, topic, classification). The first file committed complies, so no retrofit debt ever accrues.
3. **Curated index.** An llms.txt-style manifest at the repo root with one described line per important file, not a bare listing. Name it per the repo's convention (llms.txt or _index equivalent) and note the regeneration path if it is generated.
4. **.gitattributes and CODEOWNERS scaffold.** Generated paths marked linguist-generated, CODEOWNERS protecting generated artifacts and decision records, both committed even if short.
5. **Org ruleset inheritance confirmed.** New repos inherit the estate default-branch and tag rulesets automatically. Confirm live (GET the repo's rules for its default branch) and record the check in the birth report. Never assume inheritance, prove it once.
6. **Intake inbox, when the repo will receive session records.** Create intake/ with the ADR 0027 convention README and note the distillation cadence owner.
7. **Project connection recorded** per Project ownership, the owning Project named and the repo connected where that surface supports connections.
8. **Archive Index row registered.** Add the repo's current registration row to the existing GitHub Archive Index sheet in the same pass: Repo name, Default branch, What it holds (purpose, entity type, owner, deployment and Factory agent instructions), and Pile. Preserve historical archive/worktree rows and copied-SHA receipts. Re-read the sheet to verify the landed row. A proposed row, a pending entry, or a skill's project table is not registration.

Report the birth with each item named and its evidence, including the Archive Index row. If registration cannot land, fix the cause or name the exact remaining gap.

## Path two, repo audit (walk this repo)

Fires on explicit audit and organization requests (trigger 2). One repo per pass. An explicit audit fixes gaps in the pass that found them. Organization starts with evidence and the smallest useful batch, never a giant folder reorganization.

Run order:

For an explicit Phase Two / Repo Design Tower pass, complete the linked sequence's input reads before designing. The dispatch bounds the work: a design-only or skill-amendment job does not authorize a target-repository content audit or edits outside its named paths. Do not report a full audit or readiness verdict for checks outside that scope.

1. Read the Repo rules, Project ownership, and the current Archive Index row fresh, then inventory the repo live (tree, workflows, rulesets in effect, .gitattributes, CODEOWNERS, index file, intake state, largest files, frontmatter sampling). Before content changes, complete the ownership, front-door, and content assessment in [references/content-architecture.md](references/content-architecture.md), including its stop checks and authority classification. Every grade below cites evidence read this session, never memory.
2. Grade each of the ten points PASS or FAIL, one line of evidence per point. A point that does not apply (no CI exists, no intake inbox, no deployed copies) grades N/A with the reason, and N/A is declared, never silently skipped.
3. **Fix reversible gaps in the same pass.** Missing AGENTS.md, missing index, missing .gitattributes or CODEOWNERS, missing frontmatter on recent files, header banners on generated files, all get fixed and committed in the pass that found them, on a branch merged sequentially. Backup-then-proceed applies, never rewrite history to fix a finding.
4. **Do the rest too.** Deleting or rewriting existing content, spending, ruleset or access edits, and judgment calls are all just work now. Do them, record each in the audit record, and report. Where a call truly needs business truth no source holds, ask one question with a recommendation. A rewrite that changes governed meaning is still worth a note in the record.
5. **File the audit record.** A dated record lands as a Google Doc in the owning brain's home folder in Drive (HQ brain if none), titled `repo-standards-audit-<repo>`, carrying the per-point table, bounded content assessment, fixes applied with commit hashes, and open items. Use [references/audit-record-template.md](references/audit-record-template.md). Report `READY` when the applicable baseline and usable front doors are evidenced, otherwise `REMEDIATION REQUIRED`. `ORGANIZE EXISTING REPO` is an action recommendation within that report, not a third verdict.

The walk of the existing estate runs this path one repo per pass, in the order the current authorized mission and Archive Index set. Historical aura, lane-ledger and Job Tracker sequencing is not a current execution prerequisite. Consolidation requires actual workflow, import/package, deployment and shared-infrastructure consumers, preservation of unique branches/history and unfinished work, and current owner coordination. Inactivity alone never proves no dependents. Keep stored readiness scores and denominators unchanged until the real readiness engine reruns.

## Path three, readiness check (Project attachment and material touch)

Fires on triggers 3, 4, and 5. This path EVALUATES AND ROUTES. It does not restructure a repo because somebody touched it. That distinction is the whole point: an explicit audit (path two) is licensed to fix; a readiness check is not.

Expected input: the repo, plus the owning Project, Table, or Room context when known. When the Project context is unknown, say so and evaluate the repo half rather than guessing an owner.

Run order:

1. **Resolve live ownership and topology** through GitHub (repo exists, visibility, archived flag, description, default branch) and the repo's GitHub Archive Index row (What it holds, Pile). Never infer ownership from a repo name. No row means `UNREGISTERED` and `REMEDIATION REQUIRED`; the smallest safe remediation for that gap is the row itself, not a replacement repo or restructure. Use reachable owning canon to establish the proposed row's owner, or report ownership unproven rather than inventing it.
2. **Read the Repo rules fresh**, and Project ownership for the Project half.
3. **Resolve the relevant Project ownership and setup evidence.** Verify current capabilities rather than assuming project membership is enumerable. Establish relationships from live owning canon, the native Factory assignment or Workstream, each project's current plan and verified session context. A Project relationship that no accessible live source supports is reported `UNPROVEN`, never invented and never assumed from a matching name.

Then verify, each with its evidence:

- **Archive Index row present and current.** The row exists and its What it holds and Pile match the live repo (GitHub description, archived or locked flag, and the first H1 in root `CLAUDE.md`). Name a missing row or a mismatch as a gap. Do not edit a row just to erase a mismatch: first reconcile the repo with its accepted job and owner. The sheet is topology authority; `project-knowledge/estate-manifest.json` is observed-state machinery and the systems census is a separate inventory.
- **One clear durable job.** The repo does one thing, and its own README, AGENTS.md, and GitHub description say the same thing. A description contradicting the repo's accepted canon is a gap, not a detail.
- **Owning domain or entity named.**
- **Correct canonical pointers**, out and in, and none pointing at a deleted or renamed repo.
- **Repo rules baseline readiness** across the ten points.
- **Project identity**, the owning Project relationship per Project ownership, and whether the Project already has an owning repo this one would collide with.
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
5. **A scoped native Factory assignment** when the remediation is structural work, naming the repo, branch, bounded change and acceptance check. Reuse the current assignment when it already covers the work. Structural remediation is routed, not performed inline by this evaluation-only path.

An automatic readiness evaluation never silently repairs, renames, archives, consolidates, or restructures anything. It routes the work to a scoped Factory assignment (or does it, when the brief says to) and reports.

## Topology drift, and who watches it

The former Aura weekly governance scan (`aura tools/governance/aura-governance-scan.py`, ADR 0033) is retired. Do not reactivate it. Find the current owner and producer of topology checks in the HQ records, check that it runs, and if nothing does, run the comparison yourself rather than creating a second watcher, daemon, registry or dashboard.

Compare the sheet against the live org: an active org repo with no row is `UNREGISTERED REPO`, a row for a repo that is gone is `ORPHAN POINTER`, and an archived or locked repo shown open, or the reverse, is `STATUS MISMATCH`. Fix the row when the cause is clear and report what changed.

## Deployed copies and this skill's own hygiene

This skill practices point 8 on itself. The canonical home is `expert-partners-skills plugins/operating-doctrine/skills/repo-standards/SKILL.md`, and it reaches every surface only through the GitHub skills marketplace. Per the HQ Rulebook and the Decision Log entry "No skill exceptions" (2026-10-19), there is no uploaded, hand-made, or platform-only copy, and the old aura deployed copy and its Codex mirror are retired. Codex takes the skill through its daily sync from the marketplace. The deploy pipeline (`tools/skill-deploy/deploy-skill.sh`) stays the producer of checksums and packaging. Hand-editing a copy is a violation, fixes flow through canonical source and the marketplace.

## Boundaries

- Path three evaluates and routes. Only an explicit audit fixes in place.
- It inherits the operating-doctrine and never overrides it.
- It never invents standard points. Ten points, one ADR. An eleventh point is an ADR amendment.
- One standard, one skill. No second repo-onboarding or repo-readiness skill. Extend this file instead.
