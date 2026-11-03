# Dependency policy

`check_versions.py` keeps the build and test tooling reproducible. It reads files in
the tree only. It never contacts a package index or registry and never runs a resolver.

```bash
python3 tools/dependency-policy/check_versions.py           # check this repository
python3 tools/dependency-policy/check_versions.py --root DIR
python3 -m unittest discover -s tools/dependency-policy/tests -v
```

It prints `dependency-policy: PASS` and exits 0, or prints one `FAIL` line per problem
and exits 1. `.github/workflows/dependency-policy.yml` runs the tests and the check, then
dry-runs an install of each top layer, which covers every lock below it, to prove the
locks are complete. The check cannot see a missing transitive dependency, so a new lock
that no listed lock includes must be added to that job's install list.

## Python locks

Every `requirements*.txt` file in the repository is a lock in pip's hash-checking
format, the same format `pip-compile --generate-hashes` and `uv pip compile
--generate-hashes` write.

- Each requirement, direct and transitive, is `name==version`, optionally followed by an
  environment marker, and carries at least one `--hash=sha256:` value.
- The only option allowed is `-r <file>`, to layer one lock on another. Editable
  installs, URLs, local paths and index options are refused.
- Ranges (`>=`, `<`, `~=`, `!=`), wildcards (`==13.*`) and bare names are refused.
- A package pinned in two files, or twice in one install, must carry one version.

Because the files carry hashes, pip installs them in `--require-hashes` mode and stops
on any package the lock does not list. That makes the transitive set exact: a missing
dependency fails the install rather than resolving silently.

Current layers:

| Lock | Adds |
|---|---|
| `requirements-tooling.txt` | CI lint and repository tooling (PyYAML) |
| `plugins/research-ops/skills/video-discovery/requirements.txt` | video-discovery runtime |
| `.../video-discovery/requirements-verification.txt` | av and Pillow, on the runtime |
| `.../video-discovery/requirements-dev.txt` | pytest, on verification |
| `plugins/research-ops/skills/source-hunter/requirements.txt` | Pillow, on the video-discovery runtime |
| `.../source-hunter/requirements-dev.txt` | pytest, on the source-hunter runtime |

Each file's header names its direct dependencies. Every other entry is transitive.

### Changing a Python dependency

Resolve against Python 3.12, the CI interpreter, in universal mode so the lock also
works on macOS and Windows.

1. Write the direct requirements of the whole install you are changing into a scratch
   file outside the repository, with the range you want, for example `/tmp/dev.in`.
2. Resolve it with hashes:

   ```bash
   uv pip compile /tmp/dev.in --universal --python-version 3.12 \
     --generate-hashes --no-header -o /tmp/dev.txt
   ```

3. Copy the new or changed blocks into the right layer. A block goes in the lowest
   layer whose install needs it, and is not repeated in a layer that includes it.
4. Keep a package shared by two installs (Pillow today) at one version in both.
5. Run the check, then install the top layer in a fresh Python 3.12 environment with
   `pip install --require-hashes -r <lock>` and `pip check`.

A tool such as a type checker belongs in `requirements-tooling.txt` with its full
hash-locked closure.

An exact pin also freezes yt-dlp, whose extractors follow changes on video sites. When
video-discovery or source-hunter needs a newer release, re-resolve with
`--upgrade-package yt-dlp` added to step 2 and follow the remaining steps.

### Workflow installs

Workflows install Python packages only with `pip install ... -r <requirements*.txt>`,
named from the repository root. A package named on the command line, even with
`==`, is refused because nothing verifies its hash or its dependencies. Options that
take a value, other than `-r`, are refused too, since their value reads as a package.
Every `pip install` on a line is checked, including one chained with `&&`, `||`, `;`
or `|`, one inside a subshell, and one with pip options before `install`.

`PENDING_WORKFLOWS` in `check_versions.py` names a workflow that still installs by
name and the text of the one finding waived there. That finding prints as `WARN`
instead of failing. Every other finding in the workflow still fails. The entry itself
fails once the waived finding is gone, so remove it in the change that fixes the
workflow.

## JavaScript producers

Every `tools/*/package.json` is a producer (today `tools/capability-feed` and
`tools/skill-map`).

- It has a `package-lock.json` at lockfile version 2 or 3. The lock's root dependency
  sections equal package.json's, every package resolves from
  `https://registry.npmjs.org/`, and every package carries a sha512 integrity.
- A dependency two producers both declare, in any dependency section, carries the
  identical specifier in each (gray-matter and zod today).
- A package path both lockfiles resolve, direct or transitive, resolves to the identical
  version and integrity in each. The producers parse the same SKILL.md frontmatter, so a
  different gray-matter, js-yaml or zod could make the skill graph and the feed disagree.
- Workflows install with `npm ci`, never `npm install`.

To move a shared dependency, change both producers in one pull request: edit both
package.json files the same way, run `npm install` in each, and commit both lockfiles.

This policy covers build dependencies only. Plugin versions are the release step's
(`tools/release`), not this check's.
