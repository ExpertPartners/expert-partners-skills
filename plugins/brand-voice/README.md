# brand-voice plugin: capability record

This record describes the package. It does not restate skill instructions: the sources of truth are [plugin.json](.claude-plugin/plugin.json), the `brand-voice` entry in [marketplace.json](../../.claude-plugin/marketplace.json), and each `skills/<name>/SKILL.md`. When this file and a SKILL.md disagree, the SKILL.md wins. Editable brand truth lives in each brand's owning repo, not here.

| Field | Value |
| --- | --- |
| Name | brand-voice (marketplace `expert-partners`) |
| Problem solved | Grounds any brand-facing draft in the right brand's voice, audience, and naming so agents do not blend brands. |
| Audience | Allison Gaddy, Don Hobbs, and the agents writing for their brands (Claude, Codex, Cowork). |
| Owner | Allison Gaddy (package). Brand truth: each brand's owning repo; person-level Allison voice: `ExpertPartners/allison-gaddy` `voice/` (aura ADR 0086). |
| Canonical source | This folder in `ExpertPartners/expert-partners-skills`. Registry: aura ADR 0045. |
| Current version | See `version` in plugin.json (0.5.2 at this record's last update). |
| Forms | Claude plugin (this package). Related: the Allison Gaddy Voice Writer custom GPT (ChatGPT) for the AG Personal Brand voice. |
| Lifecycle | Live. `moxie-signature-group-brand` is benched (ADR 0045) and still ships. |

## Skills

| Skill | Invoke when | Do not invoke for |
| --- | --- | --- |
| [brand-voice](skills/brand-voice/SKILL.md) | Choosing which brand applies; cross-brand review. | Final voice rules (defer to the per-brand card). |
| [ep-brand](skills/ep-brand/SKILL.md) | Expert Partners as a company. | EPIC or FAM program copy, personal content. |
| [fam-epic-brand](skills/fam-epic-brand/SKILL.md) | EPIC and Free Agent Movement content. | YouTube @TheAllisonGaddy and personal content (ag-personal-brand). |
| [ag-personal-brand](skills/ag-personal-brand/SKILL.md) | Allison as an individual: YouTube, speaking, essays, LinkedIn. | EP, EPIC, FAM, or consumer real estate. |
| [ag-luxury-brand](skills/ag-luxury-brand/SKILL.md) | Consumer luxury real estate under the Allison Gaddy name. | Agent-facing or coaching content. |
| [don-hobbs-brand](skills/don-hobbs-brand/SKILL.md) | Anything written as Don. | Allison's voice. |
| [the-strong-ones-brand](skills/the-strong-ones-brand/SKILL.md) | The Strong Ones book, podcast, and community (inside AG Personal Brand). | Business or real estate content. |
| [moxie-signature-group-brand](skills/moxie-signature-group-brand/SKILL.md) | Revival work only, when Allison asks. | Any new work (route to AG Luxury). |

## Dependencies

- Knowledge: per-brand owner canon (`canon/` in `ExpertPartners/ag-personal-brand` and `ExpertPartners/ag-luxury`; `docs/DECISION-LOG.md` in ag-luxury); legacy `skills/brand-voice/brand-context-*.md` as background only; `themes/`.
- Tools: optional estate-brain MCP `get_brand_context` (serves ag-luxury and don-hobbs as of 2026-09-25). No actions or write connectors.

## Deployment and health

- Distributed through the expert-partners marketplace to claude.ai org plugin sync, Claude Code, Cowork, and Codex.
- Last recorded surface check: aura skill-lifecycle reconciliation of 2026-09-24 (point in time, not re-verified; re-read the platform before acting). It recorded org sync current at 0.5.1, a stale Claude Code install of brand-voice 0.2.0 shadowing the org copy (repair: `claude plugin update brand-voice@expert-partners`), stale standalone claude.ai uploads of don-hobbs-brand and moxie-signature-group-brand, and a stale Codex synced mirror.
- Validation: `python3 tools/plugin-validate/validate_plugins.py`. No behavioral fixtures exist yet.

## Overlaps and candidates

- The Allison Gaddy Voice Writer GPT (setup guide: `ExpertPartners/ag-personal-brand` `project-knowledge/ag-custom-gpt-setup-guide.md`) overlaps ag-personal-brand. Decision recorded: the skill is the packaged capability and the GPT is a consumption surface; GPT prompt text is not copied here (ADR 0086). Re-pointing or retiring the GPT needs ChatGPT access.
- RETIREMENT CANDIDATE: moxie-signature-group-brand (benched but still shipped) and its standalone claude.ai upload. Removal needs Allison's approval.
- The legacy `brand-context-moxie.md` background file follows the Moxie decision.
