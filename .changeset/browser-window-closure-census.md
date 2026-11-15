---
operating-doctrine: patch
---

Browser jobs now prove a closed job window through Chrome's own window census instead of AppleScript. On the M2, Chrome stopped answering AppleScript while a Factory-launched consumer waited on an Automation consent it cannot hold, so every finish timed out after the window had already closed and left the job failed. Job windows are now checked with chrome.windows.getAll from a maintenance connector, a maintenance window proves its own removal by its page close event, and the live close records that the route issued the window removal before it runs. Receipts from before that record count the earlier live_window_scheduled stage as the same issued removal, so the lifecycle sweep can settle jobs whose windows already closed.
