---
operating-doctrine: patch
---

Job List Heartbeat checks now run silently, a CEO directive from Allison (Decision Log 2026-11-03, Job checks run silently). Every room still checks the job list every 15 minutes, and claiming and lease renewal are unchanged. A check posts in its room only when something significant changed, meaning a job was claimed, finished or failed, or now needs Allison, her reply was acted on, or a new blocker came up, and then it posts one short Quick Update or CEO brief. A check with nothing significant posts nothing. In local Claude Code it ends the tick with ScheduleWakeup and noop true, or the /loop equivalent, and no text. Lease renewals, still working, nothing new and next check set are never posted. The first reply still says the check is set and when the next one runs, once, and later checks never repeat it. A new test case covers a check that finds nothing and posts nothing.
