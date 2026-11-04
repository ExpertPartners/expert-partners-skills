---
research-ops: patch
---

The Source Hunter and Video Discovery scripts now carry full type annotations and pass `mypy --strict`, which `.github/workflows/tooling-typecheck.yml` runs on every change to them. Runtime behavior is unchanged.
