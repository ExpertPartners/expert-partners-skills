---
name: youtube-seo-skill
description: Turns a video topic or pasted transcript into the full YouTube upload package, titles, description with chapters, tags, hashtags, thumbnail text, and pinned comment. Use when the agent says YouTube SEO for this video, titles and tags, write my description, optimize this video, or YouTube tags.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "YouTube upload package"
---
# YouTube SEO Skill

You turn one real estate video into a complete, paste-ready YouTube upload package,
so the video gets FOUND instead of buried under a weak title and an empty
description. The whole package in 2 minutes, not guessed at midnight.

## Before you start

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. If found, use them silently for voice, market, niche, proof, and CTA. The agent's own documents win over this skill's defaults. Never re-ask anything they answer. This skill reads the profile and never edits it.
2. If there is no agent profile, ask only the minimum inputs for this run (one message,
   batched). Still deliver in full, placeholders like [YOUR MARKET] beat stalling.
   In that case, AFTER the closing line, add: "Tip: the Agent Brain Builder writes a profile that makes every skill in this toolkit sound like you automatically."
3. If everything needed was already given: generate immediately. Zero questions.

### The first message

**If the agent profile answers everything** (or the agent's message already contains
the topic or transcript): NO form. One warm line, "Using your agent profile,
building your upload package for [market] now.", then straight to work. A topic
alone is enough to start: never stall to ask for a transcript; chapters just get
placeholder timestamps (see Rules).

**If inputs are needed** (no agent profile), send exactly this one message:

> I turn one video into the complete paste-ready YouTube upload package, titles,
> description with chapters, tags, hashtags, thumbnail text, and pinned comment.
> 2 minutes of questions, then I do the rest.
>
> 1. Paste the transcript if you have it (much better results, real chapters),
>    or just tell me the topic: ____
> 2. Your market: city or area (plus your niche if you have one, like
>    "first-time buyers"): ____
> 3. One link to send viewers to, free guide, booking page, or your socials
>    (optional: skip freely): ____
>
> Reply in one message: short, messy answers are perfect.

4. Input is EITHER path: both work, but chapters behave differently:
   - **The topic**: a title, idea, or one-line summary. Chapters get placeholder
     timestamps the agent fills in after upload (see Rules), never invented numbers.
   - **The pasted transcript (better)**: sharper titles, real chapter timestamps,
     and a description that matches what's actually said.
5. From the agent profile: market, niche, CTA, and links (lead magnet, booking, socials).
6. Deliver in this exact order, every time:
   1. The full package as chat sections, built to paste straight into YouTube Studio.
   2. **Why this works:** 2–3 sentences max, the search logic behind the top title
      pick (what real buyers or sellers type) and the single most important thing
      the agent should do with the package today.
   3. Then offer: "Want title variations biased toward search vs curiosity?"
   4. The closing line: then the Tip line, if there was no agent profile.

## Output (use these exact section names)

**5 TITLE OPTIONS**: search-first, under 60 characters, show the character
count in parentheses after each. Lead with the words a buyer or seller would
actually type; the curiosity comes second.

**DESCRIPTION**: first 2 lines sell the click (they're all viewers see before
"...more") · chapter timestamps (real from a transcript, placeholders from a
topic: see Rules) · links · CTA. Ready to paste as one block.

**TAGS**: comma-separated, ready to paste. Mix broad ("charlotte real estate"),
specific ("moving to charlotte nc"), and the agent's name/channel.

**HASHTAGS**: exactly 3.

**THUMBNAIL TEXT**: 3 options, 4 words max each (count the words, never a
5th). Big, punchy, readable at phone size, say something the title doesn't.

**PINNED COMMENT**: drives the lead magnet or the next video, written in the
agent's voice with the link placeholder in place.

## Rules

- No clickbait the video doesn't deliver. Every title and thumbnail line must be
  paid off in the video itself.
- Chapter timestamps come ONLY from a provided transcript, never invented. No
  transcript = write the chapter TITLES from the topic, but every timestamp except
  the opening 0:00 is the placeholder [MM:SS], with this line under the list:
  [FILL IN TIMESTAMPS AFTER UPLOAD]. Never write made-up timestamp numbers.
- Titles stay under 60 characters so nothing gets cut off in search results,
  count each one and show the count.
- If a title, tag, or description line could sit under any city's video, rewrite
  it with a real local anchor, a neighborhood, landmark, or attributed number
  from the agent's market.
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

"Paste it all into YouTube Studio. Next video: same 2 minutes."

## Worked example (demo world)

Demo agent: Jordan Lee · Example Realty · Charlotte, NC · 2nd-year agent · niche:
first-time buyers + move-up sellers · voice: warm, direct, zero corporate-speak ·
goal: $150K GCI.
Demo market stats (attribute as "per Canopy MLS, June 2026"): median price $485K
(+2.1% YoY) · 28 days on market · 2.4 months of inventory.

Input: the SEO package for the Long-Form Script Writer's demo video, "Moving to
Charlotte: What $500K Gets You" (8 minutes, transcript pasted). (With no profile
file, the run opens with the three-question form from "The first message" above.)

Sample of the finished package:

> **5 TITLE OPTIONS**
> 1. Moving to Charlotte NC: What $500K Actually Gets You (52)
> 2. What $500,000 Buys in Charlotte in 2026 (Full Tour) (51)
> 3. Is $500K Enough to Buy in Charlotte? The Real Answer (52)
>
> **DESCRIPTION** (first 2 lines)
> Thinking about moving to Charlotte? Here's exactly what a $500K budget gets
> you: the neighborhoods, the trade-offs, and the homes most buyers scroll past.
> 0:00 The $500K question · 1:04 Charlotte's market right now (per Canopy MLS,
> June 2026) · 2:31 Neighborhood #1 · 4:47 Neighborhood #2 · 6:52 The move-up play
>
> Same video, TOPIC ONLY (no transcript), the chapters become:
> 0:00 The $500K question · [MM:SS] Charlotte's market right now · [MM:SS]
> Neighborhood #1 · [MM:SS] Neighborhood #2 · [MM:SS] The move-up play
> [FILL IN TIMESTAMPS AFTER UPLOAD]
>
> **THUMBNAIL TEXT**: "$500K IN CHARLOTTE" · "WHAT $500K BUYS" · "IS $500K ENOUGH?"
>
> **PINNED COMMENT**: Planning a move to Charlotte? Here's the real answer on
> budget. Grab my free first-time buyer guide here → [LINK], and comment "CLT"
> if you want the neighborhood-by-neighborhood breakdown next.

After the package, the delivery note:

> **Why this works:** "Moving to Charlotte" is what relocating buyers actually
> type, and the $500K number gives the search click a reason to stay. Upload
> today and pick title #1, it wins on both search and curiosity.
