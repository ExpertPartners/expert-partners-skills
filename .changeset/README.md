# Changesets

A changeset is one small note that says which plugin a pull request changes and what changed. Builders add a note here instead of editing a version or a CHANGELOG. Two pull requests that each add their own note never touch the same file, so they merge without conflict.

## Writing a note

Add one file per pull request, named `<issue number>-<short slug>.md`, for example `.changeset/159-one-owner-for-versions.md`:

```markdown
---
operating-doctrine: minor
brand-voice: patch
---

One paragraph, in the words the CHANGELOG should carry, saying what changed and why.
```

- Between the `---` lines, write one line per plugin the pull request changes: the plugin name as it appears in `.claude-plugin/marketplace.json`, then `patch`, `minor` or `major`.
- Below the closing `---`, write the change. It cannot be empty.
- Do not edit `version` in `plugins/<plugin>/.claude-plugin/plugin.json` or `.claude-plugin/marketplace.json`, and do not add or edit the top entry of any `CHANGELOG.md`. The auto-merge gate refuses a pull request that does. A brand new plugin may carry its first version.
- A pull request that changes no plugin needs no note.

## What happens on main

`tools/release/release.py` reads every note, gives each plugin one version bump at the largest level any note asks for, writes that version to both the plugin's `plugin.json` and its marketplace entry, adds one entry to the top of `plugins/<plugin>/CHANGELOG.md` carrying every note's text, and deletes the notes it used. `tools/release/README.md` explains how to run it.

This README is never read as a note.
