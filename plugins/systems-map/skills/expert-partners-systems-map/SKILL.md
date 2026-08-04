---
name: expert-partners-systems-map
description: |
  The canonical map of where every Expert Partners system lives, what each system's one job is, and what access Claude already holds across the stack. Load this at the start of every Cowork project, every chat, and every Claude Code session, and fire it the moment any of the following happens: a decision is being made about where to store, log, or record something; Claude is about to claim a credential, tool, scope, or access is missing; Claude is about to ask Allison to grant access, authorize, connect, or take a manual action; uncertainty surfaces about what systems exist or what Claude can reach; a new project or session is starting cold. This skill exists so Claude never has to be re-told what it can access and never puts a thing in the wrong system. It inherits the operating-doctrine and never overrides it.
allowed-tools: []
# --- skill-map metadata (additive, all optional) ---
tier: plugin
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "where every system lives and what Claude can reach"
---

# Expert Partners Systems Map and Access Map

This is the bible of where things live and what Claude can reach. The full version is in GitHub canonical, in the expert-partners doctrine area (`doctrine/expert-partners-systems-map.md`). This skill is the operative version that loads everywhere so nobody has to repeat it. When this skill and the full bible ever diverge, the bible wins and this skill is re-synced from it.

## The one rule

Each system has exactly one job. Discrepancies happen when a system is asked to carry something that belongs somewhere else. When in doubt, match the thing to the one job below, not to whatever is closest at hand.

## First read for every cold session

The estate manifest is the brain's table of contents: `aura/docs/estate/estate-manifest.md`. It indexes every canonical source with a last-verified date and evidence. A cold session reads it first, then the lane ledger (`aura/docs/estate/lanes.md`) for what is in flight and what each lane awaits. Pointers, never copies; the manifest carries its own maintenance rules.

## The entity and the platform

Expert Partners LLC is the legal and operating entity. Don Hobbs operates under Expert Partners LLC; his IP (Gateway to Mastery, Think Big Live Big, 2020 Vision, events, coaching clients, and related training assets) lives under Expert Partners LLC. He is not a separate brand stack or a separate business container.

The brand registry is canonical in aura ADR 0045 (ruled 2026-07-30): six active brands (Expert Partners, EPIC, Don Hobbs Personal Brand, AG Personal Brand, AG Luxury, Free Agent Movement), with Moxie Signature Group benched. No new Moxie work; consumer real estate routes to AG Luxury.

PartnerSync is the white-labeled GoHighLevel platform layer, the agency container (company `FOz8PSvqj7aYASb3wDzm`, "Expert Partners LLC dba Partner Sync"). It is plumbing, not a legal entity and not a brand. It holds five brand locations: EPIC, Expert Partners, AG Personal Brand, Moxie Signature Group (location exists physically; the brand is benched per aura ADR 0045, route no new work there), and Free Agent Nation Circle Community. The canonical registry with IDs, states, purposes, and the implementation priority order is `partnersync/reference/ghl-location-registry.md`; a mirror lives in the expert-partners repo at `reference/ghl-location-registry.md`. The location a contact lives in IS the brand statement; the peer brand-tag vocabulary is retired as contact-routing architecture (ruled 2026-07-27; full rule in `partnersync/doctrine/cross-location-identity-rules.md`).

## Storage map: what each system does, one job each

| System | Its one job | What goes here | What never goes here |
| --- | --- | --- | --- |
| Notion | Single source of truth for funnel records and human logging. A funnel is not done until it lives here. | Funnel records (Funnels and Funnel Messages), status, human-readable logs, regenerated-from-canon human views | Doctrine, technical reference, secrets. Nothing authored in Notion competes with git canon |
| GitHub canonical (`aura`, `expert-partners`, `ghl-automation`, `expert-partners-skills`, `partnersync`) | Single source of truth for doctrine, decisions, and technical reference. `aura` is the seat of the operating system; its `decisions/` directory is canonical for ADRs and rulings (queue clean 0001 through 0047, renumber evidence in `aura/decisions/README.md`). Per-repo decisions directories that predate this remain as historical records. | Doctrine, decisions (ADRs), references, project knowledge, every n8n workflow's design doc. Commit AND push | Funnel records, secrets or tokens |
| Memory (Claude) | Claude cross-session recall, auto-loads each session | Short structured facts a future session must know, plus pointers to canonical docs | Human-facing content, secrets, anything long |
| 1Password | Secrets and tokens vault | Tokens, API keys, PITs, client secrets, passwords | Anything that belongs in GitHub or Notion. Secrets never go in GitHub or Notion |
| AWS | Compute and hosting, not a document store | Backend services, runtime token storage, scripts | Documentation, anything you go to read |
| n8n | Execution layer only: runs workflows, stores nothing canonical | Workflow runtime for automation logic that GHL's API cannot build (see the platform-selection rule below) | Design docs, doctrine, records. Every workflow's design doc lives in GitHub |
| Google Workspace | Delivery and collaboration only, never canonical | Documents delivered to humans, collaboration surfaces, transcripts and formal docs for reference | Canonical doctrine, decisions, records of truth |
| Airtable | Migration tracker only, temporary (retires after the migrations) | Migration status during the move | Permanent records, doctrine |
| Claude Code (M4) | Implementation engine: git push and live GHL reads and writes | Git commits and pushes, GHL API reads and writes via the Marketplace app token, scripts. Tokens live here | The source of truth itself, open-ended brainstorming |
| Cowork | Orchestration, connector work, and verification | Planning, Notion / Airtable / Drive via connectors, data-layer writes, verification, handing Code exact bridge blocks | Direct GHL token work (that runs in Code) |

