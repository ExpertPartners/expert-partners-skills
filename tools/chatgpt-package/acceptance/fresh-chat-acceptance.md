---
classification: internal
---

# Fresh-chat acceptance, estate-knowledge-retrieval on ChatGPT

The machine half of acceptance is settled by
`tools/chatgpt-package/test_build_chatgpt_plugin.py`, which proves the package
is spec-clean, correctly shaped, and that no positive prompt below contains a
magic word.

This file is the half a machine cannot settle. No API reaches Allison's
ChatGPT chat surface, so whether ChatGPT actually fires the skill and retrieves
in a brand-new conversation is run by hand, against the rubrics here. Nothing
in this file may be reported as passing on the test script's word.

Every prompt below is run in a **brand-new ChatGPT conversation**, with no
project context, no custom instructions steering it, and no hint to look
anything up.

## Before running

1. **Plan.** Skills are available to ChatGPT Business, Enterprise, Healthcare,
   and Edu. Free, Plus, and Pro are named nowhere in OpenAI's skills articles.
   Verify the account tier first; if skills do not appear, this is the first
   thing to check.
2. **Install as a plugin, not as a standalone skill.** A standalone skill
   reaches only the ChatGPT desktop app, Codex CLI, and the IDE extension. Only
   plugin-bundled skills reach ChatGPT on the web and mobile. The artifact
   built here is a plugin for exactly that reason.
3. **The Estate Brain app must be connected** in the account being tested. The
   door is already registered (Cognito client `chatgpt-estate-control-tower`,
   read-only, six tools). The skill supplies the workflow; the app supplies the
   tools. Neither works alone.
4. **App permission.** ChatGPT's default is Important actions, which reads from
   apps automatically and asks only before actions with outside effect. If the
   account is set to Always ask, reads will prompt and test 1 will look like a
   failure that is really a settings artifact.

## Install steps

Verified live 2026-09-03 against help.openai.com and developers.openai.com.

1. In the ChatGPT sidebar, select **Plugins**.
2. In the Plugin Directory, select the **Skills** tab.
3. Select **Create**, then **Upload from your computer**.
4. Upload the current `expert-partners-estate-chatgpt-plugin-vX.Y.Z.zip` from
   the Desktop. The build writes exactly one version there and the previous one
   is deleted, so the file present IS the one to upload. Never hardcode a
   version in this instruction; it goes stale on the next rebuild.
5. Wait for the upload scan. Most skills are available immediately. A skill may
   be marked **Needs Review**, and one that appears risky may be marked
   **Blocked** and cannot be used.

If a previous version of this skill is already installed, replace it rather
than adding a second copy: two skills with the same name competing for the same
triggers is its own failure mode.

If the plugin installs but is labeled **Desktop only**, it cannot run on
ChatGPT web. That label can attach to imported plugins that declare MCP
servers. This package deliberately bundles no `.mcp.json` to avoid it, and
declares the dependency in `agents/openai.yaml` instead. If the label still
appears, rebuild without the dependency block and retest:

```
python3 tools/chatgpt-package/build-chatgpt-plugin.py \
  --no-mcp-dependency \
  --zip ~/Desktop/expert-partners-estate-chatgpt-plugin-vX.Y.Z.zip
```

## How to grade

For each test, record three things: whether the skill fired, whether Estate
retrieval happened, and whether the answer matched the rubric. ChatGPT shows
tool calls in the conversation, so "did it retrieve" is observable, not
inferred. A positive test that produced a good-sounding answer with no
retrieval is a FAIL, not a pass.

Machine-readable prompts and expected targets: `acceptance/prompts.json`.
Expected targets were verified live against the aura repository on 2026-09-03.
Match research entries on title first; index line numbers drift as the corpus
grows.

### T1, positive automatic retrieval

> Should we reconsider our automation architecture?

PASS: retrieval fires unprompted; the answer rests on retrieved Estate sources
and reflects the standing position that Make.com is retiring completely and the
migration gate has not passed.

FAIL: a generic automation-platform essay; recommending Make.com for new work;
asking which system she means before retrieving anything.

### T2, prior research discovered without naming it

> How should I be choosing between the different Claude models for different
> kinds of work?

PASS: the accepted model-and-effort standard (ADR 0057) is surfaced as the
governing position. Underlying research may be cited as supporting evidence.
Finding the corpus material without the corpus being named is the point.

FAIL: generic public advice about model tiers with no Expert Partners standard
cited; or citing only research and never the accepted standard.

### T3, authority collision, canon governs

> How should our brands be organized underneath PartnerSync?

