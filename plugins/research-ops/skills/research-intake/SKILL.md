---
name: research-intake
description: >
  Files a research report that surfaces in ANY conversation, pasted, uploaded,
  or linked, into the department folder of the business brain, AG, EP or HQ,
  that owns its subject under the live HQ Rulebook, named Cal's way,
  [Brand-Department][V1.0] Name. Never files into the Deep Research folder.
  Use whenever a research report, deep-research output, or external analysis
  appears in conversation with intent to use it, not just to read it once.
  Answers Allison's question FIRST, files behind the answer,
  never files the same report twice, asks one question naming the two
  likeliest homes when the owning department is unclear, then reports the
  Drive link.
tier: plugin
zone: cataloging
status: live
subtitle: "file a research report into the brain that owns its subject"
---

# Research Intake Skill

Files a research report into the business brain that owns its subject, in the
department folder the report serves, named the way Cal names files. Allison
ruled this on Nov 2, 2026, recorded in the Decision Log entry of 2026-11-03,
Google Drive Cleanup and Organization. Cal teaches that useful research goes
into the knowledge of the department it serves, and none of her material
teaches a central research folder. Research has no single home folder. Each
report has one home, in the brain that owns it.

The Deep Research folder in Drive is no longer research's home. Nothing this
skill does writes into it.

## 0. Answer first

The report is evidence Allison is using RIGHT NOW to think something through.
Answer her actual question or give her the read she asked for before doing any
filing work. Filing happens after, silently, and is reported in one line at
the end, never instead of engaging with the content.

## 1. Never duplicate a filing

Before writing anything, search Drive, shared drives included, through the
Drive connector for the report's Drive file id if it has one, or its title if
it does not. A filed copy carries a Cal prefix in front of the title, so
search for the title inside the name, not for an exact name.

A file id match is the report. A title match is only a candidate, because
anyone can give a file the same title. Count a title match as the report only
when it is the one candidate and its content is the same report Allison
showed you. If no candidate passes, treat the report as having no Drive home
yet, and step 5 saves it from the content Allison supplied.

- **A match already filed in a department folder of AG, EP or HQ Business
  Brain**: this is a rediscovery, not a new filing. Create nothing, add no
  entry and no Job Tracker row, skip to step 8 and report the existing Doc.
- **Any other match**, including the linked file itself or a copy in the Deep
  Research folder: that file is the report. Use it, make no second copy, and
  carry on to step 2. Step 5 moves it home.

## 2. Find the brain that owns the subject

This skill carries no copy of which brain owns which subject. That lives only
in the routing canon: Organization Instructions, the HQ Rulebook and the
Decision Log, all in HQ Business Brain, Company Core, each found by its
title. Read all three live every time, and let the newest Decision Log entry
win. If any of them cannot be read, save and move nothing, and tell Allison
which source failed.

Read the report's actual subject matter, not just its title or filename, and
pick the one brain, AG, EP or HQ Business Brain, whose ownership in the
routing canon covers it. The brain's short name is its brand tag: AG, EP or
HQ.

Where the routing canon splits one brand across brains by the kind of
material, file by the kind of material the report is, into the folder the
canon names for that kind.

## 3. Find the department it serves

Pick the department the report's knowledge serves, using the department words
in the HQ Rulebook for that brain. Each word matches a department folder in
that brain, and the folder name ends with the department and the brain tag,
like `Marketing [AG-BB]` or `Operations [HQ-BB]`. Find the folder by name in
Drive. Never hard-code a folder id.

A folder name alone proves nothing, because anyone can share a folder with
the same name. Accept a folder only when it is the one match inside that
brain's own folder tree and is owned by allison@expertpartners.com or sits in
an Expert Partners shared drive. Ignore folders reached only through Shared
with me. If no folder or more than one folder passes, treat the home as
unclear (step 4).

Research goes only to a folder the routing canon names as a department folder
or a subfolder for that kind of material, never to a folder this skill
invents. HQ owns folder structure, so if the right folder does not exist yet,
treat the home as unclear (step 4) instead of creating one.

The target folder is the department folder found here, or the subfolder the
routing canon names for that kind of material, checked the same way.

## 4. When the home is unclear, ask one question

When the report fits more than one brain or department, or no department
clearly, ask Allison one question that names the two likeliest homes, for
example, "Should this go to EP Marketing or AG Marketing?" Save and move
nothing for this report until she answers. Then file it where she says.

