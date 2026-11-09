# Dependency policy

`check_versions.py` keeps the build and test tooling reproducible. It reads files in
the tree only. It never contacts a package index or registry and never runs a resolver.

`check_unused.py` flags declared dependencies nothing uses and imports nothing
declares. It reads the tree and runs the installed knip binary. It never contacts a
registry, fetches a package, or edits a file.

```bash
python3 tools/dependency-policy/check_versions.py           # reproducibility rules
python3 tools/dependency-policy/check_unused.py             # usage rules
python3 tools/dependency-policy/check_unused.py --only python   # or --only javascript
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
| `requirements-tooling.txt` | CI lint, the Ruff formatter, type checking, unused-code detection and coverage tooling; also pins PyYAML for the skills-graph workflow |
| `plugins/research-ops/skills/video-discovery/requirements.txt` | video-discovery runtime |
| `.../video-discovery/requirements-verification.txt` | av and Pillow, on the runtime |
| `.../video-discovery/requirements-dev.txt` | pytest, on verification |
| `plugins/research-ops/skills/source-hunter/requirements.txt` | Pillow, on the video-discovery runtime |
| `.../source-hunter/requirements-dev.txt` | pytest, on the source-hunter runtime |
| `tools/factory-inbox/requirements.txt` | Factory Inbox bridge runtime |

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

## Dependency usage

`check_unused.py` is the usage half of the policy. It prints one `USED` line per
direct dependency with its kind and evidence, one `FAIL` line per problem, and ends
with `unused-dependencies: PASS` (exit 0) or `FAIL` (exit 1).
`.github/workflows/tooling-unused-dependencies.yml` runs the check and the tests.
Both pull requests and pushes to main run it when inspected tooling Python sources
or either JavaScript producer's sources change, as well as when their declarations,
locks or detector configuration change.

JavaScript: knip reads the one shared configuration, `tools/dead-code/knip.json`
(the dead-code job owns it; no second knip config exists). The runner reports the
dependency issue types the dead-code gate leaves out: unused `dependencies` and
`devDependencies`, unused optional peer dependencies and binaries, and `unlisted`
imports, meaning an import package.json never declares. knip has no
unused-optionalDependencies report: an optional dependency is a declared integration
point, and this check never asks to remove one.

Python: each lock's `# Direct: ...` header names the direct dependencies; every other
pin is transitive and is never expected to be imported. A direct dependency must show
one kind of evidence in the lock's scope (the [tool.vulture] paths in pyproject.toml
that the lock's directory governs; the root lock governs the rest):

| Kind | Evidence |
|---|---|
| `runtime` | imported by a non-test module in scope |
| `test` | imported only by test modules in scope |
| `cli` | run as `python -m <name>` or a `node_modules/.bin/<name>` path by a workflow, shell script or plist |
| `runtime, optional` / `test, optional` | the import sits behind `try: ... except ImportError` |
| `stub` | a `types-<pkg>` pin whose <pkg> a lock pins or a scoped source imports |

An import in scope must be pinned and named in a `# Direct: ...` header in the
governing lock or a layer it includes. A transitive pin alone does not declare an
import; an unimported transitive pin is still allowed. An import behind try/except is
not excused: optional integrations must still be declared. `EXCEPTIONS` in
`check_unused.py` waives only the named lazy
integrations (the Google client and Playwright, installed on the founder Mac outside
the repo locks), each with its evidence, and an entry fails once its import is gone.
Nothing is removed or disabled because a detector cannot see a use; add an evidenced
exception instead. A distribution whose import name differs from its normalized pin
name (pyyaml to yaml, pillow to PIL, beautifulsoup4 to bs4, yt-dlp to yt_dlp) is mapped
in `IMPORT_NAMES`.

## Dependency update pull requests

`.github/dependabot.yml` asks GitHub's built-in Dependabot version updates for weekly
pull requests. It changes no setting, installs no app and grants no permission.

Coverage:

| Ecosystem | Directories |
|---|---|
| `pip` | `/`, `/plugins/research-ops/skills/source-hunter`, `/plugins/research-ops/skills/video-discovery` |
| `npm` | `/tools/capability-feed`, `/tools/skill-map` |

These are every directory that holds a `requirements*.txt` lock and every
`tools/*/package.json` producer, found the same way `check_versions.py` finds them.
`group-by: dependency-name` puts one dependency's update for all listed directories in
one pull request, so a package two locks share (Pillow, gray-matter, zod) moves together.

`tests/test_update_config.py` checks the file offline, with no PyYAML, network or
GitHub call. It fails when an ecosystem or directory is dropped, when a new lock
directory or producer is not listed, or when the file gains a merge instruction, a
credential or secret reference, a permission, `open-pull-requests-limit`, `cooldown` or
an option nobody has reviewed. It also fails when a workflow merges or approves
Dependabot pull requests. A new lock directory or producer therefore needs a line in
`.github/dependabot.yml` in the same pull request. The `dependency-policy` workflow's
path filter does not list `.github/dependabot.yml`, so run the tests by hand when only
that file changes.

Activation limits:

- GitHub reads the file from main. Nothing runs until it merges, and this repository has
  not yet seen an update run, so future update activity is unverified.
- Runs also depend on the repository's and the organization's Dependabot settings, which
  this file does not read or change. If they turn version updates off, turning them on
  is a settings change for Allison and is not made here.
- Update pull requests are never merged automatically. The auto-merge gate considers only
  Factory job pull requests (`factory-droid[bot]`, body starting `Closes #N`), and no
  workflow merges or approves Dependabot pull requests. A person reviews and merges each.
- Dependabot adds its default labels (`dependencies` and an ecosystem label) and creates
  them in the repository if they are missing.
- There are no `.in` files, so Dependabot edits a lock's pins and hashes in place and does
  not re-resolve the transitive set. When an update needs a transitive package the lock
  does not list, the `locks install exactly as written` job fails on that pull request;
  re-resolve it as [Changing a Python dependency](#changing-a-python-dependency) says.
- Security update pull requests are a separate repository setting, not this file.
