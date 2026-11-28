import { test } from "node:test";
import assert from "node:assert/strict";
import { handleHubApi } from "../src/hub-api.ts";
import { HubHealthRefreshError, refreshHubSystemHealth } from "../src/hub-health-refresh.ts";
import { findTool, runTool } from "../src/tools.ts";

const secret = "synthetic-dedicated-refresh-token-000000";
const env = { FACTORY_API_KEY: "synthetic-factory-key", HUB_API_TOKEN: "synthetic-caller-token", HUB_SYSTEM_HEALTH_REFRESH_TOKEN: secret };
const sources = { "failure-tracker": "updated", "change-log": "updated", "daily-health": "unavailable", hq: "failed", ep: "unavailable", ag: "unavailable" };
const receipt = () => Response.json({ sources });
const fake = (fn: (...args: any[]) => any) => fn as typeof fetch;
const request = (auth = `Bearer ${env.HUB_API_TOKEN}`, body = "{}") =>
	new Request("https://connector.example/api/tools/refresh_hub_system_health", {
		method: "POST", headers: { Authorization: auth }, body,
	});

test("registered action accepts no caller-controlled destination, credential or payload", async () => {
	const tool = findTool("refresh_hub_system_health")!;
	assert.equal(tool.readOnly, undefined);
	assert.equal(tool.schema.safeParse({}).success, true);
	for (const input of [{ url: "https://attacker.example" }, { token: "caller-value" }, { headers: {} }, { payload: {} }, { method: "GET" }, { timeout: 1 }]) {
		assert.equal(tool.schema.safeParse(input).success, false);
		const result = await runTool(tool.name, input, env);
		assert.equal(result.ok, false);
		assert.equal(result.status, 400);
	}
});

test("uses one bodyless POST, fixed HTTPS origin, no redirects and dedicated binding", async () => {
	let calls = 0;
	const result = await refreshHubSystemHealth(env, fake(async (url, init) => {
		calls++;
		assert.equal(url, "https://hq.expertpartners.com/api/campus/system-health");
		assert.equal(init.method, "POST");
		assert.equal(init.body, undefined);
		assert.equal(init.redirect, "error");
		assert.equal(new Headers(init.headers).get("authorization"), `Bearer ${secret}`);
		assert.equal(init.signal.aborted, false);
		return receipt();
	}));
	assert.equal(calls, 1);
	assert.deepEqual(result, { sources });
});

test("fails closed before fetching if dedicated binding is absent or malformed", async () => {
	for (const token of [undefined, "", "short", "x".repeat(32) + "\r\ninjected"]) {
		let calls = 0;
		await assert.rejects(refreshHubSystemHealth({ HUB_SYSTEM_HEALTH_REFRESH_TOKEN: token }, fake(() => { calls++; })), (e: HubHealthRefreshError) => e.status === 503);
		assert.equal(calls, 0);
	}
	const result = await runTool("refresh_hub_system_health", {}, { FACTORY_API_KEY: secret });
	assert.equal(result.ok, false);
	assert.equal(result.status, 503);
	assert.equal(JSON.stringify(result).includes(secret), false);
});

test("upstream 401, 403, 409, 503 and redirects fail once without reading private bodies", async () => {
	for (const status of [301, 302, 401, 403, 409, 503]) {
		let calls = 0;
		await assert.rejects(refreshHubSystemHealth(env, fake(async () => {
			calls++;
			return new Response(`private source and ${secret}`, { status });
		})), (e: HubHealthRefreshError) => {
			assert.equal(e.status, status === 409 ? 409 : 502);
			assert.equal(e.upstreamStatus, status);
			assert.equal(e.message.includes(secret), false);
			return true;
		});
		assert.equal(calls, 1);
	}
});

test("network and response-read errors never expose provider exception text", async () => {
	for (const send of [
		fake(async () => { throw new Error(`private ${secret}`); }),
		fake(async () => new Response(new ReadableStream({ start(c) { c.error(new Error(secret)); } }))),
	]) {
		await assert.rejects(refreshHubSystemHealth(env, send), (e: HubHealthRefreshError) => {
			assert.equal(e.status, 502);
			assert.equal(e.message.includes(secret), false);
			return true;
		});
	}
});

