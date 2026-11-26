import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { URL } from "node:url";
import { allowedScopes, assertScope, BRAIN_FOLDERS } from "../src/brain.ts";
import { runTool } from "../src/tools.ts";

const config = JSON.parse(
	readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8").replace(/^\s*\/\/.*$/gm, ""),
);
const env = { ALLOWED_SCOPES: config.vars.ALLOWED_SCOPES as string };
const homes = ["hq-hr", "hq-employees", "hq-finance", "hq-audits", "hq-outputs", "ep-client-experience", "hq-library-marketing", "ep-events", "ep-acn", "ag-strong-ones", "ag-case-studies", "ag-personal-core", "ag-personal-marketing"] as const;

test("deployed allowlist includes mapped department homes and ep-private, without ag-private or unknown scopes", async () => {
	const expected = [
		"hq-core", "hq-hr", "hq-employees", "hq-skills", "hq-finance", "hq-operations", "hq-analytics", "hq-audits", "hq-outputs", "hq-partnersync", "hq-library",
		"ep-core", "ep-discovery", "ep-marketing", "ep-sales", "ep-client-experience", "ep-operations", "ep-outputs", "ep-private",
		"ag-core", "ag-marketing", "ag-sales", "ag-listings", "ag-client-experience", "ag-operations", "ag-outputs",
		"hq-library-marketing", "ep-events", "ep-acn", "ag-strong-ones", "ag-case-studies",
		"ag-personal-core", "ag-personal-marketing",
	];
	assert.deepEqual(allowedScopes(env.ALLOWED_SCOPES), expected);
	assert.equal(new Set(allowedScopes(env.ALLOWED_SCOPES)).size, 33);
	for (const denied of ["ag-private", "bogus"])
		assert.throws(() => assertScope(env.ALLOWED_SCOPES, denied));
	const listed = await runTool("list_scopes", {}, env, async () => { throw new Error("Listing scopes must not read Drive"); });
	assert.equal(listed.ok, true);
	if (listed.ok) assert.deepEqual(listed.result, {
		scopes: expected.map((scope) => ({ scope, folderId: BRAIN_FOLDERS[scope as keyof typeof BRAIN_FOLDERS] })),
	});
});

test("new department scopes discover only their exact registered direct children", async () => {
	for (const scope of homes) {
		const calls: string[] = [];
		const result = await runTool("discover", { scope }, env, async (path) => {
			calls.push(path);
			const url = new URL(path, "https://drive.invalid");
			assert.equal(url.pathname, "/drive/v3/files");
			assert.equal(url.searchParams.get("q"), `'${BRAIN_FOLDERS[scope]}' in parents and trashed=false`);
			return new Response(JSON.stringify({ files: [] }), { status: 200 });
		});
		assert.equal(result.ok, true);
		assert.equal(calls.length, 1);
		if (result.ok) {
			const discovery = result.result as { scope: string; folderId: string; files: unknown[]; complete: boolean; readAt: string };
			assert.deepEqual({ ...discovery, readAt: undefined }, { scope, folderId: BRAIN_FOLDERS[scope], files: [], complete: true, withheld: 0, readAt: undefined });
			assert.ok(Number.isFinite(Date.parse(discovery.readAt)));
		}
	}
});

test("legacy ep-client discovers the canonical folder for leaders and the client department only", async () => {
	assert.equal(assertScope(env.ALLOWED_SCOPES, "ep-client"), "ep-client-experience");
	assert.throws(() => assertScope("ep-sales", "ep-client"));
	for (const principal of [
		{ kind: "person", email: "allison@expertpartners.com" },
		{ kind: "person", email: "don@expertpartners.com" },
		{ kind: "department", id: "ep-cco" },
	] as const) {
		const r = await runTool("discover", { scope: "ep-client" }, env, async (path) => {
			assert.equal(new URL(path, "https://drive.invalid").searchParams.get("q"), `'${BRAIN_FOLDERS["ep-client-experience"]}' in parents and trashed=false`);
			return Response.json({ files: [] });
		}, principal);
		assert.ok(r.ok);
		assert.equal((r.result as any).scope, "ep-client-experience");
	}
	for (const principal of [
		{ kind: "person", email: "unknown@expertpartners.com" },
		{ kind: "department", id: "ep-cro" },
	] as const) {
		for (const tool of ["discover", "read"]) {
			const r = await runTool(tool, { scope: "ep-client", id: "file" }, env, async () => { throw new Error("Unauthorized alias must not call Drive"); }, principal);
			assert.equal(r.status, 403);
		}
	}
	const withheld = await runTool("read", { scope: "ep-client", id: "withheld-file" }, { ...env, WITHHELD_SOURCES: '["withheld-file"]' }, async () => { throw new Error("Withheld file must not call Drive"); });
	assert.equal(withheld.status, 403);
});

test("HQ departments reach outputs and only the AI department reaches audits", async () => {
	for (const id of ["hq-chro", "hq-cfo", "hq-caio"]) {
		for (const scope of ["hq-outputs", "hq-audits"]) {
			const r = await runTool("discover", { scope }, env, async () => Response.json({ files: [] }), { kind: "department", id });
			assert.equal(r.status, scope === "hq-audits" && id !== "hq-caio" ? 403 : 200);
		}
	}
	for (const scope of ["ag-core", "ag-marketing", "ag-sales", "ag-listings", "ag-client-experience", "ag-operations", "ag-outputs", "ag-private", "ag-strong-ones", "ag-case-studies"]) {
		const r = await runTool("discover", { scope }, env, async () => { throw new Error("Don must never call AG Drive"); }, { kind: "person", email: "don@expertpartners.com" });
		assert.equal(r.status, 403);
	}
});
