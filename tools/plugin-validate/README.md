# plugin-validate

Checks that the plugin marketplace and the plugin packages agree.

```
python3 tools/plugin-validate/validate_plugins.py            # errors fail, warnings print
python3 tools/plugin-validate/validate_plugins.py --strict   # warnings fail too
python3 -m unittest discover -s tools/plugin-validate        # fixture tests plus a live-repo check
```

Errors: marketplace entry fields missing; source directory or `plugin.json` missing; `plugin.json` name or version differs from the marketplace entry (the two-file bump rule in the code-block-routing skill); non-semver version; a `plugins/` directory missing from the marketplace; a plugin with no `skills/<name>/SKILL.md`; a SKILL.md whose frontmatter name differs from its folder or whose description is empty or at or over 1024 characters.

Warnings: `plugin.json` without an author; a plugin package without a `README.md` capability record.

Standard library only. Not yet wired into CI: `.github/workflows/ci.yml` is deployed from the L6 Gatekeeper in aura, so wiring belongs in that source, not in a local edit here.
