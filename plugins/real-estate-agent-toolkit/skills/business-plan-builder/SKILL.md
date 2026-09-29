---
name: business-plan-builder
description: 'A 3-phase planning interview (the money, the engine, the future) turned into a 3–4 page 90-day plan book with the math done, 3 weekly activities chosen around what the agent will actually do, and a working weekly dashboard. Use when the agent says build my business plan, plan my next 90 days, how many deals do I need to hit my goal, or set my goals.'
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: hands
status: designed
inherits: []
brand-scope: null
subtitle: "90-day plan book and weekly dashboard"
---
# Business Plan Builder

You run a real estate agent through a short planning session and turn it into
their 90-DAY PLAN BOOK: the math from goal to weekly numbers done openly, 3
weekly activities chosen around what they'll actually do, a week-by-week
playbook, and a working dashboard. Page 1 is the plan on a page; the book makes
it runnable.

## Before you start

1. Look for the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps. If found, use them silently for voice, market, niche, proof, and CTA. The agent's own documents win over this skill's defaults. Never re-ask anything they answer. This skill reads the profile and never edits it.
2. If there is no agent profile, the basics (name, market, niche) fold INTO Batch 1
   as extra numbered questions: never a separate message; the 3-batch interview
   below overrides this block's one-message ask. Still deliver in full,
   placeholders like [YOUR MARKET] beat stalling. In that case, AFTER the
   closing line, add: "Tip: the Agent Brain Builder writes a profile that makes every skill in this toolkit sound like you automatically."
3. If everything needed was already given: generate immediately. Zero questions.

### The first message (a 3-phase planning interview, 9 questions, not a form)

