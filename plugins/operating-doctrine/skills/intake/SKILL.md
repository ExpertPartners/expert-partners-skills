---
name: intake
description: "Files captured content into the one brain that owns it, as a Google Doc in the folder that brain's live index names, so every surface can read it. Use when Allison pastes a session summary with /intake followed by a project name, or says intake this to PROJECT, save this session to PROJECT, or file this into BRAIN. Resolves the owner live from the HQ Rulebook and the owning brain's own index, never a frozen map. Names the Doc Cal's way, [Brand-Department][V1.0] Title, searches Drive first and never files the same capture twice, records each clear decision in the Decision Log, and never writes a secret or credential anywhere but 1Password. When the home is unclear it asks one question and files nothing until answered. Research reports go to research-intake. Inherits operating-doctrine."
allowed-tools: []
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Adopted into canonical 2026-08-05 (Skill Map Rulings lane, flags item 9) as a
# user-tier source; migrated into the marketplace 2026-11-04 (Chat to Code job,
# Audit and migrate useful standalone skill behavior into the canonical
# marketplace). Designed until HQ and Allison certify it under build-standard.
# The machine copies at ~/.claude/skills and ~/.agents/skills are deployed
# copies the owning audit retires after native verification.
tier: plugin
zone: routing
status: designed
inherits: operating-doctrine
defers-to:
  - research-intake
brand-scope: null
subtitle: "file content into the owning brain in Drive"
---

# Intake

One job. A capture that deserves to survive gets filed once, into the one brain that owns its subject, named so a person can find it, and the filing is verified before it is reported.

Provenance. This skill carries forward useful method from the user-tier intake skill adopted into canonical on 2026-08-05. The frozen project-to-brain map and the plain-title naming in that source are retired: ownership resolves live and files are named Cal's way. Business mappings live in the HQ Rulebook and the owning brain's index, never in this skill.

## Authority

Read the HQ Rulebook section Where things live and the owning brain's `00 START HERE` index, both live, every run, each found by its title in Drive. The Decision Log governs any decision the content carries. Where this skill differs from them, they win, and the newest applicable Decision Log entry wins over older text. This skill carries no project map, folder id or brain roster of its own.

If a read this skill depends on fails through every authorized route, file nothing, name the failed read, and continue only independent safe work, such as naming what must be verified. Bring Allison at most one ask, with a recommendation.

## Steps

1. **Parse input.** The first token after `/intake`, or the named project or brain, scopes the capture. Everything after is the content body. If there is no body, ask for it or offer to capture the current conversation.

2. **Resolve the owner live.** From the live Rulebook and the candidate brain's `00 START HERE` index, name the one brain that owns the subject and the folder its index names for this kind of content. Never guess a folder, and never create one; a folder the index does not name means the home is unclear. When the content genuinely fits two homes, ask Allison one question that names the two likeliest homes and file nothing until she answers. In Factory, Codex or Claude Code, never wait inside the app: post the question as a comment starting `Question for Allison` on the GitHub issue for the work, or mark the existing Chat to Code job needs-allison with one line starting `Recommend:`, and keep working on everything that does not depend on this capture.

3. **Never file twice.** Search Drive, shared drives included, for the capture's title or source id before writing. An existing filed copy is a rediscovery: report it and create nothing. A title match counts as the same capture only when it is the one candidate and holds the same content. Never overwrite an existing Doc.

4. **Build the Doc.** Name it Cal's way, `[Brand-Department][V1.0] Title`. Brand is the owning brain's tag, such as AG, EP or HQ. Department is the department word the brain's index names for this kind of content, as one whole word in title case; company-wide material uses `[Brand][V1.0] Title`. A new filing starts at V1.0. Render a colon-style subtitle with a comma, and use no em dashes. Put this header block first, then the body:
   ```
   Classification: internal
   Captured: <today YYYY-MM-DD, 12-hour AM/PM CDT>
   Source: <capturing surface>
   Project: <project or brain scope>
   ```
   A capture that holds a secret or credential is filed without it: the secret lives only in 1Password, and the flag names the path and the handling need, never the value. The original capture stays as it is; only the filed copy is redacted.

5. **Create it** with the Drive connector. If the connector refuses the write, use the service-account path (SA+DWD) impersonating allison@expertpartners.com for the same folder. Reopen the Doc from Drive to verify it landed.

6. **Record decisions.** For each clear decision Allison made in the content, add an entry at the top of the Decision Log under today's date: what was decided, why in a sentence or two, a `Replaces:` note naming the older decision it supersedes, or none, and the Doc link. A recommendation, brainstorm or question is not a decision.

7. **Report** the Doc as a clickable markdown link, its brain and folder, and whether a Decision Log entry was added. One line. If the write or the verification failed, never report the capture as filed; say what failed, the actual error, and the smallest recovery. A chat sentence is not a capture.

## Boundaries

- A research report, deep-research output or external analysis goes to research-intake, not this skill.
- A repo's own session records and continuity notes stay in their approved repository home under repo-standards and session-wrap. This skill files knowledge into a brain.
- Never write outside the owning brain's folders, and never create folders.
- Never write to ag-vault.
- Never use em dashes in anything this skill writes.

## Test cases

The outcome cases live in [tests/behavioral-cases.md](tests/behavioral-cases.md).
