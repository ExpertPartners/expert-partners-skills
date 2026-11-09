---
name: new-project
description: >
  Run a new Expert Partners project through repo-standards before anything is
  built. Runs creation Stage A live, builds in the existing repo on USE EXISTING
  REPO, and creates the repo and scaffolds it on NEW REPO JUSTIFIED. Registers
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

Runs `repo-standards`, the one repository standard. This skill adds only the order of steps. Load the current `expert-partners-skills plugins/operating-doctrine/skills/repo-standards/SKILL.md` and `plugins/operating-doctrine/skills/code-block-routing/SKILL.md` for every run.

The legacy local bootstrap script and any older deployed copy that describes it are history, never a route.

## Steps

1. **Parse the input.** Extract the proposed project name and the durable job it would hold. Look for an existing Factory session or Workstream already carrying this request (call find_owner) and continue it.

2. **Run repo-standards creation Stage A live.** Read the GitHub Archive Index sheet and complete the ownership gate. On `USE EXISTING REPO`, do the work in that owner's repo (an archived owner is a revival candidate, so revive it rather than duplicating) and report the owner and Archive Index row. On `NEW REPO JUSTIFIED`, continue. If a live read fails, fix the access and rerun.

3. **Create and scaffold.** Create the repo and scaffold it through a Factory assignment or Claude Code in an isolated worktree, following code-block-routing's dedupe and worktree rules. Never create a repo whose name already exists in the org, active or archived.

4. **Born to standard.** Complete repo-standards Stage B: the Repo rules baseline, the Project relationship per Project ownership, and the Archive Index row through Stage B item 8.

5. **Reconcile routing.** The Archive Index row is the only registration. Check its scan profile and declared consumers. The Estate Brain door is retired (Decision Log 2026-10-13). If intake routing needs a new brain mapping, change its canonical source through a pull request, never by hand-editing a deployed copy.

6. **Report.** Stage A verdict, Job or assignment, repo URL, baseline evidence, Project relationship and the Archive Index row, with links.

## Rules

- repo-standards is the one standard. This skill runs it and is never a second one.
- ag-vault is never a valid project name here.
- Never use em dashes in any content this skill writes.

Outcome cases live in [tests/behavioral-cases.md](tests/behavioral-cases.md).
