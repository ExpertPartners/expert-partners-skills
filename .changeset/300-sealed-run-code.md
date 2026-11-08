---
operating-doctrine: minor
---

Browser jobs gain an opt-in sealed mode for one secret-bearing `browser_run_code_unsafe` call: console, page errors, network events, snapshots and tab headers are not captured, the code is not echoed, and the reply is only a fixed token or fixed error code, after which the job is finish-only. Job receipts now keep per-stage timestamps for recent calls, with no page content.
