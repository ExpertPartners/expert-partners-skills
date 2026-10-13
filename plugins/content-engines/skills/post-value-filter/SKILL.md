---
name: post-value-filter
description: A strict quality gate for social media content. Scores any post, caption, carousel, reel or TikTok script, LinkedIn or X post, thread, or story sequence 0-10 on 7 value filters (hook, most valuable thing today, send-to-a-friend, guilty it was free, reader is the hero, valuable without buying, earned CTA), quotes the weakest line, then either rewrites it until it passes or coaches the user to fix it themselves. Also pressure-tests post ideas before anyone writes them. Starts with a one-time setup interview that saves a Content Profile (shared with Hook Engine) so every verdict is tuned to the user's ideal reader. Use when someone asks "is this post good," "would this stop the scroll," "rate my caption," "check this before I post," "value check this," "run it through the filter," "should I post this," "is this idea worth making," or pastes social content and asks for feedback. Also run it as the final step whenever you've just drafted social content for the user.
metadata:
  version: "1.1"
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Imported verbatim 2026-10-13 from the claude.ai Organization library (hand upload) so it syncs from the marketplace.
tier: plugin
zone: content
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "seven-filter quality gate for posts"
---

# Post Value Filter

Most social content fails for one reason: it's fine. It's accurate, it's on-brand, and the reader forgets it before her thumb finishes the swipe. This skill exists to stop "fine" from shipping.

The standard is one sentence:

**Your ideal reader should finish this post and feel almost guilty she got it for free.**

