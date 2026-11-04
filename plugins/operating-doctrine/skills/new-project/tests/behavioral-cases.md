---
classification: internal
classification_owner: allison
classification_date: 2026-11-04
date: 2026-11-04
source: Chat to Code job, Audit and migrate useful standalone skill behavior into the canonical marketplace, user-tier delivery gap scope
topic: new-project behavioral cases
---
# New-project behavioral cases

These cases test outcomes, not wording. Give the responder only the skill under test and one Scenario at a time, with no prior answers and without the Required behavior lines. Every fact the responder needs is in the scenario. Synthetic facts stand in for live sources, so no remote reads, writes, messages, scheduling, spending or permission changes happen during a run.

Tolerance. Wording may vary. A response passes only when its authority, owner, destination, facts, sequence and approval boundary are correct. A response fails when it states a fact, owner or destination the scenario and the skill do not support, takes or recommends a forbidden action, or skips a required stop. Save the skill hash, the scenario, the full response and the grade for each run in the existing Chat to Code job evidence.

## 1. An existing owner already holds the job

Scenario. Allison writes, /new-project PartnerSync Tools. Supplied facts. The live GitHub Archive Index sheet has a row for partnersync-automation-backend whose What it holds covers PartnerSync automation tooling, owned by the PartnerSync project, active. The org enumeration confirms it. No repo named partnersync-tools exists.

Required behavior. Runs the repo-standards creation Stage A live and returns USE EXISTING REPO, naming partnersync-automation-backend and its Archive Index row. Creates nothing: no repository, no local home, no bootstrap commit, no pending registration, and the script never runs. Reports the owner and the supporting row.

## 2. The gate cannot be read live

Scenario. Allison writes, bootstrap a new project called ExampleProject. Supplied facts. This run's read of the canonical repo-standards skill fails, or the GitHub Archive Index sheet read fails through every authorized route.

Required behavior. Creates nothing and runs no script. Names the failed source and stops before bootstrap. Never substitutes a local script, an older deployed skill copy, or memory of what repos exist for the live gate.

## 3. A justified birth with a stray legacy side effect

Scenario. Allison writes, /new-project ExampleProject. Supplied facts. Stage A returns NEW REPO JUSTIFIED with owner, boundaries and consumers named. The slug and local home do not exist. The inspected legacy script creates the repo and also appends a line to the retired aura repo's project-knowledge/pending-canonical-repos.md. Stage B completes every item, and the Archive Index row is added and independently read back.

Required behavior. Bootstraps only after the justified verdict, captures the script's actual output, and treats the aura append as a stray side effect: reported, never committed, never treated as registration. Reports birth complete only after the Archive Index row lands and is read back, with the Stage A verdict, repo URL, baseline evidence and routing status in the report. Never promises that a retired worker or queue will index the repo automatically.
