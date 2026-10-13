---
name: social-analyzer
description: "Audits the last 90 days of the user's own Instagram Reels, carousels, and feed posts (never Stories) and turns it into copy-paste formulas for future posts. Reads their signed-in account through the browser (Meta Business Suite or instagram.com), or a CSV export they upload, and scores every post against their goal using reach, views, likes, comments, shares, saves, follows, profile visits, and watch time. Then it studies the exact wording: first words, opener type, hook pattern, caption shape, and CTA lines. It delivers an HTML report (printable to PDF) with winning hook formulas in their own words, words that win and lose, a caption blueprint, their best CTA word for word, a swipe file, and a 30-day plan of ready-to-post hooks and captions. Use for \"audit my Instagram,\" \"what's working on my IG,\" \"which hooks work for me,\" \"social analyzer,\" \"content autopsy,\" \"why isn't my content performing,\" or \"review my last 90 days.\""
metadata:
  version: "1.2.0"
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Imported verbatim 2026-10-13 from the claude.ai Organization library (hand upload) so it syncs from the marketplace.
tier: plugin
zone: content
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "90-day Instagram audit into post formulas"
---

# Social Analyzer

Most creators decide what to post based on how a post felt, or on the one that went viral once. This skill replaces that guess with the user's own numbers. It studies 90 days of their Instagram grid, finds the patterns behind the posts that did their job, and turns that into a plan.

The deliverable is a report the user can act on this week. Data alone isn't useful to them. What they need is the **words**: which openings, phrases, and CTAs their audience responds to, turned into fill-in-the-blank formulas and ready-to-post hooks they can copy straight into their next posts. Every number in the report exists to prove a formula or a rule.

## Ground rules (read first, follow always)

**Read only.** In the browser, look and read. Never like, comment, follow, unfollow, message, post, edit, delete, boost, archive, or change any setting. Never click "Boost post" or "Promote." If a click might change something, don't make it.

**The user signs in, never you.** If they're logged out, ask them to sign in themselves, then continue. Never type a password or a login code. If a security check, CAPTCHA, or "confirm it's you" screen appears, stop and hand control back to the user.

**Downloads need a yes.** Before clicking any export or download button, tell the user the file name and source and wait for them to say yes.

**Their account only.** Only analyze the account the user owns and is signed into.

**Reels, carousels, and feed posts only. Never Stories.** Don't open, read, or count Stories, the Story archive, Highlights, or Live videos. In Meta Business Suite, filter them out. In a CSV, delete any row whose post type is Story before you analyze anything. If Stories slip into the data, remove them and note it in the data notes. They're temporary, they're measured differently, and they'd skew every comparison.

**Move at a human pace.** Wait for pages to load, and don't reload over and over. If Instagram shows a "try again later" or rate-limit message, stop, tell the user, and switch to the CSV route.

**Never invent a number.** Record metrics exactly as shown. When a metric isn't visible, mark it missing and say so in the report. Don't estimate it. Rounded displays like "1.2K" get recorded as 1,200 and noted as rounded.

## Step 1: Set up the run

Do this in one short exchange. Don't turn it into an interview.

1. **Goal.** Ask the user to pick one. It changes what "working" means.
   - **Grow followers:** new follows and reaching non-followers
   - **Reach more people:** views, shares, and non-follower reach
   - **Get leads:** profile visits, link taps, DMs, and comments that show buying intent
   - **Make sales:** the same as leads, weighted toward direct buying signals
   - **Build community:** comments, shares, and saves
2. **Profile.** Look for a `CONTENT PROFILE` block (from Hook Engine or Post Value Filter) in the conversation, project instructions, or saved preferences. If it's there, use it silently. If not, ask two questions: who the content is for (one sentence), and what they sell, if anything.
3. **Last snapshot.** Ask them to paste their last `SOCIAL ANALYZER SNAPSHOT` (or an older `CONTENT AUTOPSY SNAPSHOT`, which works the same way) if they've run this before. If they have one, the report will include a progress section.
4. **Timeframe.** The default is the last 90 days, ending yesterday. Use a different range only if they ask.

## Step 2: Check access and pick the route

Check which tools you have.

- **Browser tools available** (Claude in Chrome, Cowork, or another browser-control tool): use **Route A**.
- **No browser tools:** use **Route B**. Tell the user in one line: "I can't see your browser from here, so we'll use a quick export instead. It takes about two minutes."

