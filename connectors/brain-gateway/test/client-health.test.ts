import assert from "node:assert/strict";
import { test } from "node:test";
import { CHECKS, MAX_AGE_MS, clientHealthApi, clientState, evaluateClients, notifyClient, observeClientTool, runReceipt, startRun, type Receipt } from "../src/client-health.ts";
import { CURRENT_DECISION_LOG } from "../src/brain.ts";

function kv() {
	const values = new Map<string, string>();
	return { values, get: async (k: string) => values.get(k) ?? null, put: async (k: string, v: string) => { values.set(k, v); }, delete: async (k: string) => { values.delete(k); } } as unknown as KVNamespace & { values: Map<string, string> };
}
const env = { SENDBLUE_API_KEY_ID: "id", SENDBLUE_API_SECRET: "secret", ALERT_TO: "+15550001111", ALERT_FROM: "+15550002222" };
const now = new Date("2026-11-24T10:30:00Z");
const ok = (result: unknown) => ({ ok: true as const, status: 200 as const, result });
const deny = (detail: string) => ({ ok: false as const, status: 403, error: "denied", detail });
const sends: string[] = [];
const send = (async (url: string | URL | Request, init?: RequestInit) => {
	if (String(url).includes("/status?")) return new Response(JSON.stringify({ status: "DELIVERED" }));
	sends.push(JSON.parse(String(init?.body)).content);
	return new Response(JSON.stringify({ status: "QUEUED", message_handle: `test-${sends.length}` }));
}) as typeof fetch;

test("PASS requires actual authenticated observations for every check, not a caller's claim", async () => {
	const k = kv(); const run = await startRun(k, "allison", now);
	assert.equal((await runReceipt(k, "allison", run.id, now))?.ok, false);
	const args = { health_run_id: run.id };
	await observeClientTool(k, "don@expertpartners.com", "list_scopes", args, ok({ scopes: [] }), now);
	assert.equal((await runReceipt(k, "allison", run.id, now))?.checks.scopes, null);
	const scopes = Array.from({ length: 22 }, (_, i) => `hq-${i}`).concat(["ep-private", "ag-core"]);
	await observeClientTool(k, "allison@expertpartners.com", "list_scopes", args, ok({ scopes: scopes.map(scope => ({ scope })) }), now);
	await observeClientTool(k, "allison@expertpartners.com", "discover", { ...args, scope: "hq-core", query: "Rulebook" }, ok({ complete: true, files: [{ id: "rulebook", name: "HQ Rulebook", version: "1" }] }), now);
	await observeClientTool(k, "allison@expertpartners.com", "read", { ...args, scope: "hq-core", id: "rulebook" }, ok({ file: { id: "rulebook", name: "HQ Rulebook", version: "1" }, totalChars: 5000, text: "DO NOT STORE THIS BODY" }), now);
	await observeClientTool(k, "allison@expertpartners.com", "read", { ...args, scope: "hq-core", id: CURRENT_DECISION_LOG }, ok({ file: { id: CURRENT_DECISION_LOG, version: "2" }, totalChars: 6000 }), now);
	await observeClientTool(k, "allison@expertpartners.com", "decisions", args, ok({ file: { id: CURRENT_DECISION_LOG, version: "2" }, authority: "current-log-only", newest: [{ date: "2026-11-24" }] }), now);
	await observeClientTool(k, "allison@expertpartners.com", "discover", { ...args, scope: "ag-private" }, deny("scope_not_allowed"), now);
	await observeClientTool(k, "allison@expertpartners.com", "read", { ...args, scope: "ep-core", id: "rulebook" }, deny("not_in_scope"), now);
	const receipt = await runReceipt(k, "allison", run.id, now);
	assert.equal(receipt?.ok, true);
	assert.equal(Object.keys(receipt!.checks).length, CHECKS.length);
	assert.ok(!JSON.stringify([...k.values.values()]).includes("DO NOT STORE"));
	assert.equal(await runReceipt(k, "don", run.id, now), null);
});

