---
name: research-intake
description: >
  Files a research report that surfaces in ANY conversation, pasted, uploaded,
  or linked, into the department folder of the business brain that owns its
  subject, named Cal's way, [Brand-Department][V1.0] Name. AG Business Brain owns
  AG Luxury and Allison's brand. EP Business Brain owns Expert Partners, EPIC,
  Don and PartnerSync product and market research. HQ Business Brain owns AI
  operations, Factory, Ember, Claude, skills, tools and PartnerSync build and
  shared operations material. Never files into the Deep Research folder. Use
  whenever a research report, deep-research output, or external analysis
  appears in conversation with intent to use it, not just to read it once.
  Answers Allison's question FIRST, files behind the answer, never files the
  same report twice, asks one question naming the two likeliest homes when the
  owning department is unclear, then reports the Drive link.
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

Before writing anything, search all of Drive, shared drives included, through
the Drive connector for the report's Drive file id if it has one, or its title
if it does not. A filed copy carries a Cal prefix in front of the title, so
search for the title inside the name, not for an exact name. If you find it,
this is a rediscovery, not a new filing. Create nothing, skip to step 6 and
report the existing Doc. If the existing Doc still sits in the Deep Research
folder, say so in the report and leave it for the Drive Cleanup work in HQ
Operations to move. Never copy it.

## 2. Find the brain that owns the subject

Read the report's actual subject matter, not just its title or filename, and
pick the one brain that owns it.

| Subject | Owning brain | Brand tag |
| --- | --- | --- |
| AG Luxury, Allison's personal brand | AG Business Brain | AG |
| Expert Partners, EPIC, Don, PartnerSync product and market research | EP Business Brain | EP |
| AI operations, Factory, Ember, Claude, skills, tools, PartnerSync build and shared operations material | HQ Business Brain | HQ |

PartnerSync is split the way the HQ Rulebook department words split it.
Research about the PartnerSync product, its market, its customers or its
competitors goes to EP Business Brain. Material about building PartnerSync or
running its shared operations goes to HQ Operations, into the
`PartnerSync Source Material [HQ-BB]` folder, found by name, and is named
`[HQ-Operations][V1.0] Title`.

## 3. Find the department it serves

Pick the department the report's knowledge serves, using the HQ Rulebook
department words. Each word matches a department folder in that brain, and
the folder name ends with the department and the brain tag, like
`Marketing [AG-BB]` or `Operations [HQ-BB]`. Find the folder by name in Drive.
Never hard-code a folder id.

| Brain | Department word | Folder |
| --- | --- | --- |
| AG, EP | Marketing | Marketing |
| AG, EP | Sales | Sales |
| AG | Listings | Listings |
| AG, EP | Client | Client Experience |
| AG, EP | Operations | Ops |
| EP | Product | Product Discovery |
| AG, EP | Private | Private |
| HQ | Finance | Finance |
| HQ | People | People and HR |
| HQ | Employees | AI Employees |
| HQ | Skills | Skills Vault |
| HQ | Reporting | Analytics and Reporting |
| HQ | Audits | Routine Audits, read-only audit reports only |
| HQ | Operations | Operations |

Research never goes to Company Core, the Archives, Claude Outputs, or a folder
this skill invents. HQ owns folder structure, so if the right department
folder does not exist yet, treat the home as unclear (step 4) instead of
creating one.

## 4. When the home is unclear, ask one question

When the report fits more than one brain or department, or no department
clearly, ask Allison one question that names the two likeliest homes, for
example, "Should this go to EP Marketing or AG Marketing?" Save nothing until
she answers. Then file it where she says.

## 5. Give the report its one home

- **No Drive home yet** (pasted text, an uploaded file with no Drive copy, a
  web page): save it into the department folder from step 3, as a Google Doc
  if it is text, or in its original file type if it is a document. Use the
  Drive connector, or SA+DWD impersonating allison@expertpartners.com if the
  connector refuses the write.
- **Already in its owning brain's department folder**: use that file where it
  is. No upload, no copy.
- **Already in Drive somewhere else**: move that same file, by its file id,
  into the department folder from step 3, and rename it to Cal's naming in the
  same step (HQ Rulebook, Every move includes a relabel). Never copy it. If
  the move is refused, leave the file where it is and say so in the report.

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
