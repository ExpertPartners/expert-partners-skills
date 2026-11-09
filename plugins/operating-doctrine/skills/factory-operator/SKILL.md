---
name: factory-operator
description: "Choose the lowest-cost reliable Factory configuration (session or Workstream, machine, model, reasoning, autonomy, overage and BYOK posture) and pre-flight the account's usage windows before starting Droid work. Use when someone is about to start, resize or rescue Factory work, asks which Droid model or settings to use, hits a Factory rate limit or the 90% banner, or asks about Factory credits, Droid Core, Extra Usage or BYOK. Picks the settings and applies them. Inherits operating-doctrine."
user-invocable: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - WebFetch
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-11-07 (Decision Log 2026-11-07, Factory Recovery and
# Optimization, issue #296). Canonical home is this file. It ships only through
# the expert-partners marketplace plugin.
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "lowest-cost reliable Factory settings, checked against live limits"
---

# Factory Operator

Operate Factory (Droid CLI, Factory App, Workstreams) efficiently for Expert Partners and AG Luxury. Choose the configuration, apply it, and get the work done.

## Read live
1. Factory model catalog and multipliers: https://docs.factory.com/models.md.
2. HQ Rulebook Model chart ("lowest pair that can do the job"), found through the `expert-partners-systems-map` skill.
3. Decision Log, newest Factory entries. The newest entry wins.
4. Factory pricing FAQ for limits behavior: https://docs.factory.com/pricing/individuals.md

If one can't be read, work from categories, not remembered numbers.

## Reuse what exists
- `session-model-advisor` for model and effort at conversation start.
- `capability-currency` (research-ops) for catalog drift.
- `tools/factory-access/auto_model.py`, installed as `~/.factory/bin/droid`. It rewrites every `droid exec` model and reasoning flag to `auto`. Don't install a second launcher.
- `.github/workflows/factory-builder-reusable.yml` for CI builds.
- `tools/skill-deploy/deploy-skill.sh` and the marketplace plugin sync for deployment.

## Workflow
1. **State.** Read actual windows (5-hour, 7-day, 30-day), pools, reset times and machines. Unknown usage is unknown.
2. **Surface.** Automation for triggered repeats, Workstream for parallel multi-part work, Session otherwise. A GitHub issue or Hub record is optional.
3. **Machine.** Ember's M2 owns browser, clicking and visible desktop work. Headless APIs, Git, builds, tests and Factory execution run on either Mac, chosen by CPU, RAM, swap, disk and availability. M4 work stays invisible and never controls browser, screen, mouse or focus.
4. **Model.** Auto Model and available Factory allowance are the default for this mission and its agents. Use the lowest effective reasoning and minimal agents. Pin a model only for a specific task reason.
5. **Parallelism.** One session for a small task. Add agents for sizeable independent scopes.
6. **BYOK.** BYOK is optional, never a prerequisite or blocker. Use an existing per-machine configuration when a task needs it. See `reference/byok-setup.md`.
7. **Overage.** Droid Core fits routine batches. Use Extra Usage when the work needs it. Fable and Mythos stay out of cybersecurity, bio and chem content.
8. **Check.** After the run, confirm through Workstream, Usage or `/cost` that models and credits match. A mismatch is a silent downgrade, so fix the configuration and rerun.

## Output
Verified state, the settings applied (CLI flags or app settings with multipliers from the live page), why not cheaper, and a short work record note in the existing assignment with result and usage evidence.

## Guardrails
- Settings change through `~/.factory/settings.json` fragments (see `scripts/render-settings-fragment.sh`). Keys appear only as `${ENV_VAR}` references.
- Never print keys, Google Doc IDs or 1Password contents. Secrets live in 1Password only.
- Name the owner of an existing capability before building a new one (`reference/settings-map.md`).
- Finish the work. Don't end with advice only.

## Reference files
- `reference/settings-map.md`: what is set where.
- `reference/decision-ladder.md`: the rules with examples.
- `reference/byok-setup.md`: optional BYOK setup.
- `reference/monitoring.md`: usage surfaces.
- `reference/verification-tests.md`: tests T1 to T10.
