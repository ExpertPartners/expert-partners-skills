import { withRoots } from "./roots.ts";
import { test } from "node:test";
import assert from "node:assert/strict";
import { BRAIN_FOLDERS, CURRENT_DECISION_LOG } from "../src/brain.ts";
import { lastResults, runDeepCheck, storeResult, type HealthResult } from "../src/health.ts";

const DOC = "application/vnd.google-apps.document";
const NOW = new Date("2026-11-21T18:00:00Z");
const RULEBOOK = "rulebook-id";
const f = (id: string, name: string) => ({ id, name, mimeType: DOC, modifiedTime: "2026-11-20T00:00:00Z", version: "7" });

function drive(opts: { logText?: string; failScope?: string; incomplete?: boolean } = {}) {
	const logText = opts.logText ?? "November 20, 2026. Newest decision\nbody\nNovember 1, 2026. Older\n";
	const healthy = withRoots(async (path: string) => {
		const url = new URL(path, "https://x");
		const q = url.searchParams.get("q");
		if (url.pathname === "/drive/v3/files" && q) {
			if (opts.failScope && q.includes(BRAIN_FOLDERS[opts.failScope as keyof typeof BRAIN_FOLDERS])) return new Response("denied", { status: 403 });
			const files = q.includes(BRAIN_FOLDERS["hq-core"]) ? [f(CURRENT_DECISION_LOG, "[HQ][V1.0] Decision Log"), f(RULEBOOK, "[HQ][V1.0] HQ Rulebook")] : [f("x", "doc")];
			return new Response(JSON.stringify({ files, incompleteSearch: !!opts.incomplete }), { status: 200 });
		}
		if (url.pathname.endsWith("/export")) {
			const id = url.pathname.split("/")[4];
			return new Response(id === RULEBOOK ? "r".repeat(5000) : logText, { status: 200 });
		}
		const id = url.pathname.split("/").pop()!;
		return new Response(JSON.stringify(f(id, "n")), { status: 200 });
	});
	return async (path: string) => {
		// An outage affects the root GET too; probes no longer list children.
		if (opts.failScope && path.includes(BRAIN_FOLDERS[opts.failScope as keyof typeof BRAIN_FOLDERS]))
			return new Response("unavailable", { status: 503 });
		return healthy(path);
	};
}

test("a healthy brain passes every check without keeping any document text", async () => {
	const r = await runDeepCheck("hq-core,ep-core", drive(), () => NOW);
	assert.equal(r.ok, true, JSON.stringify(r.checks.filter((c) => !c.ok)));
	assert.ok(r.checks.some((c) => c.name === "decision log freshness" && c.ok));
	assert.ok(r.checks.some((c) => c.name === "rulebook present" && c.ok));
	assert.ok(!JSON.stringify(r).includes("Newest decision"), "no document text in the result");
	assert.equal(r.checkedAt, NOW.toISOString());
});

test("a scope that stops answering fails the check and names only the code", async () => {
	const r = await runDeepCheck("hq-core,ep-core", drive({ failScope: "ep-core" }), () => NOW);
	assert.equal(r.ok, false);
	const bad = r.checks.filter((c) => !c.ok);
	assert.deepEqual(bad.map((c) => c.name), ["scope ep-core"]);
	assert.match(bad[0].detail, /failed \(drive_error\)/);
});

test("an incomplete listing and a stale Decision Log both fail", async () => {
	const inc = await runDeepCheck("hq-core", drive({ incomplete: true }), () => NOW);
	assert.equal(inc.ok, false);
	const stale = await runDeepCheck("hq-core", drive({ logText: "October 1, 2026. Old only\nbody\n" }), () => NOW);
	assert.equal(stale.checks.find((c) => c.name === "decision log freshness")!.ok, false);
});

test("an empty allowlist is itself a failure", async () => {
	const r = await runDeepCheck("", drive(), () => NOW);
	assert.equal(r.ok, false);
	assert.equal(r.checks[0].name, "allowlist");
});

test("the last failure survives a later pass", async () => {
	const store = new Map<string, string>();
	const kv = { put: async (k: string, v: string) => void store.set(k, v), get: async (k: string) => store.get(k) ?? null } as unknown as KVNamespace;
	const bad: HealthResult = { ok: false, checkedAt: "2026-11-20T12:00:00Z", checks: [{ name: "x", ok: false, detail: "failed (drive_error)" }] };
	const good: HealthResult = { ok: true, checkedAt: "2026-11-21T12:00:00Z", checks: [] };
	await storeResult(kv, bad);
	await storeResult(kv, good);
	const r = await lastResults(kv);
	assert.equal(r.last?.ok, true);
	assert.equal(r.lastFailure?.checkedAt, "2026-11-20T12:00:00Z");
});
