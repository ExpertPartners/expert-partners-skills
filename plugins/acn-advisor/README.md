# acn-advisor plugin: capability record

This record describes the package. It does not restate skill instructions: the sources of truth are [plugin.json](.claude-plugin/plugin.json), the `acn-advisor` entry in [marketplace.json](../../.claude-plugin/marketplace.json), and each `skills/<name>/SKILL.md`. When this file and a SKILL.md disagree, the SKILL.md wins.

| Field | Value |
| --- | --- |
| Name | acn-advisor (marketplace `expert-partners`) |
| Problem solved | Keeps the household ACN Advisor lane current: no missed ACN deadline or promotion window, and no advice resting on a stale fee, plan, or DingoBlu fact. |
| Audience | Allison and Don for their household ACN IBO positions, and the agent running the ACN Advisor lane. |
| Owner | Allison Gaddy. |
| Canonical source | This folder in `ExpertPartners/expert-partners-skills`. |
| Current version | See `version` in plugin.json (0.1.0 at this record's last update). |
| Forms | Claude plugin (this package) only. |
| Lifecycle | Live. |
| Brand scope | Structurally separate from Expert Partners LLC and every EP brand lane. Never use EP brand voice or EP business context here. |

## Skills

| Skill | Invoke when | Do not invoke for |
| --- | --- | --- |
| [acn-email-watch](skills/acn-email-watch/SKILL.md) | Start of every ACN Advisor session; "what came in from ACN". | Non-ACN inbox triage. |
| [acn-currency-check](skills/acn-currency-check/SKILL.md) | Monthly, and whenever Allison asks whether ACN knowledge is current. | General ACN questions answerable from the current brief. |

## Dependencies

- Knowledge: the 2026-08-05 ACN Master Research Brief (baseline named in acn-currency-check); the ACN Advisor guardrails both skills inherit.
- Tools: Gmail connector (search_threads) for acn-email-watch; Firecrawl monitors and scrape, or web fetch, for acn-currency-check.

## Deployment and health

- Distributed through the expert-partners marketplace to claude.ai org plugin sync, Cowork, and Codex.
- Last recorded surface check: aura skill-lifecycle reconciliation of 2026-09-24 (point in time, not re-verified). Both skills classified canonical and current, with no duplicate copies recorded.
- Validation: `python3 tools/plugin-validate/validate_plugins.py`. No behavioral fixtures exist yet.

## Overlaps and candidates

- Dangling dependency: acn-currency-check says it is "built on the capability-refresh pattern", and the standalone capability-currency skill says the same, but capability-refresh exists only as a claude.ai upload with no canonical source. Adopting it into this repo or folding it into capability-currency needs Allison's ruling; it is not imported here.
