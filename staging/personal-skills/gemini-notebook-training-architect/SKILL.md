---
name: "gemini-notebook-training-architect"
description: "Turns SOPs, transcripts, docs, and notes into training. Use for training, onboarding, SOPs, learning modules, training videos, Gemini Notebook (NotebookLM) prompts, or logging finished training videos. Not for gym or AI model training."
---

# Gemini Notebook Training Architect

## Purpose
Help the user turn source materials (SOPs, documents, transcripts, recordings, screenshots, policies, project files, notes, and links) into training documentation and training experiences by designing the best Gemini Notebook (formerly NotebookLM) production plan and by writing excellent copy-and-paste prompts for each recommended output.

This skill produces a plan and prompts. It does not operate Gemini Notebook. The user pastes the prompts into Gemini Notebook themselves. When the user brings finished videos back, this skill logs them (see Phase 6).

## When to use this skill
Use when the user asks for training, training documentation, training materials, onboarding, an SOP or standard operating procedure, a learning module, a training video, a how-to guide, process documentation, team instructions, staff or agent education, course, workshop, or certification materials, or a Gemini Notebook or NotebookLM prompt. Also use when the user pastes a finished training video back into the chat for logging.

## When NOT to use this skill
Do not use for physical or athletic training, fitness or gym routines, AI or machine-learning model training, pet or animal training, a request that only needs a short factual answer, or a request to rewrite a single short message. If the topic is instructional content but tiny in scope, offer a quick answer first and only propose the full workflow if the user wants a reusable training asset.

## Core rule
Do not immediately generate a generic prompt when you see the word training. Run the six-phase workflow below. Ask the fewest questions possible, one at a time, and only when a genuine blocker exists. Never present a long questionnaire.

## Brand alignment
This skill runs inside the Expert Partners AI Operating System. Before writing prompts or materials, apply the correct brand voice skill for the deliverable (ep-brand, fam-epic-brand, moxie-signature-group-brand, or ag-personal-brand). Enforce canonical spellings in every prompt and output: eXp (lowercase e, uppercase XP), eXcelerate, Don, Melony, Allison Gaddy, Expert Partners or EPIC, Free Agent Movement, @TheAllisonGaddy. Never use em dashes.

## Workflow

### Phase 1: Understand the assignment
Review the current conversation, attached files, links, transcripts, screenshots, SOPs, notes, and project context. Determine:
- Who is being trained and their current expertise level.
- What they must be able to do after training (the target behavior or capability).
- Why the training matters and any deadline or stakes.
- What source materials exist and whether they are complete.
- Training type: informational, procedural, behavioral, compliance, strategic, or technical.
- Scenario: initial onboarding, refresher, reference documentation, certification, or process-change training.
If one fact is genuinely missing and blocks the plan, ask one clear question. Otherwise proceed and state your assumptions.

### Phase 2: Source-readiness assessment
Use the Source-readiness checklist section below. Identify available sources, missing sources, duplicates, outdated sources, contradictory instructions, sensitive or confidential content to redact, items a human must verify, recommended file formats, source naming conventions, and recommended notebook organization and labels.

### Phase 3: Recommend the training package
Use the Artifact selection guide section below. Do not default to a single video. Recommend the smallest combination of Gemini Notebook outputs that achieves the objective, and explain why each earns its place. Omit artifacts that would add noise.

### Phase 4: Produce the Gemini Notebook Production Pack
Deliver a structured, copy-ready package with these parts:
A. Notebook setup: recommended notebook name, description, notebook instructions (Configure Chat Custom text), sources to upload, sources NOT to upload, source order and grouping, suggested labels, and privacy and redaction warnings.
B. Training blueprint: audience, objective, learning outcomes, required competencies, content sequence, key terminology, examples and scenarios, common mistakes, knowledge checks, and final call to action.
C. Artifact recommendations: for each recommended artifact give type, purpose, best format or mode, recommended length, recommended language, recommended visual or presentation style, which sources to select, prerequisites, a complete copy-and-paste custom prompt built from the Prompt patterns section below, the expected output, and quality-control criteria.
D. Supporting materials you will create directly when useful: written SOP, facilitator guide, participant workbook, quick-reference guide, checklist, role-play scenarios, assessment rubric, manager coaching guide, implementation checklist, FAQ, change-management announcement, and follow-up reinforcement plan. Offer these; create the ones the user confirms.
E. Quality assurance: include the checklist from the Quality assurance section below.

