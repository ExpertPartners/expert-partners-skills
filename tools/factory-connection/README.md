---
classification: public
---

# Factory connection

One Cloudflare Worker that wraps the Factory Public API for three users.

- Claude and ChatGPT connect to `https://factory-connection.expert-partners.workers.dev/mcp` as a remote MCP connector. Sign-in runs through a Cloudflare Access for SaaS OIDC app whose policy allows only Allison's Expert Partners account, and the Worker checks the same allowlist (`ALLOWED_EMAILS`) again at sign-in and on every MCP session.
- The Expert Partners Hub calls `GET /api/tools` and `POST /api/tools/<tool>` with a JSON body and `Authorization: Bearer <token>`. The token lives in 1Password as Factory Connection - Hub API token and in the Hub's Replit secret `FACTORY_CONNECTION_TOKEN`.
- `GET /health` reports the tool count with no secrets.

Both surfaces share one tool registry in `src/tools.ts`, so a tool added once serves all three users. The skill that teaches chats how to use it is `plugins/operating-doctrine/skills/factory-operator` (see its `reference/factory-connection.md`).

## Tools

All ten Sessions API actions, start-and-watch helpers, what every session is doing, find the owning session or Workstream, Computers, the CI Automations API, webhook automation triggers, Agent Readiness reports and AutoWiki. The full list and the live test results are in the skill reference.

## Secrets

Secrets live only in 1Password and in the Worker's Cloudflare secrets. Nothing in this folder holds one.

| Worker secret | 1Password item (Automation vault) |
| --- | --- |
| `FACTORY_API_KEY` | Factory.ai API |
| `HUB_API_TOKEN` | Factory Connection - Hub API token |
| `COOKIE_ENCRYPTION_KEY` | Factory Connection - Cookie encryption key |
| `ACCESS_CLIENT_ID`, `ACCESS_CLIENT_SECRET` | Factory Connection - Access OIDC client |
| `ACCESS_AUTHORIZATION_URL`, `ACCESS_TOKEN_URL`, `ACCESS_JWKS_URL` | Endpoints listed in the notes of the Access OIDC client item |
| `AUTOMATION_WEBHOOKS` (optional) | JSON map of webhook automation name to `{url, secret, description}`, one 1Password item per webhook |

Load or rotate them by piping from `op` into `wrangler secret bulk`, never on a command line.

## Develop and deploy

```bash
cd tools/factory-connection
npm ci
npm run type-check
npm test
CLOUDFLARE_ACCOUNT_ID=<account id> CLOUDFLARE_API_TOKEN=op://Automation/Cloudflare\ Workers\ Deploy\ Token/credential op run -- npx wrangler deploy
```

The base comes from Cloudflare's MIT licensed `remote-mcp-cf-access` demo (cloudflare/ai), with an email allowlist and an ID token audience check added.
