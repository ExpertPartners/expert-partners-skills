import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { URL } from "node:url";
import { apiPrincipal } from "../src/api-principal.ts";
import { COMPANY_CORES, DEPARTMENTS, effectiveScopes, sha256Hex } from "../src/access.ts";
import { runTool } from "../src/tools.ts";

const config = JSON.parse(readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8").replace(/^\s*\/\/.*$/gm, ""));
const ALLOWED = config.vars.ALLOWED_SCOPES as string;
const req = (token: string, dept?: string) => new Request("https://gw.invalid/api/tools/list_scopes", { method: "POST", headers: { authorization: `Bearer ${token}`, ...(dept ? { "x-brain-department": dept } : {}) } });

async function bindings() {
	const map: Record<string, string> = {};
	for (const id of Object.keys(DEPARTMENTS)) map[await sha256Hex(`synthetic-${id}`)] = id;
	return { HUB_API_TOKEN: "synthetic-hub", DEPARTMENT_TOKEN_HASHES: JSON.stringify(map) };
}

test("fixed department tokens resolve to their own profile and ignore any narrowing header", async () => {
	const b = await bindings();
	for (const id of Object.keys(DEPARTMENTS)) {
		for (const header of [undefined, "hq-cfo", "ag-ceo", "nope", "__proto__"]) {
			assert.deepEqual(await apiPrincipal(req(`synthetic-${id}`, header), b), { kind: "department", id });
		}
	}
});

test("invalid, empty, Hub-lookalike and prototype tokens never become a principal", async () => {
	const b = await bindings();
	for (const token of ["", "synthetic-unknown", "synthetic-hubx", "SYNTHETIC-HUB", "__proto__", "constructor"])
		assert.equal(await apiPrincipal(req(token), b), null, token);
	assert.equal(await apiPrincipal(new Request("https://gw.invalid/api/tools/list_scopes", { method: "POST" }), b), null);
	assert.equal(await apiPrincipal(req("synthetic-ep-cro"), { HUB_API_TOKEN: "synthetic-hub" }), null);
	assert.equal(await apiPrincipal(req("synthetic-hub", "__proto__"), b), "unknown_department");
	assert.equal(await apiPrincipal(req("synthetic-hub", "nope"), b), "unknown_department");
});

test("concurrent fixed actors keep isolated principals and scope sets", async () => {
	const b = await bindings();
	const ids = Object.keys(DEPARTMENTS);
	const runs = await Promise.all(Array.from({ length: 5 }, () => ids).flat().map(async (id, i) => {
		const principal = await apiPrincipal(req(`synthetic-${id}`, ids[(i + 1) % ids.length]), b);
		const listed = await runTool("list_scopes", {}, { ALLOWED_SCOPES: ALLOWED }, undefined, principal as any);
		return { id, principal, scopes: (listed as any).result.scopes.map((s: any) => s.scope) };
	}));
	for (const r of runs) {
		assert.deepEqual(r.principal, { kind: "department", id: r.id });
		assert.deepEqual(r.scopes, effectiveScopes(ALLOWED, { kind: "department", id: r.id }));
		for (const core of COMPANY_CORES) assert.ok(r.scopes.includes(core));
	}
});
