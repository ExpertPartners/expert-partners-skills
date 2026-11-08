# Decision ladder

Facts relied on (confirmed at https://docs.factory.com/pricing/individuals.md and https://docs.factory.com/workstreams/settings.md): the three Standard windows are independent and all need headroom; Standard is consumed before Droid Core; Droid Core is the same currency with separate limits; at a limit the current request finishes, then requests error; `/limits` toggles Droid Core or Extra Usage; Workstreams show a banner at 90% and agents stop at the limit until reset, Extra Usage, or a BYOK model; "Change models" works mid-run; Workstreams use more tokens than single sessions; Auto Model escalates and fails over but nothing documents allowance-awareness.

## Window rules

| Condition | `high` consequence | `routine` |
|---|---|---|
| 5-hour < 50% | Proceed; Auto allowed | Proceed pinned |
| 5-hour 50–89% | Proceed pinned, one Workstream at a time | Proceed pinned, max two agents |
| 5-hour ≥ 90% | Do not start on Standard. BYOK Claude on that machine if configured; else wait for the reset time | Droid Core Flash-class (lowest live multipliers, never Kimi K3) or defer |
| Weekly or monthly ≥ 80% | Flag founder; one agent; prefer BYOK for frontier work | Defer non-urgent |
| Droid Core pool at 100% | Do not propose Droid Core | Same |
| Managed compute near cap | No cloud Environments; Remote Control only | Same |

## Model ladder

1. Category from the Rulebook chart (read live).
2. Lowest tier for that category.
3. Lowest live multiplier within the tier (models page, read live).
4. Model default reasoning unless the Rulebook says higher. Lower reasoning before model.
5. `high` never below the category floor. Browser work never on the lowest tier.
6. Orchestrators plan and brief; they do not need the highest reasoning on every turn.
7. Never leave a model setting on a value that can silently fall back to a costlier model. A BYOK display name in `model` with no matching `customModels` entry on that machine falls back to the Factory pool.

## Worked examples

**A. Routine research Workstream, 5-hour 42%, Droid Core 100%.** Workstream on ag-mac-mini-m4; orchestrator Sonnet-class medium; two collection agents Sonnet-class high; one synthesis agent Opus-class high at the end; no cloud Environment; pinned; overage none; no approvals; verify via Workstream Usage.

**B. High-consequence bug fix + PR, 5-hour 96% resets 14:10.** Do not start on Standard. If ag-mac-mini-m4 has the BYOK Claude model, start a session on it at high reasoning. Else wait until 14:10. Never Droid Core for this. The work record note flags weekly usage.

**C. 90% banner mid-run.** Change models: drop agent reasoning one step. If blocked at the limit: switch agents to BYOK Claude if it is on that machine; otherwise pause until reset. Do not enable Extra Usage. Record it on the work record.

**D. Classification batch of 400 items.** Session or two-agent Workstream on ag-mac-mini-m4; Haiku-class or Luna-class (lowest Standard multipliers), or BYOK `claude-haiku-5-5`; if Standard is tight, Droid Core Flash-class; never Kimi K3.
