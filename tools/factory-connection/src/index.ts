// Factory connection: one Worker serving Claude and ChatGPT (remote MCP at /mcp, OAuth through
// Cloudflare Access, Allison only) and the Expert Partners Hub (bearer HTTP at /api).
import { env } from "cloudflare:workers";
import OAuthProvider from "@cloudflare/workers-oauth-provider";
import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler, getMcpAuthContext } from "agents/mcp/server";
import { handleAccessRequest } from "./access-handler";
import { isAllowedEmail } from "./allow";
import { runTool, TOOLS } from "./tools";
import type { Props } from "./workers-oauth-utils";

const INSTRUCTIONS = `Factory connection for Expert Partners. Before starting new work, call find_owner to see whether a Workstream or session already owns it, and send new work for a Workstream to its orchestrator with post_message. Bounded jobs start with start_and_watch or create_session, named "Section - Mission" on the first line. Defaults are Auto Model and High autonomy. Use interactionMode "spec" when architecture is unclear. Ember M2 takes all browser and visible work. Allison M4 takes invisible background work only. Deliverables land in Drive (docs) or GitHub (code), never only in a Factory shared folder.`;

function createServer() {
	const server = new McpServer({ name: "Factory connection", version: "1.0.0" }, { instructions: INSTRUCTIONS });
	const props = getMcpAuthContext()?.props as Props | undefined;
	if (!props || !isAllowedEmail(env.ALLOWED_EMAILS, props.email)) return server;
	for (const t of TOOLS) {
		server.registerTool(
			t.name,
			{
				description: t.description,
				inputSchema: t.schema,
				annotations: { readOnlyHint: !!t.readOnly, openWorldHint: true },
			},
			async (args: unknown) => {
				const r = await runTool(t.name, args, env);
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
	if (!bindings.HUB_API_TOKEN || !token || !safeEqual(token, bindings.HUB_API_TOKEN)) {
		return json({ error: "unauthorized" }, 401);
	}
	if (request.method === "GET" && url.pathname === "/api/tools") {
		return json({ tools: TOOLS.map((t) => ({ name: t.name, description: t.description, readOnly: !!t.readOnly })) });
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
		const r = await runTool(m[1], args, bindings);
		return json(r.ok ? { result: r.result } : { error: r.error, detail: (r as any).detail }, r.status);
	}
	return json({ error: "not found" }, 404);
}

const defaultHandler = {
	async fetch(request: Request, bindings: Env, ctx: ExecutionContext) {
		const { pathname } = new URL(request.url);
		if (pathname === "/health") return json({ ok: true, service: "factory-connection", tools: TOOLS.length });
		if (pathname.startsWith("/api/")) return handleHubApi(request, bindings);
		return handleAccessRequest(request, bindings as any, ctx);
	},
};

export default new OAuthProvider<Env>({
	apiHandler: { fetch: (req: Request, b: Env, ctx: ExecutionContext) => mcpHandler(req, b, ctx) },
	apiRoute: "/mcp",
	authorizeEndpoint: "/authorize",
	clientRegistrationEndpoint: "/register",
	defaultHandler: defaultHandler as any,
	tokenEndpoint: "/token",
	resourceMetadata: { resource: env.MCP_RESOURCE },
});
