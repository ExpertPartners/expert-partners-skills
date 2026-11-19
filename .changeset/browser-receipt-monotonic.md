---
operating-doctrine: patch
---

Browser job receipts never move back from finished. The facade checks for a settled receipt and replaces the file under one host-wide receipts lock, so a sweep or reconciliation that finishes a job between the check and the write is kept. A receipt loaded from disk by the lifecycle sweep keeps the control socket of the facade that owns the job instead of taking the sweep's short-lived socket.
