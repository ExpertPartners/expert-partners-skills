---
name: research-intake
description: >
  Files a research report that surfaces in ANY conversation, pasted, uploaded,
  or linked, into the Deep Research folder in Drive, in the topic subfolder for
  the lane it informs, with a short header (subject, informs lane, disposition
  awaiting ruling). The artifact stays in Drive and is never copied elsewhere.
  Use whenever a research report, deep-research output, or external analysis
  appears in conversation with intent to use it, not just intent to read it once
  and discard it. Answers the question in front of Allison FIRST, files behind
  the answer, then reports the Drive link. Replaces the aura docs/research/INDEX.md
  index of ADR 0047.
tier: plugin
zone: cataloging
status: live
subtitle: "file a research report into the Deep Research folder"
---

# Research Intake Skill

Files a research report into the Deep Research folder in Drive, the single home of Allison's research
corpus. The daily sweep (`tools/research-intake/sweep_drive.py`) catches
everything this skill never saw filed from a live conversation, and both use
the same lane-routing logic.

## 0. Answer first

The report is evidence Allison is using RIGHT NOW to think something through.
Answer her actual question or give her the read she asked for before doing any
filing work. Filing happens after, silently, and is reported in one line at
the end, never instead of engaging with the content.

## 1. Never duplicate a filing

Before writing anything, search the Deep Research folder through the Drive
connector for the paper's Drive file id if it has one, or its title if it
doesn't yet. If found, this is a rediscovery, not a new filing: skip to step 5
and report the existing Doc instead of creating a second one.

## 2. Give the artifact a stable home

- **Already has a Drive id or URL** (the user pasted a Drive link, or the
  report arrived via a project/conversation that already saved it to Drive):
  use that file where it is, no upload needed.
- **No Drive home yet** (pasted raw text, an uploaded file with no Drive
  copy, a web page): save it into the Deep Research folder as a Google Doc if
  it's text, or the original file type if it's a document, directly into the
  matching topic subfolder (see step 3), never loose at the root. Use the
  Drive connector, or SA+DWD impersonating allison@expertpartners.com if the
  connector refuses the write.

## 3. Determine the informs-lane

Read the report's actual subject matter, not just its title or filename. Tag it
with the ADR 0045 brand registry lane it informs: Expert Partners, EPIC, Don
Hobbs Personal Brand, AG Personal Brand, AG Luxury, Free Agent Movement,
Infrastructure, or Operations (the established non-brand tag for EOS- and
ACN-class operational content). A report can inform more than one lane; list
all that genuinely apply, primary lane first.

Route the Drive save (step 2) to the topic subfolder that matches the primary
lane, using the same name map `tools/research-intake/sweep_drive.py` uses
(`SUBFOLDER_LANE_SEED` plus the `ROUTES` table). If the lane's subfolder
doesn't exist yet, create it there, exactly as the sweep script would.

## 4. Write the entry

When this skill saved the file, put this entry shape at the top of the Doc:

```
Title: <title, no em dashes, colon-style subtitles rendered with a comma>
Date: <YYYY-MM-DD>
Subject: <one to two sentences, the REAL subject, not a placeholder>
Informs lane: <lane, or lanes>
Superseded by: <None recorded. Fresh filing. -- or the named decision if the conversation already surfaced one>
Disposition: <awaiting ruling -- or implement / park / superseded, if Allison ruled on it in the same conversation>
```

When the file already lived in Drive, leave it untouched and give the same
entry in the reply. If Allison ruled on the paper in the same breath she
showed it to you ("yeah, park that" / "let's build this"), record that ruling
in Disposition rather than defaulting to awaiting ruling, and add a Decision
Log entry for it (newest at the top, with a Replaces note).

## 5. Track it only if still unruled

If Disposition is still "awaiting ruling", add one row to the Job Tracker: Job
`Rule on <title>`, Waiting on `Allison`, Next step `Rule on the research`. If
Allison already ruled in step 4, skip this step entirely.

## 6. Report

Report back in one line: the title, its lane, its disposition, and the Drive link.

## Rules

- Never use em dashes in anything this skill writes (org standard); render a
  title's colon-style subtitle with a comma instead, same as the sweep script.
- Never copy a report's full text anywhere but its one Drive home.
- Never touch a disposition Allison has already ruled away from the default.
