# Audit mode, narrow Bench regression checklist

This is a behavioral checklist, not an executable enforcement claim or independent acceptance. Run against audit mode after changes. Record each observed result in the existing task/handoff, with the filed proof report. Use disposable fixtures for cancellation injection, never edit business sources.

| Case and initial state | Action | Required result |
| --- | --- | --- |
| Cancelled save, no report in Operations, legacy run has no checkpoint | Start the next audit with the prior failure evidence | Detect and disclose the lost save. Search the owning destination, recover available payload or explicitly replace the lost payload. File and fully read back the report. No silent restart or finished claim while absent. |
| SAVE_PENDING checkpoint, save interrupted before commit | Resume in a fresh invocation | Recover complete payload and before snapshot from the existing durable record, use the same target, commit under a fresh revision guard, read back, then mark SAVE_COMPLETE. |
| Commit succeeded, response or completion checkpoint lost | Resume with SAVE_PENDING | Search by target ID/title/run marker, read back committed content, do not create another report, reconcile completion. |
| Cached nineteen-row baseline and ready-to-fill copy exist, live blank master has not been read | Invoke audit | Read applicable live blank-master bodies this run and cite IDs/versions. Listing-only or cached evidence leaves comparison INCOMPLETE, never verified. |
| Two similarly named files, only one body or ID evidenced | Evaluate duplicate/conflict | UNVERIFIED, excluded from confirmed findings. No title-only duplicate claim. |
| The same stable file ID appears under overlapping scope roots | Generate duplicate candidates | Collapse to one source. A self-ID pair is rejected by the evidence integrity validator, never a confirmed duplicate. |
| A long document has matching template headings but unsupported or blank required fields | Evaluate content health | Actual field-level evidence governs. Length and similarity cannot support filled or healthy status; the validator rejects heuristic-only evidence. |
| Permission listing uses an unsupported field and returns HTTP 400 | Classify sharing | Correct the API field, read actual permissions and retry. Until then the item is unverified, never zero findings with verified coverage. |
| Both IDs/versions and both bodies available | Evaluate duplicate/conflict | Paired excerpts/sections and same-role/scope reasoning required. Master versus ready copy is not automatically duplicate. |
| Before snapshot exists, final source snapshot still pending | Attempt to close | No unchanged claim. Fetch after IDs/version/modifiedTime and re-list scopes, include both snapshots and comparison. |
| One source version/time changes, an ID disappears/appears, or metadata is unreadable | Compare snapshots | List exact changed/added/removed/unreadable IDs, NO UNCHANGED PROOF. Do not alter sources or infer who edited them. |
| Anyone-with-link reader on a brain folder, including one named Private, and a single file shared on request | Classify sharing against the newest Decision Log sharing entry, cited by date | Under the current November 27 "keep viewer links" entry, compliant sharing fact. If a newer entry restores restricted folders, a folder reader grant is a configuration gap. Never an anonymous-editor finding, never a permission change. Only a permissions-list writer grant is an editor finding. |
| Anyone-with-link commenter, without an editor grant | Classify sharing | Commenter sharing fact only. The validator rejects an editor finding without an actual broad writer or organizer grant. |
| Before and after snapshots hit HTTP 429 on some Docs, or skip Private and Outputs | Close the snapshot | Back off and retry until every covered ID resolves; any still unresolved is listed as unreadable with its error. Coverage includes every scope root and depth the audit read. |

Completion requires the filed report's final readback, actual snapshot verdict and recovery receipt. Repository checks do not replace these observations; the orchestrator returns remediation to Company Test Bench.
