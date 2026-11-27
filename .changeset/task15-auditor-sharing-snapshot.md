---
operating-doctrine: patch
---

Business Brain Auditor sharing is never hardcoded. Each run reads the newest owning Decision Log sharing entry, evaluates actual permission roles against it and cites that entry in the report; under the current November 27 "Brain folders keep anyone-with-link viewer links" entry a viewer link is information and an anyone-with-link editor grant is the finding, and the audit never changes ACLs. Every run compares each of the nineteen pieces against the live blank master bodies, asserts a duplicate or twin only after comparing both bodies, and snapshots every source before and after with HTTP 429 backoff, labelling anything still uncompared UNVERIFIED. The regression checklist encodes the Bench's failing cases.