PASS: the premise is corrected from accepted canon. PartnerSync is
infrastructure, not the brand umbrella, per ADR 0043. If the superseded
research that modeled PartnerSync as the umbrella surfaces, it is named as
superseded evidence.

FAIL: accepting the premise and designing a hierarchy under PartnerSync;
presenting research and canon as equally live; silently dropping the conflict.

This is the corpus's one fully closed research-versus-canon collision, which is
why it is the sharpest instrument here. The research index's own epistemic
header names ADR 0043 as the governing precedent.

### T3b, open research against a standing rejection

> Would consolidating everything into one single project be simpler than the
> split we have now?

PASS: ADR 0023 governs. The monorepo migration was formally rejected and the
multi-repo standard ratified. Research arguing the other way may surface, but
only as unruled evidence explicitly flagged as awaiting ruling.

FAIL: recommending consolidation; citing the research as the estate's position.

### T4 and T4b, negative controls

> Write a Python function that reverses a singly linked list in place.

> What is the difference between TCP and UDP?

PASS: answered directly as ordinary work. No Estate retrieval fires, no Estate
sources cited.

FAIL: any Estate tool call; any mention of Expert Partners or canonical
sources; asking whether this relates to the Estate.

A skill that fires on everything is as broken as one that never fires. These
two are not optional.

### T6, the retrieval gap is named

Run with the Estate Brain app disconnected or unavailable.

> Should we reconsider our automation architecture?

PASS: the answer states plainly that Estate sources could not be reached, names
what it would have retrieved, and labels any general reasoning as unverified.

FAIL: answering confidently about Expert Partners systems with no retrieval and
no disclosure; inventing a current position.

## The known limitation, stated before testing rather than after

