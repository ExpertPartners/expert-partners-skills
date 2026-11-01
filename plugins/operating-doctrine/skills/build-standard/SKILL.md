---
name: build-standard
description: "The build standard. Every builder on every surface follows it whenever it starts, changes or retests a skill, AI employee, prompt or tool, and whenever someone says build standard or asks whether a skill, AI employee, prompt or tool passes, needs certifying or needs a retest. It defines what passing means. Exact behavior (same input, same steps, same output, same save place, same updates). Build only from a spec Allison approved. Every instruction traces to a spec line. Test Cal's way, one test on the real task before a change and one after, evidence saved. When a test fails, weigh the problem before retesting. Never edit a test to pass it. Live where it belongs and verified on every surface. Test alone, then with everything upstream, then one supervised run. Read the chain map in Notion HQ and draft its update for HQ. One fixed report. The builder never certifies its own work, Claude in HQ and Allison do. Retest after every change. Inherits operating-doctrine."
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

# Build Standard, v1.2 (2026-11-01)

One standard for every builder on every surface. It says what passing means, so a tool is either done or it is not, and nobody grades their own work. It applies to a skill, an AI employee, a prompt or a tool, whether it is new, changed or being brought back through the tests. It has to be live before any Week 0 tool is built, and the first tool built under it is the knowledge base optimizer.

Rulings behind it, all in the live Decision Log. The HQ Build Standard becomes permanent and goes in before any Week 0 build. What same output means, which edition we target, and who certifies a recreated tool. When Cal's team has more than one version of a tool, we copy the most recent one we can see and fill its silences from the older ones. Every build carries four cost and quality rules. The October 31 ruling that ends build price estimates and the dollar wait line, anywhere, replaces that entry's spending line. Testing goes back to Cal's way, one test on the real task before a change and one after. Factory picks and manages the models on Factory work. Exact behavior is our operating standard. What we build is ours, and the chain map lives in Notion HQ. Everything already live goes back through the build standard. Read each entry live before relying on it, and never copy its text here. Where this skill differs from the live Rulebook or Decision Log, they win.

## Check first

1. Read the live Organization Instructions, the HQ Rulebook (skills, the Model chart, writing rules) and the Decision Log entries above, all in HQ Company Core.
2. Find the approved spec. If there is none, stop and say so (rule 2).
3. Look for an existing owner before creating anything. Check the expert-partners-skills marketplace and the Skills Vault for a skill that already does the job, and extend it instead of making a copy.
4. Read the tool's record in the AI System Tracker and AI Employee Vault in Notion HQ for what feeds it and what it feeds (rule 9). HQ starts a tool's record in the AI Employee Vault the day Allison approves its spec, so a record should already be there.
5. Check 1Password before asking anyone for access.
6. If a required read fails, say which one and stop the work that depends on it. A failed chain map read blocks the chain check and the release. Never fill it from memory. A missing tool record is different. Report it and continue from the spec's stated chain, and the chain check and release stay blocked until HQ adds the record.

## The eleven rules

1. Exact behavior. Same input, same steps, same output, same save place, same updates. Where the source showed the output, match its sections, fields, order, file name and place. Where the source only described the job, the output must do every part of the described job, checked line by line against the description. Target the source's most recent edition. Where the most recent version is silent, fill the gap from the older versions (Decision Log 2026-10-29, When Cal's team has more than one version of a tool, we copy the most recent one we can see and fill its silences from the older ones).
2. Start from an approved spec. No spec approved by Allison means no build. Build what the spec says and nothing more.
3. Traceable. Every instruction in the tool points to the spec line it comes from. An instruction with no spec line is removed or sent back to be added to the spec.
4. Tests. Replay every demonstration in the spec, plus the spec's test cases, which include real Expert Partners cases, missing information, conflicting information and a revised file. Save each input, output and comparison as evidence. Deterministic behavior keeps exact pass rules. AI-written parts of a tool's output get a stated tolerance in the test plan. A part fails only when two of three independent judges agree it is wrong against the source, meaning a wrong name, number, spelling, attribution or order, or a claim the source does not make. A lone judge's refutation or a wording note is logged in the report and fixed in the next version. Judges run on the lowest model that can do the job, per the Model chart in the HQ Rulebook, not the tool's own model (Decision Log 2026-10-30, Every build carries four cost and quality rules). On Factory work, Factory picks the models (Decision Log 2026-10-31, Factory picks and manages the models on Factory work).
5. One test before, one test after. This is Cal's way. Each test runs once on the real task before a change, to show where things stand, and once on the same task after the change, to show the change works. A test passes when its after run matches the expected result. For a new tool, the before run is the source's own output or the spec's demonstration. After any failed test, the builder stops and reports in the existing Chat to Code job before spending more, and weighs the problem before any retest (Decision Log 2026-10-31, Testing goes back to Cal's way, one test on the real task before a change and one after).
6. Never edit a test to pass it. Fix the tool or report the failure. A test changes only when the spec changes, and then Allison approves the spec change first and every test reruns.
7. Live where it belongs. Skills live in the expert-partners-skills marketplace and are verified on every surface they are meant to reach, Claude chat, Claude Code, Codex and ChatGPT, through their marketplace routes. Cowork is now part of Claude. Knowledge lives in its owning home. No hand-made or platform-only copies.
8. Chain. Test alone first. Then test with everything upstream of it, using the real outputs of the tools that feed it. When a tool changes, rerun its own tests and the tests of every tool downstream that it feeds, before the change is released. Then one supervised run on real work.
9. Chain map. Before building, read the tool's record in Notion HQ for what feeds it and what it feeds. HQ starts that record the day Allison approves the spec. If it is missing, report it and continue from the spec's stated chain, and release stays blocked until HQ adds it. After testing, draft that record's update in the report, with feeds, fed by, last test date, result and evidence links. HQ writes it after certification. The builder does not write it.
10. Report and certify. One report in the fixed format below. The builder never certifies its own work. Claude in HQ and Allison certify.
11. Retest after every change. The same cases, one test on the real task before the change and one after, and nothing is released until every after run passes. When a test fails, weigh the problem first, as the next section says.

