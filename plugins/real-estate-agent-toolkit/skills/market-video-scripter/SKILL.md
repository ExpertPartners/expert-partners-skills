---
name: market-video-scripter
description: Turn verified local real estate market statistics into a concise, camera-ready market update video package for an agent. Use when the user asks for a market update script, monthly market video, local housing market recap, buyer or seller market video, or provides current stats such as median sale price, days on market, inventory, or months supply and wants a short-form video script, on-screen text, caption, and filming notes.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "market update video package"
---
# Market Video Scripter

Turn current local housing-market data into a useful 60-second video an agent can film today. Translate numbers into decisions for real buyers and sellers rather than simply reading statistics aloud.

## Start with context

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. The agent's own documents win over this skill's defaults. Use known voice, market, niche, proof, and CTA without re-asking.
2. If the user already supplied the market and enough data, start immediately.
3. If essential inputs are missing, ask once in a single batched message. Never send a chain of intake questions.
4. If neither a usable market nor verified statistics are available and web research cannot be completed, deliver a fill-in template with placeholders. Never invent data.

Use available web search for current market research when needed. Do not claim that search or an integration exists if it is unavailable in the current environment.

## One-message intake

If inputs are needed, ask:

> I’ll turn the latest verified market numbers into a 60-second video you can film today, including the script, on-screen text, caption, and filming notes.
>
> 1. Your market or exact geography: ____
> 2. If you already have trusted stats, paste them here with the source and reporting month if you know them: ____
> 3. Your preferred CTA, such as “Comment MARKET” or a booking link (optional): ____
>
> Short, messy answers are perfect.

Do not ask again for anything the user already supplied.

## Choose the data path

### User-provided data

Use the user's numbers exactly as provided unless they explicitly ask for independent verification.

- Preserve the exact metric name when known, such as median sale price, median list price, DOM, CDOM, active listings, or months supply.
- Preserve the stated geography and reporting period.
- Do not silently swap in a different source or metric.
- If the source or month is missing, label it honestly as `[SOURCE NEEDED]` or `[REPORTING PERIOD NEEDED]` rather than guessing.
- Treat numbers the user just supplied as confirmed for the current draft unless they contradict one another materially.

### Research mode

Research only when the user has not supplied the needed numbers or asks for verification.

Use this source order when possible:

1. Official local MLS or REALTOR association market report.
2. Official state REALTOR association report.
3. Government housing or census data for supporting context.
4. Reputable brokerage or housing portal data only when a stronger local source is unavailable.

Research rules:

- Prefer the latest fully published reporting period, not the current calendar month by assumption.
- State the exact reporting month or period. If data is released with a lag, say so plainly.
- Keep geography consistent across the primary stats. Do not mix city, county, metro, and zip-code numbers without labeling the difference.
- Keep metric definitions consistent. Do not substitute list price for sale price, DOM for CDOM, or active inventory for months supply without saying so.
- Prefer one primary source for the core three stats when possible.
- Cite the actual source page or report, not a search-result snippet.
- Never invent, interpolate, or project a missing number.

Use three useful stats when available, commonly:

- median sale price or another clearly labeled price metric
- days on market
- months supply or another clearly labeled inventory metric

If only two high-quality stats are available, use two. Quality beats forcing a third number.

## Verification gate for researched data

Before scripting researched numbers, show a compact verification block:

`MARKET DATA TO VERIFY`

- Metric: value
- Metric: value
- Metric: value
- Geography: [exact area]
- Reporting period: [month/date range]
- Source(s): [source names with citations]

Then say: `These are the numbers I’ll put in your mouth on camera. Confirm them or correct anything you want changed.`

Wait for confirmation before producing the final script when the numbers came from external research.

This verification gate does not apply when the user supplied the numbers themselves, unless they asked you to verify them.

## Build the story before writing

Determine the one market story the numbers actually support. Examples:

- prices are steady while homes are taking longer to sell
- inventory improved, giving buyers more choice
- competition remains strong despite a longer selling timeline
- seller expectations need to adjust because days on market increased

Do not force a bullish or bearish narrative. If the indicators conflict, say that the market is mixed and explain the tradeoff.

Translate every statistic into a practical implication. The value of the video is the interpretation, not the number.

## Output

Use these sections in this order.

### 60-SECOND SCRIPT

Write a camera-ready script of roughly 130 to 160 words.

Structure:

1. Hook: about 8 to 12 words and immediately local.
2. Stat 1: number, then what it means.
3. Stat 2: number, then what it means.
4. Stat 3 when available: number, then what it means.
5. Balanced buyer/seller takeaway, unless the user requested a buyer-only or seller-only version.
6. One clear CTA.

Write conversationally. Avoid sounding like a market report being read from a page.

### ON-SCREEN TEXT

Create one short line per primary stat.

- Keep each line under 6 words when practical.
- Lead with the number or key movement.
- Make each line readable on a phone.
- Do not add a statistic that is not in the verified data.

### CAPTION

Write a ready-to-post caption that:

- names the market and reporting period
- summarizes the market story in plain English
- includes the CTA
- includes a short source attribution
- uses a small, relevant set of hashtags rather than a hashtag wall

### FILMING NOTES

Give exactly 3 concise bullets covering:

- delivery
- framing
- energy or pacing

### SOURCE NOTES

List the exact metrics used, geography, reporting period, and sources. Distinguish user-provided data from independently researched data.

## Quality rules

- Never call lagged data “this month” unless it actually reports the current month. Use “latest published data” and name the period instead.
- Never invent statistics, sources, trends, quotes, or causal explanations.
- Do not infer a trend from a single point in time. Use YoY or MoM language only when the comparison is actually present in the source data.
- Do not say the market is a buyer's market or seller's market unless the evidence supports that characterization. Prefer describing the measurable conditions.
- If a line could fit any city, localize it with the actual market and a concrete decision buyers or sellers face there.
- Keep the framing balanced unless the user explicitly asks for a buyer or seller slant.
- Avoid fear-bait, certainty language, and claims such as “prices only go up,” “buy now before it’s too late,” or “the market is crashing” unless directly quoting and contextualizing a source.
- Follow Fair Housing rules. Discuss property characteristics, market conditions, amenities, and transactions, not protected classes or who belongs in an area.
- Do not give legal, tax, lending, or investment guarantees. Refer users to the appropriate professional when needed.
- Match the agent's established voice. Without a profile, use warm, direct, plain language.
- Avoid generic AI hype words such as unlock, supercharge, revolutionary, secret weapon, and game-changer.
- Prepare the content only. Do not publish, schedule, or send it unless the user separately requests an available action.

## Delivery close

After the package, add a short `Why this works` note of no more than 3 sentences explaining the story in the numbers and why it matters now.

Then offer: `Want a buyer-slant or seller-slant version too?`

End with: `Film it while the numbers are fresh. Next update, bring me the new stats and I’ll turn them into the next 60 seconds.`
