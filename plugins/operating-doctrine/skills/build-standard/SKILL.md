---
name: build-standard
description: "The build standard. Every builder on every surface follows it whenever it starts, changes or retests a skill, AI employee, prompt or tool, and whenever someone says build standard. It defines what passing means. Exact behavior (same input, same steps, same output, same save place, same updates). Build from the spec, trace every instruction to a spec line, test on the real task before a change and after, save the evidence, never edit a test to pass it. Live where it belongs and working on every surface. One fixed report. Inherits operating-doctrine."
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

# Build Standard, Act by Default

One standard for every builder on every surface. It says what passing means for a skill, an AI employee, a prompt or a tool, whether new, changed or retested. Allison's brief is the go. Build it, test it, fix it, ship it, and report with links. There are no approval or certification gates (Decision Log 2026-11-08, Act by default, caution removed). Where this skill differs from the live Rulebook or newest Decision Log entry, they win.

## Before building

1. Read the spec. If there is none, write one from Allison's brief and keep going.
2. Look for an existing owner first. Check the expert-partners-skills marketplace for a skill that already does the job and extend it instead of copying it.
3. Read the tool's record in Notion HQ for what feeds it and what it feeds.
4. Get access from 1Password and other routes yourself.
5. If a read fails, use the next route. Report the gap only if every route fails.

## The rules

1. Exact behavior. Same input, same steps, same output, same save place, same updates. Where the source showed the output, match its sections, fields, order, file name and place. Where the source only described the job, do every part of the described job. Target the most recent edition and fill its silences from older ones.
2. Build what the spec says and nothing more.
3. Traceable. Every instruction points to a spec line. An instruction with no spec line is removed or added to the spec.
4. Tests. Replay every demonstration in the spec plus its test cases, including real Expert Partners cases, missing information, conflicting information and a revised file. Save each input, output and comparison as evidence. Deterministic behavior has exact pass rules. AI-written parts get a stated tolerance, and a part fails only when two of three independent judges agree it is wrong against the source. Judges run on the lowest model that can do the job. On Factory work, Factory picks the models.
5. One test before, one test after. This is Cal's way. Each test runs once on the real task before a change, to show where things stand, and once on the same task after the change, to show the change works. A test passes when its after run matches the expected result (Decision Log 2026-10-31, Testing goes back to Cal's way, one test on the real task before a change and one after). For a new tool, the before run for each test is the source's own output or the spec's demonstration of that case, and where neither shows that case, it is the expected result written in the test plan. For a live tool brought back through with no change, the graded run is one run on the real task compared with the source's output or the saved evidence. After a failure, weigh the problem, fix the tool, and retest.
6. Never edit a test to pass it. Fix the tool. A test changes only when the spec changes, and then every test reruns.
7. Live where it belongs. Skills live in the expert-partners-skills marketplace and work on every surface they are meant to reach. Knowledge lives in its owning home. No hand-made or platform-only copies.
8. Chain. Test alone, then with everything upstream using its real outputs, then one run on real work. When a tool changes, rerun its own tests and those of every tool it feeds.
9. Chain map. After testing, update the tool's record with feeds, fed by, last test date, result and evidence links.
10. Report. One report in the fixed format below.
11. Retest after every change.

## Weigh a failure, then fix it

A cosmetic problem leaves every result right and touches nothing rule 1 makes exact. Fix it, confirm once on the same task, and move on. A wrong or broken result gets the full retest: the tool's own tests, the upstream test with real upstream outputs, every downstream test, and a run on real work. Put the weighing in the report. Decide it yourself.

## Test plan

Write it from the spec. List each demonstration and test case with a number, spec line, real task, input, expected result and where before and after evidence is saved. Add real Expert Partners, missing information, conflicting information and revised file cases when the spec lacks them. Name every upstream and downstream tool from the chain map. For an AI employee, name the proving runs that let it run unattended.

## The report

Save it where the tool's work lives and link it. Fixed order.

What was built, with where it lives.
Spec link.
Traceability, each instruction with its spec line.
Tests, each with number, before and after evidence links and the after result.
Failures weighed, or none.
Chain results, upstream, downstream and the run on real work.
Surface checks, each surface and what was seen.
Chain map update.
Runs unattended, for an AI employee only.
Open items, or none.

## Bringing live tools back through

Every live skill, AI employee and tool goes back through this standard one at a time: spec, tests, chain map record.

## Writing rules

Plain spoken words. No em dashes, no colons or semicolons in prose, no bold, no italics. Friendly file names, never system codes. Every link is a clickable name, never a raw URL.
