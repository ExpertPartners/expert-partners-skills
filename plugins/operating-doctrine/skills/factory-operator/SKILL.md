---
name: factory-operator
description: "Preflight new actionable Factory assignments, including read-only reviews, and material changes for complexity, reasoning, duration, resources, model, authorized machine and justified worker count. Use before task execution or when scope, limits or routing changes. Preserve explicit model choices including Auto, use local-first execution, and distinguish recommendations from available controls and verified runtime. Small tasks get a one-line preflight, trivial continuations need none. Never changes settings or spends money merely by loading. Inherits operating-doctrine."
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

Before a new actionable Factory assignment or material change, make the smallest reliable task and resource preflight, including read-only review and explanation. This skill recommends a configuration and explains supported control paths. Loading it or receiving hook context does not change settings, enforce spending, throttle agents or reveal hidden Auto routing.

## Authority and existing owners

Read the live HQ Rulebook and newest applicable Decision Log entries. Locate them through the connected Drive tools or `expert-partners-systems-map`, never copy business documents or IDs into this repository. Newer authority wins over historical research and issue wording. Preserve Auto and available Factory allowance, with BYOK optional. Use the current resource-aware local routing rule, not a fixed headless M2/M4 priority. Cloud requires both Macs confirmed unavailable plus applicable approval. A workstream's no-cloud restriction still forbids provisioning.

