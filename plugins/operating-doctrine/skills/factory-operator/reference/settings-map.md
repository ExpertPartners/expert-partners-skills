# Settings map (verified against docs.factory.com, Nov 7 2026; re-verify on change)

Precedence: hard controls resolve top-down (Org authoritative); session defaults resolve bottom-up (Runtime > Folder > Project > User > Org > Dynamic > BuiltIn). Source: https://docs.factory.com/enterprise/hierarchical-settings-and-org-control.md

| Setting | Scope | Set in | Inherited by | Owner at Expert Partners |
|---|---|---|---|---|
| model, reasoningEffort, interactionMode, autonomyLevel, specMode* | Session default per machine | `~/.factory/settings.json`, project `.factory/settings.json`, App, Session Defaults, `/settings`, `--settings` overlay | New sessions on that machine, and Workstream agents whose agent model is "Default" | Operator (per machine) |
| subagentModelSettings (light/medium/heavy), subagentAutonomyLevel | Per machine | same; `/settings`, Subagents | Task-tool subagents | Operator |
| Mission orchestrator/worker/validator model + reasoning | Per machine | same; `droid exec --mission --worker-model …` | Missions | Operator; Extra Usage decision is founder |
| compactionTokenLimit(PerModel), compaction model | Per machine | same | All sessions on machine | Operator |
| customModels (BYOK) | Per machine, local only; not visible on hosted web/mobile; cloud Environment agents cannot see it | `~/.factory/settings.json` or desktop Settings, Custom Models | Sessions and Workstream agents on that machine | Operator (keys: founder via 1Password) |
| Workstream: orchestrator model+reasoning, agent model ("Default" or specific) + reasoning | Per Workstream | Gear icon | That Workstream | Operator |
| Workstream Defaults: remote delegation (default ON), compaction budget, default environment, additional machines | Per user | App, Settings, Workstream Defaults | Every new Workstream | Founder decides; operator sets |
| Overage preference, Extra Usage | Per account | `/limits` or Settings, Usage | All sessions and Workstreams | Founder (spend) |
| Org hard controls (modelPolicy, maxAutonomyLevel, usage limits) | Org | Enterprise Controls / Organization API | Everyone | Not available on current plan |
| Skills, AGENTS.md, MCP, hooks, plugins | Repo / user / plugin | files, `/skills`, `droid plugin` | Sessions and agents on that machine | Skills repo maintainers |

## Remote delegation trade-off

With remote delegation off, every Workstream agent runs on the orchestrator's machine (https://docs.factory.com/workstreams/machines.md), so one Workstream cannot place some agents on ember-mac-mini-m2 and others on ag-mac-mini-m4. The cost goal (no fresh managed cloud computers) is also met by leaving remote delegation on, clearing the default cloud Environment, and listing only the two Remote Control machines as additional machines. Which of the two applies is a founder decision; follow the newest Decision Log entry.

## Headless model launcher

`~/.factory/bin/droid` is the PATH launcher from `tools/factory-access/auto_model.py`. For `droid exec` it replaces `-m`, `-r`, `--spec-model`, `--worker-model` and `--validator-model` values with `auto` (reasoning `none`). Interactive sessions and non-exec commands pass through. A headless run that must use a pinned or BYOK model calls `~/.local/bin/droid` directly. Change the launcher only through `tools/factory-access` and a reviewed pull request.

Existing Expert Partners capabilities (do not duplicate): `session-model-advisor`, `ai-capability-routing`, `capability-currency`, `research-before-guessing`, `expert-partners-systems-map`; `tools/factory-access/` (preflight, auto_model launcher); `.github/workflows/factory-builder-reusable.yml`; `tools/overlap-check`, `tools/auto-merge-gate`, `tools/stall-sweeper`. The Factory Workstreams operating architecture initiative owns changes to Workstream Defaults and CI.