Not in the stack, stated so nobody re-litigates it:

- Obsidian is not part of the core architecture (ruled 2026-07-27). The one exception is EmberVault, Ember's internal knowledge vault on the M2: Ember-internal knowledge only, read-only to everyone else, never canonical, and nothing else stores anything there.
- Manychat is not live and not in the stack. It gets a doctrine line if and when Allison implements it.
- Make is frozen for new builds and migrating to n8n (ADR: `partnersync/decisions/0011-make-to-n8n-migration.md`). Existing scenarios run until rebuilt on touch.

## AI brains

The brains, their seats, machines, one jobs, SOULs, and liveness rules live in Bible Chapter 4 (`canonical-bible-chapter-4-brains-and-sync-topology.md`, expert-partners doctrine area). This map does not restate the roster. One strategic brain (Aura, M4 / Cowork) is active. Ember (M2) was frozen and quieted 2026-08-03 (workspaces archived, gateway disabled, writer crons off); all agentic rebuilds, including the Ember rebuild and the OpenClaw-to-SDK migration, are paused until Aura's brain (the estate manifest plus the Estate Brain MCP) is in place and locked down (ruled 2026-08-03). Everything else is planned and dark by design. Liveness is proven by process evidence, never by a fresh commit.

## The Estate Brain MCP: in build, not live

The Estate Brain MCP (target endpoint mcp.expertpartners.com) does NOT exist yet. Never claim it is live; any memory or document recording it as deployed with tools is a phantom of the spec (Allison's correction, 2026-08-03). Until its acceptance passes with live proof, every surface reads canon through the GitHub connector against ExpertPartners repos, or the local clone in Code. The build runs in the Estate Brain MCP Build lane (Code session of the same name, home Aura: Strategic Advisor / Estate Brain MCP Build); status lives in the lane ledger.

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
| Estate canon (until the Estate Brain MCP ships) | GitHub connector against ExpertPartners repos (chat and Cowork); local clone (Code). First read: the estate manifest | Fetch `aura/docs/estate/estate-manifest.md` directly |

Warning line, ordered by Chapter 3: the Windsor GHL connector points at a foreign GHL company (`wVd3gUNItq6OXcVVS9xL`, not the PartnerSync agency) and must never be treated as a PartnerSync source.

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

Per automation, the implementer (Claude Code / Cowork) makes the platform call against current developer docs, with a hard bias for Claude-buildable. Allison never hand-builds workflows: where GHL API limits would force manual builder work, the logic goes to n8n. GHL keeps native sends on the location's number and sending reputation. Full doctrine: `ghl-automation/doctrine/automation-platform-selection.md`.

## Web data acquisition: Firecrawl-first (ruled 2026-07-27)

Firecrawl is the primary tool for all scraping, crawling, and JS-heavy page monitoring, including the war room page monitors and the monthly capability refresh. Native web search / fetch is the fallback; browser automation is the last resort. Firecrawl is live and paid: team "Expert Partners" (renamed from Team Ember Team), Hobby plan, 5,000 credits per month, Smart Upgrade ON.

Two lanes, matched to the surface:

1. **Cowork / Claude app:** the account-wide custom connector at `https://mcp.firecrawl.dev/v2/mcp-oauth`, OAuth individual sign-in.
2. **Claude Code (unattended):** `https://mcp.firecrawl.dev/v2/mcp` with an `Authorization: Bearer` key read from `op://Automation/FIRECRAWL-API-KEY`. The key is never written in plaintext anywhere: not in configs, not on command lines, not in chat.

## Quick decision guide

- A cold session orienting? The estate manifest first, `aura/docs/estate/estate-manifest.md`, then the lane ledger.
- A funnel record or a human log? Notion. A funnel is not done until it lives there.
- Doctrine, a decision, or technical reference? GitHub canonical, commit and push. New ADRs and rulings land in `aura/decisions/`.
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

- Full bible: GitHub canonical, expert-partners doctrine area. Authoritative, version-controlled.
- This skill: provisioned org-wide in Organization settings, Skills. Loads in chat, Cowork, and Code.
- Memory: a one-line mirror that points here.

## Version

v2.2. Derived verbatim from the Expert Partners Systems Map bible v2.2 dated 2026-08-03 (expert-partners commit 756363c). Changes from skill v2.0: catches up the missed v2.1 Firecrawl doctrine, then adds the v2.2 rulings (aura canonical with decisions/ as the ADR seat, estate manifest first-read, Estate Brain MCP in build and not live, brand registry per aura ADR 0045 with Moxie benched, Ember freeze and agentic rebuild pause). Authored by Allison Gaddy.
