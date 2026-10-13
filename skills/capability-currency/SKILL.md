---
name: capability-currency
description: "Twice-monthly staying-current sweep for the Expert Partners AI Operating System, built on capability-refresh, extending never replacing it. Fires the 1st and 15th, 7 AM CDT, from launchd job com.expertpartners.capability-currency on the M4, and whenever Allison asks whether estate capability knowledge is current, whether anything moved at Anthropic, in the MCP spec, the pinned Python SDK lines, the AWS serverless stack under the Estate Brain door and memory spine, or in estate-relevant AI developments. Sweeps five heads against live sources, Firecrawl primary, overwrites the Capability Watch Doc, adds a dated entry with a source URL per claim to the Capability Refresh Changelog Doc, files the run record as a Google Doc in HQ Business Brain, and classifies findings first, preserving unactivated ones as Job Tracker rows with RETURN WHEN, carding only what Allison activates. Use it even unnamed, whenever the ask is whether the AI operating layer's knowledge is stale. Inherits the operating-doctrine."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-08-05 (Capability Currency Build lane, per the locked
# Capability Currency plan). Zone hands per the acn-currency-check precedent.
tier: organization
zone: hands
status: live
subtitle: "twice-monthly estate capability sweep"
---

# Capability Currency -- v1.1 (2026-08-30)

v1.1 amendment 2026-08-30 (ruled by Allison; ruling of record: aura decisions/0083-sequencing-without-maximalism-amendment-to-decision-0075.md; advisory of record aura intake/2026-08-30-sequencing-without-maximalism-corrected-final-advisory-super.md): activation behavior only. Findings are classified first, and the prior rule that every needed change is emitted as a flag becoming a Founder Active Work card with a proposed due date is superseded by output 4 below. All research machinery, cadence, sources, capability-watch, changelog, run record, duplicate check, and healthcheck behavior stay exactly as they were.

Keep the estate's capability knowledge honest. The AI operating layer moves faster than a monthly cadence catches, deprecation clocks start ticking the day a vendor posts them, and the 2026-08-03 Capability Check proved the cost of finding a two-day-old retirement notice two days before it fires. This skill runs the sweep twice a month so no clock gets found late.

## Relationship to capability-refresh

This skill is built on the capability-refresh pattern and extends it. capability-refresh stays untouched as the generic monthly refresh any project can call with its own specialty. capability-currency is the Aura estate instance, twice monthly per Allison's 2026-08-05 ruling, with the five sweep heads fixed below and the estate's own output rails wired in. Never fork capability-refresh, never edit it from this skill, never treat this skill as its replacement.

## When this fires

1. On schedule, the 1st and the 15th of every month at 7:00 AM CDT, fired by the launchd job com.expertpartners.capability-currency on the M4 (after the 6:15 AM session janitor).
2. Whenever Allison asks if we are current, what changed, or whether capability knowledge is stale.
3. Before any recommendation that depends on a vendor capability, SDK version, or deprecation status more than 15 days old.

A run started by the scheduler works the whole sweep to completion and pings its healthchecks check only when every output landed. The builder of this skill never grades its own run, the first sweep and its verification belong to sessions that did not build it.

## Tooling

Firecrawl is primary for every source check (the Code lane reaches mcp.firecrawl.dev with the Bearer key read from op://Automation/FIRECRAWL-API-KEY at call time, never plaintext). Built-in web fetch and web search are the fallback when Firecrawl cannot reach a source. Browser automation is the last resort and needs the browser-last gate.

## The five sweep heads

Sweep every head every run. For each head, compare live state against the baseline recorded in the Capability Watch Doc, and read every pinned line fresh from the repo, never from this skill's text. Baselines written here are as of 2026-08-05 and exist so the first runs have a floor, the watch file is the living baseline.

1. MCP spec and deprecation clocks. Sources, modelcontextprotocol.io/specification/versioning for the current spec revision (2026-07-28 as of this writing), the deprecated features registry at modelcontextprotocol.io/specification/2026-07-28/deprecated (re-resolve the path against the current revision each run), and the feature lifecycle policy at modelcontextprotocol.io/community/feature-lifecycle. Watch for new revisions, newly deprecated features, and removal-eligibility dates. The Estate Brain door is dual-era (SDK 2.0.0 on Lambda serving both the 2026 negotiation style and the legacy initialize handshake), so any clock on either era matters, the known long clock is the legacy-handshake deprecation window landing around July 2027.

2. Anthropic and Claude releases. Sources, platform.claude.com/docs/en/release-notes/overview for the API and platform, support.claude.com release notes (support.claude.com/en/articles/12138966-release-notes) for Claude Apps and Cowork, the Claude Code changelog at github.com/anthropics/claude-code/blob/main/CHANGELOG.md, and anthropic.com/news. Watch for model retirements and new model strings, API feature changes, MCP-related platform changes, Claude Code and Cowork behavior changes, and pricing or plan changes that touch the estate.

3. The pinned Python SDK lines. Read each pin fresh from aura at run time. The door's live Lambda home, tools/mcp-brain-server/server/requirements-lambda.txt (mcp>=2.0,<3 as of this writing). The Fargate bench and brainmcp, tools/mcp-brain-server/server/requirements.txt, tools/mcp-brain-server/brainmcp/pyproject.toml, and tools/mcp-brain-server/brainmcp/src/requirements.txt (all mcp[cli]>=1.29,<2.0 as of this writing, the old brainmcp >=1.9.0 floater is fixed in source and survives only in the agentcore staging cache, which is a cache, not a source). Also check the M4's installed mcp package version. Against each window, check PyPI for new mcp releases, yanked versions, and breaking changes announced inside or just outside the window.

4. The AWS serverless stack the door and spine ride. Lambda (including the Python runtime deprecation calendar), API Gateway, Aurora Serverless v2 (the memory spine's PostgreSQL home, watch engine-version end-of-life clocks), Secrets Manager, and Fargate (the door's bench). Sources, the AWS What's New feed and each service's deprecation and end-of-support pages. Watch for runtime retirements, API deprecations, pricing changes, and regional behavior changes.

5. Estate-relevant AI developments. Security advisories first, per the LiteLLM CVE precedent, check advisories (GitHub Security Advisories, osv.dev) against the packages the estate actually runs before reporting exposure, and report not-exposed findings on the record too. Then the named ecosystem pieces, Graphiti and FalkorDB (the keeper), Langfuse (the estate runs Langfuse Cloud), and any AI development material enough to change estate doctrine or open a capability the estate should act on.

## Outputs per run, all five, every run

1. Overwrite the Capability Watch Doc (Google Doc `1aaWBVTySyMPfW9XFTiDRTy_Z3TnJKAXcc1BHJ1Nl09k`, Company Core [HQ-BB]) with the current-state snapshot, updating the Last refreshed date. The watch Doc is current state, the changelog is history.

2. Add one dated entry at the top of the Capability Refresh Changelog Doc (Google Doc `1fGNxd_hsAIdnmKe7z677VYBuaR_szhSM9bbztbWEVQQ`) covering the window since the last entry, what changed, what it means for this estate, and what to act on. Every claim carries its live source URL and retrieval date. Never edit prior entries, the Doc is append-only.

3. File the run record as a Google Doc in HQ Business Brain, Company Core [HQ-BB], so the run is readable from every surface.

4. Classify every finding first, before any activation output fires, under the operating-doctrine's Decide Now disposition seam. Contained cleanup within existing authority may happen in lane as part of the run. A blocking finding surfaces immediately. A meaningful non-blocking finding is preserved as one Job Tracker row, with the come-back condition written in Waiting on as RETURN WHEN, pointing at the owning Doc rather than duplicating it. A Founder Active Work card is created only when Allison deliberately activates the finding as an initiative through the intake ritual. The existing duplicate check is preserved and applies to Job Tracker rows exactly as it applied to cards, read the Job Tracker first, never mint a duplicate, feed the existing row instead. (This supersedes the 2026-08-05 propose-with-override flag-to-card rule for sweep findings, per Allison's 2026-08-30 correction of record.)

5. The two Docs are the only standing-authority writes. Anything touching doctrine is a proposed diff for Allison, never auto-applied.

If any output rail is unreachable, say so in the run record and finish the others, a partial run that names its gaps beats a silent skip.

## Messages to Allison

Nothing texts Allison unless she has an action to take. Any message that does go out honors the CI Alert Redesign three message rules, alert only when she has an action to take, plain simple language, and no GitHub links, anything she must read lands in Google Drive as a styled doc with the Drive link in the message.

## Schedule and health

The launchd job com.expertpartners.capability-currency fires the runner script (expert-partners-skills tools/capability-currency/run-capability-currency.sh) on the 1st and 15th at 7:00 AM CDT. The runner pings the dedicated healthchecks check (1Password item op://Automation/capability-currency-heartbeat, ping_url field) on success only, and pings /fail on a crash, so a run that fails to fire or dies mid-sweep alerts instead of dying silently. The check is capability-currency-m4, it is not the session janitor's check, never touch session-janitor-m4 from this skill. Kill switch, touch ~/.claude/capability-currency-off to skip runs, remove it to resume.

## Rules that never bend

- capability-refresh stays untouched. This skill extends it and never edits, forks, or replaces it.
- Secrets live in 1Password only, read with op at call time, never plaintext in configs, command lines, or chat.
- A monitor hit or a headline is a lead, never a conclusion. Fetch the underlying live source before reporting a change as real.
- Every claim carries a source URL, unverifiable claims are labeled unverified or left out.
- No self-attestation. The session that runs the sweep never certifies its own build, and the builder never grades the first run.
- No duplicate cards, no duplicate Job Tracker rows, no duplicate healthchecks checks, no duplicate reference files. Check first.
- Doctrine changes are proposed diffs for Allison. Reference files are the only standing-authority writes.

## Formatting

Allison's rules everywhere. No em dashes, no bold, no italics, no dividers. Spoken register. Lead with what changed. End where the content ends.
