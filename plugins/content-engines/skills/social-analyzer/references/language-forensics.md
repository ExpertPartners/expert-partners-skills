# Language Forensics

This is the part of the report users value most. Numbers tell them *which* posts worked. This step tells them *what words made them work*, and hands back formulas they can copy into their next posts.

Run it on **every post** in the range, not only the top and bottom 10. Captions come with the Business Suite table and the CSV export, so the first line is always available.

## 1. Capture the words

For every post, record exactly, with no paraphrasing:

- **First line:** the caption up to the first line break, or the first sentence if there's no break. Cap it at about 150 characters.
- **First 5 words:** the opening five words of that line.
- **CTA line:** the sentence that asks for an action, word for word. Write "none" if there isn't one.
- **On-screen hook** (Reels and carousels, from the qualitative pass): the text on the first frame or on slide 1.
- **Caption shape:** how the body is built (list, numbered steps, short story, single thought, question). Also record its length bucket, how many line breaks it has, and whether it uses emojis.

## 2. Tag the opening

Give every first line **one opener type**, based on its first 3 to 5 words:

| Opener type | Looks like |
|---|---|
| Audience identifier | "Coaches:", "If you're a new mom...", "Realtors, stop..." |
| You-first | Opens with "You" or "Your" |
| Number or list | "3 ways...", "7 mistakes...", "The 1 thing..." |
| Result or figure | Opens with a dollar amount, a result, or a timeframe |
| Me-first | Opens with "I", "My", or "We" |
| Question | Opens with a question |
| Command | Opens with a verb: "Stop", "Steal", "Try", "Save" |
| Warning | "Don't", "Never", "Nobody tells you", "The mistake..." |
| Quote | Opens with a client's words or a quote in quotation marks |
| Moment | "Last Tuesday", "At 11pm", "The day I..." |
| Contrarian | "Unpopular opinion", "Everyone says... they're wrong" |
| Warm-up | "Happy Monday", "So...", "Hey guys", "Today I want to talk about" |

Then mark each first line for these **signals** (yes or no):

- **Names who it's for** within the first 5 words
- **Has a number** anywhere in the first line
- **Names a pain or a result** (what's wrong, or what they'll get)
- **Lands before the cutoff:** the full hook fits in the first 125 characters
- **Specific detail:** a concrete moment, tool, place, or amount (not "struggling" or "a lot")

Also tag the **promise type** (list, how-to, mistake, story, result, opinion, or question) and the **hook pattern** (the 12 patterns in `analysis-method.md`).

## 3. Compare the words

Use the same sample-size rules as the rest of the report (5+ posts for Strong, 3-4 for Early signal).

1. **Opener types:** the median goal score per opener type. Chart it as a breakdown titled "By first words."
2. **Signals:** for each signal, compare posts that have it with posts that don't. This is where findings like "Posts that name who they're for in the first 5 words scored 2.3x higher (8 posts vs 22)" come from.
3. **Words that win and words that lose:** find the words and 2-3 word phrases that show up in the first lines of 3 or more posts. Skip filler words like "the," "a," "and," "to," and "is." For each one, compare the median goal score of posts that use it with the account median. List up to 6 winners and up to 6 losers, each with its post count. Only include words where the gap is 25% or more.
4. **First-line length:** compare short (under 8 words), medium (8-15), and long (16+).
5. **CTA wording:** rank the exact CTA lines, grouped when they're near-identical, by the goal's key metric (profile visits for leads and sales, follows for growth, shares for reach, comments for community).

## 4. Build the formulas

This is the deliverable. Look at the **top quarter of posts** by goal score.

1. Group them by opener type plus hook pattern plus promise type.
2. Any group with 3 or more top posts becomes a **winning formula**. Fewer than 3 posts means it isn't a pattern yet.
3. Write each formula as a fill-in-the-blank line that keeps the user's own recurring words. Only the parts that change become `[slots]`.
   - Their posts: "3 invoicing mistakes that make clients pay late" and "5 pricing mistakes that keep you stuck at $5K months"
   - Formula: `[Number] [topic] mistakes that [bad result your reader wants to avoid]`
4. For each formula, include:
   - **Name:** a short plain label, like "The Mistake List."
   - **The formula**, with slots.
   - **Your proof:** 2-3 of their real first lines, quoted exactly, each with its date and one key stat.
   - **Why it works:** one line, pointing to the signals ("names the reader's pain in the first 5 words and promises a countable list").
   - **Confidence:** Strong or Early signal.
   - **3 ready-to-use hooks:** new first lines built on the formula, for topics they haven't posted yet. Pull topics from their Content Profile, the audience questions in the comments, and the angles that performed. Each one must fit before the 125-character cutoff. Never invent a number, result, or story. Use a `[placeholder]` wherever a real detail is needed.

Aim for 2-4 formulas. One well-proven formula beats five weak ones.

**The formula to retire:** find the most common opener type or structure among the bottom quarter, and show it the same way: the pattern, 2 real examples, and the numbers. Then rewrite one of those real first lines using their best winning formula, so they can see the before and after.

## 5. The first-words rule

Boil the strongest Strong finding about the opening words into one sentence the user can remember:

> "Name who it's for in your first 5 words. Your posts that did this scored 2.3x higher."

If no signal reaches Strong, say so, and give the best Early signal labeled as one.

## 6. The caption blueprint

From the top quarter, work out the body shape their best posts share, then write it as a copy-paste skeleton:

```
[Hook: use one of your winning formulas]
[One line naming the problem, in your reader's words]
[3-5 short steps or points, one per line]
[One line on what changes when they do it]
[Your best CTA, word for word]
```

Match their real habits (line breaks, emoji use, length, where the CTA sits). If their top posts don't share a shape, say so and skip the blueprint instead of making one up.

## 7. The swipe file

End with one plain-text block the user can copy into their notes or Content Profile. It holds everything they need to write the next post without reopening the report:

```
MY WINNING FORMULAS (from my Social Analyzer report, [date range])
1. [Name]: [formula]
   e.g. "[their best real example]"
2. ...
FIRST-WORDS RULE: [the rule]
WORDS THAT WORK: [list]
WORDS TO DROP: [list]
BEST CTA: "[exact wording]"
CAPTION BLUEPRINT: [the skeleton, on one line per slot]
```

## Rules

- Quote the user's own captions exactly. It's their content, so quoting it is fine. Never quote commenters by name.
- Don't claim a word or opener "works" from 1 or 2 posts.
- Keep formulas in the user's voice. Don't swap in generic marketing phrasing.
- If captions are missing or blank for most posts, say so in the data notes, and ask the user to paste the first lines of their top and bottom 10 posts before building formulas.
