# AGENTS.md -- expert-partners-skills

This repository holds the skills marketplace and its tooling. skills holds standalone skills. plugins holds plugin manifests and the skills they carry. tools holds the skill graph producer and the deploy producer. operating-doctrine holds the pointer to the canonical doctrine skill.

Business knowledge, rules, and decisions do not live here. They live in the business brains in Google Drive, starting with the HQ Rulebook and the Decision Log in HQ Business Brain, Company Core. Read those before acting on anything that could depend on a prior decision, an owner, a brand, or an operating rule. If a brain cannot be reached, say so and separate verified fact from unverified reasoning. Do not add knowledge files here.

Working here

- Read the skill you are changing and the canonical operating-doctrine skill first.
- Use an isolated branch or worktree, inspect git state before editing, and open a pull request for every change. Never force-push or bypass required checks.
- Correct the canonical skill source first. Generated files, deployed copies, and the skill graph come only from their producers in tools. Never hand-edit them.
- Never edit a plugin version in plugin.json or marketplace.json, or the top of a CHANGELOG.md. Add one note in .changeset/ instead, as .changeset/README.md explains. The release step in tools/release owns versions and CHANGELOG entries.
- Run the changed-file gates in .pre-commit-config.yaml and .github/workflows/ci.yml, plus the tests under tools, before pushing. Report real results.
- Validation command for jobs from the Chat to Code Loop: run tools/validate-job.sh from the repo root. It runs the changed-file gates from ci.yml, the skill description cap and gitleaks, and exits 0 only when all pass. A job is not done until it prints validate-job: PASS.
- Secrets live in 1Password only. They never appear in code, logs, config, or chat.
- Do not deploy, publish, upload, or delete anything permanent without the applicable founder's explicit yes.

## Company rules

Read Organization Instructions, the HQ Rulebook and the Decision Log, all in HQ Business Brain, Company Core, before relying on company rules or decisions. Find each Doc by its title in Google Drive, and never copy a Doc link or ID into this repository, because it is public. Business knowledge lives in the owning Google Drive brain. If a required read fails, stop dependent work and report it. Do not copy the instructions here.

- For messages between AIs and delivery confirmations, follow the current HQ Rulebook section Handoffs between AIs. When Allison types Q or q alone, or says ask me clarifying questions, ask before working, one question at a time, most important first, using the ask-me-questions skill.
- If a task conflicts with the Decision Log, the newest Decision Log entry wins. Follow it without asking.
- Questions go on the board (Decision Log 2026-11-02, which wins if this line drifts from it). Never wait on a question you raise yourself inside your own app (Factory, Codex, Claude Code). This does not change the ask-me-questions flow above: when Allison asks for clarifying questions, ask her in chat and wait for each answer. If a question truly needs Allison, post it as a comment on the GitHub issue starting `Question for Allison`, or mark the existing Chat to Code job needs-allison with one line starting Recommend: through the job tool's supported nonterminal path, never job_finish, and keep working on everything that does not depend on it.
- When the assignment is complete, file this job's report with job_finish, including a summary and result link, and verify it with job_status. Preserve unfinished work and its nonterminal state in its existing Chat to Code job; a partial wrap never calls job_finish. Before archive readiness, leave no uncommitted or unpushed work of its own and follow the HQ Rulebook section Session lifecycle.
- Never give legal, tax, or compliance advice, or suggest a professional, unless Allison asks.

## Review guidelines

These rules bind Codex and every other reviewer of pull requests here, and the builder answering them. A round is one review posted on the pull request.

- Block only on P0 and P1 findings. A P2 or lower finding never blocks a merge.
- Re-review only the newest commit. Do not reopen code an earlier round already reviewed unless the newest commit changed it.
- Review rounds have no limit (Decision Log 2026-11-02, No caps stop work, which wins if this line drifts from it). The builder keeps fixing P0 and P1 findings round after round. Only a finding that comes back after it was fixed goes to Allison: mark the existing Chat to Code job needs-allison with one line starting Recommend: through the job tool's supported nonterminal path, never as a question inside an app.
- Fix a P2 only when the fix is small and inside the pull request's scope. Otherwise reply on the thread with the reason it is not fixed here, and resolve the thread.
- Do not report style, rare edge cases, or refinements of an earlier fix.
