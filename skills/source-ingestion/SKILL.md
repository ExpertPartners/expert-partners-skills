---
name: source-ingestion
description: >
  Files any source material (PDF, Word doc, deck, YouTube video, transcript,
  course, Drive file, pasted text, research report, web page, interview, or
  internal original) into a durable, machine-readable source dossier in its
  correct estate home, keeping provenance and outside material distinct from
  Allison/Expert Partners synthesis. Use for "add this to GitHub", "ingest
  this", "save this source", "make this core", "this informs Authority
  Engine", "add to External Methodologies", or any plain pointer at material
  already in context, no command word required. Classifies type, creator,
  domain, methodology, CORE status (recommended only, never silently set),
  and ownership (Allison/EP, third-party, unclear); resolves the destination
  at runtime, preparing the package and reporting a planned destination when
  the owning repo does not exist yet. Write-capable surfaces build, validate,
  commit, and push; advisory surfaces classify and hand off a packet instead
  of claiming a write.
tier: user
zone: cataloging
status: live
subtitle: "ingest any source into the estate source library"
---

# Source Ingestion -- v1.0 (2026-08-23)

One canonical ingestion protocol for every source Allison encounters, so she
never has to remember a magic command. Full protocol detail lives in
`reference/` because this file stays a map, not the territory:

- `reference/protocol.md` -- the full classification protocol, the CORE rule,
  the source-vs-synthesis rule, third-party handling, and the two surface
  authority modes.
- `reference/dossier-schema.md` -- the two-file source dossier schema
  (`README.md` + `source-record.md`) and the field definitions behind it.
- `reference/routing.md` -- how a destination repo is resolved at runtime,
  the domain -> creator -> source conceptual layout for the planned
  ExpertPartners/external-methodologies library, and what to do when the
  owning repo does not exist yet.
- `reference/chatgpt-adapter.md` -- how the ChatGPT-compatible package is
  generated from this same canonical source, never hand-maintained.
- `scripts/scaffold_dossier.py` -- deterministic dossier-folder builder. Use
  it instead of hand-writing dossier files; deterministic scaffolding is more
  reliable than re-improvising folder shape from memory every time.

## Triggers

Any of: "add this to GitHub", "put this in the library", "add this to the
repo", "ingest this", "save this source", "make this core", "this needs to
inform Authority Engine", "add this to External Methodologies" -- and any
plain-language pointer at a PDF, doc, deck, video, transcript, course, Drive
file, pasted block, research report, web page, or interview already in
context, even when Allison never says a command word at all.

## Surface authority -- decide this before anything else

- **Write-capable** (Claude Code, or another surface with verified repo-write
  access): inspect live destination state, build the dossier with
  `scripts/scaffold_dossier.py`, validate it, commit and push under the
  normal push-authority rules, report exact paths and commit SHA.
- **Advisory** (North / Estate Control Tower, Cowork, plain Claude chat,
  ChatGPT, or anything without proven repo-write access): classify the
  source, resolve the destination, build the packet description, and hand it
  off as an implementation brief to a write-capable surface. Never claim a
  commit happened. This split must stay testable -- see `tests/`.

Full detail: `reference/protocol.md` section "Surface authority modes".

## The flow

1. **Classify.** Title, creator, source type, domain, methodology/program,
   provenance, original location, date (or date accessed), and ownership
   (Allison/EP, third-party, or unclear). Detail: `reference/protocol.md`.
2. **CORE is a recommendation, never a silent elevation.** Only Allison's own
   words ("core", "foundational", "really important", "we need to follow
   this", "make sure the Estate knows this") set CORE true; otherwise you may
   recommend it but she rules. Detail: `reference/protocol.md` "CORE rule".
3. **Resolve the destination.** Explicit destination from Allison wins; else
   read live estate canon; else determine the actual owning repo. If it does
   not exist yet, prepare the package and report the planned destination,
   never create the repo. Detail: `reference/routing.md`.
4. **Build the dossier** with `scripts/scaffold_dossier.py`, markdown-first,
   traceable back to page/timestamp/section where the source allows it.
   Detail: `reference/dossier-schema.md`.
5. **Write or hand off** per the surface authority mode above.

## Source vs synthesis (never blur this)

A source dossier carries outside material, attributable to its actual
creator. Allison/Expert Partners doctrine derived from that material belongs
in the downstream owning repo (the same project map the `intake` skill
already uses), with lineage back to its sources, never inside the source
dossier itself. This skill never relabels third-party methodology as
Expert-Partners-owned IP. Detail: `reference/protocol.md`.

## Composing with existing tools (never duplicate them)

- A **deep research report** that is reusable knowledge, not yet a brand
  decision, is reusable source/research material. If its natural home is the
  aura research corpus, this skill does not re-file it: it hands off to the
  `research-intake` skill, which already owns `docs/research/INDEX.md` in
  aura. If Allison has already ruled it into downstream doctrine ("this is
  now Authority Engine doctrine"), route it to that downstream owner with
  source lineage instead, per `reference/routing.md`.
- A **session summary or captured conversation** bound for a project's
  `intake/` inbox is the `intake` skill's job, not this one.
- This skill owns the broader multi-format estate source library: books,
  decks, videos, courses, transcripts, and any source material that is not
  already covered by one of the two skills above.

## Rules

- No em dashes in anything this skill writes (org standard); use commas or
  double hyphens.
- Never fabricate provenance. If ownership or licensing is genuinely unclear,
  say so in the dossier rather than inventing a legal ruling.
- Never silently relabel third-party material as Allison/Expert-Partners IP.
- Markdown-first. Never convert PDF/DOCX/deck/video/audio to an intermediate
  format as a ritual; extract or transcribe what is needed for search and
  reasoning, keep or point at the original, and preserve the trace back to
  page, slide, timestamp, or section.
- Never create `ExpertPartners/external-methodologies`. It is planned, not
  built (confirmed not to exist, live, 2026-08-23); prepare the package,
  report the planned destination.
- Never migrate a real corpus as a side effect of testing or building this
  skill. Synthetic fixtures only in `tests/fixtures/`.
- Run the sibling-session visibility check before committing to a repo this
  session does not already own.
