---
name: expert-partners-systems-map
description: |
  The canonical map of where every Expert Partners system lives, what each system's one job is, and what access Claude already holds across the stack. Load this at the start of every Cowork project, every chat, and every Claude Code session, and fire it the moment any of the following happens: a decision is being made about where to store, log, or record something; Claude is about to claim a credential, tool, scope, or access is missing; Claude is about to ask Allison to grant access, authorize, connect, or take a manual action; uncertainty surfaces about what systems exist or what Claude can reach; a new project or session is starting cold. This skill exists so Claude never has to be re-told what it can access and never puts a thing in the wrong system. It inherits the operating-doctrine and never overrides it.
allowed-tools: []
---

# Expert Partners Systems Map and Access Map

This is the bible of where things live and what Claude can reach. The full version is in GitHub canonical, in the expert-partners doctrine area. This skill is the operative version that loads everywhere so nobody has to repeat it.

## The one rule

Each system has exactly one job. Discrepancies happen when a system is asked to carry something that belongs somewhere else. When in doubt, match the thing to the one job below, not to whatever is closest at hand.

## What each system does

| System | Its one job | What goes here | What never goes here |
| --- | --- | --- | --- |
| Memory (Claude) | Cross-session recall, auto-loads each session | Short structured facts a future session must know, plus pointers to canonical docs | Human-facing content, secrets, anything long |
| Notion | Single source of truth for funnel records and human logging | Funnel records (Funnels and Funnel Messages), status, human-readable logs | Technical doctrine, reference docs, secrets |
| GitHub canonical | Single source of truth for doctrine and technical reference | Doctrine, decisions (ADRs), references, project knowledge. Commit AND push | Funnel records, secrets or tokens |
| AWS | Compute and hosting, not a document store | Backend services, runtime token storage, scripts | Documentation, anything you go to read |
| 1Password | Secrets vault | Tokens, API keys, PITs, client secrets | Anything that belongs in GitHub or Notion |
| Airtable | Migration tracker only (retires after the migrations) | Migration status during the move | Permanent records, doctrine |
| Claude Code (M4) | Implementation engine for repo and GHL live work | Git commits and pushes, GHL API reads and writes via the app token, scripts. Tokens live here | The source of truth itself, open-ended brainstorming |
| Cowork | Orchestration and reasoning brain | Planning, Notion / Airtable / Drive via connectors, data-layer writes, handing Code exact bridge blocks, verification | Direct GHL token work (that runs in Code) |

## What Claude can already reach (the access map)

Claude already holds broad access across this stack. Do not claim access is missing. Verify it live first, then act.

| Capability | Where it lives / how Claude reaches it | Verify before claiming missing |
| --- | --- | --- |
| Anthropic API (Claude Code + Cowork) | Full programmatic access is open | Call the API or MCP tool directly |
| Credentials and secrets | 1Password, the primary store, multiple vaults | Search 1Password across all vaults |
| GoHighLevel | Marketplace app token, lives in Claude Code (M4) | Read or write via the app token in Code |
| Google file creation and admin | SA plus DWD path: service-account.json impersonating allison@. Never the read-only Google MCP connectors | Test SA plus DWD before any Google admin call |
| Connectors (read and act) | Airtable, Canva, ClickUp, Cloudflare, Coupler, Fireflies, Gamma, Gmail, GoDaddy, Google Calendar, Google Drive, Granola, Make, Mercury, Miro, Notion, Slack | Call the connector tool directly |
| Compute and backend | AWS | Reach the service directly |

## Verify-first protocol (inherits operating-doctrine)

Before Claude says any credential, scope, tool, or access is missing, and before Claude asks Allison for anything:

1. Check 1Password across all vaults.
2. Test the credential live against the source system.
3. Call the API or MCP tool directly.
4. Confirm the operation actually fails.

If it succeeds, execute and report. If it genuinely fails after all four, name the specific blocker and the engineering required to remove it. Allison's hands are the last resort, only after verified, evidence-backed failure. Claude implements. Allison directs.

## Commit versus push

Commit means saved locally on the machine. Push means it is in the shared canonical record every conversation reads. Always push doctrine and reference. A commit nobody pushed is invisible to the rest of the system.

## Quick decision guide

- A funnel record or a human log? Notion.
- Doctrine, a decision, or technical reference? GitHub canonical, commit and push.
- A fact a future session must recall? Memory.
- A secret or token? 1Password.
- Running code or a backend service? AWS.
- A rule that should apply everywhere? Org-level instructions.
- A rule for just one project? That project's instructions.
- Live GHL reads or writes? Claude Code, with the Marketplace app token. Cowork orchestrates and verifies.

## Where this skill lives

- Full bible: GitHub canonical, expert-partners doctrine area. Authoritative, version-controlled.
- This skill: provisioned org-wide in Organization settings, Skills. Loads in chat, Cowork, and Code beta.
- Memory: a one-line mirror that points here.

## Version

v1.0. Derived verbatim from the Expert Partners Systems Map bible dated 2026-06-19. Authored by Allison Gaddy.
