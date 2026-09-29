---
name: gamma-presentation-builder
description: Build polished real estate presentations from source content and, when Gamma tools are available, create a new editable Gamma presentation or a new presentation from an existing Gamma template. Use for listing presentations, buyer seminars, market updates, seller consultations, recruiting decks, training decks, or requests such as "build this in Gamma," "make this a deck," or "turn this into slides."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: hands
status: designed
inherits: []
brand-scope: null
subtitle: "decks planned and built in Gamma"
---
# Gamma Presentation Builder

Turn real estate presentation content into a complete deck plan and, when Gamma tools are available, create a new editable Gamma from that plan.

## Workflow

1. Gather existing context before asking questions.
   - Use the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps, silently, for voice, market, niche, proof, CTA, and brand direction. The agent's own documents win over this skill's defaults.
   - Use presentation content already supplied in the conversation or files.
   - If the user says "use what we just made," use the most recent presentation-shaped content and state what source you used.
2. Ask at most one batched question message, and only when required content is missing.
3. Build the deck structure first.
4. If Gamma tools are available and the user asked to build/create the deck in Gamma, create a new Gamma using the integration routing in [references/gamma-integration.md](references/gamma-integration.md).
5. If Gamma tools are unavailable, provide one paste-ready Gamma build prompt that reproduces the deck structure.
6. Return the result in the required delivery order below.

## First message

If the presentation content and purpose are already clear, do not ask questions. Start with one short line and build the deck.

If the content is missing, ask one batched message:

> I can turn this into a finished presentation structure and, if Gamma is connected, create the new deck there too.
>
> 1. Paste the presentation content, attach the source, or say "use what we just made": ____
> 2. What is the deck for: listing appointment, buyer seminar, market update, recruiting, training, or something else? (optional): ____
>
> Short, messy answers are fine.

Do not ask a second setup round. Use sensible defaults and labeled placeholders when necessary.

## Deck design rules

Let the content determine the slide count. Most decks land around 8 to 15 slides, but never pad or cut substance just to hit a target.

For every slide, provide:

- title: one short, presentable line
- on-slide content: concise copy, usually one headline plus up to 3 to 5 bullets or stat callouts
- speaker note: 2 to 4 sentences in the agent's voice explaining what to say, not repeating the slide verbatim
- visual direction: the image, chart, map, comparison, proof element, or layout that should carry the slide

Build for presentation, not document reading:

- one idea per slide
- strong visual hierarchy
- short copy that can be read from across a room or on a laptop
- charts only when a chart communicates faster than prose
- use tables sparingly and only for clean comparisons
- prefer authentic property, neighborhood, agent, team, or market imagery when supplied
- never invent logos, testimonials, awards, listings, transaction counts, statistics, or brand assets

## Narrative logic

Choose the sequence that fits the deck's job rather than forcing one universal outline.

For listing presentations, usually move through:
1. seller goal and desired outcome
2. understanding of the property and market
3. pricing strategy
4. positioning and marketing plan
5. proof and differentiation
6. launch and communication process
7. next step

For buyer seminars, usually move through:
1. what the buyer wants to accomplish
2. current market context
3. financing/preparation
4. search and offer process
5. inspections, appraisal, and closing
6. local guidance and proof
7. next step

For market updates, usually move through:
1. headline takeaway
2. the few metrics that matter
3. what changed
4. what it means for buyers
5. what it means for sellers
6. local examples or segments
7. next step

Adapt freely when the source content calls for a different story.

## Required output

Use these exact section names.

### DECK STRUCTURE

Write every slide in full using this format:

Slide N: [Title]
- On-slide: [copy]
- Speaker note: [2 to 4 sentences]
- Visual direction: [one concise instruction]

### GAMMA RESULT

Use exactly one of these paths:

Connected and creation requested:
- Create the new Gamma using the current integration rules in [references/gamma-integration.md](references/gamma-integration.md).
- Return the editable `gammaUrl` when available.
- Do not claim the deck was published or shared unless the user explicitly requested those actions and the tool confirmed them.
- Do not claim speaker notes were inserted into Gamma unless the tool explicitly supports and confirms a speaker-note field. If not, keep the speaker notes in chat as the presentation script.

Not connected or creation not possible:
- Provide one paste-ready Gamma prompt containing the complete deck, not a shortened summary.
- Include the title, design direction, every slide title, every on-slide element, and every visual direction.
- Include speaker notes as clearly labeled source material, while warning that Gamma may not place them into a dedicated presenter-notes field automatically.

### WHY THIS WORKS

Use 2 to 3 sentences maximum. Explain the presentation logic, the strongest strategic choice, and the single most useful next action.

Then make one relevant follow-up offer after delivery, such as a shorter consultation version or a version adapted to another audience.

End with:

"Open the deck, make any final visual tweaks, and you're ready to present."

If no agent profile was available, add after the closing line:

"Tip: the Agent Brain Builder writes a profile that makes every skill in this toolkit sound like you automatically."

## Brand behavior

Use known brand direction when it exists, including colors, fonts, logo treatment, image style, tone, and spacing preferences.

If the user names a Gamma template, treat that as a template request and use the template workflow instead of generating from scratch.

If the user asks for a visual style but does not identify a specific theme, use Gamma theme discovery when connected. Do not invent a theme ID.

If no brand or style direction exists, default to clean, modern, restrained, and high-legibility. Do not fabricate brand colors or fonts.

## Data, compliance, and truthfulness

- Use market numbers only when supplied by the user, present in trusted source material, or retrieved from a citable source.
- Attribute time-sensitive market data with source and date/month.
- Use labeled placeholders for missing numbers instead of inventing them.
- Do not make legal, tax, mortgage, or investment guarantees.
- Follow fair housing requirements. Describe properties, amenities, location, access, and lifestyle characteristics, never protected classes or who "belongs" in an area.
- Use only real testimonials, rankings, awards, credentials, and transaction proof.
- Never fabricate property photos, client quotes, MLS results, or brokerage statistics and present them as factual.

## Integration and action boundaries

- Creating a new Gamma is allowed only when the user asked to build/create the deck and Gamma tools are available.
- A generated Gamma is a new editable asset. Do not describe it as an edit to an existing Gamma unless the integration actually supports that operation.
- Current Gamma generation tools create new content. They do not provide general in-place editing of an existing generated Gamma. Direct the user to the Gamma editor for manual refinements after generation.
- Do not change sharing permissions, publish, export, or organize into folders unless the user explicitly asked for those actions or they are required by the request.
- If the user explicitly asks for PowerPoint, PDF, or PNG export and Gamma supports it, request that export through the integration and return the export link when confirmed.

## Quality check before delivery

Verify all of the following:

- the deck has a clear audience and purpose
- the opening earns attention quickly
- each slide carries one primary idea
- slide copy is concise and presentation-ready
- speaker notes add context instead of duplicating the slide
- visual directions are specific enough to build from
- all claims and statistics are grounded
- the CTA is specific and usable
- no promised Gamma action exceeds the integration's confirmed capability
- the Gamma result or fallback prompt matches the deck structure exactly
