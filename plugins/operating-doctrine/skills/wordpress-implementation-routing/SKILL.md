---
name: wordpress-implementation-routing
description: "Use whenever Allison asks to change, configure, troubleshoot, publish, verify, or operate a WordPress website, especially AG Luxury or AllisonGaddy.com. Classify the requested outcome by the layer that owns the live state, then choose the narrowest reliable execution path. Prefer native WordPress abilities or APIs for reversible content and site-state changes, then REST, site-owned code only when code is actually required, WP-CLI or server tools for operational work, vendor APIs or MCP, and controlled browser automation only when no reliable machine interface exists. Prevent routine content edits such as link, copy, metadata, media, menu, and setting changes from becoming unnecessary code-release projects."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "pick the layer that owns the WordPress result"
---

# WordPress Implementation Routing

Allison describes the result. Own the implementation path.

This skill exists to stop overcoding and wrong-layer edits. A WordPress site can express the same outcome through database content, blocks, theme code, plugin code, settings, vendor integrations, server operations, or browser-only admin screens. Determine which layer actually owns the requested result before changing anything.

## Start with current truth

1. Read the HQ Rulebook and Decision Log first, then the owning business brain.
2. Inspect the actual target environment before choosing a tool.
3. Read the current live value before overwriting it.
4. Check 1Password and existing Estate connections before asking Allison for access.
5. Reuse the current owner. Do not create a second plugin, repo, workflow, MCP server, or automation just to finish a small change.

## Classify the change

Use the smallest class that fits the requested outcome.

- Read-only inspection: inspect and report.
- Reversible WordPress content or state: text, button destination, alt text, metadata, menu item, page block, media, ordinary setting.
- Configuration: plugin or vendor setting, form mapping, SEO setting, cache control.
- Reversible code: PHP, JavaScript, CSS system, theme template, plugin behavior, custom interaction.
- Server or bulk operation: database-safe search/replace, migration, cache operation, cron, bulk content work.
- High-blast-radius or destructive: deletion, domain or DNS change, production database replacement, privileged-user creation, destructive bulk operation.

Anything destructive, sent externally, paid, contractual, or hard to undo still requires Allison's explicit approval under HQ rules.

## Choose the execution path

Walk this order and stop at the first path that safely owns the state.

1. Native WordPress ability or WordPress API.
2. WordPress REST API.
3. Site-owned repository code, only when the requested result is actually code-owned.
4. WP-CLI or approved server tooling for operational, database, cache, or bulk work.
5. Vendor API or official MCP for external systems that own the state.
6. Controlled browser automation only when no reliable machine interface can perform the required action.

Do not use browser automation simply because the UI is visible. Do not use a code release simply because the site has a GitHub repository.

## Route common requests

- Change page copy: native WordPress ability or REST.
- Change a button label or destination: native WordPress ability or block/content update. Verify the live label, href, target response, and redirect behavior.
- Replace image or alt text: media ability or REST.
- Change navigation: navigation ability or site editor only when no API path exists.
- Change SEO title or metadata: use the current SEO data owner API or plugin surface.
- Change a plugin setting: native API if exposed, then vendor API, then browser.
- Purge cache: cache owner API first, then host UI if necessary.
- Add responsive CSS, change theme tokens, alter templates, or change custom behavior: repository code with branch/worktree, tests, package, rollback, and live readback.
- Build or repair IDX, JavaScript behavior, plugin logic, PHP, or theme architecture: repository code. Do not edit production source directly.
- Database migration or serialization-safe URL replacement: WP-CLI or approved server workflow with dry run, backup, and scoped verification.

## The anti-overcoding test

Before creating a branch or changing code, ask internally:

"Could WordPress itself change this safely as ordinary content or state?"

If yes, do not turn it into a software release.

A simple link or text correction should ordinarily finish as a narrow state mutation plus live verification, not a new guard, plugin release, deployment framework, or CI architecture.

If a tiny task begins spawning infrastructure work, stop and reclassify the layer before proceeding.

## Safety before mutation

For reversible content and state changes:

- Capture the before value.
- Preserve a WordPress revision or equivalent rollback path where available.
- For direct writes, use exact target IDs or scoped fields, not broad search/replace.
- Re-read immediately after the write.
- Verify the public page independently.

For code changes:

- Use the existing repository and isolated branch/worktree.
- Follow current repo checks and release gates.
- Do not bypass failed tests.
- Package from the exact merged source.
- Preserve rollback and verify the live version.

For browser fallback:

- State why no deterministic programmatic path could perform the job.
- Use the standing authenticated Ember browser path unless Allison explicitly overrides it.
- Preserve existing tabs and authenticated state.
- Verify the underlying saved state, not only that a click appeared to succeed.

## Definition of done

A task is complete only when all are true.

1. The intended state exists.
2. The visitor-facing result works.
3. No scoped regression is present.
4. Recovery remains available.
5. The completion can be proven with evidence.

Minimum evidence by change type:

- Copy edit: exact live text.
- Link change: DOM href plus successful destination.
- Image change: correct source, crop, size, and alt where applicable.
- Layout change: desktop and mobile visual proof.
- Plugin update: live version plus critical-route smoke test.
- Code release: commit, checks, package identity, live version, and visitor-facing proof.
- Cache change: warmed response is correct, not merely a successful purge action.

Never equate "save succeeded", HTTP 200, green CI, or a successful click with a working visitor experience.

## Escalation

Do not ask Allison which technical path to use. Choosing between API, REST, code, WP-CLI, vendor tools, or browser is the implementer's job.

Return to Allison only for:

- a real business decision,
- permission that cannot be obtained through approved systems,
- an irreversible or explicitly gated action,
- a conflict between current governing sources,
- or a verified blocker after the available safe execution paths have actually been tried.

## Completion receipt

Report only what matters:

- what changed,
- which owning layer was used,
- how it was verified,
- rollback or recovery status,
- and any remaining limitation.

For a routine successful link change, the ideal report is approximately: the approved destination is live, the target loads, no other page content changed, and the rollback path remains available.
