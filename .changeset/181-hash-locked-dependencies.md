---
research-ops: patch
---

Source Hunter and Video Discovery now install from exact, hash-locked requirement files. Every Python package, direct and transitive, is pinned with `==` and carries its sha256 hashes, so `pip install -r` runs in hash-checking mode and refuses any package the lock does not list. The pins freeze what the earlier ranges resolved to on Python 3.12, with Pillow at one version in both skills.
