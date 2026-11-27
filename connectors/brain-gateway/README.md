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

Reads fail closed. A partial export, a changed document, an incomplete listing or a document above two million characters (sixteen million for one spreadsheet tab) returns an error and never a best guess. Nothing is cached.

## Scope and permissions

- Scopes are the routing keys in `src/brain.ts`, copied from the Hub reader. The live Departments, Workspaces and Brain Folders map owns what each folder is.
- Only scopes named in the `ALLOWED_SCOPES` var in `wrangler.jsonc` are reachable. The approved department homes include `hq-hr`, `hq-employees` and `hq-finance`, using their existing registry entries. EP Private is included for Allison and Don as leaders. Department profiles cannot reach it. Other private scopes remain excluded. The mapped Routine Audits folder and shared HQ Outputs folder are included. Routing Routine Audits does not settle its proposed organizational assignment.
- Workspace and shelf homes that sit inside another department's folder have their own scopes, so the department that owns them reaches them directly: `hq-library-marketing` (EP and AG Growth), `ep-events` (Event Planning, under EP Growth), `ep-acn` (ACN Advisor, under EP CEO), `ag-strong-ones` (The Strong Ones, under AG Growth) and `ag-case-studies` (AG CEO). Don never reaches the AG ones.
- `ep-client` is a compatibility alias for `ep-client-experience`. It resolves before the caller scope check, keeps the canonical key in responses and `list_scopes`, and grants no additional access.
- `ag-core` routes to the consolidated private AG Company Core. The legacy `ag-personal-core` key retains that same folder identity for existing callers. `ag-marketing` and `ag-personal-marketing` likewise route to the same consolidated Marketing folder, but remain distinct scope keys with their existing profile grants. The configured legacy `ag-personal-cgo` profile retains its existing non-Core scopes and receives the same three-Core grant as every other AI profile. Core sharing alone grants neither Marketing key nor other non-Core folders. Don remains excluded from all AG scope keys.
- Registration permits read-only gateway routing, not new Drive permissions or company-wide access. Existing sign-in, department instructions, leader and specific exception constraints still apply. Deployment must preserve the existing Worker identity, secrets and service account. Verify each added scope through live `list_scopes` and `discover`, checking its registered folder identity and current direct children.
- Drive access is a dedicated service account with the `drive.readonly` scope only. It has no domain-wide delegation and no delegated user. It sees only the folders and shared drives it was added to as a Viewer. The client refuses any path outside the Drive v3 files API and any method other than GET.

## Who can read what

Access is enforced in the gateway, in `src/access.ts`, from the November 20, 2026 Decision Log entries on leader-level access and department access. Instructions and folder maps do not create Drive permissions, so the gateway applies the limits itself.

