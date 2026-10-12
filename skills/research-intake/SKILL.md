---
name: research-intake
description: >
  Files a research report that surfaces in ANY conversation, pasted, uploaded,
  or linked, into the aura repo's docs/research/INDEX.md as one new dated
  entry (title, subject, informs lane, disposition awaiting ruling). Never
  copies the report's content into the repo; the physical artifact stays in
  the Deep Research Drive folder (or wherever it already lives) and the index
  points at it by Drive file id. Use whenever a research report, deep-research
  output, or external analysis appears in conversation with intent to use it,
  not just intent to read it once and discard it. Answers the question in
  front of Allison FIRST, files behind the answer, then reports the commit
  hash. Implements ADR 0047 (aura decisions/0047-autonomous-research-pipeline-
  and-standing-write-authority.md), as corrected 2026-08-08 to the
  informs-lane-in-one-index design rather than the ADR's original per-paper
  docs/research/ file design.
tier: user
zone: cataloging
status: live
subtitle: "file a research report into the aura research index"
---

# Research Intake Skill

Files a research report into `docs/research/INDEX.md` in the aura repo, the
single canonical map of Allison's research corpus (ADR 0047). This is the
chat-surface half of ADR 0047's pipeline; `tools/research-intake/sweep_drive.py`
plus its daily launchd job is the mechanical half that catches everything this
skill never saw filed from a live conversation. Both write the same index
shape and share the same lane-routing logic, so a paper looks identical in the
index whichever path filed it.

## 0. Answer first

The report is evidence Allison is using RIGHT NOW to think something through.
Answer her actual question or give her the read she asked for before doing any
filing work. Filing happens after, silently, and is reported in one line at
the end, never instead of engaging with the content.

## 1. Never duplicate a filing

Before writing anything, check whether this exact paper is already indexed:
search `docs/research/INDEX.md` (via the estate-brain `search` tool, or a
direct `grep` if working in the aura repo) for the paper's Drive file id if it
has one, or its title if it doesn't yet. If found, this is a rediscovery, not
a new filing: skip straight to step 5 and report the existing entry instead of
creating a second one.

## 2. Give the artifact a stable home

The index links to a real file; it is never a copy of one (ADR 0047 as
corrected 2026-08-08, see the ADR's revision record). Two cases:

- **Already has a Drive id or URL** (the user pasted a Drive link, or the
  report arrived via a project/conversation that already saved it to Drive):
  use that id directly, no upload needed.
- **No Drive home yet** (pasted raw text, an uploaded file with no Drive
  copy, a web page): save it into the Deep Research Drive folder
  (`197mXOs0T2cgGilRylwTQc0VFtx1CuUP7`) via SA+DWD impersonating
  allison@expertpartners.com, as a Google Doc if it's text or the original
  file type if it's a document. Save it directly into the matching topic
  subfolder (see step 3), never loose at the root, since this skill already
  knows the lane a mechanical sweep would have to guess at.

## 3. Determine the informs-lane

Read the report's actual subject matter, not just its title or filename
(this is the advantage this skill has over the mechanical sweep, which only
sees a filename). Tag it with the ADR 0045 brand registry lane it informs:
Expert Partners, EPIC, Don Hobbs Personal Brand, AG Personal Brand, AG
Luxury, Free Agent Movement, Infrastructure, or Operations (the established
non-brand tag already in use for EOS- and ACN-class operational content).
A report can inform more than one lane; list all that genuinely apply,
primary lane first.

Route the Drive save (step 2) to the topic subfolder that matches the
primary lane, using the same name map `tools/research-intake/sweep_drive.py`
uses (`SUBFOLDER_LANE_SEED` plus the `ROUTES` table). If the lane's subfolder
doesn't exist yet, create it there, exactly as the sweep script would.

## 4. Write the entry

Append one `###`-level entry under today's date in `docs/research/INDEX.md`,
in this exact shape (matching every existing entry in the file):

```
### <Title, no em dashes, colon-style subtitles rendered with a comma>
- Drive file id[ (Google Doc)]: `<id>`
- URL: <drive or docs.google.com URL>
- Date: <YYYY-MM-DD>
- Subject: <one to two sentences, the REAL subject, not a placeholder --
  this skill has actually read or discussed the content>
- Informs lane: <lane, or lanes>
- Superseded by: <None recorded. Fresh filing. -- or a named ADR/doctrine
  file if the conversation already surfaced one>
- Disposition: <awaiting ruling -- or implement / park / superseded, if
  Allison ruled on it in the same conversation that surfaced it>
```

If Allison ruled on the paper in the same breath she showed it to you
("yeah, park that" / "let's build this"), record that ruling directly in
Disposition and Superseded-by rather than defaulting to awaiting ruling; a
ruling that already happened in front of you is not something to re-queue.

## 5. File the Your Move item only if still unruled

If Disposition is still "awaiting ruling" after step 4, file one Your Move
item (`docs/estate/your-move-queue.md` mechanism: `repository_dispatch` event
`your-move` at `ExpertPartners/aura`, token from
`op://Automation/estate-brain-mcp/credential`), keyed
`research-intake/<drive-id>`, first person, no `page` (routine filings ride
the Friday review per ADR 0047 point 7, they never text). If Allison already
ruled in step 4, skip this step entirely; there is nothing left for her to do.

## 6. Commit, push, report

Commit `docs/research/INDEX.md` (and any new intake note, if this filing came
from a full session capture rather than a single paper) with message
`research(intake): file <title>` and trailer `Push-Policy: docs`, then push.
This is a delegated additive write under ADR 0047 standing write authority;
no per-action approval is needed. Report back in one line: the entry's
title, its lane, its disposition, and the commit hash.

## Rules

- Never use em dashes in anything this skill writes (org standard); render a
  title's colon-style subtitle with a comma instead, same as the sweep script.
- Never copy a report's full text into the repo. The index entry plus the
  Drive link is the filing; docs/research/ per-paper files are retired as a
  pattern (ADR 0047 correction, 2026-08-08) except for the two legacy filings
  the ADR named at acceptance.
- Never touch a disposition Allison has already ruled away from the default.
- Run the sibling-session visibility check before committing to aura from a
  surface other than the session that already owns aura's working copy.
