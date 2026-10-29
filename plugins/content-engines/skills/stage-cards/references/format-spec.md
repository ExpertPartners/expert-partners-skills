# Stage Cards, format spec

The format Allison approved on October 29, 2026 for all event cards, copied from her final Finish Strong cards. Find that Doc by its title in Google Drive, [EXPNTX][V1.2] Finish Strong Speaker Intros 4x6 Cards. Never copy its link, ID, or its text into this repository.

## Page

| Setting | Value |
| --- | --- |
| Page size | 6 by 4 inches, landscape (432 by 288 points) |
| Margins | 380 twips top and bottom (19 points), 480 twips left and right (24 points) |
| Font | Poppins |
| Body size | 11, dropping to 10 when a segment needs room to stay on one card |
| Header size | 11, always |
| Line spacing | Single |
| Space above and below paragraphs | None. Blank lines between paragraphs are empty paragraphs |
| Card break | A page break at the end of each card's last paragraph. No trailing blank page |

## Card patterns

Timed segment. One header line, bold, navy #243B57, size 11. Order is time, then speaker, then short topic, like 9:15 AM. Name - Short topic. Long topics are cut short with an ellipsis. Body paragraphs follow with no blank line under the header.

Emcee cross-intro. No navy header. The paragraph opens with a bold label naming who introduces whom, like AG intro Nic, then a dash and the text. Short cross-intros and the line that starts slides can share one card.

Panel. Header line. A lead-in paragraph. The panelists as a bulleted list, one per panelist. Then the welcome line, which names the panelists.

Sponsor. Header line. A bold opening paragraph. A plain paragraph listing each company with its rep. A bold closing ask. Body is usually size 10.

Slide notes. Header reads host name, a dash, the slide number and title, like AG - Opening slide 4. Title. Each note is one short line that starts with a bullet dot. The one line the speaker must land is bold.

Anything else. A plain header naming the segment, then the body.

## Splitting

Split only when a segment will not fit at size 10. Split at a sentence break. The second card has no header and never says continued. Never split to make cards look even.

## Card markup

stage_cards.py reads a plain text file in this markup. One card per block, blocks separated by a line holding only three dashes.

| Line | Meaning |
| --- | --- |
| # text | Header line, bold navy, size 11 |
| plain text | Body paragraph. Consecutive plain lines join into one paragraph, a blank line starts a new one and leaves one empty paragraph between |
| - text | Bulleted list item |
| text with **bold** spans | Bold run inside any line |
| @10 or @11 | Force the body size for this card. Without it the script picks 11 and drops to 10 only when needed |

Bullet dots typed as text, a dot then two spaces, pass through as plain text. Use them for slide notes.

## Check before done

1. Page count of the exported PDF equals the card count.
2. Card N starts on page N.
3. Every body run is Poppins 10 or 11, every header is Poppins 11 bold navy.
4. No card is split without the user asking or the text forcing it.
