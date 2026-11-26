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
- `discover` lists the current direct children of one scope, newest first, across every page, with an optional name filter. An optional `folder` lists inside a subfolder of the scope instead.
- `read` returns one document in pages after verifying the whole document. It fetches the full export, checks the file version before and after, and checks the file is still a direct child of the scope, or of the given `folder`.

Nested folders. `folder` takes a subfolder id from `discover`. The gateway walks its parents up to the scope's registered root, at most four levels, before listing and again after every read. Each step must be one real folder, untrashed, not withheld, with exactly one parent, in the root's shared drive, and no step may be another scope's registered root, so a nested home is reachable only through its own scope key. Anything else, including a shortcut or a folder moved out mid-read, is refused with `not_in_scope` or `left_scope`. `folder` never widens scope: the scope check runs first. Responses carry `folder: { id, depth }` only when `folder` was given, so callers that omit it see the same contract as before.
- `decisions` reads the complete current Decision Log and returns every heading that shares the newest date.

Reads fail closed. A partial export, a changed document, an incomplete listing or a document above two million characters returns an error and never a best guess. Nothing is cached.

## Scope and permissions

- Scopes are the routing keys in `src/brain.ts`, copied from the Hub reader. The live Departments, Workspaces and Brain Folders map owns what each folder is.
- Only scopes named in the `ALLOWED_SCOPES` var in `wrangler.jsonc` are reachable. The approved department homes include `hq-hr`, `hq-employees` and `hq-finance`, using their existing registry entries. EP Private is included for Allison and Don as leaders. Department profiles cannot reach it. Other private scopes remain excluded. The mapped Routine Audits folder and shared HQ Outputs folder are included. Routing Routine Audits does not settle its proposed organizational assignment.
- Workspace and shelf homes that sit inside another department's folder have their own scopes, so the department that owns them reaches them directly: `hq-library-marketing` (EP and AG Growth), `ep-events` (Event Planning, under EP Growth), `ep-acn` (ACN Advisor, under EP CEO), `ag-strong-ones` (The Strong Ones, under AG Growth) and `ag-case-studies` (AG CEO). Don never reaches the AG ones.
- `ep-client` is a compatibility alias for `ep-client-experience`. It resolves before the caller scope check, keeps the canonical key in responses and `list_scopes`, and grants no additional access.
- AG Personal uses `ag-personal-core` for Company Core and `ag-personal-marketing` for its separate Marketing department. The `ag-personal-cgo` workspace profile reads those two scopes and shared HQ governance only. Existing EP and AG Luxury department profiles gain no AG Personal access, and Don remains excluded. AG Luxury Marketing keeps its existing `ag-marketing` scope key and folder, with the `ag-cgo` profile relabeled AG Luxury Chief Growth Officer.
- Registration permits read-only gateway routing, not new Drive permissions or company-wide access. Existing sign-in, department instructions, leader and specific exception constraints still apply. Deployment must preserve the existing Worker identity, secrets and service account. Verify each added scope through live `list_scopes` and `discover`, checking its registered folder identity and current direct children.
- Drive access is a dedicated service account with the `drive.readonly` scope only. It has no domain-wide delegation and no delegated user. It sees only the folders and shared drives it was added to as a Viewer. The client refuses any path outside the Drive v3 files API and any method other than GET.

## Who can read what

Access is enforced in the gateway, in `src/access.ts`, from the November 20, 2026 Decision Log entries on leader-level access and department access. Instructions and folder maps do not create Drive permissions, so the gateway applies the limits itself.

- Leaders. Allison reads HQ, EP and AG. Don reads HQ and EP and never AG. Any other signed-in person gets no scopes.
- Departments. A department identity reads its own folders from the Departments, Workspaces and Brain Folders map, its company's outputs folder, and shared HQ governance (`hq-core`). Marketing departments also read `hq-library`. A department reaches another department only through a named exception in `DEPARTMENTS[...].exceptions`, which stays empty until a decision names the source.
- Effective scopes are always the deployed `ALLOWED_SCOPES` intersected with the caller's profile, so a profile can never widen the allowlist.
- The named `ag-shared-brand` file-read exception lets `ag-ceo`, `ag-cgo`, `ag-cro`, `ag-cco` and `ag-coo` read exactly five shared brand sources now owned by AG Personal Company Core, as required by their existing Project instructions. Call `read` with scope `ag-personal-core` and the exact permitted ID, without `folder`. It does not add either Personal scope to `list_scopes`, permit discovery, grant access to other Personal files or allow nested-folder reads. The five IDs live only in the `FILE_READ_EXCEPTIONS` Worker secret as `{"ag-shared-brand":["<id1>","<id2>","<id3>","<id4>","<id5>"]}`. Both deployed core roots, the department's existing Luxury entitlement, normal full-read membership/version verification and withheld-file checks remain required. No other department, Don or unknown person receives this exception, and Personal gains no Luxury access.
- The Hub token acts as Allison and may narrow itself with the `X-Brain-Department` header. Department tokens are fixed to their department. They are stored only as SHA-256 hashes in the `DEPARTMENT_TOKEN_HASHES` secret (`{"<hash>":"<department id>"}`), and none are issued yet.
- Spreadsheets. A Google Sheet that is a direct child of a scope is readable one whole tab at a time. `read` without `sheet` returns the tab list. `read` with an exact tab title returns every row of that tab with its sheet row number, through the Sheets v4 values API using the same drive.readonly token. The same membership and same-version checks apply, and no write scope is requested.
- Withheld sources. A historical or unapproved document that still sits in an approved folder is withheld by its Drive file id in the `WITHHELD_SOURCES` secret, a JSON array such as `["<file id>"]`. `discover` never lists it, including by name query, and reports only a `withheld` count. `read` refuses it with 403 before any Drive call. An unreadable or malformed list refuses every tool call instead of withholding nothing, and an empty array withholds nothing. The ids live in the Worker secret, not here, because this repository is public. The source's owning department decides which ids belong there.
- MCP sign-in uses the signed-in person's profile. Per-department narrowing on MCP needs a separate sign-in identity per department, which comes with each department's Week 4 decision rights.

