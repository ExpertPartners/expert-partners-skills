---
name: job-list-heartbeat
description: |
  Every Claude session checks the job list every 15 minutes, a CEO directive from Allison. Always on as doctrine for every Claude Code session and every Claude chat, in any project on any surface. Fires at the first reply of every session and at every scheduled check. In its first reply the session runs job_inbox under its own name and any old name, claims and acts on its jobs, then sets its own 15-minute check with what its surface supports, a /loop or ScheduleWakeup locally, send_later chained in cloud Claude Code, a recurring task at the shortest interval elsewhere, and keeps it running for the life of the session. Each check reads both names, acts on Start presses and Allison's replies, renews the lease on every claimed job and schedules the next check. A check with nothing new for Allison sends her nothing, otherwise one brief CEO update. A surface with no timer checks on every reply and says so once. It never asks Allison to wake it. Inherits operating-doctrine.
allowed-tools: []
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-11-03 (Decision Log 2026-11-02, CEO directive, every Claude
# session checks the job list every 15 minutes). A simple CEO directive skill,
# so it ships with no proving line.
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "check the job list every 15 minutes"
---

# Job List Heartbeat

One job. Every Claude session checks the Chat to Code job list in its first reply, then keeps checking it every 15 minutes on its own timer for as long as the session lives. No session ever needs Allison to wake it.

Source: the HQ Rulebook, Handoffs between AIs, and the Decision Log 2026-11-02 entries Every HQ conversation connects in its first reply, CEO directive, every Claude session checks the job list every 15 minutes, Every job check runs every 15 minutes, around the clock, and Claimed jobs return after one missed check. The Rulebook wins wherever this differs. This skill applies the Messages Between AIs section of operating-doctrine to the clock.

## Who it binds

Every Claude Code session and every Claude chat, in any project, on any surface, local or cloud, whether or not anyone gave it a job yet. The check runs every 15 minutes, all day and night, every day, whether Allison is at her desk or away.

## Trigger

This is doctrine, so it is always on. It fires at two moments.

1. The first reply of every session, before any other work.
2. Every scheduled check after that.

## The first reply

1. Run job_inbox under the session's own name, then under every old name it has carried. Read the live job tool schema before calling it. Never guess a tool's arguments.
2. Claim each job meant for this session with job_claim, so job_status shows who is doing it, and start the work.
3. Set the session's own 15-minute check with what its surface supports. If a check for this session already exists (a recurring task that started this session, or one set earlier), verify it and set no second one.
   - Claude Code on a local machine. A /loop or a ScheduleWakeup loop every 15 minutes.
   - Claude Code in the cloud. send_later, chained, so each check schedules the next one 15 minutes out.
   - A surface with scheduled tasks. One recurring task at the shortest interval the scheduler allows. A check that starts a fresh session runs hourly around the clock, the shortest it can run.
4. Verify the check is scheduled. Read it back from the surface's own schedule list or tool result, and say in the reply that it is set and when the next one runs. A check that was asked for but not read back is not set.

## Every check

1. Run job_inbox under the session's name and every old name.
2. Act on every Start press and every reply from Allison waiting there. Claim new work with job_claim and start it in the same check.
3. Renew the lease on every job this session has claimed and is still working, using the renew the live job tool offers. A claimed job goes back to the list after 20 minutes, one missed check, so a working session renews on every check and never lets the sweep take back work in progress.
4. If the timer is one-shot (send_later, ScheduleWakeup), schedule the next check and confirm it. A timer that already repeats (a /loop, a recurring scheduled task) is left as it is, so checks never stack up.

## Quiet checks

A CEO directive from Allison (Decision Log 2026-11-03, Quiet checks). A check that finds nothing relevant for her sends her nothing, so no reply text, no message, no text and no push. Doing the check is the job, and reporting that nothing changed is noise. When something relevant changed, like work finished, a decision she must make, something stuck or a result she would want, she gets one brief CEO update covering what moved, what it means, and the one thing that needs her if any. The Rulebook decides what counts as needing her. The check itself never stops.

## Renewing between checks

The lease is 20 minutes, and some surfaces check less often than that (an hourly scheduled task). So while a session is working a claimed job, it renews that job's lease in every reply, not only at the check, and before any step it expects to run longer than 15 minutes. A run started by an hourly task finishes or renews each job it claims before that run ends.

## A surface with no timer

When the surface truly cannot run a timer, research it first, the way research-before-guessing says. If no timer exists, the session runs the full check at the top of every reply instead, and says once, plainly, that this surface cannot run a timer, so it checks the job list on every reply. It says that one time, not on every reply.

## When the session ends

The check runs for the life of the session. When the session wraps, it releases the check it owns, the same as every monitor and scheduled wakeup, per session-steward section 7A, and reports background activity as NONE.

## Never

- Ask Allison to wake the session, nudge it, or press anything so it checks.
- Skip the first-reply check because the session was opened for something else.
- Wait on a question inside its own app. A question that truly needs Allison goes on the board, per the HQ Rulebook.
- Let a claimed job's lease lapse while the work continues.
- Say the check is set without reading it back.

## Test cases

1. A new Claude Code session opens. Pass when its first reply runs job_inbox under its name and sets a 15-minute check, verified as scheduled.
2. A job assigned to the session gets a Start press. Pass when the next check picks it up, within 15 minutes on a 15-minute surface and within the surface's shortest interval elsewhere.
3. A chat on a surface with no timer. Pass when it checks on every reply and says once that it cannot run a timer.
4. A session claims a job. Pass when each check and each working reply renews the lease so the sweep never returns it while work continues, on an hourly surface too.
5. A session started by a recurring task. Pass when it verifies that task and adds no second recurring check.
6. A check where nothing changed for Allison. Pass when the session sends her no message or reply text at all.
7. A check where a job she approved finished. Pass when she gets one brief CEO update and nothing else.
