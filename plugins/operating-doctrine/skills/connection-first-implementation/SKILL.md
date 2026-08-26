---
name: "connection-first-implementation"
description: "Fires whenever Allison asks to configure, audit, operate, build, troubleshoot, or change any external service and a connector, plugin, MCP server, API, SDK, or CLI could make direct implementation possible. Inspect the connections already held before concluding anything is missing, then reach for the strongest official connection immediately rather than deferring it. Prefer connected first-party tools, then official MCP servers and connectors, then existing Estate integrations, then the official API, SDK, or CLI, with browser and manual work last. Documentation access and execution access are different capabilities and are never reported as one. Reuse least-privilege credentials from approved secret storage, scope tools narrowly, never expose secret values to chat, repositories, configs, logs, or artifacts, and prove access with a harmless read before claiming it. Return to Allison's original objective the moment the connection is proven. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-08-26 (Estate Control Tower - Twilio Direct Access - Connection
# First Setup lane). Twilio was the acceptance fixture that proved the ladder below.
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "hold the connection before you hold the screenshot"
---

# Connection First Implementation

The failure this removes is Allison operating a vendor dashboard by hand, or pasting screenshots of one, for information and actions Claude could have read or performed directly. Every screenshot she takes of a settings page is a connection somebody declined to go get.

This skill fires on the ordinary shape of her request, not on the word "connection". Configure this. Audit that. Why is this service behaving this way. Change this setting. Build against this API. Any of those, against any external service, starts here.

It is the operational form of the access rules already in force. Access-check-first says exhaust the access you hold before asking Allison for any. Browser-last says exhaust programmatic paths before driving a browser. This skill is what those two look like when the job is an external service and the question is which door to walk through.

## The ladder

Walk it top down. Stop at the first rung that can actually do the job, and say which rung you landed on.

1. **Connected first-party tools.** Tools already live in this session, shipped by the vendor. Search the tool inventory before concluding a tool does not exist. Half of all missing-capability claims are unsearched-inventory claims.
2. **Official MCP servers and connectors.** The vendor's own hosted or published server, installed through the officially supported method for this surface. First-party beats community every time, and a community server running alongside an official one is an injection surface, not a convenience.
3. **Existing Estate integrations.** A component the Estate already owns that already holds this job. The systems map is the register of what exists. Reuse it rather than standing up a second one.
4. **The official API, SDK, or CLI.** Stable, versioned, first-party, with credentials resolved at runtime. Often the safest rung even when a flashier option exists one rung up.
5. **Browser or manual work.** Last, declared as an exception, with the reason no programmatic path exists and the failed attempt named.

A rung is only "unavailable" after a real attempt produced a real error. Report the error, never the assumption.

## Documentation access is not execution access

These are two different capabilities and collapsing them is how a lane ends up believing it can act when it can only read about acting.

A documentation server tells you what an endpoint expects. An execution path calls it against a live account. A vendor may ship one, the other, or both, and the same vendor may ship them at different maturity levels on the same day. Verify which one you actually have, name both separately when reporting, and never let a proven documentation connection stand in as proof of account access.

## Maturity is a decision input, not a footnote

Alpha, proof-of-concept, and public beta labels are evidence, not decoration. A first-party label does not by itself make something adoptable. Before adopting any execution path, establish from live evidence that its security model, credential handling, stability, and tool exposure are acceptable for the account it will touch. When a stable official path does the same job, the stable path wins even if the newer one is more interesting.

## Credentials

- Reuse the least-privilege credential that already exists in approved secret storage. The credential almost always exists already, so the question is where it is, never whether to create one.
- Resolve secrets at runtime, into the consuming process. Never into chat, a repository, a config file, a log, a command line, a generated artifact, or a session transcript. An inline secret on a command line can be persisted into a permissions allowlist and outlive every later cleanup.
- Never reach for a broader credential because it is more convenient. A root or admin token used where a scoped key would serve is a finding, not a shortcut.
- Never widen, create, or transfer permissions to make a job easier. That changes who holds access, which is Allison's call and hers alone. Reading permissions is ordinary verification and needs no approval.
- When the scoped credential genuinely lacks a permission the job requires, stop and report the exact permission by name, with the request that was refused. Do not broaden it and continue.

## Prove it with a harmless read

Access is a verified claim. Prove it with a read that changes nothing, or a test that reverses cleanly, before reporting the connection live. Then map the boundary deliberately: probe the resources the job will need and record which ones the credential correctly refuses. A refusal is a useful result and belongs in the report, because it tells Allison exactly where the ceiling is before a later lane discovers it mid-flight.

Distinguish the three failure shapes rather than lumping them:

- **Authentication or authorization refusal.** The credential is not permitted here. This is the one that may need Allison.
- **Feature not enabled on the account.** The path is correct and the product is off. Enabling it is usually a setting change and sometimes a purchase, so it is reported, never toggled.
- **Wrong path.** Your request was malformed or the resource does not exist. Fix it yourself, from the vendor's live documentation.

## Setup serves the objective and then gets out of the way

Return to what Allison actually asked for the moment the connection is proven. Connection setup is a means, and letting it become its own architecture project is the second failure mode this skill guards, right behind the screenshot.

Concretely: do not stand up a new MCP server, repository, agent, gateway, credential store, or access system when an existing Estate component or a first-party vendor mechanism already owns that job. Do not create a second source of record for something that already has one. Check for the duplicate before creating anything, and remove a redundant thing you added yourself in the same pass you discover it is redundant.

The mirror of that restraint is that a safe, high-value connection is established now, not deferred. There is no later to move it into. When establishing a connection this pass removes recurring manual work from Allison's hands, establishing it is the work, and "we can wire that up another time" is the failure phrasing.

## What the report carries

1. The knowledge connection now available, named exactly, with its maturity.
2. The execution mechanism chosen, and why it beat the alternatives that were actually considered.
3. The proof, quoting the harmless reads.
4. What Claude can now do directly, in terms of what Allison no longer has to click.
5. What still needs her authorization, one line each, with a recommendation.

## Worked example, Twilio, 2026-08-26

The acceptance fixture that produced this skill, kept because it exercises every distinction above.

Twilio ships two things with the same brand on them. The hosted server at `https://mcp.twilio.com/docs` is documentation only, needs no account and no credential, and states plainly that it does not execute API calls. It is real capability and it is not account access. The Twilio Labs execution server is first-party and carries an alpha label, so it was evaluated and set aside rather than adopted, because the stable REST API did the same job with a credential the Estate already held.

Execution therefore ran on the official REST API with an existing scoped API key resolved at runtime from approved storage, never printed and never written down. Harmless reads proved it: the phone number record and its voice routing, the verified caller IDs, recent calls, usage, balance, and the usage triggers all returned live. The boundary showed up exactly where least privilege should put it, with the account, key-list, and subaccount resources refused. One resource returned a not-found rather than a refusal, which the vendor documentation explained as a product feature switched off at the account level, so it was reported for Allison's ruling instead of being switched on.

Documentation connection, execution connection, adoption judgment, runtime credentials, proven boundary, and a reported gate that was never crossed. That is the whole shape.

## Boundaries

- This skill chooses and proves doors. It never grants, widens, or transfers access, never spends money, never mutates a production setting to demonstrate a capability, and never touches a vendor's live configuration in a lane whose job was to establish the connection.
- Read-only verification is always in bounds and never needs permission. Acting on what the verification found follows the standing gates.
- It inherits the operating-doctrine and never overrides it. Verify before speaking, automation as the standard, strongest path with reasoning, no deferral language.
