---
operating-doctrine: patch
---

The headless route check now lets the GoHighLevel workflow builder through (`/v2/location/{id}/automation/workflows`, `/workflows` and `/workflow` paths) for reading and editing workflows, because GoHighLevel has no public workflow API. It reports the line "Headless route checked, GoHighLevel workflows, no API, no public workflow API". Contacts and every other API-covered GoHighLevel path still go through the access map.
