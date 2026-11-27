---
operating-doctrine: minor
---
Workers clean up after themselves. The M2 browser sweep now runs every 15 minutes and closes only windows whose owning session has ended, holding and logging failed, pending, shared, unproven and Grok windows, with one JSON line per decision. The browser Stop hook leaves a cleanup receipt before it clears its session marker and prints the browser count for the session-wrap Cleanup done line. The M4 janitor closes any browser an AI opened on the M4 and logs the opening session, never Allison's own Chrome or Safari. Session wrap now requires each session to clean its own browser windows, temp files, Scratch folders and stray worktrees and report them in a Cleanup done line.
