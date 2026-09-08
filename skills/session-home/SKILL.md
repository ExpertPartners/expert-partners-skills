---
name: session-home
description: |
  Look up the correct Claude Code project home and GitHub repo for any topic, then
  output the exact cd + claude command and a first-action prompt template.
  Use BEFORE opening a new session to avoid landing in the wrong folder.
  Also handles "I'm already in the wrong folder" -- runs a lightweight closeout and
  gives the redirect steps.
  Trigger when: user asks "where should I open a new session for X", "which folder
  for X", "am I in the right folder", or starts describing work that doesn't match
  the current working directory.
argument-hint: "[topic or description of the work]"
allowed-tools: Bash, Read
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Adopted into canonical 2026-08-05 (Skill Map Rulings lane, flags item 9);
# the machine copy at ~/.claude/skills is a deployed copy.
tier: user
zone: routing
status: live
subtitle: "route work to the right project home"
---

# Session Home -- project routing

You are enforcing the session-routing doctrine so no work ends up in the wrong folder or the wrong GitHub repo.

## Routing table

Read `~/Claude/projects/Aura/doctrine/session-routing.md` first. That file is the authoritative source. The table below is a quick-reference copy; the doctrine file wins if there is any discrepancy.

| Topic | Project home | GitHub repo |
|---|---|---|
| Cross-brand strategy, ADRs, Aura doctrine | `~/Claude/projects/Aura/` | `ExpertPartners/aura` |
| AG personal brand, YouTube, speaking | `~/Claude/projects/AGPersonalBrand/` | `ExpertPartners/ag-personal-brand` |
| Free Agent Movement, Free Agent Nation, FAM keynotes, cohorts | `~/Claude/projects/FAM/` | `ExpertPartners/free-agent-nation` |
| Expert Partners, EPIC, coaching programs | `~/Claude/projects/ExpertPartners/` | `ExpertPartners/expert-partners` |
| Moxie Signature Group brand + marketing, North Dallas RE | `~/Claude/projects/MoxieSignatureGroup/` | `ExpertPartners/moxie` |
| Moxie website build + engineering (Next.js, RETS, deploys, code) | `~/Claude/projects/Moxie Website Builder Partner/` | `ExpertPartners/moxie-signature-group-website` |
| PartnerSync, GHL sync, Make.com S1-S10 | `~/Claude/projects/PartnerSync/` | `ExpertPartners/partnersync` |
| GHL automation, workflows, pipelines (ghl-automation retired 2026-09-08; reference in partnersync, executable source in partnersync-automation-backend) | `~/Claude/projects/PartnerSync/` (reference) or `~/Claude/projects/partnersync-automation-backend/` (executable) | `ExpertPartners/partnersync` / `ExpertPartners/partnersync-automation-backend` |
| Book "You've Got a Friend" manuscript | `~/Claude/projects/book/` | `ExpertPartners/youve-got-a-friend-book` |
| HeyGen avatar video | `~/Claude/projects/HeyGen/` | `ExpertPartners/heygen` |
| eXp Explained 2.0 | `~/Claude/projects/eXpExplained2/` | `ExpertPartners/exp-explained-2` |
| Azulio Partnership | `~/Claude/projects/AzulioPartnership/` | `ExpertPartners/azulio-partnership` |

## Step 1 -- Determine the correct home

If the user passed a topic as args, use it. If not, ask one short question: "What is this session going to work on?"

Match the topic against the routing table. If a topic spans multiple projects (rare), split into separate sessions or anchor in Aura only if the output is truly cross-brand doctrine.

## Step 2 -- Check current location

Run: `pwd` to get the current working directory.

Compare against the correct home. Then output one of two paths:

### Path A: Current session is already in the right place

Output:
```
You are in the right folder: <current-path>
GitHub repo: <repo>
Nothing to change.
```

### Path B: Current session is in the wrong place

Output ALL of the following:

**1. Mismatch notice:**
```
Mismatch detected:
  Current location: <cwd>
  Correct location: <correct-path>
  GitHub repo:      <repo>
```

**2. Steps to fix (in order):**
```
1. Run /session-closeout in this session first (captures everything in an archive note).
2. Then open a new terminal and run:

   cd <correct-path> && claude

3. Paste this as your first message in the new session:

   Read session-state.md and working/ for current context.
   We're continuing <topic> from a session that was misrouted to <wrong-path>.
   The closeout note is at <wrong-path>/archive/session-<name>-closeout-YYYY-MM-DD.md.
   [Describe the first action you want done here.]
```

**3. Why this matters:**
Explain briefly: work committed in the wrong folder goes into the wrong GitHub repo. Doctrine, ADRs, and project-knowledge files in the wrong place break the cross-brain sync chain (Ember, Aura, Cowork).

## Step 3 -- Pre-session routing (before any work starts)

If the user is asking this BEFORE opening a new session (most common case), output:

```
Project home:  <correct-path>
GitHub repo:   <repo>
Command:       cd <correct-path> && claude

First message to paste when Claude Code loads:
-----
Read session-state.md. I'm starting a new session on [topic].
First action: [describe it here].
-----
```

Keep the output tight. No explanation beyond what is listed above.

## Edge cases

- **Aura as default (wrong):** If someone opens Aura for per-project work because "Aura is the main project," that is a routing error. Aura is only correct for cross-brand advisory and doctrine work.
- **"I don't know where this belongs":** Apply the borderline-case rules from the doctrine file. When genuinely ambiguous (new project type never seen before), default to Aura temporarily AND note it as a routing decision to formalize in the doctrine file.
- **New project with no existing folder:** Check `gh repo list ExpertPartners` to see if a repo exists. If not, this needs an ADR before creating new repos. Flag it; do not create folders or repos on the fly.
