---
operating-doctrine: patch
---

Browser lifecycle cleanup no longer blocks Stop forever on a failed allocation that never recorded a window, tab or relay claim, once an exact-process census of the signed-in Chrome, taken after the allocation, is recorded with `browser_lifecycle.py --record-census`. The sweep reports such a job as `failed_no_artifacts_by_census` and the hook says so; the receipt stays failed and is never marked finished. Receipts with real window or page IDs, pending ownership, relay claims or a live state keep blocking as before.
