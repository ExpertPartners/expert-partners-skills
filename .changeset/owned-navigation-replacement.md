---
operating-doctrine: patch
---

Preserve an owned HTTPS navigation job when the pinned Playwright extension automatically reattaches to the same Chrome tab. Require the exact Chrome and Playwright target IDs to match, recheck redirect policy and ownership, and never replay navigation.
