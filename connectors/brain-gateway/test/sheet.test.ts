import { test } from "node:test";
import assert from "node:assert/strict";
import { BrainError, BRAIN_FOLDERS, createBrainReads, MAX_CHARS, SHEET_MAX_BYTES, SHEET_MAX_CHARS } from "../src/brain.ts";
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

function bigFake(opts: { rows: string[][]; versions?: string[]; statuses?: { status: number; retryAfter?: string }[]; title?: string }) {
	const calls: string[] = [];
	let v = 0;
	const versions = opts.versions ?? ["7"];
	const statuses = [...(opts.statuses ?? [])];
	const title = opts.title ?? "Source Inventory";
	const drive = async (path: string) => {
		calls.push(path);
		const url = new URL(path, "https://x");
		if (url.pathname === "/drive/v3/files")
			return new Response(JSON.stringify({ files: [{ id: ID, name: "Ledger", mimeType: SHEET, modifiedTime: "x", version: "7" }] }), { status: 200 });
		if (url.pathname === `/drive/v3/files/${ID}`)
			return new Response(JSON.stringify({ id: ID, name: "Ledger", mimeType: SHEET, modifiedTime: "x", version: versions[Math.min(v++, versions.length - 1)] }), { status: 200 });
		if (url.pathname === `/v4/spreadsheets/${ID}`) return new Response(JSON.stringify({ sheets: [{ properties: { title } }] }), { status: 200 });
		if (url.pathname.startsWith(`/v4/spreadsheets/${ID}/values/`)) {
			const s = statuses.shift();
			if (s) return new Response("busy", { status: s.status, headers: s.retryAfter !== undefined ? { "retry-after": s.retryAfter } : {} });
			assert.equal(decodeURIComponent(url.pathname.split("/values/")[1]!), `'${title.replace(/'/g, "''")}'`);
			return new Response(JSON.stringify({ range: `'x'!A1:Z${opts.rows.length}`, values: opts.rows }), { status: 200 });
		}
		return new Response("nope", { status: 404 });
	};
	return { drive, calls };
}

async function readAll(reads: ReturnType<typeof createBrainReads>, max: number, sheet = "Source Inventory") {
	let offset: number | null = 0;
	let text = "";
	let version: string | undefined;
	const pages: { text: string; partialRow?: boolean; version: string }[] = [];
	while (offset !== null) {
		const r: any = await reads.read("hq-core", ID, offset, max, undefined, sheet, version);
		version ??= r.file.version;
		pages.push({ text: r.text, partialRow: r.partialRow, version: r.file.version });
		text += r.text;
		offset = r.nextOffset;
	}
	return { text, pages };
}

test("a tab above the document cap pages completely on whole rows with one version", async () => {
	const rows = Array.from({ length: 3000 }, (_, i) => [`id-${i}`, "x".repeat(700), `é ${i}`]);
	const reads = createBrainReads(bigFake({ rows }).drive, undefined, undefined, async () => {});
	const { text, pages } = await readAll(reads, 200_000);
	assert.ok(text.length > MAX_CHARS);
	const lines = text.trimEnd().split("\n");
	assert.equal(lines.length, 3001);
	assert.equal(lines[1], `R1\t${JSON.stringify(rows[0])}`);
	assert.equal(lines[3000], `R3000\t${JSON.stringify(rows[2999])}`);
	for (const p of pages) {
		assert.ok(p.text.length <= 200_000);
		assert.ok(p.text.endsWith("\n"));
		assert.equal(p.partialRow, undefined);
		assert.equal(p.version, "7");
	}
});

test("one row longer than the page is split and flagged, and joins back exactly", async () => {
	const rows = [["a"], ["y".repeat(500)], ["b"]];
	const reads = createBrainReads(bigFake({ rows }).drive, undefined, undefined, async () => {});
	const { text, pages } = await readAll(reads, 120);
	assert.ok(pages.some((p) => p.partialRow));
	assert.equal(text, `Tab Source Inventory. One line per sheet row, R number then the cells as a JSON array.\n${rows.map((r, i) => `R${i + 1}\t${JSON.stringify(r)}\n`).join("")}`);
});

test("a version change between pages refuses with changed_during_read", async () => {
	const rows = Array.from({ length: 50 }, (_, i) => [`r${i}`]);
	const reads = createBrainReads(bigFake({ rows, versions: ["7", "7", "8"] }).drive, undefined, undefined, async () => {});
	const first: any = await reads.read("hq-core", ID, 0, 100, undefined, "Source Inventory");
	await assert.rejects(reads.read("hq-core", ID, first.nextOffset, 100, undefined, "Source Inventory", first.file.version), (e: BrainError) => e.code === "changed_during_read");
});

