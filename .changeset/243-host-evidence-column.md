---
operating-doctrine: patch
---

The headless route check reads an optional Host evidence column on the access map. A live row whose browser host is still unknown can now leave Hosts empty by declaring Host evidence unresolved, instead of failing the whole refresh. It keeps its live status in the cache, is counted and named in every refresh report as still needing real host evidence, and never matches a navigation. Setting up rows with empty Hosts work as before. A hostless live row without the declaration still fails as a half-finished edit, and a row that loses hosts the last good copy protects still keeps the last good copy, even when it now declares Host evidence unresolved.
