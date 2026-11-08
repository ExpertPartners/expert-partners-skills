---
operating-doctrine: patch
---

Browser job preflight now waits out the short-lived second Chrome process that any launch of the Chrome binary creates, including a peer job opening its window, instead of failing the call as "Operation outcome uncertain". Job receipts now name the static refusal code at the failed stage.
