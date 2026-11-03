# overlap-check

Decides whether a Chat to Code build may start, before the Factory droid runs. Authority: Decision Log 2026-11-02, Factory runs everything at once (the only reason to hold a build is a real collision, and the held build names what it waits on), and Claimed jobs return after one missed check, five open pull requests per repo.

| File | What it does |
|---|---|
| `overlap_check.py` | The check. `check` judges one Job issue and labels it. `next` restarts the oldest waiting job after a pull request closes. Python standard library only. |
| `tests/test_overlap_check.py` | Unit tests for no overlap, ordinary overlap, shared-file overlap, the five pull request cap, the restart, and the workflow wiring. All GitHub calls are mocked. |
| `../../.github/workflows/factory-builder-reusable.yml` | The reusable builder that runs the check, then the droid. |
| `../../.github/workflows/factory-chat-to-code-loop-builder-skills.yml` | This repo's caller, the one small file other repos copy. |

## When a build waits

The check reads the issue's Files in scope (the `## Files in scope` heading or the bare `Files in scope` line from the job template, one path per line, backticks and `(new)` allowed). It compares them with:

- the changed files of every open builder pull request (opened by `factory-droid[bot]` or on a `job/` branch), and
- the Files in scope of every other open issue labeled `job` and `in-progress`.

Two paths collide when they are the same file, when one is a directory ending in `/` that holds the other, when one is a glob that matches the other, or when a shared file is named without its directory (`plugin.json`) and the other path ends in that name. Shared files are plugin.json, marketplace.json, CHANGELOG.md, AGENTS.md and lockfiles. A shared-file collision holds the build like any other and is marked shared file in the comment.

| Situation | Result |
|---|---|
| No collision, fewer than five open builder pull requests | Starts. The issue gets `in-progress` and loses `waiting`. |
| A file collides with pull request or job #N | Waits. The issue gets `waiting` and the comment line `Waiting on #N, same file`. |
| Five or more open builder pull requests | Waits. The comment line is `Waiting, this repo has 5 open pull requests`. |

A pull request that closes the issue being judged is that job's own earlier work, so it neither collides nor counts toward the cap. An issue lists no Files in scope only by mistake; it starts, with a warning in the run log.

Each issue gets one comment from the check, edited in place when the reasons change and marked Started once the build goes ahead.

Two jobs judged at the same moment could both see a clear path. After labeling itself `in-progress` the check pauses (`OVERLAP_SETTLE_SECONDS`, 10 by default) and looks again, and on that second look only an older issue can hold it. The newer job waits and the older one builds.

## Starting again

The caller also runs on `pull_request_target` closed. That run never checks out pull request code. `next` walks the open issues labeled `job` and `waiting`, oldest first, and dispatches the builder workflow for the first one that would start now. One dispatch per closed pull request. The dispatched run checks again before it builds.

## Installing the builder in another repo

1. Copy `.github/workflows/factory-chat-to-code-loop-builder-skills.yml`, keep its triggers and permissions, keep its `# factory-automation:` line only if Factory issued that id for the new repo, and change `uses:` to `ExpertPartners/expert-partners-skills/.github/workflows/factory-builder-reusable.yml@main`.
2. Make sure the Factory GitHub App is installed on the repo and the organization-level Actions secret `FACTORY_API_KEY` is available to it. A repository secret with the same name overrides the organization one.

The author allowlist (AllisonGaddy, expertpartners, expertpartners-ember) lives in the reusable workflow, so every repo gets the same rule.

## Tests

From the repository root:

```
python3 -m unittest discover -s tools/overlap-check/tests -v
```
