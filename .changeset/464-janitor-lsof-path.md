---
operating-doctrine: patch
---
The M4 Scratch janitor calls lsof by its full path. Under launchd it had stopped at "lsof unavailable" on every run since it was installed, because launchd's PATH has no /usr/sbin. The AI browser check now runs even when lsof is unavailable.
