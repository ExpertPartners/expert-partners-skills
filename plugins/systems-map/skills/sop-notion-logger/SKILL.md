---
name: "sop-notion-logger"
description: "Automatically log every SOP to the Notion SOPs Database the moment it is created or materially revised, in any CoWork session. Fires whenever an SOP, standard operating procedure, process doc, team workflow instruction, or runbook is written, updated, promoted, or archived, even if nobody says the word \"log\". Also fires when reviewing Claude Code session output that created an SOP, so the Notion entry gets created from CoWork."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-11-02 (Decision Log 2026-10-25, Which of the 19 personal
# skills move into the marketplace). Moved in from Allison's claude.ai skills.
tier: plugin
zone: cataloging
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "every SOP logged to the Notion SOPs Database"
---

# SOP Notion Logger

Every SOP created or materially revised in CoWork gets logged to the Notion SOPs Database in the same session, automatically, without Allison asking. This is a standing rule, not an optional step. An SOP that is not in Notion does not exist.

## Where it goes

Notion Ops Hub: Expert Partners > SOP Hub > SOPs Database.
Data source: search Notion for the database named "SOPs Database" and use its data source (parent type data_source_id). This public repository holds no Notion IDs, so always find it by name.
If the Notion tools cannot reach this data source, search Notion for "SOPs Database" under the SOP Hub page and verify before concluding anything moved. Never create a second SOP database.

## When to fire

1. You just wrote a new SOP (a file, a doc, or a process laid out for the team to follow).
2. You materially revised an existing SOP (roles, steps, systems, or cadence changed, not typo fixes).
3. An SOP was promoted (Draft to Active), sent for review, or retired.
4. You are processing output from a Claude Code session that created an SOP but could not log it (look for a LOG TO NOTION block or an unlogged SOP file).

## How to log, no duplicates ever

1. Search the data source first for an existing entry with the same or near-same name. If it exists, update that page (status, content summary, last reviewed date). Only create a new page if no entry exists.
2. Create or update with these properties:
   - Name: the SOP title, no date prefix.
   - Status: Draft for anything not yet promoted by Allison; Active only when Allison has explicitly promoted it; In Review, Completed, Archived as appropriate.
   - Department: best fit from Marketing, Finance, Operations, Customer Service.
   - Tools Needed: pick from the existing multi-select options only; do not invent new options.
   - SOP Review Frequency (Months): 1 for processes tied to fast-changing external programs, 3 for internal automation-backed processes, 6 for stable ones.
   - date:Last Reviewed (SOP):start: today's date.
3. Page content: a short summary (what it covers, roles, automation status), plus the canonical file location (project folder path, Drive doc, or repo path). The Notion page is the index card; the file is the SOP.
4. Confirm to Allison in one line that it was logged, with the Notion link.

## Formatting

No em dashes anywhere. No bold or italics in body prose. Plain headers, short paragraphs.

## Flags

Logging an SOP usually means a process was created or changed, so check whether these fire and raise them: FLAG: UPDATE KNOWLEDGE DOCS, FLAG: UPDATE TEAM GPT, FLAG: TEAM TRAINING NEEDED (Maria, Joyce, Jevelyn, or the VAs).
