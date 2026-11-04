# Standing opening prompt (session open)

Use this context loader when a worker starts or resumes its existing assignment. Keep the same job identity and use the current code-block-routing route for any worker handoff. A first-message box is only for a brand new chat Allison explicitly asked to create, never a requirement that she wake an existing worker.

```
CONTINUITY PROMPT

We are continuing this project. Before anything, load context. From Drive, fetch the most recent continuity note for this work from the owning brain, and read Organization Instructions, the HQ Rulebook and the Decision Log. Retrieve the prior session report from the existing Chat to Code job through job_status. Dated session records already saved in this project's files are history, not a second current work record. Treat the continuity note as a predecessor's interpretation to verify. Check job_status for the existing job, owner and exact scope before starting. Claim the assigned non-code job where required, never another active worker's assignment. If no job exists, use the current code-block-routing route, job_create for non-code work or one GitHub Job issue for code, without making a duplicate record.

Then verify before trusting. Reconcile the note's claims against the current job, owning plan, actual repository/worktree/branch, changes, linked pull request and checks as applicable. Distinguish a worktree that exists from a proven active owner. Resolve ordinary mismatches from current evidence and preserve unrelated work. A failed required read or a proven scope collision stops only the dependent action and is reported with its owner, verified state and missing evidence.

Give a brief readback of the goal, decisions still standing, exact next action and warnings. Execute the already-authorized safe next action without another start confirmation. A genuinely missing founder fact or approval goes on the existing AI Workboard through the current supported question route, with a recommendation and the evidence already checked. Keep working on independent authorized actions while that answer is pending. Do not invent a permission gate or treat this context read as completion of the assignment.

Lane: [name the lane or project]
```

Why the fetch is active and not left to Project knowledge: Project knowledge retrieval is RAG (relevant-chunk retrieval, not guaranteed recall), and native chat memory is a summary profile, not a decision log. The Drive connector fetch is deterministic. Do not switch this to passive retrieval.
