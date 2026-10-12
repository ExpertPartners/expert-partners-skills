---
name: "cowork-direct-execution"
description: "Direct-execution directive scoped to surfaces that actually hold direct execution access, meaning Cowork with its shell sandbox, file tools, and connector suite per the systems map. On those surfaces all code, scripts, API calls, and implementation work execute directly with the access already held, and handing Allison a paste block to courier is the failure condition. On claude.ai chat surfaces without direct execution this skill stands down entirely and code-block-routing governs every dispatch to Claude Code. Dispatching a properly routed paste block from a surface that cannot execute the work itself is CORRECT behavior, not the failure condition. This skill never overrides code-block-routing. Where dispatch is the only execution path, code-block-routing wins. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
defers-to:
  - code-block-routing
brand-scope: null
subtitle: "direct execution on surfaces that hold the access"
---

# Cowork Direct Execution

Permanent directive authored by Allison, 2026-07-31. Scoped 2026-08-06 after the code-block-routing catalog diagnosis (aura intake/2026-08-07-diagnosis-code-block-routing-catalog-failure.md, culprit 3). Cowork executes. Allison never couriers code. And a surface that cannot execute dispatches properly instead of pretending it can.

## Scope: where this skill fires and where it stands down

This skill fires ONLY on surfaces that actually hold direct execution access. Today that means Cowork with its shell sandbox, file tools, and connector suite per the expert-partners-systems-map. Before treating this skill as active, verify the surface: if there is no shell sandbox and no file tools, this skill is not in play.

On claude.ai chat surfaces without direct execution, this skill stands down entirely and code-block-routing governs every dispatch to Claude Code. Dispatching a properly routed paste block from a surface that cannot execute the work itself is CORRECT behavior, not the failure condition. The failure condition this skill names (Allison as courier) exists only where the surface could have executed the work itself and handed her a paste block anyway.

## The rule

On execution-capable surfaces, all code, scripts, API calls, configuration changes, and implementation work run directly using the tools the surface already holds: the shell sandbox, file tools, the MCP connectors across the stack (GitHub, Notion, GHL, n8n, Google via SA plus DWD, and the rest per the systems map), and direct API calls with credentials from 1Password. Cowork implements; Allison directs. Her hands are the last resort.

## The failure condition

On execution-capable surfaces, handing Allison a paste block, code snippet, or terminal command to carry into Claude Code, a terminal, or any other surface is the failure condition this directive exists to remove. Before producing any paste block or manual step, Cowork must prove it cannot execute the work itself: check the systems map, check 1Password across all vaults, and test the tool or credential live. If Cowork can reach it, Cowork runs it and reports the result. Never conclude access is missing without a live test.

## When Claude Code is genuinely required

Rare cases only, on execution-capable surfaces: work that truly needs Allison's local machine beyond the sandbox, or a long-lived Claude Code session that already owns a lane. Even then, Allison's clipboard is never the transport. Route the brief through an automated relay: commit it to the shared GitHub repo or place it in the designated Google Drive location where the Code session reads it, following the same zero-courier pattern as the video-transcript-relay skill. Report to Allison what was executed and where, never what to paste. (On surfaces without direct execution this section does not apply; there, code-block-routing's paste-block dispatch is the correct and only path.)

## Precedence

This skill never overrides code-block-routing. Where dispatch is the only execution path, code-block-routing wins.

What this skill changes, on execution-capable surfaces only, is whether a hand-off happens at all: where the surface can execute the work directly, it does, and no courier block is produced (example: canon promotions to the partnersync repo happen through Cowork's GitHub access directly, with the commit hash reported in the same response, no Canon Doc Sync paste block). Whenever a block IS dispatched, from any surface, code-block-routing governs it entirely: the routing line, the waiting-on statement, the lane ledger row, the pin choreography, all of it. In the rare automated-relay case the routing target is a repo or Drive file rather than Allison's hands, and code-block-routing still governs the structure. This skill inherits the operating-doctrine and never overrides it.

## Never (execution-capable surfaces only)

- Never end a response with a fenced block Allison is expected to copy anywhere
- Never ask Allison to open a terminal, paste into Claude Code, or relay output back
- Never claim a credential, tool, or scope is missing without testing it live first
- Never mark implementation work done until it has actually executed and been verified

None of these prohibitions apply on a surface without direct execution access. There, this skill is silent and code-block-routing rules the dispatch.
