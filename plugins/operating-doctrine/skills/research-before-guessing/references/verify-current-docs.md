---
classification: internal
classification_owner: allison
classification_date: 2026-11-04
date: 2026-11-04
source: user-tier verify-docs skill, adopted 2026-08-05 (Skill Map Rulings lane, flags item 9), migrated into research-before-guessing 2026-11-04 (Chat to Code job, Audit and migrate useful standalone skill behavior into the canonical marketplace)
topic: verify current third-party documentation before building on it
---
# Verify current docs

Use with research-before-guessing when the guess or the build depends on the current behavior of third-party software, an SDK, an API, a library or a platform. Training-cutoff memory is months behind; verify before recommending or building, never after. The parent skill's order of sources, the HQ Rulebook and the Decision Log govern; nothing here adds a rule.

## When to verify

- Work about to be done depends on a volatile third-party fact: a version, endpoint, parameter, auth model, limit, price, model name, setting or deprecation.
- Allison says latest, current, new version, or names a version, such as v3 or the new API.
- Code or config about to be written calls a third-party endpoint or depends on a library's current behavior.

A question about our own tools, code, settings or skills is answered from the current owning code, configuration or live setting, in the parent skill's order (owning brain, HQ Rulebook and Decision Log, then the live system). It is verified that way, not exempted and not answered from a vendor fetch. A strategy question that depends on no current surface needs no docs check.

## The cache

A project may keep `verified_docs.md` in its repo, committed to git so every surface reads the same notes. It is supporting evidence: where the official docs live, what was found last time, when, and what surprised the check. Read it first to find the source fast and to compare against what you find now.

An entry's age never settles a volatile fact. When the work depends on one, check the current first-party source, however recent the entry is, and refresh the entry's date and contents after the check. If the file does not exist and the repo would benefit, start it with a top-level heading and one line saying entries are supporting evidence, not a substitute for a current check.

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

1. Confirm the exact product and API surface from the work itself (code, config, lockfile, the request). Pick the most likely one and say so when those leave it ambiguous.
2. Read the cache entry, if any, as supporting evidence.
3. Read the vendor's current first-party source: the canonical docs, the current API surface or schema, the authentication model, and release notes or breaking changes from the last six months. A connected documentation MCP, such as Context7, may supplement; web search plus fetch is sufficient on its own. Record the source and the date.
4. Compare with the cache and the plan, then write or refresh the cache entry.
5. Report. No change is one or two lines with the source and date. A breaking change or deprecation that affects the plan is called out loudly. When the repair is inside work already authorized, make it and keep going. Only a real business call of hers goes to Allison, as one question with a recommendation, while independent work continues.

## Failure modes

- Official docs are gated or need sign-in: use the access routes already authorized first, such as connected tools, accounts and sessions already signed in, credentials retrieved through 1Password, the vendor's public repo, SDK source or changelog. Never ask anyone to paste a secret into chat. Only when no route reaches it, report it as one question with a recommendation.
- Every route returns nothing usable: try the other routes the parent skill names, then report verification incomplete, label the dependent claim unverified, and propose the smallest next step. Never fabricate a version, endpoint or date.
- Sources conflict: surface the conflict and default to the most recent dated first-party source, labeled with its date.

## Test cases

The outcome cases live in [../tests/behavioral-cases.md](../tests/behavioral-cases.md).
