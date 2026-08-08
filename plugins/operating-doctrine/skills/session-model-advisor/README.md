# Session Model Advisor -- plain English

## What it's for

Every Claude conversation runs on some model (Haiku, Sonnet, Opus, Fable) at some effort level (low, medium, high, xhigh, max). The right choice depends on the task -- a format-locked social post wants a smaller model at low effort, because lower effort holds tighter to narrow rules like "no em dashes." A dense financial analysis wants a bigger model at high effort. Nobody currently checks this on the way in. Allison ruled the answer in ADR 0057 (`decisions/0057-model-and-effort-operating-standard.md` in the aura repo) on 2026-08-08. This skill is what makes that ruling actually apply, turn one, every conversation, instead of sitting in a doc nobody reads before typing.

## What it does, in one sentence

At the very first message of a new conversation, before answering anything else, it checks what model/effort is running, fetches the ADR 0057 standard live, matches the task to the standard's categories, and says out loud "stay" or "switch" with one line of why.

## Why it fetches the ADR live instead of just knowing the rules

Because the rules will change. ADR 0057 says so itself -- the model names attached to its categories (Opus 5, Sonnet 5, Haiku 4.5, Fable 5 as of 2026-08-08) are a fact of the moment, not a fact for all time. If this skill had the matrix typed into it, every time the estate's model lineup shifts, someone would have to remember to come back and edit this file, and the two copies would eventually disagree without anyone noticing. Instead, this skill always goes and reads the ADR fresh. Change the ADR, and the skill's behavior changes automatically, with zero edits here.

## Why it's honest about not knowing, sometimes

Claude Code can genuinely check what model and effort are running -- there's a file on disk that records it. Claude Chat and Claude Projects (the claude.ai web/app surfaces) cannot be checked this way at all -- there's a menu next to the send button, and nothing tells the conversation itself what's selected in that menu. This skill says so plainly on those two surfaces instead of pretending to know. That's a deliberate design choice, not a bug. A wrong guess stated as fact is worse than an honest "I can't see this, tell me."

## Where the pieces live

- **This SKILL.md** -- the technical instructions, written for Claude to follow.
- **The SessionStart hook** (`reference/session-model-effort-banner.sh`, installed separately to `~/scripts/`) -- a completely separate, dumber piece. It just prints "here's the model and effort this Claude Code session is configured for" as a banner line when a session starts. It does zero judgment. This skill does all the judgment. They're kept apart on purpose so a hook glitch never quietly replaces the actual fit-check with a bare number nobody evaluated.
- **`reference/workflow-diagram.md`** -- a visual (Mermaid) walk of the same five steps described in SKILL.md, for anyone who reads better as a diagram than as prose.
- **`reference/training-walkthrough-script.md`** -- see the note below on why this isn't an actual recorded video.

## On the "training video" -- a scoped call, not a skipped step

This estate's skill standard (the four-artifact rule) calls for SKILL.md, a training video, a workflow diagram, and a README on every finished skill. The video is written for customer-facing GHL membership content, a recorded walkthrough someone outside the estate would watch to learn a process. This skill has an audience of exactly one, Allison and the Claude sessions she runs. There's no GHL membership area this belongs in, and producing an actual narrated video (technically possible via the Mira agent and HeyGen, just disproportionate for a one-viewer internal skill) would cost real production time for close to zero marginal benefit over a written walkthrough. In place of the video, `reference/training-walkthrough-script.md` is the same content a screen-recording narration would say, in the order it would say it, so if a real video is ever wanted, the script is already written. This is a scoped adaptation, named as such, not a silent gap.

## How to know it's working

Open a new conversation on any surface and send a real first message. The very first thing back should be a one-to-three-line "Model/effort check" statement, before the actual answer to whatever was asked. If that line doesn't show up, or if it makes up a Chat/Projects model reading instead of saying it can't see one, something regressed -- check `SKILL.md` Step 5's phrasing against what actually came back.
