---
name: estate-knowledge-retrieval
description: "Retrieve Allison Gaddy's Expert Partners Estate knowledge before answering, including in a brand new unnamed conversation, never inventing a rename, retitle, or identity step of its own as the price of an answer. Use whenever a request touches Expert Partners, EPIC, AG Personal Brand, AG Luxury, Free Agent Movement, Don Hobbs, PartnerSync, Ember, or the Estate itself: its brands, people, systems, architecture, automation, processes, strategy, decisions, doctrine, projects, or prior research. Use it for what did we decide, what do we use, how does this work here, should we reconsider this, and any question whose answer depends on what this business already established. Start from the Estate manifest through the Estate Brain tools and retrieve narrowly. Accepted decisions govern; research is evidence, never authority. Never answer from memory: if retrieval is unavailable, say so plainly. Skip for general knowledge unconnected to Allison's businesses."
tier: organization
zone: routing
status: live
subtitle: "retrieve Estate knowledge before answering"
metadata:
  short-description: "Retrieve Estate knowledge before answering"
---

# Estate Knowledge Retrieval v1.2

Allison Gaddy's Expert Partners Estate keeps its durable truth in canonical
GitHub repositories, reached through the Estate Brain tools. This skill makes
retrieval automatic, so she never has to ask for it.

She will not say "check the Estate", "look in the repo", "search my research",
or "start from canon". She should not have to. A question that depends on what
this business already established is the trigger by itself.

## Never invent identity ceremony

This skill does not create, infer, or demand Room, Table, or title ceremony of
its own. It never invents a naming step as the price of an answer.

Specifically, it never asks Allison to name the conversation, rename or retitle
it, confirm that a title matches something, declare which workstream it belongs
to, or reply "done", when nothing in applicable governance actually requires
that step. A vendor-generated visible title is never identity, so a title that
merely looks wrong is not a reason to stop and ask for one.

Where higher-priority governance genuinely applies and explicitly requires an
identity or title act before work proceeds, this skill yields to that
governance. It does not override it, argue with it, or route around it, and the
presence of a legitimate identity gate is not a retrieval failure. Satisfy the
gate under the rules that own it, then retrieve.

Outside a governed context, an ordinary unnamed conversation is a valid place
to retrieve and answer, and retrieval proceeds without ceremony.

## Fire on

A substantive request that could reasonably depend on any of:

- Expert Partners Estate knowledge, doctrine, or accepted decisions
- Allison's prior research
- brands, companies, people, systems, architecture, or processes
- strategy, projects, or prior Estate work
- how something here is currently built, run, or ruled

Phrasings that qualify without naming any source: what did we decide, what do
we use, how does this work here, should we reconsider this, what is our
position, why did we do it this way, is this still current.

## Do not fire on

General knowledge, generic technical questions, and requests with no
connection to Allison's businesses. "Every question could theoretically use
more context" is not a trigger. A generic question stays generic.

## Retrieval procedure

1. **Start at the doorway, not at memory.** Call `get_manifest` first. It is
   the Estate's table of contents and it names what canonical sources exist,
   where each lives, and when each pointer was last verified. Never start from
   recollection or from a copy of Estate knowledge held anywhere else.

2. **Retrieve narrowly.** Use `search` with the specific subject, restricting
   to the repositories the manifest points at. Read the returned excerpts
   before fetching anything.

3. **Widen only when the narrow pass is insufficient.** Escalate in this
   order: `search` again with adjacent terms, `list_topics` to see what exists
   in a domain, `list_repos` when the owning repository is unclear,
   `get_brand_context` when the question is brand specific.

4. **Fetch by path for anything recent.** Same-day and very recent files are
   reached with `fetch` by exact path and are never assumed to be searchable
   yet. If the manifest or an index names a path, fetch that path directly.

5. **Follow the research trail only when the question warrants it.** The
   research corpus index lives in the aura repository at
   `docs/research/INDEX.md`. Each entry carries a subject, the lane it
   informs, a disposition, and, for filed entries, a digest path under
   `docs/research/digests/` plus a Google Drive pointer to the original
   artifact. Read the digest first. Go to the original artifact in Drive only
   when the digest is genuinely insufficient for the question asked.

6. **Consult live external sources** when current outside facts materially
   affect the answer, and say which parts came from outside.

## Authority

When sources disagree, this is the order:

1. Allison's current direction in the live conversation
2. Accepted current canon and decisions
3. Current canonical domain and repository knowledge
4. Project knowledge and relevant implementation evidence
5. Deep research corpus evidence
6. The original research artifact, when the digest or index is insufficient
7. Live external sources, for current outside facts

Two rungs are load bearing and carry their own canon. Accepted decisions
outrank any research document, always, on every claim where the two touch.
And durable truth is created or superseded only by Allison, never by a
research report and never by agreement inside a conversation.

## Research is evidence, never authority

Every artifact in the research corpus is model generated research, dated the
day it was produced. It informs; it rules nothing.

When research conflicts with a later accepted decision, the decision governs.
Do not silently blend the two and do not quietly drop the research. Say what
the research proposed, say what canon ruled, and say which one governs. A
conflict that Allison can see is worth more than a smooth answer that hides
it.

An entry still marked awaiting ruling has not been adopted. Treat it as a
proposal, not as a position this business holds.

## Name the gap, never paper over it

If Estate retrieval is required but unavailable, and the Estate tools cannot
be reached, say that plainly in the answer. Never present a memory based
answer as though Estate state had been checked.

The honest form is short: name that the Estate could not be reached, name what
would have been retrieved, then answer separately and label it as unverified
general reasoning.

## Context discipline

Search before fetching. Fetch only the files or artifacts needed for the
question actually asked. Do not pull whole directories, do not fetch an
original research artifact when the digest answers it, and do not flood the
answer with everything retrieved. Cite what was used.

## Answering

Lead with the answer. Name the canonical sources it rests on. Where canon and
research disagree, surface the disagreement. Where something could not be
verified, say so.
