---
name: intake
description: >
  File a session summary or any captured content into the owning brain's home folder in
  Google Drive as a Google Doc, so every surface can read it. Use when the user pastes a
  claude.ai session summary with /intake followed by a project name, or says "intake this to
  PROJECT", "save this session to PROJECT", "file this into BRAIN". Replaces the old repo
  intake/ inbox. Any decision inside the content also gets a Decision Log entry.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Adopted into canonical 2026-08-05 (Skill Map Rulings lane, flags item 9);
# the machine copy at ~/.claude/skills is a deployed copy.
tier: user
zone: routing
status: live
subtitle: "file content into the owning brain in Drive"
---

# Intake Skill

Files captured content as a Google Doc in the owning brain's home folder in Drive.
Decisions inside it go to the Decision Log.

## Project -> brain map

| Project keyword | Brain |
|---|---|
| FAM / free agent / Free Agent Nation | EP Business Brain |
| Moxie (BENCHED 2026-07-30, ADR 0045: do NOT intake; route consumer RE content to AG Luxury) | none |
| AG Luxury / luxury | AG Business Brain |
| Expert Partners / EP | EP Business Brain |
| EPIC | EP Business Brain |
| AG / personal brand | EP Business Brain for the industry side, AG Business Brain for the consumer side |
| Anything shared by both companies | HQ Business Brain, Company Core [HQ-BB] (folder `1Za4sU2YQ3UP2E-ujxVNtvH-2sQ-zndjw`) |

Azulio, The Strong Ones, book / You've Got a Friend, HeyGen, PartnerSync, Tonic,
Aura, Founder Command Center / EOS, and Email Deliverability have no brain assigned
in the Business Brain spec yet. Ask which brain. If the project is not in this table,
ask, or suggest `/new-project` if it is genuinely new. NEVER write to ag-vault.

## Steps

1. **Parse input.** First token after `/intake` (or the named project) is the
   project. Everything after is the content body (markdown). If no body, ask
   for it or offer to capture the current conversation.

2. **Resolve the brain** from the map. Open that brain's `00 START HERE` Doc
   through the Drive connector and file into the folder it names for this kind
   of content.

3. **Build the Doc.** Plain title, no date prefix. If the title exists, add
   `-2`, `-3`. Never overwrite. Put this header block first:
   ```
   Classification: internal
   Captured: <today YYYY-MM-DD, 12-hour AM/PM CDT>
   Source: claude-code
   Project: <project>
   ```
   Then the body.

4. **Create it** with the Google Docs or Drive connector. If the connector
   refuses the write, use the service-account path (SA+DWD) for the same
   folder. Open the Doc from Drive to verify it landed.

5. **Record decisions.** For each clear decision in the content, add an entry at
   the top of the Decision Log (Google Doc `1ausL1HV3ns3VMZH86jD8zjWnAKSQ3DaUfFzkiwR1qWc`)
   under today's date: what was decided, why in a sentence or two, a `Replaces:`
   note naming the older decision it supersedes (or none), and the Doc link.

6. **Report** the Doc as a markdown link, plus a note if a Decision Log entry was added.

## Rules
- Never use em dashes in any content this skill writes (org standard). Convert to
  double hyphens or commas.
- Never write outside the brains' folders.
- Never touch ag-vault.
