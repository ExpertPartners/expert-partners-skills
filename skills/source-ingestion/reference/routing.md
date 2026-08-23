# Destination Routing -- reference

This skill never hardcodes the full Estate repository map. It resolves a
destination at runtime, in this order:

1. **Allison's explicit destination wins.** If she names a repo, a project,
   or says a phrase like "add this to External Methodologies", that is the
   destination; do not second-guess it.
2. **Read live estate canon.** Use the estate-brain MCP (`list_repos`,
   `search`, `fetch`) or a live `gh repo view` / `git ls-remote` check to
   confirm the repo actually exists and to find its current conventions
   before writing into it. Never rely on a memorized map that may have gone
   stale (per Rule 5 / sourced-or-retrieved).
3. **Determine the actual owning repo** from the classification in
   `reference/protocol.md`:
   - Reusable outside/source material (section 4A) -> the estate source
     library, `ExpertPartners/external-methodologies` (see below).
   - Allison/Expert Partners synthesis derived from a source (section 4B) ->
     the downstream brand/project repo that owns that content. Use the same
     project -> home/repo map the `intake` skill already maintains
     (`skills/intake/SKILL.md`, "Project -> home/repo map"); this skill does
     not keep a second copy of that table.
   - A deep research report -> `reference/protocol.md` section 6 (usually
     `research-intake`, sometimes a downstream owner once ruled).
4. **If the desired repo does not exist yet, PREPARE and report, never
   create it without authorization.** New-repo creation is its own decision
   (the `new-project` skill's job, or an explicit ruling from Allison), not
   something source-ingestion does as a side effect of filing one source.

## ExpertPartners/external-methodologies (planned, not built)

Verified live 2026-08-23 (`gh repo view ExpertPartners/external-methodologies`
returns "Could not resolve to a Repository"): this repo does not exist. This
skill never creates it. When a source's correct home is this library and it
does not exist yet, the dossier is built to a local staging path (or the
calling surface's working directory) and the report states plainly: "planned
destination: ExpertPartners/external-methodologies (not yet created)".

Its currently approved conceptual organization, once it exists, is
domain -> creator -> methodology/source:

```
external-methodologies/
  marketing/
    russell-brunson/
      expert-secrets/
  personal-development/
    <creator>/
      <source>/
  recruiting/
    freedom-funnel/
      <creator-or-source>/
```

Books are a source FORMAT, never a top-level domain; a book by a given
creator lives under that creator, under the domain the book's actual subject
matter belongs to. Creator-first organization inside each domain is
preferred because it is what carries provenance forward cleanly; two
creators writing about the same domain never get merged into one folder.

Domain names are not a fixed enum; they are named from the real subject
matter of what is being filed (marketing, personal-development, recruiting,
sales, leadership, and so on, as sources actually arrive). Do not invent a
domain taxonomy in advance of real material.

## Downstream synthesis destinations

For section 4B routing (Allison/EP doctrine derived from a source), reuse
`skills/intake/SKILL.md`'s project table exactly; do not copy it here, since
a second copy is a second thing to go stale. If the project is not in that
table, follow that skill's own fallback: ask Allison, or suggest
`/new-project` if the destination is genuinely new.
