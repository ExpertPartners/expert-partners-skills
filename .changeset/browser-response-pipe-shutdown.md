---
operating-doctrine: patch
---

Close disconnected browser facade clients cleanly by redirecting a failed response pipe before interpreter shutdown. Existing owned-job cleanup still runs, and active peers are untouched.
