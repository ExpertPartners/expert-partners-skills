---
name: ghl-tag-audit-and-cleanup
description: Audit Allison's GoHighLevel tags and, only after she approves, run a safe tag cleanup using the dry-run-approve-rollback-execute pattern. Use whenever Allison says "audit my tags", "clean up my tags", "run a safe cleanup", "remove old event tags", "add a tag to a batch", or wants any bulk tag change in GHL. The audit is read-only. The cleanup NEVER changes live data without a dry run Allison has reviewed and approved and a rollback file exported first.
---

# GHL Tag Audit and Safe Cleanup

## What this does

Two phases. First, a read-only audit of Allison's tags so she can see what to keep, review, or delete. Second, only on her go, a safe cleanup that changes tags using the non-negotiable safety pattern: dry run, approve, rollback file, batched execute, exception report.

## The one rule

Nothing touches live GHL data without a dry-run report Allison has reviewed and approved, and a rollback file exported first. If either is missing, stop.

## Phase 1: Audit (read-only)

1. Connect to GHL via the MCP. If it is not connected, say so and stop.

2. Pull all contact tags. Produce a table: Tag Name, Contact Count, Status (Keep / Review / Likely Delete), Notes. Flag duplicates and near-duplicates, tags under 5 contacts, and anything that looks like a test or temp tag. Give a recommended cleanup plan.

3. Save the audit to `/dry-run-reports/tag-audit-[date].csv`. Change nothing. Confirm no changes were made.

4. Stop and let Allison decide what to act on. Do not proceed to any change on your own.

## Phase 2: Safe cleanup (only after Allison approves an action)

Follow this exact sequence. Do not skip a step, do not reorder, do not expand scope.

1. Manual trigger. This never runs automatically.

2. Pull the affected contacts, read-only, using the exact filter the change will use.

3. Generate the dry-run table: Contact ID, First Name, Last Name, Email, Current State, Proposed Change, Reason, Risk Flag. Count the total affected. Flag anything unusual. Save to `/dry-run-reports/` with today's date.

4. STOP. Show Allison the summary and the table. Wait. Do not execute until she types: approved, run live.

5. Export a rollback file (snapshot of the affected contacts before any change) to `/rollback-files/`.

6. Execute in batches of 25 with a 2-second pause between batches to respect the GHL rate limit. Only touch contacts on the approved list.

7. Log every action: Contact ID, tags added, tags removed, timestamp, success or fail. If one fails, log it and keep going.

8. Produce a final execution log in `/change-logs/` and a separate exception report in `/dry-run-reports/` for any failures.

9. If this was a one-time cleanup workflow, archive it: turn it off and label it ARCHIVED with the date.

## How Allison reviews a dry run

Under 50 contacts, every row. Over 50, spot-check 15 to 20 percent and look hard for contacts that should not be on the list and for any Risk Flag that is not None.

## Warning signs to surface

Changes start before approval. Non-matches get silently skipped instead of flagged. Scope grows beyond the approved list. A large batch reports 100 percent success with zero exceptions, which usually means failures are hiding. No batch pause. Missing exception report.
