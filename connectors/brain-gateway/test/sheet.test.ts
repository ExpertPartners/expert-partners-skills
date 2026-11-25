import { test } from "node:test";
import assert from "node:assert/strict";
import { BrainError, BRAIN_FOLDERS, createBrainReads } from "../src/brain.ts";
import { driveFetch } from "../src/google.ts";

const SHEET = "application/vnd.google-apps.spreadsheet";
const ID = "sheet1";

function fake(opts: { versions?: string[]; inScope?: boolean; valuesStatus?: number; mime?: string } = {}) {
	const calls: string[] = [];
	let v = 0;
	const versions = opts.versions ?? ["7"];
	const drive = async (path: string) => {
		calls.push(path);
		const url = new URL(path, "https://x");
		if (url.pathname === "/drive/v3/files") {
			const q = url.searchParams.get("q") ?? "";
			const files = opts.inScope === false || !q.includes(BRAIN_FOLDERS["hq-core"]) ? [] : [{ id: ID, name: "Ledger", mimeType: opts.mime ?? SHEET, modifiedTime: "2026-11-25T00:00:00Z", version: "7" }];
			return new Response(JSON.stringify({ files }), { status: 200 });
		}
		if (url.pathname === `/drive/v3/files/${ID}`)
			return new Response(JSON.stringify({ id: ID, name: "Ledger", mimeType: SHEET, modifiedTime: "x", version: versions[Math.min(v++, versions.length - 1)] }), { status: 200 });
		if (url.pathname === `/v4/spreadsheets/${ID}`)
			return new Response(JSON.stringify({ sheets: [{ properties: { title: "Week 9", sheetId: 1 } }, { properties: { title: "Week 10", sheetId: 2 } }] }), { status: 200 });
		if (url.pathname.startsWith(`/v4/spreadsheets/${ID}/values/`)) {
			assert.equal(decodeURIComponent(url.pathname.split("/values/")[1]!), "'Week 10'");
			return new Response(JSON.stringify({ range: "'Week 10'!A1:C3", values: [["Source", "Clock", "Sentence"], ["ep", "00:01", "line\nwith\ttab"], ["ep2"]] }), { status: opts.valuesStatus ?? 200 });
		}
		return new Response("nope", { status: 404 });
	};
	return { drive, calls };
}

test("spreadsheet without a tab lists its tabs", async () => {
	const r = await createBrainReads(fake().drive).read("hq-core", ID);
	assert.match(r.text, /- Week 9\n- Week 10\n/);
	assert.equal(r.nextOffset, null);
});

test("one whole tab reads with sheet row numbers and verified version", async () => {
	const r = await createBrainReads(fake().drive).read("hq-core", ID, 0, 60000, undefined, "Week 10");
	assert.equal(r.sheet, "Week 10");
	assert.equal(r.file.version, "7");
	const lines = r.text.trim().split("\n");
	assert.equal(lines[1], 'R1\t["Source","Clock","Sentence"]');
	assert.equal(lines[2], 'R2\t["ep","00:01","line\\nwith\\ttab"]');
	assert.equal(lines[3], 'R3\t["ep2"]');
});

test("unknown tab, out-of-scope sheet, changed version and incomplete values all refuse", async () => {
	await assert.rejects(createBrainReads(fake().drive).read("hq-core", ID, 0, 100, undefined, "Nope"), (e: BrainError) => e.code === "sheet_not_found");
	await assert.rejects(createBrainReads(fake({ inScope: false }).drive).read("hq-core", ID, 0, 100, undefined, "Week 10"), (e: BrainError) => e.code === "not_in_scope");
	await assert.rejects(createBrainReads(fake({ versions: ["7", "8"] }).drive).read("hq-core", ID, 0, 100, undefined, "Week 10"), (e: BrainError) => e.code === "changed_during_read");
	await assert.rejects(createBrainReads(fake({ valuesStatus: 500 }).drive).read("hq-core", ID, 0, 100, undefined, "Week 10"), (e: BrainError) => e.code === "incomplete_export");
});

test("sheet is refused for a document", async () => {
	await assert.rejects(
		createBrainReads(fake({ mime: "application/vnd.google-apps.document" }).drive).read("hq-core", ID, 0, 100, undefined, "Week 10"),
		(e: BrainError) => e.code === "not_a_spreadsheet",
	);
});

test("client reaches only read paths, GET only", async () => {
	const seen: { url: string; method?: string }[] = [];
	const f = (async (url: string, init?: RequestInit) => {
		if (String(url).includes("oauth2")) return new Response(JSON.stringify({ access_token: "t", expires_in: 3600 }), { status: 200 });
		seen.push({ url: String(url), method: init?.method });
		return new Response("{}", { status: 200 });
	}) as typeof fetch;
	const { generateKeyPairSync } = await import("node:crypto");
	const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
	const key = JSON.stringify({ client_email: "a@b", private_key: privateKey.export({ type: "pkcs8", format: "pem" }) });
	const d = driveFetch(key, f);
	await d("/v4/spreadsheets/x?fields=sheets");
	assert.equal(seen[seen.length - 1]!.url, "https://sheets.googleapis.com/v4/spreadsheets/x?fields=sheets");
	assert.equal(seen[seen.length - 1]!.method, "GET");
	await assert.rejects(d("/v4/other"));
	await assert.rejects(d("/upload/drive/v3/files"));
});