## Daily health check

A cron trigger runs a live check every day at 12:00 UTC (Decision Log, Nov 20 2026, Business Brain connection monitoring). It probes every allowed scope, lists one scope completely each day on a rotation, reads the whole current Decision Log and checks that its newest entry is under 14 days old, and confirms the HQ Rulebook is present with a current version. Workers allow a limited number of outbound requests per run, which is why only one scope is listed completely per day. The result keeps only counts, versions, dates and error codes, never document text, and a later pass never hides an earlier failure. Leaders read it at `GET /api/health/deep` with the Hub token, and `?run=1` runs it now. Failures also log to Worker logs. Alerting to Allison goes through Ember's question line once that is live.

## ChatGPT client checks

The daily Codex heartbeat runs `scripts/chatgpt_check.py` on the existing signed-in M2 profiles for both leaders. It verifies the ChatGPT identity, uses the existing gateway connection, and closes its owned browser job in `finally`. It never reconnects an account. Private runtime settings supply the existing profile routes, proof conversation IDs, app ID, gateway URL and the existing Hub-token 1Password item. No token value is written to settings or passed on a command line.

Each run starts through the existing authenticated leader API at `POST /api/health/clients/{allison|don}/start`. A temporary `health_run_id` on the same four MCP read tools lets the gateway record actual authenticated outcomes. The canary checks leader scopes, current Rulebook discovery and verified read, current Decision Log read, decisions, private-scope denial and cross-scope denial. HTTP tool calls cannot attest a client check, a different identity cannot fill it, and the finalizer cannot accept a claimed PASS. Receipts contain only counts, versions, codes and proof identifiers, never source text. Short-lived run observations expire after a day.

`GET /api/health/clients` shows the latest receipts and notification state. `POST /api/health/clients/evaluate` runs the same missing-receipt evaluator used hourly at fifteen minutes past the hour. A receipt older than 26 hours, including a runner that never starts or never finishes, triggers a missed-check alert. The original 12:00 UTC server-to-Drive check is unchanged. Client and server states remain separate.

The existing Sendblue line sends one failure, missed-check or recovery notice per state transition. HTTP refusal or provider rejection does not advance the state. Pending deliveries are checked through the documented Sendblue status endpoint, and failed delivery is retried. The leader-only `POST /api/health/clients/drill` accepts a client and `failed`, `healthy` or `missed` state only after a real passing baseline. It exercises the same deadline evaluator and sender against an isolated, TEST-labelled receipt; it cannot alter production health or fabricate a successful client run.

KV replication is eventually consistent. The M2 runner allows a new lease to propagate before asking ChatGPT to execute and waits for bounded observation propagation before finalizing. Keep the client monitor on the existing gateway and the native Codex automation; do not add a second gateway, OAuth link or local scheduler.

## Secrets

Secrets live only in 1Password and in the Worker's Cloudflare secrets. Nothing in this folder holds one. Load or rotate them by piping from `op` into `wrangler secret bulk`, never on a command line.

| Worker secret | Purpose |
| --- | --- |
| `GOOGLE_SA_KEY` | Service account key JSON for the read-only Drive account |
| `HUB_API_TOKEN` | Bearer token for the Hub |
| `COOKIE_ENCRYPTION_KEY` | Encrypts the approval cookie |
| `ACCESS_CLIENT_ID`, `ACCESS_CLIENT_SECRET` | Cloudflare Access OIDC app |
| `ACCESS_AUTHORIZATION_URL`, `ACCESS_TOKEN_URL`, `ACCESS_JWKS_URL` | Access OIDC endpoints |
| `WITHHELD_SOURCES` | JSON array of Drive file ids withheld from discovery and reads (not a credential, kept out of this public repository) |

## Develop and deploy

```bash
cd connectors/brain-gateway
npm ci
npm run type-check
npm test
```

Deploy with `npx wrangler deploy` after the KV namespace id in `wrangler.jsonc` is real and the secrets above are set.

The base comes from Cloudflare's MIT licensed `remote-mcp-cf-access` demo through `connectors/factory-connection`. The scope map, discovery and verified-read contract come from the Expert Partners Hub reader.

## Failure alerts

The daily check texts Allison through the existing Sendblue line when a check fails, and once when it recovers (`src/alert.ts`). Secrets set with `wrangler secret put` from 1Password (Ember vault, Sendblue API and Secret Key): `SENDBLUE_API_KEY_ID`, `SENDBLUE_API_SECRET`, `ALERT_TO`, `ALERT_FROM`. The text names failed checks and short error codes, never document text. A refused send keeps state so the next run retries.
