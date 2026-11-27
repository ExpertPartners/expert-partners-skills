import type { EmaOptions } from "@cloudflare/workers-oauth-provider";
import { isAllowedEmail } from "./allow.ts";

// The normal OAuth flow remains available. This additional grant accepts only
// the configured Claude organization and still applies the service's allowlist.
export const CLAUDE_CLIENT = "https://claude.ai/oauth/mcp-oauth-client-metadata";
export type ManagedEnv = { CLAUDE_TRUSTED_ISSUER: string; MCP_RESOURCE: string; ALLOWED_EMAILS: string };
export const managedAuthorization: EmaOptions<ManagedEnv> = {
  allowPublicClients: true, // Claude's CIMD client is public; its signed ID-JAG binds the client.
  trustedIssuers: async ({ iss, env, clientInfo }) => {
    const issuer = env.CLAUDE_TRUSTED_ISSUER;
    if (!issuer || !/^https:\/\/identity\.anthropic\.com\/issuers\/iss_[a-z0-9]+$/.test(issuer)
      || iss !== issuer || clientInfo.clientId !== CLAUDE_CLIENT) return null;
    return { issuer, jwksUri: `${issuer}/jwks.json`, algorithms: ["ES256", "RS256"] };
  },
  mapClaims: async ({ claims, env, resource, clientInfo, requestedScope }) => {
    if (clientInfo.clientId !== CLAUDE_CLIENT || claims.iss !== env.CLAUDE_TRUSTED_ISSUER
      || resource !== env.MCP_RESOURCE || typeof claims.email !== "string"
      || !isAllowedEmail(env.ALLOWED_EMAILS, claims.email)) return null;
    const email = claims.email.trim().toLowerCase();
    return {
      userId: `claude-${encodeURIComponent(claims.sub)}`,
      scope: requestedScope,
      accessTokenTTL: 900,
      metadata: { issuer: claims.iss, subject: claims.sub },
      props: { email, login: claims.sub, name: email, enterprise: true },
    };
  },
};
