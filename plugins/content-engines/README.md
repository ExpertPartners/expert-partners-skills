# content-engines plugin: capability record

This record describes the package. It does not restate skill instructions: the sources of truth are [plugin.json](.claude-plugin/plugin.json), the `content-engines` entry in [marketplace.json](../../.claude-plugin/marketplace.json), each `skills/<name>/SKILL.md`, and [references/titans-core.md](references/titans-core.md). When this file and a SKILL.md disagree, the SKILL.md wins.

| Field | Value |
| --- | --- |
| Name | content-engines (marketplace `expert-partners`) |
| Problem solved | Turns Allison Gaddy's marketing frameworks (RARE, XAVIER, the Titans family, Master Marketer) into repeatable engines for content, offers, and conversation-to-sale work. |
| Audience | Allison and the teams and clients she coaches (agents, coaches, founders); agents drafting marketing work for her. |
| Owner | Allison Gaddy. |
| Canonical source | This folder in `ExpertPartners/expert-partners-skills`. |
| Current version | See `version` in plugin.json (0.4.0 at this record's last update). |
| Forms | Claude plugin (this package); standalone claude.ai uploads of two member skills; related Allison custom GPTs (see GPT lineage). |
| Lifecycle | Live. |
| Brand scope | Brand-neutral engines. Voice and brand tokens defer to the brand-voice plugin. |

## Skills

| Skill | Invoke when | Do not invoke for |
| --- | --- | --- |
| [master-marketer-free-agent-builder](skills/master-marketer-free-agent-builder/SKILL.md) | Brand, funnel, content-system, and high-ticket offer strategy in Allison's voice. | Building funnels in GHL (funnel-operations). |
| [rare-content-engine](skills/rare-content-engine/SKILL.md) | Social posts, hooks, scripts, and reels using RARE (Reveal, Activate, Refine, Engage). | Long-form brand canon. |
| [xavier-offer-builder](skills/xavier-offer-builder/SKILL.md) | Constructing or auditing an offer. | Profile or DM audits (dm-to-dollars). |
| [dm-to-dollars](skills/dm-to-dollars/SKILL.md) | Profile audits, lead-flow math, conversation-to-offer bridging. | Offer construction (xavier-offer-builder). |

## Dependencies

- Knowledge: `references/titans-core.md` (shared Titans core); the brand-voice plugin for voice.
- Tools: none required. No actions or connectors.

## GPT lineage (recorded 2026-09-25 from the Drive "Custom GPT Databaase" profiles; the GPT instruction text itself was not visible)

| Custom GPT | Relationship | Decision |
| --- | --- | --- |
| RARE Content Creator | Same RARE framework as rare-content-engine. | Migrate into rare-content-engine (no new plugin). Blocked: the GPT's instructions and its knowledge files are only reachable in the ChatGPT builder. |
| RARE YouTube Content Builder | RARE applied to YouTube in Allison's voice. | Candidate to fold into rare-content-engine plus ag-personal-brand. Needs the GPT instructions. |
| Content Bucket Builder | Content-bucket ideation. | Overlaps rare-content-engine and master-marketer; decide after reading the GPT. |
| Dramatic Demonstrations, Launch Formula Coach, Fan Funnel Builder | Marketing strategy coaches closest to master-marketer. | Stay separate for now; no duplicate plugin. |

Recorded link defects in the Drive profiles (not edited): the Fan Funnel Builder profile carries the RARE Content Creator URL, and the RARE YouTube Content Builder profile carries the Content Bucket Builder URL.

## Deployment and health

- Distributed through the expert-partners marketplace to claude.ai org plugin sync, Cowork, and Codex.
- Last recorded surface check: aura skill-lifecycle reconciliation of 2026-09-24 (point in time, not re-verified). Org sync current; stale standalone claude.ai uploads of master-marketer-free-agent-builder and rare-content-engine; stale Codex synced mirror and `claude-cowork` import copies.
- `plugin.json` has no `author` field. Not added here because open draft PR #6 (video-transcript-relay, from 2026-07-31) edits the same file; that PR is based on 0.2.0, would set 0.3.0 against a 0.4.0 main, and does not touch marketplace.json, so it needs a rebase or a decision before either change lands.
- Validation: `python3 tools/plugin-validate/validate_plugins.py`. No behavioral fixtures exist yet.

## Overlaps and candidates

- content-coach, post-grader, post-scheduler (claude.ai uploads with no canonical source) overlap this plugin and the staged `social-*` skills in aura (`project-knowledge/operations/blotato-social-automation/skills-staging/`). One identity needs Allison's ruling before any import.
- RETIREMENT CANDIDATES (need Allison's per-item approval): the stale standalone claude.ai uploads of master-marketer-free-agent-builder and rare-content-engine.