Full step-by-step instructions for both routes, including what each metric means and where to find it, are in `references/data-collection.md`. Read it before you start collecting.

**Route A: browser.** Confirm the user is signed in and the account is a Professional account (Creator or Business). Collect metrics from the Meta Business Suite content table. If that isn't available, use per-post insights on instagram.com. Then open the top and bottom posts to read hooks, captions, CTAs, and comments.

**Route B: CSV.** Walk the user through exporting content data from Meta Business Suite and uploading the file. Captions come with the export. For the top and bottom posts, ask them to paste each Reel's spoken opener or on-screen text if they want hook analysis on video.

**Personal accounts:** Insights don't exist for personal accounts, so saves, shares, reach, and follows can't be analyzed. Tell the user plainly, explain that switching to a free Professional account takes a minute in Instagram settings, and note that insights only start collecting after the switch. Offer a limited analysis of likes, comments, and captions in the meantime. Don't switch the account for them.

## Step 3: Tag every post

Record the metrics for every post in the range, plus its **exact first line, first 5 words, and CTA line**. Then tag each one: format, angle or topic, hook pattern, opener type, caption length, CTA type, posting day and time, and (for Reels) length and whether there's on-screen text in the first frame.

Hooks, captions, CTAs, and comments need a closer read. Do that full qualitative pass on the **top 10 and bottom 10 posts** by goal score (or all of them if there are 30 posts or fewer). Tag the rest from their captions and metadata.

The tagging system, including the 12 hook patterns and the CTA categories, is in `references/analysis-method.md`.

## Step 4: Analyze

Follow `references/analysis-method.md`. The essentials:

- **Use rates, not raw counts.** Divide by reach (per 1,000 accounts reached) so small-reach posts aren't punished for reaching fewer people.
- **Score each post against the goal**, using the weights for the goal the user picked.
- **Compare with medians, not averages**, so one viral post doesn't warp everything. Report outliers separately.
- **Respect sample size.** A pattern needs at least 5 posts to be called Strong. With 3-4 it's an Early signal. With fewer than 3, don't draw a conclusion.
- **Flag confounders:** boosted posts, collabs, trending audio, and a big follower jump during the period.

If you can run code, use it for the math. If not, calculate carefully and show your working in the data notes.

## Step 4b: Language forensics (the most important step)

Follow `references/language-forensics.md` on every post. It produces:

- **Winning formulas:** 2-4 fill-in-the-blank hook formulas built from the user's own top posts, each with their real examples, the proof, and 3 ready-to-use hooks for new topics.
- **The formula to retire:** the opening their weakest posts share, with a before-and-after rewrite.
- **The first-words rule:** one sentence about how their best posts open.
- **Words that win and words to drop**, with post counts.
- **The caption blueprint:** a copy-paste skeleton of their best-performing caption shape.
- **Their best CTAs**, word for word, ranked.
- **The swipe file:** all of the above in one block they can copy into their notes.

If this step can't be done well (captions missing, too few posts), say exactly what's missing and ask for it. A report without formulas is the failure case this skill exists to avoid.

## Step 5: Build the report

Use `references/report-template.html`. Copy it exactly and fill in only the `REPORT` data object at the top of its script. The template draws the charts, the layout, dark mode, and the Save as PDF button. Don't rewrite the HTML or CSS.

The sample data in the template is there to show the shape. Replace every value with this user's real data. The report puts the words first and the numbers after, in this order: Do this first, winning formulas, the first-words rule and word lists, the caption blueprint and CTAs, the 30-day plan, the swipe file, then the supporting findings, charts, and top and bottom posts.

Field notes:
- `formulas`: 2-4 items from language forensics. `examples` are the user's real first lines, quoted exactly. `newHooks` are 3 ready-to-use hooks.
- `retire`: the formula to retire, with a `before` (their real line) and an `after` (rewritten with a winning formula). Use `null` if there's no clear pattern.
- `firstWordsRule`, `wordsWin`, `wordsLose`, `captionBlueprint`, `ctaScripts`, `swipeFile`: from language forensics.
- `breakdowns`: one chart per dimension. Always include "By first words" (opener type), plus format, angle, hook pattern, and CTA, and day posted or caption length if they show a finding. `median` draws the account-median line. Set `highlight: true` on the winning row. Include only groups with 3+ posts.
- `plan[].type`: `"double"`, `"fix"`, or `"experiment"`. `plan[].formula` names the formula it uses. `plan[].caption` is a short caption outline for that exact topic, following the blueprint.
- `confidence`: `"Strong"` or `"Early signal"`.
- `progress`: `null` on a first run.
- Any section with no data: use `[]` or `null`, and the template hides it.

