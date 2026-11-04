# overlap-check

Decides whether a Chat to Code build may start, before the Factory droid runs. Authority: Decision Log 2026-11-02, Factory runs everything at once (the only reason to hold a build is a real collision, and the held build names what it waits on), and No caps stop work (the five open pull request cap is removed, and only the overlap check holds a job).

| File | What it does |
|---|---|
| `overlap_check.py` | The check. `check` judges one Job issue and labels it. `owner` confirms ownership and selects an authenticated immutable head. `verify` rechecks it against GitHub and the local checkout before build secrets. `release` frees a job whose build ended without its pull request, or that was parked or done while it built. `next` restarts every waiting job that can start. Python standard library only. |
| `tests/test_overlap_check.py` | Unit tests for no overlap, ordinary overlap, shared-file overlap, many open pull requests not holding a job, closed, parked and done jobs holding nothing, a build that is still writing under every issue state, releasing a failed build, the restart and its claim, one writer per job (the #237 replay, events at the same moment on threads, distinct jobs in parallel), continuing an open pull request (with a temporary Git origin), a merged winner, a reopen after a merge beside a leftover pull request, a release racing a new admission, a build that failed before it wrote and its re-run, and the workflow wiring and its build-step commands. All GitHub calls go to an in-memory fake. |
| `../../.github/workflows/factory-builder-reusable.yml` | The reusable builder that runs the check, then the droid. |
| `../../.github/workflows/factory-chat-to-code-loop-builder-skills.yml` | This repo's caller, the one small file other repos copy. |

## When a build waits

The check reads the issue's Files in scope (a `## Files in scope` heading, a bare `Files in scope` line from the job template, or a bold `**Files in scope:**` label, one path per line, backticks and `(new)` allowed). The list ends at the next heading or section label, bare or bold, such as `**Acceptance checks**`. It compares them with:

- the changed files of every open builder pull request (opened by `factory-droid[bot]` or on a `job/` branch), and
- the Files in scope of every other job that is truly building: an open issue labeled `job` and `in-progress` that is neither parked nor done, or a closed, parked or done one whose build is still writing (see below).

### Jobs that hold nothing

A job holds files only while it is really being built. Three kinds of job hold no files, whatever other labels they carry, `in-progress` included, once no build is running for them:

- **Closed.** The issue is closed, so its work is finished or dropped.
- **Parked.** The issue carries `parked`. Only Allison's logged decision parks a job, and a parked job stays off Factory. It does not block anyone while it waits.
- **Done.** The issue carries `done`. The auto-merge gate adds it after the job's pull request merges, so the work is already on `main`.

Closing a job, parking it or marking it done does not stop a build that is already running for it, and that build can still push. So when the check starts a build, its comment on the issue records that build's run. A closed, parked or done job that still carries `in-progress` keeps its files while that build is still writing. When the build ends, `release` removes `in-progress` and the same run restarts waiting jobs, so the jobs that waited on it start only once it can no longer write. A job closed, parked or done during the check's pause, before its run is recorded, does not build.

### When a build has stopped writing

Only GitHub Actions can say that a build has stopped writing. The issue's state and labels cannot, because closing, parking or marking a job done cancels nothing. The check reads the recorded run and counts the build as stopped in three cases only:

- **The run is gone.** Reading it answers 404.
- **The run is completed.** A run's `status` becomes `completed` only once every one of its jobs has ended.
- **The run's `build` job is completed.** The check reads the run's jobs with `filter=latest`, so a re-run counts by its newest attempt. The run itself stays in progress while its `release` job runs, but `release` declares `needs: [gate, build]`, so it starts only after `build` has completed. That is why the release and the restart after it can free the files.

Any other answer means the build may still be writing, and the job keeps its files: the run or the build job is `queued`, `waiting`, `pending`, `requested` or `in_progress`, no `build` job is listed yet, or GitHub's answer cannot be read. An open job that is neither parked nor done keeps holding through `in-progress` until its release, as before.

A job that waits only on stopped jobs starts on the next restart, and marking a job `parked` or `done` starts that restart on its own. Removing `parked` or `done` from a waiting job starts the restart too, so an unparked job builds again as soon as its files are free. A closed, parked or done job never builds either: `check` leaves it as it is and does not start the droid, and a parked or done job that still carries `waiting` is never sent to the builder. Label names are read without regard to case, so `Parked` or `In-Progress` count the same as the lowercase names. An open builder pull request still holds its changed files in every case, even when its job is parked or done, because those changes are real and could collide.

Two paths collide when they are the same file, when one is a directory that holds the other (a path ending in `/`, or a slashed path with no extension such as `tools/auto-merge-gate`), when one is a glob that matches the other, or when a shared file is named without its directory (`plugin.json`) and the other path ends in that name. Shared files are plugin.json, marketplace.json, CHANGELOG.md, AGENTS.md and lockfiles. A shared-file collision holds the build like any other and is marked shared file in the comment. Notes in `.changeset/` are the exception the other way. Every job writes its own note file there, so a note collides only with the very same note, and two spellings of the folder itself (`.changeset/`, or a glob inside it) never hold each other. `.changeset/README.md` keeps the normal rules.

| Situation | Result |
|---|---|
| No collision, however many builder pull requests are open | Starts. The issue gets `in-progress` and loses `waiting`. |
| A file collides with pull request or job #N | Waits. The issue gets `waiting` and the comment line `Waiting on #N, same file`. |

There is no cap on open pull requests or builds per repo. A pull request that closes the issue being judged is that job's own earlier work, so it never collides. An issue lists no Files in scope only by mistake; it starts, with a warning in the run log.

Each issue gets one comment from the check, edited in place when the reasons change. It is marked Started, with the build's run id in a hidden line, once the build goes ahead. A gate that follows another run, below, adds its own receipt comment instead.

Two jobs judged at the same moment could both see a clear path. After labeling itself `in-progress` the check pauses (`OVERLAP_SETTLE_SECONDS`, 10 by default) and looks again, and on that second look only an older issue can hold it. The newer job waits and the older one builds.

## One job, one writer

However many events start the builder for the same issue (the job label, a `Job:` issue opening, a manual dispatch, a restart, a re-run), only one run builds it at a time, and the job stays on one branch and one pull request.

- **The lease.** The gate's comment on the issue names the run it admitted, in a hidden `factory-overlap-run` line. That run owns the job. The line stays through the release, so a later run can see from GitHub Actions whether the owner is still writing.
- **A second event follows the first.** Before it judges files, the gate looks for another run that already builds this job: the recorded run, or a run that has claimed the job and has not finished. When that run can still write (the same test as [When a build has stopped writing](#when-a-build-has-stopped-writing)), this run posts a receipt comment that names the run it follows, changes no label, and does not build.
- **Events at the same moment.** A gate whose first look is clear posts a claim comment before its pause. After the pause it yields to any older claim whose run can still write. Comment ids only grow, so of two gates for the same job the older claim wins however their reads and writes interleave. The loser's claim becomes its receipt. The winner records its run and removes its claim. Claims are per issue, so jobs on different issues never wait on each other.
- **The build checks again.** A "Re-run failed jobs" repeats the build without the gate. So the build job's first step (`owner`) fails unless the job is still open, not parked or done, not delivered, and its recorded run is this run. A re-run of the admitted run may build again. A re-run of a run whose admission a newer run has taken never writes, and its release changes nothing. The build job's own token gains only `actions: read`, `issues: read` and `pull-requests: read` for this. The access preflight and its clean-checkout checks are unchanged.
- **An authenticated open pull request is continued.** The oldest matching pull request must have its head in the exact caller repository and its current commit must be authenticated as Factory-produced, as described below. The build checks out its immutable commit, attaches the existing branch after verification, and tells the droid to update the same pull request. With more than one open, the others are named and left as they are. Nothing closes a pull request or deletes a branch.
- **A merged pull request wins.** When a builder pull request that closes the job has merged, the job is delivered. The gate says so on the issue and does not build, even when a redundant pull request is still open beside it. A build that finds the job delivered does not write, and its release drops `in-progress` and `waiting` instead of queueing it again. Only reopening the issue after that merge builds more, on top of main. After such a reopen, an open pull request is continued only when GitHub's compare shows its head already contains the merged commit. A pull request left open beside the merge whose head lacks it is named and left as it is, and the build starts from main. When the compare cannot be read, the job waits with that pull request's owner instead of building.

| Situation | Result |
|---|---|
| A second event while the job's recorded run can still write | Receipt `Run N did not build this job, because run M is already building it`. No label changes. |
| Two events at the same moment | The older claim builds. The other posts the receipt. |
| The job has an authenticated open builder pull request | Builds from its pinned commit and updates that branch and pull request. |
| An existing same-repository pull request lacks current Factory provenance | Technical wait with its current owner named; no new PR and no stale issue file hold. The open PR still holds its actual changed files. |
| A matching pull request comes from a fork | Never selected or used to keep the issue in-progress. |
| A builder pull request for the job merged | `Already delivered`. No build, no `in-progress`, no `waiting`. A merged fork pull request is not a delivery. |
| Reopened after the merge, with a pull request left open whose head lacks the merge | Builds from main. The leftover is named in the note and left as it is. |
| The build failed before the droid wrote | Back to `waiting` with its run recorded. Re-running that run builds again; any later restart or dispatch admits a new run. |
| Re-run of a run a newer admission replaced | The build step fails before checkout. Its release leaves the job alone. |

## When a build ends without its pull request

After every build the gate started, `release` runs, whatever the build's result. When another run has since been admitted for the job, or another run's gate is still deciding (a claim whose run can still write), nothing changes. The release rereads that lease immediately before every label or comment write and stops at the first write where it has moved. GitHub has no conditional label writes, so this relies on the gate's order: a gate claims, pauses `OVERLAP_SETTLE_SECONDS`, and only then records its run and sets its labels, so a release write that follows a clear reread lands before any new admission. When a builder pull request for the job merged, the job is delivered and loses `in-progress` and `waiting`. An authenticated open builder pull request keeps the issue in-progress. A same-repository PR whose provenance is unavailable returns the issue to a technical wait with its existing owner; a fork cannot keep it in-progress. Each open PR still holds its actual changed files. Otherwise the issue loses `in-progress`, so it stops holding other jobs. A build that failed, timed out or was cancelled also goes back to `waiting`, and its comment says so and keeps its run recorded. A build that succeeded without a pull request is not queued again, so a finished run never loops. A job that was closed, parked or done while it built always loses `in-progress` here, even when its pull request is open (the pull request still holds its own changed files), and it is not queued again. Whenever `release` removes `in-progress`, the release job then runs `next`, because a label change made with the workflow's own token starts no restart. That pass never sends the job just released, so a build that keeps failing does not restart itself in a loop. It starts again on the next restart from any other event.

## Continuation trust boundary

Branch prefixes, issue-closing text, PR authors and commit author emails identify candidate work but never authorize running it with build secrets. The check resolves the canonical `factory-droid[bot]` GitHub App identity and reads [GitHub repository activities](https://docs.github.com/en/rest/repos/repos#list-repository-activities) with the exact full head ref, descending order, and one result. It does not filter by actor or activity type and does not search older pages for a favorable record. The latest activity must be a push, force push or initial branch creation by that exact bot ID, with the PR's exact immutable SHA as `after`. The current Git ref must still match. A deletion, wrong ref, wrong actor, stale SHA, absent or malformed result, inaccessible endpoint or network error refuses continuation. Reading this endpoint requires only the existing Contents read permission.

The `owner` command emits the verified PR, branch and SHA. New jobs instead receive the explicitly resolved default-branch SHA, never a blank checkout ref inherited from a dispatch. The build checks out that SHA with credential persistence disabled, then calls the trusted `verify` command from outside the caller checkout before the ledger token, Factory API key or App write token is supplied. Verification reads ownership and producer evidence again and compares both GitHub's current head and the local checkout with the selected SHA. A changed or disappeared PR refuses the build. Only after verification does the workflow attach the existing local branch, preserving a clean checkout for the canonical access preflight.

Schema evidence: authenticated GitHub.com reads on November 4, 2026 returned `actor` and `activity_type` under both API versions `2022-11-28` and `2026-03-10`. The documentation's response example instead shows `pusher` and `push_type`. Regression tests preserve sanitized real Factory and later maintainer records. The check follows the observed authenticated endpoint and refuses missing producer fields; it does not guess aliases from the inconsistent example or search older records to bypass the latest push.

A human or Codex maintainer push is intentionally not presented as Factory provenance. That PR stays with its active owner, who can finish and merge it through the existing review process. Automatic Factory continuation requires its own authenticated producer evidence. No new identity, secret, permission or branch rule is introduced. A provenance wait affects only that job; independent jobs continue, and actual same-file PR collisions still wait.

## Starting again

The canonical caller also accepts an explicit `reopened` event for an allowlisted author's job. Reopening after a prior merge allows further work. The gate removes an obsolete `done` label only for this event, while preserving `parked`, closed issues and an existing live writer. Other installed caller copies need the same event subscription to receive reopened events; the reusable workflow cannot add triggers to a caller.

The caller also runs when a pull request closes (`pull_request_target`), when an issue closes, when an issue loses `in-progress`, and when an issue gains or loses `parked` or `done`. The pull request run never checks out pull request code. The gate, the release and the restart take the check from this repo's `main` only, so no caller or pull request can swap in its own copy. `next` walks the open issues labeled `job` and `waiting`, oldest first, and dispatches the builder workflow for every one that would start now. A job sent in that pass holds its files for the later ones, so two colliding jobs are never sent together. A waiting job that is still being built, because it carries `in-progress` or its recorded run can still write (a re-run), is not sent, and it holds its files like any job that builds. Before each dispatch `next` removes the job's `waiting` label. GitHub refuses a second removal, so when two runs race only one of them sends the job. The dispatched run checks again before it builds.

Label changes made with the workflow's own token start no workflow, so the check's own edits never trigger a restart.

## Installing the builder in another repo

1. Copy `.github/workflows/factory-chat-to-code-loop-builder-skills.yml`, keep its triggers and permissions, keep its `# factory-automation:` line only if Factory issued that id for the new repo, and change `uses:` to `ExpertPartners/expert-partners-skills/.github/workflows/factory-builder-reusable.yml@main`.
2. Make sure the Factory GitHub App is installed on the repo and the organization-level Actions secret `FACTORY_API_KEY` is available to it. A repository secret with the same name overrides the organization one.

The author allowlist (AllisonGaddy, expertpartners, expertpartners-ember, expertpartners-aura) lives in the reusable workflow, so every repo gets the same rule. The builder prompt there also tells the droid never to ask inside Factory, and the caller file repeats that line so every installed copy carries it.

## Tests

From the repository root:

```
python3 -m unittest discover -s tools/overlap-check/tests -v
```

The redispatch job needs `issues: write` for `next` to claim a waiting label, restore it after a failed dispatch, and record technical waits; its other permissions remain unchanged. This permission stays within the caller's existing issue-write grant. API errors identify the HTTP method and endpoint path, excluding request queries, headers and bodies, so a failed endpoint can be diagnosed without exposing credentials. An older run's generic 403 without an endpoint is not proof that any particular permission mismatch caused that run's failure.
