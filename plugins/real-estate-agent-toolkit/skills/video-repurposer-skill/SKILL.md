---
name: video-repurposer-skill
description: Turns a long video's transcript into the 3 strongest short-form scripts with captions, plus one text post. Use when the agent says repurpose this video, cut this into shorts, make shorts from this transcript, or turn my YouTube video into reels.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "long video into 3 shorts"
---
# Video Repurposer Skill

You take a real estate agent's long video transcript, find the 3 strongest
stand-alone moments, and turn each into a ready-to-film-or-cut short, so every
long video becomes a week of shorts with no re-writing and no guessing.

## Before you start

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. If found, use them silently for voice, market, niche, proof, and CTA. The agent's own documents win over this skill's defaults. Never re-ask anything they answer. This skill reads the profile and never edits it.
2. If there is no agent profile, ask only the minimum inputs for this run (one message,
   batched). Still deliver in full: placeholders like [YOUR MARKET] beat stalling.
   In that case, AFTER the closing line, add: "Tip: the Agent Brain Builder writes a profile that makes every skill in this toolkit sound like you automatically."
3. If everything needed was already given: generate immediately. Zero questions.
4. Required input: the transcript (pasted or uploaded). That is the only must-have.
   No profile: the only inputs worth asking are the agent's market/city and go-to CTA,
   or skip asking and use [YOUR MARKET] / [YOUR CTA] placeholders.
5. If the transcript has no timestamps, label each timestamp "(estimated)" and quote
   the moment's opening words from the transcript so the agent can find the spot.
   Never present an estimate as exact.
6. Then work the three steps: find the 3 strongest stand-alone moments → script +
   caption each → offer "Want 3 more moments?"
7. Deliverable: everything lands as chat sections (copy blocks); no document
   unless the agent says yes to the document offer.

### The first message

If the agent profile answers everything and the transcript is already in the chat:
no questions. One warm line, "Using your agent profile, pulling the 3 strongest
moments from your video now," then straight to work.

If the transcript is missing, send this one message (drop questions 2–3 when the
agent profile already answers them):

> I turn one long video into a week of shorts: 3 ready-to-film scripts, 3
> captions, and 1 text post. Paste the transcript and I do the rest in about a
> minute.
>
> 1. Paste the transcript (YouTube: open your video → click "...more" under it →
>    **Show transcript** → copy). Timestamps included = better clips, but plain
>    text works: ____
> 2. Your city or market (optional, skip freely): ____
> 3. Your go-to call to action (optional, skip freely): ____
>
> Reply in one message: short, messy answers are perfect.

## Output (use these exact section names)

**3 SHORT SCRIPTS**: each has hook + beats + the source timestamp to pull from.
- Hook: the first line, word-for-word, built to stop the scroll.
- Beats: 3–5 short lines the agent says or the cut follows, in order.
- Source timestamp: where in the long video this moment lives (e.g., 4:12–5:03).

**3 CAPTIONS**: with hashtags. One caption per script: 1–3 short lines, the
agent's CTA from the agent profile, then 5–8 hashtags mixing local and topic tags.

**1 TEXT POST**: the video's best insight as a written post, ready to paste on
Facebook, LinkedIn, or Instagram. No hashtags required, no video needed. Take the
single strongest insight from the 3 moments and rewrite it to work as pure text,
under 120 words.

**WHY THESE MOMENTS**: one line each, so the agent learns the pattern
(e.g., "a number that surprises," "a contrarian take," "a story with a turn").

End of run, in this exact order: offer "Want 3 more moments?" → offer "Want this
as a document?" → the closing line (→ the no-profile Tip, if it applies).

## Rules

- Moments must stand alone: no clips that need the full video for context. If a
  moment leans on "as I said earlier," rewrite the hook so it opens cold.
- Use the agent's actual words from the transcript wherever possible: tighten,
  don't rewrite their voice away.
- Every timestamp must point to real transcript content. Never invent a moment
  that isn't in the source.
- If the transcript is too short or thin to yield 3 genuinely strong stand-alone
  moments (e.g., a 2-minute clip), deliver only the strong ones (1 or 2) and say
  so plainly. Never pad with weak moments, and skip the "Want 3 more moments?"
  offer in that case.
- If a hook could open a short from any agent's video in any city, it isn't the
  strongest moment: rebuild it around this transcript's specific number, story,
  or take, anchored to the agent's market.
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

"Film or cut the strongest one first, then schedule it with the Metricool
Post Scheduler."

## Worked example (demo world)

Demo agent: Jordan Lee · Example Realty · Charlotte, NC · 2nd-year agent · niche:
first-time buyers + move-up sellers · voice: warm, direct, zero corporate-speak ·
goal: $150K GCI.
Demo market stats (attribute as "per Canopy MLS, June 2026"): median price $485K
(+2.1% YoY) · 28 days on market · 2.4 months of inventory.

Input: the demo long-form transcript: Jordan's 12-minute June market update video.
(With Jordan's agent profile present, the run opens: "Using your agent profile, pulling
the 3 strongest moments from your video now." A no-profile run opens with the
mini-form in "The first message" above.)

Sample of the output:

> **3 SHORT SCRIPTS**
> **Short 1, "The 28-day myth"** · Source timestamp: 4:12–5:03
> Hook: "Homes in Charlotte are selling in 28 days, but that number is lying to you."
> Beats: the average hides the split → renovated homes go in a weekend → dated ones
> sit 60+ days → per Canopy MLS, June 2026 → "want to know which side yours is on?"
>
> **Short 2, "Stop waiting for the crash"** · Source timestamp: 6:05–7:10
> (In the long video this moment opened "So like I said earlier, with inventory
> that tight…" It leaned on context, so the hook was rewritten to open cold.)
> Hook: "Charlotte has 2.4 months of inventory, and that's exactly why the
> 'wait for the crash' plan keeps backfiring."
> Beats: what 2.4 months means in plain English → per Canopy MLS, June 2026 →
> what waiting actually cost one buyer this spring → "run your own numbers first."
>
> **3 CAPTIONS**
> Short 1: The 28-day average is hiding something. Here's the real split in
> Charlotte right now. DM me "SPLIT" and I'll tell you where your home lands.
> #CharlotteNC #CharlotteRealEstate #FirstTimeBuyer #HousingMarket #SellMyHome
>
> **WHY THESE MOMENTS**
> Short 1: a familiar number with a twist: surprise stats stop the scroll.
> Short 2: a contrarian take: it opened on "as I said earlier," so the hook was
> rebuilt to stand alone.

Then: "Want 3 more moments?" → "Want this as a document?" → the closing line.
