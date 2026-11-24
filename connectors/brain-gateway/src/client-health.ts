// Client canaries share the gateway's KV and Sendblue line. No document bodies are retained.
import { z } from "zod";
import { CURRENT_DECISION_LOG } from "./brain.ts";
import type { ToolResult } from "./tools.ts";
import type { AlertEnv } from "./alert.ts";

export const CLIENTS = ["allison", "don"] as const;
export type Client = typeof CLIENTS[number];
export const MAX_AGE_MS = 26 * 60 * 60 * 1000;
const RUN_MS = 10 * 60 * 1000;
export const CHECKS = ["scopes", "discover", "rulebook", "decision_read", "decisions", "scope_denial", "cross_scope_denial"] as const;
type CheckName = typeof CHECKS[number];
type Observation = { ok: boolean; at: string; version?: string; count?: number; totalChars?: number; fileId?: string; code?: string };
type Run = { id: string; client: Client; startedAt: string };
type Status = "healthy" | "failed" | "missed";
export type Receipt = { runId: string; checkedAt: string; ok: boolean; checks: Record<CheckName, Observation | null>; conversationId?: string; runnerError?: "none" | "browser_error" | "cleanup_failed" };
type Notice = { state: Status; at: string; handle?: string; delivery?: string };
const uuid = z.uuid();
const finishBody = z.object({ conversationId: uuid.optional(), runnerError: z.enum(["none", "browser_error", "cleanup_failed"]).optional() }).strict();
const failedDelivery = new Set(["ERROR", "DECLINED"]);
const delivered = new Set(["DELIVERED", "READ", "RECEIVED"]);
const deliveryStatus = (data: any): string => typeof data.status === "string" ? data.status : typeof data.status?.status === "string" ? data.status.status : "UNKNOWN";
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });
const get = async <T>(kv: KVNamespace, key: string): Promise<T | null> => {
	const raw = await kv.get(key);
	return raw ? JSON.parse(raw) as T : null;
};
const base = (client: Client) => `health:chatgpt:${client}`;
const runKey = (run: string) => `health:chatgpt:run:${run}`;

export async function startRun(kv: KVNamespace, client: Client, now = new Date()): Promise<Run> {
	const active = await get<Run>(kv, `${base(client)}:active`);
	if (active && now.getTime() - Date.parse(active.startedAt) < RUN_MS) throw new Error("run_active");
	const run = { id: crypto.randomUUID(), client, startedAt: now.toISOString() };
	await kv.put(runKey(run.id), JSON.stringify(run), { expirationTtl: 86400 });
	await kv.put(`${base(client)}:active`, JSON.stringify(run), { expirationTtl: 600 });
	if (!await kv.get("health:chatgpt:activated")) await kv.put("health:chatgpt:activated", now.toISOString());
	return run;
}

/** Only the authenticated MCP handler calls this, after actual execution. HTTP tools cannot attest. */
export async function observeClientTool(kv: KVNamespace, email: string, tool: string, args: any, result: ToolResult, now = new Date()) {
	if (!uuid.safeParse(args?.health_run_id).success) return;
	const run = await get<Run>(kv, runKey(args.health_run_id));
	if (!run || email !== `${run.client}@expertpartners.com` || now.getTime() - Date.parse(run.startedAt) > RUN_MS) return;
	const r: any = result.ok ? result.result : null;
	let check: CheckName | undefined;
	let value: Observation = { ok: false, at: now.toISOString() };
	if (tool === "list_scopes") {
		check = "scopes";
		const keys: string[] = r?.scopes?.map((s: any) => s.scope) ?? [];
		value = { ...value, count: keys.length, ok: result.ok && keys.length === (run.client === "allison" ? 24 : 17) && keys.includes("ep-private") && (run.client === "allison" ? keys.includes("ag-core") : !keys.some(s => s.startsWith("ag-"))) };
	} else if (tool === "discover" && args.scope === (run.client === "allison" ? "ag-private" : "ag-core")) {
		check = "scope_denial";
		value.ok = !result.ok && result.status === 403 && result.detail === "scope_not_allowed";
	} else if (tool === "discover" && args.scope === "hq-core" && args.query === "Rulebook") {
		check = "discover";
		const f = r?.files?.find((f: any) => f.name.includes("HQ Rulebook"));
		value = { ...value, ok: result.ok && r.complete === true && !!f, count: r?.files?.length ?? 0, ...(f ? { fileId: f.id, version: f.version } : {}) };
	} else if (tool === "read" && args.scope === "ep-core") {
		check = "cross_scope_denial";
		value.fileId = args.id;
		value.ok = !result.ok && result.status === 403 && result.detail === "not_in_scope";
	} else if (tool === "read" && args.scope === "hq-core" && args.id === CURRENT_DECISION_LOG) {
		check = "decision_read";
		value.ok = result.ok && r?.file?.id === CURRENT_DECISION_LOG && r.totalChars > 0;
	} else if (tool === "read" && args.scope === "hq-core") {
		check = "rulebook";
		value.fileId = args.id;
		value.ok = result.ok && r?.file?.id === args.id && r.file.name?.includes("HQ Rulebook") && r.totalChars > 0;
	} else if (tool === "decisions") {
		check = "decisions";
		value.ok = result.ok && r?.file?.id === CURRENT_DECISION_LOG && r.authority === "current-log-only" && r.newest?.length > 0;
	}
	if (!check) return;
	if (result.ok && r?.file?.version) value.version = String(r.file.version);
	if (result.ok && r?.totalChars) value.totalChars = r.totalChars;
	if (!result.ok) value.code = result.detail ?? `http_${result.status}`;
	// Separate keys prevent parallel calls from overwriting one another. Retry replaces only its check.
	await kv.put(`${runKey(run.id)}:${check}`, JSON.stringify(value), { expirationTtl: 86400 });
}

