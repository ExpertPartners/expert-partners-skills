---
classification: internal
classification_owner: allison
classification_date: 2026-11-04
date: 2026-11-04
source: user-tier verify-docs skill, adopted 2026-08-05 (Skill Map Rulings lane, flags item 9), migrated into research-before-guessing 2026-11-04 (Chat to Code job, Audit and migrate useful standalone skill behavior into the canonical marketplace)
topic: verify current third-party documentation before building on it
---
# Verify current docs

Use with research-before-guessing when the guess or the build depends on the current behavior of third-party software, an SDK, an API, a library or a platform. Training-cutoff memory is months behind; verify before recommending or building, never after. The HQ Rulebook and Decision Log govern; nothing here adds a rule.

## When to verify

- A third-party tool enters the working context and the project has no fresh cache entry for it.
- Allison says latest, current, new version, or names a version, such as v3 or the new API.
- The cache entry is older than 30 days, or a major version change is implied.
- Code or config about to be written calls a third-party endpoint.

Do not verify internal tools, the estate's own code, or strategy questions that do not depend on a current API surface.

## The cache

Each project keeps `verified_docs.md` in its working directory, committed to git so every surface reads the same cache. Check it first. A fresh entry, under 30 days old with no major version change implied, is the answer; report the cached state and do not re-fetch. If the file does not exist, start it with a top-level heading and a one-line note about the 30-day re-verify rule.

Entry shape:

```markdown
## <Target name>

- Verified: <YYYY-MM-DD>
- Version: <version string>
- Official docs: <URL>
- Auth: <auth model>
- Key surface: <top endpoints or methods>
- Recent breaking changes: <list or "none in last 6 months">
- Source: Context7 / WebFetch / WebSearch
- Notes: <anything else that surprised the check>
```

Never write an entry without a real source URL and a real read behind it.

## How to verify

1. Confirm the exact product and API surface. If ambiguous, ask one short question, then proceed with the answer.
2. Check the cache (above). Exit on a fresh hit.
3. Pull the vendor's current first-party documentation by web search and fetch: the canonical docs URL, the current API surface, the authentication model, and release notes or breaking changes from the last six months. A connected documentation MCP, such as Context7, may supplement; the search plus fetch pair is sufficient on its own. Record the source and the date.
4. Write or refresh the cache entry.
5. Surface findings. A breaking change or deprecation that affects the plan is called out loudly and stops the dependent work until Allison sees it; a clean result is reported in one or two lines.

## Failure modes

- Official docs are gated or auth-required: say so and ask for the credential or a public URL. Never guess.
- The verification routes return nothing usable: report verification incomplete and propose the smallest next step. Never fabricate a version, endpoint or date.
- Sources conflict: surface the conflict and default to the most recent dated first-party source, labeled with its date.
