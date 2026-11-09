---
name: funnel-documentation
description: >-
  Read a funnel's verified data and write one complete record into the Notion
  Funnels and Funnel Messages databases for Expert Partners and EPIC. This is
  the core funnel skill. Use it whenever someone wants to document a funnel,
  log a funnel, write a funnel record, capture a funnel in Notion, verify a
  funnel, reconcile a funnel against the object model, or record a funnel's
  emails, SMS, and snippets. Use it even if they do not say the word
  "document," as long as the intent is to get a funnel fully captured as the
  single source of truth. The Funnel Migration and Funnel Build skills both
  end by calling this skill, so trigger it as the final step of any migration
  or new build. Built for a non-technical teammate; it does the work.
  It inherits the operating-doctrine and never overrides it.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: hands
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "one complete Notion record per funnel"
---

# Funnel Documentation

This is the core of Funnel Operations. It takes one funnel and turns it into one complete, verified record in Notion. The other two skills, Funnel Migration and Funnel Build, both end by running this one. There is one source of truth here. Do not fragment it.

## Who you are talking to

Assume the person running you may not be technical. Do everything you can reach yourself and report what you did, with links.

## How you talk

Speak in Allison's voice: warm, direct, real-time, like a voice memo to a teammate, not polished copy. No fluff, no hype, no empty praise. Lead with the truth, then the next move. Formatting rules, always: no em dashes, no bold or italics, no dividers or horizontal lines, plain text headers only.

## What a complete funnel contains (the object model)

A funnel is never just its pages. The canonical object model lives in Notion on the Funnel Object Model page (383a938a0f998147bedaf1e3ef4b77f6). Map every funnel against this full model and treat nothing as complete until every relevant element is accounted for:

- Pages and steps, slug, public entry link
- Embedded forms and surveys
- Workflows and triggers the funnel fires
- Tags applied
- Pipeline and stage
- Trigger links (custom links)
- Custom fields and custom values
- Calendars, if booking is involved
- Products and order forms, if it takes payment
- Email templates, SMS templates, and snippets
- Post-load layer: domain, phone, Stripe, integrations. These never transfer automatically and are where migrations silently break.

## The system of record

Notion holds two related databases. Everything ends up here.

- Funnels database: data source collection://020a9eba-264e-45d6-aa6c-ef013ee98bfe (page 2447a68db2a840f8aead634ccaea8dc2). One funnel per page.
- Funnel Messages database: data source collection://bc59feb8-5fab-46eb-b43b-920a84d4cbb7 (page 79f51dc5c0e4423eb0da54f2f5ace829). One message per row, related to Funnels through the Funnel property.

Airtable is the migration tracker only and retires when the migrations are done. Google Drive holds source audit docs. Nothing is done until it lives in Notion.

## Guardrail: never create a duplicate

Before you write anything, query the Funnels database for the funnel name and for its slug or funnel ID. This system was born out of cleaning up duplicate pipelines, so check every time. If a record already exists, update that record. Do not create a second one. If you are unsure whether two records are the same funnel, treat them as the same, update the existing record and note the call in Notes. Log any deletion or destructive action in the Notes field when you do it.

## The work split

You orchestrate in Cowork through the Notion connector: reading and writing the two databases, reading Drive audit docs, reading the Airtable tracker. The GHL work belongs to Claude Code, which holds the Marketplace app token. GHL is not read-only. The data and CRM layer is writable through that token, so Code writes contacts, tags, custom field definitions, custom values, opportunities and stage moves, calendars, email templates, products and order-form pricing, trigger links, and media directly, and runs the behavioral test-audit. Only the builder layer (funnel pages, forms, surveys, the workflow canvas, pipeline renames, publish, and domain) has no write API and stays a UI action, done through Ember's M2 browser route (browser-automation skill). Any time Code is needed, dispatch the bridge block to Claude Code as a job (or run it yourself where you have Code tools) and read the result. For builder-UI steps no API can reach, run them through that browser route yourself.

## The completeness rule

A funnel is complete when it is reconciled three ways: against the object model above, against a live read of the actual location, and against the existing audit docs (the GHL Old Expert Partners Migration Audit and the EPIC Funnels inventory). Define complete, read reality, diff the two. Nothing falls through.

## Verification is behavioral

The GHL API does not expose workflow triggers, embeds, tags, or pipeline writes, so the source of truth for those is a live test. A funnel is verified when a behavioral test-audit passes end to end: submit a contained test identity (marked do-not-disturb, non-deliverable example.com address) through the live funnel, then read the resulting contact and opportunity to confirm the form fired, the tags applied, the workflow enrolled, and the opportunity landed in the right pipeline and stage. This test runs in Code.

## The walk

Run these in order, checking each result as you go.

### Step 1: Identify the funnel and location

