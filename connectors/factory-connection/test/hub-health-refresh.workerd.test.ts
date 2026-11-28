import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath, URL } from "node:url";
import { after, before, beforeEach, test } from "node:test";
import { build } from "esbuild";
import { Miniflare, Response, type Request } from "miniflare";

const root = fileURLToPath(new URL("../", import.meta.url));
const config = JSON.parse((await readFile(new URL("../wrangler.jsonc", import.meta.url), "utf8"))
	.replace(/^\s*\/\/.*$/gm, ""));
const secret = "synthetic-workerd-refresh-token-000000";
const caller = "synthetic-workerd-caller";
const endpoint = "https://hq.expertpartners.com/api/campus/system-health";
const sources = { "failure-tracker": "updated", "change-log": "updated", "daily-health": "unavailable", hq: "failed", ep: "unavailable", ag: "unavailable" };
const calls: Array<{ url: string; method: string; auth: string | null; body: string }> = [];
let upstreamStatus = 200;
let upstreamBody = "";
let runtime: Miniflare;

before(async () => {
	// Bundle the real HTTP handler and registered action, not a copy or injected fetch.
	const bundle = await build({
		stdin: {
			contents: `
				import { handleHubApi } from "./src/hub-api.ts";
				export default { async fetch(request, env) {
					if (new URL(request.url).pathname === "/request-construction") {
						const modes = {};
						for (const redirect of ["error", "manual"]) {
							try {
								new Request("${endpoint}", { method: "POST", redirect });
								modes[redirect] = { constructs: true };
							} catch (error) {
								modes[redirect] = { constructs: false, name: error.name };
							}
						}
						return Response.json(modes);
					}
					return handleHubApi(request, env);
				} };
			`,
			resolveDir: root,
			loader: "ts",
		},
		bundle: true,
		write: false,
		format: "esm",
		platform: "browser",
		target: "es2022",
	});
	runtime = new Miniflare({
		modules: true,
		script: bundle.outputFiles[0].text,
		compatibilityDate: config.compatibility_date,
		compatibilityFlags: config.compatibility_flags,
		bindings: { FACTORY_API_KEY: "synthetic-unused", HUB_API_TOKEN: caller, HUB_SYSTEM_HEALTH_REFRESH_TOKEN: secret },
		// Intercept EVERY outbound request. No test can reach production or a redirect target.
		outboundService: async (request: Request) => {
			calls.push({ url: request.url, method: request.method, auth: request.headers.get("authorization"), body: await request.text() });
			return new Response(upstreamBody, {
				status: upstreamStatus,
				headers: { Location: "https://must-not-receive-bearer.invalid/redirect", "Content-Type": "application/json" },
			});
		},
	});
	await runtime.ready;
});

after(async () => { await runtime?.dispose(); });
beforeEach(() => {
	calls.length = 0;
	upstreamStatus = 200;
	upstreamBody = JSON.stringify({ sources, privateSource: secret });
});

const invoke = (body = "{}") => runtime.dispatchFetch("https://connector.invalid/api/tools/refresh_hub_system_health", {
	method: "POST",
	headers: { Authorization: `Bearer ${caller}` },
	body,
});
const assertOnePost = () => assert.deepEqual(calls, [{
	url: endpoint, method: "POST", auth: `Bearer ${secret}`, body: "",
}]);

test("production-compatible workerd rejects error redirect mode before any outbound request", { timeout: 15_000 }, async () => {
	const response = await runtime.dispatchFetch("https://connector.invalid/request-construction");
	assert.deepEqual(await response.json(), {
		error: { constructs: false, name: "TypeError" }, manual: { constructs: true },
	});
	assert.equal(calls.length, 0);
});

test("actual Worker HTTP action sends one fixed bodyless POST and sanitizes its receipt", { timeout: 15_000 }, async () => {
	const response = await invoke();
	assert.equal(response.status, 200);
	assert.deepEqual(await response.json(), { result: { sources } });
	assertOnePost();
});

test("actual Worker refuses every redirect without forwarding its bearer or retrying", { timeout: 15_000 }, async () => {
	for (const status of [301, 302, 303, 307, 308]) {
		calls.length = 0;
		upstreamStatus = status;
		upstreamBody = `private source ${secret}`;
		const response = await invoke();
		assert.equal(response.status, 502);
		assert.deepEqual(await response.json(), {
			error: "Hub health refresh was refused or unavailable.", detail: { upstreamStatus: status },
		});
		assertOnePost();
	}
});

test("actual Worker refuses non200 and parallel-busy responses once, without private bodies", { timeout: 15_000 }, async () => {
	for (const status of [201, 400, 401, 403, 409, 500, 503]) {
		calls.length = 0;
		upstreamStatus = status;
		upstreamBody = secret;
		const response = await invoke();
		assert.equal(response.status, status === 409 ? 409 : 502);
		const body = await response.json() as { error: string; detail: { upstreamStatus: number } };
		assert.equal(body.detail.upstreamStatus, status);
		assert.equal(JSON.stringify(body).includes(secret), false);
		assertOnePost();
	}
});

test("actual Worker never retries malformed or oversized receipt outcomes", { timeout: 15_000 }, async () => {
	for (const body of ["not JSON", JSON.stringify({ sources: { hq: "healthy" } }), " ".repeat(16_385)]) {
		calls.length = 0;
		upstreamBody = body;
		const response = await invoke();
		assert.equal(response.status, 502);
		assert.equal((await response.text()).includes(secret), false);
		assertOnePost();
	}
});

test("actual Worker rejects caller-controlled URL, body or credentials before outbound fetch", { timeout: 15_000 }, async () => {
	for (const input of [{ url: "https://attacker.invalid" }, { body: {} }, { token: "caller-supplied" }]) {
		const response = await invoke(JSON.stringify(input));
		assert.equal(response.status, 400);
		assert.equal(calls.length, 0);
	}
});
