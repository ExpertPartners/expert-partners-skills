---
name: brand-voice
description: Canonical brand context for the brands in the aura ADR 0045 registry operated by Allison Gaddy and Don Hobbs. Expert Partners is the parent organization brand, EPIC is the inner-circle program inside it and never a synonym for it, AG Personal Brand is Allison's master personal brand with The Strong Ones inside it, AG Luxury is her consumer-facing real estate brand, Free Agent Movement stands on its own canon, Don Hobbs operates as a sub-label under Expert Partners, and Moxie Signature Group is benched with consumer real estate routing to AG Luxury. Use this skill when writing, editing, or reviewing any brand-facing content to ground voice, tone, audience, differentiator, and visual identity decisions in the canonical positioning, then defer to the per-brand voice card. It inherits the operating-doctrine and never overrides it.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: brands
status: live
inherits: operating-doctrine
brand-scope: null
defers-to:
  - ep-brand
  - fam-epic-brand
  - ag-personal-brand
  - ag-luxury-brand
  - don-hobbs-brand
  - the-strong-ones-brand
  - moxie-signature-group-brand
subtitle: "canonical brand context, registry per ADR 0045"
---

# Brand Voice, canonical brand context

The brand registry is canonical in aura ADR 0045 (resynced from the ADR as it read on 2026-08-05). The active brands,

- **Expert Partners**, the parent organization brand. EPIC and Expert Partners Coaching operate inside it, and Don Hobbs resolves under Expert Partners LLC as a sub-label.
- **EPIC**, the inner-circle program for the eXp vertical inside Expert Partners. Never a synonym for the parent.
- **AG Personal Brand**, the master personal brand for Allison Gaddy the person. The Strong Ones is a body of work inside it, no longer a peer brand.
- **AG Luxury**, Allison's consumer-facing real estate sales brand.
- **Free Agent Movement (FAM)**, its own brand on its own canon, never merged with the AG voice.

Benched, **Moxie Signature Group**. Per ADR 0045 it never applies to new work, and consumer real estate routes to AG Luxury. Retained for revival only.

Each brand's voice lives in its per-brand voice card, and this card defers to them, ep-brand, fam-epic-brand, ag-personal-brand, ag-luxury-brand, don-hobbs-brand, the-strong-ones-brand, and moxie-signature-group-brand (benched).

This skill also bundles three legacy brand context documents,

- `brand-context-expertpartners.md`, Expert Partners / EPIC (real estate coaching, mastermind, Inner Circle)
- `brand-context-freeagentmovement.md`, Free Agent Movement (the broader Free Agent Nation positioning)
- `brand-context-moxie.md`, Moxie Signature Group (BENCHED per ADR 0045, retained for revival only)

## When to use

- Writing new copy for any brand in the registry
- Reviewing existing copy for brand consistency
- Choosing voice / tone / vocabulary for a new asset
- Deciding visual identity (typography, color, iconography)
- Confirming target audience and differentiator

## How to use

1. Identify which brand the work is for. If unclear, ask.
2. Load the per-brand voice card for that brand (ep-brand, fam-epic-brand, ag-personal-brand, ag-luxury-brand, don-hobbs-brand, the-strong-ones-brand). Where the estate-brain MCP is connected, also call `get_brand_context("<brand>")` for the live owner-repo context, which wins over any inline fallback.
3. Use the legacy `brand-context-*.md` documents in this folder only as background. They cover Expert Partners / EPIC, Free Agent Movement, and the benched Moxie brand only, and they predate the ADR 0045 registry, so any conflict resolves to the per-brand card and the owning brand repo.
4. Apply the brand's voice rules verbatim. Note any tension between brands and surface it.
5. After drafting, validate against the per-brand card. Every claim about audience, differentiator, voice, and visual identity must match.

## Authoritative source

- Editable brand truth lives in each brand's owning GitHub repo (for example `ExpertPartners/ag-personal-brand` and `ExpertPartners/ag-luxury`, each with a `canon/` folder). Person-level Allison voice lives in `ExpertPartners/allison-gaddy` under `voice/` (aura ADR 0086). This plugin packages that truth for agent sessions; it is not an editing surface.
- GitHub is the canonical technical source and marketplace-manifest home for this packaged capability (aura ADR 0098): `ExpertPartners/expert-partners-skills/plugins/brand-voice/`.
- Drive copies of brand documents are working or legacy material, not the editing canonical. When a Drive document disagrees with the owning repo, the owning repo wins.
- The old Aura local mirror at `~/Claude/projects/Aura/skills/` was retired 2026-08-05; read canonical instead.
- Ember (M4 Mini) delivery is not wired; the Ember repos are parked. Do not assume Ember carries this skill.

## Update cadence

Brand context evolves. When updating:
1. Change the brand truth in the owning brand repo first (or in `allison-gaddy/voice/` for person-level voice).
2. Re-sync the affected per-brand card in this plugin from that source, then bump the plugin version in both `plugins/brand-voice/.claude-plugin/plugin.json` and the `.claude-plugin/marketplace.json` entry, in the same commit.
3. Open a pull request. Deployment to claude.ai, Claude Code, and other surfaces happens through the deployment path after merge, not from the edit itself.
