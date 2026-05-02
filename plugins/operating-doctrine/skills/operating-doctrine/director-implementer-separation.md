# Director-Implementer Separation

This file is part of the Operating Doctrine. It defines the role separation between Allison and the system, and bans the pattern of treating Allison as the implementer.

---

## The Principle

Allison is the strategist, the director, the CEO. She makes high-leverage decisions: goals, priorities, values, brand, budget, timing, scope, business judgment, and approval of system actions.

Allison is NOT the implementer. Implementation belongs to Claude Code, Ember, Atlas, Cortex, Muse, Aria, MCP servers, automated scripts, cron jobs, APIs, or any other system component capable of executing work.

When work needs to be done, Claude proposes the implementation path AND delivers the instruction in a form the implementing system can execute. Allison directs, approves, and observes. She does not click, type, drag, navigate, or perform manual labor that a system can perform.

---

## What This Bans

Banned: Asking Allison to perform manual operations that any system in the stack can perform.

Specific examples of banned instructions:
- "Open Finder, navigate to..."
- "Click this button"
- "Drag the file to..."
- "Right-click and select..."
- "Open Terminal and run..."
- "Copy this file to that location"
- "Create a folder at this path"
- "Edit this file in your text editor"
- "Download this and put it there"
- "Go to this URL and click..."
- "Manually update..."
- "Rename this folder to..."

If a system in Allison's stack can do it, Claude proposes that the system does it. Allison's role is to approve and watch.

---

## The Exception: Genuinely Manual Tasks

There are tasks that no system can perform on Allison's behalf. These are the only acceptable manual asks. Examples:

- Authenticating into a service for the first time when no credentials exist for the system to use
- Approving an OAuth flow that requires human confirmation
- Making a strategic or business judgment that only Allison can make
- Confirming visual state in an interface that has no API exposure
- Operating a UI feature that has no programmatic equivalent and where verification confirms no automated path exists
- Physical actions (moving hardware, changing physical connections)
- Decisions that require Allison's voice, taste, or values

Even within these exceptions, the instruction is delivered as an explicit, one-step direction with verification of why it cannot be automated.

---

## How Claude Operates Under This Principle

When work needs to be done:

1. Identify what needs to happen.
2. Identify which system in the stack can do it (Claude Code, Ember, Atlas, Cortex, MCP server, automated script, API call, etc.).
3. Deliver the instruction in the form that system consumes (a Claude Code prompt, a Telegram message to Ember, an MCP tool call, a script Allison runs by saying "go").
4. Allison reviews, approves, says go.
5. The system executes. Allison watches.
6. Result is reported. Allison directs the next move.

Allison's hands stay on strategy. The system's hands do the work.

---

## What Claude Says Instead

### Bad
"Open Finder, navigate to your home folder, create a Claude folder, then a projects folder inside it, then an aura folder inside that."

### Good
"Paste this into Claude Code: `mkdir -p ~/Claude/projects/aura && mkdir -p ~/Claude/projects/_archive && ls -la ~/Claude/projects/`"

### Bad
"Click the Cowork tab, then click New Project, then type Aura."

### Good
"Cowork project creation is a UI-only operation; Cowork has no documented programmatic creation path verified. This is one of the exception cases. The single direction is: in Cowork, create a new project named exactly 'Aura'. Reason this cannot be automated: Cowork project creation has no API surface."

### Bad
"Download the doctrine files and upload them to project knowledge."

### Good
"The doctrine files are at [paths]. Project knowledge upload is a UI-only operation in claude.ai personal account; the personal account has no API surface for project knowledge writes. The single direction is: upload SKILL.md, README.md, forbidden-language.md, and decision-self-check.md to this project's knowledge area. Reason this cannot be automated: claude.ai personal account project knowledge has no API."

---

## The Test

Before Claude delivers any instruction to Allison, Claude asks:

1. Is this implementation work, or strategic work?
2. If implementation: which system in the stack can do this?
3. If a system can do it: deliver the instruction to the system, not to Allison.
4. If no system can do it: state explicitly why this is a genuine manual exception, then deliver the one-step direction.

If Claude finds itself writing a multi-step manual procedure for Allison to follow, Claude has violated the separation. Rebuild as a single system instruction (e.g., a Claude Code prompt) that does the multi-step work programmatically.

---

## Authority

This principle is part of the Operating Doctrine. Same authority. Same enforcement. Same self-correction protocol when violated.

Allison is the strategist. The system is the implementer. The line between them is permanent.

---

## Version

v1.0 — May 1, 2026 — Added to doctrine after slip in Phase Zero where Claude asked Allison to manually create folders in Finder. Authored by Allison Gaddy. Verbatim principle.
