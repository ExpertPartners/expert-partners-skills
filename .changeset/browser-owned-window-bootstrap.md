---
operating-doctrine: patch
---

Preserve the connector's existing singleton tab group when isolating a fresh browser job from a shared window. Avoid the ungroup-and-regroup ownership release in Playwright Extension 0.6.0, preserve foreign tabs, and verify the exact new window and blank seed cleanup.

Release unused facade control sockets lazily, exit on disconnected stdio, and expire zero-job tunnels after five minutes without interrupting active jobs or in-flight calls.
