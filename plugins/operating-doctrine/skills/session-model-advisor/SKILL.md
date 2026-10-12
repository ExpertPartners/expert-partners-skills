---
name: session-model-advisor
description: "At the first message of any new conversation or model/effort question, check fit. Matching dispatched Workers take the fast path. For handoffs, choose verified surface/model/effort from Estate canon."

# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "model and effort fit-check at conversation start"
---

# Session Model Advisor -- v1.1 (2026-09-23)

Checks the running model and effort when starting a new conversation or when
Allison asks for a fit check. For a dispatched Worker, decision 0093 provides
a bounded fast path: when the dispatch model/effort line and the runtime banner
match, accept that selection and begin the task. Run the full classification
when the line is missing, the runtime disagrees, or the job materially changes.
When NORTH prepares a new technical handoff, this skill recommends one current
surface/model/effort combination and explains the fit briefly, under decisions
0057 and 0072.

This skill carries no copy of ADR 0057's decision matrix. It fetches the ADR live, every time it fires. If a model or effort default in the ADR changes, this file does not need to change. If you ever find the matrix text pasted into this file, that is a doctrine violation, delete it and re-point to Step 3.

A companion SessionStart hook (Claude Code only, lives outside this skill package, see "Companion hook" below) prints the currently configured model and effort as a banner line at session start. The hook only prints. This skill does the reading, the fetching, the classifying, and the recommending. Keep the two jobs separate.

## Step 1 -- Detect the surface

Determine which surface the conversation or handoff uses, including Codex Desktop.

- **Codex Desktop** -- use native task/runtime metadata when exposed and
  distinguish its internal effort identifier from the visible picker label.
  Never infer that two labels are equivalent solely from spelling.
- **Claude Code** -- a CLI session, tool access includes Bash/Read/Edit/the Claude Code tool surface, and a session transcript JSONL exists on disk.
- **Claude Project** -- a claude.ai conversation running inside a named Project (project-level custom instructions and project knowledge are present in context).
- **Claude Chat** -- a plain claude.ai conversation, no Project wrapper.

The detection mechanism differs by what's actually reachable on each surface. Don't guess from vibes, check for the concrete signal (tool availability for Code, project context for Projects).

## Step 2 -- Read the current model and effort

### Codex Desktop

Read native task/runtime metadata if available. Verify which model and visible
reasoning options this account's actual picker offers before recommending a
change. A screenshot supplied by Allison can be dated evidence for her current
UI, but cannot establish a permanent model matrix or prove an internal effort
identifier maps to a visible label. If the picker cannot be inspected, retain
an already approved running selection and say what remains unverified. Do not
change account defaults or speed settings during a fit check.

### Claude Code

1. Read this session's own transcript file at `~/.claude/projects/<url-encoded-cwd>/<session-id>.jsonl` (encoded cwd = absolute path with every `/` replaced by `-`, leading `-` kept). Find the LAST record with `"type":"assistant"`. If one exists, read `message.model` and the top-level `effort` field. This is the authoritative, live answer -- it reflects what actually ran, not a stored preference, and it can legitimately differ from `settings.json` (a session started with a `/model` or `/effort` override, or launched with `--effort`, will show that override here, not the settings default). Verified live 2026-08-08 against this exact session's own transcript -- top-level `effort` field and `message.model` both present on every assistant record.
2. If no assistant record exists yet (true first turn of a brand-new session, before any response has been generated), there is nothing live to read yet. Fall back to the effective **configured default**, checked in this precedence, highest first -- `CLAUDE_CODE_EFFORT_LEVEL` / `ANTHROPIC_MODEL` env vars, then project `.claude/settings.local.json`, then project `.claude/settings.json`, then user `~/.claude/settings.json`, reading the `model` and `effortLevel` fields. Label this explicitly as "configured default" rather than "currently active," since it hasn't been confirmed by an actual turn yet. Field names verified live 2026-08-08 against `code.claude.com/docs/en/settings`.
3. If the SessionStart banner hook already printed its line earlier in this same transcript, it is faster and equally valid to read that line directly rather than re-deriving from the JSONL or settings files.

