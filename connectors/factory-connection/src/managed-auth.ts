import type { EmaOptions } from "@cloudflare/workers-oauth-provider";
import { isAllowedEmail } from "./allow.ts";

// The normal OAuth flow remains available. This additional grant accepts only
// the configured Claude organization and still applies the service's allowlist.
export const CLAUDE_CLIENT = "https://claude.ai/oauth/mcp-oauth-client-metadata";
export type ManagedEnv = { CLAUDE_TRUSTED_ISSUER: string; MCP_RESOURCE: string; ALLOWED_EMAILS: string };
export const managedAuthorization: EmaOptions<ManagedEnv> = {
  allowPublicClients: true, // Claude's CIMD client is public; its signed ID-JAG binds the client.
  trustedIssuers: async ({ iss, env }) => {
    const issuer = env.CLAUDE_TRUSTED_ISSUER;
    if (!issuer || !/^https:\/\/identity\.anthropic\.com\/issuers\/iss_[a-z0-9]+$/.test(issuer)
      || iss !== issuer) return null;
    return { issuer, jwksUri: `${issuer}/jwks.json`, algorithms: ["ES256", "RS256"] };
  },
  mapClaims: async ({ claims, env, resource, requestedScope }) => {
    if (claims.iss !== env.CLAUDE_TRUSTED_ISSUER
      || resource !== env.MCP_RESOURCE || typeof claims.email !== "string"
      || !isAllowedEmail(env.ALLOWED_EMAILS, claims.email)) return null;
    if (requestedScope.some(scope => scope !== "mcp")) return null;
    const email = claims.email.trim().toLowerCase();
    return {
      userId: `claude-${encodeURIComponent(claims.sub)}`,
      scope: requestedScope.length ? requestedScope : ["mcp"],
      accessTokenTTL: 900,
      metadata: { issuer: claims.iss, subject: claims.sub },
      props: { email, login: claims.sub, name: email, enterprise: true },
    };
  },
};