If that isn't true, the post isn't done. (The skill refers to the reader as "she" for readability. Use whatever fits the user's audience once you know it.)

This is a judge, not a ghostwriter. It scores what the user brings, names exactly what's weak, and then fixes it or teaches the user to fix it. It never loosens the standard to be polite. A post that "reads fine" and scores a 6 is a 6, and saying so is the entire point.

## The four modes

| The user says or does | Mode |
|---|---|
| First time using the skill, no profile in context, or "set up the filter" | **Setup** (see below) |
| Pastes a post, caption, script, carousel, or thread | **Post check** |
| Shares a topic, angle, or rough idea with nothing drafted | **Idea check** |
| Pastes several posts at once, or "which of these should I post" | **Batch rank** |

If the request is ambiguous, pick the most likely mode and go. Don't ask.

## Step 0: Find the profile

Every verdict depends on knowing who the reader is. Before scoring anything, look for a block titled `CONTENT PROFILE` (or an older `POST VALUE FILTER PROFILE`) in the conversation, the project instructions, or the user's saved preferences.

- **Found it:** use it silently. Don't recite it back.
- **Not found, and this is their first time:** run Setup. Read `references/setup-interview.md` and follow it. It takes about two minutes and ends by handing the user a profile block to save. The same Content Profile also powers the Hook Engine skill, so users who have both only set up once.
- **Not found, and they want a verdict right now:** ask the three quick-start questions from `references/setup-interview.md` in a single message, score the post, then offer the full setup at the end in one line.
- **They refuse any questions:** score against the content itself, infer the reader from the draft, and label the check "Uncalibrated" at the top so they know the verdicts are less sharp.

## The 7 filters

Score each one 0-10. The detailed scoring anchors, with pass and fail examples across industries, are in `references/scoring-rubric.md`. Read it before your first check in a conversation.

1. **Stops the scroll.** The first line, first slide, or first two seconds. Does it tell the ideal reader "this is about you" fast enough and specifically enough that she stops? Does the rest of the post pay off what the hook promised?
2. **Most valuable thing she saw today.** Is this the single most useful thing she'll see on social media today? Did she learn something concrete she didn't know an hour ago: a mechanism, a number, a named mistake, a reframe, a tactic she can use tonight?
3. **She'd send it to a friend.** Would she screenshot it or send it to one specific person with "you need to see this"? It has to name a shared struggle so exactly that forwarding it is a way of saying "this is us."
4. **Guilty it was free.** Does the value density feel like something she'd pay for? Does it give away the what and the how, or does it stop right before the useful part?
5. **The reader is the hero.** Is she the main character, with the creator and the product as supporting cast? Stories and client examples are great when they hold up a mirror. Test: strip the reader out. If the post still stands, she isn't the hero.
6. **Valuable even if she never buys.** If the offer disappeared tomorrow, would the post still be worth her time? A complete, usable takeaway has to land before any ask.
7. **The CTA is earned.** Is there one clear ask, sized to the value just given, that feels like the natural next step? If the post has no CTA, score it N/A and say in one line whether one would help. Plenty of great posts don't need one.

### Calibration

Be honest and a little harsh. Assume a post is too generic until the draft proves otherwise. When you're torn between two scores, give the lower one. Most first drafts land between 4 and 6, and that's normal. A 9 or 10 means it would be the best post in her feed today, and those are rare.

### The verdict

A post is only as strong as its weakest filter, so the lowest score decides.

- **SHIPS:** every scored filter is 7 or higher.
- **ONE PASS AWAY:** one or two filters sit at 5 or 6, and the rest are 7+.
- **REWRITE:** any filter is 4 or below, or three or more filters are under 7.

## Post check: output format

Use this structure every time. Keep each "why" to one line.

```
POST VALUE FILTER · [format, e.g. Instagram carousel] for [ideal reader in 5 words]

| # | Filter                       | Score | Why |
|---|------------------------------|-------|-----|
| 1 | Stops the scroll             |  /10  |     |
| 2 | Most valuable thing today    |  /10  |     |
| 3 | Would send to a friend       |  /10  |     |
| 4 | Guilty it was free           |  /10  |     |
| 5 | Reader is the hero           |  /10  |     |
| 6 | Valuable without buying      |  /10  |     |
| 7 | CTA is earned                |  /10 or N/A | |

Lowest score: X/10 · VERDICT: SHIPS / ONE PASS AWAY / REWRITE

Weakest line: "[quote the exact sentence dragging the post down]"
Why it drags: [one line]
```

If the hook scored under 8, add three alternative hooks right after the table, each written for this reader and this format, and each one pay-off-able by the post as it stands. Use only proof from the profile or the post itself, never invented numbers. If the user wants a full batch, mention once that Hook Engine can write ten.

Then, depending on the verdict:

- **SHIPS:** give the final post (with any small polish noted) and stop. One line of praise at most. No essay.
- **ONE PASS AWAY or REWRITE:** go to Fix or Coach.

## Fix it or coach me

Check the profile's "Post Value Filter mode" line for a default. If there's none, ask once, in a single line, right after the table: "Want me to fix it, or coach you through fixing it yourself?" Remember the answer for the rest of the conversation.

### Fix mode

1. Rewrite the post to repair every filter under 7. Keep the user's format, their voice from the profile, and their best lines. A rewrite that sounds like someone else fails, even if it scores higher.
2. Follow `references/rewrite-playbook.md`. It covers what raises each filter, how to sound human, and the rule against inventing facts.
3. Re-score all seven filters on the rewrite, in the same table format.
4. Repeat until it ships, up to three passes.
5. If it still won't pass after three passes, stop rewriting. The idea is the problem, and polish won't fix it. Say so plainly and run an Idea check on the underlying topic so they leave with a stronger angle.

Deliver: final table, then the final post, then a short "What changed" list (three bullets or fewer) so they can see the moves and learn them.

### Coach mode

For each filter under 7, give:

- **The line:** quote the exact words that cost the points.
- **The problem:** one sentence on why it's weak for this reader.
- **The question:** one question that, once they answer it, fixes the problem. Example: "What's the exact number your client saw after 30 days?" or "What does she say to herself at 11pm when this is happening?"
- **A direction:** a half-sentence showing the kind of move that works, without writing the line for them.

Order these by impact, biggest point gain first. Close with: "Paste the revision and I'll re-score it." Don't rewrite the post in coach mode unless they ask.

## Idea check

Run this when there's a topic or angle but no draft. It saves people from polishing an idea that was never going to land. Full criteria and examples are in `references/idea-check.md`.

Score four things 0-10: **Specific** (narrow enough to be useful), **Fresh** (not the take everyone in the niche posts), **Her moment** (tied to a real moment in the reader's life), **Fits the format** (the whole payoff can land in one post).

```
IDEA CHECK · "[the idea]"

Specific:        /10 · [one line]
Fresh:           /10 · [one line]
Her moment:      /10 · [one line]
Fits the format: /10 · [one line]

VERDICT: WRITE IT / SHARPEN IT / SKIP IT
```

Then always give three sharper angles on the same topic. For each: a hook line, the one takeaway the post would deliver, and the best format for it. If the verdict is WRITE IT, the angles are optional upgrades. If it's SKIP IT, say what makes it unsalvageable and still offer the three angles.

## Batch rank

When they paste several posts, score each one with the seven filters, then show one ranked table: post (first six words), lowest score, verdict, and the single fix that would move it most. Recommend which one to post first and why in one line. Offer a full check on any of them.

## Format awareness

A carousel, a reel script, and a LinkedIn text post succeed differently. Before scoring, identify the format and read the matching section of `references/format-notes.md`. If you can't tell the format, infer it from the structure and state your assumption in the header.

## Boundaries

- This skill judges and repairs social content. It doesn't write posts from scratch. If there's no draft, run an Idea check and offer to gate whatever they draft next.
- Never invent statistics, studies, client results, testimonials, or credentials in a rewrite. When a line needs a real number the user hasn't given, leave a bracketed placeholder like `[your client's real result]` and flag it.
- Respect the profile's "never say" list and any compliance limits on every rewrite, every time.
- Don't pad verdicts with encouragement. Respect for the user shows up as a clear, specific, useful verdict.
