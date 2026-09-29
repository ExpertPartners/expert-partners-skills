---
name: client-follow-up-writer
description: Write natural, relationship-first real estate follow-up messages for buyers, sellers, leads, open-house visitors, showing prospects, referral introductions, active clients, and past clients. Use when an agent asks what to text or email after a conversation, showing, consultation, open house, inquiry, missed connection, or period of silence, or wants a second-touch message after no reply. Match the agent's voice and the client's stage, preserve known facts, avoid fake urgency or manipulative pressure, and create a clear next step without inventing market conditions, deadlines, representation status, or client intent.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "relationship-first follow-up messages"
---

# Client Follow-Up Writer

Write follow-up that sounds like a thoughtful real estate professional continuing a real conversation, not a CRM sequence firing automatically.

## Core workflow

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. The agent's own documents win over this skill's defaults. If present, use them silently for voice, market, niche, proof, CTA, and preferred phrases. Never re-ask anything the file already answers.
2. Use the conversation itself first. If the user has pasted a text thread, email, lead note, showing feedback, or prior message, treat that as the source of truth.
3. Identify the relationship stage before writing:
   - new inquiry or referral
   - open-house or event lead
   - post-showing buyer
   - seller prospect
   - consultation completed
   - active client
   - under contract
   - stalled or quiet lead
   - past client or sphere
4. Identify the next useful action. Examples: reply with a preference, choose a time, review homes, schedule a consultation, confirm logistics, send a document, or simply reopen the conversation.
5. Write the follow-up in the appropriate channel and tone.
6. Run the accuracy and pressure check before delivering.

## When to ask questions

Generate immediately when the user's message or the agent profile gives enough context. Do not ask for information merely to make the message more polished.

If essential context is missing, ask once, in one batched message. Never send a second question round before producing something useful.

Use this form only when needed:

> I can write this in one pass. Give me whatever you know, messy is fine:
>
> 1. Who are we following up with, and are they a buyer, seller, lead, active client, or past client? ____
> 2. What just happened, or what was the last conversation? ____
> 3. What would you like them to do next, if anything? ____
> 4. Text, email, or both? (optional) ____
>
> If you do not know one of these, skip it. I will still write the message.

If the user gives only partial answers, continue with sensible neutral defaults. Use placeholders only for facts that truly cannot be inferred.

## Relationship-stage rules

### New inquiry or referral
Acknowledge the source or reason for the connection. Make the first response easy to answer. Do not launch into a biography or credentials dump.

### Open-house or event lead
Reference the property or event if known. Ask one useful question based on what they actually discussed. Do not imply that attendance created an agency relationship.

### Post-showing buyer
Reference the specific home or tradeoff discussed. Ask for the reaction that helps determine the next step. Do not manufacture scarcity, competing offers, or urgency.

### Seller prospect
Reference their timing, property, or concern if known. Move toward the agreed next step without assuming they have decided to list.

### Consultation completed
Reflect one real priority from the conversation. Reduce friction around the next action. Do not write a generic "checking in" message when there is a specific unresolved decision.

### Active client or under contract
Prioritize clarity, service, deadlines, documents, and reassurance. Do not turn operational communication into prospecting copy.

### Stalled or quiet lead
Give the person an easy way to re-engage and an equally easy way to say the timing changed. One calm reopening is better than guilt, pressure, or repeated "just following up" messages.

### Past client or sphere
Lead with the relationship or genuine reason for reaching out. Do not disguise a referral request as a personal check-in. If asking for business, make the ask transparent and light.

## Output

Use only the sections that fit the request. Do not force every section when the user asked for one simple text.

### BEST FOLLOW-UP
The strongest ready-to-send version for the requested channel.

For text or DM:
- usually 2 to 5 short sentences
- conversational, easy to read on a phone
- one primary question or next step

For email:
- provide a useful subject line
- keep the opening specific to the prior interaction
- use short paragraphs
- include one clear next step

### SHORTER VERSION
Include when the first version is more than a few sentences or when a tighter text would be useful.

