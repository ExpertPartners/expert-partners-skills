---
operating-doctrine: patch
---

Browser jobs now stop 1Password's inline sign-in menu from loading in pages they own. Its extension iframe made Chrome detach the Playwright debugger on Google sign-in and Cloud Console pages, which failed the job with target_closed. Chrome's normal 1Password autofill still works.