Check the current [model catalog](https://docs.factory.com/models.md) before quoting IDs, reasoning support or multipliers, and [individual pricing](https://docs.factory.com/pricing/individuals.md) before describing windows or overage. If a required authority read fails, stop only the work dependent on it and name the gap. If catalog or usage data is unavailable, give a conditional recommendation with unknowns, not invented prices or headroom. Missing BYOK verification or exhausted BYOK never blocks an available approved Factory route.

Reuse `session-model-advisor` for task fit, `capability-currency` for catalog drift, `tools/factory-access/` for the existing PATH launcher, and the marketplace/plugin producers for delivery. Do not build another launcher, dashboard, tracker, scheduler or billing service. Do not modify the launcher or user defaults to activate this skill.

## Lightweight activation

The operating-doctrine plugin adds a short `SessionStart` routing instruction and a `UserPromptSubmit` reminder. The hook does no inference or task evaluation. On a new actionable assignment, invoke `Skill(factory-operator)` if not loaded for that task. Await its result before any task operations, never in parallel with reads or other task tools. Reuse a still-current preflight for unchanged continuations. Do not recursively invoke this skill, reload it on every tool call, or perform a fresh account investigation on every message.

Greetings, acknowledgements and status-only continuations need no preflight. A new read, review or explain assignment still qualifies. For a small task, give one line with routine complexity/effort, brief duration/resource estimate, current machine and zero additional workers. Do not turn it into a large evaluation or fresh account investigation. A short new task such as “fix tests” also qualifies. Re-evaluate when scope, risk, selected route, available resources or parallelism changes materially. No exactly-once guarantee is claimed.

## Task preflight

Use this order before task execution, compressed to one line for small assignments. Keep it to one compact paragraph or small table, not a second planning project.

1. **Verified state**. Name the task and existing work record, current explicit selection (including Auto), current machine evidence, tools/data needed and relevant limits evidence with its time. Separate requested settings, saved settings and observed runtime. Do not infer a physical machine solely from a null `computerId`.
2. **Complexity and reasoning**. Classify the task as routine, bounded build or complex/high-consequence, with one reason. State the minimum reasoning needed for correctness, not maximum effort by habit. Preserve the user's model choice. Lower effort only when that model supports it and quality holds.
3. **Duration and resources**. Estimate a range for elapsed time and tool/model turns, context overhead, output, build CPU/RAM/disk, external calls and possible compute. Label estimates as estimates. Use observed comparable usage when available. Auto's unknown backend means a conditional range, not a fabricated exact credit or dollar quote.
4. **Execution recommendation**. Name the cheapest capable category/model and reasoning from live evidence, why a cheaper route would risk the result, the authorized machine and surface, and autonomy no broader than the task needs. Preserve Auto when selected. A named-model alternative is a recommendation, not an override or a claim about Auto's hidden backend. Without a live catalog, name a category and the verification needed rather than an unverified ID.
5. **Parallelism**. Default to sequential execution, zero additional workers for inline work, or one active worker when delegation is needed. This is a starting recommendation, not a product count cap. Add workers only for independent sizeable tasks after accounting for headroom, machine capacity, coordination overhead and write collisions. Name the type and count explicitly, including the already-running orchestrator separately.
6. **Controls and next check**. State what can be changed through the currently available supported interface, what is only recommended, what needs approval and what remains unknown. Verify any authorized change independently. Record the estimate and actual outcome in the existing work record, without creating a new tracker.

### Three different worker mechanisms

- Workstream agents are separate long-lived sessions coordinated by an orchestrator. Their machine and model choices depend on workstream settings and the target's configuration.
- Task subagents use the installed tool's `light`, `medium` and `heavy` complexity tiers and model/autonomy inheritance. A complexity tier is not a worker count or a reasoning enum, and does not set Workstream agents.
- Mission workers and validators use Mission-specific settings, execution and billing policy. Never start a Mission or enable Extra Usage merely because a task is complex.

Use the actual tool schemas and current documentation. No fixed maximum agent count, automatic throttling, budget-aware Auto routing, or automatic cross-surface synchronization is established by this skill.

## Routing and limits

Choose a Session for inline bounded work, the existing Workstream for coordinated independent work, and existing Automations for approved recurring triggers. Missions require their own approved plan and current spending policy. Do not create a new workstream for a small question.

Use `ember-mac-mini-m2` for authenticated browser and visible desktop work. For authorized headless work, choose a reachable local Mac using measured CPU, available RAM, swap, thermal and disk/I/O load, data/tool access and active founder work. Protect M4 memory headroom and foreground responsiveness. Never control its screen, browser, mouse, keyboard focus or windows. An inventory entry proves neither execution nor current resource headroom. Cloud is not an automatic fallback. Keep delegation available for explicit authorized Mac routing and avoid default cloud targets, but distinguish the desired policy from actual saved defaults.

Read available `/limits`, `/cost`, `/stats`, Workstream Usage and Settings Usage. Account for all Standard windows, Droid Core, resets, Extra Usage posture and managed compute without treating a warning threshold as measured remaining budget. When unknown, say so and recommend a bounded sequential step with a check before expansion. Do not suspend approved work merely for missing optional BYOK evidence.

At an actual allowance block, report the affected pool and reset evidence, preserve progress, and use only an already-authorized available route. Never enable Extra Usage, buy credits, change plan, create paid compute or silently degrade quality. Do not invent a numeric concurrency cap from a percentage. Re-estimate after meaningful scope/resource changes rather than claiming background monitoring or automatic throttling.

## Supported changes versus recommendations

Read [settings-map.md](reference/settings-map.md) before changing anything. A separately authorized implementation can use supported session controls, but this skill and its hooks are instruction/context only.

- Existing session model, reasoning, interaction mode and autonomy have documented Sessions API controls, subject to actual access and response fields. Machine is a creation-time `computerId`, not a documented machine migration PATCH.
- User/project defaults affect future or inheriting sessions. They are not proof an existing Workstream changed. Workstream agent models, Task tiers and Mission fields are separate scopes.
- StageSettingsChanges may stage supported operations in the main desktop chat only when present in its live schema. Staged is not applied. Do not invent a control or a page.
- When control is unavailable, state exact desired fields and supported surface, the blocker and verification needed. Do not write guessed JSON, use private endpoints, grant permissions or ask the user to do work an authorized tool can do.

## Verification and output

Report these fields, sized to the task.

1. Verified state and evidence timestamp
2. Complexity, required reasoning, duration and resource estimate
3. Recommendation, selected route preserved, machine, surface, worker type/count and why not cheaper
4. Automatic behavior versus available authorized changes versus recommendation-only versus unknown
5. Stop conditions, approvals and next measurement
6. Existing work record update and observed result

Verify selected model/reasoning/autonomy from available runtime evidence. A request, HTTP 201, saved fragment or absent response field is not proof a runtime applied it. With Auto selected, label the selected route Auto and the backend unknown unless a supported observation actually exposes it. Do not treat an unobservable Auto backend as a silent downgrade.

Report tokens and Factory-reported counters separately from dollars and invoices. Session `factoryCredits` includes subagents, so do not sum overlapping parent/child trees as daily spend. Optional BYOK usage needs provider billing evidence for any actual charge claim. No synthetic exhaustion tests, speculative cloud sessions or repeated paid discovery.

## Guardrails and references

Never print secrets, private document IDs or credential contents. Never change explicit model choice, global defaults, permissions, billing or infrastructure just by loading this skill. `scripts/render-settings-fragment.sh` prints optional examples, not applied settings, and must not overwrite existing configuration.

Follow the live authority's model quality floors, retention and approval requirements, and content prohibitions. A cheaper route never overrides them.

- [decision-ladder.md](reference/decision-ladder.md) has worked preflight examples.
- [settings-map.md](reference/settings-map.md) distinguishes control scope and evidence.
- [monitoring.md](reference/monitoring.md) reuses available monitoring and alerts.
- [verification-tests.md](reference/verification-tests.md) defines bounded before/after checks.
- [byok-setup.md](reference/byok-setup.md) describes optional BYOK, never a prerequisite.
