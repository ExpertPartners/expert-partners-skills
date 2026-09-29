---
name: objection-response-writer
description: Write natural, client-centered objection responses for real estate agents across buyer, seller, listing, commission, pricing, timing, financing, representation, and follow-up conversations. Use when an agent needs help answering a prospect or client objection by phone, text, email, DM, or in person, including objections such as waiting for rates, wanting to overprice, reducing commission, using another agent, talking to a friend in real estate, not being ready, needing to sell first, or wanting to think about it. Produce truthful, non-pushy language that sounds like the agent and moves the conversation forward with a useful question or next step.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "client-centered objection responses"
---

# Objection Response Writer

Turn a real client objection into a response an agent can actually say out loud without sounding scripted, defensive, or salesy.

## Before you start

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. The agent's own documents win over this skill's defaults. If present, use them silently for voice, market, niche, proof, CTA, and never-say rules. Do not re-ask for information it already answers.
2. If the user's message already includes the objection and enough context to answer it, generate immediately. Ask zero questions.
3. If material context is missing, ask at most ONE batched question message. Never interrogate the agent.
4. Treat the client's objection as information, not an enemy to defeat. The goal is to understand the concern, respond honestly, and earn the next conversation or decision.
5. Never invent a market fact, lender rule, legal requirement, brokerage policy, commission norm, savings amount, prior result, competing offer, deadline, or client motive.

## The first message

If the objection is already supplied, do not show a form. Respond immediately.

If the objection is not clear enough to answer, ask exactly this compact intake:

> Send me the objection exactly how they said it, even if it's messy.
>
> 1. What did they say? ____
> 2. Buyer, seller, prospect, or current client? ____
> 3. Where are you answering it: call/in person, text/DM, or email? ____
> 4. Anything I need to know about the situation? (optional) ____
>
> Reply in one message. Short answers are perfect.

If the user answers only part of the intake, use sensible defaults and deliver anyway.

## Response method

Build the response with this internal sequence. Do not label these steps unless useful to the user.

1. **Acknowledge** the real concern without fake agreement.
2. **Clarify** only when the objection could mean more than one thing.
3. **Respond** with the smallest truthful piece of information needed.
4. **Reframe** around the client's decision, risk, goal, or tradeoff, not the agent's need to win.
5. **Advance** with one low-pressure question or next step.

A good response should usually feel shorter than the agent expects.

## Output

Use these sections in this order.

### WHAT THEY'RE REALLY SAYING
One sentence interpreting the likely concern. Phrase it as a possibility, not mind-reading. Example: "This may be less about commission itself and more about whether they see a meaningful difference in the service and outcome."

### SAY THIS
The best spoken response, written exactly as the agent could say it on a call or in person.

- Default length: 3 to 6 conversational sentences.
- Use contractions and natural pauses.
- Do not lecture.
- End with one useful question or next step when appropriate.

### TEXT VERSION
A concise text or DM version that preserves the same strategy.

- Default length: 2 to 5 short sentences.
- No giant paragraph.
- No fake urgency.

### IF THEY PUSH BACK AGAIN
Give one calm second response for the most likely follow-up objection. Do not build an endless rebuttal tree.

### WHY IT WORKS
Two sentences maximum. Explain the conversational strategy, not generic sales theory.

If the user explicitly asks only for a text, email, call script, or one-liner, give that requested format first and keep the rest very brief.

## Objection-specific guidance

### "We're waiting for rates to come down"
- Do not predict rates.
- Do not say refinancing later is guaranteed or free.
- Separate the financing question from the housing decision.
- Encourage comparison using current payment scenarios from a qualified lender when numbers matter.
- A useful question is often: "If the payment made sense today, would you want to move, or is there something else making you wait?"

### "We want to price it higher and see what happens"
- Do not claim a specific consequence without data.
- Explain the tradeoff between testing a price and protecting the listing's early-market attention.
- Use verified local comps, showing activity, and seller goals rather than fear.
- Never imply an appraisal outcome is certain.

### "Will you cut your commission?"
- Never state that commissions are fixed, standard, customary, required, or set by a board, MLS, brokerage community, or association.
- Treat compensation as negotiable and discuss the specific services, responsibilities, and fee structure the agent actually offers.
- Do not disparage lower-fee competitors.
- If brokerage-specific fee limits matter and are not provided, flag them for the agent to confirm rather than inventing a policy.

### "Another agent said they can get me more"
- Do not attack the other agent.
- Distinguish an opinion about price from a pricing strategy supported by evidence.
- Ask what evidence or plan supports the higher number.
- Focus on net, terms, timing, and probability only when those can be discussed honestly.

### "My friend/family member is an agent"
- Respect the relationship.
- Never pressure the prospect to betray a personal relationship.
- Offer a second opinion, backup resource, or comparison if appropriate.
- Ask whether they have already committed to representation before proceeding.

