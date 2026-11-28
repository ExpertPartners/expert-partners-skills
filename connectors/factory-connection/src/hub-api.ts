import { runTool, TOOLS, type ToolEnv } from "./tools.ts";

export function json(data: unknown, status = 200) {
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

export async function handleHubApi(request: Request, bindings: ToolEnv & { HUB_API_TOKEN?: string }) {
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
