# AGENTS.md -- expert-partners-skills

This repository holds the skills marketplace and its tooling. skills holds standalone skills. plugins holds plugin manifests and the skills they carry. tools holds the skill graph producer, the deploy producer, the merge gate, the guard hooks (tools/hooks) and the generated-surface renderer (tools/generate). operating-doctrine holds the pointer to the canonical doctrine skill.

Business knowledge, rules, and decisions do not live here. They live in the business brains in Google Drive, starting with the HQ Rulebook and the Decision Log in HQ Business Brain, Company Core. Read those before acting on anything that could depend on a prior decision, an owner, a brand, or an operating rule. If a brain cannot be reached, say so and separate verified fact from unverified reasoning. Do not add knowledge files here.

Use headless access first, then Ember's signed-in Chrome on the M2 when that gets the job done. A guard that refuses only because it is out of date gets updated, not obeyed.

Working here

- Read the skill you are changing and the canonical operating-doctrine skill first.
- Use an isolated branch or worktree, inspect git state before editing, and open a pull request for every change. Never force-push or bypass required checks.
- Correct the canonical skill source first. Generated files, deployed copies, and the skill graph come only from their producers in tools. Never hand-edit them.
- Never edit a plugin version in plugin.json or marketplace.json, or the top of a CHANGELOG.md. Add one note in .changeset/ instead, as .changeset/README.md explains. The release step in tools/release owns versions and CHANGELOG entries.
- Run the changed-file gates in .pre-commit-config.yaml and .github/workflows/ci.yml, plus the tests under tools, before pushing. Report real results.
- Validation command for repository changes: run tools/validate-job.sh from the repo root. The historical command name is not a queue dependency. It runs the changed-file gates from ci.yml, the skill description cap and available secret scan. Report any missing check separately from its PASS marker.
- Secrets live in 1Password only. They never appear in code, logs, config, or chat.
- Act by default. Allison's brief is the go and there are no approval gates. Deploy, publish, merge and clean up as the work needs, then report with links.

## Company rules

Read Organization Instructions, the HQ Rulebook and the Decision Log, all in HQ Business Brain, Company Core, before relying on company rules or decisions. Find each Doc by its title in Google Drive, and never copy a Doc link or ID into this repository, because it is public. Business knowledge lives in the owning Google Drive brain. If a required read fails, stop dependent work and report it. Do not copy the instructions here.

- For messages between AIs and delivery confirmations, follow the current HQ Rulebook section Handoffs between AIs. When Allison types Q or q alone, or says ask me clarifying questions, ask before working, one question at a time, most important first, using the ask-me-questions skill.
- If a task conflicts with the Decision Log, the newest Decision Log entry wins. Follow it without asking.
- Use the current native Factory assignment and owning Workstream for coordination. Do not require a GitHub issue or Hub record, create a Chat to Code job, restart polling, or ask Allison to relay routine messages. Existing issues and PRs remain source-control evidence, not universal intake requirements. Retrieval and technical gaps stay AI owned. A genuine founder decision names the blocker and recommendation through the current supported route, without claiming completion. User-requested clarifying questions remain separate.
- Before creating any repository, run the live repo-standards placement gate. Prefer an existing repo and folder. Missing authority stops placement; native execution is not a shortcut around ownership or registration.
- Finish with the actual checks, result links and limits in the owning assignment. Preserve unfinished work with its owner, return condition and expected result. A source PR, merge, installed delivery and active use are separate claims. Merge when checks pass.
- Never give legal, tax, or compliance advice, or suggest a professional, unless Allison asks.

## Review guidelines

These rules bind Codex and every other reviewer of pull requests here, and the builder answering them. A round is one review posted on the pull request.

- Block only on P0 and P1 findings. A P2 or lower finding never blocks a merge.
- Re-review only the newest commit. Do not reopen code an earlier round already reviewed unless the newest commit changed it.
- Review rounds have no numeric cap. Fix in-scope findings through the existing PR and authorized review route. Recurring findings require root-cause evidence. Only a genuine founder decision uses the decision route above. Do not report unfinished work as done.
- Fix a P2 only when the fix is small and inside the pull request's scope. Otherwise reply on the thread with the reason it is not fixed here, and resolve the thread.
- Do not report style, rare edge cases, or refinements of an earlier fix.
