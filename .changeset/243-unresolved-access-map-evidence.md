---
operating-doctrine: patch
---

The headless route check no longer rejects the whole access map when a row declares its host evidence unresolved (status setting up with no hosts yet). Such rows stay in the cache and in the refresh report as evidence that still needs real hosts, never match a navigation, and are not treated as no API or complete. A refresh that would drop hosts a cached row protects still fails and keeps the last good copy, so first installs can load a map that carries unresolved rows without weakening the half-edited-row guard. hooks/README.md documents the projection contract, including the two deliberate ways to lift a protection.
