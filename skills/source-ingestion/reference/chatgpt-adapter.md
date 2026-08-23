# ChatGPT-Compatible Package -- reference

Canonical source: this skill's `SKILL.md` and `reference/*.md`. The ChatGPT
package is GENERATED from that canonical source by
`tools/skill-deploy/deploy-skill.sh source-ingestion --chatgpt-zip <path>`.
It is never hand-maintained; if the ChatGPT copy and this canonical copy ever
disagree, this canonical copy wins and the zip gets regenerated.

## Why a separate package at all

Verified live 2026-08-23 against `learn.chatgpt.com/docs/build-skills`
(fetched directly) plus corroborating search results (thepromptindex.com,
agensi.io, skillselion.com, the `openai/skills` GitHub repo, and
developers.openai.com), ChatGPT's skill format differs from the Claude Agent
Skills format this repo otherwise targets in two concrete ways:

1. **SKILL.md frontmatter is name + description ONLY.** ChatGPT's spec does
   not have this repo's skill-map fields (`tier`, `zone`, `status`,
   `subtitle`) and there is no evidence it tolerates extra frontmatter keys
   gracefully; the generator strips to exactly `name` and `description` to
   stay inside the documented contract.
2. **`agents/openai.yaml`** is an OpenAI-specific optional file (UI metadata
   for the ChatGPT desktop app: `interface.display_name`,
   `interface.short_description`, `interface.icon_small/large`,
   `interface.brand_color`, `interface.default_prompt`,
   `policy.allow_implicit_invocation`, `dependencies.tools`). Claude's Agent
   Skills format has no equivalent file. All its fields are optional; the
   generator only writes `interface.display_name`,
   `interface.short_description`, and `policy.allow_implicit_invocation:
   true`, leaving icons/branding/tool-dependencies for Allison to add by hand
   later if she wants richer desktop-app presentation.

Everything else (the markdown body, `reference/`, `scripts/`) copies through
unchanged; the substantive protocol is never re-authored per surface.

## Size limits (verified live 2026-08-23)

WebSearch aggregation (thepromptindex.com citing the same spec the
`openai/skills` repo documents) reports: max zip upload 50 MB, max 500 files
per skill version, max 25 MB per individual uncompressed file. The direct
fetch of `learn.chatgpt.com/docs/build-skills` confirms the required
structure and frontmatter fields but does not itself restate the numeric
limits on that page; the numbers above are the aggregator-sourced figures and
are flagged as such in the generator's own printed output. This corrects the
mission brief's stated "under 25 MB" ceiling, which is the per-file limit,
not the zip limit; the generator enforces the tighter, verified 25 MB
per-file and prints a warning if the whole zip is approaching 50 MB, since a
small-text skill like this one will never be close to either number.

## Regenerating the package

```
tools/skill-deploy/deploy-skill.sh source-ingestion \
  --chatgpt-zip ~/Desktop/Claude\ Skill\ Zips/source-ingestion-chatgpt.zip
```

Staging happens in a `mktemp -d` directory that is discarded after zipping,
the same pattern the existing `--zip` (Claude standalone) path already uses,
so the generated ChatGPT copy never becomes an independent editable source of
truth sitting in the repo.

## Known compatibility limitation

`scripts/scaffold_dossier.py` is a Python script with no external
dependencies beyond the standard library, so it runs unmodified inside a
ChatGPT skill's `scripts/` folder wherever ChatGPT's runtime can execute
Python. This has not been live-tested inside an actual ChatGPT skill
execution sandbox as part of this lane (out of scope: this lane builds and
verifies the package structure and size, not a live ChatGPT install). Treat
"the script itself runs there" as UNVERIFIED until proven live in that
environment.