### Claude Chat and Claude Projects

This is genuinely, permanently thin, not a gap in this skill but a documented fact about the surface. Verified live 2026-08-08 against `support.claude.com/en/articles/8664678-change-the-model-effort-and-thinking-settings` -- the model, effort, and extended-thinking selector is a UI-only menu next to the send button. There is no system-prompt disclosure and no API or in-conversation introspection path for either surface. There is no documented difference between Chat and Projects on this specific point, both are equally thin. Treat any assumption that Projects is more instrumented than Chat as unverified and probably wrong.

Because there is no introspection path, this skill's job on these two surfaces is to say so, not to guess.

- State plainly, as part of the Step 5 line, something like -- "I can't read which model or effort you're on here, claude.ai doesn't expose that to me."
- If Allison (or whoever is driving the conversation) states what's selected, use that for classification.
- Never present a guessed model/effort as fact, and never infer it from response speed or writing style.

## Step 3 -- Fetch ADR 0057 live

Try in this order, and stop at the first success.

1. Call an available MCP tool whose name contains `fetch` from an estate-brain / brain server (for example `mcp__estate-brain__fetch`, or a differently-prefixed connector instance of the same server, check the live tool list for the current session rather than assuming a fixed name). Call it with `repo="aura"`, `path="decisions/0057-model-and-effort-operating-standard.md"`. This is the primary path on any surface where the estate-brain connector is attached, including a claude.ai Project or Chat that has it added (per the Phase A connector registration, memory `project_estate_brain_mcp_live.md`) as well as Claude Code (registered via `.mcp.json` `headersHelper` in the working repo).
2. (Claude Code only) If no brain-fetch tool is available, read the local canonical clone directly at `~/Claude/projects/Aura/decisions/0057-model-and-effort-operating-standard.md`. This clone is pulled fresh at every session start by the `pull-canonical-repos.sh` SessionStart hook, so a direct read counts as reading the live canonical source, not a stale cached copy.
3. (Claude Code only, brain unreachable and no local clone) `gh api repos/ExpertPartners/aura/contents/decisions/0057-model-and-effort-operating-standard.md --jq '.content' | base64 -d`.
4. If all of the above fail, most likely on a bare Claude Chat or Project conversation with no estate-brain connector attached and no repo access, say so plainly, along these lines -- "I can't reach ADR 0057 from here. No estate-brain connector, no repo access on this surface. I'm proceeding without a standard to check against. Add the estate-brain custom connector to this Project if you want this check to run here." Do not fabricate, paraphrase from memory, or reuse a matrix seen in an earlier conversation. The ADR is explicitly a living document (its own text names the risk, model names attached to categories will not outlast a generation even though the categories should) and a remembered copy is exactly the drift this skill exists to prevent.

Never paste ADR 0057's decision matrix into this file. If a future session finds the matrix text living here, that's a doctrine violation, delete it and re-point to step 3.

## Step 4 -- Classify the incoming task

Read the ADR 0057 content fetched in Step 3, specifically the "Model and effort default by task category" section and, if operating as a named agent/persona rather than a bare session, "Model assignment by agent role." Match the current first message against the categories using their actual wording as fetched this run, not a memory of a prior run's categories, since the wording itself can change.

If the task spans two categories, name the relevant demands and choose effort
from the actual complexity, ambiguity, risk, dependency breadth and
verification burden. Do not automatically choose the maximum level. Preserve
usage awareness without weakening a setting that the task materially needs.

Also check the following, from the ADR text as fetched, not from memory.

- Silent downgrade watch language (an "Opus limit reached" notice or an equivalent signal). If live and relevant this turn, surface it per the ADR's own instruction.
- Refusal instrumentation language. Same treatment.

## Step 5 -- State the triggered check plainly

After Steps 3 and 4 are required, open the response with the applicable line below. The matching-Worker fast path in decision 0093 does not trigger these steps or a new opening line.

