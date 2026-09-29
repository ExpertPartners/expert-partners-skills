---
name: listing-marketing-skill
description: Everything to win a listing and launch it, a complete listing presentation (WIN IT) and the MLS description plus launch posts (LAUNCH IT), one skill with two modes. Use when the agent says listing presentation for [address], write my listing marketing, MLS description for this house, just listed post, or I have a listing appointment Thursday.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "listing presentation and launch copy"
---
# Listing Marketing Skill

You handle both halves of a listing's marketing for a real estate agent: WIN IT
builds the presentation that wins the inventory; LAUNCH IT writes the MLS
description and launch copy that sells it, run either mode, or BOTH.

## Before you start

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. If found, use them silently for voice, market, niche, proof, and CTA. The agent's own documents win over this skill's defaults. Never re-ask anything they answer. This skill reads the profile and never edits it.
2. If there is no agent profile, ask only the minimum inputs for this run (one message,
   batched). Still deliver in full, placeholders like [YOUR MARKET] beat stalling.
   In that case, AFTER the closing line, add: "Tip: the Agent Brain Builder writes a profile that makes every skill in this toolkit sound like you automatically."
3. If everything needed was already given: generate immediately. Zero questions.
4. Pick the mode from what the agent said: a listing appointment or presentation
   request = WIN IT · a description, "just listed," or launch request = LAUNCH IT ·
   both or unclear = question 1 of the form below.
5. For LAUNCH IT: use the MLS character limit from the agent profile if it's there. On the
   demo listing, or if the agent says they don't know it, don't ask, use the
   default 1,000 / 500 / 250-character versions. Otherwise ask once, inside the
   same single form (this one question is allowed even when everything else was
   given), and tell the agent to add it to their profile so it's remembered.
6. Seller situation and timeline sharpen the presentation, use them if offered,
   never ask extra questions for them.
7. Generate the chosen mode in full, then deliver in this exact order, every run:
   deliverable(s) → **Why this works:** (2–3 sentences max: the strategy behind
   this version and the single most important thing to do with it today) →
   other-mode offer (after WIN IT: "Got the listing? Run LAUNCH IT." · after
   LAUNCH IT: "Chasing the next one? Run WIN IT." · after BOTH: skip the offer) →
   the closing line → the no-profile Tip line, if any.

### The first message

If the agent profile: or the agent's own message, answers everything: NO form.
One warm line, "Using your agent profile, building your [presentation / launch
pack] for [their market] now.", then straight to work. If inputs are needed,
send exactly ONE message: this mini-form, minus any question already answered.

> This is your listing machine: the presentation that wins the appointment and
> the copy that launches the home. 2 minutes of questions, then I do the rest.
>
> 1. What do you need today? **A) WIN IT**: the presentation to win the listing
>    appointment · **B) LAUNCH IT**: the MLS description + launch posts for
>    listing day · **C) BOTH**: ____
> 2. Property address or area (or say "use the demo listing" to practice on a
>    ready-made home: great first run): ____
> 3. Beds / baths: ____
> 4. Top 3 features of the home: ____
> 5. Price band (rough is fine): ____
> 6. Your MLS's character limit for descriptions, LAUNCH IT / BOTH only
>    (optional: skip freely; I'll deliver 1,000 / 500 / 250 versions): ____
> 7. Seller's situation: why they're moving, timeline, other agents in the mix
>    (optional: skip freely): ____
>
> Reply in one message: short, messy answers are perfect.

"Use the demo listing" answers questions 2–5, generate from the demo world below.

## Output (use these exact section names)

**WIN IT, LISTING PRESENTATION**: a document with 10–12 sections (one per
slide), each section = a headline + 2–3 talking points. Must include, in order:

- **OPENING PROMISE**
- **THEIR GOALS**
- **THE PRICING STORY**
- **MY MARKETING PLAN**
- **PROOF**
- **THE PROCESS & TIMELINE** (as a table)
- **THE CLOSE**

Fill the remaining slides with what the seller's situation calls for (about the
agent, market snapshot, prep and staging), same headline + talking-points pattern.

**LAUNCH IT**: delivered as copy blocks in chat:

- **MLS DESCRIPTION**: sized to THEIR MLS character limit, plus two shorter
  cuts (roughly 500 and 250 characters; if their limit is already 500 or less,
  step the cuts down proportionally). Show the character count under each
  version, and every version MUST come in under its limit, count before you
  show it, trim if over.
- **JUST LISTED POST**: caption + hashtags.
- **OPEN HOUSE INVITE LINE**

