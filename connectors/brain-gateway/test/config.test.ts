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
const homes = ["hq-hr", "hq-employees", "hq-finance"] as const;

test("deployed allowlist includes mapped department homes without private or proposed scopes", async () => {
	const expected = [
		"hq-core", "hq-hr", "hq-employees", "hq-skills", "hq-finance", "hq-operations", "hq-analytics", "hq-partnersync", "hq-library",
		"ep-core", "ep-discovery", "ep-marketing", "ep-sales", "ep-client-experience", "ep-operations", "ep-outputs",
		"ag-core", "ag-marketing", "ag-sales", "ag-listings", "ag-client-experience", "ag-operations", "ag-outputs",
	];
	assert.deepEqual(allowedScopes(env.ALLOWED_SCOPES), expected);
	assert.equal(new Set(allowedScopes(env.ALLOWED_SCOPES)).size, 23);
	for (const denied of ["ep-private", "ag-private", "hq-audits", "hq-outputs", "bogus"])
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
			assert.deepEqual({ ...discovery, readAt: undefined }, { scope, folderId: BRAIN_FOLDERS[scope], files: [], complete: true, readAt: undefined });
			assert.ok(Number.isFinite(Date.parse(discovery.readAt)));
		}
	}
});
