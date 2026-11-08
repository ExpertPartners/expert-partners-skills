---
name: session-home
description: |
  Check that a piece of work is happening in its current owning home. Resolves
  the owner live from the HQ Rulebook (Where things live, Project ownership), the
  GitHub Archive Index row, the native Factory assignment and the owning
  brain's index, then reads the actual host and workspace. Confirms an
  already-correct workspace and changes nothing. Routes business material to its
  indexed Drive brain home, never a repo or folder. Code work found in the wrong
  workspace is not committed there; it goes on the current code route for the
  owning repo, never as a terminal-and-paste step for Allison. A failed live read
  stops placement. Trigger when the user asks where work should happen, which
  repo or folder for X, am I in the right place, or starts work that does not
  match the current workspace.
argument-hint: "[topic or description of the work]"
allowed-tools: Bash, Read
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
inherits: operating-doctrine
brand-scope: null
subtitle: "route work to its current owning home"
---

# Session Home

One job. Before work lands, confirm it is happening in the home that currently owns it, so nothing is committed to the wrong repo and no business material ends up outside its brain.

Provenance. This skill carries forward useful method from the user-tier session-home skill adopted into canonical on 2026-08-05. The fixed topic-to-folder table, the hard-coded local folder layout and the closeout-then-paste redirect in that source are retired. The retired aura `doctrine/session-routing.md` is history, never a source. This skill carries no ownership table, folder path or repo roster of its own.

## Step 1. Name the work

Use the work described in the request. If none is described, ask one short question about what the work is. Then sort it:

- **Code**: changes to a repository's files, tooling, skills or automation.
- **Business material**: rules, decisions, brand notes, plans, meeting notes, transcripts, research and other knowledge.
- **Both**: split them, and route each part on its own.

## Step 2. Resolve the owner live

Read these live this session, each found by its title or its current tool, never from memory:

1. The HQ Rulebook sections Where things live and Project ownership.
2. For code, the owning repo's row in the GitHub Archive Index sheet (What it holds, Pile), checked against the live org.
3. In-flight work through the owning Factory assignment or Workstream, current branches/worktrees and open PRs. Read an existing issue when it carries relevant work, but do not require one. Chat to Code records and the Job Tracker are historical evidence, not a queue to restart.
4. For business material, the owning brain's `00 START HERE` index, which names its folder for that kind of content.

The newest applicable Decision Log entry wins over older text. Never infer an owner from a repo name, a folder name or a deployed copy of this skill.

If a read that placement depends on fails through every authorized route, stop placement. Name the failed source, say what is verified and what is not, and place nothing. No table, aura file, memory, older deployed copy or folder name stands in for the failed read. Continue only work that does not depend on placement.

## Step 3. Read the actual workspace

Read where this session actually runs instead of assuming a folder layout: the host, the working directory, and for a Git workspace its top level, `origin` remote, branch and worktree list. Compare that with the owner from Step 2.

## Step 4. Act on the result

- **Already in the right home.** Say so, name the owner and the evidence, and change nothing.
- **Business material.** It goes to the folder the owning brain's index names, filed through the intake skill, never into a repo or a local folder, and no copy stays in the workspace. Secrets and credentials go to 1Password only and are never copied into notes, transcripts, Docs or repos.
- **Code work in the wrong workspace.** Commit and push nothing here. Continue the authorized native Factory assignment in the owning repo on an isolated branch/worktree, coordinating current owners and open PRs first. No GitHub issue, Hub record or job queue is a prerequisite. Preserve and report any edits already made in the wrong workspace; do not discard user work. Never hand Allison a terminal command, a folder to open or a routine first message to paste.
- **Allison explicitly asks to start a brand new chat.** Only then does the one first-message copy box apply, built by lane-spawn under code-block-routing. Ordinary routing and mismatch handling never become a paste task.
- **No owner exists yet.** Report the live checks and what came back. The work needs the repo-standards creation gate (run through new-project) before any repo or folder exists. Create nothing on the fly.

## Edge cases

- **Aura as a home.** Aura is retired and locked read-only. It is never a home, a source or a fallback.
- **Work spanning owners.** Split it by owner. Cross-brand rules and decisions live in the HQ Business Brain in Drive.
- **Genuinely unclear ownership.** Bring Allison one question with a recommendation, routed the way the HQ Rulebook and Decision Log route questions, and keep working on everything that does not depend on the answer.

## Why it matters

Work committed in the wrong workspace lands in the wrong repo, and knowledge stored outside its brain breaks the one-home rule. Each thing has one home, in the owning Drive brain or the owning repo.

## Test cases

The outcome cases live in [tests/behavioral-cases.md](tests/behavioral-cases.md).
