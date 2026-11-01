# Standing opening prompt (session open)

Allison pastes this to open a new session, lane name filled in. For a message from another AI, use the current HQ Rulebook section Handoffs between AIs and include the actual sender, receiver, model and effort or speed in the same copy box. Keep the existing job identity on continuation.

```
CONTINUITY PROMPT

We are continuing this project. Before anything, load context. From Drive, fetch the most recent continuity note for this lane from the owning brain, and read the HQ Rulebook and the Decision Log. Retrieve the prior session report from the existing Chat to Code job through job_status. Dated session records already saved in this project's files are history, not a second current work record. Treat the continuity note as the latest truth candidate. Check job_status for this lane's existing job before starting and use job_claim rather than duplicating it. If no job exists, use job_create. Code work travels as a GitHub issue labeled job.

Then verify before trusting. Reconcile the note's stated state against the live board card (by its number) and the repo. If anything does not match, flag the mismatch to me before doing any work.

Then, before doing any work, restate back to me the mission in one line, the decisions still standing, the exact next step we left off on, and any warnings or dependencies. Do not start work until I confirm. One step and one question at a time.

Lane: [name the lane or project]
```

Why the fetch is active and not left to Project knowledge: Project knowledge retrieval is RAG (relevant-chunk retrieval, not guaranteed recall), and native chat memory is a summary profile, not a decision log. The Drive connector fetch is deterministic. Do not switch this to passive retrieval.
