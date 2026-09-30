---
name: open-house-kit-writer
description: Create a complete, paste-ready residential real estate open house kit from one listing or property brief. Use when an agent asks for an open house kit, open house marketing, event promotion, flyer copy, sign-in language, neighbor invitations, host scripts, setup checklists, attendee follow-up, or a seller recap. Built for real estate agents who need one coordinated package before, during, and after an open house without inventing property facts, market data, or client information.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "open house kit from one listing"
---

# Open House Kit Writer

Turn one listing into a complete open house operating kit so the agent does not have to write each piece separately.

## Before you start

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. The agent's own documents win over this skill's defaults. If found, use their voice, market, brokerage, CTA, links, and contact details silently. Never re-ask for information already present.
2. Treat a listing URL, MLS remarks, property flyer, or pasted property brief as source material. Use only facts actually supplied or verified. Never invent features, upgrades, prices, school information, market statistics, seller circumstances, or offer activity.
3. If the user already supplied enough to identify the property and open house date/time, generate immediately. Do not stop for optional details.
4. If essential inputs are missing, ask once in one batched message. Accept incomplete or messy answers, then build the kit with clearly marked placeholders rather than asking again.
5. Write and prepare only. Do not publish, schedule, message leads, change CRM records, or create ads unless the user separately asks and an appropriate authorized tool is available.

## The one question message

Use this only when essential inputs are missing:

> I’ll turn one listing into the complete open house kit: promotion, flyer copy, sign-in language, host talk track, setup checklist, follow-up, and seller recap.
>
> Send whatever you have in one reply:
> 1. Property address or area + listing link/remarks if available: ____
> 2. Open house date and time: ____
> 3. Best 3–5 property features or selling points: ____
> 4. Your preferred CTA or link, if any: ____
>
> Short, messy answers are perfect. If something is missing, I’ll use a placeholder instead of slowing you down.

## Build the kit in this order

### 1. OPEN HOUSE SNAPSHOT

Give the agent a compact control block:

- Property
- Date and time
- Host
- Primary CTA
- Top 3 property talking points
- Any missing facts or approvals that must be filled before use

Keep this operational, not promotional.

### 2. PROMOTION COPY

Create all of the following:

- **Announcement post**: 3–5 days before the event
- **Tomorrow reminder**: one short social post
- **Today post**: one short social post
- **Story/Reel caption**: concise, conversational, location-forward
- **Neighbor invitation**: short text or email the agent can send to nearby homeowners or sphere contacts

Every version must include the actual date/time and a clear next action. Do not use fake urgency, fake scarcity, or unsupported claims such as “won’t last.”

### 3. PROPERTY FLYER COPY

Write paste-ready copy for a one-page flyer:

- Headline
- One-sentence positioning line
- 4–6 factual feature bullets
- Short property description, about 80–130 words
- Open house date/time block
- Agent CTA and contact placeholder if contact details are unavailable

If the property is luxury, elevate the tone without becoming vague or ornamental. If it is not luxury, keep it clean and useful rather than pretending it is.

### 4. SIGN-IN COPY

Provide a simple visitor sign-in structure with only useful fields:

- Name
- Email
- Mobile
- “Are you currently working with a real estate agent?”
- “What would be most helpful after your visit?” with neutral choices such as property details, similar homes, financing contact, home-value conversation, or no follow-up

Then add:

`[USE YOUR BROKERAGE-APPROVED PRIVACY / CONSENT LANGUAGE HERE]`

Never invent legal consent language or tell the agent that a generic disclosure guarantees TCPA, state privacy, or brokerage compliance.

### 5. HOST TALK TRACK

Write a natural, low-pressure talk track with these moments:

1. **Welcome**: greet the visitor and let them orient themselves.
2. **Opening question**: learn what brought them in without interrogating them.
3. **Property bridge**: mention 1–2 relevant features based on what they say.
4. **Needs discovery**: ask whether they are actively buying, casually looking, or gathering information.
5. **Representation check**: politely determine whether they are already represented.
6. **Next-step offer**: offer one useful next step, not a hard close.
7. **Exit**: thank them and confirm only the follow-up they requested.

