---
name: session-wrap
description: "Closes out and hands off work on every surface. Writes the session record and continuity note, updates durable state, captures anything worth keeping, then archives. It also evaluates a finite mission when acceptance evidence lands. Fires when Allison types wrap and archive, or only W or w, in a Claude Code or Codex session, and then wraps and archives the session immediately."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Adopted into canonical 2026-08-05 (Skill Map Rulings lane, add-on brief note 4):
# estate-wide skill, adopted here per the ruling 9 pattern. Its earlier home and
# deployed copy in the retired aura repo are history in GitHub Archive. Content
# copied verbatim.
tier: plugin
zone: routing
status: live
subtitle: "the one canonical session close-out"
---

# Session Wrap

Wrap means finish the work, save what a cold future worker needs, and archive. No gates, no certification, no second question.

## Triggers

Allison typing wrap and archive, or only W or w, in a Claude Code or Codex session. Also run it when a session finishes its own work and nothing is left. Do the wrap, then archive the session yourself.

## What to do

1. Finish any remaining authorized work. Don't leave advice where an action would do.
2. Write the session record from artifacts and repo state, not chat scrollback. Use `reference/record-template.md`.
3. Write the continuity note as its own document so the next session can pick up cold. Use `reference/continuity-template.md`.
4. Save both in their owning home (the owning Drive brain for business material, the owning repo for code) and link them in your final report. Drive writes, the Decision Log format and connector fallbacks are in `reference/mcp-and-dashboard.md`.
5. Record each clear decision Allison made in the Decision Log, with a `Replaces:` note. A recommendation or brainstorm is not a decision.
6. Sweep once for anything a cold worker would need that nothing above captured, and route it to its home with `estate-memory-router`. Use `remember-this` for a future obligation. Say nothing if nothing qualifies.
7. If a canon or rule changed, run `canon-sync-protocol`.
8. Stop your own monitors, scheduled wakeups, subscriptions and background tasks.
9. Archive the session.

## Finite missions

When a mission has acceptance criteria and the evidence lands, say it is done and wrap. If criteria are not met, keep working.

## Rules

- No secrets, credentials or PII in any record. Name the 1Password item, never the value.
- If unsure of a value, say so. Never guess paths, IDs or dates.
- Point, don't paste. Link to the owning document instead of copying state.
- Report what you did with links, short.

## Session open

To resume, read the latest continuity note from the owning brain, check the actual repo, branch and open PRs, and carry on. See `reference/opening-prompt.md`.
