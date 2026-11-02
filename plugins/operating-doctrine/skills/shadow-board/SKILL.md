---
name: shadow-board
description: "Seats a board of five real, named experts on a project, decision, plan or draft. Each member scores it 0 to 100 from their own lens, the board runs one anonymous peer review and one synthesis, then produces one revised version aimed at 100 from every member and saves the finished review as a Google Doc company record. Use when someone says shadow board, board of advisors, score this 0 to 100, assemble the council, or get expert perspectives on this draft. Asks exactly one question when the input is too vague to review. Keeps the same board for the life of a project. A one-run swap keeps the seat's lens and needs the user's yes. Every score cites the exact words in the work that earned it. At most three revise and rescore passes. The true score always shows and is never raised. The skill never changes itself. Inherits operating-doctrine."
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

# Shadow Board, v1.0 (2026-11-02)

A board of five real experts reviews one piece of work. Each member scores it 0 to 100 from their own lens, the members debate, and the board produces one revised version aimed at 100 from every member. The finished review is saved as a company record.

Source. The approved spec, [HQ][V1.0] Spec - Shadow Board, and the Decision Log entries of 2026-10-29, 2026-10-31 and 2026-11-01. Read them live before relying on them. The HQ Rulebook and the Decision Log win wherever this skill differs. Never copy a Drive link or ID into this repository, because it is public.

The member brief, the reply form, the peer review, the synthesis and the Doc layout are written out in references/board-procedure.md. Use them at each step.

## 1. Input

The skill takes a project, decision, plan or draft, plus the conversation it came from.

If the input is too vague to review, ask exactly one question. That one question draws out the decision, what is at stake, the options already weighed and what has been tried. Wait for the answer, then start the review.

Clear input goes straight to the review, with no question.

## 2. The board

Choose five real, named experts whose perspectives differ and fit the work. For each one, say why they belong, the lens they bring and what they will challenge.

- By default, keep the same board for the life of that project.
- A new, unrelated task gets a newly chosen board.
- Before the skill is saved for a project, the user chooses fixed board or fresh each time. That choice is saved as the project's preference.

## 3. Swapping a member for one run

The user may swap one member for a single run.

- The stand-in keeps the seat's lens.
- The stand-in is described from their real published work.
- The stand-in is shown to the user, and the user says yes before the board meets.
- The swap is not saved into the skill. The next run seats the saved board.
- No added seats. The board is always five.

## 4. What each member is told

Every member gets the same question and the full business context, word for word, plus its own persona, meaning its name, its lens and its declared bias. No member gets a summary in place of the context.

Members run as separate subagents, launched together. None sees another's first answer. When subagents are not available, run the members one at a time, each without sight of the others, and say so in the review.

## 5. Each member's reply

Each member replies with these, in this order.

1. A score from 0 to 100.
2. What works.
3. What is weak.
4. What would make it 100.
5. A verdict of one or two sentences.
6. Three key points.
7. One watch-out.

Every score must cite the exact words in the work that earned it. A score with no cited words is not complete.

Read every score against four bands. There are no part weights.

| Score | Band |
| --- | --- |
| 90 to 100 | Ready |
| 75 to 89 | Solid but needs fixes |
| 60 to 74 | Uneven |
| Under 60 | Rework the core |

## 6. Debate

One round of anonymous peer review. Each member sees all first answers, shuffled and unlabeled, and says what it agrees with, what it pushes back on, and whether its own view shifted.

Then one synthesis. It names the core tension and keeps the differences that remain. It gives the recommendation, the conditions that would stop or reject it, and the observable signs it is working.

## 7. Revise and rescore

Produce one revised version aimed at 100 from every member. Then every member rescores it with the same reply form.

At most three revise-and-rescore passes. After the third, stop and say plainly what is holding the score down. The peer review and the synthesis are not passes.

## 8. When the score stays low

- The true score always shows. It is never raised to hit 100.
- Missing inputs the user must supply are listed separately from weak points the work still has.
- The board asks the user for the missing inputs.
- Never call it 100 unless every member scored it 100.

## 9. The finished review

The finished review is laid out in this order.

1. Before and after scores, and the biggest change.
2. The revised work.
3. One tab or section per member.
4. The debate, meaning the peer review and the synthesis.
5. Stop conditions.
6. Success signs.

## 10. Saving

The company record is a native Google Doc.

- Save it to Claude Outputs [EP-BB]. When the input came from a private file, save it to Private [EP-BB] instead. Find each folder in Google Drive by its name.
- Name it by the company rule, [Company][Version] Title.
- A rerun advances the version, keeps the earlier one, and shows the earlier score beside the new one.
- Old versions are archived in the owning brain, never deleted.
- An interactive HTML view may be offered as well, but the Google Doc is the record.

## 11. The skill never changes itself

A review changes only that piece of work or a saved preference. It never edits this skill.

The skill changes only through a deliberate rebuild that HQ and Allison certify. Updates reach every copy only through the expert-partners-skills marketplace.

## Credit

These sources are credited in plain words, and no course text is quoted.

- Cal and The Uncommon Business, for the board and scoring moves, moves 13 and 14 of their published reference sheet. The build follows these first (Decision Log 2026-10-29). Cal's own tools also settle the swap, the member brief, the scoring bands, the three passes, the honest low score, the layout and the rule that the skill never changes itself (Decision Log 2026-11-01).
- Carter Jensen, for the generated board skill, followed second. That covers the one clarifying question, a fresh board for a new task, and the choice of fixed or fresh before the skill is saved.
- Eliot Prince, for the council's independent members launched together, the anonymous peer review and the synthesis, and the verdict, key points and watch-out in each reply, used only where Cal and Carter are silent.
- HQ's addition is everything else. That includes the save home, the naming, the versions, the archive, the certification by HQ and Allison and the marketplace updates, which close by existing company rules (Decision Log 2026-10-31), and the one-at-a-time fallback when subagents are not available.

If the Week 0 browser hunt recovers Cal's or Carter's own board file, that file overrides these choices through a later certified rebuild, never through an edit made during a review.

## Canonical home

The canonical home is `expert-partners-skills plugins/operating-doctrine/skills/shadow-board/SKILL.md`. It reaches every surface only through the GitHub skills marketplace. Fixes flow through this source, never through a copy.
