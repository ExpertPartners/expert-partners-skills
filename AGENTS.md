# AGENTS.md -- expert-partners-skills

This repository holds the skills marketplace and its tooling. skills holds standalone skills. plugins holds plugin manifests and the skills they carry. tools holds the skill graph producer and the deploy producer. operating-doctrine holds the pointer to the canonical doctrine skill.

Business knowledge, rules, and decisions do not live here. They live in the business brains in Google Drive, starting with the HQ Rulebook and the Decision Log in HQ Business Brain, Company Core. Read those before acting on anything that could depend on a prior decision, an owner, a brand, or an operating rule. If a brain cannot be reached, say so and separate verified fact from unverified reasoning. Do not add knowledge files here.

Working here

- Read the skill you are changing and the canonical operating-doctrine skill first.
- Use an isolated branch or worktree, inspect git state before editing, and open a pull request for every change. Never force-push or bypass required checks.
- Correct the canonical skill source first. Generated files, deployed copies, and the skill graph come only from their producers in tools. Never hand-edit them.
- Run the changed-file gates in .pre-commit-config.yaml and .github/workflows/ci.yml, plus the tests under tools, before pushing. Report real results.
- Secrets live in 1Password only. They never appear in code, logs, config, or chat.
- Do not deploy, publish, upload, or delete anything permanent without the applicable founder's explicit yes.
