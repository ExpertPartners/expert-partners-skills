---
name: new-project
description: >
  Run a new Expert Partners project through repo-standards before anything is
  built. Uses live creation Stage A, creates nothing on USE EXISTING REPO or a
  failed live read, and proceeds only on NEW REPO JUSTIFIED with the required
  creation authorization. Files the build as one GitHub Job issue on the current
  code route, never a local script, a copy box or a new repo made to hold the
  job. Reports birth complete only after Stage B and an independent readback of
  the GitHub Archive Index row. Use when Allison says /new-project followed by a
  name, "new project: NAME", or "bootstrap a new project called NAME".
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Adopted into canonical 2026-08-05 (Skill Map Rulings lane, flags item 9) as a
# user-tier source; migrated into the marketplace 2026-11-04 (Chat to Code job,
# Audit and migrate useful standalone skill behavior into the canonical
# marketplace). Designed until HQ and Allison certify it under build-standard.
# The machine copies at ~/.claude/skills and ~/.agents/skills are deployed
# copies the owning audit retires after native verification.
tier: plugin
zone: routing
status: designed
calls:
  - repo-standards
subtitle: "run the repo-standards gate, then file a justified build as a job"
---

# New-Project Skill

Runs `repo-standards`, the one repository standard implementation. This skill
adds only the order of steps and the hand-off to the current code route; Repo
rules and Project ownership govern. Load current canonical
`expert-partners-skills plugins/operating-doctrine/skills/repo-standards/SKILL.md`
and `plugins/operating-doctrine/skills/code-block-routing/SKILL.md` for every
run. If either cannot be reached live, create nothing and name the failed
source.

Provenance. This skill carries forward useful method from the user-tier
new-project skill adopted into canonical on 2026-08-05. It is the existing
runner of the repo-standards creation gate, not a second gate. The legacy local
bootstrap script, the copy box for another implementation session and any older
deployed copy that describes them are history, never a route.

<!-- RULED-BY: history in GitHub Archive date:2026-08-07 -->
<!-- RULED-BY: history in GitHub Archive date:2026-08-27 -->
<!-- RULED-BY: history in GitHub Archive date:2026-09-01 -->

## Steps

1. **Parse input without creating anything.** Extract the proposed project
   name and the durable job it would hold. Identify the Project context and any
   existing Chat to Code job or GitHub Job issue that already carries this
   request, through job_status and the candidate repos' issues, so the run
   continues that record instead of starting a second one.

2. **Run repo-standards creation Stage A live.** Read its authorities and the
   GitHub Archive Index sheet, then complete the ownership gate.
   Proceed only on `NEW REPO JUSTIFIED`. On `USE EXISTING REPO`, stop, report
   the owner and supporting Archive Index row, and create nothing: no repo, no
   scaffold, no creation job, no pending registration. Work that belongs to that
   owner follows the normal code route for that repo. An archived owner is a
   revival candidate, not permission to create a duplicate or unarchive it. If
   the gate cannot return a verdict because a live read failed, stop, name the
   failed source and the missing evidence, and create nothing. A local script,
   an older deployed skill or memory of what repos exist never substitutes for
   the gate.

3. **Confirm creation authorization.** A justified verdict is not permission.
   Confirm the creation authorization that repo-standards and the current HQ
   Rulebook require is present and covers this repository. If it is missing,
   stop creation and report the verdict with the one missing authorization and
   a recommendation. When it truly needs Allison, raise it the way the HQ
   Rulebook and Decision Log route questions (on the GitHub issue or the
   existing Chat to Code job), never as a question the run waits on in chat,
   and keep working on anything that does not depend on it.

4. **File the build on the current code route.** With `NEW REPO JUSTIFIED` and
   authorization both present, file the creation and scaffold work as one code
   job exactly as code-block-routing describes: one GitHub issue titled `Job:`,
   carrying its five parts, with the Stage A verdict and evidence, the
   authorization, and the Stage B checklist in the acceptance checks. The issue
   starts the Builder on its own. File it where the current route takes code
   jobs, continuing an existing Job issue when one already carries the request.
   Never create a repository only so that a job has somewhere to land, never
   run a local bootstrap script, and never hand Allison or another session a
   copy box to carry the build. If the current route does not say where this
   job lands, stop creation and raise it as a decision the way step 3 routes
   questions (HQ Rulebook, No new homes just to finish setup) instead of
   inventing a destination. The build follows code-block-routing's dedupe and worktree isolation rules.

5. **Gate birth on repo-standards Stage B.** The new repo reaches the live Repo
   rules baseline, its Project relationship is recorded per Project ownership,
   and its Archive Index row is added through Stage B item 8. Read the sheet
   back independently, outside the job's own claim, before anything says birth
   complete. A merged scaffold, a repo URL, an open issue or a pending entry
   without the landed row is an incomplete birth.

6. **Reconcile downstream routing.** The Archive Index row is the only
   registration. Check the row's scan profile and declared consumers. The Estate
   Brain door is retiring (Decision Log 2026-10-13), so no door registration is
   requested. Never promise that a retired worker or queue will index the repo
   automatically. If intake routing needs a new brain mapping, change its
   canonical source (`expert-partners-skills plugins/operating-doctrine/skills/intake/SKILL.md`)
   from the Archive Index row through the normal pull request path, never by
   hand-editing a deployed copy.

7. **Report the Stage B result with evidence.** Include the Stage A verdict,
   the authorization, the Job issue, repo URL, baseline evidence, Project
   relationship, the Archive Index row and its readback date, and routing
   status. Name remaining gaps explicitly.

## Rules

- Never creates a repo the gate did not justify or the required authorization
  does not cover. repo-standards is the one standard; this skill is a runner of
  it, never a second one.
- Never create a repository whose name already exists in the org, active or
  archived.
- ag-vault is never a valid project name here.
- Never use em dashes in any content this skill writes (org standard).

## Test cases

The outcome cases live in [tests/behavioral-cases.md](tests/behavioral-cases.md).
