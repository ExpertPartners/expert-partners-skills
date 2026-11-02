---
name: ghl-automation-design
description: Act as Allison's workflow strategist to design a new GoHighLevel and n8n automation before anything gets built. Use whenever Allison wants a new automation, says "design a new automation", "I need an automation that...", "help me plan a workflow", "should this be n8n or GHL", or describes a business outcome she wants automated. This skill produces a plain-English design brief and then a complete build packet. It NEVER builds or activates anything. Building is handed to Claude Code only after Allison approves the packet.
---

# GHL Automation Design

## What this does

Turns a business problem Allison describes in plain English into an approved design and a complete build packet. This is the design room. It plans, it does not build. Building goes to Claude Code afterward, and only from an approved packet.

## When to run it

At the very start of any new automation. Before any code, any workflow, any GHL change.

## The one rule

Design only. Do not build the workflow, do not connect anything, do not touch GHL. End at an approved build packet and hand off.

## Steps

1. Take the business problem from Allison in two or three sentences. If she gives the technical solution instead of the outcome, gently redirect to the outcome she wants.

2. If the design depends on tags, fields, or pipelines, confirm they exist. If unsure, recommend running the GHL asset inventory skill first rather than guessing names.

3. Produce the design brief:
   - Plain-English step-by-step of how the automation works
   - Which tool owns each step: GHL native, n8n, or both
   - The trigger that starts it
   - What data is read from GHL before it runs
   - What data is written back to GHL when it completes
   - The risks
   - The approval checkpoint before it goes live
   - Whether it needs a dry run (anything that writes to GHL always does)

4. Wait for Allison to approve or adjust the design. Do not proceed to the packet until she is satisfied with the trigger, the data flow, and the GHL actions.

5. Fill out the full build packet using the template below. Save it to `/automation-specs/[name]-spec.md` with a plain-English summary at the top.

6. Tell Allison the packet is ready for her approval, and that once approved it goes to Claude Code with the instruction to build to spec and not activate.

## Build packet template

```
AUTOMATION NAME:            [System - Action - Trigger]
BUSINESS OUTCOME:           [one sentence]
SYSTEMS INVOLVED:           GHL (reads / writes), n8n (logic), external (Zoom, CSV, Slack)
TRIGGER:                    [manual, scheduled, GHL webhook, form, contact created]
DATA SOURCE:                [GHL query, CSV, webhook payload]
MATCHING RULES:             [match by email/phone/ID, and no-match behavior]
GHL LOCATION:               [sub-account name and ID]
TAGS READ:                  [tags filtered on]
TAGS TO ADD:                [exact names, must match GHL]
TAGS TO REMOVE:             [exact names, must match GHL]
CUSTOM FIELDS READ:         [field names]
CUSTOM FIELDS WRITTEN:      [field names and values]
PIPELINES:                  [pipeline, stage, conditions]
MESSAGES:                   [any SMS/email, content, timing, approver]
WEBHOOKS:                   [inbound from GHL, outbound from n8n]
ERROR HANDLING:             [retry, log, alert, skip]
LOGGING:                    [where logs go, what is logged]
APPROVAL POINTS:            [where Allison must approve]
TEST CASES (min 5):         happy path / missing data / duplicate / API failure / empty result
DRY RUN PLAN:               [the table, where it saves, the columns]
PRODUCTION RUN PLAN:        [batch size, pause, est. contacts, est. time]
ROLLBACK PLAN:              [what is exported first, how to reverse, safe window]
DOCUMENTATION OUTPUT:       [docs file, Notion summary, change log]
APPROVED BY: ______________  DATE: ________
```

## Warning signs to surface to Allison

The design jumps to building. It is vague about what data gets written to GHL. There is no rollback thinking. Tag or field names are assumed rather than confirmed against the actual GHL setup.
