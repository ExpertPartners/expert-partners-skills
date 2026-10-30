# Output contract

Every optimized file has this shape, in this order. Requirement IDs are lines in the approved spec, [HQ][V1.0] Spec - File to Knowledge Base Optimizer, revision 4.

## The header (R15, R20, R22, G20, R33)

A YAML block before the document title. Keys in this order. A key is always carried. A value the source and the intake do not establish reads unknown, never a guess (G19). Duration appears only when the source establishes one (R08).

```yaml
---
title: Weekly Team Call
type: transcript
source: 2026-05-05__zoom_sample__weekly_team_call.vtt
date: 2026-05-05
duration: 42 minutes 10 seconds
people: [First Speaker, "Second Speaker (Guest)"]
optimized_for: Claude Project
optimized_at: 2026-05-06
---
```

People means everyone who was there, from the intake and from the labels the source carries. A speaker is named on a line only when the source itself says who said what (G20, R11, R33).

## The sections (R16, R17, R18, R21, R34)

1. The document title as the first heading.
2. Summary. One or two paragraphs.
3. Key Takeaways. Three to seven substantive points about claims, decisions, methods or numbers.
4. Content. The cleaned source in full, divided by second level headings named for their topics. Where the source has its own headings they are the sections, shifted one level down because the title holds the first level. Speaker labels, timestamps, links and tables stay exactly as the source has them (G18).
5. Actions and Decisions. Only when the source is decision oriented. Owners and due dates only when the source gives them.
6. Source Notes. Origin and route, original file name, the date and how it is known, how people were identified, the speaker label situation, timestamps kept, tables kept, links kept, what cleanup removed, what could not be read, the part number and navigation page, and the source fingerprint (the sha256 of the cleaned source text, which is how a later run tells a revised source from an unchanged one).

Transcript lines keep every caption start time inline, exactly as the source wrote it, with the speaker label the source carries. Caption numbers and end times are not carried, and Source Notes say so.

```text
First Speaker: [00:00:17.460] Good morning, everyone. [00:00:21.030] Let's start with the numbers.
```

## Long material (R12, G16)

Past about 50,000 tokens (estimated as characters divided by four, no tokenizer, no exact rule) the material is split at section breaks into numbered parts. Each part is a complete file in the shape above, titled Title, Part n of N, with its own summary and takeaways. A navigation page, titled Title, Navigation, carries the header, a summary of the whole, and a Parts list naming each part file, its size and what it contains. The summary describes the material, drawn from the parts' summaries and the source's headings, never the file, its format or how it was split. When a stretch has no section breaks the split lands on a paragraph break and the navigation page says so.

## Combined files (G15, R24)

Made only when asked, and only from related files on the same topic. Every section opens with a line naming its source and date. A passage that appears word for word in two sources appears once and Source Notes say where else it appeared. When sources disagree, a Conflicts between sources section lists each disagreement with both claims and both dates, and no winner is chosen.

## The completion message (G12)

After saving, the tool says the file name or names, where they were saved, how many parts, the version and what it replaced, and anything that could not be read.
