---
classification: internal
classification_owner: allison
classification_date: 2026-10-09
date: 2026-10-09
source: Shadow Board lane dispatch and the two hand runs recorded in aura intake
topic: behavioral acceptance rubric
---
# Behavioral cases and evidence

Run each request in behavioral-cases.json as an independent scenario in a fresh context, with the candidate skill loaded by its description so the model, not the runner, decides whether it fires. Do not show this rubric to the model under test. Build each case's fixture folder at run time from the sources named in its fixture field, and never commit fixture text to this repo. When a run pauses at the board check-in, the runner replies go once and grades the whole conversation.

| Case | Required observable behavior |
| --- | --- |
| named-board-luxury-bio | The skill fires. The board is stated before any score as exactly Neumeier, McKee, Kapferer, Kahneman and Zinsser, in that order, with no seat added, dropped or swapped, and each seat carries why it belongs, its lens and what it will challenge. A scoring frame (purpose, audience, what 100 means, constraints including the AG Luxury voice canon) is stated, then the run pauses for a go or a swap. After go there are five scores from 0 to 100, each with what works, what is weak with the line quoted, and what gets it to 100. A debate names at least one real tension between seats and settles it or hands it back. One revised third-person bio follows in full, in the voice canon read from voice.md, with no fact that is absent from bio.md or voice.md, any wanted fact held as a labeled placeholder. Scores are rerun on the revision, and any seat under 100 names its gap. The revision is saved to a file, read back and its path given before the work is called done. |
| fresh-board-sales-email | The skill fires. Five fresh seats are picked, each a real named person with published work, with five distinct lenses suited to a cold sales email (for example copy craft, persuasion or decision psychology, the sales conversation, the recipient agent's world, and clarity), and the bio board is not reused wholesale. Board and frame are stated, then the run pauses for a go or a swap. After go come five scores with specifics, a debate, and one revised email ready to send. The run says no brand voice canon was found and keeps the draft's own voice instead of inventing one. The unsupported showings claim is flagged and either cut or held as a labeled placeholder, never replaced by an invented statistic. Scores are rerun, and the revision is saved with its path given. |
| typo-does-not-trigger | The skill does not fire. The typo is fixed directly (foward becomes forward) with no board, no scores and no revision beyond the fix. |

Every case also fails on any em dash, bold, italics or horizontal divider in the output, and on any quotation invented and attributed to a real board member.

For each run, keep the model and harness used, whether the skill fired (shown by the tool call itself, not the model's say-so), the transcript or its location, and the grade against this table with any failing behavior named. That evidence goes in the lane's carry-back, never in this folder.
