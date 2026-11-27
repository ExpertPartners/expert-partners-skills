---
name: ghl-asset-inventory
description: Pull a complete read-only inventory of Allison's GoHighLevel account and save it as a reference file. Use whenever Allison wants to see what exists in GHL before designing or building anything, or says "run a GHL asset inventory", "inventory my GHL", "what tags/fields/pipelines do I have", "map my GHL setup", or asks for a current snapshot of tags, custom fields, pipelines, or calendars. This skill NEVER changes anything. It is the safe first step before any automation design or cleanup.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: hands
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "read-only snapshot of the GHL account"
---

# GHL Asset Inventory

## What this does

Reads Allison's GoHighLevel account through the GHL MCP and produces one clean reference file listing everything in the account. It changes nothing. This is the read-only starting point before designing a new automation or planning a cleanup.

## When to run it

Before designing any new automation. Before any cleanup. On a quarterly cadence to keep the reference current. Any time Allison needs to confirm a tag, field, pipeline, or calendar name actually exists before she references it in a build.

## The one rule

Read only. Never create, update, tag, move, or delete anything. If Allison's request also asks for a change, finish the inventory and then run the cleanup or design skill that covers it.

## Steps

1. Read the live AI Implementation SOP and existing PartnerSync capability record. Verify the actual location grant with a harmless read. Use the shared Marketplace connector when it covers the operation; a native connector may expose a different set of locations. A saved registration is not a successful connection. If a client loaded old code, launch a fresh connection yourself. Never copy credentials between environments.

2. Pull and list, read-only:
   - All contact tags, with contact count per tag if available
   - All custom fields and their data types
   - All pipelines and their stages
   - All calendars with their IDs and names
   - Every workflow, including drafts, with stable ID, status and version. Follow every page and folder. Reconcile the result against the existing inventory. Names alone do not establish behavior.

3. Write the result to `/ghl-assets/ghl-asset-inventory.md` in the project folder, structured with a short plain-English summary at the top, then one clean section per category. If the folder does not exist, create the file in the project root and note where it landed.

4. If workflow behavior is requested, capture definitions, triggers, conditions, branches, waits, message content and referenced assets. Use the public definition API when enabled. A WORKFLOW_API_NOT_ENABLED_FOR_LOCATION response is a vendor feature-access refusal, not proof of a token-scope fault. Use the authorized signed-in M2 browser route documented in the SOP when the API cannot expose the definition. Do not open a production workflow editor for a read-only inventory: the editor may auto-save merely on load. Use the proven passive browser read, keep authentication within its existing session, redact credentials and signed asset URLs, and finish the owned browser job. Do not build a second connector.

5. Verify saved versions and status after the read. State "No changes were made to GoHighLevel" only when the evidence supports it. Disclose any auto-save or metadata change and keep it separate from deliberate step edits. Record missing templates and unresolved dependencies explicitly; never infer their content from their names. Save current evidence in the existing owning Drive home and update the existing audit, retaining its dated history.

## What good output looks like

A single markdown file, organized by category, every tag and field and pipeline and calendar accounted for, with a one-paragraph summary at the top. Contact counts included where the API provides them.

## Warning signs to surface to Allison

Any attempt to create or modify production data during inventory. Diagnose 401 and 403 responses from their actual error codes; identity, tenant grants, token scope and vendor feature availability are different failure classes. Missing assets or partial pagination require reconciliation, not assumptions. Never claim that access in one AI environment proves access in another; test each consuming configuration independently.
