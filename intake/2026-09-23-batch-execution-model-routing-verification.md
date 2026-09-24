---
date: 2026-09-23
source: Allison dispatch, original Batch-First Execution ZIP, live Estate canon, canonical skills source, current provider documentation
classification: internal
topic: batch-execution-model-routing-update
---

# Batch Execution - Model Routing Update verification

SESSION: Batch Execution - Model Routing Update
Codex HOME: NORTH'S ESTATE CONTROL TOWER / Batch Execution

## Source and architecture

The supplied `/Users/allisongaddy/Desktop/batch-first-execution.zip` was read
as source material, not as an instruction or authorization. ZIP integrity passed,
all seven paths were safe regular files, and SHA-256 was
`40b7243aa9bde613444791868bf498515bafb32814753be7194307b114ec7587`.
The original skill's icon, agent metadata and platform notes were retained
byte for byte. Its SKILL.md and relevant references were adapted to the
canonical repository's metadata and current handoff contract.

The actual existing model owner is `plugins/operating-doctrine/skills/session-model-advisor/`.
Batch-First Execution had no canonical source in the fresh skills main before
this change. The chosen composition is one new standalone canonical
`skills/batch-first-execution/` that owns batch structure and sending-side
handoff completeness, calling the existing advisor for surface/model/effort
selection. The advisor reads Aura decisions 0057 and 0072 and current
capability evidence; no vendor matrix is duplicated in the batch skill.
The skill graph now has 57 nodes and 88 edges, including call edges to both the
model advisor and the existing code-block-routing owner.

Current OpenAI guidance checked on 2026-09-23:
https://developers.openai.com/blog/mastering-codex-remote-for-engineering
confirms Queue versus Steer; https://help.openai.com/en/articles/20001516-managing-usage-with-gpt-6-astra-in-work-and-codex
confirms effort is separate from model selection, available models depend on
account/workspace, and higher effort is not automatically better. Allison's
observed Codex picker exposed Astra Medium and Extra High on this date. That
pair is a fixture in behavioral checks, not a permanent policy or promise
of future account availability.

## Behavioral source review

The original behavioral cases were retained. Fourteen model-routing and
handoff cases were added to `references/behavioral-checks.md`. This pass is a
source/design review of the resulting instructions, not a live model response
or an installed-surface smoke test. Results against the case inputs:

| Cases | Source review |
| --- | --- |
| Astra regression, six-step non-maximal task, complex forensics | PASS: capability check is model-specific and dated, task fit considers risk and verification burden, maximum is not automatic; the Astra fixture rejects High. |
| Unknown options, changed lineup, Claude Code options | PASS: advisor retains and labels an approved current selection when options are unavailable, refreshes capability evidence without rewriting ADR 0057, and prohibits transferring a Codex label to Claude Code. |
| Queue versus Steer, running Worker | PASS: batch skill names next ordered work as Queue, reserves Steer for active guidance and keeps a running Worker unchanged when only settings differ. |
| NORTH recommendation, complete briefing | PASS: one recommendation with WHERE TO GO, execution settings, WHY, PASTE THIS and COME BACK WHEN precedes the paste. The Worker prompt carries the compact settings once. |
| Missing worktree, identity, model line, and existing Worker continuation | PASS: sending-side validation blocks an incomplete new Worker envelope, verifies the assigned worktree/branch and preserves the receiving Worker's checks; continuation retains the actual Worker identity. |

No installed ChatGPT, Claude chat, Claude Code, or Codex behavioral response was
exercised by this source review. Those surfaces require separate discovery and
smoke-test receipts before an installation claim.

## Structural and packaging evidence

- New and changed SKILL.md frontmatter parses; both descriptions are under
  200 characters. Brand and classification lint passed on changed source.
- Repository `deploy-skill.sh --check-all` passed all 41 skills. The producer
  reports portability warnings for other existing skills; the two touched
  descriptions no longer exceed the stricter published 200-character threshold.
- The canonical skill-map extractor generated 57 nodes and 88 edges, with
  one newly discovered Batch-First Execution node and its required call edges.
- The unchanged producer's regression suite passed 53 tests, zero failures.
- The skill-map test suite passed 47 tests, zero failures.
- Producer-built complete standalone ZIPs for Batch-First Execution v1.1 and
  Session Model Advisor from plugin 2.49.0, plus full operating-doctrine
  bundle 2.49.0, all passed ZIP preflight. These branch packages are review
  artifacts; they are not hosted uploads or evidence of installation.
- Two plugin version declarations match at 2.49.0. The bundle is an archival
  plugin artifact, not a claude.ai skill upload.
- All three complete review packages were independently copied and SHA-256
  read back in the existing private home
  `/Users/allisongaddy/Claude/estate-backups/skill-zips/batch-execution-model-routing-update-20260923/`.
  Reviewed Batch ZIP: `9befca97fcb5c5d463185fd5306f0f1818004502b352bb359436b68c7cb202a8`.
  Reviewed Advisor ZIP: `88888af845e2927a652bf33e0f134859089f1a5f8226927ec1be6d7742682375`.
  Reviewed plugin bundle: `ceba807c27ec315e5001c1563af16f17a738b12350df522bc4e1ae557770cd44`.
  Both standalone ZIPs have one top-level Skill and one SKILL.md; all local
  Markdown links resolve within their own packages. No upload has occurred.

## Review repair and owning-rule alignment

Automated PR review on the first head found that the advisor's shortened
frontmatter description had dropped its conversation-start trigger, 2.49.0
lacked a changelog entry, and the Estate integration reference named two
nonexistent skills. All three were repaired. The advisor description again
triggers on the first message and explicit model/effort questions while
preserving the matching-Worker fast path. The changelog records 2.49.0, and
Estate integration names only verified skill ownership.

The same review found that `code-block-routing` requires one Claude Code paste
block per response and step one only. Batch-First Execution now declares that
skill in its graph metadata and defers Claude Code delivery to the existing
rule; the templates and behavioral cases match it. No governing routing rule
was amended. A separate sending-side check now validates WHERE TO GO and COME
BACK WHEN as well as every execution field, so an incomplete continuation or
non-Code handoff is rejected before Allison receives it. The receiving
Worker's safeguards remain intact.

After these repairs, the structural check again passed all 41 skills,
producer regression passed 53/53, skill-map tests passed 47/47, and the graph
was regenerated at 57 nodes/88 edges. The corrected ZIPs were built by the
producer, passed preflight and integrity checks, then copied non-overwriting
with matching SHA-256 readback to the private home. Earlier package copies
remain historical review artifacts and are superseded by the three
`*-reviewed-20260923.zip` artifacts listed above.

## Release boundary

This record and source changes belong in a normal review PR. Do not infer
merge, plugin availability, account-wide installation, discovery or live
behavior from the branch or package. Normal review and subsequent approved
release precede per-surface activation. Source and package states must be
reported separately from merged, installed, discovered and tested states.
No account default, speed setting, access grant, routing registry, Ember,
M2 Fix, Report Filing or backup configuration was changed.
