# Analysis Method

## 1. Rates

For every post with reach data, calculate per 1,000 accounts reached:

- **Save rate** = saves ÷ reach × 1,000
- **Share rate** = shares ÷ reach × 1,000
- **Comment rate** = comments ÷ reach × 1,000
- **Like rate** = likes ÷ reach × 1,000
- **Follow rate** = follows ÷ reach × 1,000
- **Profile visit rate** = profile visits ÷ reach × 1,000
- **Link tap rate** = link taps ÷ reach × 1,000
- **Reach ratio** = reach ÷ follower count (how far past the existing audience a post traveled)

If reach is missing but views exist, use views as the denominator for every post and say so. Never mix the two.

## 2. Goal score (0-100)

For each metric, find each post's **percentile rank** within this account (0 = worst post, 100 = best). Then combine them with the weights for the user's goal:

| Metric | Grow followers | Reach more people | Get leads | Make sales | Build community |
|---|---|---|---|---|---|
| Follow rate | 40 | 10 | 15 | 10 | 5 |
| Share rate | 20 | 30 | 10 | 5 | 25 |
| Save rate | 15 | 10 | 20 | 15 | 25 |
| Reach ratio | 15 | 35 | 5 | 5 | 5 |
| Non-follower % | 10 | 15 | 0 | 0 | 0 |
| Comment rate | 0 | 0 | 10 | 10 | 40 |
| Profile visit rate | 0 | 0 | 25 | 25 | 0 |
| Link tap rate | 0 | 0 | 15 | 30 | 0 |

When a metric is missing for the whole account, drop it and rescale the remaining weights to 100. Say which metrics were dropped. When it's missing for only some posts, score those posts on what they have, and note it.

**Buying-signal comments** (from the qualitative pass) count as a tiebreaker for Leads and Sales, and they get mentioned in the findings.

## 3. Tagging

Tag every post on each dimension below.

**Format:** Reel, carousel, image.

**Angle or topic:** build 4-8 angle groups from the captions, using the Content Profile's audience and offer as a guide. Name them in plain language based on what the posts do for the reader, like "client mistakes," "behind the scenes," "step-by-step how-to," "myth vs. reality," "personal story," "offer or promo," or "results and case studies." Every post gets one primary angle.

**Hook pattern** (from the first line or first frame). These match the patterns in Hook Engine:

| Pattern | Looks like |
|---|---|
| Start-Over Plan | "If I had to start over / from zero..." |
| Low Point | A specific personal hard moment |
| Before/After | A specific before state and after state |
| Credential Bridge | Leads with a number, credential, or experience |
| Wrong Answer | Sets up the obvious answer, then overturns it |
| Signs You're | "Signs you're..." / "You're X if..." |
| Mistake Warning | "Stop doing X" / "The X mistake..." |
| Rating | Scores something out of 10 |
| Honest Admission | Leads with a weakness, then a strength |
| Bold Declaration | One punchy, quotable statement |
| Her Exact Words | Opens with a client's phrase |
| Hot Seat | Breaks down a specific client or scenario |
| Other: [describe] | None of the above |
| No hook | Opens with a greeting, context, or throat-clearing |

**Opener type and wording signals:** tag these for every post using `language-forensics.md` (identifier, you-first, number, question, warm-up, and so on, plus the five signals such as "names who it's for in the first 5 words").

**Caption length:** short (under 125 characters, all visible before "more"), medium (125-500), long (500+).

**CTA type:** none, comment a keyword, link in bio, DM me, save this, share or send this, follow for more, question to answer in the comments, direct offer.

**Timing:** day of week, and a time block (morning 5-11, midday 11-2, afternoon 2-5, evening 5-9, late 9-5), in the user's timezone.

**Reels only:** length (under 15s, 15-30s, 30-60s, 60-90s, 90s+), on-screen text in the first frame (yes or no), and audio (original or trending).

## 4. Comparisons

For each dimension, compare groups by their **median goal score** and median key rates. Use medians, so one viral post can't distort a group.

**Sample-size rules:**
- A group with 5+ posts can support a **Strong** finding, if the gap from the account median is at least 25%.
- A group with 3-4 posts, or a gap of 10-25%, is an **Early signal**.
- Fewer than 3 posts, or a gap under 10%: no finding. Say "not enough data."

**Outliers:** any post scoring more than 3x the account's median on its top metric is an outlier. Feature outliers in their own callout ("What made this one pop"), and don't let one outlier carry a whole group's conclusion.

**Confounders:**
- Exclude boosted posts from comparisons and list them in the data notes.
- Flag collabs, whose reach includes the partner's audience.
- If followers grew more than 20% during the period, compare the first half of the period with the second half separately, since later posts had a bigger audience.
- If the user changed format or topic midway, say so, because timing and topic can be tangled together.

**Trend:** compare the median goal score of the first 45 days with the last 45 days. Report whether content is trending up, flat, or down.

## 5. What to look for beyond the obvious

Check each of these and report any Strong or Early signal:

- **The hidden winner:** a format or angle with low views but a high save or share rate. It works for the people who see it, so it needs better hooks or distribution, not less effort.
- **The empty calorie:** posts with high views or likes but near-zero saves, shares, and follows. They feel good and do little for the goal.
- **Hook-body mismatch:** Reels with good reach but short watch time or a high skip rate. The hook got the stop and the content didn't hold.
- **CTA effect:** for the same angle, do posts with a specific CTA outperform posts with none, on the goal metric?
- **Caption length effect**, split by format.
- **The comment goldmine:** questions asked more than once become content, and buying signals show which topics lead toward the offer.
- **Consistency:** posting gaps longer than 7 days, and whether performance dipped after them.
- **Offer posts:** how promo posts did compared with value posts, and whether the value posts right before them did better or worse.

## 6. Top and bottom posts

Rank posts by goal score. For each of the top 5 and bottom 5 posts, write one line on **why**, pointing to the tags and the qualitative pass ("Opens with a client's exact words, carousel format, keyword CTA. 4x your median save rate"). Don't simply restate the numbers.

## 7. Progress comparison (re-runs)

If the user pasted a previous snapshot:
- Compare the median goal score and the median of each key rate, before and after.
- Check whether each "double down" item from the last plan was used, and how those posts did.
- Report plan follow-through: how many plan items went live, and how they performed against the account median.
- Check each winning formula from the last snapshot: did posts using it keep winning? Keep it, adjust it, or retire it.
- Only compare like with like. If the goal changed, say so and compare the raw rates instead of the scores.

## 8. Snapshot format

```
SOCIAL ANALYZER SNAPSHOT
Account: @handle · Range: [start] to [end] · Goal: [goal] · Posts: [n]
Followers: [n]
Medians per 1K reach: saves [x] · shares [x] · follows [x] · comments [x] · profile visits [x]
Median reach ratio: [x] · Median goal score: [x]
Best format: [x] · Best angle: [x] · Best hook pattern: [x] · Best CTA: [x]
Winning formulas: [name: formula] · [name: formula]
First-words rule: [x]
Stop list: [1-3 items]
Double down: [1-3 items]
The one thing: [text]
```
