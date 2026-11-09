#!/bin/bash
# pre-tool-use-enforcement.sh
# PreToolUse hook. Act by default (Decision Log 2026-11-08, Act by default,
# caution removed): there are no approval gates. Deletes, force-pushes, resets,
# direct commits to main and config writes all run without a note, a quote or a
# per-step go. The approval-note path, the SSH delete scanner and the M4 batch
# executor were retired with that decision.
#
# One technical guard stays because it protects data, not an approval:
#   BLOCK: unscoped `git config user.name/user.email`. Without --global or
#          --worktree it writes the SHARED repo-local .git/config and silently
#          rewrites the commit identity for every worktree of that repo. The
#          fix is to add --global or --worktree, or run in a scratchpad clone.
#
# KILL-SWITCH:
#   Sentinel file: touch ~/.claude/pre-tool-use-enforcement-off
#   Env var:       PRE_TOOL_USE_OFF=1
#
# Reads JSON from stdin (fields: tool_name, tool_input, cwd). Block: exit 2 with
# the reason on stderr. Everything else exits 0 with no decision.

if [[ -f "$HOME/.claude/pre-tool-use-enforcement-off" || "${PRE_TOOL_USE_OFF:-}" == "1" ]]; then
  exit 0
fi

INPUT=$(cat)

# A hook that cannot read its input must not guess. Exit 2 is the only status
# Claude Code treats as a block, so this fails closed on a broken install.
command -v jq >/dev/null 2>&1 || { printf '%s\n' "pre-tool-use-enforcement: jq is not available, so the hook input cannot be read. Install jq or use the kill-switch." >&2; exit 2; }
printf '%s' "$INPUT" | jq -e 'type == "object" and ((.tool_name // "") | type == "string" and length > 0)' >/dev/null 2>&1 \
  || { printf '%s\n' "pre-tool-use-enforcement: the hook input is not a JSON object with a tool_name." >&2; exit 2; }

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""')
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""')

[[ "$TOOL" == "Bash" ]] || exit 0
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""')

# Unscoped git identity writes in a real clone.
# Scope: sets only. Reads, --unset, --global, --worktree and scratch clones pass.
if printf '%s' "$CMD" | grep -qE 'git\s+(-C\s+[^[:space:]]+\s+)?(-c\s+[^[:space:]]+\s+)*config\b' \
  && printf '%s' "$CMD" | grep -qE 'user\.(name|email)[[:space:]]+[^[:space:]-]'; then
  if ! printf '%s' "$CMD" | grep -qE '\-\-(global|system|worktree|get|get-all|get-regexp|list|show-origin|show-scope|unset|unset-all)\b'; then
    GC_TARGET=$(printf '%s' "$CMD" | sed -nE 's/.*git[[:space:]]+-C[[:space:]]+([^[:space:]]+).*/\1/p')
    [[ -z "$GC_TARGET" ]] && GC_TARGET="$CWD"
    if ! printf '%s' "$GC_TARGET" | grep -qE '/private/tmp/claude-501/|/scratchpad/|/working/_clone_|/working/[^/]*\.clone(/|$)'; then
      printf '%s\n' "pre-tool-use-enforcement: unscoped git identity write. \`git config user.name/user.email\` without --global or --worktree writes the shared repo-local .git/config and rewrites the commit identity for every worktree of this repo. Re-run it with --global (the estate identity is Allison Gaddy <allison@expertpartners.com>) or --worktree, or run it in a scratchpad clone. Target repo: $GC_TARGET. Command: ${CMD:0:200}" >&2
      exit 2
    fi
  fi
fi

exit 0
