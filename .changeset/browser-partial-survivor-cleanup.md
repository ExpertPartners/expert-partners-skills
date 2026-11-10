---
operating-doctrine: patch
---

Failed browser jobs no longer leave windows behind with only part of their tabs. The route now stops a job's own browser process outright instead of letting it close pages one at a time, so a failure can't remove the connector and strand the working page. Reconciliation accepts a missing connector when every saved working page survives, records the removal before it happens so a retry finishes cleanly, and polls briefly until Chrome stops listing the closed window. A stale facade no longer overwrites a finished receipt, and a failed step now records which of the route's own checks refused.