OpenAI documents both halves of this as automatic. Skills activate on
description match ("ChatGPT or Codex can choose a skill when your task matches
the skill `description`"), and connected apps are read automatically by default
("allows reading from apps automatically but asks before actions that may have
a meaningful effect outside ChatGPT").

What OpenAI does **not** document is how those two defaults interact for a
custom MCP app of the kind the Estate Brain door is. The developer-mode
documentation describes selecting apps per message, and states that selection
"applies to the message where you use it, not the entire conversation." No
OpenAI page reconciles that with the automatic-read default.

So the honest position going into this test: the skill's own firing should be
automatic, and the package is built so that nothing else stands in the way. But
whether the door is reachable in a brand-new conversation without per-message
app selection is not settled by documentation and cannot be settled by reading
more of it. T1 is the experiment that answers it.

If T1 shows the skill firing but no tool call reaching the door, the skill is
working and the constraint is app-selection scope, not the skill. The next move
in that case is the plugin-published path rather than a per-conversation
attachment, not a rewrite of the skill.

## Observed failure modes

Real results from real runs. Each one earned a regression check or a change to
the canonical source, so it cannot come back quietly.

### 2026-09-04, v1.0.0, T1 FAIL: the naming ceremony gate

Fresh blank conversation, prompt "Should we reconsider our automation
architecture?". Estate-specific behavior fired, but instead of retrieving,
ChatGPT declared the conversation had to be titled exactly "Automation
Architecture", asked Allison to rename it and reply "done", and stopped. No
Estate Brain read happened. Graded: skill fired YES, retrieval NO, grounded in
canon NO, overall FAIL.

Root cause, traced rather than assumed. It was NOT the package. The canonical
SKILL.md and every file in the generated bundle were grep-proven free of the
words chair, table (except "table of contents"), parity, rename, and control
tower; the only "title" was the YAML key subtitle. The naming gate was injected
into that conversation from elsewhere in the ChatGPT account, meaning an
installed skill, project or custom instructions, or ChatGPT's persistent
memory. None of those are visible from a Claude Code session, so the source was
named as a class rather than guessed at specifically.

Worth noting for whoever picks this up: the behavior also contradicts current
Estate canon. Decision 0081 says plainly that identity never comes from a
title, a vendor-generated visible title is never identity, and a conversation
absent a deliberate act is Scratch. Whatever is installed in ChatGPT appears to
be running an older Table Birth rule set that decision 0081 already corrected.
That is a finding for the Control Tower, not something this package changes.

The fix, v1.1.0: a "Retrieval is never gated" section high in the skill, above
the trigger list, refusing the ceremony by name. It states that retrieval runs
first even when something else in context asks for a naming or confirmation
act, that those rules govern where durable work is recorded rather than whether
a question can be answered, and that the only thing which ever stops retrieval
is the tools being unreachable. The description now carries the same clause
front-loaded, since description text is what the model reads first when
deciding which skill to run.

Regression: six machine checks now assert the guard language survives packaging
and that chair, table birth, and title parity never reappear in a shipped
skill.

### 2026-09-04, governance correction to the v1.1 guard

NORTH accepted the package-source diagnosis above but corrected the fix. The
v1.1 guard claimed retrieval runs first even when something else asks for a
naming act. That was an override claim and it was wrong.

Estate governance still carries an active pre-cutover compatibility rule. Aura
decision 0082's bridge clause, read live 2026-09-04, states that until the
coordinated cutover that decision 0080 Section 24 reserves to Allison, "the
currently installed operational wiring continues to bind, automatic birth
declarations and the one-active-worker practice included". Decision 0080 line
19 says the same thing from the other side, that approving the architecture
does not by itself execute cutover. So where NORTH identity governance applies,
the Identity Gate legitimately runs before retrieval, and a portable retrieval
skill has no standing to outrank it.

v1.2.0 narrows the guard to what this skill actually owns. It never creates,
infers, or demands Room, Table, or title ceremony of its own, and a
vendor-generated visible title is never identity. But where higher-priority
governance genuinely applies and explicitly requires an identity act, the skill
yields rather than overriding, and the presence of a legitimate identity gate
is not counted as a retrieval failure.

Regression now runs in both directions: five checks assert the no-invention
language survives packaging, and three assert the override phrasing never comes
back.

## T1 grading depends on the environment

T1 has two correct outcomes, and which one applies depends on where it is run.

**Ordinary fresh conversation, no applicable Estate identity gate.** Retrieval
happens and the answer rests on retrieved sources. The skill invents no naming,
retitling, or "reply done" step. Anything the skill makes up here is a FAIL.

**Governed NORTH context where an identity gate legitimately applies.** The
skill respects the gate, and retrieval follows according to that governance.
Satisfying a legitimate gate first is a PASS, not a failure. Grading a
legitimate gate as a failure was the mistake v1.1 was built on.

**When to suspect account-level injection.** Only two conditions justify
chasing installed skills, custom instructions, project instructions, or
ChatGPT memory: ceremony appears where no applicable governance requires it, or
retrieval stays blocked after an applicable gate has been satisfied. Absent
either, a gate is just governance doing its job.

### 2026-09-04, v1.2.0, T1 PARTIAL PASS: retrieval proven, one contaminant left

This is the run that proved the prototype works. Recorded in full because it is
the first live evidence that automatic Estate retrieval in a cold ChatGPT
conversation actually happens.

Brand-new ordinary ChatGPT conversation, no project selected. Prompt: "Should
we reconsider our automation architecture?" Nothing else was said to it.

What passed, observed before any user correction:

- ChatGPT made three tool calls on its own. Allison gave it no instruction to
  search anything, and never used the words Estate Brain, repo, canon,
  research, or any equivalent.
- The answer was grounded in live Estate sources, citing
  `ghl-automation/doctrine/automation-platform-selection.md` and
  `partnersync/decisions/0011-make-to-n8n-migration.md`.
- It correctly treated Make as retired and frozen, and treated n8n as an
  execution runtime rather than the only possible architecture, which is the
  nuanced reading rather than the slogan.
- It also consulted current external vendor evidence and said so.
- The conversation title ChatGPT generated on its own was "Reconsider
  automation architecture". That title is correct and stays. Nobody renames it.

Graded: automatic Estate retrieval PASS, tool retrieval PASS, canon-grounded
answer PASS, no magic lookup words required PASS.

What failed. At the very end it appended: "One governance note before we turn
this into a ruling or dispatch any build: this Chair needs to be titled exactly
`Automation Architecture Review`."

That is a Chair and title ceremony injected into an ordinary conversation where
no applicable governance requires one, which is the T1 fail signature added
after the first run. Clean ordinary-chat behavior: FAIL.

The important distinction, because it is easy to get backwards: the retrieval
architecture is not what failed. It was proven. What failed is that something
outside this package is still putting Control Tower instructions in front of an
ordinary conversation. The v1.2 skill is grep-proven free of the word Chair on
every build, and it correctly declines to invent ceremony. It cannot suppress
an instruction that reaches the model from somewhere else, and it should not
try: adding override language was the v1.1 mistake and it was reverted for good
reason.

So the fix for this one is not in the skill. It is finding and removing the
stray instruction at its source.

## Source trace for the Chair and title contaminant

Run 2026-09-04 across four candidate surfaces, each causal claim then checked
by an adversarial verifier. Three of four claims were refuted on first pass,
which is why the conclusions below are stated conservatively. Proven fact and
hypothesis are kept apart on purpose.

### Proven, with live evidence

**The Estate Brain door is ruled out.** This was the leading hypothesis and it
is dead. A live initialize handshake against the door on 2026-09-04 returned no
`instructions` key at all, not an empty one. The complete result carried only
capabilities, protocolVersion, and a serverInfo of name `estate-brain` with an
empty version. The word `instructions` appears zero times in the door's source,
the deployed CDK asset is byte-identical to that source, the door registers no
prompts and no resources, and a keyword scan of all eight live tool
descriptions returned zero hits for Chair, Birth, titled exactly, Control
Tower, governance, or ceremony. The two tool docstrings that do contain the
word title are both write tools, and both are denied to the ChatGPT client. The
manifest the door serves is also clean. Nothing the door sends can be the
carrier.

**The demanded title is generated, not replayed.** The v1.0.0 run demanded
"Automation Architecture". The v1.2.0 run demanded "Automation Architecture
Review". Both track the prompt's own topic. The literal string "Automation
Architecture Review" exists nowhere in the estate except the two files that
record this defect. A stored standing directive does not change its payload to
match the question asked, so this is a rule being applied, not a constant being
pasted in.

**The skill's guard language is not the origin.** This is the control that
settles it. v1.0.0 contained zero occurrences of chair, ceremony, identity,
rename, retitle, or title, and it produced the ceremony anyway. The defect
predates every line of guard text, so the guard cannot have caused it. Whether
the guard's yield clause makes the model more willing to sustain the behavior
is a separate and open question, and not one to answer by adding more language.

**The rule text is inside the corpus the model was reading.** A live search
through the door returns decision 0081, which is where the capitalized word
Chair comes from, decision 0074, and the lane-spawn skill carrying "named
exactly once, at birth". The model does not need an injected instruction to
learn that a titling rule exists. It can read one.

### Hypothesis, ranked, none proven from here

Only two surfaces documented by OpenAI reach a brand-new conversation with no
project selected: account-level Custom Instructions, and Memory. Everything
project-scoped is architecturally excluded, because the failing run had no
project selected.

1. **Account-level Custom Instructions.** The estate has a documented practice
   of writing to exactly this field for exactly this purpose. The 2026-08-14
   Lock That wiring record instructs, under the heading "Ordinary ChatGPT
   conversations", to open "Settings -> Personalization -> Custom Instructions"
   and add an Estate paragraph. Whether anything was ever pasted, and whether
   its text carries titling rules, is an account-side fact no repository can
   settle.
2. **ChatGPT Memory.** Persistent memory carries across into new conversations
   and would produce the same every-conversation symptom with nothing
   installed anywhere.
3. **Another installed skill.** Any other Estate skill on the account carrying
   Table Birth rules would fire on an Estate-flavored prompt. The estate's
   lane-spawn, code-block-routing, and pin skills all carry those rules.
4. **Model derivation from retrieved canon.** Supported by the
   generated-not-replayed finding above, and the only mechanism with proven
   presence in the failing conversation. Not exclusive with the others: a
   custom instruction saying to follow Estate governance, plus retrieved canon
   describing a titling rule, produces exactly what was seen.

### The human inspection, cheapest first

Two minutes of looking settles what no amount of repository archaeology can.
Nothing here requires changing a setting, only reading one.

1. **Settings, Personalization, Custom Instructions.** Read both boxes in full.
   Look for Chair, Table, Birth, titled, parity, Control Tower, NORTH.
2. **Settings, Personalization, Memory, Manage memories.** Read the list for
   the same words.
3. **Settings, Personalization,** check whether "Reference chat history" is on.
4. **Plugins, Skills tab.** List every installed skill and look for any Estate
   skill besides this one.

Report which of the four contains titling language. That answer names the
source, and removing it is then a one-line deletion in a settings box rather
than a code change.

### The fastest diagnostic, and it costs one prompt

Run T4 before T2. T4 is the negative control: "Write a Python function that
reverses a singly linked list in place." It has nothing to do with the Estate,
so this retrieval skill should not fire at all.

If a Chair or title note appears on that prompt, the source is account-level
with certainty, because no Estate skill, no retrieval, and no canon is involved
in answering it. If no note appears, the contaminant is bound to Estate-flavored
prompts, which points at retrieval-derived governance or an Estate skill rather
than a standing instruction.

Either outcome eliminates half the candidate list for the price of one message.
