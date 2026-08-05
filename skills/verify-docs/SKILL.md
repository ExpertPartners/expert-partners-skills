---
name: verify-docs
description: Verify the current state of any third-party software, SDK, API, library, or platform before building or recommending integrations. Spawns a research subagent that pulls the latest official docs via Context7 MCP, falls back to WebFetch + WebSearch, and writes a verified-knowledge entry to the project's verified_docs.md cache. Use whenever a new tool/software/integration enters the working context (HeyGen, GoHighLevel, Make.com, Notion, Cloudflare, Higgsfield, eXp APIs, Fireflies, Gamma, Stripe, OpenAI/Anthropic SDKs, etc.) or before recommending any code or config that depends on third-party docs. Skip if the target already has a fresh entry (<30 days, no major version change implied) in verified_docs.md. Also use when the user says "latest," "current," "new version," or names a specific version ("v3," "the new API").
metadata:
  version: 1.0.0
# --- skill-map metadata (additive, all optional) ---
# Adopted into canonical 2026-08-05 (Skill Map Rulings lane, flags item 9);
# the machine copy at ~/.claude/skills is a deployed copy.
status: live
subtitle: "live-doc check before building"
---

# Verify Docs — current-knowledge enforcement

You are an expert at making sure I never act on stale documentation. Training cutoff is months behind reality; software changes daily. Run this skill any time a new third-party software/SDK/API/library/platform enters the working context, before recommending or building anything that depends on its current behavior.

## When to run

Trigger this skill when:
- The user mentions a software/SDK/API/tool not yet verified in this project's `verified_docs.md`
- The user references "the latest" / "current" / "new" version of any platform
- More than 30 days have passed since the last verification entry for that target
- The user mentions a major version change ("v3", "the new API")
- I am about to write code or config that calls a third-party endpoint

Do NOT run this skill for:
- Internal tools, custom code, files in the working directory
- Targets already verified within the last 30 days (check `verified_docs.md` first)
- Conceptual / strategy questions that don't depend on current API surface

## Workflow

### Step 1 — Confirm the target

If ambiguous, ask one short question: *"Which exact product/API surface? (e.g., HeyGen Avatar API v2, HeyGen Streaming SDK, HeyGen webhook events.)"* If the user already gave enough specificity, skip.

### Step 2 — Check cache

Read `./verified_docs.md` in the project working dir. If an entry exists for this target dated within 30 days and no major version change is implied, report the cached state and exit. No re-fetch needed.

### Step 3 — Spawn research subagent

Use the Agent tool with `subagent_type: Explore` (narrow target) or `general-purpose` (broad survey). Brief the subagent like this:

> Verify the current state of **<TARGET>**. Tasks:
> 1. **Primary:** WebSearch for "<TARGET> official documentation 2026" to find the canonical docs URL, then WebFetch that URL for the current API surface.
> 2. **Primary:** WebSearch for "<TARGET> breaking changes 2026" and "<TARGET> release notes" — capture deprecations or changes from the last 6 months.
> 3. **Supplemental (only if connected):** Context7 MCP — `mcp__Context7__resolve-library-id` then `mcp__Context7__get-library-docs`. Context7 is purpose-built for up-to-date library documentation but may not be connected; check tool availability before relying on it. If unavailable, the WebFetch + WebSearch pair is sufficient.
> 4. Return a concise structured report: current version, official docs URL, key API surface (top 5–10 endpoints/methods), authentication model, recent breaking changes, anything that contradicts pre-2026 expectations.
> Keep the report under 400 words.

Run foreground if I'm about to act on the result; background if pre-emptive context-loading.

### Step 4 — Write to cache

Append (or create) `./verified_docs.md` in the project working dir using this format:

```markdown
## <Target name>

- Verified: 2026-MM-DD
- Version: <version string>
- Official docs: <URL>
- Auth: <auth model>
- Key surface: <top endpoints/methods>
- Recent breaking changes: <list or "none in last 6 months">
- Source: Context7 / WebFetch / WebSearch
- Notes: <anything else that surprised the subagent>
```

If the file doesn't exist, start it with a top-level heading: `# Verified Docs — <project name>` plus a one-line note about the 30-day re-verify rule.

### Step 5 — Surface findings

Tell the user:
- What was verified and when
- **Any breaking change or deprecation that affects the plan** — this is the load-bearing piece. If a deprecation invalidates the user's request, stop and surface it before continuing.
- Confirm cache write

If the result is clean (matches expectations, no surprises), keep the surface brief — one or two lines. Per Allison's directives: surprises called out loudly, clean results silent.

## Per-project cache file: `verified_docs.md`

Lives in the project working dir (committed to git so Ember, Cowork, and other agents can read it). Format:

```markdown
# Verified Docs — <project name>

> Re-verify any entry older than 30 days. Re-verify immediately if a major version change is mentioned.

## HeyGen Avatar API
- Verified: 2026-05-03
- Version: v2.3
- Official docs: https://docs.heygen.com/...
- Auth: Bearer token (X-API-Key header)
- Key surface: /v2/avatar/list, /v2/video/generate, /v2/video/status, /v2/streaming/...
- Recent breaking changes: streaming endpoint moved from /v1 to /v2 in March 2026
- Source: Context7
- Notes: Webhook signature now uses HMAC-SHA256 (was SHA1 in v1)

## (next target)
...
```

## Failure modes

- **Context7 disconnected (or has no record):** WebFetch + WebSearch pair is sufficient. Note `Source: WebFetch + WebSearch` in the cache entry. Re-add Context7 to the source string if/when it reconnects.
- **Official docs are gated/auth-required:** Tell the user; ask for the right MCP credential or a public URL. Don't guess.
- **Subagent returns nothing useful:** Don't fabricate. Report "verification incomplete" and propose next step (ask the user for a public docs link, defer the work).
- **Conflicting info between sources:** Surface the conflict; default to the most recent dated source.

## Anti-patterns (don't do these)

- Don't act on training-cutoff knowledge for any third-party API.
- Don't skip the cache check (wasted tokens).
- Don't make the user wait for a subagent if the cache already has a fresh hit.
- Don't write to cache without a real source URL.
- Don't run silently when a breaking change is found — surface it loudly.
