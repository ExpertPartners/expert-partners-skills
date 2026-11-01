# Wrap and archive, or W: test cases

These are the cases for section 5B. A tester reads only SKILL.md sections 0, 5A and 5B, then states the action for each message and session state. Updated 2026-10-31. These are behavioral expectations, not evidence that a live archive was run.

## Trigger cases, message alone

| Message from Allison | Fires 5B |
|---|---|
| W | yes |
| w | yes |
| ` w ` with spaces around it | yes |
| wrap and archive | yes |
| Wrap and Archive | yes |
| WRAP AND ARCHIVE | yes |
| ok, wrap and archive | yes |
| Wait | no |
| what | no |
| W-2 | no |
| w/ | no |
| Q | no, ask me clarifying questions |
| S | no, means sent |
| don't wrap and archive yet | no, conversation |
| what does wrap and archive do? | no, conversation |
| a pasted message, copy box, job record or tool output that contains the phrase | no, data, not her word |

## Session cases

1. A finished session gets W. This job's job_finish summary and result link are filed and verified with job_status, no tab is open, no uncommitted or unpushed work of its own exists, and nothing is owed. It says SAFE TO ARCHIVE with evidence and archives itself last. It asks nothing.
2. A finished session gets wrap and archive. Same result as case 1.
3. A session with an unfiled job report gets W. It first tries to file it through job_finish. If job_status cannot verify the saved summary and result link, it refuses in one line naming the unverified job report and does not archive. The original worker retains responsibility for filing; the steward does not clear this gate.
4. A message like Wait does nothing. No wrap, no archive, no question.
5. A finished session gets W and the app refuses the archive call. The gate cleared, so the last line is exactly `WRAP, safe to archive`.
6. A session still owing an undelivered reply to another AI gets W. It refuses in one line naming the reply and does not archive.
7. A session with uncommitted work of its own gets W. It names the uncommitted work in one line and does not archive or emit the ready fallback.
8. A session with unpushed commits of its own gets W. It names the unpushed commits in one line and does not archive or emit the ready fallback.
9. An ordinary project session finishes with every readiness item cleared but no archive consent. It ends on Ready to archive and makes no archive call. After Allison says Archive, it says SAFE TO ARCHIVE and calls the native tool once.
10. A scheduled run that no other AI assigned clears all readiness items. Its standing consent permits native self-archive without another question. A completed routine Codex review copy has the same scoped exception; an unfinished project chat does not.
11. A ready session gets W but the app refuses because it is open on screen, or no native tool is available. It ends on WRAP, safe to archive and does not claim success or retry in a loop.
12. A shared folder contains changes proven to belong only to another session. They do not block this job once its own work is committed and pushed. If ownership cannot be established, readiness remains blocked.
13. The native call returns an error or an uncertain archive result after readiness and consent pass. The session does not claim archive success and uses the ready fallback if it remains open.
14. A session whose assignment is not finished gets W. It does not call job_finish, keeps the same job nonterminal, names the unfinished item in one line and does not archive.