test("45-second deadline exceeds the source deadline and never retries an uncertain POST", async (t) => {
	t.mock.timers.enable({ apis: ["setTimeout"] });
	let calls = 0;
	let signal!: AbortSignal;
	const pending = refreshHubSystemHealth(env, fake((_url, init) => {
		calls++;
		signal = init.signal;
		return new Promise((_resolve, reject) => signal.addEventListener("abort", () => reject(new Error(secret)), { once: true }));
	}));
	t.mock.timers.tick(44_999);
	assert.equal(signal.aborted, false);
	t.mock.timers.tick(1);
	await assert.rejects(pending, (e: HubHealthRefreshError) => e.status === 504 && /uncertain/.test(e.message) && !e.message.includes(secret));
	assert.equal(calls, 1);
});

test("only six sanitized outcomes leave a successful response, updated is not healthy", async () => {
	const result = await refreshHubSystemHealth(env, fake(async () => Response.json({
		sources: { ...sources, privateRow: secret }, sourceText: secret, email: "synthetic@example.invalid", credential: secret,
	})));
	assert.deepEqual(result, { sources });
	assert.equal(Object.keys(result.sources).length, 6);
	assert.equal(JSON.stringify(result).includes(secret), false);
	assert.equal(JSON.stringify(result).includes("healthy"), false);
});

test("rejects missing, malformed, invalid or oversized upstream receipts", async () => {
	for (const body of ["not JSON", JSON.stringify({ sources: { hq: "updated" } }), JSON.stringify({ sources: { ...sources, hq: "healthy" } }), " ".repeat(16_385)]) {
		await assert.rejects(refreshHubSystemHealth(env, fake(async () => new Response(body))), (e: HubHealthRefreshError) => e.status === 502);
	}
});

test("actual HTTP handler rejects missing and wrong authentication before fetching", async (t) => {
	let calls = 0;
	t.mock.method(globalThis, "fetch", fake(async () => { calls++; return receipt(); }));
	for (const auth of ["", "Bearer wrong", "Bearer synthetic-caller-tokem", "Basic synthetic-caller-token"]) {
		const response = await handleHubApi(request(auth, "invalid JSON"), env);
		assert.equal(response.status, 401);
		assert.deepEqual(await response.json(), { error: "unauthorized" });
	}
	const response = await handleHubApi(request(), { ...env, HUB_API_TOKEN: undefined });
	assert.equal(response.status, 401);
	assert.equal(calls, 0);
});

test("actual HTTP handler executes the registered action and projects private upstream fields", async (t) => {
	let calls = 0;
	t.mock.method(globalThis, "fetch", fake(async () => {
		calls++;
		return Response.json({ sources: { ...sources, privateRow: secret }, privateBody: secret });
	}));
	const response = await handleHubApi(request(), env);
	assert.equal(response.status, 200);
	assert.deepEqual(await response.json(), { result: { sources } });
	assert.equal(calls, 1);
});

test("actual HTTP handler preserves safe failure status without returning upstream body", async (t) => {
	let calls = 0;
	t.mock.method(globalThis, "fetch", fake(async () => { calls++; return new Response(secret, { status: 409 }); }));
	const response = await handleHubApi(request(), env);
	assert.equal(response.status, 409);
	assert.deepEqual(await response.json(), { error: "Hub health refresh is already in progress.", detail: { upstreamStatus: 409 } });
	assert.equal(calls, 1);
});

test("actual HTTP handler refuses input overrides before an outbound request", async (t) => {
	let calls = 0;
	t.mock.method(globalThis, "fetch", fake(async () => { calls++; return receipt(); }));
	const response = await handleHubApi(request(undefined, JSON.stringify({ url: "https://attacker.example", token: secret })), env);
	assert.equal(response.status, 400);
	assert.equal((await response.text()).includes(secret), false);
	assert.equal(calls, 0);
});
