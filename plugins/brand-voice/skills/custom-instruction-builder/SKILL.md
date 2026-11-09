---
name: custom-instruction-builder
description: "Build or audit marketing workspace custom instructions from current company knowledge and authentic voice evidence. Use for Custom Instruction Builder, workspace setup, or improving marketing project instructions. Produces a concise downloadable Markdown file without changing live settings."
tier: plugin
zone: brands
status: live
inherits: operating-doctrine
brand-scope: null
requires:
  - brand-voice
feeds:
  - brand-guardian
subtitle: "evidence-grounded marketing workspace instructions"
---

# Custom Instruction Builder

This is an independently written implementation of recovered Week 2 marketing behavior, not Cal's original prompt. Other departments' full contracts remain unrecovered. Do not claim this marketing template reproduces sales, operations, hiring or finance editions.

## Resolve and read

Resolve company, speaker, audience register, destination workspace and intended task from the request. Use `brand-voice` to retrieve current HQ authority, Shared Writing Rules and the selected Company Core canon. Read the existing workspace instructions before proposing a replacement. Preserve approved instructions and calibrated voice unless the requested change and current evidence justify a specific edit.

Read every supplied workspace file in full, including remaining pages or truncated responses. Keep a separate source report listing revision, approval state, read coverage and conflicts. A search snippet is not a full read. Missing or unreadable mission, audience or voice evidence blocks only the corresponding finished instruction draft. Return a bounded missing-input report, not invented facts or a paste-ready document with placeholders.

Resolve authority, date, audience scope and explicit supersession before using any clause. Current retrieval does not make every sentence current. Preserve applicable founder decisions over stale profile prompts, prices, punctuation and identity labels. Keep the disposition outside the paste-ready output.

Use the existing four foundation files and approved voice summary when available. Reuse a calibrated guide rather than demanding fresh extraction. Review-only drafts, historical prices, unattributed endorsements and internal targets never become approved public claims. Select the relevant audience and speaker, never blend companies or founders.

## Draft

Create `marketing-workspace-custom-instructions.md`, at most 1,000 words, with these level-two headings in exactly this order.

1. `ROLE & MISSION`
2. `ICP`
3. `VOICE`
4. `THINKING & STRATEGY PROTOCOL`
5. `KNOWLEDGE BASE`
6. `GROUND RULES`
7. `FINAL CHECK BEFORE DELIVERING`

Use `### Always Do` and `### Never Do` within GROUND RULES.

ROLE & MISSION identifies the in-house marketing thinking partner and a supported one-sentence mission. ICP summarizes the selected audience, without inventing a persona or combining distinct audiences.

VOICE is 80 to 120 words. Describe the supported voice, rhythm, opening and closing behavior, specific vocabulary and contextual exclusions. Quote only short authentic signature vocabulary supported by the selected person's sources. Do not convert absence in a small sample into a universal ban. Follow approved calibration when it differs from tentative inference.

THINKING & STRATEGY PROTOCOL gives complex work a concise objective, assumptions, risks and success criteria. Identify substantive unknowns and challenge weak angles directly. Under current HQ autonomy, resolve retrievable inputs and proceed within the brief. Ask only a genuine unresolved business question, one at a time. Do not transplant the historical three-to-five-question or routine plan-approval gate.

KNOWLEDGE BASE contains generic guidance to read the workspace knowledge fully, follow current authority and verify claims. No filenames, document titles, links or file inventory anywhere in the paste-ready output. Keep provenance in the separate report.

GROUND RULES carries current writing rules, factual accuracy, audience boundaries and specific observed business or voice constraints. Do not add unsupported company policy. For work longer than 200 words, keep the recovered editorial review of three weaknesses and one suggested change in a separate internal review, never appended to public copy.

FINAL CHECK BEFORE DELIVERING checks audience usefulness, source-supported facts, authentic voice and weak or generic sentences. Revise before delivery. Self-scoring is not independent acceptance or proof of performance.

## Deliver and preserve

Attempt downloadable file creation first. If that surface cannot create files, return the complete instructions in one Markdown code block. Do not split the paste-ready content across blocks. Keep the source report outside the artifact.

Run `python3 scripts/validate_instructions.py /absolute/path/marketing-workspace-custom-instructions.md` from this skill directory when Python is available. Otherwise perform the same heading, word-count and inventory checks directly. This checks structure, not factual truth or voice quality. Run `brand-guardian` against the same current sources for those judgments.

Save a new candidate in the owning company's existing output home, using current naming and document delivery standards. Return a link whose text is the exact document name. Do not overwrite an approved master or change live workspace settings unless that is in the brief. If asked to install instructions, preserve the prior value, change only the selected workspace, and distinguish generated, saved and active states in the receipt.

Record the knowledge owner, source revisions and update trigger separately. For static snapshots, use the recovered 30-day review plus corrections when source facts change. Do not claim dependable cross-user live sync. Do not create a scheduler as part of generation.
