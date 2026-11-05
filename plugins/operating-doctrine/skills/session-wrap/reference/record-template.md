# Session record template

Report title: `Session Record [PROJECT] [YYYY-MM-DD]`
For a genuinely completed assignment, file the report as this job's job_finish summary with a result link, then verify it through job_status. For unfinished work, preserve the progress report and open state in the same job through a schema-supported nonterminal write; never call job_finish just because a session is wrapping. Link substantive deliverables in their owning homes, not a duplicate work log. Any reply to another AI follows the current HQ Rulebook section Handoffs between AIs. Written for a reader with zero memory of the chat. Built from artifacts, the board, and repo state, never from chat scrollback.

## Required sections, in order

1. Mission. What this session was working on and why, in plain language.
2. Decisions. Every decision made, each in ADR shape:
   - The decision.
   - The context that forced it.
   - The alternatives rejected and why.
   - The consequences, what it costs and what it closes.
   - Canon-candidate: yes or no. (Yes means the canon sync protocol fires at step 5 of the wrap.)
3. Built, changed, created, deleted. What actually shipped or moved.
4. Everything touched. Every file, asset, document, repo, base, location, scenario, or ID, with full paths and IDs. No shorthand, no nicknames.
5. Open questions and flags. Every flag raised (UPDATE KNOWLEDGE DOCS, TEAM TRAINING NEEDED) with the verified current owner, exact next action and any dependency. Classify it as ripe or waiting under SKILL.md step 4. Complete or assign authorized AI work through the current HQ owner/job route. A genuine founder question uses the current board-supported question route with a recommendation. Where current HQ requires job_finish with outcome needs-allison for a non-code job, make and verify that decision request even while the assignment is unfinished. It is not completion, does not count as the single final completion report and does not clear archive readiness. An ordinary AI-owned technical or retrieval gap does not become a founder question or justify a done outcome. Waiting work keeps its named return condition and required stale or follow-up condition in the existing approved work record. Verify delivery or the saved wait; do not require Allison to relay routine work or create a duplicate record.
6. Partial work. Anything unfinished and exactly where it stopped.
7. Exact end state. The state of the world right now, as pointers.

## Hard rules

- Point don't paste (Allison ruling 2026-08-04). Reference applicable board cards, files, commits and owning documents rather than copying live state or receipts. Resolve authoritative homes through current HQ: business records in their owning Drive brain and plan, job state in its existing approved work record, and code, skills and technical artifacts with their current GitHub owner.
- If unsure of a value, say so plainly. Never guess paths, IDs, numbers, or dates.
- No secrets, credentials, or PII, ever. Token NAMES may appear, values never (1Password only, ADR 0028).
