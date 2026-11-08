# Verification tests (run in the Expert Partners Factory account)

- T1 Install the Expert Partners marketplace in Droid (`droid plugin marketplace add …`, `droid plugin install operating-doctrine@…`); `/skills` lists `factory-operator` as Effective on ember-mac-mini-m2 and ag-mac-mini-m4.
- T2 Workstream Defaults set as decided (see `settings-map.md`); two-agent Workstream from ag-mac-mini-m4; no new managed-computer time; agents on ag-mac-mini-m4.
- T3 Orchestrator Sonnet-class medium, agents Haiku-class; Workstream Usage lists exactly those models.
- T4 Same small task pinned vs Auto; compare credits; record whether Auto used a 4x model.
- T5 Overage preference readback: read `/limits` and Settings, Usage and record the overage preference and Extra Usage state. Never drive a session to a limit to prove the stop.
- T6 BYOK Claude on each machine with a `${ENV_VAR}` key reference; one short `~/.local/bin/droid exec` run; usage appears in the Console workspace, debited from included credits first.
- T7 BYOK model selected for agents on a cloud Environment; expect failure or fallback (keys are per machine). Record from docs or an existing run; do not start a cloud computer for it.
- T8 `/limits` readback; record every window, its percentage and reset time.
- T9 Multipliers quoted by the skill match https://docs.factory.com/models.md that day.
- T10 Record plan name and managed-compute allowance from Settings, Usage on the work record.

Acceptance: T1, T2, T3, T5, T6, T8, T9 pass; T4, T7, T10 recorded; CI and gitleaks pass; no multiplier, Doc ID or key in skill files; founder approves.