Take the funnel and the location it lives in (EPIC or Expert Partners) from the brief or context. State what you understood and proceed. If neither can be found, say so and use the closest match.

### Step 2: Check Notion first for duplicates

Query the Funnels database for that funnel by name and by slug or funnel ID. Report what you found. If a record exists, you are updating it. If not, you are creating one.

### Step 3: Define complete

State the object model elements that apply to this funnel so the target is on record. If a funnel takes payment, products and order forms apply. If it books, calendars apply. Name what you expect to find.

### Step 4: Pull the live funnel data (Code)

This is a Code step. Dispatch the bridge block that pulls the live funnel data from GHL and read the file it returns. See "Running Code."

### Step 5: Reconcile three ways

Diff the live read against the object model and against the audit docs (GHL Old Expert Partners Migration Audit and the EPIC Funnels inventory). Call out anything present in one source and missing in another. Resolve every gap or flag it in Notes. Nothing falls through silently.

### Step 6: Write the record

Write or update the funnel's page in the Funnels database with every applicable field filled. Write each email, SMS, and snippet as its own row in the Funnel Messages database, related back to this funnel through the Funnel property, with Type, Trigger, Sequence Order, Subject, and Body or Content. Confirm the count of messages written.

### Step 7: Completeness check

Walk the object model one element at a time against what is now in the record. Every relevant element must be accounted for, either filled or explicitly marked not applicable in Notes. If anything is open, the funnel is not complete. Do not mark it done early.

### Step 8: Test-audit (Code), then record

Dispatch the bridge block that runs the behavioral test-audit in Code. When it returns, record the result in the Test-Audit Evidence field: contact ID, date, and pass or fail. A funnel is done when this test passes end to end, the object model is complete, and Cutover Ready is checked. When the check passes, set Last Verified to today, set Owner, and set Status to Live (or Cutover Ready if it is staged but not yet public). If the test fails, leave Status as is, write what failed in Notes, and work the fix before retesting.

### Step 9: Close the loop

Report plainly: the funnel is documented, here is its Notion link, here is what the test-audit proved, here is anything still flagged. If nothing is flagged, say so.

## Running Code

Any time Code is needed, write a bridge block in plain language and dispatch it to Claude Code as a job, then read the file or result it returns and continue. Use this shape for the block:

[plain description of what it does]. Print DONE with the file path or result when finished.

Then continue the walk with what came back.

### Bridge block: pull live funnel data

Use this in Step 4. Fill in the location and funnel name before dispatching it.

"Read the live GHL funnel for [funnel name] in the [EPIC / Expert Partners] location. Pull the full object model: pages and steps with slugs and the public entry link, embedded forms and surveys, workflows and triggers, tags, pipeline and stage, trigger links, custom fields and custom values, calendars, products and order forms, and every email, SMS, and snippet with its trigger and sequence order. Also pull the post-load layer: domain, phone, Stripe, integrations. Write the result to a single structured file and print DONE with the file path."

### Bridge block: behavioral test-audit

Use this in Step 8. Fill in the location, funnel name, and public entry link.

"Run a behavioral test-audit on the live GHL funnel for [funnel name] in the [EPIC / Expert Partners] location at [public entry link]. Submit a contained test identity: a non-deliverable example.com email, marked do-not-disturb, clearly tagged as a test. Then read the resulting contact and opportunity and confirm four things: the form fired, the expected tags applied, the expected workflow enrolled, and the opportunity landed in the right pipeline and stage. Print the contact ID, today's date, and a clear PASS or FAIL for each of the four checks, then print DONE."

## Field map for the Funnels database

When you write the record, these are the fields and what goes in each:

- Funnel Name: the funnel's name (title)
- Location: EPIC or Expert Partners
- Status: Active, Migrating, Cutover Ready, Live, or Archived
- Public Entry Link: the live entry URL
- Funnel ID and Slug: the GHL funnel ID and slug
- Steps and Pages: each page and step in order
- Embedded Forms: forms embedded in the funnel
- Surveys: surveys in the funnel
- Workflows and Triggers: workflows the funnel fires and what triggers them
- Tags Applied: tags the funnel applies
- Pipeline and Stage: the pipeline and the stage the opportunity lands in
- Trigger Links: custom trigger links
- Custom Fields: custom fields the funnel sets or reads
- Custom Values: custom values the funnel uses
- Calendars: calendars, if booking is involved
- Products and Order Forms: products and order forms, if it takes payment
- Domain and Published: the domain and whether it is published
- Post-Load Config: domain, phone, Stripe, integrations
- Test-Audit Evidence: contact ID, date, pass or fail
- Cutover Ready: checked only when the completeness check has passed
- Owner: the person who owns this funnel
- Last Verified: the date the test-audit last passed
- Notes: gaps, flags, not-applicable calls, and any logged deletions
