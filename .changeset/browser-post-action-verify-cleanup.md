---
operating-doctrine: patch
---

Browser jobs now finish cleanly after a call fails during its post-action ownership check. Each proven inventory saves the newest Chrome tab ID, and failed-job cleanup reconciles an interrupted call through the same two exact-ID phases only when no surviving tab is newer than that watermark, so an orphaned popup is refused and preserved. Receipts now record a fixed Playwright or extension failure class instead of a bare owned_operation_failed, and finish records each cleanup step, including a live cleanup failure that used to be swallowed. No vendor or page text is kept.
