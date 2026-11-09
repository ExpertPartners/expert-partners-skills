---
classification: internal
classification_owner: allison
classification_date: 2026-11-08
date: 2026-11-08
source: Decision Log 2026-11-08, Act by default, caution removed
topic: new-project behavioral cases
---
# New-project behavioral cases

These cases test outcomes, not wording. Give the responder only the skill under test and one Scenario at a time. Synthetic facts stand in for live sources.

## 1. An existing owner already holds the job

Scenario. Allison writes, /new-project Sample Sync Tools. The live Archive Index sheet has an active row for sample-sync-backend whose What it holds covers Sample Sync automation tooling.

Required behavior. Returns USE EXISTING REPO naming sample-sync-backend and its row, creates no repo, and does the work in the existing repo.

## 2. The gate cannot be read live

Scenario. Allison writes, bootstrap a new project called Sample Project. The Archive Index read fails on the first route. An older deployed copy of the skill lists repos and says to run a local bootstrap script.

Required behavior. Tries another route to read the sheet, does not use the older copy, a local script or memory, and continues once the gate returns.

## 3. A justified birth

Scenario. Allison writes, /new-project Sample Project. Stage A returns NEW REPO JUSTIFIED.

Required behavior. Creates and scaffolds the repo through a Factory assignment or Claude Code in an isolated worktree, completes Stage B including the Archive Index row, and reports with links. Asks no approval question and hands Allison no copy box.
