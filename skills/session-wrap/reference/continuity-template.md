# Continuity note template

Its own markdown document, never buried inside the session record. It is what the next session loads first, so it carries its own context and stands fully alone.

## Required content, in order

1. Supersession line, verbatim first line: "This note supersedes all prior continuity notes for lane [LANE]. Dated [YYYY-MM-DD]."
2. What we were doing and why. Mission in one or two plain sentences.
3. Decisions still standing. Only the ones that constrain the next session.
4. The exact first next step. One step, concrete, executable.
5. Warnings and dependencies. What blocks, what waits, what must not be touched.
6. Relevant paths, IDs, and values. Full paths, exact IDs, no shorthand.

## Hard rules

- The note is a predecessor's interpretation, not ground truth. It must be cheap to verify: prefer pointers (card numbers, file paths, commit refs) over restated state so the next session can reconcile against the live board and repo.
- If unsure of a value, say so. Never guess.
- No secrets, credentials, or PII, ever.
