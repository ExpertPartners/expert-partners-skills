# Monitoring and limits without a new service

| Existing surface | Evidence available | Boundary |
|---|---|---|
| CLI `/limits` | Standard windows, Core/Extra Usage posture, resets | No documented public rolling-percentage endpoint established |
| `/cost`, `/stats [period]`, `/context` | Session usage and context information | Read reported units, not inferred invoice dollars |
| Settings Usage | Plan, available account usage and controls | Inspect entitlement and actual state, never assume alert availability |
| Workstream Usage | Agent/session usage breakdown and native 90% warning | Warning is not a preflight throttle. Backend visibility may be restricted |
| v0 Sessions API | Session details and `factoryCredits` where returned | Lifetime counter includes Task subtree. Avoid overlapping parent/child sums |
| Analytics API | Extended tokens/cost attribution where enabled | Prior account requests returned Enterprise-only 403, not proof v0 counters are absent |
| Native monthly-cap emails and org alerts | Threshold notifications where entitled/configured | Informational, never automatic spending enforcement |
| Existing telemetry collector | Supported OTEL observations if already configured | Do not build a collector or assume hosted Analytics metrics appear in customer OTEL |

Autonomously read a supported available surface before asking a user for data. If no supported route exposes the needed window, label it unknown and retain bounded sequential execution. Do not make every message repeat a full account inventory. Track estimate versus actual in the existing work record, not a dashboard, schedule or duplicated tracker.

Keep four things separate, requested configuration, saved settings, observed runtime, and bills. Under Auto, report backend unknown unless current supported evidence exposes it. A visibility policy can hide backend choices. Factory-reported `factoryCredits` or exec `factory_credits` are not dollar charges. Optional BYOK provider charges require provider records; never assert included credits paid without readback.

At a native warning, reduce proposed scope or parallelism where justified, then observe. At a real limit or unexpected managed provisioning, preserve progress and report the exact signal. Hooks only add context, they do not continuously watch limits, stop workers, throttle concurrency or guarantee budget-aware Auto routing.

Sources checked 2026-11-08 include [CLI reference](https://docs.factory.com/droid-cli/cli-reference.md), [Workstream settings](https://docs.factory.com/workstreams/settings.md), [Sessions API](https://docs.factory.com/api-reference/sessions.md), [Analytics](https://docs.factory.com/api-reference/analytics.md), [app settings](https://docs.factory.com/factory-app/settings.md) and [telemetry](https://docs.factory.com/enterprise/telemetry/index.md).
