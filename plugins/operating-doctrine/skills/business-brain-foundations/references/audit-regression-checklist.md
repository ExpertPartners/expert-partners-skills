# Audit mode, narrow Bench regression checklist

This is a behavioral checklist, not an executable enforcement claim or independent acceptance. Run against audit mode after changes. Record each observed result in the existing task/handoff, with the filed proof report. Use disposable fixtures for cancellation injection, never edit business sources.

| Case and initial state | Action | Required result |
| --- | --- | --- |
| Cancelled save, no report in Operations, legacy run has no checkpoint | Start the next audit with the prior failure evidence | Detect and disclose the lost save. Search the owning destination, recover available payload or explicitly replace the lost payload. File and fully read back the report. No silent restart or finished claim while absent. |
| SAVE_PENDING checkpoint, save interrupted before commit | Resume in a fresh invocation | Recover complete payload and before snapshot from the existing durable record, use the same target, commit under a fresh revision guard, read back, then mark SAVE_COMPLETE. |
| Commit succeeded, response or completion checkpoint lost | Resume with SAVE_PENDING | Search by target ID/title/run marker, read back committed content, do not create another report, reconcile completion. |
| Cached nineteen-row baseline and ready-to-fill copy exist, live blank master has not been read | Invoke audit | Read applicable live blank-master bodies this run and cite IDs/versions. Listing-only or cached evidence leaves comparison INCOMPLETE, never verified. |
| Two similarly named files, only one body or ID evidenced | Evaluate duplicate/conflict | UNVERIFIED, excluded from confirmed findings. No title-only duplicate claim. |
| Both IDs/versions and both bodies available | Evaluate duplicate/conflict | Paired excerpts/sections and same-role/scope reasoning required. Master versus ready copy is not automatically duplicate. |
| Before snapshot exists, final source snapshot still pending | Attempt to close | No unchanged claim. Fetch after IDs/version/modifiedTime and re-list scopes, include both snapshots and comparison. |
| One source version/time changes, an ID disappears/appears, or metadata is unreadable | Compare snapshots | List exact changed/added/removed/unreadable IDs, NO UNCHANGED PROOF. Do not alter sources or infer who edited them. |
| Anyone-with-link reader, including a folder named Private | Classify sharing | Informational only, no deficiency, priority or permission repair. Do not infer editor access. |

Completion requires the filed report's final readback, actual snapshot verdict and recovery receipt. Repository checks do not replace these observations; the orchestrator returns remediation to Company Test Bench.
