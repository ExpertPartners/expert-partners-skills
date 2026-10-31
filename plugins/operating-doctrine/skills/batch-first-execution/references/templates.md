# Assignment templates

Use the smallest template that fits. Fill in the actual known fields before
delivery. Bracketed labels below are authoring placeholders, not instructions
to send incomplete work to Allison. When `code-block-routing` governs a Claude
Code paste, its one-block-per-response and step-one-only rule overrides the
multi-step presentation in sections A and B: deliver only M01 or prompt 1,
retain the plan in the checkpoint, and release the next block after verified
predecessor evidence. The staged session-wrap exception remains scoped there.

Follow the current HQ Rulebook section Handoffs between AIs. Each outgoing assignment and return is one complete copy box with sender, receiver, model and effort or speed. The receiver uses job_create or job_claim, preserves its existing job on continuation, and files job_finish with a summary and result link. Code jobs travel as GitHub issues labeled job.

## A. One-paste master assignment

```text
FROM: [Sending AI and conversation]
TO: [Receiving AI and conversation]
MISSION: [One bounded outcome]
WORKER/SURFACE: [Known intended execution surface]
EXISTING HOME / RETURN TO: [Preserve established names; omit if none]
EXECUTION SETTINGS
SURFACE: [Verified surface]
MODE: [Verified mode]
MODEL: [Verified model or explicitly retained approved selection]
EFFORT/SPEED: [Verified option or explicitly retained approved setting]

Execute this as one sequential assignment. Continue through the authorized
milestones without asking me to relay routine intermediate results. Inspect
your own outputs and adapt within the stated boundaries. Do not invent facts
that only later steps can discover.

FIRST
Read applicable current instructions and the relevant source material.
Check job_status for the existing owner, then use job_create or job_claim.
For code work, retain the GitHub issue labeled job.
Verify the intended account, repository/branch or worktree, relevant access,
and active ownership before a write. Reuse existing evidence where current.
Keep unrelated work untouched. Do not create new infrastructure or expand
permissions to make this assignment run.

AUTHORITY AND BOUNDARIES
Allowed: [Specific reads/writes and paths]
Protected: [Specific state that must not change]
Approval gates: [Specific actions requiring a decision]
Completion condition: [Observable evidence]
Working checkpoint: [Existing resolved artifact or appropriate scoped path]
Retry/work limit: [Proportionate actual limit]

MILESTONES - ONE AT A TIME
M01: [Goal]
Input: [Source]
Action: [Bounded action]
Deliverable: [Artifact/state]
Verification: [Actual runnable or observable check]
Depends on: [None or IDs with required outcomes]
On failure: [Bounded repair, then block specified dependents]
Human gate after this milestone: [None or exact decision]

[Repeat only for the useful number of milestones.]

EXECUTION RULES
Before each milestone, verify dependency evidence and current authorization.
A previous response ending is not success. Mark unmet prerequisites BLOCKED.
Do not run dependent work after failure. Continue only named independent work
that remains safe. Do not interpret queued follow-ups as approval.
After each milestone, update the checkpoint with status, evidence, current
revision and the next safe action. Re-read it after compaction or resumption.
Before retrying a write, verify whether it already landed.
If new information requires a decision beyond scope, finish other authorized
independent work, then return the one decision; do not guess permission.

FINAL CARRY-BACK
File job_finish with a summary and result link; verify it with job_status.
Give a plain-language outcome, verified milestone count, blocked/unverified
items, evidence links/paths, actual changes, and the one next human action.
Do not claim merge, deployment, activation, or live verification without proof.
```

## B. Numbered queue packet

Explain outside the blocks: "There are [N] prompts. Submit each separately in
order to the same worker using verified Queue behavior. Do not paste later
blocks into a different worker or use Steer as a substitute for Queue."

If an existing task is running, queue after it rather than interrupting it.
Only give app-specific keyboard instructions supported by current evidence.
Resolve the complete Worker envelope and execution settings before handing
Allison prompt 1. Repeat the compact settings only when a later prompt starts
a different Worker/run or genuinely changes them; retain the dependency guard
in every queued prompt.

### Prompt 1 of N - initialize and perform M01

Include the compact mission, allowed scope, complete milestone map, checkpoint,
stop conditions, budget, final return destination, and M01's specific work.
Include the same guard as every other prompt. Do not make prompt 1 an idle
acknowledgment when it can safely perform the first useful work.

### Every subsequent prompt

```text
FROM: [Sending AI and conversation]
TO: [Receiving AI and conversation]
MODEL: [Verified model for the receiving chat]
EFFORT/SPEED: [Verified setting for the receiving chat]
PROMPT [i] OF [N] - [Mission identifier] / [Milestone ID]

Treat this as the next ordered work item, not an instruction to interrupt.
Before acting, read the shared checkpoint and verify the required predecessor
outcomes. If any dependency or approval is missing, mark this item BLOCKED and
do not execute it. A queued message is not evidence of success or approval.

Mission: [Same bounded mission]
Checkpoint: [Same resolved artifact]
Preserved boundaries: [Compact critical constraints]
Required predecessors: [IDs and their exact required evidence]
Required approval: [None or evidence of actual approval]
This milestone: [Input, action, deliverable, verification]
On failure: [Bounded repair and affected downstream work]
Afterward: Update checkpoint and preserve the final return destination.
[For the final block: reconcile all milestones and return consolidated report.]
```

If multiple blocks arrive during one turn, retain them as ordered work items.
Never skip the guard, even when a later prompt says "continue" or "finish."
Use stable milestone IDs so duplicate submission can be detected safely.

## C. Decision-gated assignment

Do not draft a supposedly unconditional ten-step execution queue when step 3
requires Allison to choose an architecture. Group the known work:

```text
FROM: [Sending AI and conversation]
TO: [Receiving AI and conversation]
MODEL: [Verified model for the receiving chat]
EFFORT/SPEED: [Verified setting for the receiving chat]
Run discovery, comparison and a recommendation as one authorized batch.
Use job_create or job_claim, then job_finish with a summary and result link.
You may do: [Scope]. You may not do: [Unapproved implementation].
Return evidence, your recommended option, and the one decision required.
Do not execute implementation phases until that decision is explicitly made.
```

Preparing next-step drafts is allowed when labeled conditional and non-running.

## D. Minimal checkpoint

Use an existing record. Scale this down for small tasks.

```text
Mission / approved boundaries:
Executor / actual home / branch or revision:
Milestones: ID | state | dependency | evidence | next action
Current blockers / decisions required:
Partial writes checked for duplication:
Last verified state and timestamp:
Next safe action:
Return destination:
```

Working checkpoints are operational state, not new business canon. Use the
existing Chat to Code job for durable status, checked with job_status.

## E. Consolidated return

```text
FROM: [Sending AI and conversation]
TO: [Receiving AI and conversation]
MODEL: [Verified model for the receiving chat]
EFFORT/SPEED: [Verified setting for the receiving chat]
Job report: [Verified job_finish summary and result link]
Outcome: [One sentence]
Verified: [Count and names, against the stated scope]
Blocked / failed / skipped / unverified: [Exact distinctions]
Evidence: [Tests, read-backs, artifacts, commits or PRs as applicable]
Changes: [Actual changes; distinguish local, pushed, merged, deployed]
Usage: [Only measured usage or "not measured"]
Your next action: [One concrete decision/action, or "None"]
Resume from: [Checkpoint and next safe milestone, when unfinished]
```
