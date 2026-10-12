---
classification: internal
source: claude-code
project: expert-partners-skills
captured_at: 2026-09-08T12:45:00-05:00
---

# Disclosure: NORTH review correction, remaining active text brought to decision 0091 and the exception-only title verification

Filed by the worker session Startup Efficiency - Routing Simplification, owning
table Startup Efficiency, room NORTH'S ESTATE CONTROL TOWER. This is the second
disclosure on the same branch. The first,
intake/2026-09-08-disclosure-worker-title-form-superseded-by-decision-0091.md,
covered the worker title form. NORTH's review of tip 127d1e0 found active
text still teaching the superseded behavior, and this commit corrects it in
place. The ruling-provenance gate requires a disclosure per commit that
rewrites a cited ruling line, so this file exists for this commit.

## What this commit supersedes in active text

Ruling of record aura decisions/0091-allison-controlled-two-word-routing-names.md.

One. Table-name permanence. Active lines in code-block-routing (Lane Identity
By Surface), lane-spawn (Table Birth mechanic 4, the What did NOT come back
paragraph, Naming, the Rules list), session-steward (section 0), and the pin
and code-block-routing descriptions said a Table is named once, exactly once,
set once, or stable for the Table's life, and the Birth declaration template
read exact permanent table name. Decision 0091 lets Allison rename an
existing Table by explicit direction, so each active line now says the name
stands until Allison herself renames it, prior names kept as historical
aliases, and names are exactly two clear words. The code-block-routing
heading Session Naming: Table Name Plus Job now reads Two-Word Job Title.

Two. Routine title rereads. Active lines in code-block-routing (Session Naming
mechanics 1 and 2, Window Titles Drift consequences, Lane Identity By Surface,
the SESSION NAME template, the Desktop and CLI dispatch paragraph), pin
(section 5 birth paragraph, CLI paragraph, the First-contact self-verification
recipe and its report line, section 4 envelope check), and session-steward
(sections 1 and 2) commanded an independent transcript reread after every
successful set_session_title call and a disk self-verification at every first
contact. These now state the implementation detail this branch adopted on
2026-09-08 (no rule change under decision 0074): one search for the native
tool, a successful title call is its own verification, and the transcript
reread is the exception path for a tool error, actually observed drift, or
evidence needed to resolve a mismatch. Decision 0074's rule that a worker
titles itself at birth and repairs its own drift is unchanged.

## What is preserved

Every version-history paragraph (lane-spawn v1.4, v1.5, v1.8; pin v4.8, v4.9;
session-steward v1.4; code-block-routing's 2026-08-07 and 2026-08-26 drift
amendments) keeps its original wording and is marked SUPERSEDED IN PART or
followed by the superseding amendment, per the append-and-mark convention. No
history was rewritten to make a search come back empty. Decisions 0065, 0074
(as amended), 0077, 0081, 0082, 0084, and 0088 are otherwise untouched, and
no registry, registrar record, ledger column, or routing-state write exists.

## Scope of the commit that carries this disclosure

code-block-routing, lane-spawn, session-steward, pin, and the 2.48.0 CHANGELOG
entry. Plugin version unchanged at 2.48.0 (still unreleased on this branch).
