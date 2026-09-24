---
classification: internal
classification_owner: allison
classification_date: 2026-09-23
date: 2026-09-23
source: Grok Repo Templates - Qualification Setup dispatch
project: expert-partners-skills
captured_at: 2026-09-23T20:41:40Z
topic: synthetic candidate package boundary
---
# Candidate input boundary

DRAFT / NOT RELEASED. This directory is a prepared input set, not a request to run it.

`requests.json` is an exact, immutable fixture capture of the canonical case file identified in `source-inputs.json`. It preserves every case ID and the complete original request. The copy is retained only to bind a future run to fixed bytes, with the source as owner. Do not edit the fixture to change a scenario.

`source-inputs.json` pins the source paths and bytes. `case-modes.json` preserves the canonical suite's mode distinction: ordinary cases use the parent's existing non-Grok paths; `grok-` cases load the current Auditor and Fixer references as well. Hypothetical Fixer situations remain synthetic situations. The audit-record reference supplies the existing output shape.

Each full case request is presented without rewriting or selectively extracting its subquestions. Each expressly independent situation starts with that situation's stated facts. Facts from another situation do not carry over. No prior candidate answers or grader feedback are included.

These source pointers are preparation inputs. They do not establish that an execution surface can deliver the fixed inputs, isolate independent runs, or capture actions. There are no responses or results in this directory.
