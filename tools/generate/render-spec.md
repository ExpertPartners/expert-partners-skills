---
classification: internal
classification_owner: allison
classification_date: 2026-08-06
---

# Render spec for the generated CLAUDE.md (ADR 0055 amendment 1)

Binding on generate/render.py and every template that feeds the CLAUDE.md target, from Phase 2 forward. Ordered by Allison's acceptance ruling on ADR 0055 (validation brief intake/2026-08-07-decision-brief-adr-0055-validation-accept-with-four-amendmen.md, commit 211418a).

## Size ceiling

The generated CLAUDE.md targets UNDER 200 LINES. Grounded in Anthropic's current guidance, read live 2026-08-06 at code.claude.com/docs/en/memory, which states "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence" and "CLAUDE.md files are loaded in full regardless of length, though shorter files produce better adherence." The current hand-written baseline is 110 lines. The render must never grow the file past the 200 line target, and a render that would exceed it fails the build rather than shipping a bloated file. Re-verify the live guidance at each phase that changes the template (doc-check rule).

## The boundary

CLAUDE.md holds stable, broadly applicable rules and canon POINTERS. Per-brand facts live in canon files (canon/<brand>/) that skills reference by path. Rendering canon content into CLAUDE.md wholesale is forbidden, it would quietly degrade every session. If an instruction only matters for one part of the tree, the brief's carried-forward option applies, path-scoped rules in .claude/rules/ with a paths front matter field (documented at the same live doc), a Phase 2 design choice, not a Phase 1 change.

## The gate stays

The byte-identity gate from Phase 1 remains the acceptance mechanism. Any template change dry-runs to a temp path first, and generate/checksums.txt plus the CI drift check must agree with what lands. If the byte-identity gate ever fails unexpectedly, hold Phase 2 (brief, benchmarks section).
