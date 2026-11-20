---
classification: public
---

# Drive brain gateway

One read-only Cloudflare Worker that gives authorized AI environments current, scoped access to the Expert Partners Business Brains in Google Drive (HQ, EP, AG), with no stored copy of any document.

- Claude, ChatGPT and Factory connect to `https://brain-gateway.expert-partners.workers.dev/mcp` as a remote MCP connector. Sign-in runs through the same Cloudflare Access for SaaS OIDC pattern as `factory-connection`, limited to the `ALLOWED_EMAILS` var and checked again on every MCP session.
- The Expert Partners Hub calls `GET /api/tools` and `POST /api/tools/<tool>` with `Authorization: Bearer <token>`.
- `GET /health` reports the tool count and nothing else.

## Tools

Four read tools, no write tools.

- `list_scopes` lists the scopes the gateway may read.
- `discover` lists the current direct children of one scope, newest first, across every page, with an optional name filter.
- `read` returns one document in pages after verifying the whole document. It fetches the full export, checks the file version before and after, and checks the file is still a direct child of the scope.
- `decisions` reads the complete current Decision Log and returns every heading that shares the newest date.

Reads fail closed. A partial export, a changed document, an incomplete listing or a document above two million characters returns an error and never a best guess. Nothing is cached.

## Scope and permissions

- Scopes are the routing keys in `src/brain.ts`, copied from the Hub reader. The live Departments, Workspaces and Brain Folders map owns what each folder is.
- Only scopes named in the `ALLOWED_SCOPES` var in `wrangler.jsonc` are reachable. Private, finance and HR scopes are left out until Allison adds them.
- Drive access is a dedicated service account with the `drive.readonly` scope only. It has no domain-wide delegation and no delegated user. It sees only the folders and shared drives it was added to as a Viewer. The client refuses any path outside the Drive v3 files API and any method other than GET.

## Secrets

Secrets live only in 1Password and in the Worker's Cloudflare secrets. Nothing in this folder holds one. Load or rotate them by piping from `op` into `wrangler secret bulk`, never on a command line.

| Worker secret | Purpose |
| --- | --- |
| `GOOGLE_SA_KEY` | Service account key JSON for the read-only Drive account |
| `HUB_API_TOKEN` | Bearer token for the Hub |
| `COOKIE_ENCRYPTION_KEY` | Encrypts the approval cookie |
| `ACCESS_CLIENT_ID`, `ACCESS_CLIENT_SECRET` | Cloudflare Access OIDC app |
| `ACCESS_AUTHORIZATION_URL`, `ACCESS_TOKEN_URL`, `ACCESS_JWKS_URL` | Access OIDC endpoints |

## Develop and deploy

```bash
cd connectors/brain-gateway
npm ci
npm run type-check
npm test
```

Deploy with `npx wrangler deploy` after the KV namespace id in `wrangler.jsonc` is real and the secrets above are set.

The base comes from Cloudflare's MIT licensed `remote-mcp-cf-access` demo through `connectors/factory-connection`. The scope map, discovery and verified-read contract come from the Expert Partners Hub reader.
