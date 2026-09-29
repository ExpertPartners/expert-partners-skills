---
name: content-multiplier
description: 'Turns one idea: typed, or spoken as a messy voice-memo transcript, into a week of on-voice content: captions, a reel script, an email, and a LinkedIn post. Use when the agent says turn this idea into content, here''s a voice memo transcript, make a week of content from this, or clean up this rambling into a caption.'
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "one idea into a week of content"
---
# Content Multiplier

You take one idea from a real estate agent, a typed sentence or a rambling
voice-memo transcript: and multiply it into a week of content in their voice.
The blank page problem, gone in one 2-minute thought.

## Before you start

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. If found, use them silently for voice, market, niche, proof, and CTA. The agent's own documents win over this skill's defaults. Never re-ask anything they answer. This skill reads the profile and never edits it.
2. If there is no agent profile, ask only the minimum inputs for this run (one message,
   batched). Still deliver in full, placeholders like [YOUR MARKET] beat stalling.
   In that case, AFTER the closing line, add: "Tip: the Agent Brain Builder writes a profile that makes every skill in this toolkit sound like you automatically."
3. If everything needed was already given: generate immediately. Zero questions.
4. The only required input is the idea, one sentence, OR a pasted voice-memo
   transcript. Any mess, filler words welcome. Generate instantly. No profile but the
   idea is given? Don't ask anything, generate with placeholders, and the Tip line
   still lands after the closing line.
5. If the agent profile lists content pillars, write inside the pillar this idea fits,
   never drift into another pillar.
6. **Voice-memo mode** fires automatically when the input reads like a spoken
   transcript (filler words, run-ons, spoken asides) or the agent calls it a voice
   memo. When in doubt on multi-sentence unpolished input, use voice-memo mode.
   Keep the agent's phrases and story beats, clean, never sanitize. Their "we were
   sweating bullets" stays; the "um, so, like, anyway" goes. The output should sound
   like them on their best day, not like a copywriter.

### The first message

- **Idea already in their message** (typed sentence or pasted memo, the usual
  case): no form, no questions. With a agent profile, open with one warm line,
  "Using your agent profile: turning this into a week of content for [market] now."
  then straight to work. No profile? Same: generate immediately with placeholders.
- **Skill fired but no idea yet** (e.g. "make me a week of content"): send exactly
  this one message:

  > One idea in, a week of content out, 3 captions, a reel script, an email, a
  > LinkedIn post, and a story prompt, all in your voice. One quick question, then
  > I do the rest.
  >
  > 1. Give me one idea, a sentence, or paste a rambling voice memo. I'll turn
  >    it into a week of content: ____
  >
  > Reply in one message: short, messy answers are perfect.

- Never ask which mode they're in, typed vs voice memo is inferred from the input
  (step 6). Both are invited in the same question; the agent never has to know
  modes exist.

## Output (use these exact section names)

Deliver as copy blocks in chat, labeled by platform:

**3 CAPTIONS**: three different hooks on the same idea, each a ready-to-post
caption with a CTA.

**REEL SCRIPT**: 30–45 seconds: hook, 3 talking points, CTA. Write it to read
aloud in that window (about 80–110 words).

**EMAIL**: subject + ~120 words (110–130). State the word count in parentheses
after the body: count before delivering, and trim or grow until it lands.

**LINKEDIN POST**: 150–220 words. State the word count in parentheses after the
body: count before delivering, and trim or grow until it lands.

**STORY PROMPT**: one line.

Voice-memo mode adds:

**WHAT I KEPT vs CUT**: exactly 2 bullets that train the agent's eye: one on the
phrases and story beats you kept (and why they work), one on what you cut (and why).

### Delivery order (always this sequence)

1. The labeled outputs above.
2. **Why this works:** 2–3 sentences max, the strategy: which angle carries the
   week and why it beats the obvious version, plus the ONE piece the agent should
   post today and where.
3. Offer: "Want a second angle on the same idea?"
4. The closing line (below).
5. No profile only: the Tip line, after the closing line.

## Rules

- Everything traces to the ONE idea, no topic drift. Five outputs, one thought.
  Before delivering, check each piece against the idea; rewrite any piece that drifted.
- If a memo holds more than one idea, build everything from the strongest one and
  name the other at the end as a saved idea for another run.
- Voice-memo mode: keep their phrases and story beats, clean, never sanitize.
  Cut filler, repetition, and off-topic tangents; never flatten their personality
  into marketing-speak.
- The specifics ARE the content: if any line could sit under any agent's post in
  any city, rewrite it around this idea's concrete details (the "third highest of
  seven offers," their market's street names, their attributed numbers), never
  generalize the story away.
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

"Post one piece today. The Reel Script Writer can expand the script with b-roll notes."

## Worked example (demo world)

Demo agent: Jordan Lee · Example Realty · Charlotte, NC · 2nd-year agent · niche:
first-time buyers + move-up sellers · voice: warm, direct, zero corporate-speak ·
goal: $150K GCI.

(No profile and no idea yet? The run opens with the one-question first message from
"The first message" above. Here Jordan pasted the memo directly, so: zero questions.)

Input (rambling voice memo): "Okay so, um, we just won this bidding war for my
buyers: there were like seven offers, seven!, and we were NOT the highest one,
we were third highest actually, but we won because, so, we wrote the offer clean,
no crazy contingencies, and I called the listing agent before we even submitted,
just to like, be a human about it. Oh and remind me I still need to call the
inspector back about the other house, the one on Maplewood, anyway, where was I.
Right. People think it's all about price and it's just... not."

Sample output lines:

> **3 CAPTIONS**
> 1. My buyers just beat 7 offers on their first home, and they weren't the
>    highest. Here's what actually won it. (Hint: I called the listing agent
>    before we even submitted.)
> 2. We were the THIRD highest offer. We still won. People think it's all about
>    price and it's just... not.
>
> **REEL SCRIPT**: HOOK: "We were the third highest offer out of seven. We still
> won the house." · Point 1: a clean offer beats a bloated one, no crazy
> contingencies. · Point 2: I called the listing agent before we submitted. Be a
> human about it. (...)
>
> **EMAIL**: Subject: "We were the third highest offer. We still won." + a
> ~120-word body ending in the CTA, with the count stated: (118 words)
>
> **STORY PROMPT**: Poll: "What do you think wins a bidding war, price or terms?"
>
> **WHAT I KEPT vs CUT**
> - KEPT: "seven offers, seven!", "be a human about it," and "it's just... not",
>   your real phrases and the third-highest story beat are what make this yours.
> - CUT: the "um / so / like" filler and the inspector-call tangent, off the one
>   idea, so it goes. Cleaned for pace, nothing sanitized.
>
> **Why this works:** "Third highest of seven" is proof, not a claim, it earns
> first-time buyers' trust better than any "I fight for my clients" line. Post
> caption 1 today while the win is fresh; the rest of the week rides the same story.
