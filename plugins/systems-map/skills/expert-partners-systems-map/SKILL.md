---
name: expert-partners-systems-map
description: |
  The canonical map of where every Expert Partners system lives, what each system's one job is, and what access Claude already holds across the stack. Load this at the start of every Cowork project, every chat, and every Claude Code session, and fire it the moment any of the following happens: a decision is being made about where to store, log, or record something; Claude is about to claim a credential, tool, scope, or access is missing; Claude is about to ask Allison to grant access, authorize, connect, or take a manual action; uncertainty surfaces about what systems exist or what Claude can reach; a new project or session is starting cold. This skill exists so Claude never has to be re-told what it can access and never puts a thing in the wrong system. It inherits the operating-doctrine and never overrides it.
allowed-tools: []
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: brain
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "where every system lives and what Claude can reach"
---

# Expert Partners Systems Map and Access Map

This is the operative map of where things live and what Claude can reach. The HQ Rulebook (Drive) is the first read and wins wherever the two differ. Business knowledge, rules, and decisions live in Google Drive, in the business brains: HQ Business Brain serves both companies, AG Business Brain is AG Luxury, EP Business Brain is Expert Partners. GitHub holds only what tools run from.

## Two words that are not the same

A business brain is a Google shared drive that holds knowledge. A repo is a GitHub folder that holds code. They are not the same thing, and the list of repos is just the code list.

## The one rule

Each system has exactly one job. Discrepancies happen when a system is asked to carry something that belongs somewhere else. When in doubt, match the thing to the one job below, not to whatever is closest at hand.

## First read for every cold session

The HQ Rulebook first, then the Chat to Code job list through job_status for what is in flight and what each job awaits (older work may still sit in the Job Tracker), then the owning brain's `00 START HERE` Doc. Pointers, never copies.

## The entity and the platform

Expert Partners LLC is the legal and operating entity. Don Hobbs operates under Expert Partners LLC; his IP (Gateway to Mastery, Think Big Live Big, 2020 Vision, events, coaching clients, and related training assets) lives under Expert Partners LLC. He is not a separate brand stack or a separate business container.

The brand registry's original record is aura ADR 0045 (ruled 2026-07-30), kept as history. Read current brand canon from the Drive brand canon Docs named in the brand-voice skill. The six active brands (Expert Partners, EPIC, Don Hobbs Personal Brand, AG Personal Brand, AG Luxury, Free Agent Movement), with Moxie Signature Group benched. No new Moxie work; consumer real estate routes to AG Luxury.

PartnerSync is the white-labeled GoHighLevel platform layer, the agency container (company `FOz8PSvqj7aYASb3wDzm`, "Expert Partners LLC dba Partner Sync"). It is plumbing, not a legal entity and not a brand. It holds five brand locations: EPIC, Expert Partners, AG Personal Brand, Moxie Signature Group (location exists physically; the brand is benched per aura ADR 0045, route no new work there), and Free Agent Nation Circle Community. The location IDs live in section 7.1 of the PartnerSync Identity Canon in Drive (02 - Identity Canon). The location a contact lives in IS the brand statement; the peer brand-tag vocabulary is retired as contact-routing architecture (ruled 2026-07-27; full rule in `partnersync/doctrine/cross-location-identity-rules.md`).

## Storage map: what each system does, one job each

