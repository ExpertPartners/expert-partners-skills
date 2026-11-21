---
operating-doctrine: patch
---

The browser job window adapter now waits for Chrome to finish starting before it hands over the connector page. When Chrome had just crashed or restarted, the connector page could open before the Playwright Extension loaded and show ERR_BLOCKED_BY_CLIENT, which stalled every new browser job until someone clicked Repair. The adapter now waits up to 20 seconds for a Chrome that has been running at least 15 seconds, still never starts a stopped Chrome, and refuses cleanly instead of opening a blocked page.
