# Monitoring surfaces on the current (Individual/Teams) plan

| Surface | Shows | Source |
|---|---|---|
| `/limits` | Window percentages, reset times, Droid Core / Extra Usage toggles | https://docs.factory.com/droid-cli/cli-reference.md |
| `/cost`, `/stats [period]`, `/context` | Session usage, period stats, context | same |
| App Settings, Usage, Personal Usage page (Usage by Session card) | Visual usage per session | https://docs.factory.com/changelog/release-notes.md |
| Workstream, Usage | Credits, agent count, per-session breakdown by model/credits/share; 90% banner | https://docs.factory.com/workstreams/settings.md |
| Desktop assistant settings navigation | Opens Usage / Custom Models / Workstream Defaults; never submits | https://docs.factory.com/llms.txt |
| Factory Public API, read-only (`/api/v0/computers`, `/api/v0/environments`, `/api/v0/sessions`) | Registered and managed computers, default Environment, recent sessions and the computer each ran on | https://docs.factory.com/openapi.json |

Check before relying on: Analytics API and org usage alert thresholds and per-user caps are documented as Enterprise features. Source: https://docs.factory.com/api-reference/analytics.md

Pre-flight = read `/limits` (or Settings, Usage) and paste it. Post-run = read Workstream Usage or `/cost`. Catalog drift = `capability-currency` sweep. Managed-compute leak check = list computers and sessions through the Public API and look for managed or ephemeral computer IDs.
