---
operating-doctrine: patch
---

The owned browser route now re-binds the job's own Chrome tab after a click or script sends it to another site, not only after `browser_navigate`. Chrome swaps the tab's page target on a cross-site move, so a click that opened a payment approval page used to close the retained page and fail the job. The same proof applies as before: the exact saved tab, window and group, one attached target, an https origin that passes the headless route policy, and an unchanged Chrome generation. Nothing is replayed, and the job still fails when no replacement is proven.
