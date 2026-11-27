import { test } from "node:test";
import assert from "node:assert/strict";
import { CLAUDE_CLIENT, managedAuthorization as auth, type ManagedEnv } from "../src/managed-auth.ts";
const issuer = "https://identity.anthropic.com/issuers/iss_test";
const env: ManagedEnv = { CLAUDE_TRUSTED_ISSUER: issuer, MCP_RESOURCE: "https://example.test/mcp", ALLOWED_EMAILS: "allison@example.test,don@example.test" };
const input = { env, clientInfo: { clientId: CLAUDE_CLIENT, redirectUris: [], tokenEndpointAuthMethod: "none" as const }, request: new Request("https://example.test/token") };
const claims = { iss: issuer, sub: "user:123", aud: "https://example.test", client_id: CLAUDE_CLIENT, jti: "unique", exp: 9999999999, iat: 9999999900, email: "don@example.test", resource: env.MCP_RESOURCE };
test("issuer selection pins organization, client, signing algorithm and public-key endpoint", async () => {
  assert.deepEqual(await auth.trustedIssuers({ ...input, iss: issuer }), { issuer, jwksUri: `${issuer}/jwks.json`, algorithms: ["ES256", "RS256"] });
  for (const iss of ["https://attacker.test", issuer + "/", issuer + "evil"])
    assert.equal(await auth.trustedIssuers({ ...input, iss }), null);
  assert.equal(await auth.trustedIssuers({ ...input, iss: issuer, clientInfo: { ...input.clientInfo, clientId: "other" } }), null);
  assert.equal(await auth.trustedIssuers({ ...input, iss: issuer, env: { ...env, CLAUDE_TRUSTED_ISSUER: "https://attacker.test" } }), null);
});
test("validated claims retain member identity and cannot expand the existing allowlist or resource", async () => {
  const mapped = await auth.mapClaims({ ...input, claims, resource: env.MCP_RESOURCE, requestedScope: ["read"] });
  assert.equal(mapped?.userId, "claude-user%3A123");
  assert.deepEqual(mapped?.props, { email: "don@example.test", login: claims.sub, name: "don@example.test", enterprise: true });
  assert.deepEqual(mapped?.scope, ["read"]);
  for (const email of ["other@example.test", "don@example.test.evil", undefined])
    assert.equal(await auth.mapClaims({ ...input, claims: { ...claims, email }, resource: env.MCP_RESOURCE, requestedScope: [] }), null);
  assert.equal(await auth.mapClaims({ ...input, claims, resource: "https://other.test/mcp", requestedScope: [] }), null);
  assert.equal(await auth.mapClaims({ ...input, claims, env: { ...env, ALLOWED_EMAILS: "allison@example.test" }, resource: env.MCP_RESOURCE, requestedScope: [] }), null);
});
