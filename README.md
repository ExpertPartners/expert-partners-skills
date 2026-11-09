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
| [Video Discovery](plugins/research-ops/skills/video-discovery/SKILL.md) | Bounded public video discovery, ownership review and partial playback checks in research-ops. |
| [Agent instructions](AGENTS.md) | The lean AI entry point. CLAUDE.md imports it. |

Edit a skill in its declared canonical home. The [deployment tool](tools/skill-deploy/deploy-skill.sh) produces deployed copies, checksum manifests and upload ZIPs. The [skill-map tools](tools/skill-map/) generate the graph from canonical skill sources. Correct the sources, never the generated output. The root [operating-doctrine/](operating-doctrine/SKILL.md) file is a pointer to the canonical plugin skill.

To make a correction, find the skill's source path in the graph or marketplace, follow AGENTS.md and the checks in [ci.yml](.github/workflows/ci.yml), and open a pull request.

## Repository checks

Use Python 3.12 for the repository's Python tooling. Install the hash-locked tools once:

```bash
python3 -m pip install --require-hashes -r requirements-tooling.txt
```

Format Python files with `python3 -m ruff format <path>` and verify them without writing with
`python3 -m ruff format --check <path>`. CI checks changed Python files, and the pre-commit hook
formats staged Python files.

Run the focused native test suites and repository checks from the root:

```bash
python3 -m unittest discover -s tools/auto-merge-gate/tests -v
python3 -m unittest discover -s tools/dependency-policy/tests -v
python3 -m unittest discover -s tools/readiness/tests -p 'test_agents_links.py' -v
python3 tools/readiness/check_agents_links.py
python3 tools/dependency-policy/check_versions.py
```

For CI and generated-output recovery steps, see the [repository operations runbook](runbooks/repository-operations.md).
