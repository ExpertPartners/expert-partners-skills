# Source Dossier Schema -- reference

The smallest clean schema that satisfies the mission's field list, no
manufactured folders. A dossier is exactly two files, produced by
`scripts/scaffold_dossier.py`:

```
<domain>/<creator-slug>/<source-slug>/
  README.md          -- quick-glance overview and provenance
  source-record.md   -- the detailed structured extraction
```

Directory shape is domain -> creator -> source (ADR-pending conceptual
organization for `ExpertPartners/external-methodologies`; see
`reference/routing.md`). Books are a source FORMAT, never a domain; a book
lives under its actual subject domain, under its author.

## README.md

Frontmatter (all fields required unless marked optional; `unclear` is a
legitimate value for `ownership`, never left blank):

```yaml
---
title: <source title>
creator: <author/creator name>
source_type: pdf | docx | deck | youtube-video | youtube-transcript |
  podcast-transcript | course | drive-file | pasted-text | research-report |
  web-page | interview | original
domain: <actual subject domain>
methodology: <program/book/framework name, or null>
provenance: <one to two sentences: who made this, in what context>
original_location: <URL, Drive id, file path, or physical description>
date: <YYYY-MM-DD, or "accessed YYYY-MM-DD" if the creation date is unknown>
ownership: allison-ep | third-party | unclear
core: true | false
core_basis: <Allison's own words that set this, or "recommended, not yet
  ruled" if core is a recommendation still awaiting her decision>
downstream: [<brand/product/system this may inform>, ...]
destination: <the repo/path this dossier lives in, or "PLANNED: <repo>
  (not yet created)">
binary: stored | linked | both | not-applicable
binary_location: <path or URL, if stored or linked>
---
```

Body: a short human-readable overview, in prose --

- Why this source matters (one paragraph).
- What it is, plainly (one paragraph).
- Related sources, if any (list, each a relative link to another dossier or
  an external reference).

## source-record.md

The detailed, structured, machine-readable extraction. Sections, in order,
present only when the source actually supports them (never manufacture an
empty section just to fill the template):

1. **Concepts, frameworks, and principles** -- the substantive content,
   organized however the source itself organizes it.
2. **Terminology** -- a short glossary of terms the source coins or uses in a
   specific way.
3. **Examples** -- concrete examples, case studies, or illustrations the
   source gives.
4. **References** -- page numbers, timestamps, section headings, or slide
   numbers, whenever the source format supports them (a PDF cites pages, a
   video transcript cites timestamps, a deck cites slide numbers). Never
   fabricated when the source does not support them.
5. **Allison / Expert Partners observations** -- kept in its own clearly
   labeled section, never interleaved with the source's own claims. This is
   commentary ABOUT the source, not the source itself; if it grows into
   actual doctrine, it graduates out to the appropriate downstream repo per
   `reference/routing.md`, not left here pretending to be source material.
6. **Machine-readable extraction / transcript**, when appropriate and not
   already fully covered by section 1 (for example, a full timestamped
   transcript for a video, kept as an appendix rather than duplicated
   through the summary above).

## Why two files, not more

A dossier needs exactly one file a human skims (README.md) and one file the
Estate actually reasons over (source-record.md). Splitting further (a
separate provenance.md, a separate creator.md, a separate concepts.md) adds
folders without adding retrievability; a single well-labeled source-record.md
section list already gives an AI reader everything it needs to jump straight
to the part it wants.
