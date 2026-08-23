# Source Ingestion Protocol -- reference

Full detail behind `SKILL.md`. This file is the substantive canonical
protocol. Everything else that presents source-ingestion on another surface
(the ChatGPT adapter, any future adapter) reads FROM this file; it never
carries its own copy of these rules.

## 1. Input contract

The workflow accepts any of: a local file or attachment, a Google Drive
file/link (when the running surface has Drive access), a web or YouTube URL,
a transcript, pasted source text, a research report, a folder or group of
related sources, or a plain-language request that points at material already
sitting in the conversation's context. It never requires a slash command or a
fixed phrase; see `SKILL.md` "Triggers".

## 2. Classification fields

For every source, determine or record:

- **Title**
- **Creator / author**
- **Source type** -- book (PDF), Word document, slide deck, YouTube video,
  YouTube transcript, podcast/audio transcript, course/training material,
  Google Drive file, pasted text, deep research report, web page/article,
  interview, or internal original material. Books are a source FORMAT, never
  a top-level domain.
- **Subject / domain** -- the actual subject matter (marketing, personal
  development, recruiting, sales, leadership, and so on). Determined from the
  real content, not guessed from the filename or a keyword.
- **Methodology / program / book / video name**, when the source is itself
  named material (a book title, a course name, a framework name).
- **Provenance** -- who created it and in what context (a course module, a
  YouTube channel, a purchased program, an internal working session).
- **Original source location** -- the URL, Drive id, file path, or physical
  description of where the source actually lives.
- **Date, or date accessed**, when available.
- **Ownership classification** -- one of `allison-ep` (Allison or Expert
  Partners authored it), `third-party` (someone else's IP, being used for
  internal research), or `unclear` (genuinely ambiguous; never force a
  guess).
- **CORE status** -- see section 3.
- **Downstream systems/brands/products** this source may inform (a list;
  a source can inform more than one).
- **Canonical destination** -- see `reference/routing.md`.
- **Binary handling** -- whether the original binary should be stored,
  linked, or both. Prefer link-plus-durable-markdown-extraction over storing
  large binaries in git unless the binary itself is small and central.

## 3. CORE rule

CORE is about guaranteed Estate usability, not file location. A CORE source
must end up as a durable, high-quality, machine-readable source dossier in
the canonical GitHub home, even if the original binary stays somewhere else
(Drive, a purchased-course platform, wherever it already lives).

Allison may designate CORE explicitly, in her own words: "core",
"foundational", "really important", "we need to follow this", "make sure the
Estate knows this", or a clear equivalent. When she has not said one of
these, the skill may RECOMMEND core status with its reasoning, but it never
silently elevates ordinary material to CORE. The dossier's `core:` field
(see `reference/dossier-schema.md`) always reflects Allison's actual ruling,
recorded plainly, never a guess dressed as a ruling.

## 4. Source vs synthesis

Two categories, never blurred:

- **A. Outside/source material.** The dossier itself. Attributable to its
  real creator. Read section 5 for how third-party material is handled.
- **B. Allison/Expert Partners synthesis.** Doctrine, decisions, products,
  frameworks, and original IP that Allison or Expert Partners produced,
  including material that was INSPIRED BY or DERIVED FROM outside sources.
  This belongs in the appropriate downstream owning repo (the `intake`
  skill's project -> home/repo map is the same map used here), and it should
  carry traceable lineage back to the sources that informed it, typically a
  reference to the source dossier's path or a citation in the doctrine
  document itself.

This skill never writes third-party methodology into a downstream brand
repo's canon as if Expert Partners authored it, and it never writes Expert
Partners doctrine into a source dossier as if it were the outside material.

## 5. Third-party material

Legitimate internal research use of third-party material is never blocked
merely because the source is third-party. At the same time:

- Preserve attribution and provenance in the dossier, always.
- Never imply Allison or Expert Partners authored third-party material, in
  the dossier or anywhere it is used.
- Never automatically publish third-party source material outward (no
  posting, no external distribution) as a side effect of ingestion.
- Keep the dossier's structured summary/analysis distinguishable from any
  verbatim quotation of the original.
- If it is genuinely unclear whether a full verbatim extraction should be
  retained, default to preserving the original (or a pointer to it) plus the
  structured source dossier, and say the ambiguity is unresolved. Never
  invent a legal ruling on Allison's behalf.

## 6. Deep research routing

Reusable research knowledge belongs with reusable source knowledge, not
automatically inside a brand's canon. Two paths:

- **Still reusable research, no ruling yet.** If the report's natural home is
  the aura research corpus, hand off to the `research-intake` skill (owns
  `docs/research/INDEX.md`); do not build a source dossier for it here, to
  avoid two competing homes for the same report.
- **Already ruled into downstream doctrine.** When Allison says something
  equivalent to "this is now Authority Engine doctrine" (or names any other
  downstream owner), route the material to that downstream repo per
  `reference/routing.md`, carrying lineage back to the original report
  (link the report, or its research-intake index entry, from the new
  doctrine document). The report does not have to stop existing as reusable
  source material just because a doctrine decision drew on it; both can be
  true, correctly linked.

## 7. Surface authority modes

**Write-capable mode** (Claude Code, or any surface with verified,
tested repo-write access):

1. Inspect live destination state (does the repo exist, does the target path
   already hold this source, is there a naming collision).
2. Build the dossier with `scripts/scaffold_dossier.py`.
3. Validate: relative links resolve, no em dashes, frontmatter fields
   present, `core:` reflects an actual ruling not a guess.
4. Commit and push only when authorized under the normal Estate push-authority
   rules (net-new additive content into an owned repo is ordinarily
   delegated; a protected repo may need a branch and PR, same as the
   `intake` skill's map already specifies).
5. Report exact paths and the commit SHA (or PR URL).

**Advisory mode** (North / Estate Control Tower, Cowork, plain Claude chat,
ChatGPT, or any surface without proven repo-write access):

1. Classify and resolve the destination exactly as above.
2. Prepare the ingestion packet: everything write-capable mode would have put
   in the dossier, laid out plainly (not necessarily as committed files).
3. Do NOT claim a commit happened. Never say "added to GitHub" or "saved to
   the repo" from an advisory surface.
4. Produce the handoff: a routed implementation brief a write-capable surface
   (ordinarily Claude Code) can execute directly, naming the exact target
   repo/path or the planned destination if the repo does not exist yet.

This distinction is tested in `tests/`; see test cases 7 and 8.
