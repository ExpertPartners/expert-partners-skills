# AGENTS.md -- expert-partners-skills

This repository holds the skills marketplace and its tooling. skills holds standalone skills. plugins holds plugin manifests and the skills they carry. tools holds the skill graph producer and the deploy producer. operating-doctrine holds the pointer to the canonical doctrine skill.

Business knowledge, rules, and decisions do not live here. They live in the business brains in Google Drive, starting with the HQ Rulebook and the Decision Log in HQ Business Brain, Company Core. Read those before acting on anything that could depend on a prior decision, an owner, a brand, or an operating rule. If a brain cannot be reached, say so and separate verified fact from unverified reasoning. Do not add knowledge files here.

Working here

- Read the skill you are changing and the canonical operating-doctrine skill first.
- Use an isolated branch or worktree, inspect git state before editing, and open a pull request for every change. Never force-push or bypass required checks.
- Correct the canonical skill source first. Generated files, deployed copies, and the skill graph come only from their producers in tools. Never hand-edit them.
- Run the changed-file gates in .pre-commit-config.yaml and .github/workflows/ci.yml, plus the tests under tools, before pushing. Report real results.
- Validation command for jobs from the Chat to Code Loop: run tools/validate-job.sh from the repo root. It runs the changed-file gates from ci.yml, the skill description cap and gitleaks, and exits 0 only when all pass. A job is not done until it prints validate-job: PASS.
- Secrets live in 1Password only. They never appear in code, logs, config, or chat.
- Do not deploy, publish, upload, or delete anything permanent without the applicable founder's explicit yes.

## Company rules

Read Organization Instructions, the HQ Rulebook and the Decision Log, all in HQ Business Brain, Company Core, before relying on company rules or decisions. Find each Doc by its title in Google Drive, and never copy a Doc link or ID into this repository, because it is public. Business knowledge lives in the owning Google Drive brain. If a required read fails, stop dependent work and report it. Do not copy the instructions here.

- For messages between AIs and delivery confirmations, follow the current HQ Rulebook section Handoffs between AIs. When Allison types Q or q alone, or says ask me clarifying questions, ask before working, one question at a time, most important first, using the ask-me-questions skill.
- File this job's report with job_finish, including a summary and result link, and verify it with job_status. Preserve unfinished work in its existing Chat to Code job. Before archive readiness, leave no uncommitted or unpushed work of its own and follow the HQ Rulebook section Session lifecycle.
- Never give legal, tax, or compliance advice, or suggest a professional, unless Allison asks.
