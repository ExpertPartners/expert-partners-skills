# Unused-code check

`check_dead_code.py` finds executable code that nothing reaches in the canonical
tooling: the Python under `tools/` and the source-hunter and video-discovery skill
scripts, and the two JavaScript producers. It reads the tree and runs the installed
detectors. It never makes a network request, and it never edits or deletes a file.

```bash
python3 tools/dead-code/check_dead_code.py               # check this repository
python3 tools/dead-code/check_dead_code.py --verbose     # also list each name-dispatched definition
python3 tools/dead-code/check_dead_code.py --only python # or --only javascript
python3 -m unittest discover -s tools/dead-code/tests -v
```

It prints one `ENTRY` line per entrypoint, then a `WARN` line per pending finding and a
`FAIL` line per problem, and ends with `dead-code: PASS` (exit 0) or `dead-code: FAIL`
(exit 1). `.github/workflows/tooling-dead-code.yml` runs the check and the tests.

Install the detectors first:

```bash
python3 -m pip install --require-hashes -r requirements-tooling.txt   # vulture
(cd tools/capability-feed && npm ci --ignore-scripts)                 # knip
(cd tools/skill-map && npm ci --ignore-scripts)
```

## Scope

| Language | Detector | Configuration | What it covers |
|---|---|---|---|
| Python | vulture | `[tool.vulture]` in `pyproject.toml` | `tools/`, and `scripts/` and `tests/` of source-hunter and video-discovery |
| JavaScript | knip | `tools/dead-code/knip.json` | every `tools/*/package.json` producer |

Markdown skills, generated feeds and graphs, deployed copies and `node_modules` are not
executable source and are not scanned.

Python findings are the vulture kinds that are code: functions, methods, classes,
properties, imports and unreachable statements. Variables and attributes are left out on
purpose. In this code they are mostly data that something reads by name, such as dataclass
fields, JSON records, protocol parameters and attributes that a library reads, and vulture
cannot tell those from dead data. `python -m vulture` from the repository root prints
vulture's raw list, data names included. That list is useful for a manual look, but it is
not the gate.

JavaScript findings are the knip issue types that are code: unused files, unused exports
and types, duplicate exports and unresolved imports. `ignoreExportsUsedInFile` is on, so
an export that only its own file uses is not reported. That code runs, and removing its
`export` keyword is a style change, not dead-code removal. Dependency declarations belong
to `tools/dependency-policy`.

## Entrypoints

The inventory comes from the source, not from a hand-kept list.

Python modules are entrypoints when any of these is true:

- `cli`: the module has an `if __name__ == "__main__":` guard.
- `test`: the module is a `test_*.py`, `*_test.py` or `conftest.py` in a `tests/` or `test/`
  directory, which is where unittest and pytest discover tests.
- `run`: a workflow, shell script, launchd plist or `SKILL.md` names the module's path.
  Comment lines in workflows and shell scripts do not count.

Every other module must be reached from an entrypoint by an import, or by a literal file
path that a loader opens, such as `importlib.util.spec_from_file_location(...,
os.path.join(HERE, "..", "drift-check.py"))`. A module that nothing reaches is reported as
an unreachable `module`.

JavaScript entries are listed explicitly per producer under `workspaces` in `knip.json`.
The runner checks that list against what package.json scripts and workflows run with
`node`. An entry that nothing runs fails, and a file that a script or workflow runs but
that is missing from the list also fails. knip reads the file in knip's own workspace
format. Because the repository root has no package.json, the runner gives knip one
producer at a time.

## Name-dispatched definitions

Some definitions are called by name, out of the detectors' sight. The runner clears a
finding only when the source shows one of these uses, and `--verbose` lists each one with
its evidence:

- Python calls the special method (`__call__`, `__exit__` and the like).
- unittest loads a `TestCase` subclass in a test module, its `setUp`, `tearDown` and
  `test*` methods, and the module hooks `setUpModule`, `tearDownModule` and `load_tests`.
- pytest collects `test*` functions and `Test*` classes in a test module, calls the
  `pytest_*` hooks in `conftest.py`, and injects a fixture that a test names as a
  parameter or through `usefixtures`. A fixture that no test requests is still reported.
- The method declares the interface of a `typing.Protocol` class.
- The method overrides one that its base class defines, and the base calls it. The base
  must be a class in the same module or a standard library class whose own methods include
  that name, for example `io.RawIOBase.readable` or
  `urllib.request.HTTPRedirectHandler.redirect_request`. A method that the base does not
  define is still reported.

Imports and unreachable statements are never cleared this way.

## Exceptions and pending findings

Two tables in `check_dead_code.py` hold the only per-finding entries. Each key is
`<path>:<kind>:<name>`.

- `EXCEPTIONS` is for code that is used dynamically in a way none of the rules above
  sees. The value must name the use and where it happens. It is empty today.
- `PENDING_FINDINGS` is for real findings in files that this check's own change does not
  own. They print as `WARN` until the owner removes or uses the code.

An entry in either table fails once its finding is gone, so neither table can hide new
code or outlive the gap it records. There is no blanket ignore. Nothing is deleted because
a detector cannot see a dynamic use. Add an evidenced exception instead.

Current real findings:

| Finding | Owner |
|---|---|
| `plugins/research-ops/skills/source-hunter/scripts/stitch.py`: function `_numbers` has no caller | source-hunter |
| `tools/plugin-sync/chatgpt-import-check.py`: `import zipfile` is never used | plugin-sync |
