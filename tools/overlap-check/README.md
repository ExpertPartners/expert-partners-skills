# overlap-check

Decides whether a Chat to Code build may start, before the Factory droid runs. Authority: Decision Log 2026-11-02, Factory runs everything at once (the only reason to hold a build is a real collision, and the held build names what it waits on), and No caps stop work (the five open pull request cap is removed, and only the overlap check holds a job).

| File | What it does |
|---|---|
| `overlap_check.py` | The check. `check` judges one Job issue and labels it. `release` frees a job whose build ended without its pull request, or that was parked or done while it built. `next` restarts every waiting job that can start. Python standard library only. |
| `tests/test_overlap_check.py` | Unit tests for no overlap, ordinary overlap, shared-file overlap, many open pull requests not holding a job, closed, parked and done jobs holding nothing, a job parked while its build runs, releasing a failed build, the restart and its claim, and the workflow wiring. All GitHub calls are mocked. |
| `../../.github/workflows/factory-builder-reusable.yml` | The reusable builder that runs the check, then the droid. |
| `../../.github/workflows/factory-chat-to-code-loop-builder-skills.yml` | This repo's caller, the one small file other repos copy. |

## When a build waits

The check reads the issue's Files in scope (a `## Files in scope` heading, a bare `Files in scope` line from the job template, or a bold `**Files in scope:**` label, one path per line, backticks and `(new)` allowed). The list ends at the next heading or section label, bare or bold, such as `**Acceptance checks**`. It compares them with:

- the changed files of every open builder pull request (opened by `factory-droid[bot]` or on a `job/` branch), and
- the Files in scope of every other job that is truly building: an open issue labeled `job` and `in-progress` that is neither parked nor done, or that is parked or done while the build the check started for it is still running.

### Jobs that hold nothing

A job holds files only while it is really being built. Three kinds of job hold no files, whatever other labels they carry, `in-progress` included, once no build is running for them:

- **Closed.** The issue is closed, so its work is finished or dropped.
- **Parked.** The issue carries `parked`. Only Allison's logged decision parks a job, and a parked job stays off Factory. It does not block anyone while it waits.
- **Done.** The issue carries `done`. The auto-merge gate adds it after the job's pull request merges, so the work is already on `main`.

Parking a job, or marking it done, does not stop a build that is already running for it, and that build can still push. So when the check starts a build, its comment on the issue records that build's run. A parked or done job that still carries `in-progress` keeps its files while that run is going. When the build ends, `release` removes `in-progress` and the same run restarts waiting jobs, so the jobs that waited on it start only once it can no longer write. If the run cannot be read, the job keeps its files. If the run is gone or has ended, the job holds nothing. A job parked during the check's pause, before its run is recorded, does not build.

A job that waits only on stopped jobs starts on the next restart, and marking a job `parked` or `done` starts that restart on its own. Removing `parked` or `done` from a waiting job starts the restart too, so an unparked job builds again as soon as its files are free. A closed, parked or done job never builds either: `check` leaves it as it is and does not start the droid, and a parked or done job that still carries `waiting` is never sent to the builder. Label names are read without regard to case, so `Parked` or `In-Progress` count the same as the lowercase names. An open builder pull request still holds its changed files in every case, even when its job is parked or done, because those changes are real and could collide.

Two paths collide when they are the same file, when one is a directory that holds the other (a path ending in `/`, or a slashed path with no extension such as `tools/auto-merge-gate`), when one is a glob that matches the other, or when a shared file is named without its directory (`plugin.json`) and the other path ends in that name. Shared files are plugin.json, marketplace.json, CHANGELOG.md, AGENTS.md and lockfiles. A shared-file collision holds the build like any other and is marked shared file in the comment. Notes in `.changeset/` are the exception the other way. Every job writes its own note file there, so a note collides only with the very same note, and two spellings of the folder itself (`.changeset/`, or a glob inside it) never hold each other. `.changeset/README.md` keeps the normal rules.

| Situation | Result |
|---|---|
| No collision, however many builder pull requests are open | Starts. The issue gets `in-progress` and loses `waiting`. |
| A file collides with pull request or job #N | Waits. The issue gets `waiting` and the comment line `Waiting on #N, same file`. |

There is no cap on open pull requests or builds per repo. A pull request that closes the issue being judged is that job's own earlier work, so it never collides. An issue lists no Files in scope only by mistake; it starts, with a warning in the run log.

Each issue gets one comment from the check, edited in place when the reasons change. It is marked Started, with the build's run id in a hidden line, once the build goes ahead.

Two jobs judged at the same moment could both see a clear path. After labeling itself `in-progress` the check pauses (`OVERLAP_SETTLE_SECONDS`, 10 by default) and looks again, and on that second look only an older issue can hold it. The newer job waits and the older one builds.

## When a build ends without its pull request

After every build the gate started, `release` runs, whatever the build's result. When an open builder pull request closes the issue, that pull request holds the files and nothing changes. Otherwise the issue loses `in-progress`, so it stops holding other jobs. A build that failed, timed out or was cancelled also goes back to `waiting`, and its comment says so. A build that succeeded without a pull request is not queued again, so a finished run never loops. A job that was closed, parked or done while it built always loses `in-progress` here, even when its pull request is open (the pull request still holds its own changed files). It is not queued again, and the release job then runs `next`, because a label change made with the workflow's own token starts no restart.

## Starting again

The caller also runs when a pull request closes (`pull_request_target`), when an issue closes, when an issue loses `in-progress`, and when an issue gains or loses `parked` or `done`. The pull request run never checks out pull request code. The gate, the release and the restart take the check from this repo's `main` only, so no caller or pull request can swap in its own copy. `next` walks the open issues labeled `job` and `waiting`, oldest first, and dispatches the builder workflow for every one that would start now. A job sent in that pass holds its files for the later ones, so two colliding jobs are never sent together. Before each dispatch `next` removes the job's `waiting` label. GitHub refuses a second removal, so when two runs race only one of them sends the job. The dispatched run checks again before it builds.

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