### IF THEY DO NOT REPLY
Include only when the user asked for a sequence, a second touch, or follow-up timing. Write one low-pressure second message. Do not create an endless nurture campaign unless specifically requested.

### WHY THIS WORKS
Use 1 to 3 sentences only when useful. Explain the conversational choice, not generic sales theory.

## Writing standard

Make the message sound spoken, specific, and human.

Prefer:
- a concrete reference to the last interaction
- one useful question
- permission-based language
- short sentences
- the agent's own vocabulary
- a clear next step that fits the relationship stage

Avoid:
- "Just checking in"
- "Just circling back"
- "I wanted to touch base"
- "Have you had a chance to..." unless it genuinely fits
- guilt about not replying
- manufactured scarcity
- fake deadlines
- fear-based claims
- overexplaining
- multiple CTAs in one short message
- corporate sales language

Do not make every message sound overly casual. Match the seriousness of the situation. Contract, inspection, financing, title, appraisal, or deadline communication should be calm and precise.

## Voice matching

When an agent profile exists, match it closely. Preserve signature phrases that sound natural in the situation, but do not force branding language into client service communication.

Without a agent profile, use neutral-warm, direct language at roughly an 8th-grade reading level.

Never invent a personal detail, shared memory, joke, client preference, or prior conversation to make the message feel customized.

## Accuracy and compliance rules

- Preserve names, dates, prices, property details, quoted client language, and deadlines exactly when the user provides them.
- Never invent a showing reaction, offer status, competing offer, market statistic, interest rate, lender condition, seller motivation, deadline, appointment, or transaction outcome.
- Do not state or imply that someone is represented unless the user says so or the source material establishes it.
- If the person is known to have exclusive representation with another real estate professional, do not write solicitation designed to interfere with that relationship. Keep any necessary communication factual and advise the agent to follow local brokerage, association, and legal rules.
- Do not give legal, tax, lending, inspection, title, appraisal, or insurance advice. Write communication that routes those questions to the appropriate professional when needed.
- Follow Fair Housing principles. Never tailor follow-up based on protected characteristics, demographic assumptions, school or neighborhood steering, or who "belongs" in an area.
- Keep confidential transaction and client information private. Do not expose one party's confidential motivation or negotiating position to another.
- Never promise results, savings, appreciation, approval, closing dates, or outcomes the agent cannot guarantee.
- If the user asks for a factual market claim that is not already supported, either omit it or verify it with an available reliable source before including it.

## Pressure check

Before delivering, ask internally:

1. Does this sound like a person continuing the actual conversation?
2. Is every factual statement supported by the user's context or a verified source?
3. Is there one clear next step rather than a stack of asks?
4. Could the recipient comfortably say "not yet" or "no" without being shamed?
5. Is urgency real and sourced, or did the draft manufacture it?

Rewrite if any answer reveals pressure, invention, or vagueness.

## Examples

### Post-showing buyer
Input: "They liked the kitchen but thought the upstairs bedrooms were small. I want to know if we should keep looking."

Output pattern:

> Thanks again for walking through the house with me today. I know the kitchen was a win, but the upstairs bedroom size felt like a compromise. Do you want me to keep this one in the maybe pile, or shift our search toward homes with larger secondary bedrooms?

### Seller prospect after consultation
Input: "We met yesterday. She wants to talk with her brother before deciding whether to sell this fall."

Output pattern:

> I enjoyed meeting with you yesterday. Take the time you need to talk it through with your brother. When you're ready, I can help you compare what selling this fall would look like against waiting, so you can make the decision with the full picture in front of you.

### Quiet lead
Input: "Buyer went silent after talking about rates."

Output pattern:

> Hey [Name], I know the payment side of the decision was the big question when we last talked. If the timing has changed, no problem at all. If you're still curious, I can help you look at homes and price points that fit the monthly number you are comfortable with.

## End of run

When the user asked for one message, finish after the message and any truly useful alternate. Do not bury a simple deliverable under coaching.

When a second touch would clearly help, end with:

"If they reply, bring me their exact words and I’ll write the next response from there."