Deliver it as an HTML file or artifact the user can open, save, and print. Tell them: "Click **Save as PDF** at the top, or open the file in your browser and print it. Choose 'Save as PDF' as the printer."

**How to write the findings:**
- Every finding has three parts: what you saw, the evidence (post counts, rates, and one or two example posts with dates), and what to do about it.
- Label confidence: **Strong** (5+ posts, a clear gap) or **Early signal** (3-4 posts, or a small gap).
- Be direct and specific. "Carousels that open with a client mistake got 3.1x the saves of your average post (6 posts)" beats "Educational content performs well."
- Write like a sharp strategist talking to the owner: plain words, no jargon, no hype. No em dashes, and none of: leverage, unlock, elevate, game-changer, journey, delve, "it's not X, it's Y."
- Don't pad. If the data doesn't support a section, say what's missing in one line instead of filling it.

**The one thing:** the report opens with the single highest-impact change the user can make. Choose it from the Strong findings only, and make it about words whenever the evidence allows, like "Open every post with your reader's role, the way your 5 best posts do," rather than "Post more carousels."

## Step 6: The 30-day plan

Build 12-16 posts at their current posting pace (never more than one extra post a week above what they already do). Split them roughly:

- **60% double down:** repeat the winning format, angle, and hook pattern on new topics.
- **30% fix and retry:** a promising angle that underperformed because of a fixable issue (weak hook, buried CTA, wrong format).
- **10% experiment:** one or two things the data hasn't tested yet.

Every plan item must be **copy-paste ready**, so the user can post it with only the real details filled in. Each one gets:
- week and format
- the angle and the **winning formula** it uses
- a **ready-to-post hook**, written out in full, within the 125-character cutoff
- a **caption outline** for that exact topic, following their caption blueprint, 3-5 short lines with `[slots]` only where a real detail is needed
- the **exact CTA line**, taken from their best-performing CTA wording
- a one-line "why" that points to the evidence

Draft hooks and captions follow the ground rules: no invented numbers, results, or stories. Use `[placeholders]` where the user needs to fill in a real detail.

Also turn the questions people asked in the comments into plan items. Questions from the audience are the cheapest content ideas available.

## Step 7: Profile update and snapshot

**Content Profile update.** Write a `What works for me` section drawn from the Strong findings only: the winning formulas (each written out, with one real example), the first-words rule, words to use and drop, the best CTA word for word, and the best format, angle, and posting window. This is how Hook Engine and Post Value Filter learn the user's own formulas, so keep the formulas exact. If the user has a Content Profile, give them the full updated block with this section added or replaced, and remind them to swap it into wherever they saved it. If they don't have one, give them the section on its own and mention that Hook Engine and Post Value Filter both read it.

**Snapshot.** Fill in the `snapshot` field in the report with the `SOCIAL ANALYZER SNAPSHOT` block (the format is in `references/analysis-method.md`), and also paste it at the end of your chat reply. Tell them: "Save this. Paste it in next time you run Social Analyzer and I'll show you what changed."

## Step 8: Wrap up in chat

Keep the chat reply short, because the report holds the detail. Include:
- the one thing to do first
- their #1 winning formula, with one real example and one ready-to-use hook
- three headline findings, one line each
- the report file, and how to save it as a PDF
- the profile update and the snapshot block
- one line pointing to the next step: "Paste your swipe file into your Content Profile, then ask Hook Engine to 'use my winning formulas' for your next post, and run the draft through Post Value Filter before posting." Mention those skills only if they're installed or the user has used them. Otherwise, skip this line.

## If something goes wrong

- **Fewer than 10 posts in 90 days:** extend to 180 days if they agree. If there still aren't enough, run the analysis anyway, label everything Early signal, and focus the plan on consistency.
- **Metrics missing for older posts:** analyze what's there and list the gaps in the data notes.
- **The layout doesn't match these instructions:** Instagram and Meta change their interfaces often. Look for the equivalent label (for example, "Accounts reached" instead of "Reach"). If you can't find something after a reasonable look, switch to the CSV route instead of guessing.
- **The user wants Stories analyzed:** this skill covers Reels, carousels, and feed posts only, by design. Say so in one line, and suggest they check Stories insights in the Instagram app.
