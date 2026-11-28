---
operating-doctrine: patch
---

Isolate temporary browser cleanup connections with the existing owned-window initializer. Cleanup now preserves peer tabs when the extension initially places its connection in a shared window.
