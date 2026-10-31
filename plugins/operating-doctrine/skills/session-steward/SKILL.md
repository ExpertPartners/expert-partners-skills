---
name: session-steward
description: "Continuity and lifecycle steward for code sessions. Identifies workers from stable session IDs, repository/worktree/branch, job state and transcript evidence; flags unclaimed work and proven scope collisions; checks job_inbox each pass and job_status for ownership; has finished workers release what they own; and reports evidence gaps through job_finish with a summary and result link. Archive consent follows the live HQ Rulebook."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
defers-to:
  - code-block-routing
  - pin
brand-scope: null
subtitle: "Claude Code takes care of Claude Code"
---

# Session Steward

<!-- RULED-BY: aura/decisions/0107-retire-routing-naming-ceremony.md date:2026-10-12 superseded naming text removed -->

Ruled by Allison 2026-08-26. The problem this kills: Allison hunting for mystery Code sessions and remembering which worker belongs to which work. Claude Code takes care of Claude Code.

## Historical amendments, not current instructions

v1.6 (2026-10-24, Decision Log 2026-10-24, Archiving is gated on the paper trail, and an orphan sweep catches what slips, Allison's words, love this whole thing, yes, let's go): every Steward pass runs the orphan sweep, new section 10, and the archive pass in section 7 now archives a session only when its report row and Done pointer exist. The sweep is written for both stewards, Claude Code, Session Steward and Codex, Session Steward. Found Oct 24 when a session opened and closed pull request 92 and archived with no report row, and another vanished with its row unread. Adds to v1.5.

