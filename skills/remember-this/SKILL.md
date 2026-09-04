---
name: remember-this
description: "Turns a future obligation into a durable, self-resurfacing commitment so Allison stops carrying it mentally. Fires when she says remember this or clearly asks to preserve a follow-up, and fires on its own when an advisor notices an important non-blocking item that would cost real drift, rework, or lost leverage if forgotten but would hijack the current mission if pursued now. Resolves the owning repo LIVE, writes ONE open GitHub issue in that repo carrying a mechanical RETURN WHEN condition, refuses duplicates, verifies the write before claiming it, and reports in one short line. Proactive capture is allowed; proactive activation is not. Distinct from Lock That (which alone creates or supersedes Allison's durable authority), from pin (a lightweight current-position bookmark), from intake (evidence and working knowledge), and from operational state. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-09-04 (Immediate Pain Controls campaign, issue #15).
# Canonical home is this file. It is homed under skills/ and carried by no plugin,
# so it owes exactly one shelf, the claude.ai organization Skills upload, plus the
# aura deployed copy and that copy's Codex mirror.
tier: organization
zone: brain
status: live
subtitle: "future obligations get a durable home and a wake condition"
---

# Remember This -- v1.0 (2026-09-04)

Allison must be able to say `remember this`, or say nothing at all, and trust that the thing does not evaporate. This skill is the mechanism that earns that trust. It does not store anything itself. It routes a future obligation into the durable home that already owns it and attaches the wake condition that brings it back.

Source of record: `expert-partners-skills` issue #15, whose RETURN WHEN fired 2026-08-31.

## What this is, in one line

A future obligation gets ONE open GitHub issue in the repo that owns the work, carrying a literal `RETURN WHEN:` line, verified to exist before anyone says it was saved.

## What this is not

These four boundaries are load-bearing. Blurring any of them is the failure this skill exists to prevent.

- **Not Lock That.** Only Allison's exact `Lock that` creates or supersedes durable Estate authority, under decisions 0060 and 0061, and encountering that phrase triggers a mandatory live read of both before anything is done. Remembering an obligation never promotes a decision, never ratifies a recommendation, and never turns a candidate into canon. A captured item may say a decision is pending; it may never say a decision is made.
- **Not pin.** Pin is a lightweight bookmark of the current position between surfaces. It is a place-keeper for right now, it expires with the moment, and it is never durable memory.
- **Not intake.** Intake preserves evidence and working knowledge a cold future reader would need. Remember This preserves an ACTION still owed. Knowledge that has no action attached goes to intake, not here.
- **Not operational state.** Lane rows, board cards, and work-state records are deterministic machinery with their own contracts. A wait that already has a home in the lane ledger's waiting-on column with a named condition and a stale date is already remembered, and duplicating it here is memory spam.

## Trigger one, explicit

Allison says `remember this`, or clearly asks that a follow-up be preserved: "don't let me forget", "come back to this when X", "we need to do this after Y". Run the full flow below. No gate applies; she asked.

## Trigger two, advisor-detected

NORTH or Aura may capture an important non-blocking item without being asked. This is the half that removes Allison as the Estate's detection mechanism, and it is also the half that can flood her with junk, so it is gated hard.

Capture proactively only when ALL FIVE are true:

1. **Forgetting it creates real future cost.** Concrete drift, rework, contradiction, lost provenance, or lost leverage. Not "this was interesting".
2. **Pursuing it now would expand or hijack the current mission.** If it is a contained finding that is a natural extension of the open work, finish it now instead (operating-doctrine, clean as you go). This skill is for what genuinely must wait.
3. **A legitimate existing owner resolves live.** Not a guess, not a topic-similarity match. See owner resolution below. No owner, no capture; say so instead.
4. **A sensible RETURN WHEN can be stated.** If no condition can be named that would ever make this ripe, it is not an obligation, it is a wish.
5. **It is more than chatter.** Not a reaction, not brainstorming, not an unsupported hunch, not a restatement of something already captured.

**Proactive capture is allowed. Proactive activation is not.** Capturing an item never authorizes starting the work, opening a side discussion, spawning a lane, or re-scoping the current mission. The capture is the whole action.

If the five gates do not all clear, say nothing. Silence is the correct output for an item that does not qualify, and a mention of "I considered capturing this" is itself the noise this gate exists to remove.

## The flow, zero freedom

### 1. Resolve the owner, live

Never guess a repo from topic similarity, and never create one. Read the live estate before writing:

- Estate Brain `list_repos` and `search` for the subject, and the Estate manifest for the durable owner of that job.
- The `intake` skill's project map for the local home and GitHub repo of a named project.
- `gh api orgs/ExpertPartners/repos` when the candidate set is genuinely unclear.

The owner is the repo that owns the durable JOB, not the repo the conversation happened to be near. If the obligation is about a rule or doctrine, the owner is the repo holding that rule. If it spans several, pick the one that would have to act first, and name the others in the body.

