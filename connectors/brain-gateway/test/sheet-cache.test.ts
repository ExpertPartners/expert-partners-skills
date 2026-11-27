import { beforeEach, test } from "node:test";
import assert from "node:assert/strict";
import { BRAIN_FOLDERS, createBrainReads, SHEET_CACHE_MAX_BYTES, sheetCache } from "../src/brain.ts";
import { runTool } from "../src/tools.ts";

beforeEach(() => sheetCache.clear());

function fixture() {
	const state = { version: "1", member: true, revoked: false, lists: 0, versions: 0, exports: 0, afterVersion: () => {} };
	const drive = async (path: string) => {
		const url = new URL(path, "https://test.invalid");
		if (url.pathname === "/drive/v3/files") {
			state.lists++;
			return Response.json({ files: state.member ? [{ id: "ledger", name: "Ledger", mimeType: "application/vnd.google-apps.spreadsheet", modifiedTime: "x" }] : [] });
		}
		if (url.pathname.startsWith("/drive/")) {
			state.versions++;
			if (state.revoked) return new Response("", { status: 403 });
			const version = state.version;
			state.afterVersion();
			return Response.json({ id: "ledger", version });
		}
		if (!path.includes("/values/")) return Response.json({ sheets: ["One", "Two"].map((title) => ({ properties: { title } })) });
		state.exports++;
		const title = decodeURIComponent(url.pathname.split("/values/")[1]!);
		// One-byte chunks exercise multi-byte UTF-8 boundaries, including supplementary characters.
		const bytes = new TextEncoder().encode(JSON.stringify({ values: [[title, "界😀é"]] }));
		return new Response(new ReadableStream({ start(c) { for (const b of bytes) c.enqueue(Uint8Array.of(b)); c.close(); } }));
	};
	return { state, drive };
}

test("persistent cache separates exact tabs, skips only export, and invalidates old versions", async () => {
	const { state, drive } = fixture();
	const read = (sheet: string) => createBrainReads(drive).read("hq-core", "ledger", 0, 1000, undefined, sheet);
	const one = await read("One");
	const two = await read("Two");
	assert.notEqual(one.text, two.text);
	assert.match(one.text, /界😀é/);
	assert.equal((await read("One")).text, one.text);
	assert.equal((await read("Two")).text, two.text);
	assert.equal(state.exports, 2);
	assert.equal(state.lists, 8);
	assert.equal(state.versions, 8);
	await assert.rejects(read("one"), (e: any) => e.code === "sheet_not_found");
	state.version = "2";
	await read("One");
	assert.equal(sheetCache.get("ledger", "1", "Two"), undefined);
	assert.equal(state.exports, 3);
});

test("a cache hit still refuses withheld, removed membership, revoked access and version drift", async () => {
	for (const failure of ["withheld", "member", "revoked", "drift", "left"]) {
		const { state, drive } = fixture();
		const read = (withheld?: Set<string>) => createBrainReads(drive, undefined, withheld).read("hq-core", "ledger", 0, 100, undefined, "One");
		await read();
		if (failure === "member") state.member = false;
		if (failure === "revoked") state.revoked = true;
		if (failure === "drift") state.afterVersion = () => { state.version = "2"; };
		if (failure === "left") state.afterVersion = () => { state.member = false; };
		await assert.rejects(read(failure === "withheld" ? new Set(["ledger"]) : undefined));
		assert.equal(sheetCache.stats().entries, 0, failure);
		assert.equal(state.exports, 1, failure);
	}
});

