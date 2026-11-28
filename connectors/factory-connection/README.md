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
| `HUB_SYSTEM_HEALTH_REFRESH_TOKEN` (optional) | Existing dedicated Hub System health refresh credential, not the gateway or Factory API token |

Load or rotate them by piping from `op` into `wrangler secret bulk`, never on a command line.

## Source decision authority

Every dispatch checks the existing owning assignments, installed marketplace and live gap dispositions. Source recovery is resolved separately from implementation ownership. The private routing seed pins `decisionLogUrl`, `founderDecisionActor` and `decisionReceiptDigest`. Gap URLs and status edits never supply founder authority.

The existing decision document contains `SOURCE RECOVERY DECISION BEGIN v1` / `SOURCE RECOVERY DECISION END` JSON receipts. Each names an ID, recording time, action, founder, exact predecessor, capabilities and aliases, and provenance containing a unique human entry heading, its actual instruction quote and canonical source URL. A reopening must reference the active closure and a separate human entry with the explicit statement `FOUNDER explicitly superseded source recovery closure RECEIPT_ID for CAPABILITY_ID.` An actor label or copied closure instruction is insufficient.

The trusted digest covers the complete canonical receipt history. Reads never advance it. When the existing decision-writing owner records an evidenced founder decision, that same owner validates the full chain, retains every historical receipt and alias, updates the existing private seed's closed-item fallback projection, then publishes the matching digest. Preserve current implementation owners, assignments and approval state. Publish the fallback closures and digest in the same existing seed save and verify readback. This is an integrity publication, not an approval or another tracker. Never refresh the digest merely to silence a mismatch.

Missing, edited, truncated, replayed, forked, unsupported or unstable authority fails source recovery closed. Unrelated document edits do not change the canonical receipt digest. Approved implementation may continue with its current live owner during a source-authority outage. A removed implementation row retains its known source closure but cannot invent an owner or approval. IDs and registered outcome aliases are resolved independently; conflicts and ambiguous outcomes cannot dispatch work.

## Daily System health refresh

`refresh_hub_system_health({})` uses the existing MCP and bearer-authenticated HTTP surfaces. It makes one bodyless POST to the fixed Hub System health endpoint with the dedicated server-side secret. Call it only after the existing daily routine has saved and read back its real pass or fail receipt. It adds no scheduler, shell executor, arbitrary URL, credential input or source-body output.

The action returns only the six source outcomes, `updated`, `unavailable` or `failed`. Updated means the snapshot was stored, not that a brain is healthy. Missing configuration fails closed. Upstream refusals and invalid receipts fail without exposing their bodies; a 409 is returned without retry. The 45-second deadline accommodates the Hub's 30-second source-read deadline. A network failure or timeout has an uncertain outcome and must not trigger a blind repeat.

The request uses Workers-supported `redirect: "manual"`. Every non200 response, including redirects, is refused without following `Location` or forwarding the dedicated bearer to another destination. Workers does not implement `redirect: "error"` and throws before sending it. See the [Workers Request reference](https://developers.cloudflare.com/workers/runtime-apis/request/).

`npm test` includes actual Miniflare/workerd regression tests, using the compatibility date and flags from `wrangler.jsonc`. They bundle the real HTTP handler and registered action and intercept all outbound traffic locally. These tests exercise request construction, a successful sanitized receipt, redirect refusals, non200 responses, malformed and oversized bodies, and rejected caller overrides. They never call production.

The existing service publisher binds the already-approved dedicated credential from 1Password to the optional Worker secret and deploys through the normal service release. It must match the Hub's dedicated refresh secret, never its gateway token. This source change does not activate that binding, alter Hub production settings or prove future daily execution. After activation, the same scheduled task must prove save-before-refresh through a real scheduled run.

## Develop and deploy

```bash
cd connectors/factory-connection
npm ci
npm run type-check
npm test
CLOUDFLARE_ACCOUNT_ID=<account id> CLOUDFLARE_API_TOKEN=op://Automation/Cloudflare\ Workers\ Deploy\ Token/credential op run -- npx wrangler deploy
```

The base comes from Cloudflare's MIT licensed `remote-mcp-cf-access` demo (cloudflare/ai), with an email allowlist and an ID token audience check added.

## Claude-issued Auto Connect

The token endpoint also supports the JWT bearer ID-JAG grant through the pinned OAuth provider library. Configure `CLAUDE_TRUSTED_ISSUER` with the organization issuer shown in Claude. Only that exact issuer is trusted. Registered OAuth clients remain authenticated by the provider, and every signed ID-JAG must bind to the requesting client's exact ID. The library validates signature, audience, client binding, resource, lifetime and replay markers; the claims mapper independently enforces `ALLOWED_EMAILS` and the canonical MCP resource. Member identity remains in encrypted token props, so existing per-person resource restrictions still apply. Public clients use the same signature-verified, audience- and client-bound assertions; issued tokens last 15 minutes with no refresh token. KV replay protection is eventually consistent, not a globally atomic single-use guarantee.

This does not grant a new person access or change existing browser OAuth grants. Configure Claude through its visible organization settings after deployment, then verify the saved Auto Connect state.
