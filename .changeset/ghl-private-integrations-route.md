---
operating-doctrine: patch
---

The headless route check lets the GoHighLevel Settings, Private Integrations page through, because GoHighLevel has no public API to create a private integration token or grant its scopes. Every other GoHighLevel settings path still goes through the access map. This restores an exception that existed only as an M2-local patch and was lost when the plugin updated.
