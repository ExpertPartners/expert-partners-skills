import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { URL } from "node:url";
import { DEPARTMENTS, effectiveScopes, pinnedReadFor } from "../src/access.ts";
import { BRAIN_FOLDERS } from "../src/brain.ts";
import { runTool } from "../src/tools.ts";

const config = JSON.parse(readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8").replace(/^\s*\/\/.*$/gm, ""));
const ALLOWED = config.vars.ALLOWED_SCOPES as string;
const allowed = ALLOWED.split(",");
const dept = (id: string) => ({ kind: "department" as const, id });
const person = (email: string, department?: string) => ({ kind: "person" as const, email, department });
const CEOS = { "ep-ceo": "ep-", "ag-ceo": "ag-", "hq-chro": "hq-" } as const;
const brain = (p: string) => allowed.filter((s) => s.startsWith(p) && !s.endsWith("-private") && !s.startsWith("ag-personal-"));

test("each CEO whole-brain profile reaches every non-private scope of its own brain", () => {
	assert.deepEqual(brain("hq-").sort(), ["hq-analytics", "hq-audits", "hq-core", "hq-employees", "hq-finance", "hq-hr", "hq-library", "hq-library-marketing", "hq-operations", "hq-outputs", "hq-partnersync", "hq-skills"]);
	assert.deepEqual(brain("ep-").sort(), ["ep-acn", "ep-client-experience", "ep-core", "ep-discovery", "ep-events", "ep-marketing", "ep-operations", "ep-outputs", "ep-sales"]);
	assert.deepEqual(brain("ag-").sort(), ["ag-case-studies", "ag-client-experience", "ag-core", "ag-listings", "ag-marketing", "ag-operations", "ag-outputs", "ag-sales", "ag-strong-ones"]);
	for (const [id, prefix] of Object.entries(CEOS)) {
		const s = effectiveScopes(ALLOWED, dept(id));
		for (const scope of brain(prefix)) assert.ok(s.includes(scope as any), `${id} reaches ${scope}`);
		assert.ok(!s.some((x) => x.endsWith("-private")), `${id} reaches no private scope`);
		// Only its own brain plus the three shared Cores.
		assert.deepEqual(s.filter((x) => !x.startsWith(prefix)).sort(), ["ag-core", "ep-core", "hq-core"].filter((c) => !c.startsWith(prefix)).sort());
	}
});

test("CEO whole-brain discover reaches Drive for every own scope and is refused elsewhere", async () => {
	for (const [id, prefix] of Object.entries(CEOS)) {
		for (const scope of brain(prefix)) {
			const r = await runTool("discover", { scope }, { ALLOWED_SCOPES: ALLOWED }, async (path) => {
				assert.equal(new URL(path, "https://drive.invalid").searchParams.get("q"), `'${BRAIN_FOLDERS[scope as keyof typeof BRAIN_FOLDERS]}' in parents and trashed=false`);
				return Response.json({ files: [] });
			}, dept(id));
			assert.equal(r.status, 200, `${id} ${scope}`);
		}
		for (const scope of allowed.filter((s) => !effectiveScopes(ALLOWED, dept(id)).includes(s as any))) {
			const r = await runTool("discover", { scope }, { ALLOWED_SCOPES: ALLOWED }, async () => { throw new Error("denied call reached Drive"); }, dept(id));
			assert.equal(r.status, 403, `${id} ${scope}`);
		}
	}
});

test("person intersection holds: Don narrowed to a CEO profile never gains AG, Allison gains nothing private", () => {
	for (const id of Object.keys(CEOS)) assert.ok(effectiveScopes(ALLOWED, person("don@expertpartners.com", id)).every((s) => !s.startsWith("ag-")), id);
	assert.deepEqual(effectiveScopes(ALLOWED, person("don@expertpartners.com", "ag-ceo")), ["hq-core", "ep-core"]);
	assert.deepEqual(effectiveScopes(ALLOWED, person("allison@expertpartners.com", "ep-ceo")).sort(), [...brain("ep-"), "hq-core", "ag-core"].sort());
	assert.ok(!effectiveScopes(ALLOWED, person("don@expertpartners.com", "ep-ceo")).includes("ep-private"));
});

test("pinned leader files stay unnarrowed-leader only, including for CEO profiles", () => {
	const json = JSON.stringify({ "gap108-week2-builder": [{ id: "a", parent: "p", drive: "d" }, { id: "b", parent: "p", drive: "d" }, { id: "c", parent: "p", drive: "d" }] });
	for (const id of Object.keys(CEOS)) {
		assert.throws(() => pinnedReadFor(dept(id), "gap108-week2-builder", "a", undefined, json));
		assert.throws(() => pinnedReadFor(person("allison@expertpartners.com", id), "gap108-week2-builder", "a", undefined, json));
	}
	assert.ok(pinnedReadFor(person("allison@expertpartners.com"), "gap108-week2-builder", "a", undefined, json));
});

test("non-CEO departments keep exactly their prior grants", () => {
	const prior: Record<string, string[]> = {
		"ep-cro": ["ep-sales", "ep-outputs"], "hq-cfo": ["hq-finance", "hq-outputs"], "ag-cro": ["ag-sales", "ag-listings", "ag-outputs"],
		"hq-caio": ["hq-operations", "hq-analytics", "hq-partnersync", "hq-audits", "hq-outputs"],
	};
	for (const [id, own] of Object.entries(prior))
		assert.deepEqual(effectiveScopes(ALLOWED, dept(id)).sort(), [...own, "hq-core", "ep-core", "ag-core"].sort(), id);
	assert.equal(Object.keys(DEPARTMENTS).length, 14);
});