- **Stay** -- "Model/effort check -- staying on `<model>` at `<effort>`. This reads as `<category from ADR 0057>`, which calls for this level. Proceeding."
- **Switch** -- "Model/effort check -- this reads as `<category from ADR 0057>`, which the standard puts at `<recommended model/effort>`. You're currently on `<current model/effort>`. Recommend switching before I continue, `<one-line why>`."
- **No introspection (Chat/Projects)** -- "Model/effort check -- I can't read your current selection on this surface. Based on the task (`<category>`), ADR 0057 calls for `<recommended>`. If that's not what's selected, switch via the model menu next to the send button before I continue."
- **No ADR access** -- "Model/effort check -- can't reach ADR 0057 from this surface right now (`<reason>`). Proceeding on the current model/effort without a standard to check against."
- **Dispatch** -- classify the job being handed off against current ADR 0057,
  not the current conversation. Apply decision 0072 when selecting an
  implementation engine. Check the current surface, model and exact effort or
  speed options through [capability evidence](reference/handoff-capability.md).
  Recommend one combination, with one short reason. For a new Claude Code
  session, also supply code-block-routing's required MODEL AND EFFORT envelope
  line. Batch-First Execution checks that this line and the other routing
  fields are present before Allison receives the paste block. For a running
  Worker that need not be interrupted, keep its selection and place any new
  recommendation on the next run. Never use a Codex-specific label on Claude
  Code without independent verification; never invent an unavailable level.
  If current options cannot be verified, retain the currently configured
  approved selection and label the uncertainty explicitly.

Keep it to one to three lines. This is a fit-check, not an essay. State it, then move on to the actual work.

## Companion hook (Claude Code only)

A separate SessionStart hook, `session-model-effort-banner.sh`, prints the currently configured model and effort as a plain banner line at the start of every Claude Code session on this machine. It prints only, no classification, no recommendation, no ADR fetch. That is deliberate -- the hook stays a one-line, no-judgment printer, and this skill carries all the reasoning, so a hook failure never silently substitutes for the actual fit-check. The hook's source, install path, and exact fallback order live in `reference/session-model-effort-banner.sh` and `reference/companion-hook.md` in this skill package. It is installed to `~/scripts/` and wired into `~/.claude/settings.json`, not shipped inside this skill's runtime folder, because Claude Code hooks are host-machine configuration, not portable skill content that travels with the plugin install.

## Anti-patterns (don't do these)

- Don't hardcode ADR 0057's matrix into this file, ever, even "just this once" or "as a fallback for when the fetch fails." A failed fetch is Step 3's last bullet, not a reason to paste the matrix here.
- Don't guess at Chat's or a Project's current model/effort and state the guess as fact.
- Don't let the model/effort check become a wall of text. One to three lines, then the actual response.
- Don't skip a triggered check because the task "looks simple." Simple-looking, format-locked work is exactly where ADR 0057 says lower effort holds tighter and higher effort drifts. A matching dispatched Worker follows decision 0093 instead of repeating the check.
- Don't re-fetch ADR 0057 on every turn of a long conversation. Once per conversation, at the first message, is the trigger. Re-check mid-conversation only if the model/effort is changed or the task shape changes dramatically.
- Don't claim Cowork/Projects introspection works "because Code has a way." The two surfaces are unrelated. Verify each on its own terms every time this skill or its documentation is revised.
- Don't trust a remembered model/effort vocabulary mapping twice, even within the same day. The 2026-08-10 finding is why: the strong-end setting on the `/effort` picker (broken spelling `Ultra-code`, see code.claude.com/docs/en/workflows for the exact canonical spelling) looks like a sibling of `max` but is a session-only Claude Code setting (`xhigh` plus workflow orchestration), not an effort level, and the persisted `effortLevel` setting does not even accept it. A mapping that was correct at 9 AM is not evidence for 2 PM. Re-verify against current Claude Code documentation every time, not from memory of the last check today.
- Don't ever write that setting's name bare and contiguous in a skill file, a dispatch block, or any prose a Claude Code session will read as a live prompt. Live-confirmed 2026-08-10, this lane's own incident: the bare word fires the real activation instead of describing it, even inside a quoted worked example. Write it broken (`Ultra-code`).
