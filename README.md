# Expert Partners AI Operating System Skills

This repository holds the skills marketplace and the tools that package, deploy and index skills. Business knowledge, rules, and decisions live in the business brains in Google Drive, starting with the HQ Rulebook and Decision Log in HQ Business Brain, Company Core. Read AGENTS.md before changing anything.

| Start here | What it provides |
| --- | --- |
| [Plugin marketplace](.claude-plugin/marketplace.json) | Plugin descriptions and paths to their source packages. |
| [Skill graph](tools/skill-map/skills-graph.json) | Individual skills, descriptions, relationships and canonical source paths. |
| [Standalone skills](skills/) | Canonical skills distributed independently of a plugin. |
| [Plugin sources](plugins/) | Plugin-carried skills, manifests and supporting assets. |
| [Operating Doctrine](plugins/operating-doctrine/skills/operating-doctrine/SKILL.md) | The canonical operating instructions inherited by the skills. |
| [Repo Standards](plugins/operating-doctrine/skills/repo-standards/SKILL.md) | The repository baseline and audit workflow. |
| [Agent instructions](AGENTS.md) | The lean AI entry point. CLAUDE.md imports it. |

Edit a skill in its declared canonical home. The [deployment tool](tools/skill-deploy/deploy-skill.sh) produces deployed copies, checksum manifests and upload ZIPs. The [skill-map tools](tools/skill-map/) generate the graph from canonical skill sources. Correct the sources, never the generated output. The root [operating-doctrine/](operating-doctrine/SKILL.md) file is a pointer to the canonical plugin skill.

To make a correction, find the skill's source path in the graph or marketplace, follow AGENTS.md and the checks in [ci.yml](.github/workflows/ci.yml), and open a pull request.
