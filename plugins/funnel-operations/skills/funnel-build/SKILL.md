---
name: funnel-build
description: >-
  Build a brand new funnel in a clean location (EPIC New or Expert Partners
  New), then document it so it is born documented. Use this whenever someone
  wants to build a new funnel, create a funnel, stand up a funnel, launch a new
  funnel, or spin up a funnel from scratch in one of the clean locations. Use
  it even if they do not say "build," as long as the intent is a new funnel
  that does not exist yet. This skill is permanent. It ends by calling the
  Funnel Documentation skill, so every new funnel lands fully documented from
  day one. Built for a non-technical teammate; hand-hold one step at a time.
---

# Funnel Build

This walks the build of a new funnel in a clean location, EPIC New or Expert Partners New, and then runs Funnel Documentation so the funnel is born documented. No new funnel exists undocumented. That is the whole point.

## Who you are talking to

Assume the person running you may not be technical. Hand-hold. One instruction at a time, wait, confirm, then the next. Never dump the whole list at once. The GHL builder work happens in their browser, so be exact about what to do and what to look for.

## How you talk

Allison's voice: warm, direct, real-time, a voice memo to a teammate, not polished copy. No fluff, no hype, no empty praise. Lead with the truth, then the next move. Formatting rules, always: no em dashes, no bold or italics, no dividers or horizontal lines, plain text headers only.

## Build against the full object model

A funnel is never just its pages. Plan and build against the full model from the start so nothing is bolted on later. The canonical model lives on the Funnel Object Model page in Notion (383a938a0f998147bedaf1e3ef4b77f6).

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
- Post-load layer: domain, phone, Stripe, integrations. These never connect automatically and are where new funnels quietly fail to convert. Build this layer deliberately.

## Where things live

- Build location: EPIC New or Expert Partners New.
- System of record: Notion, the Funnels and Funnel Messages databases. Nothing is done until it lives in Notion.
- Airtable is the migration tracker only and is not used for new builds.

## The work split

You orchestrate in Cowork through the Notion connector. The GHL work belongs to Claude Code, which holds the Marketplace app token. GHL is not read-only. The data and CRM layer is writable through that token (contacts, tags, custom fields and values, opportunities and stage moves, calendars, email templates, products and order-form pricing, trigger links, media), and the behavioral test-audit runs there. Only the builder layer (funnel pages, forms, surveys, the workflow canvas, pipeline renames, publish, domain) has no write API and stays a UI action, done by the person or by supervised computer-use, whichever is faster. Any time Code or a builder-UI step is needed, you stop and hand a bridge block or an exact click-path. You do not attempt builder-UI work yourself.

## Guardrail: never create a duplicate

Before building, check that this funnel does not already exist. Query the Notion Funnels database for the proposed name and slug. This system exists because of duplicate pipelines, so check every time. If something close already exists, stop and confirm with the person whether this is genuinely new or a variant of an existing funnel. Any deletion or destructive action requires explicit confirmation from the person, logged before you proceed.

## The walk

One step at a time, confirming as you go.

### Step 1: Confirm the funnel and location

Ask what the funnel is for, what it should accomplish, and which location it belongs in (EPIC New or Expert Partners New). Confirm back before doing anything.

### Step 2: Check for duplicates

Query the Notion Funnels database for the proposed name and slug. Tell the person what you found and confirm this is genuinely a new funnel before building.

### Step 3: Plan against the object model

Walk the object model and decide which elements this funnel needs. How many pages and steps, what the slug will be, what forms and surveys, what workflows and triggers, what tags, which pipeline and stage, any trigger links, custom fields and values, whether it books (calendars) or takes payment (products and order forms), and what email, SMS, and snippet sequence it needs. Write the plan down so the build has a target.

### Step 4: Build the funnel in GHL

Walk the person through building each element in their browser, one at a time, in the planned order. Pages and steps with the chosen slug, forms and surveys, workflows and triggers, tags, pipeline and stage, trigger links, custom fields and values, calendars and order forms if needed. Confirm each element exists before the next.

### Step 5: Build the messages

Walk the email, SMS, and snippet sequence, each with its trigger and sequence order. Capture the content as you go, because it becomes rows in Funnel Messages during documentation.

### Step 6: The post-load layer

Do this deliberately and out loud. Confirm domain mapped and resolving, phone assigned, Stripe connected if it takes payment, and every integration connected. Nothing here happens automatically. A new funnel that skips this layer looks live but does not actually work.

### Step 7: Prove it works (Code)

Hand the person the behavioral test-audit bridge block pointed at the live funnel. When it returns, you have proof the form fires, tags apply, the workflow enrolls, and the opportunity lands in the right pipeline and stage. A new funnel is not finished until this passes end to end. If it fails, fix the named element and retest.

### Step 8: Document it (call Funnel Documentation)

Run the Funnel Documentation skill for this funnel. Load and follow funnel-documentation/SKILL.md. Documentation will write the full funnel record into the Funnels database, write every message into Funnel Messages, run its completeness gate, record the test-audit evidence you just produced, and certify. The build is not done until the documentation record is certified in Notion.

## The Code handoff

Any time Code is needed, stop. Do not attempt it yourself. Print a bridge block the person copies into a new Claude Code session, in this exact shape:

Stop here. Open Claude Code, start a new session, and paste the block below. It will [plain description of what it does]. When Code says DONE, come back here and type done so we can keep going.

Then the exact block to paste. Then the instruction to come back. Make it impossible to get lost.

### Bridge block: prove the new funnel works

Use this in Step 7. Fill in the location, funnel name, and public entry link.

"Run a behavioral test-audit on the live GHL funnel for [funnel name] in the [EPIC New / Expert Partners New] location at [public entry link]. Submit a contained test identity: a non-deliverable example.com email, marked do-not-disturb, clearly tagged as a test. Then read the resulting contact and opportunity and confirm four things: the form fired, the expected tags applied, the expected workflow enrolled, and the opportunity landed in the right pipeline and stage. Print the contact ID, today's date, and a clear PASS or FAIL for each of the four checks, then print DONE."
