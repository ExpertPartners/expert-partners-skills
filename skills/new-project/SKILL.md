---
name: new-project
description: >
  Run a new Expert Partners project through repo-standards before bootstrapping.
  Uses live creation Stage A, creates nothing on USE EXISTING REPO, and proceeds
  only on NEW REPO JUSTIFIED. After creation, runs Stage B and registers the
  GitHub Archive Index row before reporting birth complete. Use when Allison
  says /new-project followed by a name, "new project: NAME", "bootstrap a new
  project called NAME", or the session-wrap new-project variant fires.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Adopted into canonical 2026-08-05 (Skill Map Rulings lane, flags item 9);
# the machine copy at ~/.claude/skills is a deployed copy.
tier: user
zone: routing
status: live
calls:
  - repo-standards
subtitle: "run the repo-standards gate, then bootstrap a justified project"
---

# New-Project Skill

Runs `repo-standards`, the one repository standard implementation. This skill
supplies bootstrap mechanics; Repo rules and Project ownership govern.
Load current canonical `expert-partners-skills plugins/operating-doctrine/skills/repo-standards/SKILL.md`
for every run. If it cannot be reached live, create nothing and name the failed
source. A local script or an older deployed skill never substitutes for the gate.

<!-- RULED-BY: aura/decisions/0056-repo-baseline-standard.md date:2026-08-07 -->
<!-- RULED-BY: aura/decisions/0078-claude-project-repository-setup.md date:2026-08-27 -->
<!-- RULED-BY: aura/intake/2026-09-01-repo-final-reconciliation-execution-map.md date:2026-09-01 -->

## Steps

1. **Parse input without creating anything.** Extract the proposed project home
   name (PascalCase, e.g., `ExampleProject`) and optional script type (`brand` or
   `standalone`, default `standalone`). Script type is a bootstrap option, not
   the Manifest's entity type. Identify the durable job and Project context.

2. **Run repo-standards creation Stage A live.** Read its authorities and the
   GitHub Archive Index sheet, then complete the ownership gate.
   Proceed only on `NEW REPO JUSTIFIED`. On `USE EXISTING REPO`, stop, report
   the owner and supporting Archive Index row, and create nothing: no repo, local home,
   bootstrap commit, or pending registration. An archived owner is a revival
   candidate, not permission to create a duplicate or unarchive it. If the gate
   cannot return a verdict, stop before bootstrap and name the missing evidence.

3. **Bootstrap only the justified repo.** Verify the proposed slug and local
   home do not already exist, then inspect the current script and its side
   effects before running:
   ```bash
   bash ~/scripts/new-project.sh <ProjectHome> [type]
   ```
   The script is scaffolding, not a readiness verdict. Capture its actual
   output, new repo URL, local home, initial commit, and any pending-registration
   file it changed. Its `DONE` message or template TODO never proves a complete
   birth. If it partially fails, inspect what it created and resume that repo's
   Stage B; do not blindly rerun creation. If the script is absent or unsuitable,
   any replacement bootstrap still requires the same live Stage A verdict and
   Stage B completion. Do not modify unrelated host scripts in this run.

4. **Run repo-standards Stage B on the new repo.** Bring the scaffold to the live
   Repo rules baseline, replace placeholder identity with the verified job, record
   the Project relationship per Project ownership, and add the Archive Index row
   through Stage B item 8. The birth report is the Stage B report. Until the row
   is on the sheet and independently read back, birth is incomplete.

5. **Reconcile downstream routing.** The Archive Index row is topology
   registration. Check the row's scan profile and declared consumers. The
   Estate Brain door is retiring (Decision Log 2026-10-13), so no door
   registration is requested for a new repo.

   The inspected legacy script appends to the retired aura repo's
   `project-knowledge/pending-canonical-repos.md`. aura is read-only history, so
   treat any such write as a stray side effect. Report it, do not commit it, and
   never treat it as registration or an active automatic sync. The Archive Index
   row is the only registration. The old "S1 CANONICAL_REPOS sync" wording
   referred to a completed Synapse worker lane, not a Make scenario. Never
   promise that a retired worker or queue will index the repo automatically.

   If intake routing needs a new brain mapping, update its canonical skill
   source (`expert-partners-skills skills/intake/SKILL.md`) from the Archive Index row,
   then use the deployment pipeline under the current rollout scope. Never
   hand-edit `~/.claude/skills/intake/SKILL.md`. Routing tables remain
   downstream consumers of topology.

6. **Report the Stage B result with evidence.** Include the Stage A verdict,
   repo URL, local home, baseline evidence, Project relationship, landed Entity
   row commit and readback, and routing status.
   Name remaining gaps explicitly. A pending queue entry, script success, or
   repo URL without the Archive Index row cannot be reported as a completed birth.

## Rules

- Never creates a repo the gate did not justify. repo-standards is the one
  standard; this skill is a runner of it, never a second one.
- Never create a project home that already exists on disk.
- ag-vault is never a valid project name here.
- Never use em dashes in any content this skill writes (org standard).
- Run the sibling-session visibility check before any commit to shared repos.

## New-project variant (from claude.ai)

If the session-wrap new-project prompt fires in claude.ai, the output is a
`/new-project <ProjectHome> [type]` block for the implementation session. That
session starts at step 1 and runs Stage A before any script; a handoff never
counts as a prior gate verdict.
