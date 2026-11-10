---
operating-doctrine: patch
---

Browser job receipts now keep fixed-label connection diagnostics at the first route-side failure and again at failed-job reconciliation. Each snapshot says whether the job's connector tab survives, whether the extension still lists the job's own tabs under its exact client name, whether each saved tab has a debugger attached, and a close reason that is reported or derived, else unknown. Collection is read-only from a maintenance connector and never changes the job outcome. Failed disposal now carries the live failure's close reason into reconciliation instead of discarding it.