export async function runReceipt(kv: KVNamespace, client: Client, id: string, now = new Date()): Promise<Receipt | null> {
	const run = await get<Run>(kv, runKey(id));
	if (!run || run.client !== client) return null;
	const checks = Object.fromEntries(await Promise.all(CHECKS.map(async name => [name, await get<Observation>(kv, `${runKey(id)}:${name}`)]))) as Receipt["checks"];
	// Join observed identities only after propagation, not during another MCP call's write.
	if (checks.rulebook) checks.rulebook.ok = checks.rulebook.ok && !!checks.discover?.fileId && checks.rulebook.fileId === checks.discover.fileId;
	if (checks.cross_scope_denial) checks.cross_scope_denial.ok = checks.cross_scope_denial.ok && !!checks.rulebook?.fileId && checks.cross_scope_denial.fileId === checks.rulebook.fileId;
	return { runId: id, checkedAt: now.toISOString(), ok: CHECKS.every(name => checks[name]?.ok === true), checks };
}

function noticeText(client: Client, state: Status, test: boolean) {
	const name = client === "allison" ? "Allison" : "Don";
	const prefix = test ? "TEST. " : "";
	if (state === "healthy") return `${prefix}${name}'s ChatGPT Drive Brain Gateway has recovered. All seven live client checks passed.`;
	if (state === "missed") return `${prefix}${name}'s daily ChatGPT Drive Brain Gateway check is missing. No check receipt arrived within 26 hours. Codex and the M2 check runner need attention. Server health alone cannot verify this connection.`;
	return `${prefix}${name}'s ChatGPT Drive Brain Gateway check failed. One or more live tools or access-boundary checks did not pass. The existing gateway monitor holds the failed check details.`;
}

/** Same transition and delivery path for production and explicitly labelled, isolated alert drills. */
export async function notifyClient(kv: KVNamespace, env: AlertEnv, client: Client, state: Status, test = false, doFetch: typeof fetch = fetch, now = new Date()) {
	const key = test ? `${base(client)}:drill-notice` : `${base(client)}:notice`;
	const previous = await get<Notice>(kv, key);
	if (!previous && state === "healthy") return { action: "quiet" };
	if (!env.SENDBLUE_API_KEY_ID || !env.SENDBLUE_API_SECRET || !env.ALERT_TO || !env.ALERT_FROM) return { action: "unconfigured" };
	const headers = { "content-type": "application/json", "sb-api-key-id": env.SENDBLUE_API_KEY_ID, "sb-api-secret-key": env.SENDBLUE_API_SECRET, "user-agent": "brain-gateway-alert" };
	let delivery = previous?.delivery;
	try {
		if (previous?.handle && !delivered.has(delivery ?? "") && !failedDelivery.has(delivery ?? "")) {
			const r = await doFetch(`https://api.sendblue.co/api/status?handle=${encodeURIComponent(previous.handle)}`, { headers });
			if (r.ok) {
				const d: any = await r.json();
				delivery = deliveryStatus(d);
				await kv.put(key, JSON.stringify({ ...previous, delivery }));
			}
		}
		if (previous?.state === state && !failedDelivery.has(delivery ?? "")) return { action: "quiet", ...previous, delivery };
		const r = await doFetch("https://api.sendblue.co/api/send-message", { method: "POST", headers, body: JSON.stringify({ number: env.ALERT_TO, from_number: env.ALERT_FROM, content: noticeText(client, state, test) }) });
		if (!r.ok) return { action: "send_failed" };
		const d: any = await r.json();
		if (!d.message_handle || failedDelivery.has(deliveryStatus(d)) || d.error_code) return { action: "send_failed" };
		const notice: Notice = { state, at: now.toISOString(), handle: d.message_handle, delivery: deliveryStatus(d) };
		await kv.put(key, JSON.stringify(notice));
		// Bounded metadata-only history, including drill receipts. No phone numbers or message bodies.
		await kv.put(`${key}:sent:${notice.handle}`, JSON.stringify(notice), { expirationTtl: 30 * 86400 });
		return { action: state === "healthy" ? "recovered" : "sent", ...notice };
	} catch { return { action: "send_failed" }; }
}

