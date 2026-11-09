# Repository operations runbook

This repository owns skill sources, developer tooling and their validation or generation
workflows. It does not run a production application. Use this playbook for repository CI
failures and generated-surface drift, not for customer or production incidents.

## First response

1. Identify the failed workflow, check name and commit SHA. Read the corresponding workflow
   under [`.github/workflows/`](../.github/workflows/) to confirm its inputs and exact command.
2. Reproduce the narrow check from the repository root. Follow the commands in
   [Repository checks](../README.md), then run [`tools/validate-job.sh`](../tools/validate-job.sh)
   for changed-file validation.
3. Fix the canonical source or lock that caused the failure. Do not edit generated graph,
   feed or rendered files by hand.
4. Rerun the same check and relevant native `unittest` suite. Confirm the generated output
   with its producer's check mode before treating drift as repaired.

## Common failures

| Failure | Local evidence and recovery |
|---|---|
| Python requirements or workflow install | Run `python3 tools/dependency-policy/check_versions.py` and `python3 -m unittest discover -s tools/dependency-policy/tests -v`. For lock-install failures, follow [Dependency policy](../tools/dependency-policy/README.md) to resolve complete hash-locked requirements. |
| Skills graph or AI Workforce feed | Read [the skills-graph workflow](../.github/workflows/skills-graph.yml). It runs the graph extractor, producer tests and feed validation. Correct canonical skill or producer inputs, then use the same commands and generated-output check from that workflow. |
| Release-note validation | Run `python3 tools/release/release.py --check` to validate the current changesets without writing. See the [release procedure](../tools/release/README.md). |
| Generated rendered surfaces | Use the renderer's `--dry-run` and `--check` modes as documented in the [generated-surface README](../tools/generate/README.md). Verify the configured targets before any write mode. |
| Broken agent-instruction link | Run `python3 tools/readiness/check_agents_links.py` and `python3 -m unittest discover -s tools/readiness/tests -p 'test_agents_links.py' -v`. Fix the source link or restore its intended target. |

## Safe recovery

- Keep changes on the isolated branch and preserve other working changes.
- Use a workflow's documented read-only or check mode before any producer write.
- Keep changes to canonical sources and lock files; generated artifacts are updated only by
  their producers.
- Do not activate workflows, publish or deploy, change access, or write to production
  services as part of repository diagnosis.
