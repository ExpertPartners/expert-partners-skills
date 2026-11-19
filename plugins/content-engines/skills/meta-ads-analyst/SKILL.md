---
name: meta-ads-analyst
description: "Analyze authorized Meta Ads Insights or exports, recalculate comparable KPIs, and distinguish verified results from missing evidence and next-test hypotheses. Read only."
metadata:
  version: "1.0.0"
tier: plugin
zone: content
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "Read-only Meta ad performance analysis"
---

# Meta Ads Analyst

Original substitute. Cal's employee body is not recovered; the original gap remains open. Use this for the company's own authorized ad performance, not competitor estimates.

1. Read the active workspace's brand and brief. Identify the account, date range, currency, reporting level, goal, conversion event, account time zone and attribution setting. Do not combine totals with their breakdowns, overlapping dates, currencies, objectives, attribution windows or conversion definitions.
2. Prefer an existing read-only Meta Marketing API/Ads Insights integration. Query only the supplied authorized account and requested report. Use an authorized existing export next, then a dated internal performance report. For a necessary browser read, route to the assigned browser owner; do not modify campaigns, budgets, creatives, permissions or tracking. Do not contact leads. Use scoped credentials through approved storage, never in reports or command arguments.
3. Run `node <plugin-root>/lib/marketing-employees.mjs` with a request object on stdin; see [runtime contract](../../lib/marketing-employees.md). Map exact spend, impressions, link clicks, and the single named conversion event from the export. Use attributed realized revenue only. The same row units must cover every metric. Blank is unknown, not zero. If the source offers only precomputed figures, use `reported`, not invented rows or dates.
4. Return a decision brief. Show the measurement window and evidence link, source-reported versus recomputed figures, material denominators and attribution gaps. Explain one action to improve the decision, with the metric/event and comparison to obtain or verify. With mixed time windows, insufficient data or no matched prior period, say what cannot be inferred. Recommend a test only, never execute it. Do not call reported pipeline cash revenue or infer scale headroom from one period.
