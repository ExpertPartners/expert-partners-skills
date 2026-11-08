# Settings scope and evidence

Checked against current Factory docs on 2026-11-08. Documented is not live-tested. Inspect the actual available tool schema, account policy and runtime before applying a separately authorized change.

| Control | Supported surface | Scope and evidence boundary |
|---|---|---|
| Session model, reasoning, autonomy, interaction mode | App selector, CLI `/settings`, Sessions API `PATCH /api/v0/sessions/{sessionId}` with `sessionSettings` | Existing session only. Effective in-flight timing not tested. A response omitting settings cannot verify them |
| Machine | Existing computer's `computerId` in session creation | Creation-time choice. No documented session machine migration PATCH |
| Session/spec defaults | User/project settings, App Session Defaults, supported runtime overlay | Future or inheriting sessions, not proof existing sessions changed |
| Workstream orchestrator and agent model/reasoning | Workstream gear / Change models | Workstream scope. Agent “Default” uses target machine defaults. Existing/new-agent propagation unverified |
| Task models/reasoning | `subagentModelSettings` light/medium/heavy model and effort, custom droids, Task complexity | Spawn-time tier routing, not Workstream agent settings. Current Task schema has no machine or arbitrary model argument |
| Task autonomy | `subagentAutonomyLevel` and org ceiling | Separate from session autonomy and Mission workers |
| Mission models/reasoning | Orchestrator/worker/validator fields, defaults and CLI flags | Separate Mission scope and spending policy |
| Workstream routing defaults | App Workstream Defaults, remote delegation, default environment, additional machines | Defaults for Workstreams started later. No verified callable public mutation here |
| BYOK custom models | Per-machine custom-model settings and runtime credentials | Optional route. Matching entry/key must exist on actual target. Not a prerequisite for approved Auto work |
| Overage, Extra Usage, rolling windows | `/limits`, Settings Usage | Account scope. Never silently enable or purchase |
| Org model/autonomy controls | Enterprise Controls or supported org API where available | Hard policy overrides lower preferences. Do not infer absence solely from plan name |
| Alerts | Personal monthly-cap alerts, org thresholds where entitled | Informational, not a preflight throttle or a spending limit |
| Skills and context hooks | Existing operating-doctrine plugin and marketplace producer | Context guidance, not model changes or hard worker caps |

## Public Sessions API

[Sessions API](https://docs.factory.com/api-reference/sessions.md) documents creation and session settings updates for selected organizations. Model, reasoningEffort and autonomyLevel are supported session fields, subject to authorization and policy.

Do not send machine/routing/count/budget fields to session PATCH. In particular `computerId`, `environmentId`, `remoteDelegation`, `defaultEnvironment`, `additionalMachines`, `agentModel`, `maxAgents`, `maxParallelism`, `tokenBudget`, `creditBudget`, `computeBudget`, `speed` and `sessionDefaultSettings` are not documented fields for that operation. Do not send guessed null resets.

The bounded account test on 2026-11-08 created an idle explicit-M2 session with no messages. HTTP 201 and GET confirmed its computer, and GET reported zero session credits, but omitted `sessionSettings`. Thus effective model/reasoning/autonomy were not proven. No live model/reasoning PATCH was tested. The own-test archive metadata PATCH was acknowledged but persistent archive state was not read back. Do not repeat tests merely to fill an absent field.

## Current authority and target policy

Read live HQ authority. Preserve Auto with available Factory allowance. M2 owns authenticated browser and visible work. Headless local selection is resource-aware, not a fixed M2/M4 order, and protects M4 memory and foreground responsiveness without touching its visible desktop. Cloud requires both local options confirmed unavailable and approval. A narrower no-cloud assignment still forbids cloud. BYOK exhaustion is not a reason to block available approved Factory use.

Remote delegation off pins Workstream agents to the orchestrator's machine. Leaving it available with explicit authorized Mac targets allows cross-machine routing. Desired no-cloud defaults and descriptions are guidance until actual controls are saved and read back. A computer inventory alone proves neither saved routing defaults nor M4 execution.

If native settings staging is present in the main desktop chat, use only its actual matching operations. StageSettingsChanges is not available to workers, and was unavailable in the inspected orchestrator catalog. Stage is not apply, and protected-target navigation never submits a form. If unavailable, name the exact target, desired fields, blocker, owner and expected readback in the existing work record. Do not bypass installed browser policy.

## Existing launcher and distribution

`tools/factory-access/auto_model.py` owns the PATH launcher. It forces Auto for `droid exec`; do not change it or add another launcher for preflight. A separately authorized pinned test can invoke the vendor binary directly without rewriting the user's selection or defaults.

Existing owners include `session-model-advisor`, `capability-currency`, `tools/factory-access/`, the operating-doctrine hooks and marketplace/plugin sync. Source references are [settings](https://docs.factory.com/droid-cli/settings.md), [Workstream settings](https://docs.factory.com/workstreams/settings.md), [machines](https://docs.factory.com/workstreams/machines.md), [subagents](https://docs.factory.com/harness/subagents.md) and [enterprise controls](https://docs.factory.com/enterprise/hierarchical-settings-and-org-control.md).