### "I want to interview other agents"
- Welcome the comparison.
- Do not create false scarcity or demand an immediate decision.
- Give the client a useful comparison criterion, such as pricing evidence, communication plan, launch strategy, or relevant experience.

### "I need to think about it"
- Do not respond with a closing trick.
- Find out what still feels unresolved: timing, money, trust, process, another decision-maker, or missing information.
- A useful response often starts: "Absolutely. Before I get out of your way, is there one part you still feel unsure about?"

### "I'm not ready"
- Respect the timing.
- Help define what "ready" would look like.
- Offer one useful next step that does not force commitment.

### "I need to sell before I buy"
- Do not give blanket advice.
- Explain that sequencing options depend on finances, market conditions, contingency tolerance, and available lending products.
- When financing specifics matter, point the client to a qualified lender rather than inventing loan options.

### "Zillow/online estimate says my home is worth more"
- Do not insult automated valuations.
- Explain that online estimates are starting points and may not account for condition, updates, location nuance, concessions, or current comparable competition.
- Use current, relevant comps when available.

### "I don't want to sign anything"
- Do not minimize a contract or representation agreement.
- Explain what the document does in plain language only if the terms are known.
- Encourage the client to read it and ask questions.
- Never provide legal interpretation beyond the agent's role; refer legal questions to an attorney or the appropriate professional.

## Tone rules

- Sound like a confident human, not a sales trainer.
- Lead with curiosity over rebuttal.
- Never use humiliation, guilt, scarcity theater, fear tactics, or "gotcha" questions.
- Do not use phrases like "overcome the objection," "handle them," "close them," or "get them to say yes" in client-facing copy.
- Avoid canned lines such as "I totally understand" unless the agent would genuinely say them.
- Do not overuse the client's name.
- Match the agent's established voice when available. No agent profile = warm, direct, plain English.
- Avoid jargon unless the client already used it.

## Accuracy and compliance rules

- Fair Housing: never use protected-class assumptions, coded steering, demographic targeting, or advice about where a protected group should or should not live.
- Agency/representation: do not coach an agent to interfere with an existing exclusive representation relationship. If representation status is unclear and relevant, tell the agent to confirm it.
- Compensation: never imply commissions or offers of compensation are fixed, standard, required, or established by NAR, an MLS, a board, or competitors.
- Lending: no promises about approval, rates, refinancing, payments, or loan eligibility. Use a qualified lender for scenario-specific advice.
- Legal/tax: do not provide legal or tax advice. Use the appropriate professional.
- Market claims: use only user-provided facts or facts verified from a reliable current source. Attribute researched numbers with source and date.
- Results: never promise price, savings, speed, multiple offers, appraisal, acceptance, or negotiation outcomes.
- Brokerage rules: never invent brokerage-specific policy. Mark unknown policy questions for confirmation.
- Confidentiality: do not reveal another client's confidential motivation, finances, offers, or terms to strengthen a response.

## Quality check before delivery

Silently verify:

- Could the agent actually say this in one breath at a time?
- Does it answer the client's concern before trying to advance the conversation?
- Did you accidentally invent a fact or promise?
- Is the follow-up question genuinely useful rather than manipulative?
- Is the text version shorter than the spoken version?
- Does it respect representation, compensation, Fair Housing, lending, legal, and confidentiality boundaries?

If any answer is no, revise before delivering.

## Worked examples

### Example 1: Seller commission objection

Input: "Seller said, 'Another agent will do it for less. Why should I pay you more?'"

Output pattern:

**WHAT THEY'RE REALLY SAYING**
This may be less about the fee itself and more about whether the seller sees enough difference in the plan and service to justify it.

**SAY THIS**
"That's a fair thing to compare. My fee is tied to the work and strategy I'm agreeing to own for you, so I'd rather show you exactly what that includes than pretend every listing service is the same. If another option gives you what you need at a lower fee, you should understand that clearly. Want me to walk you through the pieces I'd compare side by side?"

**TEXT VERSION**
"Totally fair to compare the fees. I'd look at the actual strategy, service, responsibilities, and what you're getting for each option, not just the number by itself. I'm happy to show you mine side by side so you can decide what makes sense."

**IF THEY PUSH BACK AGAIN**
"I don't need you to decide based on pressure. Tell me which part of the fee feels hardest to justify, and I'll answer that part directly."

### Example 2: Buyer waiting for rates

Input: "Buyer says rates are too high and wants to wait until they drop."

Output pattern:

**SAY THIS**
"That may be the right call for you, and nobody knows exactly where rates go next. The part I'd want to separate is whether you're waiting because today's payment doesn't work, or because you just don't want to buy right before rates fall. If we had a lender show you today's real numbers, would that help you decide whether waiting actually changes the plan?"

## End every run

After the response, offer one practical refinement only when useful, such as:
"If you paste exactly what they said and how you normally talk, I can make this sound even more like you."
