import { test } from "node:test";
import assert from "node:assert/strict";
import { registerHooks } from "node:module";
import { resolveDepartmentToken, mcpPrincipal } from "../src/mcp-principal.ts";
import { COMPANY_CORES, DEPARTMENTS, effectiveScopes, sha256Hex } from "../src/access.ts";
import { BRAIN_FOLDERS } from "../src/brain.ts";
import { runTool } from "../src/tools.ts";

// The provider's auth path is real; only its unused Worker RPC base needs a Node shim.
const hook = registerHooks({
	resolve(specifier, context, next) {
		return specifier === "cloudflare:workers"
			? { url: "data:text/javascript,export class WorkerEntrypoint {}", shortCircuit: true }
			: next(specifier, context);
	},
});
const { default: OAuthProvider } = await import("@cloudflare/workers-oauth-provider");
hook.deregister();

const resource = "https://gw.invalid/mcp";
const emails = "allison@expertpartners.com,don@expertpartners.com";
const allowed = Object.keys(BRAIN_FOLDERS).filter(s => s !== "ag-private").join(",");
async function fixture() {
	const map: Record<string, string> = {};
	for (const id of Object.keys(DEPARTMENTS)) map[await sha256Hex(`synthetic-${id}`)] = id;
	const env = { MCP_RESOURCE: resource, DEPARTMENT_TOKEN_HASHES: JSON.stringify(map), OAUTH_KV: { get: async () => null } };
	const provider = new OAuthProvider({
		apiRoute: "/mcp", authorizeEndpoint: "/authorize", tokenEndpoint: "/token",
		resourceMetadata: { resource }, resolveExternalToken: resolveDepartmentToken,
		defaultHandler: { fetch: async () => new Response("not found", { status: 404 }) },
		apiHandler: { fetch: async (_req: Request, _env: unknown, ctx: any) => Response.json(mcpPrincipal(ctx.props, emails)) },
	});
	const request = (token?: string, extra: Record<string, string> = {}) => provider.fetch(new Request(resource, {
		method: "POST", headers: { ...(token ? { authorization: `Bearer ${token}` } : {}), ...extra },
	}), env as any, {} as any);
	return { env, request };
}

test("real OAuth provider accepts all fixed actors, ignores identity headers and refuses invalid credentials", async () => {
	const { env, request } = await fixture();
	for (const id of Object.keys(DEPARTMENTS)) {
		const r = await request(`synthetic-${id}`, { "x-brain-department": "hq-cfo", "x-email": "allison@expertpartners.com" });
		assert.equal(r.status, 200);
		assert.deepEqual(await r.json(), { kind: "department", id });
	}
	for (const token of [undefined, "unknown", "__proto__", "user:grant:revoked"]) {
		const r = await request(token);
		assert.equal(r.status, 401);
		assert.match(r.headers.get("www-authenticate")!, /Bearer/);
	}
	for (const hashes of [undefined, "null", "[]", "false", "{", JSON.stringify({ [await sha256Hex("synthetic-ep-cro")]: "__proto__" })]) {
		env.DEPARTMENT_TOKEN_HASHES = hashes as any;
		assert.equal((await request("synthetic-ep-cro")).status, 401);
	}
});

test("existing person props preserve allowlist and Don boundary; malformed department props cannot fall back to a leader", () => {
	for (const email of ["allison@expertpartners.com", "don@expertpartners.com"])
		assert.deepEqual(mcpPrincipal({ email, accessToken: "synthetic", login: "user", name: "User" }, emails), { kind: "person", email });
	assert.equal(mcpPrincipal({ email: "unknown@expertpartners.com" }, emails), null);
	for (const department of [undefined, "__proto__", "constructor", "nope"])
		assert.equal(mcpPrincipal({ kind: "department", department, email: "allison@expertpartners.com" }, emails), null);
	assert.ok(effectiveScopes(allowed, mcpPrincipal({ email: "don@expertpartners.com" }, emails)!).every(s => !s.startsWith("ag-")));
});

test("concurrent department and OAuth person contexts do not bleed; resolved actors reach all Cores and no ungranted non-Core", async () => {
	const { env } = await fixture();
	await Promise.all(Array.from({ length: 3 }, () => Object.keys(DEPARTMENTS)).flat().map(async id => {
		const resolved = await resolveDepartmentToken({ token: `synthetic-${id}`, env });
		assert.equal(resolved?.audience, resource);
		const principal = mcpPrincipal(resolved!.props, emails)!;
		const person = mcpPrincipal({ email: "don@expertpartners.com" }, emails)!;
		assert.deepEqual(principal, { kind: "department", id });
		assert.equal(person.kind, "person");
		for (const core of COMPANY_CORES) {
			const discovered = await runTool("discover", { scope: core, department: "hq-cfo" }, { ALLOWED_SCOPES: allowed }, async () => Response.json({ files: [] }), principal);
			assert.equal(discovered.status, 200);
			const source = { id: "synthetic-source", name: "Synthetic", version: "1", mimeType: "application/vnd.google-apps.document", modifiedTime: "2026-11-27T00:00:00Z" };
			const read = await runTool("read", { scope: core, id: source.id }, { ALLOWED_SCOPES: allowed }, async path =>
				{
				const url = new URL(path, "https://drive.invalid");
				if (url.pathname === "/drive/v3/files") return Response.json({ files: [source] });
				return url.pathname.endsWith("/export") ? new Response("Synthetic content") : Response.json(source);
			}, principal);
			assert.equal(read.status, 200, JSON.stringify(read));
			assert.equal((read as any).result.nextOffset, null);
		}
		for (const scope of Object.keys(BRAIN_FOLDERS).filter(s => !effectiveScopes(allowed, principal).includes(s as any))) {
			const denied = await runTool("discover", { scope }, { ALLOWED_SCOPES: allowed }, async () => { throw new Error("Denied request reached Drive"); }, principal);
			assert.equal(denied.status, 403);
		}
	}));
});

test("consolidated legacy marketing keys keep folder identity without adding either scope to unrelated profiles", () => {
	assert.equal(BRAIN_FOLDERS["ag-marketing"], BRAIN_FOLDERS["ag-personal-marketing"]);
	assert.equal(BRAIN_FOLDERS["ag-core"], BRAIN_FOLDERS["ag-personal-core"]);
	for (const id of ["ep-cro", "ag-cro", "hq-cfo"]) {
		const scopes = effectiveScopes(allowed, { kind: "department", id });
		assert.ok(!scopes.includes("ag-marketing") && !scopes.includes("ag-personal-marketing"));
	}
});