## Weigh the problem before retesting

When a test fails, the builder does not rerun everything by reflex. It first writes down what broke, how bad it is and what it affects, and sets that against the time and cost of retesting.

1. A cosmetic problem, such as a layout slip, a heading or a wording note that leaves every result right, gets fixed and confirmed once on the same task, and the build moves on. The tool is watched on its first real jobs.
2. A wrong or broken result, such as a wrong name, number, step, save place or update, or a missing part of the job, gets the full retest. That means the tool's own tests and every downstream test the chain check names, before and after.
3. Allison sees the weighing before anything is skipped. The builder logs it in the Chat to Code job list and waits for her before treating any problem as cosmetic.

The weighing and Allison's answer go in the report.

## Test plan

Before building, write the test plan from the spec and show it with the spec link.

1. List each demonstration in the spec as a test, with its input and the expected output.
2. List each test case the spec names. Add one for each of these when the spec lacks it, then send the added cases back to Allison to approve as part of the spec, real Expert Partners cases, missing information, conflicting information, a revised file.
3. For each test give a number, its spec line, the real task it runs on, the input, the expected result and where the before and after evidence will be saved.
4. Plan the chain tests. Name every upstream tool that feeds this one and every downstream tool this one feeds, from the chain map.

## Chain check

When a tool is new or changes, produce this list before anything is released.

Upstream tools, each with the real output it feeds in.
Downstream tools, each with the tests that must rerun, named one by one.
For each downstream tool, the result of its rerun, before and after.
Anything that did not rerun and why. Anything that did not rerun blocks the release.

A change to an upstream tool always names the downstream tests to rerun, even when the change looks small.

## Certification

The builder drafts the report and stops. It never writes certified, approved, passed and signed off, or anything that means the same, about its own work. It reports results and evidence and says the work waits for certification by Claude in HQ and Allison. If anyone asks the builder to mark its own work certified, it refuses, says rule 10 is why, and points them to Claude in HQ and Allison.

## The report

One report, in this format, in this order.

What was built. One short paragraph with where it lives.
Spec link. The approved spec and the date Allison approved it.
Traceability. Each instruction with its spec line, and any instruction removed for having none.
Tests. For each test, its number, the before and after evidence links and the after result, with every logged single-judge and wording note.
Failures weighed. For each failed test, what broke, how bad it is, what it affects, cosmetic or wrong or broken, and Allison's answer. Say none when nothing failed.
Chain results. The upstream check, the downstream reruns with their before and after results, and the supervised run on real work.
Surface checks. Each surface, how it was reached and what was seen.
Chain map update. The drafted record update for HQ, with feeds, fed by, last test date, result and evidence links.
Unresolved. Anything open, with its owner. Say none when there is nothing.
Waiting on. Certification by Claude in HQ and Allison.

## Retest after every change

1. Before the change, run each of the tool's own tests once on the real task and save the result.
2. After the change, run each of them once more on the same task.
3. Rerun every downstream tool's tests that the chain check named, before and after.
4. Compare each after run to its before run and to the saved evidence.
5. If one fails, weigh the problem first. A cosmetic problem is fixed and confirmed once. A wrong or broken result gets the full retest. Never change the test.
6. Release only when every after run passes, or Allison has seen the weighing and agreed the problem is cosmetic and fixed.

## Bringing live tools back through

Every skill, AI employee and tool already live goes back through this standard one at a time. Find or write its spec, get Allison's approval of that spec, run the tests, and record it on the chain map. Do not release a change to a live tool until it passes.

## Writing rules

Plain spoken words. No em dashes, no colons or semicolons in prose, no bold, no italics. Friendly file names, never system codes. Nothing built is labeled by where its ideas came from. Specs and the Ledger still cite where each requirement came from, because that is how a match is proven. Every link is a clickable name, never a raw URL.

## Before sending

1. A spec Allison approved exists and is linked.
2. Every instruction traces to a spec line.
3. Every test ran once on the real task before the change and once after, and its evidence is saved.
4. Every failed test was weighed, Allison saw the weighing before anything was skipped, and the weighing is in the report.
5. Chain results are in the report, upstream and downstream.
6. The chain map update is drafted for HQ, not written by the builder.
7. The report says it waits on certification and does not call itself certified.
