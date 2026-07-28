---
name: "document-formatting-standard"
description: "Allison's default formatting and delivery standard (v2) for every document Claude creates: Poppins throughout, 1.5 line spacing, size-and-color headers with Brand Blue H2s, no bold or italics, no em dashes, no colons or semicolons in drafted prose, YYYY-MM-DD date-prefixed filenames, and delivery as a styled Google Doc via SA+DWD with only a two-line summary in chat. Apply whenever creating, restyling, or delivering a document unless a brand skill's typography explicitly governs that deliverable."
---

# Document Formatting Standard (v2)

Ruled by Allison Gaddy, July 27, 2026, after the Wave 1 message review doc. Upgraded to v2 the same day with the punctuation rule and the delivery rule. This is the default look and delivery path for every document Claude produces in Cowork or Claude Code: Word docs, PDFs, Google Docs, review docs, reports, SOPs rendered as deliverables, anything styled. It applies unless a brand skill's visual identity explicitly governs the deliverable (a Moxie listing piece, a FAM lead magnet, an EP-branded sales page keep their brand typography; internal and working documents use this standard).

## The standard

Typeface: Poppins for everything. Title, headers, body, labels. No font mixing in working documents.

Line spacing: 1.5 throughout (in docx-js: spacing line 360).

Hierarchy by size and color, never by bold or italics:

- Title: Poppins 22pt, black #000000 (docx-js size 44)
- H1 section headers: Poppins 17pt, black #000000 (size 34)
- H2 subheaders: Poppins 13pt, Brand Blue #2757CF (size 26)
- Body: Poppins 11pt, black #000000 (size 22)
- Labels and meta text: Poppins 9pt, gray #555555 (size 18)

Spacing rhythm (docx-js values): H1 before 320 after 160; H2 before 280 after 120; body after 160; labels after 60. Title after 80 with a gray subtitle line after 280.

Quoted or message-style content: indent left 360 DXA, body size, so it reads as a block without borders or boxes.

Page: US Letter (12240 x 15840 DXA), 1 inch margins all around.

Filenames: date-prefixed, `YYYY-MM-DD <Title>`, using the date the document is created.

## Punctuation rule (v2, ruled by Allison 2026-07-27)

No colons or semicolons anywhere in drafted prose. Periods and commas only.

This applies to every document, email draft, message draft, and deliverable written for Allison or her team. It covers body text, headers, subtitles, and captions inside the deliverable.

Exempt: code blocks, technical references (file paths, URLs, config values, API syntax, timestamps), and data tables. The rule governs prose, not notation.

## Delivery rule (v2, ruled by Allison 2026-07-27)

Anything drafted for Allison to read, send, or keep lands as a styled Google Doc:

- Created via the SA+DWD path impersonating allison@expertpartners.com (never the read-only Google connectors), so ownership is native.
- Real Poppins and 1.5 line spacing applied through the Google Docs API (batchUpdate text and paragraph styles), not left as defaults.
- Filename date-prefixed per the filename rule above.
- Link handed to Allison in chat as a markdown hyperlink, never a raw URL.
- Chat carries only a two-line summary of the document. The document is the deliverable; chat is the pointer.

Stays in chat: Claude Code paste blocks (commands, prompts, snippets bound for another surface) and quick factual answers. Those are not documents and do not get wrapped in one.

## Hard rules (inherit Allison's voice rules)

- Never bold, never italics. Hierarchy comes from size and color only.
- Never an em dash, anywhere, including headers.
- No colons or semicolons in drafted prose (see punctuation rule above).
- Never horizontal rules, dividers, or decorative lines.
- No emoji in documents.
- Subtitle and provenance lines (date, audience, draft status) in gray meta style under the title.

## Implementation notes

In docx-js, set the default document style to Poppins size 22 and build helpers: title, h1, h2, body, label, and an indented msg block, using the values above. Verify output by converting to PDF and rendering a page image before delivering. In HTML or PDF pipelines, mirror the same values: Poppins via font stack 'Poppins, sans-serif', line-height 1.5, H2 color #2757CF.

In the Google Docs API, insert the text first, then apply updateTextStyle with weightedFontFamily Poppins and the sizes above, and updateParagraphStyle with lineSpacing 150. Set named-range or heading styles explicitly; do not rely on the doc's default font.

Poppins must be installed on the machine that opens a docx for it to render; it is part of the Expert Partners brand stack and present on Allison's machines. Name it explicitly in every run so it renders correctly there, whatever the fallback elsewhere. Google Docs serves Poppins natively from Google Fonts.

## Where this standard lives

This file, in expert-partners-skills (plugins/operating-doctrine/skills/document-formatting-standard/), is the canonical copy. Cowork loads its saved operative copy of the same skill; Claude Code applies the same standard via the user CLAUDE.md pointer and the expert-partners plugin marketplace mirror. If the standard changes, Allison rules it, and every copy updates together. The org-provisioned copy in Cowork does not auto-sync; after any change here, Allison re-uploads it per the skills sync ADR.
