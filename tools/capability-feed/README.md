# AI Workforce feed

This producer generates `ai-workforce-feed.json`, the public-safe AI Workforce feed that
Expert Partners HQ shows people. It is generated output. Never edit it by hand.

```
canonical GitHub truth (this repo)
  -> generate-feed.mjs (validated, public-safe, deterministic)
  -> tools/capability-feed/ai-workforce-feed.json on main
  -> GitHub contents API, raw media type (read-only token)
  -> a server-side reader, never the browser (the HQ app has none yet, checked Oct 19, 2026)
```

A capability change takes one canonical change in GitHub. The skills-graph workflow
regenerates the feed and commits it with the skill graph, so HQ needs no manual edit
and no one maintains a separate list.

## Where the truth comes from

| Feed content | Canonical source |
|---|---|
| Packages (plugins, collections) | `.claude-plugin/marketplace.json` and each `plugins/<name>/.claude-plugin/plugin.json` |
| Package display name, collection shelves | `plugins/<name>/README.md` (H1, and the "Skills by function" section) |
| Every skill, its lifecycle and relationships | `tools/skill-map/skills-graph.json`, produced by `tools/skill-map` from SKILL.md frontmatter |
| Skill summary, display name, "Use when" sentence | the skill's own SKILL.md (this repo's skills only) |
| How a package is presented | `feed.config.json`, where every entry cites its evidence |
| Verified deployment state | canonical capability records, once the AI Capability Curator writes them (below) |

`feed.config.json` is a presentation policy, not a registry. It lists no capabilities.
Today it says two things. The Real Estate Agent Toolkit is shown as one portable
collection of its 40 skills. The household ACN line is left off the Expert Partners HQ,
because its own plugin.json says it is structurally separate from Expert Partners LLC.

Skills owned by aura appear from their skill-graph entry alone (subtitle, lifecycle,
relationships), so the feed is a pure function of this repository's tree.

## Truth rules

- A field is filled only from a named canonical source. Otherwise it is empty or omitted.
- Skill-map lifecycle maps to HQ status like this. `designed` is Designed, `benched` is
  Deprecated, `retired` is Retired. `live` and `sleeping` are Unknown, because a live
  source is not evidence of deployment.
- Nothing is Active until a canonical capability record names the verified surfaces and
  the verification. A package is Active only when everything current inside it is.
- `verifiedSurfaces` stays empty and `lastVerified` says "Not yet verified on any
  platform" until that verification exists.
- Provenance (`source`, `sourceLinks`) appears only when the package README carries a
  "Source material" section with public https links. No GitHub link to this private
  organization is ever emitted.
- `generatedAt` and `verifiedAt` are the time this content was generated and validated
  against canonical sources. An unchanged feed keeps its timestamps, so main never
  churns on a no-op run.

## Public safety

Records are projected field by field, so private frontmatter keys, body text, access
lists, and unknown capability-record fields never reach the feed. The finished feed is
then scanned, and refused outright, if any value looks like a 1Password reference, a
token or key, a credential assignment, a JWT, a private GitHub URL, an email address, a
phone number, or a private host. A refused run writes nothing and the workflow fails,
so the last good feed stays in place.

The feed is also refused above 900 KiB. A reader gets it in one request, and the default
GitHub contents API response returns no content for files over 1 MB, so the cap keeps
the file well inside that.

## Run it

```bash
cd tools/capability-feed && npm ci && npm test
```

```bash
node tools/capability-feed/generate-feed.mjs --write
```

`--check` exits 1 when the committed feed differs from what the sources produce or
breaks HQ's contract. `--stdout` prints the feed without writing. Exit code 2 means the
sources were refused, with every problem listed.

## Automation

`.github/workflows/skills-graph.yml` runs the tests, regenerates the graph, then the
feed. On main it commits both together and verifies the committed feed with `--check`.
On a branch it validates without writing, and fails if the branch edits the feed file
to anything other than generator output. Changes to the marketplace, plugin manifests,
package READMEs, SKILL.md files, or this producer all trigger it, and so does an aura
skill change through the existing repository dispatch.

## HQ wiring

A server-side reader should read the committed file straight from GitHub, the way the HQ app already reads skills-graph.json. The token lives only in
approved secret storage and in HQ's server environment, never in this repo or the browser.

```
GET https://api.github.com/repos/ExpertPartners/expert-partners-skills/contents/tools/capability-feed/ai-workforce-feed.json?ref=main
Accept: application/vnd.github.raw+json
Authorization: Bearer <read-only token for this repo>
```

The raw media type returns the JSON itself, with no header or wrapper, so HQ parses the
response body directly. The repo is private, so the token needs read access to contents
on this repo only. Building a reader in the HQ app is a separate change in that repo, not here.

## Capability records (AI Capability Curator)

Under aura ADR 0098 the AI Capability Curator maintains capability lifecycle, with
GitHub as canonical truth. When the Curator settles where its canonical records live,
add that repo-relative directory to `capabilityRecordSources` in `feed.config.json` and
to the workflow's `paths`. Nothing else changes. The feed then regenerates whenever a
record does.

Each JSON file in a source directory has this shape.

```json
{
  "schema": "expert-partners-capability-record/v1",
  "records": [
    {
      "id": "agent-bio-writer",
      "status": "Active",
      "verifiedSurfaces": ["Claude Code"],
      "lastVerified": "2026-10-02, AI Capability Curator check",
      "verifiedAt": "2026-10-02T15:00:00Z"
    }
  ]
}
```

- A record for an existing id may set humanName, summary, status, source, maintainer,
  verifiedOwner, categories, portable, verifiedSurfaces, invocationInstructions,
  sourceLinks, lastVerified, replacedBy, replaces, accessNote, bestFor, useCases,
  askExamples, and outcome, and may add relatedIds and keywords. Kind never changes.
- A record for a new id must be kind `capability` or `agent`, with humanName and
  summary, and may group existing skills through containsSkillIds. This is how a
  durable capability (for example a GPT migrated into a plugin) appears in HQ.
- Every other field is ignored, so a record may keep private working notes.
- Status Active needs verifiedSurfaces and lastVerified in the same record.
- Every id a record names must resolve, and every link must be public-safe https.
- One canonical record per id across all sources.

## What the tests prove

`test/feed.test.mjs` runs against a synthetic repository and the live one.

1. Generation is deterministic, and only timestamps depend on the clock.
2. Invalid source data is refused with the reason named, and nothing is written.
3. Secrets and private-only fields cannot reach the feed.
4. Skill and plugin relationships resolve, and excluded packages leave no trace.
5. Collection membership resolves in canonical shelf order.
6. Unknown deployment state is never promoted to Active.
7. Generated-output drift and hand edits are detected.
8. Marketplace and skill-graph changes produce exactly the expected feed change.

They also prove the envelope passes HQ's own schema (mirrored in `lib/hq-contract.mjs`
from HQ commit `5cc9811`), and that the real
Real Estate Agent Toolkit stays one collection of 40 portable skills.