Where the question goes depends on where this skill is running.

- **Claude chat or Cowork**: ask in chat and wait for her answer.
- **Factory, Codex or Claude Code**: never wait inside the app. Follow the
  HQ Rulebook question path: post the question as a comment starting
  `Question for Allison` on the code job's GitHub issue, or use
  `job_finish` with outcome `needs-allison` for the affected non-code job
  and one line starting `Recommend:` in its summary, following the live
  tool schema. This requests a decision, not completion. Never use `done`
  for unfinished work or finish an unrelated job. Retrieval and technical
  gaps stay AI owned unless an actual founder decision is missing.
  Keep working on everything that does not depend on this report, and file
  it where she says once she answers.

## 5. Give the report its one home

- **No Drive home yet** (pasted text, an uploaded file with no Drive copy, a
  web page): save it into the target folder from step 3, as a Google Doc if
  it is text, or in its original file type if it is a document. Use the Drive
  connector, or SA+DWD impersonating allison@expertpartners.com if the
  connector refuses the write.
- **Already in its owning brain's target folder**: use that file where it is.
  No upload, no copy.
- **Already in Drive somewhere else, owned by allison@expertpartners.com or in
  an Expert Partners shared drive**: move that same file, by its file id, into
  the target folder from step 3, and rename it to Cal's naming in the same
  step (HQ Rulebook, Every move includes a relabel). Never copy it. If the
  move is refused, leave the file where it is and say so in the report.
- **Already in Drive, owned by someone else**: leave it where it is, with its
  name unchanged, because a move or rename changes it for its owner and every
  collaborator. Never copy it. Say so in the report and name the home it
  belongs in.

Name the file `[Brand-Department][V1.0] Title`. Brand is the tag from step 2.
Department is the department word from step 3, as one whole word in title
case. A new filing starts at V1.0. Render a colon-style subtitle in the title
with a comma, and use no em dashes. For example,
`[AG-Marketing][V1.0] Dallas Luxury Market Report, Q3 2026` or
`[HQ-Operations][V1.0] Factory Missions Research`.

## 6. Write the entry

When this skill saved the file, put this entry shape at the top of the Doc:

```
Title: <title, no em dashes, colon-style subtitles rendered with a comma>
Date: <YYYY-MM-DD>
Subject: <one to two sentences, the REAL subject, not a placeholder>
Home: <brain and department, e.g. AG Business Brain, Marketing>
Superseded by: <None recorded. Fresh filing. -- or the named decision if the conversation already surfaced one>
Disposition: <awaiting ruling -- or implement / park / superseded, if Allison ruled on it in the same conversation>
```

When the file already lived in Drive, leave its contents untouched and give
the same entry in the reply. If Allison ruled on the report in the same breath
she showed it to you ("yeah, park that" / "let's build this"), record that
ruling in Disposition rather than defaulting to awaiting ruling, and add a
Decision Log entry for it (newest at the top, with a Replaces note).

## 7. Track it only if still unruled

If Disposition is still "awaiting ruling", add one row to the Job Tracker: Job
`Rule on <title>`, Waiting on `Allison`, Next step `Rule on the research`. If
Allison already ruled in step 6, skip this step entirely.

## 8. Report

Report back in one line: the file name, its brain and department, its
disposition, and the Drive file as a clickable file name. For a rediscovery,
report the existing Doc the same way.

## The Deep Research folder and the daily sweep

- Nothing writes into the Deep Research folder, not this skill and not a sweep.
- The brand-registry lane tags of ADR 0045 and the Deep Research subfolder
  routing (`SUBFOLDER_LANE_SEED` and `ROUTES`) are retired. The owning brain
  and department replace them.
- The daily sweep (`tools/research-intake/sweep_drive.py`) lived in the
  retired aura repo and is not part of this skill. Its filing into the Deep
  Research folder is retired. If a sweep runs again, it only reports new
  research files sitting outside an owning brain, and it writes nothing.

## Rules

- Never use em dashes in anything this skill writes (org standard); render a
  title's colon-style subtitle with a comma instead.
- One home only. Never copy a report's full text anywhere but its one Drive
  home in its owning brain.
- Never touch a disposition Allison has already ruled away from the default.
