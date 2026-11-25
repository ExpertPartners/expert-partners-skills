// Drive brain gateway: one read-only Worker serving Claude, ChatGPT and Factory (remote MCP at /mcp,
// OAuth through Cloudflare Access, Allison only) and the Expert Partners Hub (bearer HTTP at /api).
import { maybeAlert, type AlertEnv } from "./alert.ts";
import { clientHealthApi, evaluateClients, observeClientTool } from "./client-health.ts";
import { z } from "zod";
import { env } from "cloudflare:workers";
import OAuthProvider from "@cloudflare/workers-oauth-provider";
import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler, getMcpAuthContext } from "agents/mcp/server";
import { handleAccessRequest } from "./access-handler";
import { departmentForToken, DEPARTMENTS } from "./access.ts";
import { lastResults, runDeepCheck, storeResult } from "./health.ts";
import { driveFetch } from "./google.ts";
import { isAllowedEmail } from "./allow";
import { runTool, TOOLS } from "./tools";
import type { Principal } from "./access.ts";
import type { Props } from "./workers-oauth-utils";

const INSTRUCTIONS = `Read-only access to the Expert Partners Business Brains in Google Drive (HQ, EP, AG). Start with list_scopes, then discover a scope to find documents, then read one by id. Read the Rulebook and Decision Log from hq-core before relying on any rule. Reads return the live document, never a copy, and fail closed when a complete verified read is not possible. Nothing here can write.`;

function createServer() {
	const server = new McpServer({ name: "Drive brain gateway", version: "1.0.0" }, { instructions: INSTRUCTIONS });
	const props = getMcpAuthContext()?.props as Props | undefined;
	if (!props || !isAllowedEmail(env.ALLOWED_EMAILS, props.email)) return server;
	for (const t of TOOLS) {
		server.registerTool(
			t.name,
			{
				description: t.description,
				inputSchema: t.schema.extend({ health_run_id: z.uuid().optional().describe("Only for an authorized ChatGPT health check: the temporary run id supplied by the existing monitor. Omit in normal business work.") }),
				annotations: { readOnlyHint: true, openWorldHint: true },
			},
			async (args: unknown) => {
				const r = await runTool(t.name, args, env, undefined, { kind: "person", email: props.email });
				try { await observeClientTool(env.OAUTH_KV, props.email, t.name, args, r, undefined, env.ALLOWED_SCOPES); }
				catch { console.error("[brain-gateway] client health observation failed"); }
				const payload = r.ok ? r.result : { error: r.error, status: r.status, detail: (r as any).detail };
				return { content: [{ type: "text" as const, text: JSON.stringify(payload, null, 2) }], isError: !r.ok };
			},
		);
	}
	return server;
}

const mcpHandler = createMcpHandler(createServer);

function json(data: unknown, status = 200) {
	return new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });
}

/** Constant-time compare for the Hub bearer token. */
function safeEqual(a: string, b: string) {
	const enc = new TextEncoder();
	const x = enc.encode(a);
	const y = enc.encode(b);
	if (x.length !== y.length) return false;
	let diff = 0;
	for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
	return diff === 0;
}

async function handleHubApi(request: Request, bindings: Env) {
	const url = new URL(request.url);
	const auth = request.headers.get("authorization") ?? "";
	const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
	// Two kinds of bearer. The Hub token acts as Allison and may only narrow itself with
	// X-Brain-Department. A department token is fixed to its department and cannot be widened.
	let principal: Principal | null = null;
	if (bindings.HUB_API_TOKEN && token && safeEqual(token, bindings.HUB_API_TOKEN)) {
		const dept = request.headers.get("x-brain-department") ?? undefined;
		if (dept && !DEPARTMENTS[dept]) return json({ error: "unknown department" }, 400);
		principal = { kind: "person", email: "allison@expertpartners.com", department: dept };
	} else {
		const id = await departmentForToken((bindings as any).DEPARTMENT_TOKEN_HASHES, token);
		if (id) principal = { kind: "department", id };
	}
	if (!principal) return json({ error: "unauthorized" }, 401);
	if (url.pathname.startsWith("/api/health/clients")) {
		if (principal.kind !== "person" || principal.department) return json({ error: "forbidden" }, 403);
		return clientHealthApi(request, bindings.OAUTH_KV, bindings as unknown as AlertEnv);
	}
	// Health: leaders only. GET shows the last stored daily result and the last failure; ?run=1 runs it now.
	if (request.method === "GET" && url.pathname === "/api/health/deep") {
		if (principal.kind !== "person" || principal.department) return json({ error: "forbidden" }, 403);
		if (url.searchParams.get("run") === "1") {
			const result = await runDeepCheck(bindings.ALLOWED_SCOPES, driveFetch(bindings.GOOGLE_SA_KEY));
			await storeResult(bindings.OAUTH_KV, result);
		}
		return json(await lastResults(bindings.OAUTH_KV));
	}
	if (request.method === "GET" && url.pathname === "/api/tools") {
		return json({ tools: TOOLS.map((t) => ({ name: t.name, description: t.description, readOnly: true })) });
	}
	const m = url.pathname.match(/^\/api\/tools\/([a-z_]+)$/);
	if (request.method === "POST" && m) {
		let args: unknown = {};
		try {
			const text = await request.text();
			args = text ? JSON.parse(text) : {};
		} catch {
			return json({ error: "body must be JSON" }, 400);
		}
		const r = await runTool(m[1], args, bindings, undefined, principal);
		return json(r.ok ? { result: r.result } : { error: r.error, detail: (r as any).detail }, r.status);
	}
	return json({ error: "not found" }, 404);
}

const defaultHandler = {
	async fetch(request: Request, bindings: Env, ctx: ExecutionContext) {
		const { pathname } = new URL(request.url);
		if (pathname === "/health") return json({ ok: true, service: "brain-gateway", tools: TOOLS.length });
		if (pathname.startsWith("/api/")) return handleHubApi(request, bindings);
		return handleAccessRequest(request, bindings as any, ctx);
	},
};

const provider = new OAuthProvider<Env>({
	apiHandler: { fetch: (req: Request, b: Env, ctx: ExecutionContext) => mcpHandler(req, b, ctx) },
	apiRoute: "/mcp",
	authorizeEndpoint: "/authorize",
	clientRegistrationEndpoint: "/register",
	defaultHandler: defaultHandler as any,
	tokenEndpoint: "/token",
	resourceMetadata: { resource: env.MCP_RESOURCE },
});

export default {
	fetch: (request: Request, bindings: Env, ctx: ExecutionContext) => provider.fetch(request, bindings, ctx),
	// Daily live check of the Business Brain connection (cron in wrangler.jsonc).
	async scheduled(event: ScheduledController, bindings: Env, ctx: ExecutionContext) {
		ctx.waitUntil(
			(async () => {
				if (event.cron === "15 * * * *") {
					console.log("[brain-gateway] ChatGPT client checks:", JSON.stringify(await evaluateClients(bindings.OAUTH_KV, bindings as unknown as AlertEnv)));
					return;
				}
				const result = await runDeepCheck(bindings.ALLOWED_SCOPES, driveFetch(bindings.GOOGLE_SA_KEY));
				await storeResult(bindings.OAUTH_KV, result);
				if (!result.ok) console.error("[brain-gateway] daily check failed:", JSON.stringify(result.checks.filter((c) => !c.ok)));
				console.log("[brain-gateway] alert:", await maybeAlert(bindings.OAUTH_KV, bindings as unknown as AlertEnv, result));
			})(),
		);
	},
};
