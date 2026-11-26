import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { URL } from "node:url";
import { DEPARTMENTS, effectiveScopes } from "../src/access.ts";
import { runTool } from "../src/tools.ts";
import { BRAIN_FOLDERS } from "../src/brain.ts";

const config = JSON.parse(readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8").replace(/^\s*\/\/.*$/gm, ""));
const ids = ["shared-playbook", "shared-unique", "shared-proof", "shared-voice", "shared-summary"];
const env = { ALLOWED_SCOPES: config.vars.ALLOWED_SCOPES as string, FILE_READ_EXCEPTIONS: JSON.stringify({ "ag-shared-brand": ids }) };
const luxury = ["ag-ceo", "ag-cgo", "ag-cro", "ag-cco", "ag-coo"];
const dept = (id: string) => ({ kind: "department" as const, id });
const person = (email: string, department: string) => ({ kind: "person" as const, email, department });
const file = (id: string) => ({ id, name: "Fictional shared source", mimeType: "application/vnd.google-apps.document", modifiedTime: "2026-11-25T00:00:00Z", version: "1" });
const forbidden = async () => { throw new Error("Unauthorized request must not reach Drive"); };
function driveFor(id: string, options: { moved?: boolean; changed?: boolean } = {}) {
	let version = 0;
	return async (path: string) => {
		const url = new URL(path, "https://drive.invalid");
		if (url.pathname === "/drive/v3/files") {
			assert.equal(url.searchParams.get("q"), `'${BRAIN_FOLDERS["ag-personal-core"]}' in parents and trashed=false`);
			return Response.json({ files: options.moved ? [] : [file(id)] });
		}
		if (url.pathname === `/drive/v3/files/${id}/export`) return new Response("Fictional complete shared source", { headers: { "content-type": "text/plain" } });
		assert.equal(url.pathname, `/drive/v3/files/${id}`);
		return Response.json({ ...file(id), version: String(options.changed ? ++version : 1) });
	};
}

test("only the five named Luxury identities read each exact shared file without widening scopes", async () => {
	assert.deepEqual(Object.entries(DEPARTMENTS).filter(([, d]) => d.fileExceptions?.length).map(([id]) => id), ["ag-ceo", "ag-cgo", "ag-cro", "ag-cco", "ag-coo"]);
	for (const id of luxury) {
		for (const principal of [dept(id), person("Allison@ExpertPartners.com", id)]) {
			assert.ok(!effectiveScopes(env.ALLOWED_SCOPES, principal).includes("ag-personal-core"));
			for (const source of ids) {
				const result = await runTool("read", { scope: "ag-personal-core", id: source, max_chars: 10 }, env, driveFor(source), principal);
				assert.equal(result.status, 200);
				assert.ok(result.ok);
				assert.equal((result.result as any).text, "Fictional ");
				assert.equal((result.result as any).nextOffset, 10);
			}
			for (const tool of ["list_scopes", "discover"]) {
				const result = await runTool(tool, { scope: "ag-personal-core" }, env, forbidden, principal);
				if (tool === "discover") assert.equal(result.status, 403);
				else {
					assert.ok(result.ok);
					assert.ok(!(result.result as any).scopes.some((s: any) => s.scope.startsWith("ag-personal-")));
				}
			}
		}
	}
});

test("non-exception files, wrong scope, nested requests, Don and other departments cannot use the exception", async () => {
	for (const id of luxury) {
		for (const args of [
			{ scope: "ag-personal-core", id: "different-personal-file" },
			{ scope: "ag-personal-marketing", id: ids[0] },
			{ scope: "ag-personal-core", id: ids[0], folder: BRAIN_FOLDERS["ag-personal-core"] },
		]) assert.equal((await runTool("read", args, env, forbidden, dept(id))).status, 403);
		for (const email of ["don@expertpartners.com", "unknown@expertpartners.com"])
			assert.equal((await runTool("read", { scope: "ag-personal-core", id: ids[0] }, env, forbidden, person(email, id))).status, 403);
	}
	for (const id of Object.keys(DEPARTMENTS).filter((id) => !luxury.includes(id) && id !== "ag-personal-cgo"))
		assert.equal((await runTool("read", { scope: "ag-personal-core", id: ids[0] }, env, forbidden, dept(id))).status, 403);
	for (const scope of ["ag-core", "ag-marketing"])
		assert.equal((await runTool("read", { scope, id: ids[0] }, env, forbidden, dept("ag-personal-cgo"))).status, 403);
});

test("exception still requires allowlist, valid five-file secret, membership, same version and no withholding", async () => {
	const args = { scope: "ag-personal-core", id: ids[0] };
	for (const allowed of ["ag-core", "ag-personal-core", "hq-core"])
		assert.equal((await runTool("read", args, { ...env, ALLOWED_SCOPES: allowed }, forbidden, dept("ag-ceo"))).status, 403);
	assert.equal((await runTool("read", args, { ...env, FILE_READ_EXCEPTIONS: undefined }, forbidden, dept("ag-ceo"))).status, 403);
	for (const secret of ["{", "[]", "{}", JSON.stringify({ "ag-shared-brand": [...ids, "sixth"] }), JSON.stringify({ "ag-shared-brand": Array(5).fill(ids[0]) })])
		assert.equal((await runTool("read", args, { ...env, FILE_READ_EXCEPTIONS: secret }, forbidden, dept("ag-ceo"))).status, 502);
	assert.equal((await runTool("read", args, { ...env, WITHHELD_SOURCES: JSON.stringify([ids[0]]) }, forbidden, dept("ag-ceo"))).status, 403);
	assert.equal((await runTool("read", args, env, driveFor(ids[0]!, { moved: true }), dept("ag-ceo"))).status, 403);
	const changed = await runTool("read", args, env, driveFor(ids[0]!, { changed: true }), dept("ag-ceo"));
	assert.equal(changed.status, 502);
	assert.equal((changed as any).detail, "changed_during_read");
});
