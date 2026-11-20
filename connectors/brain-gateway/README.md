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
- Only scopes named in the `ALLOWED_SCOPES` var in `wrangler.jsonc` are reachable. The approved department homes include `hq-hr`, `hq-employees` and `hq-finance`, using their existing registry entries. Private scopes remain excluded. Routine Audits remains excluded while its department-home assignment is proposed.
- Registration permits read-only gateway routing, not new Drive permissions or company-wide access. Existing sign-in, department instructions, leader and specific exception constraints still apply. Deployment must preserve the existing Worker identity, secrets and service account. Verify each added scope through live `list_scopes` and `discover`, checking its registered folder identity and current direct children.
- Drive access is a dedicated service account with the `drive.readonly` scope only. It has no domain-wide delegation and no delegated user. It sees only the folders and shared drives it was added to as a Viewer. The client refuses any path outside the Drive v3 files API and any method other than GET.

## Who can read what

Access is enforced in the gateway, in `src/access.ts`, from the November 20, 2026 Decision Log entries on leader-level access and department access. Instructions and folder maps do not create Drive permissions, so the gateway applies the limits itself.

- Leaders. Allison reads HQ, EP and AG. Don reads HQ and EP and never AG. Any other signed-in person gets no scopes.
- Departments. A department identity reads its own folders from the Departments, Workspaces and Brain Folders map, its company's outputs folder, and shared HQ governance (`hq-core`). Marketing departments also read `hq-library`. A department reaches another department only through a named exception in `DEPARTMENTS[...].exceptions`, which stays empty until a decision names the source.
- Effective scopes are always the deployed `ALLOWED_SCOPES` intersected with the caller's profile, so a profile can never widen the allowlist.
- The Hub token acts as Allison and may narrow itself with the `X-Brain-Department` header. Department tokens are fixed to their department. They are stored only as SHA-256 hashes in the `DEPARTMENT_TOKEN_HASHES` secret (`{"<hash>":"<department id>"}`), and none are issued yet.
- MCP sign-in uses the signed-in person's profile. Per-department narrowing on MCP needs a separate sign-in identity per department, which comes with each department's Week 4 decision rights.

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