test("LRU is bounded, isolates file ids, retains same-version tabs and evicts oversized text", () => {
	const text = "x".repeat(SHEET_CACHE_MAX_BYTES / 4);
	sheetCache.set("a", "1", "One", text);
	sheetCache.set("a", "1", "Two", text);
	assert.equal(sheetCache.stats().bytes, SHEET_CACHE_MAX_BYTES);
	sheetCache.get("a", "1", "One");
	sheetCache.set("b", "1", "One", "b");
	assert.equal(sheetCache.get("a", "1", "Two"), undefined);
	assert.equal(sheetCache.get("a", "1", "One"), text);
	assert.equal(sheetCache.get("b", "1", "One"), "b");
	sheetCache.set("huge", "1", "One", "x".repeat(SHEET_CACHE_MAX_BYTES / 2 + 1));
	assert.equal(sheetCache.get("huge", "1", "One"), undefined);
	assert.ok(sheetCache.stats().bytes <= SHEET_CACHE_MAX_BYTES);
	sheetCache.policy("new-policy");
	assert.equal(sheetCache.stats().bytes, 0);
});

test("warm tool requests re-authorize each actor and policy, including changes during a hit", async () => {
	const { state, drive } = fixture();
	const env = { ALLOWED_SCOPES: "ag-personal-core,hq-core", WITHHELD_SOURCES: "" };
	const args = { scope: "ag-personal-core", id: "ledger", sheet: "One" };
	const leader = { kind: "person" as const, email: "allison@expertpartners.com" };
	const call = () => runTool("read", args, env, drive, leader);
	assert.equal((await call()).status, 200);
	assert.equal((await runTool("read", args, env, drive, { kind: "person", email: "don@expertpartners.com" })).status, 403);
	assert.equal((await call()).status, 200);
	const exports = state.exports;
	assert.equal((await runTool("read", args, env, drive, { kind: "department", id: "ag-personal-cgo" })).status, 200);
	assert.equal(state.exports, exports, "authorized actor can reuse text, not the prior actor's authorization");
	state.afterVersion = () => { env.WITHHELD_SOURCES = '["ledger"]'; };
	assert.equal((await call()).status, 403);
	assert.equal(sheetCache.stats().entries, 0);
	state.afterVersion = () => {};
	env.WITHHELD_SOURCES = "";
	assert.equal((await call()).status, 200);
	env.ALLOWED_SCOPES = "hq-core";
	assert.equal((await call()).status, 403);
	assert.equal(sheetCache.stats().entries, 0);
});

test("a named per-ID exception and its policy epoch are checked again on warm requests", async () => {
	const { state, drive } = fixture();
	const env = { ALLOWED_SCOPES: "ag-core,ag-marketing,ag-personal-core", FILE_READ_EXCEPTIONS: '{"ag-shared-brand":["ledger","b","c","d","e"]}' };
	const args = { scope: "ag-personal-core", id: "ledger", sheet: "One" };
	const actor = { kind: "department" as const, id: "ag-cgo" };
	const call = () => runTool("read", args, env, drive, actor);
	assert.equal((await call()).status, 200);
	assert.equal((await call()).status, 200);
	assert.equal(state.exports, 1);
	state.afterVersion = () => { env.FILE_READ_EXCEPTIONS = '{"ag-shared-brand":["other","b","c","d","e"]}'; };
	assert.equal((await call()).status, 403);
	assert.equal(sheetCache.stats().entries, 0);
});

test("nested parent moves invalidate an already cached tab", async () => {
	const { state, drive } = fixture();
	let parent = BRAIN_FOLDERS["hq-core"] as string;
	const nestedDrive = async (path: string) => {
		const url = new URL(path, "https://test.invalid");
		if (url.pathname === "/drive/v3/files/nested" || url.pathname === `/drive/v3/files/${BRAIN_FOLDERS["hq-core"]}`)
			return Response.json({ id: url.pathname.split("/").pop(), mimeType: "application/vnd.google-apps.folder", parents: [parent], driveId: "drive", trashed: false });
		return drive(path);
	};
	const read = () => createBrainReads(nestedDrive).read("hq-core", "ledger", 0, 100, "nested", "One");
	await read();
	state.afterVersion = () => { parent = "outside"; };
	await assert.rejects(read());
	assert.equal(sheetCache.stats().entries, 0);
	assert.equal(state.exports, 1);
});
