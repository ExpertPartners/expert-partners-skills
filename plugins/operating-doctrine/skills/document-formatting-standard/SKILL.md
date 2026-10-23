---
name: "document-formatting-standard"
description: "Allison's formatting and delivery standard (v4) for every document an AI makes. The live HQ Rulebook's Document formatting section owns every number: Google Docs, Poppins for Expert Partners and HQ, the AG Luxury brand guide for AG Luxury, the Rulebook's current line spacing, no blank lines between paragraphs, short paragraphs, and no bold, italics, em dashes, or dividers. Files take Cal's naming and go to their brain home, delivered as a link named for the document. Read the Rulebook live, then apply it with the tool notes here. Use whenever creating, restyling, or delivering a document."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
defers-to:
  - deliverable-link
brand-scope: null
subtitle: "the Rulebook sets the look, this skill applies it"
---

# Document Formatting Standard (v4, 2026-10-22)

<!-- RULED-BY: intake/2026-10-22-disclosure-rulebook-sync-formatting-tabs-session-wrap.md date:2026-10-22 -->

This version supersedes the hard-coded values, plain-title filenames, Aura Docs folder, and re-upload note of v3. Disclosure of record: intake/2026-10-22-disclosure-rulebook-sync-formatting-tabs-session-wrap.md.

## The source is the Rulebook

The Document formatting section of [V1 - Company Core - HQ Rulebook](https://docs.google.com/document/d/15sCFxMvG8OZMZik5w0Hzqzh7HyphrB7rJ8NBtm46JBE/edit) sets every number for company documents. That covers fonts, sizes, colors, line spacing, and paragraph spacing. [V1 - Company Core - Decision Log](https://docs.google.com/document/d/1ausL1HV3ns3VMZH86jD8zjWnAKSQ3DaUfFzkiwR1qWc/edit) records each change.

Read that section live before you make or restyle a document. Never use a remembered value. Line spacing alone moved from 1.5 to 1.15 and back to 1.5 during October 2026.

If this skill and the Rulebook ever differ, the Rulebook wins. Report the difference to [HQ 🧠] - Chief HR Officer in the Handoffs tab of the Job Tracker.

## What the Rulebook asks for, in short

This list only says what to look up. The numbers live in the Rulebook.

- Every document an AI makes is a Google Doc.
- Expert Partners and HQ documents use Poppins throughout, with the Rulebook's title, heading, and body sizes and its Brand Blue for Heading 2.
- AG Luxury documents follow the AG Luxury brand guide as the Rulebook states it, Italiana for titles and headings, Manrope for body, black and white, with Rich Gold only for small details.
- Line spacing is whatever the Rulebook says today.
- No empty line sits between paragraphs. Line spacing and a small space after each paragraph do the separating, and headings keep their own spacing.
- Paragraphs stay short, one or two sentences that carry one idea.
- No bold, no italics, no em dashes, and no horizontal dividers.

## Names, home, sharing, and delivery

- Name the file the way the Rulebook's naming rule says, which follows Cal's convention.
- Save it in its one home in the owning business brain, per the Rulebook's Where things live section.
- Set sharing the way the Rulebook's Sharing section says.
- Hand it over as a link whose text is the exact document name, never a raw URL (see the deliverable-link skill). Chat carries a short summary, and the document is the deliverable.

Claude Code paste blocks, commands, snippets, and quick factual answers stay in chat. They are not documents.

## Applying it with tools

These notes translate the Rulebook's values. They never replace them.

- Create the Doc through the service account impersonating allison@expertpartners.com where that path is reachable, otherwise through a write-capable Drive or Docs connector, so ownership is native.
- In the Google Docs API, insert the text, then apply updateTextStyle with weightedFontFamily and the Rulebook's sizes, and updateParagraphStyle with lineSpacing set to the Rulebook value times 100 (1.5 becomes 150).
- Use the native named styles (TITLE, HEADING_1, HEADING_2, NORMAL_TEXT) so the outline works. A visually enlarged paragraph is not a heading.
- Never insert empty paragraphs to make space. Use spaceBelow on body paragraphs instead.
- In docx-js, line spacing is the Rulebook value times 240 and font sizes are in half points.
- Before you report done, read the saved document back. Check the font, the line spacing, the heading styles, and that no empty paragraphs sit between paragraphs.

## Where this standard lives

This file in expert-partners-skills, plugins/operating-doctrine/skills/document-formatting-standard/, is the canonical copy. Claude Code, Claude surfaces, and Codex receive it through the expert-partners plugin marketplace.
