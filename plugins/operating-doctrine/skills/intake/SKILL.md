---
name: intake
description: "Files captured content into the one brain that owns it, as a Google Doc in the folder that brain's live index names, so every surface can read it. Use when Allison pastes a session summary with /intake followed by a project name, or says intake this to PROJECT, save this session to PROJECT, or file this into BRAIN. Resolves the owner from the live HQ Rulebook, Decision Log and owning brain's index, never a frozen map. Names the Doc under current naming and version rules, searches Drive first, distinguishes rediscovery from a proven revision, preserves known classification, records clear decisions, and never writes a secret or credential anywhere but 1Password. When the home is unclear it asks one question and files nothing until answered. Research reports go to research-intake. Inherits operating-doctrine."
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

Read Organization Instructions, the HQ Rulebook and the Decision Log, all live every run and each found by its title in Drive, before deciding ownership, naming, versions or handling. Then read the owning brain's current `00 START HERE` index and applicable living plan. Where this skill differs from them, they win, and the newest applicable Decision Log entry wins over older text. This skill carries no project map, folder id or brain roster of its own.

If a read this skill depends on fails through every authorized route, file nothing, name the failed read, and continue only independent safe work, such as naming what must be verified. Bring Allison at most one ask, with a recommendation.

## Steps

1. **Parse input.** The first token after `/intake`, or the named project or brain, scopes the capture. Everything after is the content body. If there is no body, ask for it or offer to capture the current conversation.

2. **Resolve the owner live.** From the current authority reads and the candidate brain's live `00 START HERE` index, name the one brain that owns the subject and the folder its index names for this kind of content. Never guess a folder, and never create one; a folder the index does not name means the home is unclear. When the content genuinely fits two homes, ask Allison one question that names the two likeliest homes and file nothing until she answers. In Factory, Codex or Claude Code, never wait inside the app: post the question as a comment starting `Question for Allison` on the GitHub issue for the work, or mark the existing Chat to Code job needs-allison with one line starting `Recommend:` through the supported nonterminal path, never job_finish, and keep working on everything that does not depend on this capture.

3. **Distinguish rediscovery from revision.** Search Drive, shared drives included, for the capture's source id, source link or title before writing, and read candidate contents. An identical capture already filed is a rediscovery: report its existing Doc, create nothing, archive nothing and add no duplicate decision entry. A title match alone proves neither identity nor revision. Treat changed content as a revision only when its source identity, an explicit revision relationship or current owning records establish that it replaces the earlier capture. For a proven revision, read the current version and the owning index's archive home, then apply the live naming, version and archive rules. Preserve the old version instead of overwriting or deleting it. Do not create another V1.0 or an arbitrary duplicate suffix for that revision. If the relationship or required home is unclear, resolve that uncertainty before writing rather than silently treating unrelated same-title content as a revision.

4. **Build the Doc.** Apply the current naming rules with the owning brain's brand tag and, where applicable, the department word its index names. Company Core or company-wide material uses `[Brand][Version] Title`, without inventing CompanyCore as a department. A genuinely new filing starts at V1.0; a proven revision uses the version established in step 3. Render a colon-style subtitle with a comma, use no em dashes, and follow document-formatting-standard. Preserve the capture's known classification and handling requirements rather than relabeling everything internal. If classification is unknown, resolve it from the source and current rules instead of inventing a label. Put this header block first, then the body:
   ```
   Classification: <confirmed source classification>
   Captured: <actual YYYY-MM-DD, 12-hour AM/PM and zone at that date>
   Source: <capturing surface>
   Project: <project or brain scope>
   ```
   Use the task's actual time zone and date, including daylight-saving changes, rather than a fixed CDT label. A capture that holds a secret or credential is filed without it: the secret lives only in 1Password, and the flag names the path and the handling need, never the value. The original capture stays as it is; only the filed copy is redacted. Preserve applicable privacy boundaries and existing access; intake does not change permissions to make filing work.

5. **Create and verify it** with the existing approved Drive or Docs creation route. If the connector refuses the write, use the supported service-account path (SA+DWD) impersonating allison@expertpartners.com for the same folder, where reachable under the current implementation instructions. Reopen the Doc from Drive to verify its contents, title, classification and home. For a proven revision, preserve and verify the preceding version in the existing archive home under current rules, without deleting it or inventing a folder; report the revision as complete only after that required archive step is verified.

6. **Record decisions.** For each clear, not-yet-recorded decision Allison made in the content, use the current Decision Log save process and placement, with the actual date, what was decided, why in a sentence or two, a `Replaces:` note naming the older decision it supersedes, or none, and the Doc link. Use the supported revision control to preserve other writers' changes and read the saved entry back before reporting it. If the Doc changed, reread and reconcile rather than overwriting another writer. A recommendation, brainstorm or question is not a decision, and rediscovery never adds a duplicate entry.

7. **Report** the Doc as a clickable markdown link, its brain and folder, and whether a Decision Log entry was added. One line. If the write or the verification failed, never report the capture as filed; say what failed, the actual error, and the smallest recovery. A chat sentence is not a capture.

## Boundaries

- A research report, deep-research output or external analysis goes to research-intake, not this skill.
- A repo's own session records and continuity notes stay in their approved repository home under repo-standards and session-wrap. This skill files knowledge into a brain.
- Never write outside the owning brain's folders, and never create folders.
- Never write to ag-vault.
- Never use em dashes in anything this skill writes.

## Test cases

The outcome cases live in [tests/behavioral-cases.md](tests/behavioral-cases.md).
