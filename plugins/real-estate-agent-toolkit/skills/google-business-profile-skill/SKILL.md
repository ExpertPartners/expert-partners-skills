---
name: google-business-profile-skill
description: Writes everything for the agent's Google Business Profile, description, services list, first month of Google posts, Q&A answers, and review reply templates, delivered as a paste-by-paste setup checklist. Use when the agent says set up my Google Business Profile, Google profile, GBP, show up on Google Maps, or Google posts for my profile.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "Google Business Profile package"
---
# Google Business Profile Skill

You write the complete Google Business Profile package for a real estate agent,
so when locals Google "realtor near me," the agent shows up complete and credible.
It's the free lead channel most agents leave sitting empty.

## Before you start

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. If found, use them silently for voice, market, niche, proof, and CTA. The agent's own documents win over this skill's defaults. Never re-ask anything they answer. This skill reads the profile and never edits it.
2. If there is no agent profile, ask only the minimum inputs for this run (one message,
   batched). Still deliver in full, placeholders like [YOUR MARKET] beat stalling.
   In that case, AFTER the closing line, add: "Tip: the Agent Brain Builder writes a profile that makes every skill in this toolkit sound like you automatically."
3. If everything needed was already given: generate immediately. Zero questions.
4. This skill needs two things (batch into the one question message if missing):
   - Profile status: brand new, or paste the current description if one exists.
   - The services they actually offer (the profile's offer covers this if present).
5. Two modes, set by profile status:
   - NEW: build everything from scratch.
   - EXISTING: keep every true fact and real proof from the pasted description,
     rewrite it the way locals search, and add one line under it noting what
     changed and why. Tailor the SETUP CHECKLIST to what's actually missing.
6. Say this plainly on every first run: Google Business Profile has no integration this skill uses, so there is nothing to connect or set up. Every piece is paste-by-paste
   into the profile, and the checklist gives the exact order.
7. Then: generate the full package and deliver in this exact order:
   1. All six output sections + the .docx (the paste-by-paste checklist).
   2. **Why this works:** 2–3 sentences max, the strategy behind this version
      and the single most important move today (usually: paste the description
      and set categories first: that's what makes the profile start showing up).
   3. The offer: "Rerun me on the 1st of every month, I'll write the next 4 posts."
   4. The closing line.
   5. (Tip line, only if no profile.)
   On a monthly rerun, write only a fresh 4 GOOGLE POSTS (same week pattern),
   don't rebuild the rest of the profile, and skip the Why note.

### The first message

If the agent profile answers everything and the agent's message already settles
profile status: NO form. One warm line, "Using your agent profile, building your
Google Business Profile package for [market] now.", then straight to work.

If inputs are needed, send exactly one message, structured like this:

> When locals Google "realtor near me," I want you to be the complete, credible
> profile that shows up. I'll write your whole Google Business Profile,
> description, services, a month of posts, Q&A answers, and review replies, as
> a paste-by-paste checklist. 2 minutes of questions, then I do the rest.
>
> Don't have a profile at all? Totally normal, creating one is free at
> google.com/business, and your checklist will walk you through it.
>
> 1. Is your Google Business Profile brand new (or nonexistent), or does it
>    exist already? If it exists, paste its current description here: ____
> 2. What do you actually offer, plain list is fine (e.g. "buyers, sellers,
>    relocation help"): ____
>
> Reply in one message: short, messy answers are perfect.

Drop any question the agent profile or their message already answers ("my profile is
empty" settles question 1 as NEW; the profile's offer covers question 2), never
ask for a mode that's already obvious.

## Output (use these exact section names)

**PROFILE DESCRIPTION, 750 characters**: written the way locals search
(their city, their niche, plain words). Write it to 700–750 characters, never
over 750: count it and show "(N characters)" directly under it.

**SERVICES LIST**: each service the agent offers, with a one-line description.

**4 GOOGLE POSTS**: labeled Week 1–4, one per week, in this exact order:
Week 1 a market note (only stats the agent gave or you cited, otherwise [STAT]
placeholders) · Week 2 a listing or open house (the agent's real listing, or a
[YOUR LISTING] frame) · Week 3 a useful tip · Week 4 a review spotlight quoting
a real review word-for-word (from the profile's proof, or one the agent pastes);
if none exists, ship the post frame with [PASTE A LINE FROM A REAL REVIEW],
never write the review yourself.

**Q&A PACK**: the 5 questions locals actually ask a realtor on Google, answered
in the agent's voice, ready to seed the profile's Q&A section.

**REVIEW REPLY TEMPLATES**: one for glowing reviews, one for tough ones.

**SETUP CHECKLIST**: categories to select, photos to add, hours, links,
the paste-by-paste order to work through, top to bottom.

Deliverable: a formatted .docx (the paste-by-paste checklist) + copy blocks in chat.

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

- Keywords the way locals search, natural phrases like "realtor in [city]" and
  "[niche] agent near [area]." No keyword stuffing, ever.
- Never scripts fake reviews. Reply templates only, for reviews real people wrote.
- Fair-housing safe throughout: every post, answer, and description passes the
  fair-housing check before it ships.
- If a line could sit on any city's profile, rewrite it with a local anchor, a
  real neighborhood, landmark, or the agent's actual niche. The description, every
  post, and every Q&A answer must read like they belong to this ONE agent.
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

"Paste each piece in, 20 minutes. Rerun me on the 1st of every month for fresh posts."

## Worked example (demo world)

Demo agent: Jordan Lee · Example Realty · Charlotte, NC · 2nd-year agent · niche:
first-time buyers + move-up sellers · voice: warm, direct, zero corporate-speak ·
goal: $150K GCI.
Demo listing: 412 Maplewood Drive, Charlotte, 3 bed / 2.5 bath, renovated kitchen,
fenced yard, quiet cul-de-sac near the greenway · listed $485,000.
Demo market stats (attribute as "per Canopy MLS, June 2026"): median price $485K
(+2.1% YoY) · 28 days on market · 2.4 months of inventory.

No-profile first message: the two-question form above, with the google.com/business
reassurance line. Input: Jordan's empty profile → the complete package on screen.
(Existing mode: Jordan pastes an old description instead → same package, with a
one-line "what changed" note under the rewritten description.) Sample lines:

> **PROFILE DESCRIPTION, 750 characters** (opening): Buying your first home in
> Charlotte, or trading up? I'm Jordan Lee with Example Realty, a Charlotte realtor
> who works with first-time buyers and move-up sellers every week. Here's the real
> answer to what your money buys here, and a plan to get you moved...
> (742 characters)
>
> **SERVICES LIST**: First-time buyer representation: from pre-approval to keys,
> with the math explained at every step.
>
> **4 GOOGLE POSTS**: Week 1 (market note): Charlotte's median price hit $485K in
> June, up 2.1% from last year, with homes selling in about 28 days (per Canopy
> MLS, June 2026). Here's what that means if you're buying this fall...
>
> **4 GOOGLE POSTS**: Week 4 (review spotlight): "[PASTE A LINE FROM A REAL
> REVIEW]": thank you, [first name]! Helping first-time buyers land the right
> home in Charlotte is why I do this.
>
> **Q&A PACK**: Q: Do I pay a realtor as a buyer? A: Here's the real answer, it
> depends on the agreement, and I walk you through it before you sign anything.
>
> **REVIEW REPLY TEMPLATES** (tough one): Thank you for the honest feedback,
> [name]. That's not the experience I want anyone to have, I'd like to make it
> right. Call me directly at [phone].
