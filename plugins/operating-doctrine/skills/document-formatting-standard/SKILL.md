---
name: "document-formatting-standard"
description: "Allison's formatting and delivery standard (v4.3) for every document an AI makes. The live HQ Rulebook's Document formatting section owns every number: Google Docs, Poppins throughout for every brand and room, AG Luxury included, the Rulebook's current line spacing, no blank lines between paragraphs, short paragraphs, and no bold, italics, em dashes, or dividers. Files take Cal's naming and go to their brain home, delivered as a link named for the document. Covers every Google Doc in the HQ, EP and AG brains, existing ones included. Read the Rulebook live, then apply it with the tool notes here. Use whenever creating, restyling, or delivering a document."
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

# Document Formatting Standard (v4.3, 2026-11-23)

<!-- RULED-BY: intake/2026-10-22-disclosure-rulebook-sync-formatting-tabs-session-wrap.md date:2026-10-22 -->

This version supersedes the hard-coded values, plain-title filenames, Aura Docs folder, and re-upload note of v3. Disclosure of record: intake/2026-10-22-disclosure-rulebook-sync-formatting-tabs-session-wrap.md.

v4.1 follows Decision Log 2026-10-24, Every document made in work with Allison uses Poppins. AG Luxury documents no longer take Italiana and Manrope. Assigned by [HQ 🧠] - Chief HR Officer.

v4.2 extended the standard to existing documents. v4.3 follows the newer November 23 correction, Company documents stay at 1.5 line spacing, every brain, existing documents included, and the same-day paragraph, heading and bullet spacing decisions. The earlier 1.15 entry is superseded. Assigned by [HQ 🧠] - Chief HR Officer.

## The source is the Rulebook

The Document formatting section of the HQ Rulebook sets every number for company documents. That covers fonts, sizes, colors, line spacing, and paragraph spacing. The Decision Log records each change.

Read that section live before you make or restyle a document. Do not rely on a remembered value. Line spacing alone moved from 1.5 to 1.15 and back to 1.5 during October 2026. November 23's 1.15 entry was corrected to 1.5 the same day. The newest Decision Log entry wins.

If this skill and the Rulebook ever differ, the Rulebook wins. Fix this skill to match and say so in your report.

## What the Rulebook asks for, in short

This list only says what to look up. The numbers live in the Rulebook.

- Every document an AI makes is a Google Doc.
- Every document uses Poppins throughout, for every brand and every room, AG Luxury included, with the Rulebook's title, heading, and body sizes. Expert Partners and HQ documents set Heading 2 in the Rulebook's Brand Blue.
- AG Luxury documents stay black and white, with the Rulebook's Rich Gold only for small details. Italiana and Manrope are the allisongaddy.com website fonts and belong only to public, client-facing design, never to working documents.
- Line spacing is whatever the Rulebook says today.
- No empty line sits between paragraphs. Line spacing and a small space after each paragraph do the separating, and headings keep their own spacing.
- Paragraphs stay short, one or two sentences that carry one idea.
- No bold, no italics, no em dashes, and no horizontal dividers.

## Existing documents

The standard covers every Google Doc already in the HQ, Expert Partners and AG Business Brains, not only new ones. When you open, edit, or touch an existing Doc that is off standard, restyle it to the Rulebook in the same pass. Restyling changes formatting only, never wording, and never counts as an unrequested change to a business-brain file.

Restyling means Poppins throughout, the Rulebook's line spacing, real named heading styles in place of enlarged or bold paragraphs, removal of empty paragraphs used as spacers, removal of bold and italics in body text, and the brand's color rules.

Preserve wording, hyperlinks, file names and file locations. Deliberate special layouts, such as 4x6 speaker cards, keep their layout and Poppins rather than being flattened into a working-document layout.

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
- A Drive content import is not a completed formatting step. A real Week 10 save retained HTML body line spacing but dropped its body-level Poppins font and saved Arial. Do not infer native formatting from HTML, CSS, a successful upload or a text export. After an import or replacement, apply the native Docs text and paragraph styles to the saved document. Use an available Docs write connector or the existing delegated Google API route rather than stopping at the import.
- Before reporting a save complete, read the native Doc and check the effective style of every nonempty text run and paragraph. Resolve inherited named styles as well as explicit overrides. Confirm the live Rulebook's font, sizes, spacing and named headings, with no bold, italics or interior empty spacer paragraphs. Correct a mismatch in the same save operation and read it back again. A saved subject, current text and correct folder do not establish a formatting pass.
- Use the native named styles (TITLE, HEADING_1, HEADING_2, NORMAL_TEXT) so the outline works. A visually enlarged paragraph is not a heading.
- Never insert empty paragraphs to make space. Apply the live Rulebook's paragraph rhythm through spaceAbove and spaceBelow. The November 23 rules set body spaceBelow to 12 PT, headings spaceAbove to 18 PT and spaceBelow to 6 PT, list-item spaceBelow to 6 PT, and the final item in each list to 12 PT.
- In docx-js, line spacing is the Rulebook value times 240 and font sizes are in half points.
- Apply the font, line spacing and heading styles as you build, with no empty paragraphs between paragraphs.

