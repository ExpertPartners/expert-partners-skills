---
operating-doctrine: patch
---

Restore fresh owned browser connections after Playwright Extension 0.6.0 turns its initial connector into about:blank. Adopt only the connection's single blank page back onto its own connector, and normalize the new extension status response while retaining 0.5.0 support.
