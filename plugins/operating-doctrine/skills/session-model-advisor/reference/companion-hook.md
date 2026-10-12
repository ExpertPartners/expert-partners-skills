# Companion SessionStart hook -- install notes

`session-model-effort-banner.sh` (in this same `reference/` folder) is a Claude Code SessionStart hook, not a skill. It ships inside this skill package so the source travels with the skill and any machine can re-install it, but Claude Code hooks are host-machine configuration (`~/.claude/settings.json`), not something a plugin install auto-wires. Installing it is a one-time step per machine.

## Install

```bash
cp reference/session-model-effort-banner.sh ~/scripts/session-model-effort-banner.sh
chmod +x ~/scripts/session-model-effort-banner.sh
```

Then add an entry to the `SessionStart` array in `~/.claude/settings.json` (append to the existing `hooks` list under the `matcher: ""` group, do not replace the array, this estate already runs several SessionStart hooks).

```json
{
  "type": "command",
  "command": "$HOME/scripts/session-model-effort-banner.sh",
  "timeout": 5
}
```

## What it prints

One line, at every session start (fresh or resumed).

```
MODEL/EFFORT (ADR 0057 companion banner, print-only) -- model=claude-sonnet-5 effort=high [source=live session transcript] -- the session-model-advisor skill does the fit-check against ADR 0057, not this hook.
```

On a brand-new session (no assistant turn yet to read), the source label reads `configured default (...)` instead of `live session transcript`, and that distinction is intentional. A configured default can differ from what actually runs once `/model` or `/effort` gets used mid-session. The banner says which kind of answer it's giving.

## Kill switch

Same pattern as this estate's other hooks (`routing-check.sh`, `backup-claude-memory.sh`).

- `touch ~/.claude/session-model-banner-off` -- disables globally until removed
- `SESSION_MODEL_BANNER_OFF=1` -- disables for one launched session

## Why this isn't wired automatically by installing the plugin

Claude Code plugins distribute skills, not host settings. `~/.claude/settings.json` is per-machine, per-Allison configuration that a marketplace plugin install does not and should not touch on its own, doing so silently would append hook commands to a file the plugin doesn't own without her having reviewed the diff. The one-time manual step above is the honest version of that -- visible, reviewable, and identical in spirit to how every other estate hook (`pre-tool-use-enforcement.sh`, `routing-check.sh`) got wired in.
