import { test } from "node:test";
import assert from "node:assert/strict";
import { COMPANY_CORES, DEPARTMENTS, departmentForToken, effectiveScopes, sha256Hex } from "../src/access.ts";
import { BRAIN_FOLDERS } from "../src/brain.ts";
import { runTool } from "../src/tools.ts";

const all = Object.keys(BRAIN_FOLDERS).filter((s) => s !== "ag-private").join(",");
const source = { id: "synthetic-source", name: "Synthetic", version: "7", mimeType: "application/vnd.google-apps.document", modifiedTime: "2026-11-27T00:00:00Z" };

test("every fixed token profile lists, discovers and reads every company Core to terminal null", async () => {
	for (const id of Object.keys(DEPARTMENTS)) {
		const token = `synthetic-${id}`;
		const resolved = await departmentForToken(JSON.stringify({ [await sha256Hex(token)]: id }), token);
		assert.equal(resolved, id);
		const principal = { kind: "department" as const, id: resolved! };
		const listed = await runTool("list_scopes", {}, { ALLOWED_SCOPES: all }, undefined, principal);
		assert.ok(listed.ok);
		for (const scope of COMPANY_CORES) {
			assert.ok((listed.result as any).scopes.some((s: any) => s.scope === scope));
			const drive = async (path: string) => {
				const url = new URL(path, "https://drive.invalid");
				if (url.pathname === "/drive/v3/files") {
					assert.equal(url.searchParams.get("q"), `'${BRAIN_FOLDERS[scope]}' in parents and trashed=false`);
					return Response.json({ files: [source] });
				}
				if (url.pathname.endsWith("/export")) return new Response("first second third");
				return Response.json(source);
			};
			const discovery = await runTool("discover", { scope }, { ALLOWED_SCOPES: all }, drive, principal);
			assert.equal(discovery.status, 200, `${id} discover ${scope}, formerly 403`);
			let offset: number | null = 0;
			let joined = "";
			do {
				const page = await runTool("read", { scope, id: source.id, offset, max_chars: 6, expect_version: "7" }, { ALLOWED_SCOPES: all }, drive, principal);
				assert.ok(page.ok, `${id} read ${scope}`);
				assert.equal((page.result as any).file.version, "7");
				joined += (page.result as any).text;
				offset = (page.result as any).nextOffset;
			} while (offset !== null);
			assert.equal(joined, "first second third");
		}
	}
});

test("Core grants preserve deployed allowlist, withholding and non-Core boundaries for every profile", async () => {
	for (const [id, d] of Object.entries(DEPARTMENTS)) {
		const principal = { kind: "department" as const, id };
		assert.deepEqual(effectiveScopes("", principal), []);
		for (const scope of Object.keys(BRAIN_FOLDERS)) {
			if (COMPANY_CORES.includes(scope as any) || d.scopes.includes(scope as any) || d.exceptions.includes(scope as any)) continue;
			for (const tool of ["discover", "read"]) {
				const denied = await runTool(tool, { scope, id: "not-an-exception" }, { ALLOWED_SCOPES: all }, async () => { throw new Error("Denied call reached Drive"); }, principal);
				assert.equal(denied.status, 403, `${id} ${tool} ${scope}`);
			}
		}
		for (const scope of COMPANY_CORES) {
			const withheld = await runTool("read", { scope, id: source.id }, { ALLOWED_SCOPES: all, WITHHELD_SOURCES: JSON.stringify([source.id]) }, async () => { throw new Error("Withheld call reached Drive"); }, principal);
			assert.equal(withheld.status, 403);
		}
	}
});

test("Don narrowed to any AI profile still never acquires AG access", () => {
	for (const department of Object.keys(DEPARTMENTS)) {
		assert.ok(effectiveScopes(all, { kind: "person", email: "don@expertpartners.com", department }).every((s) => !s.startsWith("ag-")));
	}
});
