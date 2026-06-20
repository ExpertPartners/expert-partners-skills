# ADR 0001: Add funnel-operations and systems-map plugins

Date: 2026-06-19
Status: Accepted

## Context

Four skills were published to the claude.ai managed-skills store but had no home
in this canonical repo: `funnel-build`, `funnel-documentation`, `funnel-migration`
(Shared skills), and `expert-partners-systems-map` (Organization skill). An org-wide
scan of all 44 ExpertPartners repos confirmed they existed only as local working
copies (`~/Claude/projects/Funnel Operations/skills/` and a local-agent-mode session
copy). With no canonical source, re-cutting upload ZIPs meant hunting local disk
each time, and there was nothing to verify uploads against.

## Decision

Land the four skills in this repo as two new plugins, matching the existing modular
one-concern-per-plugin pattern (operating-doctrine, brand-voice, content-engines):

- `plugins/funnel-operations`: funnel-build, funnel-documentation, funnel-migration.
- `plugins/systems-map`: expert-partners-systems-map (kept separate from
  operating-doctrine so that plugin's 2.0.0 scope and version stay stable).

Both registered in `.claude-plugin/marketplace.json` at version 0.1.0.

## Provenance

- funnel-* SKILL.md: copied verbatim from `~/Claude/projects/Funnel Operations/skills/`
  (the current Jun 19 2026 working copies, newer than the versions then in the store).
- expert-partners-systems-map SKILL.md: copied verbatim from the local-agent-mode
  session copy (the only on-disk source).
- Content was not modified. All four frontmatters validate against the Agent Skills
  spec (name matches ^[a-z0-9-]{1,64}$, folder==name, description <=1024 chars).

## Consequences

- These skills now have a canonical, version-controlled, CI-validated home.
- Upload ZIPs for the claude.ai store are re-cut from a verified commit in this repo,
  not from ad-hoc local copies.
- They are single-file skills (SKILL.md only); no companion files exist.
