---
name: factory-operator
description: "Choose the lowest-cost reliable Factory configuration (session or Workstream, machine, model, reasoning, autonomy, overage and BYOK posture) and pre-flight the account's usage windows before starting Droid work. Use when someone is about to start, resize or rescue Factory work, asks which Droid model or settings to use, hits a Factory rate limit or the 90% banner, or asks about Factory credits, Droid Core, Extra Usage or BYOK. Decides configuration only; never spends money or changes settings itself. Inherits operating-doctrine."
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

Operate Factory (Droid CLI, Factory App, Workstreams) efficiently and safely for Expert Partners and AG Luxury. This skill decides configuration. It does not spend money, change permissions or create infrastructure.

## Authorities you read live (never copy their contents into this skill)

1. Factory model catalog and multipliers: https://docs.factory.com/models.md. Quote the multiplier and default reasoning from today's page.
2. HQ Rulebook: the Model chart ("lowest pair that can do the job"), the silent-downgrade stop signal, and the Fable/Mythos content prohibition. Locate it through the `expert-partners-systems-map` skill.
3. Decision Log: the newest Factory entries. The newest entry wins where older Rulebook wording differs (for example, older "prefer Factory cloud Environments" wording).
4. Factory pricing FAQ for limits behaviour: https://docs.factory.com/pricing/individuals.md

If any of these cannot be read, say so and proceed with categories only, never with remembered numbers.

## Existing capabilities to reuse (do not duplicate)

- `session-model-advisor` for model and effort fit at conversation start.
- `capability-currency` (research-ops) for catalog drift sweeps.
- `tools/factory-access/auto_model.py`, the founder-approved PATH launcher installed as `~/.factory/bin/droid`. It rewrites every `droid exec` model and reasoning flag to `auto`. Never install a second launcher.
- `.github/workflows/factory-builder-reusable.yml` for CI builds.
- `tools/skill-deploy/deploy-skill.sh` and the marketplace plugin sync for deployment.

## Inputs to collect

- Work description and the work record (the GitHub issue for code work).
- Consequence class: `high` (customer-facing, money, permissions, production) or `routine`.
- Current `/limits` output (Standard 5-hour, weekly and monthly %, Droid Core %, Extra Usage state, reset times). If missing, ask for it or open Settings, Usage in the desktop app.
- Machines online (ember-mac-mini-m2, ag-mac-mini-m4) and whether authenticated browser, Drive or local-only data is needed.

## Workflow

1. **Verified state.** Summarise windows, pools, machines and the catalog date. Note any model that disappeared or changed multiplier since the last `capability-currency` sweep.
2. **Surface.** Automation for triggered repeats; Workstream for parallel multi-part work with PR output or a broad research mission; Mission only if Extra Usage is already authorised and on; otherwise Session.
3. **Machine.** ember-mac-mini-m2 for signed-in authenticated admin, browser, Drive and local data. ag-mac-mini-m4 via Remote Control for code, tests, builds and unauthenticated research. Cloud Environment only when both Macs must be offline, and say that managed compute will be consumed. Keep Workstream Defaults, Remote delegation off and the default cloud Environment cleared, unless the founder has recorded otherwise (see `reference/settings-map.md`).
4. **Model ladder.** Map to a Rulebook category, take its lowest tier, choose the lowest live multiplier in that tier, and use the model's default reasoning unless the Rulebook says higher. `high` consequence never drops below the category floor. Lower reasoning before lowering the model.
5. **Window check.** See `reference/decision-ladder.md`. In short: 5-hour at or above 90% and `high` means BYOK Claude on that machine if configured, else wait for reset; 5-hour at or above 90% and `routine` means Droid Core Flash-class or defer; weekly or monthly at or above 80% means flag to the founder, one agent max.
6. **Parallelism.** Default two agents. Three or more only when the 5-hour window is under 50% and work is `routine`.
7. **Auto vs pinned.** Auto only when `high`, window under 50% and the task is heterogeneous; add the stop condition "report if a 4x model becomes active". Otherwise pin. Nothing documents that Auto considers remaining allowance, so never claim it does.
8. **BYOK.** BYOK models are per machine and only visible to sessions on that machine. The BYOK Anthropic model IDs currently used are `claude-haiku-5-5`, `claude-sonnet-5-5` and `claude-opus-5-5`; confirm them against the key's model list before use. For headless BYOK runs call the vendor binary `~/.local/bin/droid` directly with `-m "custom:<display-name>"`, because the `~/.factory/bin/droid` launcher forces `-m auto`. See `reference/byok-setup.md`.
9. **Posture.** Overage preference: none for `high`; Droid Core allowed for `routine` batches. Never enable Extra Usage; state the balance needed and route to the founder. Fable/Astra need founder approval (and Fable needs the retention opt-in). Fable/Mythos are forbidden for cybersecurity, bio and chem content.
10. **Verify after.** Confirm via Workstream, Usage or `/cost` that models and credits match. A mismatch is a silent downgrade: stop and report.

## Output format (always this order)

1. Verified state
2. Recommendation (copy-pasteable CLI flags or exact app settings, multipliers quoted from the live page)
3. Why not cheaper
4. Stop conditions
5. Approvals required (none, or founder: Extra Usage, Fable/Astra, Console workspace, auto-reload, cloud Environment)
6. Verification test
7. Work record note (one paragraph for the GitHub issue that tracks the work)

## Guardrails

- Never write `~/.factory/settings.json`; print a fragment (see `scripts/render-settings-fragment.sh`) and say where to paste it. Keys only as `${ENV_VAR}` references.
- Never print keys, Google Doc IDs, 1Password item IDs or 1Password contents. Secrets live in 1Password only.
- Never enable Extra Usage, buy credits, turn on auto-reload, create Console workspaces, Environments or Droid Computers, or change org settings.
- Never run a test that burns credits only to prove a limit stop.
- Before proposing anything new, name the owner of the existing capability (`reference/settings-map.md` lists them).
- Finish the authorised work completely (configuration plus work record note); do not end with advice only.

## Reference files

- `reference/settings-map.md`: what is set where and who inherits it.
- `reference/decision-ladder.md`: the rules with worked examples.
- `reference/byok-setup.md`: Console workspace steps (founder) and per-machine fragment (operator).
- `reference/monitoring.md`: which usage surfaces exist on the current plan.
- `reference/verification-tests.md`: acceptance tests T1 to T10.
