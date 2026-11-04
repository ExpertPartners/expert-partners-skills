---
date: 2026-11-04
source: tools/skill-map/package.json and package-lock.json
topic: npm tooling lock provenance and consistency
classification: public
---

# Skill map dependency lock

`package-lock.json` is npm output derived from this directory's `package.json`.
Its lock format is version 3. The original producing npm version is not recorded;
the format alone does not identify that version. Do not hand-edit the lock or
insert warning comments into JSON.

The exact generated attribute and existing review owner are in
[.gitattributes](../../.gitattributes) and [CODEOWNERS](../../.github/CODEOWNERS).
Dependency updates remain with the existing package and lock owner. The lock is
an input to the graph producer's install, not a generated graph or a skill package.

## Existing integrity control

The `lock-install` job in
[dependency-policy.yml](../../.github/workflows/dependency-policy.yml) runs this
native command for both JavaScript tooling packages:

```sh
npm ci --ignore-scripts --no-audit --no-fund
```

The typecheck, coverage, dead-code and unused-dependency workflows also consume
this lock with `npm ci`. The graph workflow installs this package before running
its producer. These existing consumers do not authorize a lock update or release.

For an isolated consistency proof, copy only this directory's `package.json` and
`package-lock.json` into a separate directory. Use a scrubbed environment, distinct
empty user/global npm configuration files and the public npm registry. Run the
same scripts-disabled command and verify a real `node_modules` install whose
direct versions match the lock. Both input files must remain byte-identical.
A changed dependency or missing lock must fail; a cache miss or dry run is not
a successful install.

An authorized dependency update uses npm to regenerate the lock alongside its
manifest change. No graph, layout, feed, skill, version, publication or deployment
is changed by this metadata. Native semantics: [npm ci documentation](https://docs.npmjs.com/cli/v11/commands/npm-ci/).