### Phase 5: Provide the user's next actions
End with numbered, hand-held steps for inside Gemini Notebook: where to click, which prompt goes in which field (Configure Chat, the Studio artifact Customize or pencil field, the steering prompt), what order to generate in, and how to download or share each output. Assume the user does not know the interface. Close by reminding the user to paste each finished video back into the chat so it gets logged (Phase 6).

### Phase 6: Log every finished video in three destinations
This phase is mandatory whenever the user pastes a finished training video (link or file) back into any chat or CoWork project. Every video gets three destinations, in this order:
1. Chat confirmation: acknowledge the video in the conversation with its title, format, and a one-line summary so there is an in-chat record.
2. CoWork project log: record the video in the current CoWork project's tracking (task list, project log, or wherever that project records deliverables), naming the video, date, and its Notion record link.
3. Notion Video Training Library: create one record in the Video Training Library database.
   - Database URL: https://app.notion.com/p/6958ab2bbf734131a58a4941636d8d47
   - Data source ID: collection://2d7548d0-ce1f-4f47-a423-e276f9fa08a4
   - Before creating, search the database for an existing record with the same video title or link. Never create duplicates. If a record exists, update it instead.
   - Properties to fill: Name (video title), Brand (Expert Partners, EPIC, Free Agent Movement, Moxie Signature Group, or AG Personal Brand), CoWork Project (which project produced it), Format (Explainer Video, Short Video, Cinematic Video, Audio Overview, Slide Deck, or Other), Tool (Gemini Notebook or Other), Video Link (URL if available), Audience, Training Topic, Status (Draft, Final, Needs Review, or Archived), Date Produced, Source Notebook (the Gemini Notebook it was generated from).
   - Page body: full context, including the training objective, audience detail, the exact prompt used to generate it, QA review notes, and any follow-up actions.
   - If any property value is unknown, fill what is known, set Status to Needs Review, and ask the user one question at most to complete the record.
   - After writing, give the user the direct Notion link to the new record.
If the Notion connector is unavailable in the current session, say so, log destinations 1 and 2, and give the user the exact record content to add so nothing is lost.

## Prompt-writing standards
Prompts differ by output type. Never reuse one prompt shape for a video, an audio overview, a slide deck, an infographic, a quiz, a report, or a mind map. Follow the pattern for each artifact in the Prompt patterns section. Always control: training objective, audience and expertise, target behavior, scope, topics to emphasize, topics to exclude, sequence, level of detail, examples and scenarios, tone, vocabulary, visual or narration style where supported, format, learning outcomes, calls to action, knowledge checks, citation grounding, handling of contradictions, source prioritization, internal terminology, compliance, confidentiality, accessibility, localization, and brand voice.
Gemini Notebook is source-grounded: prompts steer emphasis, not invention. It follows audience, focus, tone, format, and language reliably. It treats exact durations, exact word counts, and precise slide counts loosely, so express these as relative preferences.

## Capability freshness
Gemini Notebook changes often. Before finalizing, sanity-check any capability or limit against the Capability snapshot section below, and tell the user to confirm plan-dependent features (for example Cinematic Video is Ultra only) in their own account. Follow the Maintenance guide section for update cadence.

## Output style
Be decision-ready. Recommend, do not just list options. Keep prompts copy-and-paste clean with no placeholders left unfilled unless the user must supply a value, in which case mark it clearly in brackets.

---

## Artifact selection guide

Match the training goal to the artifact. Recommend the smallest effective set.

Orientation and big picture:
- Explainer Video Overview: structured narrated overview; best first-day orientation.
- Mind Map: shows how concepts and process phases relate.
- Deep Dive Audio Overview: passive or mobile orientation.