## Where this standard lives

This file in expert-partners-skills, plugins/operating-doctrine/skills/document-formatting-standard/, is the canonical copy. Surfaces receive it through the plugin marketplace.

## Native save procedure

Invoke this skill and `deliverable-link` before a company document write. Resolve the live Rulebook and current decisions, the same-subject native Doc, its canonical name and owning parent. Say the resolved destination in assistant prose before the first write. Use the existing connector or delegated Google route for the content save, updating the same Doc when its purpose has not changed. Legacy intake instructions do not override the current save rule.

After the last content write, run `scripts/format_native_doc.py` from this installed skill folder. It uses the existing local Google adapter, not a new credential or service. Resolve that adapter from the configured Google Workspace MCP server or an already verified route. Supply its absolute Python module path, the authorized subject, actual document ID, live Rulebook ID, exact metadata name and parent ID.

```text
python3 /absolute/installed/skill/scripts/format_native_doc.py \
  --adapter /absolute/existing/google/server.py \
  --subject AUTHORIZED_SUBJECT --document-id ACTUAL_DOC_ID \
  --rulebook-id LIVE_RULEBOOK_ID --name 'EXACT_METADATA_NAME' \
  --parent-id ACTUAL_OWNING_PARENT
```

The helper reads the live Rulebook under a version check, retains existing text and links, inserts a missing subject title, applies native named styles under a revision guard and verifies the saved text, title and effective fonts and sizes through the native PDF export. It requires the existing Python `pypdf` dependency for export inspection and checks that before writing. An omitted native font-size field is never assumed to mean the body size. The helper returns a successful `NATIVE_DOC_VERIFIED` receipt and the exact-name link only after verification. Use that exact link in the final reply. A later content write invalidates the earlier receipt.

Known Today and Handoff source projections also require exact, balanced standalone boundaries. Today sections require complete JSON; Handoff sections retain their existing pipe-row and key=value grammar. The helper rejects corrupted closers, duplicate singleton blocks and appended stale Today JSON before formatting writes, then verifies exact payload hashes after saving. Repeated Handoff instances remain supported. Preserve malformed historical evidence outside the active machine section; never replace only a closing-marker substring. The owning consumer still validates its business schema against the full saved document before a source or week is accepted.

The installed plugin's Factory-compatible hooks check the known native Google document-content and style write tools and inline Google API calls, including nested `Execute` calls. File metadata, sharing, cleanup and JSON evidence uploads are not native document-content saves. They require successful skill loads and the pre-write destination announcement. The Stop hook binds each successful formatter result to that exact saved ID and name, then reads the actual final native revision and content again before checking the caption. A later detected content or style write invalidates the earlier receipt. It rejects an invalid receipt or caption on repeated Stop calls as well. A corrected, freshly verified reply ends the correction. A repeat call does not establish a save pass.

The recognized connector routes include Google Docs `update_doc` with its exact `documentId` and Google Drive `create_file` with native Google Doc `contentMimeType`. A missing, empty, unreadable or invalid transcript produces an explicit unverified-runtime denial, including on repeated Stop calls. It does not waive a known write or establish a save pass. Manually invoking this hook inside a cloud Project does not demonstrate that the platform runs native hooks or supplies transcript evidence; that runtime's enforcement remains unverified until actual platform invocation is proved.

Supported hosts invoke these hooks with actual transcript evidence. Do not manually fabricate Stop events or empty transcript paths in a web-only client. Where available, run the existing formatter and native PDF/readback route independently and require its fresh verified receipt before declaring a save pass; report unsupported hook enforcement separately. Standalone formatter-file inspection with `ls`, `cat` or `test -f`, and a standalone Python formatter `--help` call, do not perform a document save. Compound commands containing a real formatter invocation remain guarded.

This is bounded workflow enforcement, not an arbitrary-code security boundary. Opaque shell scripts, arbitrary API clients, disabled hooks, web-only surfaces and sessions that have not loaded the plugin remain outside its verified interception. Nested calls do not fire Factory `PostToolUse`, so verification uses the transcript at Stop, not an invented post-call capability. This helper supports single-tab text with native TITLE and H1/H2. Multi-tab Docs, tables, objects, generated list glyphs and special layouts remain with their owning layout procedure and receive no pass from this helper. It requests all native tabs and refuses those structures before writing, including headers, footers, positioned objects and nonstandard page sizes. Definitive Google API request failures stay in history without pretending a mutation succeeded. An uncertain write to an exact structured target remains unverified until a later successful formatter reads that same target back; a creation whose target is unknown remains unbound and unverified. An interrupted or failed save remains unverified.
