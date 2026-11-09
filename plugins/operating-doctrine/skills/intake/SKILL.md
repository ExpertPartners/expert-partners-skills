---
name: intake
description: "Files captured content into the brain that owns it as a Google Doc and reports the link. Use when Allison pastes a session summary with /intake followed by a project name, or says intake this to PROJECT, save this session to PROJECT, or file this into BRAIN. Resolves the owner from the HQ Rulebook and the brain's index, names the Doc under Cal's file naming, searches Drive first, and keeps secrets in 1Password only. Research reports go to research-intake. Inherits operating-doctrine."
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
status: live
inherits: operating-doctrine
defers-to:
  - research-intake
brand-scope: null
subtitle: "file content into the owning brain in Drive"
---

# Intake

Retired as a gated procedure. When Allison pastes content and says intake this, save this session or file this, the AI files it as a Google Doc in the owning brain's folder and reports the link.

Mechanics that still apply

- Find the owning brain from the HQ Rulebook and the brain's `00 START HERE` index.
- Name the Doc by Cal's file naming. Search Drive first and update the existing Doc when it is the same material.
- Secrets go to 1Password only, never into a Doc.
- Research reports go to research-intake.
- If the home is truly unknowable, ask one question with a recommendation.

Decision Log 2026-11-08, Act by default, caution removed, supersedes the older intake gates.
