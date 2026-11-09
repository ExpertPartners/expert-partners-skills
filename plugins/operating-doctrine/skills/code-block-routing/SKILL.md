---
name: "code-block-routing"
description: "Retired as a routing gate. AI to AI relays, copy-box handoffs, routing lines, job-list filing and paste-block dispatch are gone. The AI starts Claude Code or Factory work itself in an isolated worktree. Use code blocks only for text Allison literally copies, such as a command or message she asked for. Inherits operating-doctrine."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "relays retired, code blocks only for text she copies"
---

# Code Block Routing

Retired under Decision Log 2026-11-08, Act by default, caution removed. AI to AI relays, copy-box handoffs, PASTE INTO routing lines, dispatch dedupe checks, job_create and job_claim filing, scheduled job_inbox checks and carry-back blocks no longer exist. The AI starts the work itself and reports what it did with links. This skill stays so existing references resolve.

## What remains

- Start the Claude Code or Factory run yourself. Allison does not carry a prompt anywhere.
- Work in an isolated git worktree cut from a freshly fetched remote ref (`git worktree add ../worktrees/<name> -b <name> origin/main`), so concurrent sessions never reset each other's uncommitted edits.
- Pick the model and effort with the session-model-advisor skill.
- Use a fenced code block only for text Allison literally copies, such as a command she asked for or a message she will send. Put the block alone with a one-line label. When she types S or s alone, that means sent.
- Links use file names, never raw URLs, and prose has no em dashes.

This skill inherits the operating-doctrine and never overrides it.
