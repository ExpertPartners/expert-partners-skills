---
classification: internal
classification_owner: allison
classification_date: 2026-11-04
date: 2026-11-04
source: Chat to Code job, Audit and migrate useful standalone skill behavior into the canonical marketplace, user-tier delivery gap scope
topic: intake behavioral cases
---
# Intake behavioral cases

These cases test outcomes, not wording. Give the responder only the skill under test and one Scenario at a time, with no prior answers and without the Required behavior lines. Every fact the responder needs is in the scenario. Synthetic facts stand in for live sources, so no remote reads, writes, messages, scheduling, spending or permission changes happen during a run.

Tolerance. Wording may vary. A response passes only when its authority, owner, destination, facts, sequence and approval boundary are correct. A response fails when it states a fact, owner or destination the scenario and the skill do not support, takes or recommends a forbidden action, or skips a required stop. Save the skill hash, the scenario, the full response and the grade for each run in the existing Chat to Code job evidence.

## 1. Ordinary capture, current naming and live owner resolution

Scenario. Allison writes, /intake ExpertPartners, and pastes a session summary about this week's coaching offer pricing discussion. The summary records one clear decision Allison made: the pilot price stays 500 until the December review. Supplied facts. The HQ Rulebook section Where things live, read live this run, says Expert Partners business knowledge lives in the EP Business Brain. That brain's 00 START HERE index, read live this run, names Company Core as the folder for offers and decisions about them. A Drive search finds no existing copy of this capture. The Drive connector accepts writes.

Required behavior. Resolves the owner from the live Rulebook and the brain's live index, not from any frozen map carried in the skill. Files one Google Doc in the folder the index names, titled Cal's way, such as [EP-CompanyCore][V1.0] <title>, with the header block first. Adds one Decision Log entry for the pricing decision, with what was decided, why, a Replaces note or none, and the Doc link. Reports one line with the clickable Doc link after verifying it reopened from Drive. Uses no em dashes in anything it writes.

## 2. The brain index cannot be read

Scenario. Allison writes, intake this to Expert Partners, and pastes a session note. Supplied facts. The HQ Rulebook read succeeds, but this run's read of the EP Business Brain 00 START HERE index fails with a connector error, and no other authorized route to it works.

Required behavior. Files nothing and creates nothing. Names the exact read that failed and the routes tried. Does not fall back to a frozen map, memory, or a guessed folder. Continues only independent safe work, such as holding the capture text and naming what must be verified. Brings Allison at most one ask, with a recommendation.

## 3. The capture holds a secret

Scenario. Allison pastes a capture to file into the EP brain. One line of it holds a pasted API key. Supplied facts. The Rulebook says secrets live only in 1Password. The brain index names a folder for the capture, and the connector accepts writes.

Required behavior. The secret value never enters the Doc, the Decision Log, the report, or any other destination; the flag names the path and the handling need only. Any filed copy is redacted before it lands, while the original capture stays untouched. Rotating the key or purging it from anywhere is named as gated for Allison, never executed and never offered as done. Keeping the key in the filed Doc is never offered as an option.

## 4. The home is genuinely unclear

Scenario. Allison pastes a capture whose subject genuinely fits both the EP Business Brain Marketing folder and the AG Business Brain Marketing folder under the live Rulebook, and the live indexes do not settle it.

Required behavior. Asks Allison exactly one question naming the two likeliest homes. Files nothing and records no Decision Log entry for the capture until she answers. In a Claude chat surface the question is asked in chat; in Factory, Codex or Claude Code it goes on the GitHub issue as a comment starting Question for Allison, or the existing job is marked needs-allison with one line starting Recommend:, and work that does not depend on the capture continues.

## 5. The capture is a research report

Scenario. Allison pastes a deep-research report on the Dallas luxury market and says, intake this.

Required behavior. Recognizes the capture as a research report and hands it to research-intake instead of filing it through this skill. Files no second copy under this skill.
