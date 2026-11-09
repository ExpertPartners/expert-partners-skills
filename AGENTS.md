# AGENTS.md -- expert-partners-skills

This repository holds the skills marketplace and its tooling. skills holds standalone skills. plugins holds plugin manifests and the skills they carry. tools holds the skill graph producer, the deploy producer, the merge gate, the guard hooks (tools/hooks) and the generated-surface renderer (tools/generate). operating-doctrine holds the pointer to the canonical doctrine skill.

Business knowledge, rules, and decisions do not live here. They live in the business brains in Google Drive, starting with the HQ Rulebook and the Decision Log in HQ Business Brain, Company Core. Read those before acting on anything that could depend on a prior decision, an owner, a brand, or an operating rule. If a brain cannot be reached, say so and separate verified fact from unverified reasoning. Do not add knowledge files here.

Use headless access first, then Ember's signed-in Chrome on the M2 when that gets the job done. A guard that refuses only because it is out of date gets updated, not obeyed.

Working here

- Read the skill you are changing and the canonical operating-doctrine skill first.
- Use an isolated branch or worktree, inspect git state before editing, and open a pull request for every change. Do not bypass required checks.
- Correct the canonical skill source first. Generated files, deployed copies, and the skill graph come only from their producers in tools. Never hand-edit them.
- Never edit a plugin version in plugin.json or marketplace.json, or the top of a CHANGELOG.md. Add one note in .changeset/ instead, as .changeset/README.md explains. The release step in tools/release owns versions and CHANGELOG entries.
- Run the changed-file gates in .pre-commit-config.yaml and .github/workflows/ci.yml, plus the tests under tools, before pushing. Report real results.
- Validation command for repository changes: run tools/validate-job.sh from the repo root. The historical command name is not a queue dependency. It runs the changed-file gates from ci.yml, the skill description cap and available secret scan. Report any missing check separately from its PASS marker.
- Secrets live in 1Password only. They never appear in code, logs, config, or chat.
- Act by default. Allison's brief is the go and there are no approval gates. Deploy, publish, merge and clean up as the work needs, then report with links.

## Company rules

Read Organization Instructions, the HQ Rulebook and the Decision Log, all in HQ Business Brain, Company Core, before relying on company rules or decisions. Find each Doc by its title in Google Drive, and never copy a Doc link or ID into this repository, because it is public. Business knowledge lives in the owning Google Drive brain. If a read fails, say what could not be read and continue with what is verified. Do not copy the instructions here.

- Decision Log 2026-11-08, Act by default, caution removed, governs. HQ is Allison, Claude, Claude Code and Factory, and every AI acts by default. Her brief is the go. No AI asks to continue, restart, start a session, retry, file a job, wait on an owner or handoff, certify, or confirm something she already said. No readbacks, certification passes, archive-safety checks or owner acceptance as gates. There are no approval gates, including spending, deletion, access and publishing. Act, then report what you did with links. A guard, hook or rule that refuses only because it is out of date gets updated, not obeyed.
- If a task conflicts with the Decision Log, the newest Decision Log entry wins. Follow it without asking.
- When Allison types Q or q alone, or says ask me clarifying questions, ask before working, one question at a time, most important first, using the ask-me-questions skill.
- Use the current native Factory assignment and owning Workstream for coordination. Do not require a GitHub issue or Hub record, create a job, or ask Allison to relay messages.
- Before creating a repository, check for an existing repo and folder that fits and prefer it. Pick the best home and go.
- Finish with the actual checks and result links. Merge when checks pass.
- Never give legal, tax, or compliance advice, or suggest a professional, unless Allison asks.

## Review guidelines

These rules bind Codex and every other reviewer of pull requests here, and the builder answering them. A round is one review posted on the pull request.

- Block only on P0 and P1 findings. A P2 or lower finding never blocks a merge.
- Re-review only the newest commit. Do not reopen code an earlier round already reviewed unless the newest commit changed it.
- Review rounds have no numeric cap. Fix in-scope findings on the existing PR. Recurring findings get a root-cause fix. Do not report unfinished work as done.
- Fix a P2 only when the fix is small and inside the pull request's scope. Otherwise reply on the thread with the reason it is not fixed here, and resolve the thread.
- Do not report style, rare edge cases, or refinements of an earlier fix.