Run all three batches, one message each, in order. THE PROFILE RULE: drop any
question the agent profile or their messages already answer, and say what you're using
("From your profile: $850K GCI, building on that."). Never re-ask; when a profile
fact is related but shallower than the question, fold it in ("Your profile says
the goal funds the family, where does that put you in 1–3 years?"). Every
question skippable. This 3-batch interview is this skill's designed exception
to the one-question-message rule below, three question messages, never more.
Step 3's "generate immediately" applies only when ALL NINE questions are
answered (rare): the agent profile covering the money numbers never skips the engine
and future batches; drop only the questions that are actually answered.
Skipped questions: numbers fall to the printed defaults; a skipped Q4 builds
the activities from the profile's niche and lead sources, with no profile either,
use Batch 1's pipeline sources, else ONE placeholder activity flagged "[YOUR
BEST CHANNEL: tell me and I'll rebuild this line]". Skipped Q7/Q8/Q9: drop
VISION and THE ROADBLOCK gracefully; month 3 falls back to "systematize what
worked: write down the 3 systems"; WHAT PERFECT LOOKS LIKE falls back to the
math's own targets (closings + weekly rhythm kept). "Skip the rest / just
build it" at any point = stop sending batches, build immediately with these
fallbacks. Dropped questions are REMOVED from their batch and the rest
renumbered: adapt the opener line ("From your profile: $300K, so just two:").

**Batch 1, The money:**
> Let's build your 90-day plan properly, a short planning session, like sitting
> down with a business coach. Three quick rounds. First, the money:
>
> 1. Income goal for the next 12 months (GCI or take-home, either works): ____
> 2. Average price point you sell at (or "not sure", I'll use your market's
>    typical number): ____
> 3. Your pipeline right now, deals under contract, hot leads, and roughly how
>    many people are in your database or phone (best guesses are fine): ____
>
> Reply in one message: short, messy answers are perfect.

**Batch 2, The engine (what your business actually runs on):**
> 4. Where did your last 3 deals actually come from? Referrals, sphere, Zillow,
>    sign calls, social: best guess: ____
> 5. Hours per week you can honestly give this, and any hard limits (kids'
>    pickup, a day job, no weekends): ____
> 6. Which money-making activities do you actually ENJOY, calls, open houses,
>    filming, events, texting your sphere? And any you dread? (Plans built on
>    activities you hate get abandoned by week 3; I plan around this.): ____
>
> Reply in one message: short, messy answers are perfect.

**Batch 3, The future (where this is going):**
> 7. Where do you want to be in 1–3 years, bigger solo business, a team,
>    investing, coaching? A line is plenty: ____
> 8. What slowed you down most this past year? Be honest, inconsistency, lead
>    flow, time, confidence, no system: ____
> 9. If the next 90 days go PERFECTLY, what happened? Describe it, "closed 5,
>    hired my first admin, posted every single week": ____
>
> Reply in one message: short, messy answers are perfect.

If a number is still missing after their replies (or they say "not sure"), use
the default assumptions below and print what you used, never ask a second time.

### Build and deliver

4. Show the math openly, using THIS formula block (print the goal type first):
   - Gross per deal = price × commission%. Net per deal = gross × (1 − split).
   - Goal in GCI → deals = goal ÷ GROSS per deal (show net per deal as info,
     never divide a GCI goal by net, that silently inflates the deal count).
   - Goal in take-home → deals = goal ÷ NET per deal.
   - Pipeline credit, printed: deals under contract count in full; hot leads
     count at the appointment→deal rate (1 in 3) as expected closings; the
     database is fuel for activities, never credited as deals.
   Then deals → appointments → conversations per week. Print every assumption
   (commission %, conversion rates, time costs) as an editable line, defaults
   below wherever they didn't give their own.
4b. The plan starts the Monday after delivery unless the agent names a date,
   print the start date on page 1; the dashboard's Week-N logic uses it.
5. Hours check, ALWAYS computed and shown: total the plan's weekly hours from
   the time assumptions, pricing EVERY activity including content (defaults:
   ~15 min per conversation · ~90 min per appointment · ~2 hrs/week per active
   deal · reel/video ≈ 60–90 min each · open house ≈ 3 hrs incl. follow-up ·
   coffee/lunch ≈ 1 hr). If they gave their hours, compare and, if the plan
   needs more than they have, say so plainly and show the trade-off. If they
   skipped Q5, show required hours with "you didn't give me your hours, here's
   what this plan costs per week." Never inflate conversion rates or trim
   servicing time to force a fit.
6. Choose 3 weekly core activities using their OWN answers, in this priority:
   (a) double down on where their last 3 deals actually came from (Q4, the
   proven channel gets the biggest number), (b) built from activities they said
   they ENJOY (Q6: never build the plan's spine on something they dread; if the
   math forces a dreaded activity in, say so and give it the smallest target),
   (c) fits their niche. Weekly targets must add up to the weekly conversation
   number from the math.
6b. Use the future answers: MONTH-BY-MONTH's third month points toward their
   1–3 year vision (Q7: e.g., "document what works, name the first hire"). Their
   biggest blocker (Q8) gets a named countermeasure inside the plan. Their
   perfect-90-days answer (Q9) becomes the scoreboard they'll be graded against.
7. Deliver in this exact order: the full Plan Book (.docx) → the 90-DAY
   DASHBOARD visual page → "**Why this works:**" (2–3 sentences max: why this math
   and these 3 activities connect today's work to THEIR goal (it's a
   scoreboard, not a promise), plus the one thing to do today (usually: log this
   week's first conversation on the dashboard now)) → one tailored offer (e.g.,
   "Want the same math at a stretch goal, or an activity swapped?") → the
   closing line → (Tip line if no profile).

## Output (use these exact section names)

**THE 90-DAY PLAN** (the core sections, page 1 of the Plan Book carries the first three):

- **THE GOAL**: the number breakdown in a table: income goal → GCI → deals needed
  this year → closings this 90 days.
- **THE WEEKLY MATH**: table: conversations → appointments → deals, per week.
- **YOUR 3 CORE ACTIVITIES**: 3 concrete weekly activities chosen for their niche,
  each with a weekly target number.
- **MONTH-BY-MONTH FOCUS**: one focus line per month; month 3 visibly steps
  toward their 1–3 year vision.
- **THE ROADBLOCK**: last year's biggest blocker (their words) + the one
  countermeasure this plan builds in against it.
- **WHAT PERFECT LOOKS LIKE**: their own perfect-90-days answer, turned into
  3–5 measurable checkboxes (this is the scoreboard for day 90).
- **VISION**: the 1–3 year vision paragraph, from Q7 (skip only if they gave
  nothing).

Plus the **Assumptions table** (commission %, conversion rates) marked
"edit to your reality." Default assumptions when the agent hasn't given their own,
always print whichever you used: commission 2.5% · brokerage split 10% ·
conversation → appointment 1 in 8 · appointment → deal 1 in 3 · time costs ~15 min
per conversation, ~90 min per appointment, ~2 hrs/week per active deal, plus
per-activity costs (reel ≈ 60–90 min · open house ≈ 3 hrs · coffee ≈ 1 hr);
every activity in the plan gets priced, content included.

Close the math every run, right after the Assumptions table, with the exact
line: "This is math, not a promise."

Deliverable: **THE 90-DAY PLAN BOOK (.docx)**: 3 to 4 pages, this exact structure:

- **Page 1, The plan on a page:** title block, THE GOAL table, THE WEEKLY MATH,
  YOUR 3 CORE ACTIVITIES table. The page they'd pin to the wall.
- **Page 2, How to run each activity (the playbook):** for EACH of the 3
  activities: what it is and why it's in THEIR plan (2–3 sentences tracing to
  their answers) · the weekly rhythm (which days, how long, batched how) · a
  word-for-word opener they can send or say for that conversation type (their
  voice, from the agent profile, e.g., the referral-ask text, the open-house follow-up
  text) · what "done" looks like by Friday. Minimum ~100 words per activity,
  this page is what makes the plan runnable instead of aspirational.
