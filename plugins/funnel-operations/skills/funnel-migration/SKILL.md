---
name: funnel-migration
description: >-
  Move a funnel out of the old PartnerSync location and into EPIC or
  Expert Partners, verify every object-model element transferred, certify
  the cutover with a live behavioral test, then document it. Use this whenever
  someone wants to migrate a funnel, move a funnel to the new location, port a
  funnel out of the legacy Expert Partners GHL, cut over a funnel, or rebuild
  an old funnel in a clean location. Use it even if they do not say "migrate,"
  as long as the intent is moving an existing funnel from old to new. This
  skill is temporary and retires once the Expert Partners migration is done.
  It ends by calling the Funnel Documentation skill, so the funnel lands fully
  documented. Built for a non-technical teammate; hand-hold one step at a time.
  It inherits the operating-doctrine and never overrides it.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: hands
status: live
inherits: operating-doctrine
calls:
  - funnel-documentation
brand-scope: null
subtitle: "per-funnel walk from old location to clean location"
---

# Funnel Migration

STATUS (2026-07-27): STALE, retirement pending. The migration this skill served is over: EPIC went clean-in-place on its live location (partnersync ADR 0006) and the "EPIC New" build location became AG Personal Brand. Do not run this skill against the current estate without first reading the canonical registry (partnersync/reference/ghl-location-registry.md) and confirming with Allison that a genuine funnel move is in play.

This is the per-funnel walk for moving one funnel from the old PartnerSync location (legacy Expert Partners GHL) into a clean location, EPIC or Expert Partners. It verifies every object-model element, certifies the cutover with a live test, then hands off to Funnel Documentation so the funnel is born documented in the same pass. This skill is temporary. It retires after both migrations are complete.

## Who you are talking to

Assume the person running you may not be technical. Hand-hold. One instruction at a time, wait, confirm what happened, then the next step. Never dump the whole list at once. The GHL builder work happens in their browser, so be precise about what to click and what to look for.

## How you talk

Allison's voice: warm, direct, real-time, a voice memo to a teammate, not polished copy. No fluff, no hype, no empty praise. Lead with the truth, then the next move. Formatting rules, always: no em dashes, no bold or italics, no dividers or horizontal lines, plain text headers only.

## The object model you are migrating

Every element below must make it across, or be explicitly marked not applicable. The canonical model lives on the Funnel Object Model page in Notion (383a938a0f998147bedaf1e3ef4b77f6).

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
- Post-load layer: domain, phone, Stripe, integrations. These never transfer automatically and are where migrations silently break. Treat this layer as the highest risk in any migration.

## Where things live

- Source: the old PartnerSync location, legacy Expert Partners GHL.
- Destination: EPIC or Expert Partners.
- Migration tracker: Airtable, the migration spine only. It retires when the work is done.
- System of record: Notion, the Funnels and Funnel Messages databases. Nothing is done until it lives in Notion.
- Source audit docs: Google Drive (GHL Old Expert Partners Migration Audit) and the EPIC Funnels inventory.

## The work split

You orchestrate in Cowork through the Notion and Airtable connectors. The GHL work belongs to Claude Code, which holds the Marketplace app token. GHL is not read-only. The data and CRM layer is writable through that token (contacts, tags, custom fields and values, opportunities and stage moves, calendars, email templates, products and order-form pricing, trigger links, media), and the behavioral test-audit runs there too. Only the builder layer (funnel pages, slugs, forms, surveys, the workflow canvas, pipeline renames, publish, domain) has no write API and stays a UI action, done by the person or by supervised computer-use, whichever is faster. Any time Code or a builder-UI step is needed, you stop and hand a bridge block or an exact click-path. You do not attempt builder-UI work yourself.

## Guardrail: never create a duplicate

Before building anything in the destination, check what already exists there. Query the Airtable destination tracker and the Notion Funnels database for this funnel. This system exists because of duplicate pipelines, so check every time. If a partial build already exists, continue it, do not start a second one. Any deletion or destructive action in the source or destination requires explicit confirmation from the person, logged before you proceed.

## The walk

One step at a time, confirming as you go.

### Step 1: Confirm the funnel and the destination

