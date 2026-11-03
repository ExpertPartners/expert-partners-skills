# release

The one owner of plugin versions and CHANGELOG entries. Builder pull requests add notes in `.changeset/` (see `.changeset/README.md`) and never edit a version or the top of a CHANGELOG. This step folds the notes into one version bump and one CHANGELOG entry per plugin, on main, after merges.

| File | What it does |
|---|---|
| `release.py` | The release step. Python standard library only. |
| `tests/test_release.py` | Unit tests, including two branches that each add a note and merge without conflict. |

## What it does

For each plugin named by at least one note:

1. Takes the largest bump any note asks for (`major`, then `minor`, then `patch`).
2. Writes the new version to `plugins/<plugin>/.claude-plugin/plugin.json` and to the plugin's entry in `.claude-plugin/marketplace.json`. The two must agree before the bump, or nothing is written.
3. Adds `## <version> - <date>` with every note's text, in file name order, to the top of `plugins/<plugin>/CHANGELOG.md`, creating the file if the plugin has none.
4. Deletes the notes it used.

Every note is checked before anything is written. An unknown plugin, a bump that is not `patch`, `minor` or `major`, a note with no text or with a `## ` heading in its text, a note that is not UTF-8, or a version that already has a CHANGELOG entry stops the run with exit code 1 and changes nothing. The auto-merge gate applies the same note rules before a pull request merges (`note_problem` in `tools/auto-merge-gate/gate.py`, kept in step by its tests), so a bad note is refused there instead of stopping the release here.

## Running it

From the repository root, on an up to date main:

```
python3 tools/release/release.py --check   # validate the notes and print the plan, write nothing
python3 tools/release/release.py           # apply the notes
```

`--date YYYY-MM-DD` sets the entry date (default today in UTC). `--root DIR` points at another checkout.

The result is committed to main by the EP Skills Graph Bot app, the one actor allowed past the pull request rule on main, the same way `skills-graph.yml` commits the regenerated graph. A workflow that runs this step after each merge is not in this folder, because workflows live in `.github/workflows/`.

## Tests

```
python3 -m unittest discover -s tools/release/tests -v
```

The merge test makes real commits in a scratch repository, so it is skipped when git has no global identity.
