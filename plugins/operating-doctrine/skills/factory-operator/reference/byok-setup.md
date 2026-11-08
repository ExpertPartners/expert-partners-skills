# Optional BYOK setup (Anthropic)

BYOK is optional, never a prerequisite for available approved Factory Auto use. Do not change the user's explicit selection or create accounts, keys or workspaces just for preflight. The steps below apply only to a separately authorized BYOK setup. Read current provider entitlement and billing records before claiming an included-credit charge source.

Facts (confirmed): Claude Team plans include monthly API credits claimed by a Team Owner into one Claude Console organization; they are spent before purchased credits, expire each billing cycle, are usable with any Messages API key, are never charged to the Claude plan, and stop hard when empty unless purchased credits or auto-reload exist. Read the current amounts at the source: https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-ultra-and-team-plans and https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers.md
Factory BYOK keys stay local in `~/.factory/settings.json`, support `${ENV_VAR}`, and are per machine. Source: https://docs.factory.com/model-independence/byok.md

## Model IDs

The BYOK Anthropic model IDs in use are `claude-haiku-5-5` (light), `claude-sonnet-5-5` (medium) and `claude-opus-5-5` (heavy). Confirm them against the key's own model list (`GET https://api.anthropic.com/v1/models`) before adding or changing an entry. Pick the lowest that meets the task's quality floor.

## Founder-only (binds accounts; do not perform as an agent)
1. Confirm whether the Team plan's API credits are claimed and which Console org is linked (claude.ai, Organization settings, Billing, API credits).
2. In the Console, create a workspace named for Factory BYOK; set a workspace spend limit at or below the monthly included credit. Leave auto-reload off unless a monthly ceiling is authorised.
3. Create one API key per machine (ember-mac-mini-m2, ag-mac-mini-m4) inside that workspace. Store it in 1Password. Never paste it into chat, docs or repos.

## Operator (per machine)
1. Make the key available as an environment variable to the process that runs `droid daemon --remote-control`, for example `EP_ANTHROPIC_FACTORY_KEY`, read from 1Password at runtime rather than stored in plain text.
2. Add the fragment printed by `scripts/render-settings-fragment.sh byok <model-id>` to `~/.factory/settings.json`. Every `model` value in session, mission or Workstream settings that names a BYOK display name must have a matching `customModels` entry on that machine; otherwise Droid silently falls back to the Factory pool.
3. Run one short headless check with the vendor binary, because the `~/.factory/bin/droid` launcher rewrites `-m` to `auto`:
   `~/.local/bin/droid exec -m "custom:<display-name>" -r low "Reply OK"`
   Then run `/cost` in a session and confirm the Console Cost page shows the usage in the workspace.
4. Repeat on the other machine. Cloud Environments will not see this model.

## Selection rule
Preserve the explicit user route, including Auto. BYOK may be recommended only as an available authorized alternative, not a mandatory fallback. There is no documented automatic budget-aware Factory-to-BYOK switch established here. Missing or exhausted BYOK does not block available approved Factory work. Record Factory counters separately from provider dollar charges.
