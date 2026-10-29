---
name: stage-cards
description: Lays any finished text onto 4x6 stage cards, a Google Doc of 6 by 4 inch landscape pages, one segment per card, in the format Allison approved for all event cards. Layout only. Keeps the words exactly as written unless the user asks for a trim. Use for speaker cards, emcee cards, intro cards, note cards for a talk, or slide notes. Triggers on "put this on cards," "make my 4x6 cards," "note cards for my talk," "speaker cards," "emcee cards," "cards for the run of show," or any pasted talk, intros, slide notes, or run of show with cards asked for. Never writes or rewrites the words. For writing speaker intros, use speaker-introduction-writer, then hand its text here.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "any text laid onto 4x6 note cards"
---

# Stage Cards

One job, layout. Take text that is already written (a talk, intros, slide notes, a run of show) and put it on 4x6 cards that a person can hold on stage. The words stay as written. Trim only when the user asks, and then trim only what they name.

This skill never writes intros. speaker-introduction-writer writes them and hands the finished text here when the intros are for a live event.

## Step 1. Read the text and find the segments

A segment is one thing said at one moment, like one speaker intro, one talk section, one panel lead-in, one slide's notes. One segment per card. Do not merge segments to save cards.

Short pieces may share a card when together they fit at size 10 or 11, for example two emcee cross-intros and the line that starts the slides.

If the text has no clear segments, make them from its own breaks (topic shifts, headings, run of show times). Ask one question only if the segmentation would change the cards materially, such as a talk with no breaks at all.

## Step 2. Choose each card's pattern

The exact numbers for every pattern are in references/format-spec.md. In short:

- Timed segment. Header with time, then speaker, then short topic. Body below.
- Emcee cross-intro. A bold label for who introduces whom, like AG intro Nic, then the text on the same line.
- Panel. Lead-in line, panelists as bullets, then the welcome line.
- Sponsor. Bold opening, plain list of company with rep, bold closing ask.
- Slide notes. Header reads host, slide number, and title, like AG - Opening slide 4. North Texas, September 2026. Short bullet lines. The one line to remember is bold.
- Anything else. Plain header with the segment name, body below.

## Step 3. Make the fit rules hold

- Body is Poppins 11. It drops to 10 only when that segment needs room to stay on one card. Headers stay 11.
- Single line spacing. One segment per card.
- When a segment will not fit even at 10, split it at a sentence break. The second card carries no header and never says continued.
- Long topics in a header are cut short with an ellipsis so the header stays on one line.

## Step 4. Write the card file and build the Doc

Write the cards in the card markup described in references/format-spec.md, then run scripts/stage_cards.py.

1. python3 scripts/stage_cards.py check cards.txt. Shows each card's size choice and any card that will not fit.
2. python3 scripts/stage_cards.py create cards.txt --title "<file name>". Builds the Google Doc through the Google Docs API, exports it to PDF, and confirms the page count equals the card count and each card starts on its own page. Prints the Doc link.

Name the Doc the way the company names files, [Brand-Department][Version] Name, for example [EXPNTX][V1.0] Speaker Cards. If the user is on a surface that cannot run scripts or reach the Docs API, give the cards as a numbered block in chat, one card per block, and say plainly that the Doc was not built and nothing was fit-checked.

Credentials come from the environment, never from this repository. See the top of scripts/stage_cards.py.

## Step 5. Report

Give the Doc link as a clickable file name, the card count, which cards dropped to 10, which cards were split, and the result of the page check. If a check failed, say which card and fix it before reporting done.

## Rules that never bend

- Layout only. No rewriting, no new facts, no tightening unless asked.
- No em dashes or double dashes in anything this skill writes. If the pasted text has them, keep the text as written and say so once.
- Spelling locks hold in anything this skill adds, such as headers. eXp, eXcelerate, Don, Allison Gaddy, Nicole Rouseau, Free Agent Movement.
- Cards for a live event leave brokerage names exactly as the source has them. This skill does not add or remove them. That rule belongs to the writer.
