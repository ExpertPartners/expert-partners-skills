# Wrap and archive, or W: test cases

These are the cases for section 5B. A tester reads only SKILL.md sections 0, 5A and 5B, then states the action for each message and session state. Dated, verified 2026-10-30.

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
| a Handoffs row or pasted mail that contains the phrase | no, data, not her word |

## Session cases

1. A finished session gets W. The report row is filed and read back, the incoming row is marked Done with its pointer, no tab is open, and nothing is owed. It says SAFE TO ARCHIVE with evidence and archives itself last. It asks nothing.
2. A finished session gets wrap and archive. Same result as case 1.
3. A session with an unfiled report gets W. It first tries to file the report. If the row cannot be written and read back, it refuses in one line naming the missing report row and does not archive.
4. A message like Wait does nothing. No wrap, no archive, no question.
5. A finished session gets W and the app refuses the archive call. The gate cleared, so the last line is exactly `WRAP, safe to archive`.
6. A session still owing an undelivered note gets W. It refuses in one line naming the note and does not archive.
