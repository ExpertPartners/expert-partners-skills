<!-- Work is dispatched through the Factory connection. Link an issue only as optional context. -->

## Description

<!-- What this pull request changes and why, in plain words. -->

## Linked assignment and context

- Factory assignment or Workstream:
- Mission and goal:
- Decisions relied on (Decision Log date and title):

<!-- Name company documents by title only. Keep private Brain links and document IDs out of this public repository. -->

## Files and scope

<!-- List every file this pull request changes, marked (new) when it creates the file. The list must match the files in scope for the assignment. Paste the real output of the command below. -->

```text
$ git diff --name-only origin/main...HEAD
```

- Left alone on purpose:

## Testing done

<!-- One entry per acceptance check in the assignment, in the same order. Paste the exact command you ran and its real output. Mark PASS only when the pasted output shows it. Mark FAIL when a check failed or was not run, and say why. -->

1. Acceptance check:
   - Result: PASS or FAIL
   - Command and output:

     ```text
     $ the command you ran
     its real output
     ```

- Changed-file gates:

  ```text
  $ bash tools/validate-job.sh
  its real output
  ```

## Dependencies and overlap

- Depends on (pull requests, issues or setup that must land first):
- Overlaps with (open pull requests or Factory sessions that touch the same files):
- Overlap check result:

## Risks and rollback

- Risks:
- Rollback (how to undo this change, and anything that would not revert cleanly):

<!-- Keep secret values, tokens and credentials out of this pull request and out of pasted output. -->
