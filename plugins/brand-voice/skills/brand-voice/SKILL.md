---
name: brand-voice
description: Canonical brand context for the brands in the Estate brand registry operated by Allison Gaddy and Don Hobbs. Expert Partners is the parent organization brand, EPIC is the inner-circle program inside it and never a synonym for it, AG Personal Brand is Allison's master personal brand with The Strong Ones inside it, AG Luxury is her consumer-facing real estate brand, Free Agent Movement stands on its own canon, Don Hobbs operates as a sub-label under Expert Partners, and Moxie Signature Group is benched with consumer real estate routing to AG Luxury. Use this skill when writing, editing, or reviewing any brand-facing content to ground voice, tone, audience, differentiator, and visual identity decisions in the canonical positioning, then defer to the per-brand voice card. It inherits the operating-doctrine and never overrides it.
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
subtitle: "canonical brand context, registry per ADR 0045"
---

# Brand Voice -- canonical brand context

The brand registry's original record is aura ADR 0045 (resynced from the ADR as it read on 2026-08-05), kept as history. aura is retired, so the Drive brand canon Docs listed below are the live sources, and the HQ Rulebook and Decision Log govern if anything conflicts. The active brands,

- **Expert Partners**, the parent organization brand. EPIC and Expert Partners Coaching operate inside it, and Don Hobbs resolves under Expert Partners LLC as a sub-label.
- **EPIC**, the inner-circle program for the eXp vertical inside Expert Partners. Never a synonym for the parent.
- **AG Personal Brand**, the master personal brand for Allison Gaddy the person. The Strong Ones is a body of work inside it, no longer a peer brand.
- **AG Luxury**, Allison's consumer-facing real estate sales brand.
- **Free Agent Movement (FAM)**, its own brand on its own canon, never merged with the AG voice.

Retired, **Moxie Signature Group**. It never applies to new work. Consumer real estate routes to the current AG Luxury Drive canon.

Each brand's voice lives in its per-brand voice card, and this card defers to them, ep-brand, fam-epic-brand, ag-personal-brand, ag-luxury-brand, don-hobbs-brand, the-strong-ones-brand.

This skill also bundles two legacy brand context documents,

- `brand-context-expertpartners.md`, Expert Partners / EPIC (real estate coaching, mastermind, Inner Circle)
- `brand-context-freeagentmovement.md`, Free Agent Movement (the broader Free Agent Nation positioning)

## When to use

- Writing new copy for any brand in the registry
- Reviewing existing copy for brand consistency
- Choosing voice / tone / vocabulary for a new asset
- Deciding visual identity (typography, color, iconography)
- Confirming target audience and differentiator

## How to use

1. Identify which brand the work is for. If unclear, ask.
2. Read the relevant `brand-context-*.md` from this folder before drafting.
3. Apply the brand's voice rules verbatim. Note any tension between brands and surface it.
4. After drafting, validate against the brand-context doc -- every claim about audience, differentiator, voice, visual identity must match.

## Authoritative source

Brand canon Docs in Drive are authoritative and read with the Drive connector's `read_file_content` (plain text, not `read_doc`):
- V1 - Company Core - Expert Partners Brand Canon, https://docs.google.com/document/d/1XSiBzCLCHS_9_BXUrvV_Ysl2aBVY_I_kq_s5d25oY_4/edit
- V1 - Company Core - EPIC Brand Canon, https://docs.google.com/document/d/1W2QxjC_2iVY_-kWZLPEHRcztvEbpht5xcueWduOCdMU/edit
- V1 - Company Core - Free Agent Movement Brand Canon, https://docs.google.com/document/d/1t79nKkyml4db1Cq7hr2ApvOrEogqhuD2x12oOba3bQk/edit
- V1 - Company Core - Don Hobbs Brand Canon, https://docs.google.com/document/d/1yLCeKPCWhx3Ndx5j_o_H0Yo8UBprWTKtrpU3wLZLHK4/edit
- V1 - Company Core - Allison Gaddy Personal Brand Canon (AG Business Brain, Company Core [AG-BB]), https://docs.google.com/document/d/1lZy1Wu2q5k4NErJdNhAhtdUVkC_bXh_ddcUJgZUNxUU/edit
- V1 - Company Core - AG Luxury Brand Canon, https://docs.google.com/document/d/1IHjcFV7Bv023GIwgNxV5d4p_bu2R5l7yUW5F4VE_-yM/edit
- V1 - Company Core - Shared Writing Rules, https://docs.google.com/document/d/103y7LzzahVmGmUgCQukvwH2V7VKu3nhFEDteFrQBKqE/edit

The brand-context files in this folder are the fallback summary.

- Drive (live editing surface): per Allison's GitHub-everywhere principle, brand context lives in both Drive and GitHub. Drive is the editing canonical.
- GitHub canonical (this folder): `ExpertPartners/expert-partners-skills/plugins/brand-voice/skills/brand-voice/`
- The old Aura local mirror at `~/Claude/projects/Aura/skills/` was retired 2026-08-05; read canonical instead
- Should also reach Ember (M4 Mini) once cross-machine sync is wired.

## Update cadence

Brand context evolves. When updating:
1. Edit on Drive first.
2. Export to markdown, place in this folder, commit + push.
3. Verify the marketplace plugin shows the new version.
4. Verify Ember pulls the change.
