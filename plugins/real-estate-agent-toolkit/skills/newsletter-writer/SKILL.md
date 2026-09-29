---
name: newsletter-writer
description: Writes a monthly email newsletter the agent's database actually reads, built from 6 inputs gathered in 5 minutes. Use when the agent says write my newsletter, monthly email for my database, newsletter for June, asks for a monthly email to send their contacts, or says they don't know what to send their database.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "monthly database newsletter"
---
# Newsletter Writer

You write a real estate agent's monthly email newsletter, 350–500 words their
database actually reads: from 6 inputs the agent gathers in 5 minutes. This is how
they stay top-of-mind every month without a marketing team.

## Before you start

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. If found, use them silently for voice, market, niche, proof, and CTA. The agent's own documents win over this skill's defaults. Never re-ask anything they answer. This skill reads the profile and never edits it.
2. If there is no agent profile, ask only the minimum inputs for this run (one message,
   batched). Still deliver in full, placeholders like [YOUR MARKET] beat stalling.
   In that case, AFTER the closing line, add: "Tip: the Agent Brain Builder writes a profile that makes every skill in this toolkit sound like you automatically."
3. If everything needed was already given: generate immediately. Zero questions.

### The first message

If the agent's message already contains the 6 inputs: no form. One warm line,
"Using your agent profile: building your [Month] newsletter for [market] now.",
then straight to work. (No profile? Same line, minus the agent profile mention.)

Otherwise send this form, ONE message, nothing before or after it:

> Your monthly newsletter: send me 6 quick things and I'll write the whole thing,
> 350–500 words your database actually reads. About 5 minutes to gather, then I do
> the rest.
>
> 1. Market stat #1 (e.g., median price): ____
> 2. Market stat #2 (e.g., days on market): ____
> 3. Market stat #3 (e.g., inventory): ____
> 4. Local happening #1 (an event, opening, or seasonal thing around town): ____
> 5. Local happening #2: ____
> 6. One personal note: something real from your month (2 sentences is plenty): ____
>
> No idea where to find these? Say "help" and I'll give you the 5-minute list.
>
> Reply in one message: short, messy answers are perfect.

No agent profile: add one line to the SAME form, "7. Your name, market, and go-to
call-to-action (skip any: blanks are fine): ____". Never a second message.

If they say "help" or "I don't have any of this": reply with the **"where to find
these in 5 minutes"** list AND, in the same message, still deliver the full
newsletter with bracketed placeholders (e.g., [MEDIAN PRICE, per your MLS
report]) they can swap in. Never stall the run. The list:
- Market stats: your MLS monthly report, your broker's market snapshot, or the
  last market email your title rep or lender sent you.
- Local happenings: your city's events calendar, the local news site, a community
  Facebook group, or "what's opening near me", pick the 2 most interesting.
- Personal note: one real thing from your month, a closing, a client moment, a
  family thing, something you tried. Two sentences is plenty.

Once the inputs land → write the newsletter. Delivery order, every run: all
outputs → **Why this works:** (2–3 sentences max: the strategy behind this issue,
why these stats/stories will get read, plus the one thing to do today, usually
"send it before Friday while the happenings are still ahead") → offer "Subject
line A/B pair?" → the closing line (→ then the no-profile Tip, if it applies).

## Output (use these exact section names)

**THE NEWSLETTER**: 350–500 words total across the four sections (table included;
subject lines and plain-text version don't count). Count the words before
delivering: if outside 350–500, revise first, and show "(N words)" after the
THE NEWSLETTER heading. In this order:
- **MARKET MINUTE**: the 3 stats translated into plain English (what each means
  for a normal homeowner or buyer), with the numbers in a small table. Every stat
  attributed ("per [source], as of [month]"). If the agent gave fewer than 3 stats,
  use a placeholder row (e.g., [DAYS ON MARKET, per your MLS report]), never
  invent the missing number.
- **AROUND TOWN**: the 2 local happenings, written like a friend's recommendation,
  not a press release.
- **PERSONAL CORNER**: the personal note, in the agent's voice. Human, short, real.
- **ONE CTA**: exactly one call to action (from the agent profile if it exists), one line.

**3 SUBJECT LINES**: three options: one curiosity, one number-led, one local.

**PLAIN-TEXT VERSION**: the full newsletter as clean plain text with simple line
breaks, for agents without an email tool. Paste-ready into any email. Render the
market table as simple "label: value" lines, no table markup.

Deliverable: formatted .docx + the plain-text copy block in chat.

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

## Visual view

Build the visual view as a single self-contained HTML page, or with your tool's canvas or visual page feature if it has one. If neither is possible, deliver a clean formatted table instead and say so.

**NEWSLETTER PREVIEW**: also render a formatted visual page showing the newsletter as
readers will see it: header, the four sections, and a styled market table. This is
the "watch the AI build a newsletter in 2 minutes" on-camera shot. Clean, modern,
brand colors if the brand direction exists. The .docx stays the document of record;
the visual page is the visual preview. It never requires integrations and never stores
data: refreshed by re-running the skill.

## Rules

- Every stat attributed to its source. Never invent or adjust a number.
- No predictions, no "now is definitely the time" claims, report what happened,
  not what will happen.
- Boundary: this skill shares inputs with the Market Video Scripter but serves
  EMAIL: if the agent wants a market video, that stays with the Market Video Scripter.
- If any line could appear in any city's newsletter, rewrite it with a local
  anchor: a named neighborhood, street, or event from the agent's market. Stats
  never stand alone: every number gets its plain-English "what this means for you."
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

"Same time next month, 6 new inputs. That's the whole system."

## Worked example (demo world)

Demo agent: Jordan Lee · Example Realty · Charlotte, NC · 2nd-year agent · niche:
first-time buyers + move-up sellers · voice: warm, direct, zero corporate-speak ·
goal: $150K GCI.
Demo market stats (attribute as "per Canopy MLS, June 2026"): median price $485K
(+2.1% YoY) · 28 days on market · 2.4 months of inventory.

First message (no-profile case): the 6-input form above, with line 7 (name, market,
CTA) added.

Inputs: the 3 demo stats · 2 happenings (new greenway section opens Saturday; food
truck Fridays back at South End) · personal note (Jordan's clients Tom & Jess just
had a baby: second closing anniversary this month).

Sample of THE NEWSLETTER:

> **MARKET MINUTE**: Charlotte homes are selling in about 28 days, quick, but not
> the frenzy of two years ago. The median price hit $485K, up 2.1% from last June.
> Translation: sellers still have the edge, but buyers finally have room to breathe.
>
> | Stat | June 2026 | Source |
> |---|---|---|
> | Median price | $485K (+2.1% YoY) | per Canopy MLS, June 2026 |
> | Days on market | 28 | per Canopy MLS, June 2026 |
> | Months of inventory | 2.4 | per Canopy MLS, June 2026 |
>
> **AROUND TOWN**: The new greenway section opens Saturday, flat, shaded, perfect
> for a stroller. And food truck Fridays are back at South End; go early, the tacos
> sell out.
> **PERSONAL CORNER**: Two years ago I handed Tom & Jess their keys. This month
> they brought a baby home to that same house. This is why I do this job.
> **ONE CTA**: Curious what your home is worth in this market? Reply "value" and
> I'll run your numbers this week.

Sample of 3 SUBJECT LINES: "What 28 days means for your house" · "Charlotte hit
$485K: here's the part nobody mentions" · "The greenway opens Saturday (+ June
market numbers)"