export function clientState(last: Receipt | null, activated: string, now = new Date()): Status {
	return now.getTime() - Date.parse(last?.checkedAt ?? activated) > MAX_AGE_MS ? "missed" : last && !last.ok ? "failed" : "healthy";
}

export async function evaluateClients(kv: KVNamespace, env: AlertEnv, now = new Date(), doFetch: typeof fetch = fetch) {
	const activated = await kv.get("health:chatgpt:activated");
	if (!activated) return { enabled: false, clients: [] };
	const clients = [];
	for (const client of CLIENTS) {
		const last = await get<Receipt>(kv, `${base(client)}:last`);
		const state = clientState(last, activated, now);
		const alert = await notifyClient(kv, env, client, state, false, doFetch, now);
		clients.push({ client, state, last, alert });
	}
	return { enabled: true, checkedAt: now.toISOString(), maxAgeHours: 26, clients };
}

/** Called only after the existing leader bearer authentication. It never accepts a claimed PASS. */
export async function clientHealthApi(request: Request, kv: KVNamespace, env: AlertEnv): Promise<Response> {
	const path = new URL(request.url).pathname;
	if (path === "/api/health/clients" && request.method === "GET") {
		const clients = await Promise.all(CLIENTS.map(async client => ({ client, last: await get(kv, `${base(client)}:last`), lastFailure: await get(kv, `${base(client)}:lastFailure`), notice: await get(kv, `${base(client)}:notice`), drillNotice: await get(kv, `${base(client)}:drill-notice`) })));
		return json({ enabled: !!await kv.get("health:chatgpt:activated"), maxAgeHours: 26, clients });
	}
	if (Number(request.headers.get("content-length") ?? 0) > 2048) return json({ error: "body too large" }, 413);
	let body: unknown;
	try { body = request.method === "POST" ? JSON.parse((await request.text()).slice(0, 2049) || "{}") : {}; } catch { return json({ error: "invalid body" }, 400); }
	if (path === "/api/health/clients/evaluate" && request.method === "POST") return json(await evaluateClients(kv, env));
	if (path === "/api/health/clients/drill" && request.method === "POST") {
		const parsed = z.object({ client: z.enum(CLIENTS), state: z.enum(["healthy", "failed", "missed"]) }).strict().safeParse(body);
		if (!parsed.success) return json({ error: "invalid drill" }, 400);
		const baseline = await get<Receipt>(kv, `${base(parsed.data.client)}:last`);
		if (!baseline?.ok) return json({ error: "a real passing client check is required before a drill" }, 409);
		const now = new Date();
		const fixture = { ...baseline, ok: parsed.data.state !== "failed", checkedAt: parsed.data.state === "missed" ? new Date(now.getTime() - MAX_AGE_MS - 1).toISOString() : now.toISOString() };
		// Exercise the real deadline evaluator and notification function, without touching production evidence.
		const state = clientState(fixture, now.toISOString(), now);
		return json({ test: true, evaluatedState: state, baselineRunId: baseline.runId, ...await notifyClient(kv, env, parsed.data.client, state, true) });
	}
	const m = path.match(/^\/api\/health\/clients\/(allison|don)\/(start|runs\/([\w-]+)(\/finish)?)$/);
	if (!m) return json({ error: "not found" }, 404);
	const client = m[1] as Client;
	if (m[2] === "start" && request.method === "POST") {
		try { return json(await startRun(kv, client)); } catch { return json({ error: "run_active" }, 409); }
	}
	if (!uuid.safeParse(m[3]).success) return json({ error: "invalid run" }, 400);
	const receipt = await runReceipt(kv, client, m[3]);
	if (!receipt) return json({ error: "not found" }, 404);
	if (request.method === "GET" && !m[4]) return json(receipt);
	if (request.method !== "POST" || !m[4]) return json({ error: "method not allowed" }, 405);
	const parsed = finishBody.safeParse(body);
	if (!parsed.success) return json({ error: "invalid receipt" }, 400);
	const previous = await get<Receipt>(kv, `${base(client)}:last`);
	if (previous?.runId === receipt.runId) return json({ receipt: previous, replay: true });
	const active = await get<Run>(kv, `${base(client)}:active`);
	if (!active || active.id !== receipt.runId) return json({ error: "run no longer active" }, 409);
	Object.assign(receipt, parsed.data);
	if (receipt.runnerError && receipt.runnerError !== "none") receipt.ok = false;
	await kv.put(`${base(client)}:last`, JSON.stringify(receipt));
	if (!receipt.ok) await kv.put(`${base(client)}:lastFailure`, JSON.stringify(receipt));
	await kv.delete(`${base(client)}:active`);
	return json({ receipt, alert: await notifyClient(kv, env, client, receipt.ok ? "healthy" : "failed") });
}