v1.5 (2026-10-24, Decision Log 2026-10-24, Finished code sessions wrap and archive themselves, Allison's words, that's a big one, let's make that happen for sure): a finished code session wraps and archives itself without waiting for Allison to say wrap, silently, and Codex can archive its own sessions too, confirmed by Codex, Session Steward on 2026-10-24. The Steward's pass is the sweep for sessions that cannot close themselves, run by Claude Code, Session Steward for Claude Code and Codex, Session Steward for Codex. Section 7 and the Rules are amended to match. Replaces the wait for Allison's wrap in Decision Log 2026-10-23 and 2026-10-21.

v1.4 (2026-10-22, HQ Rulebook Session lifecycle section and Decision Log 2026-10-22, Code sessions wrap and archive themselves, never ask Allison, confirmed by Allison in this change's own session; disclosure of record intake/2026-10-22-disclosure-rulebook-sync-formatting-tabs-session-wrap.md): finished code sessions archive themselves where the app allows, and the Steward lists the ones that end on `WRAP, safe to archive` for one archive pass. Section 7 and the Rules are amended to match, and this supersedes the earlier rule that every archive waits on Allison's confirmation.

v1.3 (ruled by Allison 2026-09-01, the founder-load worker-lifecycle amendment, ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md, source aura issue #200, delivered 2026-09-03): the worker's terminal transition becomes a real thing it performs, not a state it drifts into. Two additions. New section 7A: a worker with no remaining owned action, whose accepted handoff or merge is finished, RELEASES what it owns before any SAFE TO ARCHIVE, meaning its monitors, its scheduled wakeups and check-ins, its PR and CI subscriptions, and its background agents and tasks. Section 7 amended: the archive motion and the lane-ledger flip are ONE lifecycle close, so a worker that has actually been archived stops advertising itself as an active wait, reconciled on evidence at the moment of the close rather than by a later human cleanup or a sweeper. Archive authority is unchanged, Allison's product confirmation still gates every archive and the home conversation still owns the flip. The live failures that forced it, 2026-09-01 to 2026-09-03: the Final Reconciliation worker stayed alive after its substantive work was complete because it kept re-arming hourly check-ins and PR subscriptions while waiting on a merge NORTH had already made, producing ongoing noise Allison had to interpret; and lanes.md still read waiting-on-carry-back for two finished workers, one of them after Allison had physically archived it. This adds no registry, no dashboard, no daemon, and no ledger column.

v1.2 (ruled by Allison 2026-08-30, ruling of record aura decisions/0082-registrar-model-amendment-to-decision-0074.md, implementing decision 0080 Section 28): the enforcement target moves with the rule it enforces. Concurrency itself is no longer the violation. A violation is an unregistered worker or a worker whose exact execution scope collides with another, proven from evidence. Bridge until cutover, decision 0082 and decision 0080 Section 24: the registrar and the table registry do not exist yet, so until Allison rules the one cutover the installed one-active-worker practice continues to bind and the Steward keeps checking it, as pre-cutover discipline rather than target-state law.

## Current workflow

This is a capability, not an agent. No new dashboard, database, registry, service, or system of record. The Chat to Code job list is the work record. Read the current HQ Rulebook section Handoffs between AIs before routing work. Use native session tools only for session evidence, job_inbox for incoming assignments, and job_status for ownership and status. Do not infer job-tool signatures; inspect the available schema.

## 1. Session identification

Identify workers from stable native session ID, durable lane/dispatch state, repository, worktree/branch, transcript evidence, model and creation time as needed.

## 3. Identify before you classify

Identification uses, in order of strength: durable job state from job_status, dispatch evidence (the block that spawned it and its CLAUDE HOME line), transcript evidence (`list_events`, `search_session_transcripts`), and session metadata (`get_session` for worktree, branch, model, creation time). Stable identity is the `local_<uuid>` sessionId, recorded with the existing job, never in a new tracker.

Honest classifications, from evidence:

- Owned worker. Durable lane or dispatch evidence identifies its owner and return destination.
- Orphan. Real work, no recoverable owning table from any evidence. Report it as an orphan with what the transcript shows it did; never invent a home (Rule 5).
- Mixed-purpose. The transcript shows genuinely different jobs sharing one session. Say mixed, plainly. Do not force a clean genealogy that never existed, and do not split history retroactively.
- Side-fix. Work discovered inside another mission. Distinguish the discovered-from context from the operational home; a worker can have one discovery source and a different operational branch or home, and a shared repo, branch family, issue, PR, or topic is NEVER by itself proof of shared table ownership.

## 4. Worker registration and scope collision (enforcement, retargeted v1.2)

Retargeted 2026-08-30 by decision 0082. Concurrency itself is not a violation. The two violations the Steward flags are an unregistered worker with no admitted durable ownership/scope record, and a proven exact execution-scope collision.

When checking: inventory active workers (`list_sessions` plus running work from job_status), establish each one's owning table and its exact execution scope from evidence per section 3, and only flag a violation when the missing registration or the exact scope conflict is PROVABLE. Suspected-but-unproven cases are reported separately as suspicions, never flagged as violations and never cleaned up on suspicion. Two workers on one table with genuinely disjoint exact scopes are not a violation and are not reported as one.

The fix for a proven violation is routing, not deletion: register an unregistered worker to the durable owner and scope the evidence supports, or report it as an orphan when no owner is recoverable. A colliding job moves to a non-conflicting worktree/scope or waits for the scope to release through an authorized terminal transition. Stale never equals dead.

Bridge until cutover, decision 0082 and decision 0080 Section 24: no registrar and no table registry exist yet, so until Allison rules the one cutover the Steward also keeps enforcing the installed one-active-worker practice exactly as v1.1 did, reporting a proven two-concurrent-independent-workers-on-one-table case as a pre-cutover violation. When the cutover lands, that check retires and scope admission stands alone.

## 5. Side-fix handling

When a worker discovers unrelated legitimate work: never silently absorb it and never silently spawn an untracked worker. Decide whether it blocks the current mission. Non-blocking work is preserved through the existing waiting or staged-kickoff mechanism. Genuinely required concurrent work gets its own admitted, non-conflicting scope and durable return path.

## 6. Passing context

Follow the current HQ Rulebook section Handoffs between AIs. Give Allison one complete message for the receiving chat, with its sender, receiver, model and effort or speed. Do not use a separate message ledger or native session messaging as a second dispatch path. The receiver uses job_create or job_claim for the existing assignment and job_finish with a summary and result link when finished.

## 7A. Terminal transition: a finished worker releases what it owns (v1.3)

Ruled by Allison 2026-09-01, ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md. The failure this kills: the Final Reconciliation worker stayed alive after its substantive work was complete because it kept re-arming hourly check-ins and PR subscriptions while waiting on a merge that had in fact already happened. **Once a worker has no remaining owned action and its accepted handoff or merge is finished, it stops producing signal.** Zombie-worker noise Allison has to interpret is the failure, not diligence.

**When the transition fires.** The worker holds no action it owns, and its handoff has been accepted or its merge has landed. Waiting on something it does not own is not the trigger, that is a genuine wait and it belongs in the existing Chat to Code job with a named condition and a stale date. The distinction is ownership, never impatience.

**What it releases, all of it, before any verdict line.** Nothing here is optional and nothing is left for Allison to notice later.

- Its own monitors and watchers, stopped, including any live-update or file watch it opened.
- Its scheduled wakeups and recurring loops, cancelled. A self-paced loop stops rather than scheduling one more tick, and a cron or scheduled task the worker created for its own use is deleted, never left firing into an archived session.
- Its hourly or periodic check-ins, ended. A check-in exists to report change on work the worker owns; with no owned work there is nothing to report, so re-arming one is the bug.
- Its PR, CI, and review subscriptions, closed, including watches on a PR that has already merged or closed.
- Its background agents and background tasks, stopped, each one confirmed stopped rather than assumed finished.

**How it is proven, not asserted.** The worker enumerates what it actually started in this session, releases each item, and then reports background activity as NONE in the same turn as its verdict. An item it cannot stop is named plainly, with what it is and why, and that is a `NOT safe to archive` (or `RECOMMEND HOLD OPEN`) rather than a silent pass. Guessing that nothing is running is not evidence.

**What it never touches.** Anything owned by another session, by the estate's standing rails, or by Allison. Estate monitors, the board snapshot publisher, the CI watcher, scheduled tasks another lane created, and launchd or cron jobs that predate this worker are all somebody else's, and a worker that stops one of those has caused an outage, not performed a terminal transition. When ownership is genuinely unclear, leave it running and say so, naming the item.

**Then, and only then**, the worker's SAFE TO ARCHIVE evidence is complete (code-block-routing, The Session Gives The Archive Verdict, fourth evidence item).

## 7. Archive candidacy and the confirmation gate

Follow the current HQ Rulebook section Session lifecycle for archive consent and session-wrap for the remaining closeout duties. A worker reports through job_finish, including its summary and result link, verified with job_status. Never archive speculatively or while the worker still owes work, has uncommitted or unpushed work of its own, or cannot verify its report. Other workers' changes are not its work.

Use the existing native session evidence to list finished sessions awaiting Allison's archive instruction and ready, consented sessions whose native archive operation failed. A report saved only in chat does not clear readiness. Keep a blocked worker's reporting obligation with that worker; the steward reports the gap instead of inventing a completed report for it.

The job list must not advertise finished work as running. Reconcile only the job actually in hand and only from proven completion evidence. Never rewrite unrelated or historical work. Do not create a separate spreadsheet archive-status record or change Claude settings.

## 8. Cloud workers

Cloud-dispatched code sessions may not appear in local Desktop lists. The receiving AI records its actual repository/worktree/branch, return destination and available stable session identifier in its existing Chat to Code job. A milestone or continuation retains that job identity rather than creating a duplicate. A missing worker identifier is reported as unknown, never invented.

## 9. Job reporting

The steward uses job_create or job_claim for its own assigned pass, never another worker's job. Its job_finish summary names scope, status, evidence, result link and unresolved ownership or reporting gaps. Use job_status to verify the saved result. Preserve existing completed jobs and do not create a competing tracker. Code assignments travel as GitHub issues labeled job.

## 10. Inbox and evidence check, every pass

1. Check job_inbox for the steward's assigned work. Claim only work within its assignment and authority; check job_status to avoid duplicate owners.
2. Compare relevant open jobs from job_status with the native session lists, archived included. Use stable worker IDs and repository/worktree/branch evidence. For a missing worker, search its native transcript or thread evidence and state what was searched. A standing room is not a missing code session, and a worker still open is not an orphan merely because time passed.
3. Check relevant pull requests and default-branch commits since the last pass against job summaries and result links, not message receipts. List work with no verified job report, with repository, number or hash, date and the evidence checked. Use the previous pass's verified result as the watermark; when unavailable, check seven days and say so.
4. Put both evidence lists in this pass's job_finish summary with a result link. A clean pass records that result in the same job, not a separate message. Route any required return to the existing HQ owner under the Rulebook's Handoffs between AIs section.

A missing job-list, native-session or GitHub read is unverified for that source, never clean. The check never closes another worker's job, restarts a session or archives anything merely because it appears on a list. HQ resolves each reported gap from evidence or returns it to its owner. No new schedule, daemon or registry is created.

## Rules

- Every pass checks job_inbox and job_status (section 10), and files its own verified job_finish summary and result link.
- Classify from evidence first, always.
- Archive only finished sessions with evidence and the consent required by the current HQ Rulebook (section 7). Never propose PRs or fixtures under review as cleanup targets.
- A finished worker releases every monitor, check-in, subscription, scheduled wakeup, and background agent it owns BEFORE any archive verdict, and reports background activity as NONE with that verdict (section 7A). Re-arming a check-in on work the worker no longer owns is the bug, and an item it cannot stop makes the verdict NOT safe rather than passing silently.
- Never stop a monitor, task, or job the worker does not own. Estate rails and other lanes' work are somebody else's; when ownership is unclear, leave it running and say so.
- Preserve truthful job state through job_finish and job_status (section 7). Reconcile only work actually in hand and only on proven evidence.
- Never infer table ownership from a shared PR, repo, branch, group, or topic alone.
- An unavailable operation is a concrete blocker, never a retry loop or an invented success.
- No new registries, agents, dashboards, databases, or spreadsheet columns, ever, in this skill's name. The table registry and worker lifecycle state authorized by decisions 0080 and 0082 are another workstream's build, never this skill's, and their existence is not a licence for anything else here.
