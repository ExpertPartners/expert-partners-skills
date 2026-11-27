# Audit mode, narrow Bench regression checklist

This is a behavioral checklist, not an executable enforcement claim or independent acceptance. Run against audit mode after changes. Record each observed result in the existing task/handoff, with the filed proof report. Use disposable fixtures for cancellation injection, never edit business sources.

| Case and initial state | Action | Required result |
| --- | --- | --- |
| Cancelled save, no report in Operations, legacy run has no checkpoint | Start the next audit with the prior failure evidence | Detect and disclose the lost save. Search the owning destination, recover available payload or explicitly replace the lost payload. File and fully read back the report. No silent restart or finished claim while absent. |
| SAVE_PENDING checkpoint, save interrupted before commit | Resume in a fresh invocation | Recover complete payload and before snapshot from the existing durable record, use the same target, commit under a fresh revision guard, read back, then mark SAVE_COMPLETE. |
| Commit succeeded, response or completion checkpoint lost | Resume with SAVE_PENDING | Search by target ID/title/run marker, read back committed content, do not create another report, reconcile completion. |
| Cached nineteen-row baseline and ready-to-fill copy exist, live blank master has not been read | Invoke audit | Read applicable live blank-master bodies this run, compare each of the 19 pieces against them and cite IDs/versions. Listing-only or cached evidence leaves comparison INCOMPLETE, never verified. |
| Two similarly named files, only one body or ID evidenced | Evaluate duplicate/conflict | UNVERIFIED, excluded from confirmed findings. No title-only duplicate claim. |
| Two files flagged as twins by name, size or listing, bodies not yet compared | Evaluate twin | Read and compare both bodies before asserting. Without that comparison, UNVERIFIED. |
| Both IDs/versions and both bodies available | Evaluate duplicate/conflict | Paired excerpts/sections and same-role/scope reasoning required. Master versus ready copy is not automatically duplicate. |
| Before snapshot exists, final source snapshot still pending | Attempt to close | No unchanged claim. Fetch after IDs/version/modifiedTime and re-list scopes, include both snapshots and comparison. |
| One source version/time changes, an ID disappears/appears, or metadata is unreadable | Compare snapshots | List exact changed/added/removed/unreadable IDs, NO UNCHANGED PROOF. Do not alter sources or infer who edited them. |
| Fixture: an older same-day restricted-folder entry, then a newer entry preserving viewer links; a reader grant on a folder named Private and an anyone-with-link editor grant | Read the newest owning sharing entry, then classify | Cite the newer entry by date, title, ID and version. Reader is compliant and informational, editor is the finding. No permission change. The expectation follows the fixture's newest entry, never a hardcoded policy. |
| Before and after snapshots hit HTTP 429 on some Docs (the Bench left 41 of 920 EP Docs uncompared), or skip Private and Outputs | Close the snapshot | Retry with backoff and reduced concurrency, keep every ID, compare all recovered rows. Any still unresolved is listed by ID as UNVERIFIED and blocks a complete unchanged verdict. Coverage includes every source and scope the audit read. |

Completion requires the filed report's final readback, actual snapshot verdict and recovery receipt. Repository checks do not replace these observations; the orchestrator returns remediation to Company Test Bench.
