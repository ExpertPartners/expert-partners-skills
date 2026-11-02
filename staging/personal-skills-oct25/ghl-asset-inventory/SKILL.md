---
name: ghl-asset-inventory
description: Pull a complete read-only inventory of Allison's GoHighLevel account and save it as a reference file. Use whenever Allison wants to see what exists in GHL before designing or building anything, or says "run a GHL asset inventory", "inventory my GHL", "what tags/fields/pipelines do I have", "map my GHL setup", or asks for a current snapshot of tags, custom fields, pipelines, or calendars. This skill NEVER changes anything. It is the safe first step before any automation design or cleanup.
---

# GHL Asset Inventory

## What this does

Reads Allison's GoHighLevel account through the GHL MCP and produces one clean reference file listing everything in the account. It changes nothing. This is the read-only starting point before designing a new automation or planning a cleanup.

## When to run it

Before designing any new automation. Before any cleanup. On a quarterly cadence to keep the reference current. Any time Allison needs to confirm a tag, field, pipeline, or calendar name actually exists before she references it in a build.

## The one rule

Read only. Never create, update, tag, move, or delete anything. If Allison's request seems to ask for a change, stop and confirm she wants the separate cleanup or design skill instead.

## Steps

1. Connect to GoHighLevel using the GHL MCP and the saved credentials. If the GHL MCP is not connected yet, say so plainly and stop. Do not attempt a workaround that writes data.

2. Pull and list, read-only:
   - All contact tags, with contact count per tag if available
   - All custom fields and their data types
   - All pipelines and their stages
   - All calendars with their IDs and names
   - All active workflow names

3. Write the result to `/ghl-assets/ghl-asset-inventory.md` in the project folder, structured with a short plain-English summary at the top, then one clean section per category. If the folder does not exist, create the file in the project root and note where it landed.

4. Confirm at the end, in these words: "No changes were made to GoHighLevel."

## What good output looks like

A single markdown file, organized by category, every tag and field and pipeline and calendar accounted for, with a one-paragraph summary at the top. Contact counts included where the API provides them.

## Warning signs to surface to Allison

Any attempt to create or modify data. Any 401 or 403 permission error, which means the token scope is wrong. Output that is missing pipelines or tags she knows exist, which means the pull was incomplete and should be rerun.
