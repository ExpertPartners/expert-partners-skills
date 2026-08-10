---
name: session-model-advisor
description: "Fires on the first user message of any new conversation, in Claude Chat, Claude Projects, and Claude Code. Reads the model and effort level currently in use, fetches ADR 0057 (Model and Effort Operating Standard, aura repo) LIVE, classifies the incoming task against ADR 0057's decision matrix, and states plainly, before doing anything else, whether to stay on the current model/effort or switch, with a one-line reason. Never hardcodes the decision matrix, always reads ADR 0057 fresh so a changed default never requires editing this skill. Use at the start of every conversation, whenever model or effort choice is in question, or when Allison asks 'right model for this,' 'should I switch,' or 'what effort level,' or whenever Aura is composing a Claude Code dispatch block for a NEW session, in which case it states what to click rather than whether to switch."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "model and effort fit-check at conversation start"
---

# Session Model Advisor -- v1.0 (2026-08-08)

Fires at the first user message of a new conversation, on every surface. Before doing anything else in the response, this skill answers one question out loud, plainly stated -- is the current model and effort level right for the task that just arrived, per ADR 0057 (`decisions/0057-model-and-effort-operating-standard.md`, aura repo)?

This skill carries no copy of ADR 0057's decision matrix. It fetches the ADR live, every time it fires. If a model or effort default in the ADR changes, this file does not need to change. If you ever find the matrix text pasted into this file, that is a doctrine violation, delete it and re-point to Step 3.

A companion SessionStart hook (Claude Code only, lives outside this skill package, see "Companion hook" below) prints the currently configured model and effort as a banner line at session start. The hook only prints. This skill does the reading, the fetching, the classifying, and the recommending. Keep the two jobs separate.

## Step 1 -- Detect the surface

Determine which of the three surfaces this conversation is running on.

- **Claude Code** -- a CLI session, tool access includes Bash/Read/Edit/the Claude Code tool surface, and a session transcript JSONL exists on disk.
- **Claude Project** -- a claude.ai conversation running inside a named Project (project-level custom instructions and project knowledge are present in context).
- **Claude Chat** -- a plain claude.ai conversation, no Project wrapper.

The detection mechanism differs by what's actually reachable on each surface. Don't guess from vibes, check for the concrete signal (tool availability for Code, project context for Projects).

## Step 2 -- Read the current model and effort

### Claude Code

1. Read this session's own transcript file at `~/.claude/projects/<url-encoded-cwd>/<session-id>.jsonl` (encoded cwd = absolute path with every `/` replaced by `-`, leading `-` kept, same encoding the session-naming rule uses). Find the LAST record with `"type":"assistant"`. If one exists, read `message.model` and the top-level `effort` field. This is the authoritative, live answer -- it reflects what actually ran, not a stored preference, and it can legitimately differ from `settings.json` (a session started with a `/model` or `/effort` override, or launched with `--effort`, will show that override here, not the settings default). Verified live 2026-08-08 against this exact session's own transcript -- top-level `effort` field and `message.model` both present on every assistant record.
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

If the task is genuinely ambiguous between two categories, name both in the Step 5 line and default to the higher-effort category. The cost of extra caution on a simple task is low, the cost of under-thinking a task the ADR would have flagged as dense or agentic is not.

Also check the following, from the ADR text as fetched, not from memory.

- Silent downgrade watch language (an "Opus limit reached" notice or an equivalent signal). If live and relevant this turn, surface it per the ADR's own instruction.
- Refusal instrumentation language. Same treatment.

## Step 5 -- State plainly, before anything else

Open the response with exactly one of these, before any other content.

- **Stay** -- "Model/effort check -- staying on `<model>` at `<effort>`. This reads as `<category from ADR 0057>`, which calls for this level. Proceeding."
- **Switch** -- "Model/effort check -- this reads as `<category from ADR 0057>`, which the standard puts at `<recommended model/effort>`. You're currently on `<current model/effort>`. Recommend switching before I continue, `<one-line why>`."
- **No introspection (Chat/Projects)** -- "Model/effort check -- I can't read your current selection on this surface. Based on the task (`<category>`), ADR 0057 calls for `<recommended>`. If that's not what's selected, switch via the model menu next to the send button before I continue."
- **No ADR access** -- "Model/effort check -- can't reach ADR 0057 from this surface right now (`<reason>`). Proceeding on the current model/effort without a standard to check against."
- **Dispatch** (composing a Claude Code dispatch block that spawns a NEW session) -- run Steps 3 and 4 against the JOB BEING HANDED OFF, not against this conversation's own task. State "RUN THIS SESSION AT: `<model>`, effort `<level>`." Name the level in ADR 0057's own vocabulary (`low`, `medium`, `high`, `xhigh`, `max`), verified fresh against current Claude Code documentation every time, never reused from an earlier verification the same day. When a level has grown a same-looking UI sibling, name both and say which one to actually click -- worked example, verified live 2026-08-10 against code.claude.com/docs/en/model-config: `ultracode` sits on the `/effort` picker next to `max` but is a session-only Claude Code setting (`xhigh` plus standing permission to orchestrate dynamic workflows), not a separate or higher effort level. This line rides with the dispatch block's other envelope lines per the code-block-routing skill's "Model And Effort Line" section; this skill supplies its content, that skill enforces its presence.

Keep it to one to three lines. This is a fit-check, not an essay. State it, then move on to the actual work.

## Companion hook (Claude Code only)

A separate SessionStart hook, `session-model-effort-banner.sh`, prints the currently configured model and effort as a plain banner line at the start of every Claude Code session on this machine. It prints only, no classification, no recommendation, no ADR fetch. That is deliberate -- the hook stays a one-line, no-judgment printer, and this skill carries all the reasoning, so a hook failure never silently substitutes for the actual fit-check. The hook's source, install path, and exact fallback order live in `reference/session-model-effort-banner.sh` and `reference/companion-hook.md` in this skill package. It is installed to `~/scripts/` and wired into `~/.claude/settings.json`, not shipped inside this skill's runtime folder, because Claude Code hooks are host-machine configuration, not portable skill content that travels with the plugin install.

## Anti-patterns (don't do these)

- Don't hardcode ADR 0057's matrix into this file, ever, even "just this once" or "as a fallback for when the fetch fails." A failed fetch is Step 3's last bullet, not a reason to paste the matrix here.
- Don't guess at Chat's or a Project's current model/effort and state the guess as fact.
- Don't let the model/effort check become a wall of text. One to three lines, then the actual response.
- Don't skip the check because the task "looks simple." Simple-looking, format-locked work is exactly where ADR 0057 says lower effort holds tighter and higher effort drifts.
- Don't re-fetch ADR 0057 on every turn of a long conversation. Once per conversation, at the first message, is the trigger. Re-check mid-conversation only if the model/effort is changed or the task shape changes dramatically.
- Don't claim Cowork/Projects introspection works "because Code has a way." The two surfaces are unrelated. Verify each on its own terms every time this skill or its documentation is revised.
- Don't trust a remembered model/effort vocabulary mapping twice, even within the same day. The 2026-08-10 finding is why: `ultracode` sits on the `/effort` picker looking like a sibling of `max`, but it is a session-only Claude Code setting (`xhigh` plus workflow orchestration), not an effort level, and the persisted `effortLevel` setting does not even accept it. A mapping that was correct at 9 AM is not evidence for 2 PM. Re-verify against current Claude Code documentation every time, not from memory of the last check today.
