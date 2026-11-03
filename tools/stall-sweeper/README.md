# stall-sweeper

Finds every Chat to Code job that has stalled and pushes it back into Factory, every 10 minutes, on GitHub's own schedule. No AI or person has to watch the board. Authority: Decision Log 2026-11-03, Every code job on the job board goes to Factory now, none sit waiting, and Decision Log 2026-11-02, No caps stop work.

| File | What it does |
|---|---|
| `sweeper.py` | The sweep. Python standard library only. |
| `tests/test_sweeper.py` | Unit tests for all seven rules, the clean board, the safety limits, one dispatch per issue, the dry run and the workflow wiring. All GitHub calls are mocked. |
| `../../.github/workflows/factory-stall-sweeper-reusable.yml` | The reusable workflow that runs the sweep. |
| `../../.github/workflows/factory-stall-sweeper.yml` | This repo's caller, the one small file other repos copy. |

## When it runs

Every 10 minutes (`*/10 * * * *`), and by hand through workflow_dispatch. A manual run has a `dry_run` box: tick it and the sweeper prints what it would do and changes nothing. GitHub can start a scheduled run a few minutes late when it is busy.

## What it does

It reads every open issue whose title begins with `Job:` and whose author is on the builder's allowlist (AllisonGaddy, expertpartners, expertpartners-ember, expertpartners-aura). A builder dispatch skips the builder's own author check, so the sweeper never dispatches an issue anyone else opened. For each issue it applies the first rule that fits:

| Rule | When | What the sweeper does |
|---|---|---|
| 1 | No `job` label and no `parked` label. | Adds `job`, comments once why, dispatches the builder. |
| 2 | Carries `done` and the pull request that closes it is merged. | Comments the merge commit and closes the issue as completed. |
| 3 | Carries `waiting`, and every issue or pull request the overlap check says it waits on is closed, parked or done. | Removes `waiting` and dispatches the builder. |
| 4 | Carries `job`, with no `in-progress`, no `waiting`, no open pull request and no builder run in the last 30 minutes. | Dispatches the builder. |
| 5 | Carries `in-progress`, with no builder run in progress and no open pull request for 45 minutes. | Removes `in-progress`, then dispatches the builder. |
| 6 | Its `factory-droid[bot]` pull request is open, not a draft, and Codex has not reviewed the current head 30 minutes after it was pushed. | Comments `@codex review`, once per head. |
| 7 | Its pull request is refused by the auto-merge gate on the current head for unresolved Codex findings or a failing check, and no builder run for it started in the last 30 minutes. | Comments on the issue what to fix (the gate's reasons and each unresolved Codex thread), then dispatches the builder. |

Rule 7 keeps sending the builder back round after round. It stops only when a Codex finding comes back after it was fixed: the same file and finding title on a new review thread, after the sweeper already asked for the old thread to be fixed. Then it adds `needs-allison` and comments one line starting `Recommend:`, and does not restart that job again. A job marked `needs-allison` is never restarted by rules 3, 4, 5 or 7.

The gate's waiting reasons are not stalls: a check still running, a Codex review not done yet, or GitHub still computing whether the pull request can merge. Rule 7 ignores them.

Every action is one plain line in the run summary, followed by a final count. A clean board gets no writes and the summary says `No stalled jobs. 0 actions taken.`

## How it knows a builder run belongs to a job

The sweeper reads the builder workflow's runs from the last three hours. A run started by an issue event carries the issue title. A run started by a dispatch carries no issue, so the sweeper reads the `OVERLAP_ISSUE` line from that run's finished `gate` job log. Logs are read only when a rule needs them.

A dispatched run whose gate has not finished yet cannot name its job. While one is queued or in progress, the sweeper dispatches nothing at all and says so in the log, so it can never send a second build for the same job. The next sweep, 10 minutes later, picks up where this one stopped.

An issue-event run whose gate was skipped (an issue closing, or losing `in-progress`, only restarts waiting jobs) does not count as a build of that issue.

## Safety

- It never merges, never pushes code, and never changes repository settings, rulesets or access. The job never gets `contents: write`, and every write goes through an allowlist in `Sweeper.write`: comment on an issue or pull request, add `job`, `waiting` or `needs-allison`, remove `in-progress` or `waiting`, close an issue as completed, and dispatch the builder with an issue number. Anything else raises before it reaches GitHub.
- It never touches a parked job or that job's pull request, and refuses any write to one.
- It refuses any repository named ember: the workflow skips it and the script exits before its first call.
- It never dispatches the same issue twice in one run, and never dispatches an issue with a builder run queued or in progress. Rule 3 claims a waiting job by removing its `waiting` label first, the same claim the overlap check's restart uses, so when both race only one sends it.
- The script is checked out from this repo's `main` only, so no caller or pull request can swap in its own copy. It uses the workflow's own token and no secret.
- Labels changed with the workflow token start no workflow, which is why the sweeper dispatches the builder itself.

## Limits

- The workflow token allows 1,000 API calls an hour per repository, shared with the repo's other workflows. A sweep reads the issues, pull requests and recent builder runs, then only what a rule needs.
- Codex may ignore an `@codex review` comment from `github-actions[bot]`. If it does, rule 6 leaves one comment per head and nothing more.
- A Codex finding reworded on its way back is not recognized as the same finding, so rule 7 sends the builder back once more instead of stopping.

## Installing in another repo

1. Install the builder first (`tools/overlap-check/README.md`, Installing the builder in another repo).
2. Copy `.github/workflows/factory-stall-sweeper.yml`, keep its triggers and permissions, set `builder_workflow` to the file name of that repo's builder caller, and change `uses:` to `ExpertPartners/expert-partners-skills/.github/workflows/factory-stall-sweeper-reusable.yml@main`.
3. Run it once by hand with `dry_run` ticked and read the summary.

## Tests

From the repository root:

```
python3 -m unittest discover -s tools/stall-sweeper/tests -v
```
