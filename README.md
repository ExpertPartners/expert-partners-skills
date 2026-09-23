# Expert Partners AI Operating System Skills

This repository is the Estate's home for canonical skills and the tools that
package, deploy and index them. Skills supply reusable operating instructions
to the Estate's AI surfaces. The
[Estate Manifest](https://github.com/ExpertPartners/aura/blob/main/docs/estate/estate-manifest.md#entity-index)
records the owner as **Estate**, the job as **Canonical skills and deployment
tooling**, and the routing context as **NORTH governance**.

## Find the right source

| Start here | What it provides |
| --- | --- |
| [Plugin marketplace](.claude-plugin/marketplace.json) | Plugin descriptions and paths to their source packages. |
| [Skill graph](tools/skill-map/skills-graph.json) | Individual skills, descriptions, relationships and canonical source paths across this repo (`eps:`) and Aura (`aura:`). |
| [Standalone skills](skills/) | Canonical skills distributed independently of a plugin. |
| [Plugin sources](plugins/) | Plugin-carried skills, manifests and supporting assets. |
| [Operating Doctrine](plugins/operating-doctrine/skills/operating-doctrine/SKILL.md) | The canonical operating instructions inherited by the skills. |
| [Repo Standards](skills/repo-standards/SKILL.md) | The existing repository baseline and audit workflow, linked to its governing Aura decisions. |
| [Agent instructions](AGENTS.md) | The lean AI entry point; [CLAUDE.md](CLAUDE.md) imports it. |

These are navigation links, not a second skill catalog. Follow a skill's source
path to read its current instructions. Aura-native skills remain canonical in
Aura. Brand and business facts remain in their owning repositories; use the
Manifest and the applicable skill to reach them.

## Sources, generated copies and history

Edit a skill in its declared canonical home. The existing
[deployment tool](tools/skill-deploy/deploy-skill.sh) produces deployed copies,
checksum manifests and upload ZIPs. Installed copies and caches consume those
sources; they are not independent places to correct a skill.

The [skill-map tools](tools/skill-map/) generate the graph from canonical skill
sources. Correct those sources rather than hand-editing the generated index.
The root [operating-doctrine/](operating-doctrine/SKILL.md) file is a legacy
pointer to the canonical plugin skill, not a competing instruction body.

[Decisions](decisions/), [doctrine](doctrine/) and [reference material](reference/)
provide supporting records. The [intake inbox](intake/README.md) captures session
evidence; [archive/](archive/) preserves history. A capture, proposal or old
record is not automatically current guidance. Trace the owning decision and
any supersession before treating it as authority.

## Make a correction

Use the source path in the graph or marketplace to locate the owner. Follow
[AGENTS.md](AGENTS.md), the applicable skill's update instructions and the
existing [repository checks](.github/workflows/ci.yml). Keep the correction
within its authorized scope and use the existing producer for any authorized
delivery to other surfaces. Changes to another repository's canon belong with
that owner, not in a duplicate skill here.
