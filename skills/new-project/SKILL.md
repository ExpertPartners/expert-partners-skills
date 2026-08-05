---
name: new-project
description: >
  Bootstrap a new Expert Partners project: creates a private GitHub repo under
  ExpertPartners/<slug>, creates ~/Claude/projects/<Home>/, writes CLAUDE.md from
  the canonical template, creates intake/ (ADR 0027 convention), pushes the initial
  commit, registers the repo for S1 CANONICAL_REPOS sync, and updates the /intake
  skill's project table so the brain can index it immediately.
  Use when Allison says "/new-project <Name>", "new project: <Name>", "bootstrap a
  new project called <Name>", or the session-wrap new-project variant fires.
# --- skill-map metadata (additive, all optional) ---
# Adopted into canonical 2026-08-05 (Skill Map Rulings lane, flags item 9);
# the machine copy at ~/.claude/skills is a deployed copy.
status: live
subtitle: "bootstrap a new Expert Partners project"
---

# New-Project Skill

Creates a complete, brain-connected project home from one command.

## Steps

1. **Parse input.** Extract the project home name (PascalCase, e.g., `FreeAgentNation`)
   and optional type (`brand` or `standalone`, default `standalone`). If the name is
   provided in a different case, normalize to PascalCase before passing to the script.

2. **Run the bootstrap script.**
   ```
   bash ~/scripts/new-project.sh <ProjectHome> [type]
   ```
   The script creates the GitHub repo, local home, CLAUDE.md, intake/.gitkeep, and
   initial commit. It also appends to
   `~/Claude/projects/Aura/project-knowledge/pending-canonical-repos.md`.
   Capture the script output and surface it.

3. **Commit pending-canonical-repos.md to aura.** After the script exits successfully,
   commit the pending-canonical-repos.md update to the aura repo:
   ```bash
   cd ~/Claude/projects/Aura
   git add project-knowledge/pending-canonical-repos.md
   git commit -m "chore(new-project): register <repo-slug> for S1 CANONICAL_REPOS sync

   Push-Policy: docs"
   git push origin main
   ```
   Run the sibling-session visibility check before this commit.

4. **Update the /intake skill's project table.** Open
   `~/.claude/skills/intake/SKILL.md` and add a row to the project map table:
   | <project keyword> | ~/Claude/projects/<Home> | ExpertPartners/<slug> | no (direct) |
   Save the file. This keeps the intake skill current without a manual step.

5. **Check brain registration.** Confirm the new repo slug appears in either (a) `CANONICAL_REPOS` in `tools/mcp-brain-server/server/server.py` (already registered) or (b) `project-knowledge/pending-canonical-repos.md` awaiting a CDK deploy (queued). If it appears in neither, the project is invisible to Aura and Ember via the brain -- add it to pending-canonical-repos.md now before closing the session.

6. **Report back.**
   - GitHub repo URL
   - Local home path
   - Pending-canonical-repos.md commit hash
   - Reminder to fill in the "What this home is" TODO in CLAUDE.md
   - Brain registration status (live in CANONICAL_REPOS, or pending CDK deploy)

## Rules
- Never create a project home that already exists on disk; the script will abort.
- ag-vault is never a valid project name here.
- Do not edit server.py or the brain server directly -- hand off via pending-canonical-repos.md only (sync point 3).
- Never use em dashes in any content this skill writes (org standard).
- Run the sibling-session visibility check before any commit to shared repos.

## New-project variant (from claude.ai)
If the user is in claude.ai and the session-wrap new-project prompt fires, the
output is a /new-project block for Claude Code:

```
/new-project <ProjectHome> [type]
```

Claude Code runs this skill when that block is pasted into a session.
