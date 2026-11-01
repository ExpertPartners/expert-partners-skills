# auto-merge-gate

Merges a finished Chat to Code job on its own once Factory's checks and Codex's automatic review both pass. No merge yes from Allison is needed. Authority: Decision Log 2026-11-01, Finished code merges itself, except in Ember's repo. Pull requests stay required, and Ember's repository is never touched: the workflow runs only in this repository, and `gate.py` refuses any repository named ember.

| File | What it does |
|---|---|
| `gate.py` | The gate. `plan` evaluates pull requests and comments refusals. `merge` re-checks and squash-merges. Python standard library only. |
| `tests/test_gate.py` | Unit tests for every refuse case and the merge case. All GitHub calls are mocked. |
| `../../.github/workflows/auto-merge-gate.yml` | Runs the gate. |

## When it runs

On `pull_request_target` (opened, synchronize, ready_for_review), `pull_request_review` (submitted), `issue_comment` (created, edited, pull requests only), `check_suite` (completed), every 15 minutes, and by hand through workflow_dispatch with an optional pull request number. A pull request event checks that pull request. The schedule, `check_suite` and a dispatch with no number check every open pull request.

GitHub does not send `check_suite` events for suites that GitHub Actions created, so most check results are picked up by the next 15 minute run. Codex editing its review summary comment starts a run straight away.

## Which pull requests it considers

All of these, or the pull request is left alone with no comment:

- open, not a draft, and based on main
- opened by `factory-droid[bot]`
- the body starts with `Closes #N`, and issue N is an issue (not a pull request) carrying the label `job`

## When it merges

All of these must be true for the current head commit:

1. Every check run and commit status on the head is complete and is success, neutral or skipped. The gate's own `auto-merge-gate` run is ignored. At least one other check must have reported, so a head with no checks yet waits.
2. Codex reviewed the head and left nothing open. The gate reads the `codex-review-state:v1` JSON in the latest review summary comment from `chatgpt-codex-connector[bot]`: `code_review.commit_sha` equals the head sha, `code_review.status` is `completed` and `code_review.has_unresolved_findings` is `false`. If the security review on the head reports unresolved findings, that also blocks. If Codex has not reviewed the head yet, the gate waits.
3. GitHub reports the pull request as mergeable.

The merge is a squash pinned to the evaluated head sha, so a push that lands mid-run makes GitHub reject it. It uses the EP Skills Graph Bot app token (repository variable `SKILLS_GRAPH_APP_CLIENT_ID`, secret `SKILLS_GRAPH_APP_PRIVATE_KEY`), never the workflow token and never Allison's login. Because the app makes the push, main still starts skills-graph and the marketplace webhook. The merge step re-checks every condition right before merging.

After a merge the gate adds the label `done` to the job issue and comments the merge commit on it. GitHub closes the issue through `Closes #N`.

## When it refuses

It posts one comment per head commit on the pull request, listing every condition that is not met. If the reasons change for the same head, it edits that comment instead of adding another. It does nothing else. A new push gets a new comment.

## Safety

- Pull request code never runs in the gate. Every event checks out `tools/auto-merge-gate` from main, and the merge credential is minted only after `plan` finds a pull request that passes. The token carries Contents write and nothing more.
- One gap is GitHub's, not the gate's: for `pull_request_review` and for a dispatch from another branch, GitHub runs the workflow file from that branch. A branch that edits `auto-merge-gate.yml` changes what those runs do, and any branch can already add a workflow that reads repository secrets. Restricting `SKILLS_GRAPH_APP_PRIVATE_KEY` to an environment that only main can use would close this. That is a repository setting, so it is left to Allison.
- The gate changes no ruleset or repository setting.

## Tests

From the repository root:

```
python3 -m unittest discover -s tools/auto-merge-gate/tests -v
```
