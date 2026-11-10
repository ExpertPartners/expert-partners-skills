# auto-merge-gate

> Current use, November 9, 2026. Chat to Code job issues are retired, so the live route is a pull request labeled `auto-merge` that merges once its checks pass. The job issue route below is kept only so older pull requests still resolve.

Legacy compatibility for older job-linked pull requests: the gate checks required CI and review status before merging. Pull requests remain required, and Ember's repository is never touched: the workflow runs only in this repository, and `gate.py` refuses any repository named ember.

| File | What it does |
|---|---|
| `gate.py` | The gate. `plan` evaluates pull requests and comments refusals. `merge` re-checks and squash-merges. Python standard library only. |
| `tests/test_gate.py` | Unit tests for every refuse case and the merge case, including the P0 and P1 threshold replayed on pull request #214. All GitHub calls are mocked. |
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
2. Codex reviewed the head and left no P0 or P1 finding open. Only P0 and P1 block (AGENTS.md, Review guidelines). The gate reads the `codex-review-state:v1` JSON in the latest review summary comment from `chatgpt-codex-connector[bot]`: `code_review.commit_sha` equals the head sha and `code_review.status` is `completed`. If Codex has not reviewed the head yet, or its review is not completed, the gate waits, whatever findings exist. When that summary is missing or covers an older commit, a `codex-review-receipt:v1` comment from `chatgpt-codex-connector[bot]` that says `Codex Review: Didn't find any major issues` and whose `Reviewed commit` (the full sha, or at least its first 10 characters) is a prefix of the head sha counts as a completed code review of the head. A Codex Security Review receipt never counts as a code review.

   `has_unresolved_findings` is an aggregate, not a severity. When it is `false` the review passes. When it is `true`, or `null` after the pull request has had findings, the gate reads each inline finding Codex left (top-level review comments by `chatgpt-codex-connector[bot]`; replies and other authors are not review evidence) and its severity badge (`![P1 Badge]` and so on). A clean receipt for the head is checked the same way, so a finding left open on an earlier commit still counts.

   - A P0 or P1 finding blocks when Codex raised it on the head (resolving the thread does not fix the code) or its thread is still unresolved. A resolved P0 or P1 from an older commit does not block.
   - A P2 or lower finding never blocks on its severity, open or resolved. Its owner fixes it when the fix is small and in scope; otherwise they reply on the thread with the reason and resolve it (AGENTS.md, Review guidelines). The gate does not check that step.
   - A finding with no readable severity, or more than one, counts as a gap in the review evidence and blocks like a P1. So does a P0 or P1 from an older commit whose thread state the gate cannot read.
   - When the summary says `true` but the gate finds no open Codex finding to read, or cannot read the review comments, it refuses and says so. It never treats that as clean.

   The same rule applies to the security review. When `security_review` on the head reports `has_unresolved_findings: true`, the gate reads the Codex findings marked `codex-security-review-finding:v1`: a P0 or P1 blocks, a P2 or lower does not, and a summary it cannot explain with an open security finding is refused as an evidence gap.

   Each refusal names the blocking finding by severity, kind, title and link, or names the missing evidence.
3. GitHub reports the pull request as mergeable.
4. The pull request leaves plugin versions and CHANGELOG entries to the release step (`tools/release`, fed by notes in `.changeset/`). The gate reads the pull request's changed files and refuses a change to a plugin's `version` in `plugins/<plugin>/.claude-plugin/plugin.json` or `.claude-plugin/marketplace.json`, a new `CHANGELOG.md`, a new CHANGELOG entry, and any edit to the top entry. It compares each file against the merge base, so a release that landed on main after the branch was cut does not count against the branch. A brand new plugin may carry its first version, and edits to older CHANGELOG entries pass. It also reads every note the pull request adds or changes in `.changeset/` (top-level `*.md`, not the README) and refuses one the release step would refuse: a bad format, a bump other than `patch`, `minor` or `major`, no text, a `## ` heading in the text, or a plugin that is not in `.claude-plugin/marketplace.json` at the head. A watched file that is not UTF-8 text or not the JSON object it should be refuses that pull request and does not stop the run. If GitHub cannot return a file at all, the run fails and nothing merges. This applies to every pull request the gate considers, including ones it considers through the merge label.

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
