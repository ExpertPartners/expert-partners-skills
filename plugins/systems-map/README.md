# systems-map plugin: capability record

This record describes the package. It does not restate the map: the sources of truth are [plugin.json](.claude-plugin/plugin.json), the `systems-map` entry in [marketplace.json](../../.claude-plugin/marketplace.json), and [skills/expert-partners-systems-map/SKILL.md](skills/expert-partners-systems-map/SKILL.md). The skill is the operative mirror of the full bible at `ExpertPartners/expert-partners` `doctrine/expert-partners-systems-map.md`; the bible wins and the skill is re-synced from it. Origin: [decisions/0001](../../decisions/0001-add-funnel-operations-and-systems-map-plugins.md).

| Field | Value |
| --- | --- |
| Name | systems-map (marketplace `expert-partners`) |
| Problem solved | Tells every session where each Expert Partners system lives, its one job, and what access agents already hold, so nobody re-explains the stack. |
| Audience | Every agent working for Allison Gaddy; loads at session start. |
| Owner | Allison Gaddy. Content owner: the bible in `ExpertPartners/expert-partners`. |
| Canonical source | Bible first (`doctrine/expert-partners-systems-map.md`, v2.5 at expert-partners 6eabe3b); this package mirrors it. |
| Current version | See `version` in plugin.json (0.5.2 at this record's last update); skill body synced to bible v2.5 on 2026-09-19. |
| Forms | Claude plugin (this package); a standalone claude.ai upload of expert-partners-systems-map; a legacy `systems-map` claude.ai upload. |
| Lifecycle | Live. Inherits operating-doctrine and never overrides it. |

## Invoke when / do not invoke for

- Invoke: session start; any question about where a system lives, which repo or tool owns a job, or what access is held.
- Do not invoke for: brand voice (brand-voice plugin), operating rules (operating-doctrine), or live platform state, which is re-read from the platform.

## Dependencies

- Knowledge: the bible and the canonical bible chapters in `ExpertPartners/expert-partners` `doctrine/`; the aura Estate Manifest.
- Tools: estate-brain MCP (preferred road to canon), GitHub connector or local clones as fallback.

## Deployment and health

- Distributed through the expert-partners marketplace to claude.ai org plugin sync, Cowork, and Codex.
- Last recorded surface check: aura skill-lifecycle reconciliation of 2026-09-24 (point in time, not re-verified). Org sync current; stale Codex synced mirror and stale `claude-cowork` import copies in Codex.
- Validation: `python3 tools/plugin-validate/validate_plugins.py`. No behavioral fixtures exist yet.

## Known drift (recorded 2026-09-25, not fixed here because the bible must change first)

- The Estate Brain paragraph lists "Six tools"; the live estate-brain server exposes eight (adds get_manifest and update_lane_row).
- The same paragraph carries a drift flag that get_brand_context lacks ag-luxury and don-hobbs; both are served as of 2026-09-25.
- The brand line reads "six active brands" including a Don Hobbs Personal Brand, while aura ADR 0045 lists five active brands with Don Hobbs as a sub-label under Expert Partners. Verify whether a later decision changed this before editing.
- Fix path: bible version bump in `ExpertPartners/expert-partners`, then re-sync this skill and bump both manifest files.

## Overlaps and candidates

- RETIREMENT CANDIDATE: the legacy `systems-map` claude.ai upload (superseded by expert-partners-systems-map). Removal needs Allison's approval in the claude.ai UI.
- The standalone claude.ai upload of expert-partners-systems-map duplicates the org plugin; the recorded 2026-08-07 approach is that the org plugin governs.
