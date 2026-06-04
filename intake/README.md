# intake/

Append-only session-intake inbox for this repo, established by ADR 0027
(Bidirectional Brain -- Session Intake Convention).

## What goes here

Files land here when Allison or an AI surface captures session content:
- Named `YYYY-MM-DD-<slug>.md`
- Required YAML frontmatter: classification, source, project, captured_at
- Default classification: `internal`
- **Append-only -- nothing here is ever modified after it lands**

## What intake/ is NOT

A filing cabinet. Raw capture lands here. Refiling into `doctrine/`,
`project-knowledge/`, `decisions/`, etc. is a separate, deliberate step.

## How it works

The `save_to_session_intake` MCP tool on `mcp.expertpartners.com` writes here
from any surface (claude.ai, Claude Code, Ember). Claude Code also has an
`/intake` skill for local sessions.

Reference: ADR 0027 in the `aura` canonical repo.
