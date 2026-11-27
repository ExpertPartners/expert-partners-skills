import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { URL } from "node:url";
import { runTool, TOOLS } from "../src/tools.ts";
import { withRoots } from "./roots.ts";

const config = JSON.parse(readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8").replace(/^\s*\/\/.*$/gm, ""));
const env = { ALLOWED_SCOPES: config.vars.ALLOWED_SCOPES as string };
const projects = [
	{ scope: "ag-course-development", folder: "18f7KzM9FSwfLCq5j8ao7huFBzSY0CTAH", owner: "ag-ceo" },
	{ scope: "ag-buyers", folder: "18rDjhZ2CxUMZdY84_5U2ln7Sy3hxPapH", owner: "ag-cro" },
	{ scope: "ag-transactions", folder: "1uTtK6tKQv2VIWUgZwv2UhZq9kPiJtxGA", owner: "ag-coo" },
	{ scope: "ag-show", folder: "1HsjeTRrieZHxuWNSGiQLehdM3-BT6jCL", owner: "ag-cgo" },
];
const person = { kind: "person", email: "allison@expertpartners.com" } as const;
const file = { id: "project-doc", name: "Project document", mimeType: "text/plain", modifiedTime: "2026-11-27T00:00:00Z", version: "1" };

test("AG project scopes support existing MCP arguments without folder or new tools", async () => {
	assert.deepEqual(TOOLS.map((t) => t.name), ["list_scopes", "discover", "read", "decisions"]);
	const listed = await runTool("list_scopes", {}, env, async () => { throw Error("No Drive call"); }, person);
	assert.ok(listed.ok);
	for (const p of projects) {
		assert.ok((listed.result as any).scopes.some((s: any) => s.scope === p.scope && s.folderId === p.folder));
		const calls: string[] = [];
		const drive = withRoots(async (path) => {
			calls.push(path);
			const url = new URL(path, "https://drive.invalid");
			assert.equal(url.searchParams.get("q"), `'${p.folder}' in parents and trashed=false`);
			return Response.json({ files: [] });
		});
		const result = await runTool("discover", { scope: p.scope }, env, drive, person);
		assert.ok(result.ok);
		assert.equal((result.result as any).folderId, p.folder);
		assert.equal((result.result as any).complete, true);
		assert.equal(calls.length, 1);
	}
});

test("project owners and AG CEO can use project scopes, other profiles cannot", async () => {
	for (const p of projects) {
		for (const id of ["ag-ceo", "ag-cgo", "ag-cro", "ag-coo", "ag-cco", "ag-personal-cgo", "ep-ceo", "hq-chro"]) {
			const permitted = id === "ag-ceo" || id === p.owner;
			const r = await runTool("discover", { scope: p.scope }, env, withRoots(async () => {
				assert.ok(permitted, "Unauthorized caller reached Drive");
				return Response.json({ files: [] });
			}), { kind: "department", id });
			assert.equal(r.status, permitted ? 200 : 403, `${id} / ${p.scope}`);
		}
		for (const email of ["don@expertpartners.com", "unknown@expertpartners.com"]) {
			for (const tool of ["discover", "read"]) {
				const r = await runTool(tool, { scope: p.scope, id: file.id }, env, async () => { throw Error("No Drive call"); }, { kind: "person", email });
				assert.equal(r.status, 403);
			}
		}
		const disabled = await runTool("discover", { scope: p.scope }, { ALLOWED_SCOPES: "ag-core" }, async () => { throw Error("No Drive call"); }, person);
		assert.equal(disabled.status, 403);
	}
});

test("every project supports verified paged reads and preserves file withholding", async () => {
	for (const p of projects) {
		const drive = withRoots(async (path) => {
			const url = new URL(path, "https://drive.invalid");
			if (url.pathname === "/drive/v3/files") {
				assert.equal(url.searchParams.get("q"), `'${p.folder}' in parents and trashed=false`);
				return Response.json({ files: [file] });
			}
			assert.equal(url.pathname, `/drive/v3/files/${file.id}`);
			return url.searchParams.get("alt") === "media" ? new Response("abcdef") : Response.json(file);
		});
		const first = await runTool("read", { scope: p.scope, id: file.id, max_chars: 3 }, env, drive, person);
		assert.ok(first.ok);
		const page = first.result as any;
		assert.equal(page.text, "abc");
		assert.equal(page.nextOffset, 3);
		const next = await runTool("read", { scope: p.scope, id: file.id, offset: 3, expect_version: page.file.version, expect_content: page.contentSha256 }, env, drive, person);
		assert.ok(next.ok);
		assert.equal((next.result as any).text, "def");
		assert.equal((next.result as any).nextOffset, null);
		const withheld = await runTool("read", { scope: p.scope, id: file.id }, { ...env, WITHHELD_SOURCES: JSON.stringify([file.id]) }, async () => { throw Error("No Drive call"); }, person);
		assert.equal(withheld.status, 403);
	}
});