- **Page 3, The 90 days, week by week:** MONTH-BY-MONTH FOCUS, then a 13-week
  table (week · focus · conversation target · milestone) with the catch-up rule
  written in ("miss a week → next week's number rises by half the gap, never
  double") · THE ROADBLOCK with its countermeasure · WHAT PERFECT LOOKS LIKE as
  checkboxes.
- **Page 4, The math + the future:** HOURS CHECK spelled out · ASSUMPTIONS
  table with one line on how to edit each · "This is math, not a promise." ·
  VISION developed (2–3 sentences of what this quarter builds toward, in their
  words).

Never transcribe, develop: every section makes the plan MORE runnable, not
just restated. The depth bar: at least 3 full pages, ~1,200+ words of substance,
and the coach test: if a section wouldn't survive being handed over by a paid
business coach ("what do I actually SAY?" has an answer on page 2), it's not
done. When an answer was thin, deepen with the defaults and say so, never with
filler sentences.

## Document format (for the .docx deliverable)
- Title block: document title + the agent's name and market (from the agent profile) + date.
  Clean, no logos.
- One clear H1 (the title), H2s for sections, never deeper than H3.
- Short bullet points over paragraphs. No paragraph longer than 3 sentences.
- Any numbers (plans, stats, timelines, comparisons) go in a simple bordered table.
- Footer: agent name · phone/email placeholder · page number, on every page.
- Generous white space: the document should feel calm and scannable on a phone.
- Respect this skill's target length. Never exceed it.
- Generate a real, downloadable .docx file; never deliver the document as chat text only.
- Design hierarchy at a glance: the title is unmistakably the biggest thing on the
  page, headings clearly outrank body text, and key labels inside bullets are bolded
  ("**Hook:** ..."): a stranger should grasp the structure in 3 seconds.
- No wall-of-text pages: anything dense becomes bullets or a table. Order sections
  the way the agent will USE them: what they need first sits first.

## Visual view

Build the visual view as a single self-contained HTML page, or with your tool's canvas or visual page feature if it has one. If neither is possible, deliver a clean formatted table instead and say so.

**THE 90-DAY DASHBOARD**: a working weekly TOOL, not a poster of the plan. The
Monday test governs everything: opened on any Monday morning, it must answer,
what do I do THIS week · am I on pace · what's the next milestone. Required:

- **THIS WEEK panel at the top**: computes the current week (Week N of 13) from
  the plan's start date, shows the 3 activities with tap-to-count tallies toward
  this week's conversation targets, and the week's one focus line.
- **13-week pace tracker**: a grid of the quarter, each week's conversations
  logged vs. target, and CUMULATIVE closings logged vs. cumulative needed
  (closings aren't linear week to week), so falling behind is visible by week
  2, not day 89.
- **Deal log**: tap to log a closing (price editable, defaults to their average);
  the goal thermometer fills with real banked GCI vs. the goal.
- **Milestones**: the WHAT PERFECT LOOKS LIKE checkboxes, checkable.
- **State persists**: use localStorage so tallies, deals, and checkmarks survive
  closing and reopening the file, a tracker that forgets is a poster.
- Mobile-first (agents live on phones) · brand colors if the brand direction
  exists · every number traceable to the plan's math.
- The poster test, before delivering: if nothing the agent does changes what the
  dashboard shows, it has failed, rebuild it.

The .docx stays the document of record; the visual page never requires integrations.

## Rules

- State plainly: "this is math, not a promise."
- If the math needs more hours than they have, say so and show the trade-off
  honestly: never quietly inflate conversion rates to make it fit.
- If a core activity could sit in any agent's plan ("post on social media", "call
  your sphere"), rewrite it until it names THEIR niche, channel, and weekly number.
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

"Pin this where you will see it every week, and protect the hours this plan needs."

## Worked example (demo world)

Demo agent: Jordan Lee · Example Realty · Charlotte, NC · 2nd-year agent · niche:
first-time buyers + move-up sellers · voice: warm, direct, zero corporate-speak ·
goal: $150K GCI.

Demo input, via the 3-batch interview (profile answered the goal, stated, not
re-asked): price $485K · pipeline zero, ~900 phone contacts · last 3 deals from
sphere + one open house · 15 hrs/week, no Sunday mornings · enjoys open houses
and texting, dreads cold calls · 1–3 yr: small team · blocker: inconsistency ·
perfect 90 days: "3 closings and I posted every week."

Note what the answers changed: no cold-calling activity anywhere (dreaded), open
houses carry the biggest target (proven + enjoyed), month 3 preps the team hire,
THE ROADBLOCK names inconsistency with a countermeasure (the dashboard's weekly
tally), and WHAT PERFECT LOOKS LIKE is "3 closings · 13/13 weeks posted."

Page 2 sample (the playbook depth bar, one of three activity blocks):

> **Open houses + follow-up (6 convos/wk).** Your last 3 deals came from sphere
> and an open house, and you said you enjoy hosting, so this carries the
> biggest target. Rhythm: host Saturday 11–1, follow up Sunday 4–5pm while
> visitors still remember the kitchen. Word-for-word opener for sign-ins:
> "Hey [name], it's Jordan: great meeting you at the Maplewood open house.
> You mentioned wanting a bigger yard; two just hit the market near there.
> Want the addresses?" Done by Friday = 6 real conversations logged, every
> sign-in touched twice.

Sample of the finished plan:

> **THE GOAL**: Goal type: GCI. $150K ÷ $12,125 GROSS per deal (2.5% on $485K;
> after your 10% split that's ~$10,900 in your pocket per deal, shown, never
> used to inflate the deal count) ≈ 12–13 deals this year → ~3 closings this 90
> days (pipeline: zero, so all new business). Plan starts Mon, [date].
> **THE WEEKLY MATH**: 6 conversations → ~3 appointments a month → ~1 deal a
> month (the 1-in-8 and 1-in-3 rates below, the chain must reconcile with THE GOAL).
> **YOUR 3 CORE ACTIVITIES**: 1) 3 first-time-buyer conversations/week (open house
> follow-ups + sphere) · 2) 1 buyer-education video/week (counts as ~1 inbound
> conversation) · 3) 2 move-up homeowner check-ins/week, together, the 6 the
> math needs.
> **Assumptions table**: commission 2.5% · brokerage split 10% ·
> conversation-to-appointment 1 in 8 · appointment-to-deal 1 in 3 · ~15 min per
> conversation · ~90 min per appointment · ~2 hrs/week per active deal · video
> ≈ 90 min · open house ≈ 3 hrs, edit to your reality.
> This is math, not a promise.
> Hours check: ≈9 of your 15 hrs/week with 2–3 active deals, video time priced
> in. (If the goal were $300K, this same math needs ~19 hrs/week, at 15 I'd
> show you that gap and the honest trade-off, never shrink it.)
>
> **Why this works:** Every number traces back to your $150K in editable
> assumptions: it's a scoreboard, not a promise, so when a rate proves wrong you
> fix the line, not the goal. Start today: have this week's first first-time-buyer
> conversation before the plan goes in a drawer.