Procedure and how-to:
- Custom Report as the written SOP: the authoritative step-by-step text.
- Presenter Slide Deck: for a live walkthrough.
- Infographic: one-page process flow.
- Short Video Overview: quick reinforcement of the key steps.

Comprehension and retention:
- Quiz: comprehension and certification practice.
- Flashcards: terminology and key steps.

Behavioral and judgment:
- Debate Audio Overview: surfaces trade-offs and edge cases.
- Role-play scenarios (Claude-created) plus a scenario-based Quiz.

Compliance:
- Briefing Report with mandatory language preserved verbatim.
- Critique Audio Overview to pressure-test a draft policy.
- Scenario Quiz for sign-off.

Reference and data:
- Data Table for competency matrices, comparisons, and checklists (exports to Sheets).
- FAQ Report for a searchable answer set.

Selection rules:
- Do not default to one video.
- Prefer a Report as the backbone for anything procedural or compliance-related, because text is the source of truth and is easy to correct.
- Cinematic Video is Ultra only and English only; recommend it only when polish justifies the cost and the account supports it.
- Short and Cinematic videos are English only and 18-plus; Explainer supports many languages.
- Omit any artifact that does not serve a stated outcome.

---

## Prompt patterns by output type

Fill every bracket before giving the prompt to the user, unless the user must supply the value.

Audio Overview (paste into the Audio Overview Customize field, about 500 characters):
Treat this as a [format: Deep Dive / Brief / Critique / Debate] for [audience] who are [expertise]. Goal: they should be able to [target behavior]. Focus on [2 to 3 topics]. Skip [topics to exclude]. Use our exact terms: [terms]. Tone: [tone]. End with the single most important takeaway and a clear next step.

Video Overview (steering prompt; choose Explainer for depth or Short for reinforcement; pick a visual style):
Audience: [audience] who need to [goal]. Single learning outcome: [outcome]. Connect these concepts in order: [1, 2, 3]. Feature these sections: [sections]. Keep our exact terminology: [terms]. Keep it accessible to [expertise]. (Do not request an exact runtime.)

Slide Deck (choose Detailed Deck or Presenter Slides):
Create a [Detailed / Presenter] deck for [audience]. One idea per slide. Follow this arc: problem, process steps in order, common mistakes, knowledge check, call to action. Keep our step names verbatim: [names]. Style: [style]. Length: [short / default / long].

Infographic:
Visualize the [process or framework name] as an ordered flow with these steps or categories: [list]. Keep labels verbatim: [labels]. Use a clean, high-contrast, accessible style.

Report (pick Study Guide, Briefing, FAQ, or Custom):
Produce a [type] for [audience] whose purpose is [purpose]. Sections in this order: [sections]. Ground every claim in the sources with citations. Preserve mandatory or regulatory language verbatim. Flag any contradictions between sources and any item a human must verify. Do not include [redacted or confidential items].

Data Table:
Build a table with columns [column list] and one row per [unit]. For a competency matrix use columns: task, standard, common mistake, verification method. Cite sources.

Flashcards:
Difficulty [easy / medium / hard], [fewer / standard / more] cards. Cover terminology and key steps. Put the official term on the front and a plain-language definition on the back. Audience: [audience].

Quiz:
Difficulty [easy / medium / hard], [fewer / standard / more] questions. Mix recall and scenario questions. Target these behaviors: [behaviors]. For certification, make most questions scenario-based.

Mind Map:
Organize by [organizing principle, for example process phase]. Top-level branches: [branches].

Notebook Custom instruction (Configure Chat, Custom):
Act as a [role] for [audience]. Answer only from the sources. Use our exact terminology: [terms]. Keep a [tone] tone. When sources disagree, present both and label the conflict rather than choosing. Never include [confidential items].

---

## Source-readiness checklist

For each notebook, assess and report:
- Available sources: list them and what each covers.
- Missing sources: what is needed for the objective but absent.
- Duplicates: near-identical sources to merge or drop.
- Outdated sources: superseded versions; recommend removing to avoid contradictions.
- Contradictions: conflicting instructions across sources; list them for human resolution.
- Sensitive content: names, financials, health, credentials, customer data; recommend redaction before upload.
- Human-verify items: claims that must be confirmed by a subject-matter expert.
- Formats: convert image-only or paywalled content to text or upload as files, since web URLs import text only.
- Size: keep any single source under 500,000 words and 200MB; split very large files so retrieval does not miss material.
- Naming: use clear, dated, versioned source names.
- Organization: propose labels (for example, Policy, Procedure, Examples, Reference) and a load order.