test("429 and 503 retry no sooner than Retry-After, bounded, other failures do not retry", async () => {
	const waits: number[] = [];
	const sleep = async (ms: number) => { waits.push(ms); };
	const ok = bigFake({ rows: [["a"]], statuses: [{ status: 429, retryAfter: "2" }, { status: 503 }] });
	const r = await createBrainReads(ok.drive, undefined, undefined, sleep).read("hq-core", ID, 0, 1000, undefined, "Source Inventory");
	assert.match(r.text, /R1\t\["a"\]/);
	assert.deepEqual(waits, [2000, 2000]);
	const exhausted = bigFake({ rows: [["a"]], statuses: [{ status: 429 }, { status: 429 }, { status: 429 }] });
	await assert.rejects(createBrainReads(exhausted.drive, undefined, undefined, async () => {}).read("hq-core", ID, 0, 1000, undefined, "Source Inventory"), (e: BrainError) => e.code === "rate_limited");
	const long = bigFake({ rows: [["a"]], statuses: [{ status: 429, retryAfter: "30" }] });
	waits.length = 0;
	await assert.rejects(createBrainReads(long.drive, undefined, undefined, sleep).read("hq-core", ID, 0, 1000, undefined, "Source Inventory"), (e: BrainError) => e.code === "rate_limited");
	assert.deepEqual(waits, []);
	const fail = bigFake({ rows: [["a"]], statuses: [{ status: 500 }] });
	await assert.rejects(createBrainReads(fail.drive, undefined, undefined, sleep).read("hq-core", ID, 0, 1000, undefined, "Source Inventory"), (e: BrainError) => e.code === "incomplete_export");
	assert.equal(fail.calls.filter((c) => c.includes("/values/")).length, 1);
});

test("tab titles with quotes are escaped, empty tabs end complete", async () => {
	const reads = createBrainReads(bigFake({ rows: [], title: "Don't" }).drive, undefined, undefined, async () => {});
	const r = await reads.read("hq-core", ID, 0, 1000, undefined, "Don't");
	assert.equal(r.nextOffset, null);
});

test("a tab above the sheet cap refuses instead of truncating", async () => {
	const rows = Array.from({ length: 9 }, () => ["z".repeat(SHEET_MAX_CHARS / 8)]);
	await assert.rejects(createBrainReads(bigFake({ rows }).drive, undefined, undefined, async () => {}).read("hq-core", ID, 0, 1000, undefined, "Source Inventory"), (e: BrainError) => e.code === "too_large");
});

test("the values body is refused by bytes while streaming, before it is parsed", async () => {
	const rows = Array.from({ length: 4 }, () => ["界".repeat(SHEET_MAX_BYTES / 9)]);
	await assert.rejects(createBrainReads(bigFake({ rows }).drive, undefined, undefined, async () => {}).read("hq-core", ID, 0, 1000, undefined, "Source Inventory"), (e: BrainError) => e.code === "too_large");
});

test("a tab exactly at the character cap reads, one character more refuses", async () => {
	const header = "Tab Source Inventory. One line per sheet row, R number then the cells as a JSON array.\n";
	const fill = (extra: number) => [["a".repeat(SHEET_MAX_CHARS - header.length - 'R1\t[""]\n'.length + extra)]];
	const at = await createBrainReads(bigFake({ rows: fill(0) }).drive, undefined, undefined, async () => {}).read("hq-core", ID, 0, 1000, undefined, "Source Inventory");
	assert.equal(at.totalChars, SHEET_MAX_CHARS);
	await assert.rejects(createBrainReads(bigFake({ rows: fill(1) }).drive, undefined, undefined, async () => {}).read("hq-core", ID, 0, 1000, undefined, "Source Inventory"), (e: BrainError) => e.code === "too_large");
});

test("one character pages and the header page still join back exactly", async () => {
	const rows = [["é"], [], ["", "x"]];
	const reads = createBrainReads(bigFake({ rows }).drive, undefined, undefined, async () => {});
	const { text, pages } = await readAll(reads, 1);
	assert.equal(text, `Tab Source Inventory. One line per sheet row, R number then the cells as a JSON array.\nR1\t["é"]\nR2\t[]\nR3\t["","x"]\n`);
	assert.ok(pages.every((p) => p.text.length >= 1));
	assert.ok(pages.some((p) => p.partialRow));
});

test("trailing empty rows that Sheets omits do not leave a dangling page", async () => {
	const r = await createBrainReads(bigFake({ rows: [["a"], ["b"]] }).drive, undefined, undefined, async () => {}).read("hq-core", ID, 0, 1000, undefined, "Source Inventory");
	assert.equal(r.nextOffset, null);
	assert.ok(r.text.endsWith('R2\t["b"]\n'));
});