Keep the language human and easy to say out loud. Never coach the agent to pressure visitors into signing an agency agreement at the door.

### 6. OPEN HOUSE SETUP CHECKLIST

Create a practical checklist grouped under:

- 24 hours before
- 60 minutes before
- At the door / welcome area
- Property walkthrough
- Marketing materials
- Tech and chargers
- Safety and security
- Before leaving

Include common items such as directional signs, sign-in device or sheets, property flyers, business cards, chargers, water, pens, lights, temperature check, valuables/security awareness, and seller-approved access instructions. Do not prescribe anything that conflicts with brokerage, MLS, HOA, building, or seller rules.

### 7. FIVE-TOUCH FOLLOW-UP

Write five short follow-ups. Each one must be useful and progressively lighter, never repetitive.

Default cadence:

1. **Same day**: thank-you + answer/offer the most relevant property information.
2. **Next morning**: useful follow-up based on the visitor’s stated interest.
3. **Day 3**: offer comparable or alternative homes, or a seller/home-value conversation if that is what they requested.
4. **Day 7**: brief check-in with a concrete reason to respond.
5. **Day 14**: permission-based close-the-loop message.

If the visitor is represented, respect that relationship. Do not write follow-up that solicits them away from their agent. If their consent or requested contact channel is unclear, flag it rather than assuming permission.

### 8. SELLER RECAP

Create a short post-open-house recap the listing agent can personalize for the seller:

- Number of visitors, only if supplied
- Common feedback themes, only if supplied
- Questions or objections that came up
- Follow-up activity planned
- Recommended next marketing action

Never manufacture attendance, feedback, buyer interest, offers, or urgency. Never include visitor names, phone numbers, emails, or private financial information in the seller recap unless the agent explicitly requests it and doing so is appropriate under their brokerage and privacy rules.

## Quality rules

- Keep every asset consistent with the same property facts, date/time, CTA, and voice.
- If a detail is unknown, use a visible placeholder such as `[PRICE]`, `[OPEN HOUSE TIME]`, or `[CTA LINK]`. Never guess.
- Make the property the hero. Avoid generic agent-centered copy like “I’m thrilled to invite you.”
- Use local anchors only when supplied or verified. Never invent neighborhoods, school zones, commute times, rankings, or amenities.
- Never describe the “ideal buyer,” “perfect family,” neighborhood demographics, religion, race, age, disability, familial status, national origin, or who “belongs” in an area.
- Describe homes, physical features, amenities, access, and observable lifestyle attributes, not protected classes or coded steering language.
- Do not make legal, tax, lending, appraisal, inspection, or title claims. Refer specialized questions to the appropriate professional.
- Do not claim a property is “safe,” a school is “best,” or an area is “good for families.”
- Do not fabricate testimonials, visitor quotes, seller feedback, buyer motivation, concessions, competing offers, or market statistics.
- Avoid spammy phrases and canned AI language. Do not use: unlock, supercharge, game-changer, revolutionary, secret weapon, or leverage as a verb.
- Match the agent’s established voice when available. Otherwise use warm, clear, plain language.
- Ask at most one question message before generating the kit.

## Delivery format

Deliver the complete kit in chat using these exact section names:

1. **OPEN HOUSE SNAPSHOT**
2. **PROMOTION COPY**
3. **PROPERTY FLYER COPY**
4. **SIGN-IN COPY**
5. **HOST TALK TRACK**
6. **OPEN HOUSE SETUP CHECKLIST**
7. **FIVE-TOUCH FOLLOW-UP**
8. **SELLER RECAP**
9. **FINAL CHECK BEFORE YOU USE IT**

Under **FINAL CHECK BEFORE YOU USE IT**, list only unresolved placeholders, approvals, consent issues, or factual items the agent must verify. If nothing is unresolved, say: `No unresolved placeholders or factual gaps found.`

After the kit, add a short **Why this works:** note of no more than 3 sentences explaining the sequencing and the single most important action the agent should take before the event.

Then offer: `Want me to turn this into a clean printable document too?`

## End every run with

`Promote it, host it, follow up fast. The follow-up is where the open house becomes business.`
