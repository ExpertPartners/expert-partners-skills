---
name: session-steward
description: "Continuity and lifecycle steward for Claude Code sessions. Identifies workers from stable session IDs, repository/worktree/branch, durable lane state, and transcript evidence; flags unregistered workers and proven scope collisions; relays context by messaging; has a finished worker release what it owns; and surfaces archive candidates behind Allison's confirmation."
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

v1.3 (ruled by Allison 2026-09-01, the founder-load worker-lifecycle amendment, ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md, source aura issue #200, delivered 2026-09-03): the worker's terminal transition becomes a real thing it performs, not a state it drifts into. Two additions. New section 7A: a worker with no remaining owned action, whose accepted handoff or merge is finished, RELEASES what it owns before any SAFE TO ARCHIVE, meaning its monitors, its scheduled wakeups and check-ins, its PR and CI subscriptions, and its background agents and tasks. Section 7 amended: the archive motion and the lane-ledger flip are ONE lifecycle close, so a worker that has actually been archived stops advertising itself as an active wait, reconciled on evidence at the moment of the close rather than by a later human cleanup or a sweeper. Archive authority is unchanged, Allison's product confirmation still gates every archive and the home conversation still owns the flip. The live failures that forced it, 2026-09-01 to 2026-09-03: the Final Reconciliation worker stayed alive after its substantive work was complete because it kept re-arming hourly check-ins and PR subscriptions while waiting on a merge NORTH had already made, producing ongoing noise Allison had to interpret; and lanes.md still read waiting-on-carry-back for two finished workers, one of them after Allison had physically archived it. This adds no registry, no dashboard, no daemon, and no ledger column.

v1.2 (ruled by Allison 2026-08-30, ruling of record aura decisions/0082-registrar-model-amendment-to-decision-0074.md, implementing decision 0080 Section 28): the enforcement target moves with the rule it enforces. Concurrency itself is no longer the violation. A violation is an unregistered worker or a worker whose exact execution scope collides with another, proven from evidence. Bridge until cutover, decision 0082 and decision 0080 Section 24: the registrar and the table registry do not exist yet, so until Allison rules the one cutover the installed one-active-worker practice continues to bind and the Steward keeps checking it, as pre-cutover discipline rather than target-state law.

This is a capability, not an agent. No new dashboard, database, registry, service, or system of record. The lane ledger (aura docs/estate/lanes.md) stays the only durable work state, unchanged in schema. The Steward reads and writes through the proven native ccd_session_mgmt tools plus the existing ledger path, and nothing else.

## 1. Session identification

Identify workers from stable native session ID, durable lane/dispatch state, repository, worktree/branch, transcript evidence, model and creation time as needed.

## 3. Identify before you classify

Identification uses, in order of strength: durable lane state (the ledger row), dispatch evidence (the block that spawned it and its CLAUDE HOME line), transcript evidence (`list_events`, `search_session_transcripts`), and session metadata (`get_session` for worktree, branch, model, creation time). Stable identity is the `local_<uuid>` sessionId, recorded in the ledger row's second cell, never in a new column.

Honest classifications, from evidence:

- Owned worker. Durable lane or dispatch evidence identifies its owner and return destination.
- Orphan. Real work, no recoverable owning table from any evidence. Report it as an orphan with what the transcript shows it did; never invent a home (ledger Rule 5).
- Mixed-purpose. The transcript shows genuinely different jobs sharing one session. Say mixed, plainly. Do not force a clean genealogy that never existed, and do not split history retroactively.
- Side-fix. Work discovered inside another mission. Distinguish the discovered-from context from the operational home; a worker can have one discovery source and a different operational branch or home, and a shared repo, branch family, issue, PR, or topic is NEVER by itself proof of shared table ownership.

## 4. Worker registration and scope collision (enforcement, retargeted v1.2)

Retargeted 2026-08-30 by decision 0082. Concurrency itself is not a violation. The two violations the Steward flags are an unregistered worker with no admitted durable ownership/scope record, and a proven exact execution-scope collision.

When checking: inventory active workers (`list_sessions` plus the ledger's Active lanes), establish each one's owning table and its exact execution scope from evidence per section 3, and only flag a violation when the missing registration or the exact scope conflict is PROVABLE. Suspected-but-unproven cases are reported separately as suspicions, never flagged as violations and never cleaned up on suspicion. Two workers on one table with genuinely disjoint exact scopes are not a violation and are not reported as one.

The fix for a proven violation is routing, not deletion: register an unregistered worker to the durable owner and scope the evidence supports, or report it as an orphan when no owner is recoverable. A colliding job moves to a non-conflicting worktree/scope or waits for the scope to release through an authorized terminal transition. Stale never equals dead.

Bridge until cutover, decision 0082 and decision 0080 Section 24: no registrar and no table registry exist yet, so until Allison rules the one cutover the Steward also keeps enforcing the installed one-active-worker practice exactly as v1.1 did, reporting a proven two-concurrent-independent-workers-on-one-table case as a pre-cutover violation. When the cutover lands, that check retires and scope admission stands alone.

## 5. Side-fix handling

When a worker discovers unrelated legitimate work: never silently absorb it and never silently spawn an untracked worker. Decide whether it blocks the current mission. Non-blocking work is preserved through the existing waiting or staged-kickoff mechanism. Genuinely required concurrent work gets its own admitted, non-conflicting scope and durable return path.

## 6. Messaging

`send_message` reaches attended sessions; unattended sessions (scheduled-task runs, remote-dispatched sessions) refuse cleanly. Handle a refusal once, record it, and stop. No retry loops. Use messaging to hand off context or relay findings, never to orchestrate background work.

## 7A. Terminal transition: a finished worker releases what it owns (v1.3)

Ruled by Allison 2026-09-01, ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md. The failure this kills: the Final Reconciliation worker stayed alive after its substantive work was complete because it kept re-arming hourly check-ins and PR subscriptions while waiting on a merge that had in fact already happened. **Once a worker has no remaining owned action and its accepted handoff or merge is finished, it stops producing signal.** Zombie-worker noise Allison has to interpret is the failure, not diligence.

**When the transition fires.** The worker holds no action it owns, and its handoff has been accepted or its merge has landed. Waiting on something it does not own is not the trigger, that is a genuine wait and it belongs in the ledger's waiting-on column with a named condition and a stale date. The distinction is ownership, never impatience.

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

The Steward surfaces archive candidates with evidence (mission achieved, verdict earned, ledger row current), supporting decision 0070's loop: the dispatching Control Tower owns moving a finished worker through canonical SESSION WRAP, then gives Allison a plain archive-or-keep-open instruction on the earned verdict. `archive_session` always prompts Allison for product confirmation and is called only after she has explicitly agreed to archive that specific session, never speculatively. The Steward never silently archives around the wrap loop, and home still flips the ledger row to `archived` as one motion with the call.

**Durable liveness: archive and ledger flip are ONE lifecycle close (v1.3).** Ruled by Allison 2026-09-03, ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md, on live evidence from `docs/estate/lanes.md`. The failure this kills: a completed worker stayed machine-visible as `waiting-on-carry-back` after its mission finished, in one case after Allison had already physically archived the session, so the canonical state was still advertising as active something that was actually dead. **When the archive motion occurs, the row is reconciled in that same close, never left for a later human cleanup.**

Three things this does and does not mean.

- **The flip belongs to the close, not to a follow-up.** Whoever performs or confirms the archive completes the row in the same motion. A carry-back that hands home an archive recommendation states plainly that the row still reads its pre-archive status and will be flipped with the click, so nothing is silently owed.
- **A stale row found later is reconciled on evidence, at the next touch.** When the Steward is already working a lane and finds a row advertising an active wait for a worker whose completion or archive is PROVEN, it reconciles that row through the guarded path as part of that work. Proven means live archive state, the home conversation's explicit confirmation, or the row's own recorded completion, and ledger Rule 5 still governs: an unproven row is left exactly as it is and reported as a suspicion, never cleaned on a hunch. Reconcile the lanes actually in hand and never sweep unrelated ones.
- **No new machinery, and no new authority.** This is not a daemon, a reconciler, a sweeper, or a scheduled job, and none of those is built or wanted. Archive authority is unchanged: Allison's product confirmation gates every archive, home owns the `archived` write, and a worker still never writes `archived` into its own row. Writes go through the shared-canonical-file-writes directive, with the estate-brain `update_lane_row` tool as the preferred guarded path. The native Auto-archive-on-PR-close preference in Claude Desktop Settings is Allison's optional toggle, mentioned when relevant, never flipped for her.

## 8. Cloud workers (the blind spot, and the hard requirement)

Cloud-dispatched Code sessions do not appear in local Desktop `list_sessions`, and unattended sessions can refuse messages. Therefore any mechanism creating a cloud worker registers, at creation time, the worker's owning table and available stable identifier (cloud session id, and local sessionId if any) in the lane ledger row, in existing cells, whenever technically available. Never assume the Steward can discover an unregistered cloud worker later. A cloud dispatch that skips its row is malformed the same way a spawning block without a WORKTREE line is.

## 9. Ledger writes (minimum, existing schema only)

The Steward writes only the minimum existing lane-state updates: its own row at registration and carry-back, stable session ID, actual repository/worktree/branch, scope, status, and return state in existing cells. Never a new column, lineage token schema, rewrite of Completed rows, or rewrite of historical resolved state. Amended 2026-08-30 (decision 0082, narrow registry retirement): the machine-structured table registry and structured worker lifecycle state that decision 0080 requires are authorized outside this skill and are built by their own workstream, lanes.md remains worker and lane operational state until implementation evidence earns a migration, all current parser guarantees hold until the coordinated revision cutover of decision 0080 Section 17, and this skill still creates no registry, column, database, dashboard, or competing source of truth. All writes obey the shared-canonical-file-writes directive; the estate-brain `update_lane_row` tool is the preferred guarded path.

## Rules

- Classify from evidence first, always.
- Never archive without Allison's product-level confirmation; never propose PRs or fixtures under review as cleanup targets.
- A finished worker releases every monitor, check-in, subscription, scheduled wakeup, and background agent it owns BEFORE any archive verdict, and reports background activity as NONE with that verdict (section 7A). Re-arming a check-in on work the worker no longer owns is the bug, and an item it cannot stop makes the verdict NOT safe rather than passing silently.
- Never stop a monitor, task, or job the worker does not own. Estate rails and other lanes' work are somebody else's; when ownership is unclear, leave it running and say so.
- The archive motion and the ledger flip are one lifecycle close (section 7). A stale row is reconciled only on proven evidence, only for lanes actually in hand, and never by a sweep or a daemon.
- Never infer table ownership from a shared PR, repo, branch, group, or topic alone.
- One refusal handling per unattended target, no retry loops.
- No new registries, agents, dashboards, databases, or ledger columns, ever, in this skill's name. The table registry and worker lifecycle state authorized by decisions 0080 and 0082 are another workstream's build, never this skill's, and their existence is not a licence for anything else here.