test("overlapping and expired runs cannot mint healthy receipts", async () => {
	const k = kv(); const run = await startRun(k, "don", now);
	await assert.rejects(startRun(k, "don", now), /run_active/);
	await observeClientTool(k, "don@expertpartners.com", "decisions", { health_run_id: run.id }, ok({ file: { id: CURRENT_DECISION_LOG }, authority: "current-log-only", newest: [{}] }), new Date(now.getTime() + 601000));
	assert.equal((await runReceipt(k, "don", run.id, now))?.checks.decisions, null);
});

test("failure, missed check and recovery use distinct deduplicated real-send transitions", async () => {
	const k = kv(); const start = sends.length;
	assert.equal((await notifyClient(k, env, "allison", "healthy", false, send, now)).action, "quiet");
	assert.equal((await notifyClient(k, env, "allison", "failed", false, send, now)).action, "sent");
	assert.equal((await notifyClient(k, env, "allison", "failed", false, send, now)).action, "quiet");
	assert.equal((await notifyClient(k, env, "allison", "missed", false, send, now)).action, "sent");
	assert.equal((await notifyClient(k, env, "allison", "healthy", false, send, now)).action, "recovered");
	assert.equal((await notifyClient(k, env, "allison", "healthy", false, send, now)).action, "quiet");
	assert.equal(sends.length - start, 3);
	assert.match(sends[sends.length - 2], /missing/);
	assert.match(sends[sends.length - 1], /recovered/);
	assert.equal((await notifyClient(k, env, "allison", "failed", true, send, now)).action, "sent");
	assert.match(sends[sends.length - 1], /^TEST/);
	assert.equal(JSON.parse(k.values.get("health:chatgpt:allison:notice")!).state, "healthy");
});

test("delivery failure is retried and an HTTP 200 provider rejection is not success", async () => {
	const k = kv();
	const reject = (async () => new Response(JSON.stringify({ status: "ERROR", message_handle: "error" }))) as typeof fetch;
	assert.equal((await notifyClient(k, env, "don", "failed", false, reject, now)).action, "send_failed");
	assert.ok(!k.values.has("health:chatgpt:don:notice"));
	await notifyClient(k, env, "don", "failed", false, send, now);
	const delayedError = (async (url: any, init: any) => String(url).includes("/status?") ? new Response(JSON.stringify({ status: { status: "ERROR" } })) : send(url, init)) as typeof fetch;
	assert.equal((await notifyClient(k, env, "don", "failed", false, delayedError, now)).action, "sent");
});

test("independent evaluator finds a missing run even when no runner calls finish", async () => {
	const k = kv(); await startRun(k, "allison", now);
	const later = new Date(now.getTime() + MAX_AGE_MS + 1);
	const r = await evaluateClients(k, env, later, send);
	assert.equal(r.clients.length, 2);
	assert.ok(r.clients.every(c => c.state === "missed" && c.alert.action === "sent"));
	const receipt = { checkedAt: now.toISOString(), ok: true } as Receipt;
	assert.equal(clientState(receipt, now.toISOString(), now), "healthy");
	assert.equal(clientState(receipt, now.toISOString(), later), "missed");
});

test("a finalizer waits for regional observations unless the runner explicitly gives up", async () => {
	const k = kv(); const run = await startRun(k, "don");
	const url = `https://gateway.invalid/api/health/clients/don/runs/${run.id}/finish`;
	let response = await clientHealthApi(new Request(url, { method: "POST", body: "{}" }), k, {});
	assert.equal(response.status, 202);
	assert.equal(k.values.has("health:chatgpt:don:last"), false);
	assert.equal(k.values.has("health:chatgpt:don:active"), true);
	response = await clientHealthApi(new Request(url, { method: "POST", body: JSON.stringify({ allowIncomplete: true, runnerError: "browser_error" }) }), k, {});
	assert.equal(response.status, 200);
	assert.equal(JSON.parse(k.values.get("health:chatgpt:don:last")!).ok, false);
});
