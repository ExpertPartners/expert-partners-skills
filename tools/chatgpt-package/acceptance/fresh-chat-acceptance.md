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
4. Upload `expert-partners-estate-chatgpt-plugin-v1.0.0.zip` from the Desktop.
5. Wait for the upload scan. Most skills are available immediately. A skill may
   be marked **Needs Review**, and one that appears risky may be marked
   **Blocked** and cannot be used.

If the plugin installs but is labeled **Desktop only**, it cannot run on
ChatGPT web. That label can attach to imported plugins that declare MCP
servers. This package deliberately bundles no `.mcp.json` to avoid it, and
declares the dependency in `agents/openai.yaml` instead. If the label still
appears, rebuild without the dependency block and retest:

```
python3 tools/chatgpt-package/build-chatgpt-plugin.py \
  --no-mcp-dependency \
  --zip ~/Desktop/expert-partners-estate-chatgpt-plugin-v1.0.0.zip
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