| System | Its one job | What goes here | What never goes here |
| --- | --- | --- | --- |
| Notion | Single source of truth for funnel records and human logging. A funnel is not done until it lives here. | Funnel records (Funnels and Funnel Messages), status, human-readable logs, regenerated-from-canon human views | Doctrine, technical reference, secrets. Nothing authored in Notion competes with Drive canon |
| GitHub (`expert-partners-skills`, `partnersync-automation-backend`, and the other code repos) | Home for what tools run from: code, the skills marketplace, connected apps | Code, skills, automation source, a short AGENTS.md per repo | Knowledge, rules, decisions (those live in Drive) |
| Memory (Claude) | Claude cross-session recall, auto-loads each session | Short structured facts a future session must know, plus pointers to canonical docs | Human-facing content, secrets, anything long |
| 1Password | Secrets and tokens vault | Tokens, API keys, PITs, client secrets, passwords | Anything that belongs in GitHub or Notion. Secrets never go in GitHub or Notion |
| AWS | Compute and hosting, not a document store | Backend services, runtime token storage, scripts | Documentation, anything you go to read |
| n8n | Execution layer only: runs workflows, stores nothing canonical | Workflow runtime for automation logic that GHL's API cannot build (see the platform-selection rule below) | Design docs, doctrine, records. Every workflow's design doc lives in GitHub |
| Google Drive and Workspace | Home of the business brains: canonical knowledge, rules, and decisions as native Google Docs, plus the Job Tracker sheet | Docs, Sheets, collaboration surfaces | Secrets, code |
| Airtable | Migration tracker only, temporary (retires after the migrations) | Migration status during the move | Permanent records, doctrine |
| Claude Code (M4) | Implementation engine: git push and live GHL reads and writes | Git commits and pushes, GHL API reads and writes via the Marketplace app token, scripts. Tokens live here | The source of truth itself, open-ended brainstorming |
| Cowork | Orchestration, connector work, and verification | Planning, Notion / Airtable / Drive via connectors, data-layer writes, verification, handing Code exact bridge blocks | Direct GHL token work (that runs in Code) |

Not in the stack, stated so nobody re-litigates it:

- Obsidian is not part of the core architecture (ruled 2026-07-27). The one exception is EmberVault, Ember's internal knowledge vault on the M2: Ember-internal knowledge only, read-only to everyone else, never canonical, and nothing else stores anything there.
- Manychat is not live and not in the stack. It gets a doctrine line if and when Allison implements it.
- Make is frozen for new builds and migrating to n8n (ADR: `partnersync/decisions/0011-make-to-n8n-migration.md`). Existing scenarios run until rebuilt on touch.

## AI brains

