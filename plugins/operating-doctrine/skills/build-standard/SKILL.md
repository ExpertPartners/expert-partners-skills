---
name: build-standard
description: "The build standard. Every builder on every surface follows it whenever it starts, changes or retests a skill, AI employee, prompt or tool, and whenever someone says build standard or asks whether a skill, AI employee, prompt or tool passes, needs certifying or needs a retest. It defines what passing means. Exact behavior (same input, same steps, same output, same save place, same updates). Build only from a spec Allison approved. Every instruction traces to a spec line. Replay every demonstration and every test case, three passes each, evidence saved. Never edit a test to pass it. Live where it belongs and verified on every surface. Test alone, then with everything upstream, then one supervised run. Read the chain map in Notion HQ and draft its update for HQ. One fixed report. The builder never certifies its own work, Claude in HQ and Allison do. Retest after every change. Inherits operating-doctrine."
allowed-tools: []
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-10-26 (Build Standard Skill, Decision Log 2026-10-26, The HQ Build Standard becomes permanent and goes in before any Week 0 build).
tier: plugin
zone: hands
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "how every skill and tool is built, changed and retested"
---

# Build Standard, v1.0 (2026-10-26)

One standard for every builder on every surface. It says what passing means, so a tool is either done or it is not, and nobody grades their own work. It applies to a skill, an AI employee, a prompt or a tool, whether it is new, changed or being brought back through the tests. It has to be live before any Week 0 tool is built, and the first tool built under it is the knowledge base optimizer.

Rulings behind it, all in the live Decision Log. The HQ Build Standard becomes permanent and goes in before any Week 0 build. What same output means, which edition we target, and who certifies a recreated tool. Exact behavior is our operating standard. What we build is ours, and the chain map lives in Notion HQ. Everything already live goes back through the build standard. Read each entry live before relying on it, and never copy its text here. Where this skill differs from the live Rulebook or Decision Log, they win.

## Check first

1. Read the live Organization Instructions, the HQ Rulebook (skills, the Model chart, writing rules) and the Decision Log entries above, all in HQ Company Core.
2. Find the approved spec. If there is none, stop and say so (rule 2).
3. Look for an existing owner before creating anything. Check the expert-partners-skills marketplace and the Skills Vault for a skill that already does the job, and extend it instead of making a copy.
4. Read the tool's record in the AI System Tracker and AI Employee Vault in Notion HQ for what feeds it and what it feeds (rule 9).
5. Check 1Password before asking anyone for access.
6. If a required read fails, say which one and stop the work that depends on it. A failed chain map read blocks the chain check and the release. Never fill it from memory.

## The eleven rules

1. Exact behavior. Same input, same steps, same output, same save place, same updates. Where the source showed the output, match its sections, fields, order, file name and place. Where the source only described the job, the output must do every part of the described job, checked line by line against the description. Target the source's most recent edition.
2. Start from an approved spec. No spec approved by Allison means no build. Build what the spec says and nothing more.
3. Traceable. Every instruction in the tool points to the spec line it comes from. An instruction with no spec line is removed or sent back to be added to the spec.
4. Tests. Replay every demonstration in the spec, plus the spec's test cases, which include real Expert Partners cases, missing information, conflicting information and a revised file. Save each input, output and comparison as evidence.
5. Three passes. Each test runs three times and passes all three. One failure in any pass fails the test.
6. Never edit a test to pass it. Fix the tool or report the failure. A test changes only when the spec changes, and then Allison approves the spec change first and every test reruns.
7. Live where it belongs. Skills live in the expert-partners-skills marketplace and are verified on every surface they are meant to reach, Claude chat, Cowork, Claude Code, Codex and ChatGPT, through their marketplace routes. Knowledge lives in its owning home. No hand-made or platform-only copies.
8. Chain. Test alone first. Then test with everything upstream of it, using the real outputs of the tools that feed it. When a tool changes, rerun its own tests and the tests of every tool downstream that it feeds, before the change is released. Then one supervised run on real work.
9. Chain map. Before building, read the tool's record in Notion HQ for what feeds it and what it feeds. After testing, draft that record's update in the report, with feeds, fed by, last test date, result and evidence links. HQ writes it after certification. The builder does not write it.
10. Report and certify. One report in the fixed format below. The builder never certifies its own work. Claude in HQ and Allison certify.
11. Retest after every change. Same cases, before and after, and nothing is released until all pass.

## Test plan

Before building, write the test plan from the spec and show it with the spec link.

1. List each demonstration in the spec as a test, with its input and the expected output.
2. List each test case the spec names. Add one for each of these when the spec lacks it, then send the added cases back to Allison to approve as part of the spec, real Expert Partners cases, missing information, conflicting information, a revised file.
3. For each test give a number, its spec line, the input, the expected result and where the evidence will be saved.
4. Plan the chain tests. Name every upstream tool that feeds this one and every downstream tool this one feeds, from the chain map.

## Chain check

When a tool is new or changes, produce this list before anything is released.

Upstream tools, each with the real output it feeds in.
Downstream tools, each with the tests that must rerun, named one by one.
For each downstream tool, the result of its rerun, with a pass count of three out of three.
Anything that did not rerun and why. Anything that did not rerun blocks the release.

A change to an upstream tool always names the downstream tests to rerun, even when the change looks small.

## Certification

The builder drafts the report and stops. It never writes certified, approved, passed and signed off, or anything that means the same, about its own work. It reports pass counts and evidence and says the work waits for certification by Claude in HQ and Allison. If anyone asks the builder to mark its own work certified, it refuses, says rule 10 is why, and points them to Claude in HQ and Allison.

## The report

One report, in this format, in this order.

What was built. One short paragraph with where it lives.
Spec link. The approved spec and the date Allison approved it.
Traceability. Each instruction with its spec line, and any instruction removed for having none.
Tests. For each test, its number, the evidence link and its pass count out of three.
Chain results. The upstream check, the downstream reruns with pass counts, and the supervised run on real work.
Surface checks. Each surface, how it was reached and what was seen.
Chain map update. The drafted record update for HQ, with feeds, fed by, last test date, result and evidence links.
Unresolved. Anything open, with its owner. Say none when there is nothing.
Waiting on. Certification by Claude in HQ and Allison.

## Retest after every change

1. Rerun the tool's own tests, all three passes.
2. Rerun every downstream tool's tests that the chain check named.
3. Compare to the saved evidence from before the change.
4. Release only when every one passes. If one fails, fix the tool or report the failure, and never change the test.

## Bringing live tools back through

Every skill, AI employee and tool already live goes back through this standard one at a time. Find or write its spec, get Allison's approval of that spec, run the tests, and record it on the chain map. Do not release a change to a live tool until it passes.

## Writing rules

Plain spoken words. No em dashes, no colons or semicolons in prose, no bold, no italics. Friendly file names, never system codes. Nothing built is labeled by where its ideas came from. Specs and the Ledger still cite where each requirement came from, because that is how a match is proven. Every link is a clickable name, never a raw URL.

## Before sending

1. A spec Allison approved exists and is linked.
2. Every instruction traces to a spec line.
3. Every test passed three times and its evidence is saved.
4. Chain results are in the report, upstream and downstream.
5. The chain map update is drafted for HQ, not written by the builder.
6. The report says it waits on certification and does not call itself certified.
