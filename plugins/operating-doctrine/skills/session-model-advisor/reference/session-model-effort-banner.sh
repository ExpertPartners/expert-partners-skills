#!/usr/bin/env bash
# session-model-effort-banner.sh
# SessionStart hook (ADR 0057 companion). Prints the model and effort level
# this Claude Code session is running at, as a single banner line.
#
# This hook does ZERO judgment. It does not fetch ADR 0057, does not
# classify the task, does not recommend staying or switching. That is the
# session-model-advisor skill's job (expert-partners-skills,
# plugins/operating-doctrine/skills/session-model-advisor). Keeping the two
# apart means a hook failure here can never silently substitute a bare
# number for the actual fit-check the skill performs.
#
# Reads stdin JSON from Claude Code (fields session_id, transcript_path,
# cwd, hook_event_name, and sometimes model -- SessionStart is the only
# event that can carry a model field, and it is not guaranteed present,
# verified live 2026-08-08 against code.claude.com/docs/en/hooks).
#
# KILL-SWITCH (mirrors routing-check.sh / backup-claude-memory.sh pattern)
#   Sentinel file -- touch ~/.claude/session-model-banner-off  -> disables globally
#                    rm    ~/.claude/session-model-banner-off  -> re-enables
#   Env var       -- SESSION_MODEL_BANNER_OFF=1                -> disables for that session

set -euo pipefail

if [[ -f "$HOME/.claude/session-model-banner-off" || "${SESSION_MODEL_BANNER_OFF:-}" == "1" ]]; then
  exit 0
fi

INPUT=$(cat)
TRANSCRIPT=$(printf '%s' "$INPUT" | jq -r '.transcript_path // ""')
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""')
HOOK_MODEL=$(printf '%s' "$INPUT" | jq -r '.model // ""')

MODEL=""
EFFORT=""
SOURCE=""

# Preferred path -- this session's own transcript already has a live turn on
# it (true on resume, or later in a long session -- not true on a session's
# very first-ever SessionStart firing, before any assistant reply exists).
if [[ -n "$TRANSCRIPT" && -f "$TRANSCRIPT" ]]; then
  LAST_ASSISTANT=$(grep '"type":"assistant"' "$TRANSCRIPT" 2>/dev/null | tail -1 || true)
  if [[ -n "$LAST_ASSISTANT" ]]; then
    MODEL=$(printf '%s' "$LAST_ASSISTANT" | jq -r '.message.model // ""' 2>/dev/null || true)
    EFFORT=$(printf '%s' "$LAST_ASSISTANT" | jq -r '.effort // ""' 2>/dev/null || true)
    [[ -n "$MODEL" ]] && SOURCE="live session transcript"
  fi
fi

# Fall back to configured defaults -- SessionStart's own model field (if the
# host happened to include it), then env var overrides, then settings.json
# in precedence order (project local > project > user).
if [[ -z "$MODEL" ]]; then
  MODEL="$HOOK_MODEL"
  SOURCE="configured default"
fi

read_json_field() {
  local file="$1" field="$2"
  [[ -f "$file" ]] || return 0
  jq -r --arg f "$field" '.[$f] // empty' "$file" 2>/dev/null || true
}

if [[ -z "$MODEL" && -n "$CWD" ]]; then
  MODEL=$(read_json_field "$CWD/.claude/settings.local.json" model)
  [[ -n "$MODEL" ]] && SOURCE="configured default (project settings.local.json)"
fi
if [[ -z "$MODEL" && -n "$CWD" ]]; then
  MODEL=$(read_json_field "$CWD/.claude/settings.json" model)
  [[ -n "$MODEL" ]] && SOURCE="configured default (project settings.json)"
fi
if [[ -z "$MODEL" ]]; then
  MODEL=$(read_json_field "$HOME/.claude/settings.json" model)
  [[ -n "$MODEL" ]] && SOURCE="configured default (user settings.json)"
fi
if [[ -z "$MODEL" ]]; then
  MODEL="${ANTHROPIC_MODEL:-unset}"
  SOURCE="configured default (fallback, nothing else set)"
fi

if [[ -z "$EFFORT" ]]; then
  EFFORT="${CLAUDE_CODE_EFFORT_LEVEL:-}"
fi
if [[ -z "$EFFORT" && -n "$CWD" ]]; then
  EFFORT=$(read_json_field "$CWD/.claude/settings.local.json" effortLevel)
fi
if [[ -z "$EFFORT" && -n "$CWD" ]]; then
  EFFORT=$(read_json_field "$CWD/.claude/settings.json" effortLevel)
fi
if [[ -z "$EFFORT" ]]; then
  EFFORT=$(read_json_field "$HOME/.claude/settings.json" effortLevel)
fi
if [[ -z "$EFFORT" ]]; then
  EFFORT="unset (defaults to high)"
fi

echo "MODEL/EFFORT (ADR 0057 companion banner, print-only) -- model=${MODEL} effort=${EFFORT} [source=${SOURCE}] -- the session-model-advisor skill does the fit-check against ADR 0057, not this hook."
