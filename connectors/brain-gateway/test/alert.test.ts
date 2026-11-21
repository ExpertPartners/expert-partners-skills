import assert from "node:assert/strict";
import { test } from "node:test";
import { alertText, maybeAlert } from "../src/alert.ts";
import type { HealthResult } from "../src/health.ts";

const env = { SENDBLUE_API_KEY_ID: "id", SENDBLUE_API_SECRET: "sec", ALERT_TO: "+15550001111", ALERT_FROM: "+15550002222" };
const bad: HealthResult = { ok: false, checkedAt: "2026-11-22T12:00:00Z", checks: [{ name: "scope hq-core", ok: false, detail: "failed (drive_error)" }, { name: "allowlist", ok: true, detail: "23 scopes allowed" }] };
const good: HealthResult = { ok: true, checkedAt: "2026-11-23T12:00:00Z", checks: [] };
const kv = () => { const m = new Map<string, string>(); return { m, get: async (k: string) => m.get(k) ?? null, put: async (k: string, v: string) => void m.set(k, v) } as unknown as KVNamespace & { m: Map<string, string> }; };
const fakeFetch = (ok: boolean, calls: any[]) => (async (url: any, init: any) => { calls.push({ url, init }); return new Response("{}", { status: ok ? 200 : 500 }); }) as typeof fetch;

test("a pass with no earlier failure sends nothing", async () => {
	const calls: any[] = [];
	assert.equal(await maybeAlert(kv(), env, good, fakeFetch(true, calls)), "quiet");
	assert.equal(calls.length, 0);
});

test("a failure texts once with the failed check and no secrets in the body", async () => {
	const k = kv(); const calls: any[] = [];
	assert.equal(await maybeAlert(k, env, bad, fakeFetch(true, calls)), "sent");
	const body = JSON.parse(calls[0].init.body);
	assert.equal(body.number, "+15550001111");
	assert.match(body.content, /scope hq-core: failed \(drive_error\)/);
	assert.ok(!body.content.includes("sec"));
	assert.equal(k.m.get("alert:state"), "failing");
});

test("recovery texts once, then stays quiet", async () => {
	const k = kv(); const calls: any[] = [];
	await maybeAlert(k, env, bad, fakeFetch(true, calls));
	assert.equal(await maybeAlert(k, env, good, fakeFetch(true, calls)), "recovered");
	assert.equal(await maybeAlert(k, env, good, fakeFetch(true, calls)), "quiet");
	assert.match(JSON.parse(calls[1].init.body).content, /healthy again/);
});

test("a refused send keeps state so the next run retries", async () => {
	const k = kv();
	assert.equal(await maybeAlert(k, env, bad, fakeFetch(false, [])), "send_failed");
	assert.equal(k.m.get("alert:state"), undefined);
});

test("missing settings means unconfigured, not a crash", async () => {
	assert.equal(await maybeAlert(kv(), {}, bad, fakeFetch(true, [])), "unconfigured");
	assert.ok(alertText(bad, false).length < 400);
});
