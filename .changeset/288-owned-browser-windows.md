---
operating-doctrine: patch
---

Allocate a separate persistent Playwright connection and existing-profile Chrome window for each named browser job. Require the exact job handle on every tool, retain working-page references, preserve headless policy, and provide owned cleanup and fail-closed recovery without replay. Refuse missing, unsigned or mismatched profiles before opening a connection. Distinguish measured concurrency and source delivery from native consumer adoption and certification.