The brains, their seats, machines, one jobs, SOULs, and liveness rules live in Bible Chapter 4 (`canonical-bible-chapter-4-brains-and-sync-topology.md`, expert-partners doctrine area). This map does not restate the roster. The aura strategic brain is retired (Aura Retirement Plan), and rules and decisions are read from the Drive business brains. Ember (M2) was frozen and quieted 2026-08-03 (workspaces archived, gateway disabled, writer crons off). The 2026-08-03 pause condition on agentic rebuilds (Aura's brain in place and locked down) was MET when the Estate Brain went live and proven on every surface (2026-08-04, re-proven 2026-08-07); Ember's wake now proceeds under the one-move wake ruling (`aura/intake/2026-08-05-ruling-ember-one-move-wake-sequencing.md`) in its own lane per the ledger. Everything else is planned and dark by design. Liveness is proven by process evidence, never by a fresh commit.

Ember has her own shared Google Drive, and it is her filing home at wake, she files her documents there when she wakes; the CI watchman is not Ember and keeps filing to the Aura Docs folder per document-formatting-standard (ruled 2026-08-05, robot delivery standards ruling, aura intake 3973c2b). Amended 2026-08-06 per the Ember Voice and Your Move Queue ruling (aura intake/2026-08-06-ruling-ember-voice-and-your-move-queue.md, ee86601). Every robot message to Allison speaks as Ember in first person (R2). Drive docs are for genuine reading material only, the your-move instruction lives on the board rendered at hq.allisongaddy.com, and robot texts link hq.allisongaddy.com only (R3, rail spec aura docs/estate/your-move-queue.md).

## Where canon is read from

Google Drive, through the Drive, Docs, and Sheets connectors. The Estate Brain MCP is retiring (Decision Log 2026-10-13), so do not read canon through it. Decisions are saved to the Decision Log, newest at the top.

## What Claude can already reach (the access map)

Claude already holds broad access across this stack. Do not claim access is missing. Verify it live first, then act.

| Capability | Where it lives / how Claude reaches it | Verify before claiming missing |
| --- | --- | --- |
| Anthropic API (Claude Code + Cowork) | Full programmatic access is open | Call the API or MCP tool directly |
| Credentials and secrets | 1Password, the primary store, multiple vaults | Search 1Password across all vaults |
| GoHighLevel | Marketplace app token, lives in Claude Code (M4) | Read or write via the app token in Code |
| Google file creation and admin | SA plus DWD path: service-account.json impersonating allison@. Never the read-only Google MCP connectors | Test SA plus DWD before any Google admin call |
| Web data (scraping, crawling, page monitoring) | Firecrawl, two lanes: Cowork / Claude app via the account-wide OAuth connector (`https://mcp.firecrawl.dev/v2/mcp-oauth`); Claude Code via the unattended lane (`https://mcp.firecrawl.dev/v2/mcp`) with a Bearer key read from `op://Automation/FIRECRAWL-API-KEY`, never plaintext | Call the Firecrawl MCP tools directly |
| Connectors (read and act) | Airtable, Canva, ClickUp, Cloudflare, Coupler, Fireflies, Gamma, Gmail, GoDaddy, Google Calendar, Google Drive, Granola, Make, Mercury, Miro, n8n, Notion, Slack | Call the connector tool directly |
| Compute and backend | AWS | Reach the service directly |
| Estate canon | Google Drive, Docs, and Sheets connectors against the business brains, first road on every surface (chat, Cowork, Code). First read: the HQ Rulebook | Read the HQ Rulebook through the Drive connector |

Warning line, ordered by Chapter 3: the Windsor GHL connector points at a foreign GHL company (`wVd3gUNItq6OXcVVS9xL`, not the PartnerSync agency) and must never be treated as a PartnerSync source.

## Google Workspace access doctrine (ruled 2026-08-06)

Canonical text, verbatim from the ruling record (aura `intake/2026-08-07-google-workspace-access-doctrine-ordered-gate-pasted.md`):

GOOGLE WORKSPACE ACCESS DOCTRINE. Claude holds super-admin-grade access to the expertpartners.com Google Workspace through the service account with domain-wide delegation, credential in 1Password, impersonating allison@expertpartners.com or don@expertpartners.com as the task requires, exact-scope law per DWD (request the exact authorized scope strings, verified by token-mint smoke test). On any surface with execution and open egress (Claude Code, Cowork), the SA road is the FIRST road for every Workspace operation, list, search, read, and write per the write-autonomy bright line. Claude never claims Workspace access is missing, never asks Allison to share, grant, or manually fetch, and never blames connector limitations without first attempting the SA road and reporting the exact failure with its error text. The claude.ai chat connectors are a convenience layer for inline reads only, their failures never mean access is missing, they mean route the operation through the Code road. Both impersonations live-verified 2026-08-05 (drive.readonly, canon sweep evidence). This doctrine inherits the operating-doctrine and the credential currency doctrine and never overrides either.

Honest limit, stated in the same ruling: this doctrine governs surfaces with execution (Claude Code, Cowork). It cannot heal the claude.ai chat surface, where the network wall blocks googleapis.com and the connector is the only road.

## Verify-first protocol (inherits operating-doctrine)

Before Claude says any credential, scope, tool, or access is missing, and before Claude asks Allison for anything:

1. Check 1Password across all vaults.
2. Test the credential live against the source system.
3. Call the API or MCP tool directly.
4. Confirm the operation actually fails.

If it succeeds, execute and report. If it genuinely fails after all four, name the specific blocker and the engineering required to remove it. Allison's hands are the last resort, only after verified, evidence-backed failure. Claude implements. Allison directs.

## Commit versus push

Commit means saved locally on the machine. Push means it is in the shared canonical record that every conversation reads. Always push doctrine and reference. A commit nobody pushed is invisible to the rest of the system.

## Universal rules versus project rules

Universal rules belong in org-level Claude instructions, where they apply everywhere across every project and session. Project-specific rules belong in that one project's instructions only. Do not paste universal rules into each project; that creates drift the moment one copy changes. One universal rule, one canonical home.

## GHL: app-token-first, and the capability boundary

GHL writes are app-token-first. Use the GoHighLevel Marketplace app token that lives in Claude Code (M4) as the primary path for reads and writes, before reaching for any other credential or a manual UI action.

The GHL capability boundary holds: the data layer is writable through the API (contacts, tags, custom fields, opportunities, and similar records), while the builder layer is blocked to automation (funnels, workflows, and other canvas-built objects are UI-only and the builder canvas is CSP-blocked). Match the work to the writable layer; route builder-layer changes to the eyes-on path. Production-contact deletion still requires a fresh explicit confirmation.

## The automation platform-selection rule (ruled 2026-07-27)

Per automation, the implementer (Claude Code / Cowork) makes the platform call against current developer docs, with a hard bias for Claude-buildable. Allison never hand-builds workflows: where GHL API limits would force manual builder work, the logic goes to n8n. GHL keeps native sends on the location's number and sending reputation. Full doctrine: `partnersync/doctrine/automation-platform-selection.md` (moved there 2026-09-08 from the retired ghl-automation repo); read alongside aura decision 0090 (2026-09-04), which routes portable orchestration into Activepieces on touch.

## Web data acquisition: Firecrawl-first (ruled 2026-07-27)

Firecrawl is the primary tool for all scraping, crawling, and JS-heavy page monitoring, including the war room page monitors and the monthly capability refresh. Native web search / fetch is the fallback; browser automation is the last resort. Firecrawl is live and paid: team "Expert Partners" (renamed from Team Ember Team), Hobby plan, 5,000 credits per month, Smart Upgrade ON.

Two lanes, matched to the surface:

1. **Cowork / Claude app:** the account-wide custom connector at `https://mcp.firecrawl.dev/v2/mcp-oauth`, OAuth individual sign-in.
2. **Claude Code (unattended):** `https://mcp.firecrawl.dev/v2/mcp` with an `Authorization: Bearer` key read from `op://Automation/FIRECRAWL-API-KEY`. The key is never written in plaintext anywhere: not in configs, not on command lines, not in chat.

## Quick decision guide

- A cold session orienting? The HQ Rulebook first through the Drive connector, then the Chat to Code job list through job_status, then the Job Tracker for older work.
- A funnel record or a human log? Notion. A funnel is not done until it lives there.
- A decision? The Decision Log in Drive, newest at the top. Rules and knowledge? The owning brain in Drive. Code the tools run from? GitHub.
- A fact a future session must recall? Memory.
- A secret or token? 1Password. Never GitHub or Notion.
- Running code or a backend service? AWS.
- Automation logic GHL's API cannot build? n8n executes it; the design doc lives in GitHub.
- A document for a human to receive or collaborate on? Google Workspace. Never canonical.
- A rule that should apply everywhere? Org-level instructions.
- A rule for just one project? That project's instructions only.
- Live GHL reads or writes? Claude Code, with the Marketplace app token, app-token-first. Cowork orchestrates and verifies.
- Scraping, crawling, or watching a JS-heavy page? Firecrawl first, on the lane that matches the surface. Native web search / fetch is fallback; browser automation is last resort.
- Which brand owns this contact? The location it lives in. Brand labels are for assets that genuinely need one, never a routing layer.
- Consumer real estate work? AG Luxury, never Moxie (benched, aura ADR 0045).

## Where this skill lives

- Full rules: the HQ Rulebook in Drive. Authoritative.
- This skill: provisioned org-wide in Organization settings, Skills. Loads in chat, Cowork, and Code.
- Memory: a one-line mirror that points here.

## Version

v3.0. Repointed 2026-10-13 to the Drive brain (Decision Log 2026-10-13); the GitHub systems map bible is retired as the first read. Prior v2.5 sync 2026-09-19
