---
name: job-list-heartbeat
description: "Retired. Sessions no longer check a job list on a timer. The AI acts on the brief and reports with links. Inherits operating-doctrine."
disable-model-invocation: true
user-invocable: false
allowed-tools: []
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-11-03 (Decision Log 2026-11-02, CEO directive, every Claude
# session checks the job list every 15 minutes). A simple CEO directive skill,
# so it ships with no proving line.
tier: plugin
zone: routing
status: retired
inherits: operating-doctrine
brand-scope: null
subtitle: "check the job list every 15 minutes"
---

# Job List Heartbeat

Retired. There is no job list to poll and no 15-minute check. Claude sessions do not run job_inbox, renew leases or set timers. The AI reads the brief, acts and reports with links.

This skill stays so existing references resolve. Decision Log 2026-11-08, Act by default, caution removed, supersedes the 2026-11-02 and 2026-11-03 heartbeat entries.
