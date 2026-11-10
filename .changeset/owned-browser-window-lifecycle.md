---
operating-doctrine: minor
---

Every browser job now owns one whole Chrome window that closes when the job is done. A lifecycle hook binds each job to its native session and closes that session's windows at Stop and SessionEnd on Factory, Claude Code and Codex, and a nightly sweep on the M2 closes windows of ended sessions. Active jobs, jobs with no proven owner and windows holding another tab are preserved. A connector born in an occupied window now moves to its own window first.
