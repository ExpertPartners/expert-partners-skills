---
title: Decision 0107 propagation repair disclosure
date: 2026-10-12
classification: internal
status: implemented
---

# Decision 0107 propagation repair disclosure

Decision 0107 was already accepted in Aura at
`decisions/0107-retire-routing-naming-ceremony.md`. This change creates no new
decision and does not redesign routing architecture.

The 2.51.0 implementation stated the supersession at the top of the affected
skills, but live instructions remained in `pin`, `lane-spawn`,
`session-steward`, `canon-sync-protocol`, and `session-wrap` that could still
require or repair visible names. Version 2.52.0 removes those remaining active
naming-only gates. Historical version prose stays intact and explicitly
non-operative where it conflicts with decision 0107.

Preserved controls include isolated worktrees created from fresh remote refs,
model and effort requirements, exact execution-scope collision checks,
repository and host boundaries, production and credential safeguards,
destructive-action confirmation, decision capture, and evidence-based
closeout.
