# Session Model Advisor -- training walkthrough script

Substitute for artifact 2 of the four-artifact rule (the "training video"). See README.md, "On the training video," for why this is a written script rather than a recording -- the four-artifact rule's video is written for customer-facing GHL membership content, this skill has an audience of one, and recording a real narrated video (technically possible via Mira/HeyGen) would be disproportionate production cost for the marginal benefit over this document. If a real recording is ever wanted, this is the shot-by-shot narration to record it from, no re-drafting needed.

---

**[Scene -- a fresh Claude Code terminal, session just started]**

"Here's what happens the moment a new conversation opens, on any of the three surfaces this skill covers -- Claude Chat, Claude Projects, or Claude Code. I'm going to show Claude Code first, because it's the one where you can actually see the machinery.

**[Type a first message -- "Draft three Instagram captions for the EPIC brand, no em dashes, format-locked."]**

Watch the very first thing that comes back, before the captions themselves. There's a one-line check, 'Model/effort check, staying on Sonnet 5 at low -- this reads as fast iterative drafting and voice-constrained work, which calls for this level. Proceeding.' That line is the whole point of this skill. It didn't answer the caption request yet. It checked whether the model and effort it's about to answer with are actually the right ones for this kind of task, according to ADR 0057, and it said so out loud first.

**[Cut to a second example -- "Build me a full financial model reconciling three years of P&L data."]**

Same opening move, different verdict. 'Model/effort check, this reads as dense analytical reasoning, which the standard puts at Opus 5, high effort. You're currently on Sonnet 5 at low. Recommend switching before I continue.' Notice it didn't just silently do the work anyway at the wrong level -- it stopped and named the mismatch, because a wrong model choice on dense work is a worse failure than a few seconds of friction asking to switch.

**[Cut to -- 'Where did that come from?']**

Here's the part that doesn't show on screen but matters most, that categorization, 'fast iterative drafting,' 'dense analytical reasoning,' isn't memorized. Every single time this fires, it goes and reads the Model chart in the HQ Rulebook fresh, live, from Drive. If Allison changes the standard tomorrow, a new model comes out, a category gets redefined, this skill's behavior changes with it, automatically, with nobody touching this skill's own file. That's deliberate. A copy of the rules baked into the skill would drift the first time the real rules changed and nobody would notice until the two disagreed.

**[Cut to a claude.ai Project, a plain browser tab]**

Now the honest part. Same skill, same first-message trigger, but on claude.ai there's no way for the conversation to see what model or effort is actually selected in the UI. That control lives in a menu next to the send button, and nothing about it is exposed back to the conversation. So instead of guessing, the line reads, 'Model/effort check, I can't read your current selection on this surface. Based on the task, ADR 0057 calls for Opus 5 at high. If that's not what's selected, switch via the model menu before I continue.' That's not a weaker version of the same feature -- it's the same discipline applied to a surface that genuinely can't be introspected. Never guess and call it a fact.

**[Closing]**

One check, three surfaces, one line before anything else happens, and a standard it reads fresh every time instead of memorizing. That's the whole skill."
