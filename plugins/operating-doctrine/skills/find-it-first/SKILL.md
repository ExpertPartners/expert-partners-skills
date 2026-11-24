---
name: find-it-first
description: |
  If AI can find it, we don't ask the client. Company policy for Expert Partners and AG Luxury (Decision Log 2026-11-23 and 2026-11-24). Always on for every AI that touches a client, prospect, member, buyer or seller. Fires before any question, form, intake, fact sheet, interview, onboarding step or email asks a client for information. Search first (their website, socials, reviews, public production, brokerage, public records, MLS and market data, property records, and everything we already hold in the CRM, GoHighLevel, the brains and call recordings), present what was found as a reveal for the client to confirm or correct, then ask only for what no source holds. Also fires when building or editing any client-facing form, script or sequence. Inherits operating-doctrine.
allowed-tools: []
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-11-24 (Decision Log 2026-11-23, If AI can find it, we don't
# ask the client, Expert Partners company policy, extended to AG Luxury
# 2026-11-24). A simple CEO directive skill, so it ships with no proving line.
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "if AI can find it, we don't ask"
---

# Find It First

One job. No AI asks a client for something AI can find. It finds it, shows the client what it found, and asks only for what is left.

Source: Decision Log 2026-11-23, If AI can find it, we don't ask the client, Expert Partners company policy, extended to AG Luxury on 2026-11-24. It grew out of the Authority Engine onboarding decision of 2026-11-23. The Decision Log wins wherever this differs.

Allison's words. "We should never, never, never ask somebody we can find. People don't know what they can find, so we show them that we can find it."

## Trigger

This is doctrine, so it is always on for anyone who touches a client. It fires hardest at these moments.

1. An AI is about to ask a client, prospect, member, buyer or seller a question.
2. An AI is building or editing a form, fact sheet, intake, interview script, onboarding step, email or text sequence that collects client information.
3. A human on the team asks an AI to draft a request for information from a client.

## What to do when it fires

1. Search first. Check every source you are allowed to reach, and stop at nothing short of what a sharp researcher would find in a few minutes.
   1. What we already hold. The CRM and GoHighLevel record, past forms, the owning brain, and call recordings and transcripts.
   2. The client's own public footprint. Their website, social profiles and follower counts, Google reviews, YouTube, press and podcasts.
   3. Public business data. Public production and sales history, brokerage and brand guidelines, licensing, team members listed publicly.
   4. Public market and property data. MLS and public sales and inventory data, property and tax records, HOA, school zones, listing history.
2. Pre-fill everything you found. Every field you can fill is filled before the client sees it.
3. Present it as a reveal. "Here's what we already found about you. Confirm or fix anything that's off." The reveal is the point. Clients do not know what is findable, so showing them is the proof of what we do.
4. Ask only what is left. Private numbers, preferences, budget, goals, decisions, and anything no source holds. Ask those once, plainly, in one place.
5. Say where each found item came from when the client might wonder, so they can correct the source and not just the field.

## Never

- Ask a client for something an available source holds.
- Send a blank form when a pre-filled one could be built.
- Ask the same thing twice across forms, emails or calls.
- Treat a found item as final. The client always gets to confirm or correct it.

## Test cases

1. An AI drafts an onboarding form for a new Authority Engine client. Pass when website, socials, follower counts, reviews and public production arrive pre-filled and the form asks only for private items such as CRM size, budget tier and team names.
2. An AG Luxury seller intake is being built. Pass when tax value, HOA, school zones, square footage and listing history arrive pre-filled from public records and the seller is asked only about timing, motivation and preferences.
3. A team member asks an AI to email a client for their brokerage brand guidelines. Pass when the AI finds the guidelines itself and sends them for the client to confirm.
4. Nothing can be found for a field. Pass when that field, and only that field, is asked.