- Leaders. Allison reads HQ, EP and AG. Don reads HQ and EP and never AG. Any other signed-in person gets no scopes.
- Departments. Under the November 27, 2026 company-knowledge decision, every configured department/workspace AI profile reads all three Company Cores (`hq-core`, `ep-core`, `ag-core`), plus its existing owning folders, outputs and named exceptions. This common grant applies centrally, including configured legacy workspace profiles. It does not grant other departments' non-Core folders, private folders or pinned leader-only files. Marketing departments also retain `hq-library`. Human leader profiles are unchanged, including Don's exclusion from AG.
- Effective scopes are always the deployed `ALLOWED_SCOPES` intersected with the caller's profile, so a profile can never widen the allowlist.
- The named `ag-shared-brand` file-read exception lets `ag-ceo`, `ag-cgo`, `ag-cro`, `ag-cco` and `ag-coo` read exactly five shared brand sources now owned by AG Personal Company Core, as required by their existing Project instructions. Call `read` with scope `ag-personal-core` and the exact permitted ID, without `folder`. It does not add either Personal scope to `list_scopes`, permit discovery, grant access to other Personal files or allow nested-folder reads. The five IDs live only in the `FILE_READ_EXCEPTIONS` Worker secret as `{"ag-shared-brand":["<id1>","<id2>","<id3>","<id4>","<id5>"]}`. Both deployed core roots, the department's existing Luxury entitlement, normal full-read membership/version verification and withheld-file checks remain required. No other department, Don or unknown person receives this exception, and Personal gains no Luxury access.
- The named `gap108-week2-builder` pinned exception lets Allison, as leader and with no department narrowing, read exactly three known source files that sit outside every scope root. Call `read` with scope `gap108-week2-builder` and the exact ID, without `folder` or `sheet`. Each ID is pinned to its parent folder and shared drive in the `PINNED_FILE_READS` Worker secret as `{"gap108-week2-builder":[{"id":"…","parent":"…","drive":"…"}]}` with exactly three entries. Before and after the read the file must still be an untrashed child of its pinned parent in its pinned drive, the version must not change, and withheld files stay withheld. The exception never appears in `list_scopes` or `discover`, grants no folder or course access, and refuses Don, every department and narrowed Hub sessions. No Drive permission is involved; the gateway's existing read-only identity already sees these files.
- The Hub token acts as Allison and may narrow itself with the `X-Brain-Department` header. Department tokens are fixed to their department and ignore that header. They are stored only as SHA-256 hashes in the `DEPARTMENT_TOKEN_HASHES` secret (`{"<hash>":"<department id>"}`). Raw tokens belong only in the approved secret store and consuming runtime. Token issuance and successful fixed-actor calls do not prove a Claude Project's live connector is bound to that profile.
- Spreadsheets. A Google Sheet that is a direct child of a scope is readable one whole tab at a time. `read` without `sheet` returns the tab list. `read` with an exact tab title returns every row of that tab with its sheet row number, through the Sheets v4 values API using the same drive.readonly token. The same membership and same-version checks apply, and no write scope is requested. A tab may be larger than the two million character document limit, up to ten million characters and twenty-four million response bytes. The byte limit is checked while the response streams, so a larger tab is refused before it is parsed. Tab pages end on whole rows, and `partialRow` marks a single row longer than the page. Pass the first page's `file.version` as `expect_version` on later pages so a change between pages is refused with `changed_during_read`. Sheets reads retry only 429 and 503, at most three attempts, never sooner than Retry-After, and return `rate_limited` when the server asks for more than eight seconds.
- Spreadsheet row pages. A tab too large to rebuild on every page can be read in bounded native row ranges instead of character offsets. Call `read` with `sheet`, `start_row` (1 for a new read) and optional `max_rows` (default 64, at most 256) and `max_chars`, then pass each returned `cursor` back with the same `sheet` until `next_row` is null. Each page fetches only its own range, never the whole tab, and runs the same scope, withholding, membership and before-and-after version checks as every other read; nothing is cached. Joining every page's `text` in order gives exactly the whole-tab text that character mode returns, byte for byte. Sheets leaves out a range's trailing empty rows without saying whether later rows exist, so those rows are held (`held_empty_rows`) and written only once a later populated row proves they are interior, and the final page drops the tab's empty tail (`discarded_tail_rows`). `start_row`, `covered_end_row` and `grid_row_count` state each page's exact coverage. Because the held count decides which empty rows are written, the cursor is HMAC-signed with the dedicated `ROW_CURSOR_KEY` secret and bound to the scope, file, tab, folder, version, grid size and next row, and expires after six hours. It grants nothing. A tampered, foreign or expired cursor returns `invalid_cursor`, a version or grid change returns `changed_during_read`, and a missing key refuses row mode with `cursor_unavailable` rather than serving unsigned pages; character mode is unaffected. A row that does not fit `max_chars` returns `row_too_large` and is never truncated; character mode can still read it in flagged parts. To continue a character-mode read whose pages end on a complete row, start row mode at the next row: the header and earlier rows are already in the prefix.
- Withheld sources. A historical or unapproved document that still sits in an approved folder is withheld by its Drive file id in the `WITHHELD_SOURCES` secret, a JSON array such as `["<file id>"]`. `discover` never lists it, including by name query, and reports only a `withheld` count. `read` refuses it with 403 before any Drive call. An unreadable or malformed list refuses every tool call instead of withholding nothing, and an empty array withholds nothing. The ids live in the Worker secret, not here, because this repository is public. The source's owning department decides which ids belong there.
- MCP OAuth sign-in continues to use the signed-in person's profile. Clients capable of supplying a static `Authorization: Bearer <department token>` header may instead use the same fixed department credential at `/mcp`. The OAuth provider's `resolveExternalToken` hook validates its hash only after no internal grant matches, binds it locally to `MCP_RESOURCE`, and supplies a department-only principal. Unknown credentials, missing hash configuration and unknown profiles are refused. No query, header, OAuth scope or tool argument can select that principal, and department calls cannot attest human client health checks. This opaque-credential compatibility route is not the normal MCP OAuth authorization flow and must not be described as MCP OAuth conformance. Credentials are never forwarded to Drive, which continues to use its separate read-only service account. Installed-client static-header support and persistent per-Project binding must be verified separately; instructions and conversation toggles are not that proof.

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
| `ROW_CURSOR_KEY` | HMAC key for spreadsheet row-page cursors, base64url of 32 random bytes, used for nothing else |

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
