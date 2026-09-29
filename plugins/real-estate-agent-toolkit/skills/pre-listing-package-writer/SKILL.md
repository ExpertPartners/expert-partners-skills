---
name: pre-listing-package-writer
description: Writes what the seller reads before the listing appointment (the intro email plus a one-page "how I sell homes" document that pre-sells the agent). Use when the agent says pre-listing package, I have a listing appointment, what do I send first, send something before my listing appointment, pre-appointment email, or a listing appointment just got booked and they ask what to send the seller.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "pre-listing email and one-pager"
---
# Pre-Listing Package Writer

The moment a listing appointment gets booked, you write what the seller reads BEFORE
the agent arrives: an intro email and a one-page pre-listing document that pre-sell
the agent, so the appointment starts half-won.

## Before you start

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. If found, use them silently for voice, market, niche, proof, and CTA. The agent's own documents win over this skill's defaults. Never re-ask anything they answer. This skill reads the profile and never edits it.
2. If there is no agent profile, ask only the minimum inputs for this run (one message,
   batched). Still deliver in full: placeholders like [YOUR MARKET] beat stalling.
   In that case, AFTER the closing line, add: "Tip: the Agent Brain Builder writes a profile that makes every skill in this toolkit sound like you automatically."
3. If everything needed was already given: generate immediately. Zero questions.
4. Required inputs: appointment day + the property/area + anything known about the
   seller (one line is enough). From the agent profile: USP, proof, process, voice, contact info.
5. One message of context → both pieces. Delivery order, always: the email (copy
   block) + the document (.docx) → **Why this works:** a 2–3 sentence note on the
   strategy (why this package wins the appointment before it starts + the one thing
   to do with it today: send it now, the day it's booked) → offer: "Want the
   printable version to bring as a leave-behind too?" → the closing line (→ the
   no-profile Tip last, if it applies). If they say yes to the leave-behind: the SAME
   one-pager, print-ready with a signature line added, never new content, never a
   second design.

### The first message

**If the agent's message (plus the agent profile) already covers the appointment day, the
property/area, and the seller:** no form. One warm line, "Using your agent profile,
building your pre-listing package for [market] now," then straight to work.

**If anything is missing**, send exactly this mini-form (one message, these three
questions only: drop any question their message or the agent profile already answered):

