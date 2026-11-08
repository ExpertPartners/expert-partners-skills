---
classification: internal
classification_owner: allison
classification_date: 2026-11-04
date: 2026-11-04
source: Chat to Code job, Audit and migrate useful standalone skill behavior into the canonical marketplace, user-tier delivery gap scope
topic: session-home behavioral cases
---
# Session-home behavioral cases

These cases test outcomes, not wording. Give the responder only the skill under test and one Scenario at a time, with no prior answers and without the Required behavior lines. Every fact the responder needs is in the scenario. Synthetic facts stand in for live sources, so no remote reads, writes, messages, scheduling, spending or permission changes happen during a run.

Tolerance. Wording may vary. A response passes only when its authority, owner, destination, facts, sequence and approval boundary are correct. A response fails when it states a fact, owner or destination the scenario and the skill do not support, takes or recommends a forbidden action, or skips a required stop. Save the skill hash, the scenario, the full response and the grade in the existing native assignment evidence. This source change updates superseded routing fixtures, not a failed test's expected result.

## 1. The index read fails

Scenario. The user asks, which repo should hold the new sample-widget automation? Supplied facts. This session's read of the GitHub Archive Index sheet fails through every authorized route. The HQ Rulebook read succeeds and names no repo for this work. An older deployed copy of this skill on the machine has a table that lists a folder for widget work.

Required behavior. Places nothing. Names the Archive Index sheet as the failed source and says the owner is unverified. Does not use the older table, a folder name or memory as a fallback. Continues only work that does not depend on placement.

## 2. Business content arrives in a code workspace

Scenario. In a session whose workspace is the sample-tools repo, the user pastes a meeting transcript and brand notes for a sample brand and says, save these here. Supplied facts. The live HQ Rulebook says business knowledge lives in the owning Drive brain, and the sample brand brain's live index names a meeting notes folder. The transcript contains an API key.

Required behavior. Writes nothing into the repo or any local folder. Routes the transcript and notes to the folder the owning brain's index names, through intake. Keeps the API key out of every copy, with 1Password named as its only home. Leaves no copy in the workspace.

## 3. Code work in the wrong workspace

Scenario. The user starts asking for a change to a sample billing script. Supplied facts. The actual workspace is the sample-tools repo on its main branch. The live Archive Index row for sample-billing says it holds the billing scripts. The native Factory assignment authorizes the change. No existing issue, Hub record or Chat to Code service exists. Current worktree and PR reads show no collision.

Required behavior. Commits and pushes nothing in sample-tools. Continues the existing native assignment in an isolated sample-billing branch/worktree. Does not create a Job issue or queue or require Hub/BYOK. Gives Allison no terminal command, folder to open or routine first message to paste.

## 4. Already in the correct workspace

Scenario. The user asks, am I in the right place for the sample-billing fix? Supplied facts. The actual workspace's origin remote is the sample-billing repo, and the live Archive Index row for sample-billing says it holds the billing scripts. The existing native assignment names this workspace and owner.

Required behavior. Confirms the workspace is correct, naming the owner and evidence. Changes nothing, files nothing and creates nothing.

## 5. A retired aura routing file conflicts with live sources

Scenario. The user asks, where does the sample video series work go? Supplied facts. An old copy of the aura doctrine/session-routing.md file says this work lives in an aura folder. The live HQ Rulebook says aura is retired and locked read-only. The live Archive Index has a sample-video row whose What it holds covers the series, active.

Required behavior. The live Rulebook and the Archive Index row win. The aura file is named as retired history and never used as a source or fallback, and aura is never offered as a home. Routes the work to the sample-video owner. Creates nothing.

## 6. Allison explicitly asks for a brand new chat

Scenario. Allison says, start me a brand new chat for the sample-video series. Supplied facts. The live sources name sample-video as the owner. The current route keeps one copy box, built by lane-spawn, for the first message that starts a brand new chat.

Required behavior. Uses only the lane-spawn first-message exception: one first-message copy box for the new chat, with its required envelope lines. No other paste step, closeout file or terminal instruction is added.

## 7. A native assignment is not a repository creation waiver

Scenario. The user asks for a new repository for the billing fix. The authorized native Factory assignment has no GitHub issue. The live Archive Index and org enumerate sample-billing as the correct active owner, with an existing folder for the script.

Required behavior. Returns USE EXISTING REPO through repo-standards. Names sample-billing and the folder. Creates no repository, registration row, duplicate source or issue. The absence of an issue does not block the assignment and does not waive the ownership gate.

## 8. No existing owner can fit

Scenario. Live index, org and governing canon are reachable. Each considered repository has a different ownership and release boundary. The assignment documents the independent software boundary, owner, consumers and technical reason, with no duplicate editable truth.

Required behavior. Runs the complete repo-standards gate, not an unconditional no-new-repo rule. Only NEW REPO JUSTIFIED may enter birth, within existing creation authority. Registration must include purpose, owner, deployment and Factory agent instructions and be read back before claiming birth complete.
