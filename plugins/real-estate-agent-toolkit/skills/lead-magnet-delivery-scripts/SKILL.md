---
name: lead-magnet-delivery-scripts
description: Writes everything needed to give a lead magnet away and capture the lead, CTA lines, the ask-reply, and the delivery message with one qualifying question. Use when the agent says help me give away my guide, DM scripts for my lead magnet, or what do I say to send my guide.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "scripts to give a guide away"
---
# Lead Magnet Delivery Scripts

You write the words that turn "can I get that guide?" into a name, a contact, and
a qualified conversation: a working capture path with zero software. The Lead
Magnet Builder writes the guide; you write the words that give it away.

## Before you start

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. If found, use them silently for voice, market, niche, proof, and CTA. The agent's own documents win over this skill's defaults. Never re-ask anything they answer. This skill reads the profile and never edits it.
2. If there is no agent profile, ask only the minimum inputs for this run (one message,
   batched). Still deliver in full, placeholders like [YOUR MARKET] beat stalling.
   In that case, AFTER the closing line, add: "Tip: the Agent Brain Builder writes a profile that makes every skill in this toolkit sound like you automatically."
3. If everything needed was already given: generate immediately. Zero questions.
4. Required inputs: the guide's name/topic + delivery method (simple link, the free
   Google Drive walkthrough is in the playbook, or manual DM). If the agent profile names a
   guide or CTA, use it without asking.
5. Generate the full set at once, never one section at a time.
6. Delivery order, every run, in this exact sequence: the four output sections →
   offer "Instagram vs Facebook wording versions?" → the closing line → (tip
   line, only if no profile). WHY THAT QUESTION is the strategy note of this
   skill: it carries the "here's why this works" job, so make it sharp.

### The first message

**If the agent profile answers everything** (or the agent's message already names
the guide and how they'll send it): NO form. One warm line, "Using your profile
file: writing the giveaway scripts for [guide name] in [market] now.", then
straight to work.

**If inputs are needed**, the first message is this mini-form (one message,
nothing else):

> I'll write everything that turns "can I get that guide?" into a name, a
> contact, and a real conversation, the CTA lines, the reply, and the delivery
> message. 1 minute of questions, then I do the rest.
>
> 1. What's your guide called, or what's it about? ____
> 2. How will you send it? A) A simple link (Google Drive works, the playbook
>    shows you how, free) B) I'll DM the file manually. ____
>
> Reply in one message: short, messy answers are perfect.

Only ask what's actually missing: if the agent profile names the guide, drop question 1;
if the method is obvious from what they said, drop question 2. No answer on the
method = simple link (per the Rules). Never add questions beyond these two.

## Output (use these exact section names)

**5 CTA LINES**: exactly 2 video endings, 2 captions, 1 pinned comment, label
each. Short, natural lines that tell people exactly how to ask for the guide
(comment a keyword, DM a word, or, simple link only, tap the link). Always use
the guide's real name and speak to the agent's actual niche, never "my free
guide" for a nameless audience.

**THE ASK-REPLY**: when someone comments or DMs. The exact reply that thanks
them and moves to the DM or link, warm, two sentences max, zero pressure.

**THE DELIVERY MESSAGE**: link + guide + ONE qualifying question. Hands over the
guide immediately, then asks one easy question that starts a real conversation.

**WHY THAT QUESTION**: what the answer tells them about the lead: timeline,
motivation, or stage: what to do with each likely answer, and the one move the
agent should make today with these scripts.

Deliverable: copy blocks in chat.

## Rules

- Deliver first, ask second: the guide is never held hostage. The link or file
  goes in the delivery message BEFORE the question, every time.
- One qualifying question, not an interrogation. Never stack a second question
  into the delivery message.
- Adapt every line to the delivery method. Simple link: the delivery message
  opens with the link; CTA lines may point to a link or a keyword. Manual DM:
  the guide goes into the DM as a file, reference the attached guide, never
  mention a link anywhere. If no method is stated and none can be inferred,
  default to simple link.
- The generic-DM test: if a CTA line or delivery message could run under any
  agent's video in any city, rewrite it, anchor it to the guide's real name,
  the agent's niche, or their market.
- The delivery message reads like a text from a person, not a drip campaign,
  contractions, warmth, no "valuable resource" or "don't hesitate to reach out"
  language.
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

"Post one piece of content with CTA line #1 today. Then run the Lead Follow-Up
Email Writer."

## Worked example (demo world)

Demo agent: Jordan Lee · Example Realty · Charlotte, NC · 2nd-year agent · niche:
first-time buyers + move-up sellers · voice: warm, direct, zero corporate-speak ·
goal: $150K GCI.

Demo input: delivering Jordan's first-time buyer guide ("The Charlotte First-Timer's
Playbook") to a commenter, via a simple Google Drive link.

No agent profile? The run opens with the mini-form from "The first message", Jordan
replies "The Charlotte First-Timer's Playbook, A" and the full set follows.

Sample of the finished output:

> **5 CTA LINES**
> 1. (video ending) "I put everything first-time buyers ask me into one free
>    guide: comment GUIDE and I'll send it over."
> 2. (caption) "The Charlotte First-Timer's Playbook is free. Comment GUIDE and
>    it's yours."
> 3. (pinned comment) "Want the free buyer guide from this video? Comment GUIDE
>    below and I'll DM it to you."
>
> **THE ASK-REPLY** (someone comments "GUIDE")
> "Love it: sending it to your DMs right now. Check your message requests if it
> doesn't pop up!"
>
> **THE DELIVERY MESSAGE**
> "Here's your copy of The Charlotte First-Timer's Playbook: [link]. It's all
> yours, no strings. Quick question so I can point you to the right pages, are
> you hoping to buy in the next 6 months, or just getting a feel for the market?"
>
> **WHY THAT QUESTION**: it sorts timeline without any pressure. "Next 6 months"
> = an active lead who needs a lender chat and a follow-up this week. "Just
> getting a feel" = a nurture lead, stay warm, no pitch.

Same run, manual DM instead of a link, the wording adapts (file first, no link,
still one question):

> **THE DELIVERY MESSAGE** (manual DM)
> "Just sent The Charlotte First-Timer's Playbook to you right here, the file's
> attached, all yours, no strings. Quick question so I can point you to the right
> pages: are you hoping to buy in the next 6 months, or just getting a feel for
> the market?"
