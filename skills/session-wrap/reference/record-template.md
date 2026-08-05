# Session record template

Title: `Session Record [PROJECT] [YYYY-MM-DD]`
Delivered as one standalone markdown artifact so Allison can click Add to Project. Written for a reader with zero memory of the chat. Built from artifacts, the board, and repo state, never from chat scrollback.

## Required sections, in order

1. Mission. What this session was working on and why, in plain language.
2. Decisions. Every decision made, each in ADR shape:
   - The decision.
   - The context that forced it.
   - The alternatives rejected and why.
   - The consequences, what it costs and what it closes.
   - Canon-candidate: yes or no. (Yes means the canon sync protocol fires at step 4 of the wrap.)
3. Built, changed, created, deleted. What actually shipped or moved.
4. Everything touched. Every file, asset, document, repo, base, location, scenario, or ID, with full paths and IDs. No shorthand, no nicknames.
5. Open questions and flags. Every flag raised (UPDATE KNOWLEDGE DOCS, TEAM TRAINING NEEDED) with what still needs to happen and who or what it waits on.
6. Partial work. Anything unfinished and exactly where it stopped.
7. Exact end state. The state of the world right now, as pointers.

## Hard rules

- Point don't paste (Allison ruling 2026-08-04). Reference board cards by number and date only. Never paste card statuses, counts, or receipts into the record. The board and the repos stay the only living copies.
- If unsure of a value, say so plainly. Never guess paths, IDs, numbers, or dates.
- No secrets, credentials, or PII, ever. Token NAMES may appear, values never (1Password only, ADR 0028).