If no existing repo can own it, that is a repo-ownership question and it goes to the `repo-standards` creation gate, which proves no existing repo can own the job before any repo is proposed. Never open the issue against a repo that does not own the work just to have somewhere to put it.

### 2. Refuse duplicates before writing

Search the resolved repo's OPEN issues for the same obligation before creating anything:

```bash
gh issue list --repo ExpertPartners/<repo> --state open --search "<distinctive terms>" --json number,title,body
```

Match on the obligation, not on wording. If an open issue already carries this obligation, do NOT create a second one. Either leave it exactly as it is, or, when this moment genuinely adds new evidence, add one comment to the existing issue and say that is what happened. One obligation, one durable entry, for its whole life.

### 3. Write it durably

Create ONE issue in the owning repo. Required shape, because the wake token is mechanical and a prose paraphrase does not fire:

```
Title: <the obligation, stated as the thing still owed>

REMEMBER THIS
OWNER: ExpertPartners/<repo>
SOURCE: <the exact surface and table or session that captured it>
CAPTURED: <YYYY-MM-DD>
WHY: <what it costs if this is forgotten, in concrete terms>

RETURN WHEN: <the mechanical condition that makes this ripe>
RETURN CONDITION STATUS: NOT FIRED
```

`RETURN WHEN:` is a literal line, spelled exactly that way, because it is the token repos are checked for when their work wakes (operating-doctrine, bias-to-action). A condition is mechanical when a reader can tell whether it has happened without judgment: a named merge, a named lane closing, a named date, a named dependency resolving. "When we have time" is not a condition.

**Never write a secret.** No key, token, password, credential, or credential-bearing material ever enters an issue body, a title, or a comment. Secrets live in 1Password only. If the obligation is about a credential, name the 1Password item reference and nothing else.

### 4. Verify before claiming

Read the issue back from GitHub after creating it, and confirm the number and the `RETURN WHEN` line are actually present:

```bash
gh issue view <n> --repo ExpertPartners/<repo> --json number,title,body,state
```

Only a successful read-back earns the receipt. A create call that returned without error is not proof; the read is.

### 5. Report, tiny

After a verified explicit capture, one short line naming what was captured and where. After a verified proactive capture, exactly this shape and nothing more:

```
Captured for later: <item>. Keep going.
```

Do not explain the routing. Do not open a side discussion. Do not ask whether she wants to talk about it. If she asks, answer then.

## Failure honesty

If the durable write cannot be made or cannot be verified, **never say it was remembered.** Chat is not a memory store, and a false receipt is worse than no capture because she will stop carrying it herself.

Say plainly, in the same turn: what the obligation is, verbatim, so it is at least on screen; that the durable write failed and the actual error; and the smallest recovery, which is normally the repo and the exact issue body ready to be created once access works. Never substitute a note in conversation and call it done. Never quietly downgrade to a lane row or a board card that the obligation does not belong in.

## Waking

A captured obligation resurfaces two ways, both already existing, neither a new watcher:

1. **On owner wake.** When work in the owning repo wakes, that repo is checked for open issues carrying `RETURN WHEN` whose condition has fired (operating-doctrine, bias-to-action; the `repo-standards` readiness path reaches the same repos).
2. **On the named condition.** When the named merge, lane close, date, or dependency actually lands, the surface that sees it lands flips `RETURN CONDITION STATUS` to `FIRED <date>` with one comment, and the obligation becomes ordinary ripe work under Decide Now.

No daemon, no sweeper, no cron, no queue, no dashboard, no second registry. If a wake mechanism does not already exist for a repo, that is a finding to report, never a reason to build one here.

## Never

- Never capture without a live-resolved owner.
- Never create a second durable entry for an obligation that already has one.
- Never create a repo, or route to a repo that does not own the work, to have a destination.
- Never promote a captured item into canon. Only Allison's exact `Lock that` does that, after the live read of decisions 0060 and 0061.
- Never write a secret into an issue.
- Never claim a capture that was not read back.
- Never turn a capture into a side quest, a lane, or a re-scope of the open mission.
- Never use em dashes in anything this skill writes.

## Canonical home and deployed copies

This skill practices ADR 0056 point 8 on itself. The canonical home is `expert-partners-skills skills/remember-this/SKILL.md`. It is homed under `skills/` and carried by no plugin, so it owes exactly one shelf, the claude.ai organization Skills upload, plus the aura deployed copy at `.claude/skills/remember-this/` and that copy's Codex mirror at `.agents/skills/remember-this/`. Deployed copies carry the DEPLOYED COPY header naming the canonical home, a version stamp, and a SHA-256 checksum manifest. `tools/skill-deploy/deploy-skill.sh` is the sole producer of deployed copies and upload zips. Hand-editing a deployed copy is a violation; fixes flow through canonical source and redeploy.