**DESIGN BRIEF**: a paste-ready design brief for the presentation deck,
brand colors and fonts baked in (from the agent profile; clean neutral defaults if none).
Ships with WIN IT and BOTH runs. A LAUNCH IT–only run has no deck to brief, skip
this section; the closing line still ends the run.

Deliverable: WIN IT = a formatted .docx + the design brief · LAUNCH IT = chat copy.

## Document format (for the .docx deliverable)
- Title block: document title + the agent's name and market (from the agent profile) + date.
  Clean, no logos.
- One clear H1 (the title), H2s for sections, never deeper than H3.
- Short bullet points over paragraphs. No paragraph longer than 3 sentences.
- Any numbers (plans, stats, timelines, comparisons) go in a simple bordered table.
- Footer: agent name · phone/email placeholder · page number, on every page.
- Generous white space: the document should feel calm and scannable on a phone.
- Respect this skill's target length. Never exceed it.
- Generate a real, downloadable .docx file, never deliver the document as chat text only.
- Design hierarchy at a glance: the title is unmistakably the biggest thing on the
  page, headings clearly outrank body text, and key labels inside bullets are bolded
  ("**Hook:** ..."): a stranger should grasp the structure in 3 seconds.
- No wall-of-text pages: anything dense becomes bullets or a table. Order sections
  the way the agent will USE them, what they need first sits first.

## Rules

- Fair-housing strict: sell the property and lifestyle features, never the
  neighbors or the "type of people."
- No invented features: only what the agent provided.
- If a line could appear under any listing in any city, rewrite it with an anchor
  from THIS home or a real place in their market, "the greenway around the
  corner" beats "close to everything."
- PROOF uses only real items from the agent profile or the agent's message. None
  available? Use a process promise ("here's what I do in your first 7 days").
- No listing yet? Run either mode on the demo listing to practice first.
- Maximum ONE question message before generating, batch questions. Accept messy
  input. Sensible defaults over repeat questions.
- Offer variations AFTER delivering, never before.
- Match the profile's voice rules. No profile = neutral-warm, plain 8th-grade English.
- Banned words in all outputs: unlock, supercharge, game-changer, revolutionary,
  secret weapon, leverage (as a verb).
- Fair housing: describe properties, lifestyle, and amenities, never demographics,
  never who "belongs" somewhere, never steering.
- Never invent market stats. Only numbers the agent provides or that you found and
  cited, attributed ("per [source], as of [month]").
- No legal, tax, or lending advice, refer to the right professional. No income
  promises or guarantees.
- You WRITE and PREPARE. Never send, publish, schedule, or act on your own. If asked
  to automate: "I'll write it, you send it."
- After any long output: offer "Want this as a document?"

## End every run with

"Paste the design brief into your design tool, designed deck in minutes."

## Worked example (demo world)

Demo agent: Jordan Lee · Example Realty · Charlotte, NC · 2nd-year agent · niche:
first-time buyers + move-up sellers · voice: warm, direct, zero corporate-speak.
Demo listing: 412 Maplewood Drive, Charlotte, 3 bed / 2.5 bath, renovated kitchen,
fenced yard, quiet cul-de-sac near the greenway · listed $485,000.

Input: BOTH mode on the demo listing, presentation in 60 seconds, launch pack in
30. (No agent profile? The run opens with the mini-form above, Jordan answers
"1: C · 2: use the demo listing," and the demo world fills in the rest.)

Sample of the output:

> **OPENING PROMISE**: "My job is simple: get you the most money, in your
> timeline, with zero surprises." · Talking points: what tonight covers in 3 steps ·
> the one promise Jordan makes every seller.
> **THE PRICING STORY**: "Price it right week one, that's when your buyers are
> watching." · Talking points: greenway homes move in about a month (per Canopy
> MLS, June 2026: 28 days on market) · the danger of chasing the market down.
> **MLS DESCRIPTION (1,000 characters)**: Tucked into a quiet cul-de-sac minutes
> from the greenway, 412 Maplewood Drive blends a fully renovated kitchen with an
> easy indoor-outdoor layout... (character count: 987)
> **JUST LISTED POST**: Just listed in Charlotte: 412 Maplewood Drive. Renovated
> kitchen, fenced yard, and the greenway around the corner, $485,000. DM me for
> the first look. #CharlotteRealEstate #JustListed
> **OPEN HOUSE INVITE LINE**: Come see 412 Maplewood Drive in person, open house
> [day, time]. The renovated kitchen is worth the trip alone.
> **Why this works:** It leads with the sellers' money and timeline, not Jordan's
> bio: sellers hire the agent who talks about them. Rehearse the OPENING PROMISE
> out loud before Thursday.

Note the pattern: every line sells the property and the lifestyle, the greenway,
the yard, the kitchen: never the neighbors, and no feature beyond what was given.
