# operating-doctrine plugin: capability record

This record describes the package. It does not restate doctrine: the sources of truth are [plugin.json](.claude-plugin/plugin.json), the `operating-doctrine` entry in [marketplace.json](../../.claude-plugin/marketplace.json), each `skills/<name>/SKILL.md`, and [CHANGELOG.md](CHANGELOG.md). When this file and a SKILL.md disagree, the SKILL.md wins. Doctrine content changes only through explicit doctrine version bumps authorized by Allison; this record is not one of them.

| Field | Value |
| --- | --- |
| Name | operating-doctrine (marketplace `expert-partners`) |
| Problem solved | Replaces default LLM habits (menus, hedging, manual workarounds) with one operating standard, and carries the routing, hand-off, naming, and delivery rules every session follows. |
| Audience | Every agent working for Allison Gaddy (Claude app, Cowork, Claude Code, Codex) and the humans reading their output. |
| Owner | Allison Gaddy. |
| Canonical source | This folder in `ExpertPartners/expert-partners-skills`. The root `operating-doctrine/SKILL.md` is a legacy pointer, not a second body. |
| Current version | See `version` in plugin.json (2.49.0 at this record's last update); history in CHANGELOG.md. |
| Forms | Claude plugin (this package). Standalone claude.ai uploads of several member skills also exist (see Deployment). |
| Lifecycle | Live. Loads at every session start. |

## Skills

| Skill | Invoke when |
| --- | --- |
| [operating-doctrine](skills/operating-doctrine/SKILL.md) | Every session and every decision point. |
| [code-block-routing](skills/code-block-routing/SKILL.md) | Any Claude Code paste block or implementation brief. |
| [connection-first-implementation](skills/connection-first-implementation/SKILL.md) | Configuring or changing an external service a connector or CLI could reach. |
| [cowork-direct-execution](skills/cowork-direct-execution/SKILL.md) | Surfaces that hold direct execution access. |
| [deliverable-link](skills/deliverable-link/SKILL.md) | Any created or updated deliverable. |
| [document-formatting-standard](skills/document-formatting-standard/SKILL.md) | Any document created for Allison. |
| [kindergartner-mode](skills/kindergartner-mode/SKILL.md) | When Allison asks for plain-talk mode. |
| [lane-spawn](skills/lane-spawn/SKILL.md) | A side task surfaces mid-lane. |
| [pin](skills/pin/SKILL.md) | Carry-back between Claude projects and Claude Code. |
| [session-model-advisor](skills/session-model-advisor/SKILL.md) | First message of a new conversation or a model/effort question. |
| [session-steward](skills/session-steward/SKILL.md) | Session naming and continuity care. |

Do not invoke for brand voice (brand-voice plugin) or system location questions (systems-map plugin). Related standalone skill: [batch-first-execution](../../skills/batch-first-execution/SKILL.md) composes with session-model-advisor and code-block-routing.

## Dependencies

- Knowledge: aura decisions cited inside each SKILL.md; the systems-map plugin for surface facts.
- Tools: none required by the package itself. Member skills describe connectors they may use.

## Deployment and health

- Distributed through the expert-partners marketplace to claude.ai org plugin sync, Claude Code, Cowork, and Codex.
- Last recorded surface check: aura skill-lifecycle reconciliation of 2026-09-24 (point in time, not re-verified). It recorded the org sync and Claude Code cache current at 2.49.0, plus duplicates: standalone claude.ai uploads (stale for code-block-routing, connection-first-implementation, lane-spawn, session-model-advisor, session-steward), a stale Codex synced mirror, and stale `claude-cowork` import snapshots in Codex.
- Validation: `python3 tools/plugin-validate/validate_plugins.py`. No behavioral fixtures exist yet.

## Overlaps and candidates

- RETIREMENT CANDIDATES (need Allison's per-item approval in the platform UI): the stale standalone claude.ai uploads of member skills listed above; the Codex synced mirror and `claude-cowork` import snapshots.
- batch-first-execution: canonical v1.1 lives in `skills/`; a v1.0 copy is recorded on the claude.ai skill shelf, Cowork, and NORTH. Replacing it needs a UI upload.
- Recorded for a future doctrine bump (not changed here): document-formatting-standard still carries an example tied to the benched Moxie brand (aura ADR 0045).
