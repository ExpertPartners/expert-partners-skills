# operating-doctrine changelog

## 2.34.1 -- 2026-08-07

GitHub sync acceptance test. No doctrine change, no skill body change. This
version bump exists to prove the claude.ai org marketplace pipe end to end,
per Allison's ruling of record (aura
intake/2026-08-07-ruling-github-sync-adopted-for-skill-deployment.md).
The pipe is proven when the deployed plugin reports 2.34.1 without any zip
touching any page.

Originally staged as 2.33.0 -> 2.33.1. Rebased past a same-day direct push
to main (8aab6bc) that bumped plugin.json to 2.34.0 without updating
marketplace.json, which still read 2.33.0 for operating-doctrine, a live
manifest drift. Resolved by carrying the bump to 2.34.1 in both files.
