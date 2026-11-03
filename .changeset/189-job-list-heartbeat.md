---
operating-doctrine: minor
---

Added the job-list-heartbeat skill, a CEO directive from Allison (Decision Log 2026-11-02, every Claude session checks the job list every 15 minutes). Every Claude Code session and every Claude chat, in any project on any surface, runs job_inbox under its own name and any old name in its first reply, claims and acts on its jobs, and sets its own 15-minute check with what its surface supports: a /loop or ScheduleWakeup loop in local Claude Code, send_later chained each check in cloud Claude Code, or a recurring scheduled task at the shortest interval allowed. Each check reads both names, acts on Start presses and Allison's replies, renews the lease on claimed jobs, and schedules the next check. A surface with no timer checks on every reply and says so once. No session ever asks Allison to wake it.