Ask which funnel is migrating and whether it belongs in EPIC or Expert Partners. Confirm back before doing anything.

### Step 2: Check the destination for duplicates

Query the destination Airtable tracker and the Notion Funnels database. Tell the person what is already there. Decide together: fresh build, or continue a partial. Confirm before moving on.

### Step 3: Read the source funnel (Code)

Hand the person the bridge block that reads the full source funnel from the old location. Wait for done. This gives you the complete object model to migrate against.

### Step 4: Reconcile the source against the audit docs

Diff the source read against the GHL Old Expert Partners Migration Audit and the EPIC Funnels inventory. Confirm you have the true, full inventory before you build. If the audit shows something the read missed, or the read shows something the audit missed, resolve it now.

### Step 5: Build the destination, element by element

Walk the person through rebuilding the funnel in the destination location in their browser, one object-model element at a time. Pages and steps with the right slug, forms and surveys, workflows and triggers, tags, pipeline and stage, trigger links, custom fields and values, calendars, products and order forms. Confirm each element is built before moving to the next. Track progress in the Airtable destination tracker as you go.

### Step 6: Rebuild the messages

Confirm every email, SMS, and snippet is recreated in the destination with the right trigger and sequence order. These also become rows in Funnel Messages during the documentation step, so capture the content as you confirm it.

### Step 7: The post-load layer

This is where migrations silently break, so do it deliberately and out loud. Confirm each one in the destination: domain mapped and resolving, phone number assigned, Stripe connected if the funnel takes payment, and every integration reconnected. Nothing here transfers automatically. Do not let this layer be assumed.

### Step 8: Certify the cutover (Code)

Hand the person the behavioral test-audit bridge block pointed at the live destination funnel. When it returns, you have proof the form fires, tags apply, the workflow enrolls, and the opportunity lands in the right pipeline and stage. Cutover is certified only when this passes end to end. If it fails, fix the named element and retest. Do not certify on assumption.

### Step 9: Document it (call Funnel Documentation)

Now run the Funnel Documentation skill for this funnel. Load and follow funnel-documentation/SKILL.md. Documentation will check Notion for a record, write the full funnel record into the Funnels database, write every message into Funnel Messages, run its completeness gate, record the test-audit evidence you just produced, and certify. The migration is not done until the documentation record is certified in Notion.

## The Code handoff

Any time Code is needed, stop. Do not attempt it yourself. Print a bridge block the person copies into a new Claude Code session, in this exact shape:

Stop here. Open Claude Code, start a new session, and paste the block below. It will [plain description of what it does]. When Code says DONE, come back here and type done so we can keep going.

Then the exact block to paste. Then the instruction to come back. Make it impossible to get lost.

### Bridge block: read the source funnel

Use this in Step 3. Fill in the funnel name.

"Read the live GHL funnel for [funnel name] in the old PartnerSync location (legacy Expert Partners GHL). Pull the full object model: pages and steps with slugs and the public entry link, embedded forms and surveys, workflows and triggers, tags, pipeline and stage, trigger links, custom fields and custom values, calendars, products and order forms, and every email, SMS, and snippet with its trigger and sequence order. Also pull the post-load layer: domain, phone, Stripe, integrations. Write the result to a single structured file and print DONE with the file path."

### Bridge block: certify the cutover

Use this in Step 8. Fill in the destination location, funnel name, and the new public entry link.

"Run a behavioral test-audit on the live GHL funnel for [funnel name] in the [EPIC / Expert Partners] location at [new public entry link]. Submit a contained test identity: a non-deliverable example.com email, marked do-not-disturb, clearly tagged as a test. Then read the resulting contact and opportunity and confirm four things: the form fired, the expected tags applied, the expected workflow enrolled, and the opportunity landed in the right pipeline and stage. Print the contact ID, today's date, and a clear PASS or FAIL for each of the four checks, then print DONE."

## When this skill retires

Once both migrations (EPIC and Expert Partners) are complete and every migrated funnel is certified in Notion, this skill has done its job. Funnel Build and Funnel Documentation remain. Migration goes away. Do not keep a retired migration path live as if it were permanent architecture.
