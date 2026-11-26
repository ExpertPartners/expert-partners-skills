import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { URL } from "node:url";
import { DEPARTMENTS, departmentForToken, effectiveScopes, PEOPLE, sha256Hex } from "../src/access.ts";
import { BRAIN_FOLDERS } from "../src/brain.ts";
import { runTool } from "../src/tools.ts";

const config = JSON.parse(readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8").replace(/^\s*\/\/.*$/gm, ""));
const ALLOWED = config.vars.ALLOWED_SCOPES as string;
const allowed = ALLOWED.split(",");
const person = (email: string, department?: string) => ({ kind: "person" as const, email, department });
const dept = (id: string) => ({ kind: "department" as const, id });

test("Allison leads all three brains, Don leads HQ and EP only, AG is Allison alone", () => {
	const a = effectiveScopes(ALLOWED, person("allison@expertpartners.com"));
	assert.deepEqual(a, allowed);
	assert.ok(a.includes("ep-private"));
	const d = effectiveScopes(ALLOWED, person(" Don@ExpertPartners.com "));
	assert.ok(d.length > 0);
	assert.ok(d.includes("ep-private"), "Don must be able to read EP Private as a leader");
	assert.ok(d.every((s) => s.startsWith("hq-") || s.startsWith("ep-")));
	assert.ok(!d.some((s) => s.startsWith("ag-")));
	assert.ok(d.includes("hq-finance") && d.includes("ep-sales"), "leader level means the whole HQ and EP brain");
	assert.ok(d.includes("ep-private"), "Don reads EP Private");
	assert.equal(d.length, 22, "Don gets all 12 HQ scopes and all 10 EP scopes");
	assert.ok(d.includes("ep-events") && d.includes("ep-acn") && d.includes("hq-library-marketing"));
});

test("anyone else signed in gets no scopes at all", () => {
	assert.deepEqual(effectiveScopes(ALLOWED, person("someone@expertpartners.com")), []);
	assert.deepEqual(effectiveScopes(ALLOWED, person("")), []);
});

test("a profile never widens the deployed allowlist", () => {
	const narrow = "hq-core,ep-core";
	assert.deepEqual(effectiveScopes(narrow, person("allison@expertpartners.com")), ["hq-core", "ep-core"]);
	assert.deepEqual(effectiveScopes(narrow, dept("hq-cfo")), ["hq-core"]);
	assert.deepEqual(effectiveScopes(undefined, person("allison@expertpartners.com")), []);
});

test("every department stays inside its own folders plus governance, never private or another department", () => {
	for (const [id, d] of Object.entries(DEPARTMENTS)) {
		for (const s of [...d.scopes, ...d.exceptions]) {
			assert.ok(s in BRAIN_FOLDERS, `${id} names an unknown scope ${s}`);
			assert.ok(!s.endsWith("-private"), `${id} must not reach private ${s}`);
		}
		assert.ok(d.scopes.includes("hq-core"), `${id} carries shared governance`);
		const company = id.split("-")[0];
		if (company === "ep") assert.ok(![...d.scopes].some((s) => s.startsWith("ag-")), `${id} stays out of AG`);
		if (company === "ag") assert.ok(![...d.scopes].some((s) => s.startsWith("ep-")), `${id} stays out of EP`);
		assert.deepEqual(d.exceptions, [], "exceptions stay empty until a decision names the source");
	}
	const cro = effectiveScopes(ALLOWED, dept("ep-cro"));
	assert.deepEqual(cro.sort(), ["ep-outputs", "ep-sales", "hq-core"]);
	assert.ok(!cro.includes("ep-marketing") && !cro.includes("hq-finance") && !cro.includes("ag-sales"));
	assert.deepEqual(effectiveScopes(ALLOWED, dept("hq-cfo")).sort(), ["hq-core", "hq-finance", "hq-outputs"]);
	assert.deepEqual(effectiveScopes(ALLOWED, dept("ag-cro")).sort(), ["ag-listings", "ag-outputs", "ag-sales", "hq-core"]);
});

test("a leader can narrow to a department but never widen", () => {
	assert.deepEqual(effectiveScopes(ALLOWED, person("allison@expertpartners.com", "ep-cro")).sort(), ["ep-outputs", "ep-sales", "hq-core"]);
	// Don narrowed to an AG department keeps only shared governance, because he is not an AG leader.
	assert.deepEqual(effectiveScopes(ALLOWED, person("don@expertpartners.com", "ag-cro")), ["hq-core"]);
	assert.throws(() => effectiveScopes(ALLOWED, person("allison@expertpartners.com", "nope")), /not known/);
	assert.throws(() => effectiveScopes(ALLOWED, dept("nope")), /not known/);
});

test("tools enforce the principal: a department cannot list, discover or read outside its scopes", async () => {
	const env = { ALLOWED_SCOPES: ALLOWED };
	const drive = async () => new Response(JSON.stringify({ files: [] }), { status: 200 });
	const listed = await runTool("list_scopes", {}, env, drive, dept("ep-cro"));
	assert.ok(listed.ok);
	assert.deepEqual((listed.result as any).scopes.map((s: any) => s.scope).sort(), ["ep-outputs", "ep-sales", "hq-core"]);
	for (const scope of ["ep-marketing", "hq-finance", "ag-sales", "ep-private"]) {
		const r = await runTool("discover", { scope }, env, drive, dept("ep-cro"));
		assert.equal(r.ok, false, scope);
		assert.equal(r.status, 403, scope);
	}
	const own = await runTool("discover", { scope: "ep-sales" }, env, drive, dept("ep-cro"));
	assert.ok(own.ok);
	const dec = await runTool("decisions", {}, env, drive, dept("ep-cro"));
	assert.notEqual((dec as any).detail, "scope_not_allowed", "governance is readable by every department");
	const donAg = await runTool("discover", { scope: "ag-core" }, env, drive, person("don@expertpartners.com"));
	assert.equal(donAg.status, 403);
	const stranger = await runTool("discover", { scope: "hq-core" }, env, drive, person("x@expertpartners.com"));
	assert.equal(stranger.status, 403);
});

test("department tokens match only by SHA-256 hash and never by guess", async () => {
	const hashes = JSON.stringify({ [await sha256Hex("tok-cro")]: "ep-cro", [await sha256Hex("tok-bad")]: "not-a-department" });
	assert.equal(await departmentForToken(hashes, "tok-cro"), "ep-cro");
	assert.equal(await departmentForToken(hashes, "tok-bad"), null);
	assert.equal(await departmentForToken(hashes, "other"), null);
	assert.equal(await departmentForToken(hashes, ""), null);
	assert.equal(await departmentForToken("{not json", "tok-cro"), null);
	assert.equal(await departmentForToken(undefined, "tok-cro"), null);
	assert.ok(!hashes.includes("tok-cro"), "the raw token is never stored");
});

test("only the approved leaders are listed", () => {
	assert.deepEqual(Object.keys(PEOPLE).sort(), ["allison@expertpartners.com", "don@expertpartners.com"]);
});

test("AG Personal Marketing has its own workspace boundary, separate from EP and AG Luxury", async () => {
	const scopes = ["ag-personal-core", "ag-personal-marketing"] as const;
	assert.deepEqual(effectiveScopes(ALLOWED, dept("ag-personal-cgo")).sort(), [...scopes, "hq-core"]);
	assert.deepEqual(effectiveScopes(ALLOWED, person("allison@expertpartners.com", "ag-personal-cgo")).sort(), [...scopes, "hq-core"]);
	assert.deepEqual(effectiveScopes(ALLOWED, person("don@expertpartners.com", "ag-personal-cgo")), ["hq-core"]);
	assert.equal(DEPARTMENTS["ag-cgo"].label, "AG Luxury Chief Growth Officer");
	assert.ok(effectiveScopes(ALLOWED, dept("ag-cgo")).includes("ag-marketing"));
	for (const scope of scopes) {
		const own = await runTool("discover", { scope }, { ALLOWED_SCOPES: ALLOWED }, async (path) => {
			assert.equal(new URL(path, "https://drive.invalid").searchParams.get("q"), `'${BRAIN_FOLDERS[scope]}' in parents and trashed=false`);
			return Response.json({ files: [] });
		}, dept("ag-personal-cgo"));
		assert.equal(own.status, 200);
		for (const principal of [
			person("don@expertpartners.com"),
			...Object.keys(DEPARTMENTS).filter((id) => id !== "ag-personal-cgo").map(dept),
		]) {
			assert.ok(!effectiveScopes(ALLOWED, principal).includes(scope));
			for (const tool of ["discover", "read"]) {
				const denied = await runTool(tool, { scope, id: "file" }, { ALLOWED_SCOPES: ALLOWED }, async () => {
					throw new Error("Cross-company or cross-department request must never call Drive");
				}, principal);
				assert.equal(denied.status, 403);
			}
		}
	}
	for (const scope of ["ag-marketing", "ag-core", "ep-marketing", "ep-core", "ag-outputs"]) {
		const denied = await runTool("discover", { scope }, { ALLOWED_SCOPES: ALLOWED }, async () => {
			throw new Error("AG Personal cannot reach another brain");
		}, dept("ag-personal-cgo"));
		assert.equal(denied.status, 403);
	}
});
