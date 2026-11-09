---
name: shadow-board
description: "Seats a board of five real, named experts on a project, decision, plan or draft. Each member scores it 0 to 100 from their own lens, the board runs one anonymous peer review and one synthesis, then produces one revised version and saves the review as a Google Doc. Use when someone says shadow board, board of advisors, score this 0 to 100, assemble the council, or get expert perspectives on this draft. Every score cites the exact words in the work that earned it. The true score always shows. Inherits operating-doctrine."
allowed-tools: []
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-11-02 (Decision Log 2026-10-29, 2026-10-31 and 2026-11-01,
# the Shadow Board rulings). Canonical home is this file. It ships only through
# the expert-partners marketplace plugin.
tier: plugin
zone: hands
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "five real experts score the work, debate it and rebuild it toward 100"
---

# Shadow Board

Five real, named experts review one piece of work. The AI runs it end to end and reports with the Doc link. No board card approval, no swap approval, no certification.

## Run it

1. Take the work and its conversation. If the input is too vague to review, ask one question with your recommendation, otherwise start.
2. Seat five real experts whose lenses differ and fit the work. Say why each belongs. Keep the same board for the life of a project. A room's appointed board (such as a Marketing Board of Directors) is seated every run, open seats filled with counterweights. A one-run swap keeps the seat's lens and just happens.
3. Each member gets the same question and the full context, and replies with a score from 0 to 100 citing the exact words that earned it, what works, what is weak, what would make it 100, a one or two sentence verdict, three key points and one watch-out. Run members as separate subagents when available, else one at a time.
4. One anonymous peer review, then one synthesis led by a neutral chair outside the five. Name the core tension, the recommendation, what would stop it and the signs it is working.
5. Produce one revised version aimed at 100 and rescore. At most three revise and rescore passes, then say plainly what holds the score down.
6. The true score always shows and is never raised. Missing inputs are listed apart from weak points.
7. Save as a native Google Doc in the owning company's brain (Claude Outputs [EP-BB], Claude outputs [AG-BB], or the matching Private folder), named [Company][Version] Title. A rerun advances the version and shows the earlier score beside the new one. Order: before and after scores, revised work, one section per member, debate, stop conditions, success signs.

Bands, no part weights: 90 to 100 Ready, 75 to 89 Solid but needs fixes, 60 to 74 Uneven, under 60 Rework the core.

A review changes only the work reviewed, never this skill. Details are in references/board-procedure.md.

## Credit

Cal and The Uncommon Business for the board and scoring moves, Carter Jensen for the generated board skill, Eliot Prince for the independent members and peer review. No course text is quoted.

Canonical home: `expert-partners-skills plugins/operating-doctrine/skills/shadow-board/SKILL.md`.
