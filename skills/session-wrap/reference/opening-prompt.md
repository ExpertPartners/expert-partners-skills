# Standing opening prompt (session open)

Allison pastes this to open a new session, lane name filled in. Same text every time.

```
CONTINUITY PROMPT

We are continuing this project. Before anything, load context. Via Estate Brain, fetch the most recent continuity note and session record for this lane from the aura intake inbox, and fetch the relevant canonical docs from the aura repo. Also read the most recent session record saved in this project's files if one is there. Treat the continuity note as the latest truth candidate. Check the lane ledger row for this lane in aura docs/estate/lanes.md before starting.

Then verify before trusting. Reconcile the note's stated state against the live board card (by its number) and the repo. If anything does not match, flag the mismatch to me before doing any work.

Then, before doing any work, restate back to me the mission in one line, the decisions still standing, the exact next step we left off on, and any warnings or dependencies. Do not start work until I confirm. One step and one question at a time.

Lane: [name the lane or project]
```

Why the fetch is active and not left to Project knowledge: Project knowledge retrieval is RAG (relevant-chunk retrieval, not guaranteed recall), and native chat memory is a summary profile, not a decision log. The MCP fetch is deterministic. Do not switch this to passive retrieval.
