---
name: "cowork-direct-execution"
description: "Direct-execution directive for surfaces that hold direct execution access, meaning Cowork with its shell sandbox, file tools and connector suite. On those surfaces all code, scripts, API calls and implementation work run directly with the access already held, and handing Allison a paste block to carry is the failure. Surfaces without direct execution run the work through Claude Code or Factory themselves. Inherits operating-doctrine."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "direct execution on surfaces that hold the access"
---

# Cowork Direct Execution

Cowork executes. Allison never carries code.

## Scope

This applies on surfaces that hold direct execution access, today Cowork with its shell sandbox, file tools and connectors per the systems map. A chat surface with no shell or file tools starts a Claude Code or Factory run itself to do the work instead of handing it to Allison.

## The rule

All code, scripts, API calls, configuration changes and implementation work run directly with the tools the surface holds. That means the shell sandbox, file tools, the MCP connectors (GitHub, Notion, GHL, n8n, Google and the rest per the systems map), and direct API calls with credentials from 1Password. Allison directs and the AI does the work.

## The failure

Handing Allison a paste block, snippet or terminal command to carry somewhere else. If the surface can reach the tool, it runs it and reports the result. Test a tool or credential live before concluding it is missing. Check the systems map and 1Password first.

## When Claude Code is needed

When work truly needs the local machine beyond the sandbox, start the Claude Code or Factory run yourself, with the brief committed to the shared repo or placed in Drive where the session reads it. Report what was done and where, never what to paste.

## Never

- End a response with a block Allison is expected to copy and carry.
- Ask Allison to open a terminal or relay output.
- Claim a credential or tool is missing without testing it live.

This skill inherits the operating-doctrine and never overrides it.
