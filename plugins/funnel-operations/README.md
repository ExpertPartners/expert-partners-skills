# funnel-operations plugin: capability record

This record describes the package. It does not restate skill instructions: the sources of truth are [plugin.json](.claude-plugin/plugin.json), the `funnel-operations` entry in [marketplace.json](../../.claude-plugin/marketplace.json), and each `skills/<name>/SKILL.md`. When this file and a SKILL.md disagree, the SKILL.md wins. Origin: [decisions/0001](../../decisions/0001-add-funnel-operations-and-systems-map-plugins.md).

| Field | Value |
| --- | --- |
| Name | funnel-operations (marketplace `expert-partners`) |
| Problem solved | Builds and documents GHL funnels so no funnel exists undocumented, with Notion as the funnel record. |
| Audience | Non-technical Expert Partners and EPIC teammates, hand-held one step at a time; agents orchestrating that work. |
| Owner | Allison Gaddy. GHL reference and doctrine are owned by `ExpertPartners/partnersync`. |
| Canonical source | This folder in `ExpertPartners/expert-partners-skills`. |
| Current version | See `version` in plugin.json (0.2.1 at this record's last update). |
| Forms | Claude plugin (this package); standalone claude.ai uploads of funnel-documentation and funnel-migration. |
| Lifecycle | funnel-build and funnel-documentation live. funnel-migration live in metadata but STALE, retirement pending since 2026-07-27 (see its STATUS line). |
| Brand scope | Expert Partners and EPIC funnels, in the brand location named by the partnersync GHL location registry. |

## Skills

| Skill | Invoke when | Do not invoke for |
| --- | --- | --- |
| [funnel-build](skills/funnel-build/SKILL.md) | Building a brand new funnel. | Moving an existing funnel. |
| [funnel-documentation](skills/funnel-documentation/SKILL.md) | Documenting or logging any funnel into the Notion Funnels and Funnel Messages databases. | Building funnel pages. |
| [funnel-migration](skills/funnel-migration/SKILL.md) | Only when Allison confirms a genuine funnel move between GHL locations. | New builds or documentation; routine funnel work. |

## Dependencies

- Knowledge: `partnersync/reference/ghl-location-registry.md` (read live, wins over any doc); the Notion Funnel Object Model page.
- Tools: Notion connector (funnel records); Airtable connector (named by funnel-migration); Claude Code with the GHL Marketplace app token for GHL data-layer reads and writes. GHL builder-layer work is a UI step for a person or supervised computer use.

## Deployment and health

- Distributed through the expert-partners marketplace to claude.ai org plugin sync, Cowork, and Codex.
- Last recorded surface check: aura skill-lifecycle reconciliation of 2026-09-24 (point in time, not re-verified). Org sync current; stale standalone claude.ai uploads of funnel-documentation and funnel-migration; stale Codex synced mirror and `claude-cowork` import copies.
- 0.2.1 aligned the funnel-migration trigger description with its own STALE status so it no longer auto-fires on any funnel-move phrasing.
- Validation: `python3 tools/plugin-validate/validate_plugins.py`. No behavioral fixtures exist yet.

## Overlaps and candidates

- RETIREMENT CANDIDATES (need Allison's approval): funnel-migration itself (its STATUS line says retirement pending); the stale standalone claude.ai uploads of funnel-documentation and funnel-migration.
- ghl-asset-inventory, ghl-automation-design, ghl-tag-audit-and-cleanup (claude.ai uploads with no canonical source) are GHL operations, not funnel operations. partnersync owns GHL doctrine, and ghl-automation-design may conflict with aura ADR 0090 (GHL automation migrates to Activepieces on touch). Their home needs Allison's ruling; they are not imported here.