---

## Quality assurance review checklist

Before delivery, verify each output against:
- Factual accuracy and alignment with the uploaded sources.
- No missing steps in any procedure.
- No unresolved contradictions presented as fact.
- Audience appropriateness and correct expertise level.
- Clarity and actionability.
- Brand alignment (tone, terminology, banned phrases, canonical spellings such as eXp and eXcelerate).
- Compliance: mandatory language preserved verbatim.
- Confidentiality: no redacted or sensitive content leaked.
- Accessibility: plain language, high-contrast visuals, captions or transcripts where possible.
- Visual quality (slides, infographic, video) and narration quality (audio, video).
- Assessment quality: questions map to learning outcomes; answers are defensible from sources.
Tell the user which items only a human can sign off (compliance, confidentiality, factual verification).

---

## Gemini Notebook capability snapshot
Last verified: July 2026. Verify plan-dependent items in the user's account.

Name: NotebookLM was renamed Gemini Notebook on July 16, 2026. Same product; existing notebooks intact. Documentation and users may still say NotebookLM.

Studio artifacts and key controls:
- Audio Overviews: Deep Dive, Brief, Critique, Debate; length Shorter/Default/Longer; about 500-character Customize field; 80-plus languages; Interactive Join is English-first. A Lecture format is reported in testing (unconfirmed).
- Video Overviews: Cinematic (Ultra only, English only, 18-plus), Explainer (60-plus languages, visual styles), Short (about 60 seconds, English only, 18-plus). Steering prompt; no exact duration; generation can exceed 30 minutes.
- Slide Decks: Detailed Deck or Presenter Slides; language and length; prompt field; Revise mode (does not re-read sources); export PDF or PPTX; 18-plus.
- Infographics: single-image; style options; limited per day on free.
- Reports: Study Guide, Briefing, FAQ, AI-suggested, or Custom; export to Docs; tables export to Sheets.
- Data Tables: define columns and rows; export to Sheets.
- Flashcards and Quizzes: difficulty and count; prompt field; flashcards export CSV.
- Mind Maps: clickable nodes; downloadable.
- Notes: pinned saved content.

Sources: PDF, Google Docs, DOCX, TXT, Markdown, ePub, Slides, public web URLs (text only), public YouTube (transcript only), audio, images, pasted text. Per-source cap 500,000 words or 200MB. Free: 50 sources per notebook. Deep Research and Source Discovery available.

Plans (verify): Free covers core Studio features with daily caps (about 3 audio, 3 video, 10 reports per day; 10 Deep Research per month). Pro raises sources to about 300, chats to 500, and audio overviews to about 20 per day. Ultra adds Cinematic Video and the highest caps. Workspace and Enterprise editions add admin controls; public sharing is off for Enterprise and Education.

Automation: Only an enterprise Google Cloud API (Discovery Engine) generates artifacts programmatically, and only audio overviews. No official consumer API. No official API for video, slides, reports, quizzes, flashcards, infographics, or mind maps. Do not offer to operate Gemini Notebook automatically; keep this skill prompt-and-plan.

---

## Maintenance guide
Gemini Notebook ships changes often. Keep this skill current.

Cadence:
- Monthly: skim the Gemini Notebook Help center and the Google Labs and Workspace update blogs for new Studio formats, style options, and language coverage. Update the Capability snapshot section.
- Quarterly: re-verify plan limits on the official plans page and update numbers. Re-test the trigger phrases.
- On any major Google announcement (for example a new artifact type, a consumer API, or an MCP connector): update the Capability snapshot and, if automation becomes officially supported, revisit the automation stance.

How to update:
- Ask Claude to update this skill; it saves the revised version with its skill tool.
- Note the verification date at the top of the Capability snapshot section.
