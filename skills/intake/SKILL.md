---
name: intake
description: >
  File a session summary or any captured content into a canonical brand/project
  repo's intake/ inbox, then commit and push so the estate-brain indexes it.
  Use when the user pastes a claude.ai session summary with "/intake <project>",
  or says "intake this to <project>", "save this session to <project>", "file
  this into <repo>". Implements the ADR 0027 session-intake convention (the
  Claude Code half; the brain write tool save_to_session_intake is the claude.ai
  half, and both MUST produce identical file shape).
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Adopted into canonical 2026-08-05 (Skill Map Rulings lane, flags item 9);
# the machine copy at ~/.claude/skills is a deployed copy.
tier: user
zone: routing
status: live
subtitle: "file content into a repo intake inbox"
---

# Intake Skill

Files captured content into `<repo>/intake/` per ADR 0027, commits, and pushes.

## Project -> home/repo map

| Project keyword | Local home | GitHub repo | Branch protected? |
|---|---|---|---|
| FAM / free agent | ~/Claude/projects/FAM | ExpertPartners/fam | yes (PR) |
| Moxie (BENCHED 2026-07-30, ADR 0045: repo archived, do NOT intake; route consumer RE content to AG Luxury) | ~/Claude/projects/MoxieSignatureGroup | ExpertPartners/moxie (archived) | n/a |
| AG Luxury / luxury | ~/Claude/projects/allisongaddy-com (clone of ag-luxury) | ExpertPartners/ag-luxury | yes (PR) |
| Expert Partners / EP | ~/Claude/projects/ExpertPartners | ExpertPartners/expert-partners | yes (PR) |
| EPIC | ~/Claude/projects/EPIC | ExpertPartners/epic | no (direct) |
| AG / personal brand | ~/Claude/projects/AGPersonalBrand | ExpertPartners/ag-personal-brand | yes (PR) |
| Azulio | ~/Claude/projects/AzulioPartnership | ExpertPartners/azulio | no (direct) |
| The Strong Ones (body of work inside AG Personal Brand per ADR 0045; repo stays separate for privacy) | ~/Claude/projects/TheStrongOnes | ExpertPartners/the-strong-ones | no (direct) |
| book | ~/Claude/projects/book | ExpertPartners/book | no (direct) |
| HeyGen | ~/Claude/projects/HeyGen | ExpertPartners/heygen | no (direct) |
| PartnerSync | ~/Claude/projects/PartnerSync | ExpertPartners/partnersync | no (direct) |
| ghl / automation | ~/Claude/projects/ghl-automation | ExpertPartners/ghl-automation | no (direct) |
| Tonic / Tonic Build Studio | ~/Claude/projects/TonicBuildStudio | ExpertPartners/tonic-build-studio | no (direct) |
| Aura | ~/Claude/projects/Aura | ExpertPartners/aura | no (direct) |
| Founder Command Center / EOS | ~/Claude/projects/FounderCommandCenter | ExpertPartners/allison-founder-command-center | no (direct) |
| Email Deliverability Command Center / email deliverability | ~/Claude/projects/EmailDeliverabilityCommandCenter | ExpertPartners/email-deliverability-command-center | no (direct) |

If the project is not in this table, ask the user which home, or suggest
`/new-project` if it is genuinely new. NEVER write to ag-vault.

## Steps

1. **Parse input.** First token after `/intake` (or the named project) is the
   project. Everything after is the content body (markdown). If no body, ask
   for it or offer to capture the current conversation.

2. **Resolve the home** from the map. Confirm the local clone exists at the home
   path. If it does not, `git clone` it first (or use `gh api` to write directly).

3. **Build the file.** Path: `<home>/intake/YYYY-MM-DD-<slug>.md` where slug is a
   short kebab-case title (derive from the first heading or ask). If the file
   exists, append `-2`, `-3`, etc. Never overwrite. Prepend frontmatter EXACTLY:
   ```
   ---
   classification: internal
   classification_owner: allison
   classification_date: <today YYYY-MM-DD>
   source: claude-code
   project: <project>
   captured_at: <today, 12-hour AM/PM CDT>
   ---
   ```
   Then the body. This shape MUST match the brain's save_to_session_intake tool.

4. **Create intake/ if missing** (with a .gitkeep). 

5. **Commit + push.**
   - Unprotected repo: `git add intake/<file>` + commit (message
     `docs(intake): capture <slug> from <source>`, trailer `Push-Policy: docs`)
     + push to main.
   - Protected repo (fam/moxie/expert-partners/ag-personal-brand): create branch
     `intake/<date>-<slug>`, commit, push, open a PR.

6. **Report** the file path and the commit hash or PR URL. Note that the brain
   will index it within a few minutes.

## Rules
- Never use em dashes in any content this skill writes (org standard). Convert to
  double hyphens or commas.
- Never write outside `intake/`.
- Never touch ag-vault.
- Run the sibling-session visibility check before committing to a shared repo.
