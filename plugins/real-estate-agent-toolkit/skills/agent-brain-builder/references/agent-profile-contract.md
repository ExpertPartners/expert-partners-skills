# Agent Profile Contract (agent-profile/v1)

The shared file every skill in the real-estate-agent-toolkit reads. The Agent Brain
Builder is the only skill that writes it. Every other skill reads it and never edits it.

## File

- Name: `agent-profile.md`. A plain Markdown file, 600 to 1,000 words.
- Legacy name: `claude-brain.md` is accepted as a read-only alias. When both exist,
  `agent-profile.md` wins. The builder offers to rename a legacy file on update.
- Location: wherever the agent's AI tool can read it (project files, a knowledge or
  custom-instructions area, or pasted at the start of a chat). The contract does not
  depend on any one platform.

## Header

The file opens with this block, then the sections below in this exact order.

```
profile-format: agent-profile/v1
agent: <full name>
updated: <YYYY-MM-DD>
canon-source: none | <where the agent's own brand, voice, or offer documents live>
```

## Sections (exact headings, in order)

1. IDENTITY: name, brokerage, market or city, years in real estate, the before-story.
2. MARKET & NICHE: the market, the niche, and 3 to 5 named communities (one line each).
3. IDEAL CLIENT: who the agent serves best.
4. VOICE RULES: voice in 3 words, 3 signature phrases, a never-say list, and 2 to 3
   verbatim lines quoted raw from how the agent actually typed their answers.
5. SERVICES & USP: what the agent offers and what actually makes them different.
6. PROOF: real deals, reviews, and wins. Agent-provided only, never drafted.
7. CONTACT & CTA: where clients come from, how to reach the agent, and the default
   call to action, which must point somewhere reachable today.
8. GOALS: the income goal, the reason behind it, and the agent's core weekly
   activities or plan if they have one.

## Rules every reader and writer follows

- Precedence: existing user or organization canon (a brand guide, voice document,
  offer document, or compliance rules) wins over this file whenever both exist. The
  profile records where that canon lives in `canon-source`. When they conflict, follow
  the canon and say so in one line.
- Missing information is written `[FILL IN LATER]`. Nothing is invented. PROOF is
  never drafted, only quoted from the agent.
- Readers use the profile silently. They never re-ask what it already answers.
- Readers never edit the profile. Changes go through the Agent Brain Builder.
- No platform names, course names, or brand names other than the agent's own appear
  in the file.

## Who reads what

| Skill | Sections it uses |
|---|---|
| daily-planner | GOALS (money task source), IDENTITY (name, hours), VOICE RULES (tone) |
| agent-brain-builder | writes all sections |
