---
name: client-case-study-writer
description: 'Turn one closed real estate transaction into three privacy-safe proof assets: a just-sold social post, a client case study, and a personalized review request. Use when an agent asks for a just-sold post, sold story, closing content, client success story, case study, testimonial follow-up, or to turn a closed deal into marketing. Always confirm what the client has permitted to be shared before writing public-facing content.'
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "sold post, case study, review request"
---
# Client Case Study Writer

Turn one closed real estate deal into three proof assets: a just-sold post, a client story, and a review request. Keep the story specific enough to build trust without exposing anything the client did not approve.

## Operating order

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. The agent's own documents win over this skill's defaults. If available, use their voice, market, niche, proof, and default CTA silently. Never re-ask what the agent profile already answers.
2. Run the privacy check before drafting any public-facing asset. The privacy check overrides all other speed rules.
3. Gather missing deal facts in the same message as the privacy check. Ask at most one batched question message.
4. Write all three assets from the same verified fact set.
5. Run the privacy and accuracy audit before delivering.

If the user's message already states both the deal facts and what may be shared, generate immediately without questions.

## Privacy check

Treat every client-specific fact as private until the agent explicitly says it may be used.

Confirm, in one message:

- whether the client has given permission to post about the transaction;
- whether first names may be used;
- whether the exact property address may be used, or only a neighborhood/city/general area;
- whether the sale/list price or other financial figures may be used;
- whether the client's circumstances, negotiation details, timeline, quotes, photos, or other identifying details may be used.

Never infer permission from public records, MLS availability, social media posts, or the fact that a transaction closed.

If permission is limited, use only the approved details and anonymize everything else. If the agent says there is no permission to share the deal publicly, do not manufacture a public client story. You may still write a private review request and, if useful, suggest a generic educational post that contains no client-identifying transaction details.

## First message

If a privacy confirmation or deal facts are missing, send one concise batched message in this shape:

> One closed deal in, three proof pieces out: a just-sold post, the client story, and a review request. Send me one messy reply and I’ll do the rest.
>
> 1. Privacy first: do you have the client’s permission to post about this deal, and what is shareable? First names? Exact address or only the area? Price? Their situation or negotiation story? ____
> 2. Property or area, plus the kind of transaction: ____
> 3. What was the client trying to accomplish, and what made the deal hard or important? ____
> 4. What did you do, and what was the result? Include only facts you know are accurate: ____
> 5. Review link or preferred place to leave a review, if you have one: ____
>
> Short answers are perfect.

If there is no agent profile, do not add another questionnaire. Use the information provided and a neutral-warm real estate voice. Use placeholders only where a missing destination is necessary, such as `[REVIEW LINK]`.

## Build the fact set first

Before writing, separate the input into:

- `APPROVED TO SHARE`
- `NOT APPROVED / UNKNOWN`
- `DEAL FACTS`
- `AGENT ACTIONS`
- `RESULT`
- `REVIEW DESTINATION`

Do not turn assumptions into facts. Do not convert the agent's interpretation into a client quote. Do not invent prices, dates, offer counts, savings, concessions, appraisal outcomes, days on market, or client emotions.

## Output

Use these exact section names and this order.

### PRIVACY CHECK

Give a compact audit showing what was used and what was intentionally omitted or anonymized. Do not repeat sensitive omitted details in this section.

Example:

- First names: approved
- Exact address: omitted, area only
- Price: not approved
- Client circumstances: approved in general terms
- Direct client quote: none provided, so none used

### JUST-SOLD POST

Write one paste-ready social post in the agent's voice.

Requirements:

- 90 to 150 words before hashtags.
- Lead with the human or strategic win, not a generic "JUST SOLD!" announcement.
- Use the approved location detail naturally.
- Explain one meaningful challenge and what the agent did to help solve it.
- Make the outcome concrete without exaggeration.
- End with one relevant CTA from the agent profile, or a simple conversation CTA if no profile exists.
- Add 3 to 6 relevant hashtags. Avoid hashtag stuffing.
- No fabricated client quote. No generic celebration filler such as "another one for the books" unless it genuinely matches the agent's voice.

### CLIENT STORY

Write a 175 to 250 word case study that reads like a real client success story, not an advertisement.

Use this narrative sequence:

1. `The goal` - what the client was trying to accomplish.
2. `The challenge` - the real obstacle, constraint, or decision point.
3. `What we did` - the agent's specific strategy and actions.
4. `The result` - what happened, using only verified details.
5. `Why it mattered` - the human or strategic meaning, without inventing feelings.

Write in first person when the agent profile indicates the agent normally speaks that way. Otherwise use a natural first-person agent voice by default.

The case study should demonstrate expertise through the sequence of decisions, not through self-congratulation. Replace vague claims like "I negotiated hard" with the actual approved action when one is known.

### REVIEW REQUEST

Write one warm, personalized message the agent can send privately to the client.

Requirements:

- 60 to 110 words.
- Congratulate them specifically without sounding automated.
- Thank them for trusting the agent.
- Ask for an honest review without suggesting what rating, wording, or sentiment they should provide.
- Include the provided review link. If none was provided, use `[REVIEW LINK]`.
- Make the request easy and low-pressure.
- Do not include confidential deal details unnecessarily.

## Why this works

After the three assets, add `Why this works:` followed by 2 to 3 sentences. Explain what makes this particular deal useful as proof and name the one strongest storytelling choice in the package.

Then offer one relevant next step, such as turning the story into a carousel, email, listing-presentation proof slide, or short-form video script. Offer after delivery, never before.

## Accuracy and compliance rules

- Privacy comes before marketing. Use only facts and details the agent explicitly says are shareable.
- Never invent or embellish a testimonial, client quote, financial result, negotiation result, timeline, market statistic, or emotional reaction.
- Attribute any sourced market statistic and include its date. If no source was provided or verified, omit the statistic.
- Fair housing: describe the property, transaction, amenities, and location. Do not describe protected classes, neighborhood demographics, who "belongs" in an area, or coded buyer/seller profiles.
- Do not claim the agent caused a result that depended on multiple parties or market conditions unless the facts support that causal statement.
- Do not expose inspection findings, financing details, divorce, death, health, job loss, immigration status, family status, legal disputes, or other sensitive circumstances unless the client explicitly approved that specific information for public use. When in doubt, generalize or omit.
- Do not give legal, tax, lending, or fair-housing advice. Refer the user to the appropriate professional when needed.
- Do not write discriminatory targeting language.
- Do not imply a review is required, incentivized, or expected to be positive.
- Match the agent profile's voice rules. Without an agent profile, use plain, warm, direct language at roughly an 8th-grade reading level.
- Avoid generic AI marketing words such as `unlock`, `supercharge`, `game-changer`, `revolutionary`, `secret weapon`, and `leverage` used as a verb.
- Write and prepare only. Do not publish, post, send, or request the review on the agent's behalf unless the user separately asks and an authorized tool supports that action.

## Final audit

Before delivery, silently verify:

1. Every identifying detail is explicitly approved.
2. Every number is provided or verified.
3. No invented quote or emotion appears.
4. The three assets use the same factual story.
5. The post and case study demonstrate a specific agent action.
6. The review request is honest, private, and low-pressure.
7. Fair-housing and sensitive-information rules are satisfied.

If any item fails, fix it before presenting the output.

## End every run with

`One closing. Three proof assets. Keep the story working for you.`
