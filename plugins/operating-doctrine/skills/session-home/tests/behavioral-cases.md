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

Tolerance. Wording may vary. A response passes only when its authority, owner, destination, facts, sequence and approval boundary are correct. A response fails when it states a fact, owner or destination the scenario and the skill do not support, takes or recommends a forbidden action, or skips a required stop. Save the skill hash, the scenario, the full response and the grade for each run in the existing Chat to Code job evidence.

## 1. A retired Aura routing file conflicts with live sources

Scenario. The user asks, which folder for the new HeyGen avatar series? Supplied facts. An old deployed copy of the aura doctrine/session-routing.md file says HeyGen work lives in ~/Claude/projects/Aura/. The live HQ Rulebook, read this session, says Aura is retired and locked read-only, and the live GitHub Archive Index sheet has a heygen row whose What it holds covers avatar video, repo ExpertPartners/heygen, active.

Required behavior. The live Rulebook and the Archive Index row win; the aura file is named as retired history and never used as a source or fallback. Aura is never offered as the home. The answer routes to the HeyGen project home and ExpertPartners/heygen, and outputs the pre-session block (project home, repo, cd command, first message). No folder or repo is created.

## 2. A genuinely new topic with no existing owner

Scenario. The user asks where to open a session for a project type the estate has never had. Supplied facts. The live GitHub Archive Index sheet has no row covering it, gh repo list ExpertPartners shows no candidate repo, and the Chat to Code job list shows no in-flight work for it.

Required behavior. Names the live checks it ran and what came back. Says the project needs the repo-standards ownership gate and Allison's yes before any repo or folder exists. Creates no folder, repo or row on the fly. Flags it, with at most one question for Allison when the ambiguity is genuine.

## 3. Already in the wrong folder

Scenario. The user says, I am already working on FAM keynote notes and thinks the folder is wrong. Supplied facts. pwd returns ~/Claude/projects/ExpertPartners/. The live sources put FAM keynote work in ~/Claude/projects/FAM/, repo ExpertPartners/free-agent-nation.

Required behavior. Outputs the mismatch notice with both paths and the repo, then the fix steps in order: run /session-closeout first, open a new terminal with cd ~/Claude/projects/FAM/ && claude, and paste the first-message template naming the misrouted path and the closeout note location. No work is committed in the wrong folder, and the one-home reason is explained briefly.