> A booked listing appointment: perfect timing. I'll write the intro email plus the
> one-page "how I sell homes" document the seller reads before you arrive, so the
> appointment starts half-won. Two minutes of questions, then I do the rest.
>
> 1. Appointment day: ____
> 2. The property or area (address or neighborhood, either is fine): ____
> 3. One line about the seller, anything you know ("downsizing, interviewing two
>    other agents" is plenty): ____
>
> Reply in one message: short, messy answers are perfect.

## Output (use these exact section names)

**THE INTRO EMAIL**: confirms the appointment, sets expectations, one proof point,
warm close. If the agent profile holds no proof, the "proof point" becomes ONE service
commitment the agent controls (see PROOF below), never an invented stat.

**THE PRE-LISTING DOCUMENT** (one page), with these sections:

- **HOW I SELL HOMES** (5 steps), the agent's process from the agent profile, or a clean
  standard 5-step process if the agent profile has none.
- **WHAT MAKES ME DIFFERENT** (from the agent profile), the USP in the agent's own words.
- **PROOF**: real deals, reviews, wins from the agent profile only. Thin track record: use
  whatever real proof exists (even one review counts). No proof at all: fill the
  section with 2–3 service commitments the agent controls (response time, data behind
  every pricing recommendation, communication cadence), clearly framed as commitments,
  never dressed up as results, never padded, never invented.
- **WHAT WE'LL COVER AT THE APPOINTMENT**: a short agenda that sets expectations.
- **HOW TO PREPARE** (3 things), three simple things the seller can do before
  the agent arrives.

One-page budget (hard limit: check before delivering): each HOW I SELL HOMES step
one line · WHAT MAKES ME DIFFERENT max 3 bullets · PROOF max 3 bullets · agenda 4–5
bullets · each HOW TO PREPARE item one line. If it won't fit one page, cut words,
never cut a section.

Deliverable: the document as a formatted .docx + the email as a copy block in chat.

## Document format (for the .docx deliverable)
- Title block: document title + the agent's name and market (from the agent profile) + date.
  Clean, no logos.
- One clear H1 (the title), H2s for sections, never deeper than H3.
- Short bullet points over paragraphs. No paragraph longer than 3 sentences.
- Any numbers (plans, stats, timelines, comparisons) go in a simple bordered table.
- Footer: agent name · phone/email placeholder · page number, on every page.
- Generous white space: the document should feel calm and scannable on a phone.
- Respect this skill's target length. Never exceed it.
- Generate a real, downloadable .docx file; never deliver the document as chat text only.
- Design hierarchy at a glance: the title is unmistakably the biggest thing on the
  page, headings clearly outrank body text, and key labels inside bullets are bolded
  ("**Hook:** ..."): a stranger should grasp the structure in 3 seconds.
- No wall-of-text pages: anything dense becomes bullets or a table. Order sections
  the way the agent will USE them: what they need first sits first.

## Rules

- Proof only from the agent profile: no invented stats, deals, or awards.
- If the email or one-pager could go to any seller in any city unchanged, rewrite it:
  the seller's one line and the property/area must visibly shape the email opening,
  the proof point chosen, and the appointment agenda.
- Use the seller line strategically: "interviewing other agents" sharpens WHAT MAKES
  ME DIFFERENT; "downsizing" or another life event warms the tone and the agenda.
  The package should read like it was written for this seller, because it was.
- No market promises: never promise a sale price, an over-asking amount, days to
  sell, or a number of offers. "I'll get you $50K over asking" and anything in that
  class is banned. Commitments about the agent's own actions are fine.
- Maximum ONE question message before generating: batch questions. Accept messy
  input. Sensible defaults over repeat questions.
- Offer variations AFTER delivering, never before.
- Match the profile's voice rules. No profile = neutral-warm, plain 8th-grade English.
- Banned words in all outputs: unlock, supercharge, game-changer, revolutionary,
  secret weapon, leverage (as a verb).
- Fair housing: describe properties, lifestyle, and amenities; never demographics,
  never who "belongs" somewhere, never steering.
- Never invent market stats. Only numbers the agent provides or that you found and
  cited, attributed ("per [source], as of [month]").
- No legal, tax, or lending advice: refer to the right professional. No income
  promises or guarantees.
- You WRITE and PREPARE. Never send, publish, schedule, or act on your own. If asked
  to automate: "I'll write it, you send it."
- After any long output: offer "Want this as a document?"

## End every run with

"Send this the day the appointment gets booked. Run the Listing Marketing Skill for
the presentation itself."

## Worked example (demo world)

Demo agent: Jordan Lee · Example Realty · Charlotte, NC · 2nd-year agent · niche:
first-time buyers + move-up sellers · voice: warm, direct, zero corporate-speak ·
goal: $150K GCI.
Demo leads: Mike & Dana (sellers, interviewing 3 agents Thursday).

Demo input: Listing appointment booked for Thursday → package sent Monday.
(With no agent profile, Jordan would first get the three-question mini-form from "The
first message" above; his one-message reply produces everything below.)
Context: Mike & Dana, move-up sellers, home near the Charlotte greenway. Jordan's
profile holds no closed-deal stats yet: this is the thin-track-record path, so note how
nothing gets invented.

Sample of the finished package:

> **THE INTRO EMAIL**
> Subject: Thursday's confirmed, here's what to expect
> Hi Mike and Dana, looking forward to Thursday. Before I come by, I put together a
> one-pager on exactly how I sell homes; it's attached, and it takes two minutes to
> read. One thing you can hold me to: every pricing recommendation I make comes with
> the data behind it, so you'll see the why, not just the number. The last section of
> the one-pager lists three quick things that make Thursday easier: that's all the
> prep you need. See you Thursday.
> Jordan
>
> **THE PRE-LISTING DOCUMENT** (opening lines)
> **HOW I SELL HOMES**: 1. Price it with real data, together. 2. Prep and stage the
> home so it shows its best. (...steps 3–5 follow the same pattern, one line each)
> **PROOF**: What you can hold me to: 1. Every pricing call backed by data you'll
> see. 2. You hear from me within hours, never days. 3. One point of contact, me,
> from listing day to closing.
> **HOW TO PREPARE**: 1. List any updates you've made to the home. 2. Find your
> survey and utility info if handy. 3. Write down your ideal moving timeline.
>
> **Why this works:** Mike & Dana are interviewing three agents: this package makes
> Jordan the only one they've already "met" before Thursday, and the data-backed
> pricing commitment answers the question every seller walks in with. Send it today,
> not Wednesday night: first professional impression wins.
