import { beforeEach, test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { BRAIN_FOLDERS, ROW_PAGE_MAX_BYTES, sheetCache } from "../src/brain.ts";
import { runTool } from "../src/tools.ts";

beforeEach(() => sheetCache.clear());

const SHEET = "application/vnd.google-apps.spreadsheet";
const KEY = Buffer.alloc(32, 7).toString("base64url");
const TAB = "Source Inventory";

type Row = string[];
/** Emulates Sheets: a range response drops that range's empty tail; empty rows inside it come back as []. */
function sheetFake(opts: { rows: Row[]; grid: number; tab?: string }) {
	const state = { version: "602", grid: opts.grid, member: true, wholeReads: 0, rangeReads: 0, onVersion: () => {} };
	const tab = opts.tab ?? TAB;
	const trim = (rows: Row[]) => {
		let n = rows.length;
		while (n > 0 && rows[n - 1]!.length === 0) n--;
		return rows.slice(0, n);
	};
	const drive = async (path: string) => {
		const url = new URL(path, "https://x");
		if (url.pathname === "/drive/v3/files") {
			const q = url.searchParams.get("q") ?? "";
			const files = state.member && q.includes(BRAIN_FOLDERS["hq-core"]) ? [{ id: "ledger", name: "Ledger", mimeType: SHEET, modifiedTime: "x" }] : [];
			return Response.json({ files });
		}
		if (url.pathname === "/drive/v3/files/ledger") {
			const version = state.version;
			state.onVersion();
			return Response.json({ id: "ledger", name: "Ledger", mimeType: SHEET, modifiedTime: "x", version });
		}
		if (url.pathname === "/v4/spreadsheets/ledger") return Response.json({ sheets: [{ properties: { title: tab, gridProperties: { rowCount: state.grid, columnCount: 26 } } }] });
		if (url.pathname.startsWith("/v4/spreadsheets/ledger/values/")) {
			const range = decodeURIComponent(url.pathname.split("/values/")[1]!);
			const quoted = `'${tab.replace(/'/g, "''")}'`;
			if (range === quoted) {
				state.wholeReads++;
				return Response.json({ range: `${quoted}!A1:Z${state.grid}`, values: trim(opts.rows) });
			}
			const m = range.slice(quoted.length).match(/^!(\d+):(\d+)$/);
			assert.ok(range.startsWith(quoted) && m, range);
			state.rangeReads++;
			const s = Number(m![1]), e = Number(m![2]);
			const values = trim(opts.rows.slice(s - 1, e));
			return Response.json({ range: `${quoted}!A${s}:Z${e}`, ...(values.length ? { values } : {}) });
		}
		return new Response("nope", { status: 404 });
	};
	return { state, drive };
}

const env = (extra: Record<string, string> = {}) => ({ ALLOWED_SCOPES: "hq-core", ROW_CURSOR_KEY: KEY, ...extra });

async function legacy(f: ReturnType<typeof sheetFake>, tab = TAB) {
	let offset: number | null = 0, text = "";
	while (offset !== null) {
		const r: any = await runTool("read", { scope: "hq-core", id: "ledger", sheet: tab, offset, max_chars: 200_000 }, env(), f.drive);
		assert.equal(r.status, 200, JSON.stringify(r));
		text += r.result.text;
		offset = r.result.nextOffset;
	}
	sheetCache.clear();
	return text;
}

async function rows(f: ReturnType<typeof sheetFake>, args: { start_row?: number; max_rows?: number; max_chars?: number }, tab = TAB) {
	const pages: any[] = [];
	let r: any = await runTool("read", { scope: "hq-core", id: "ledger", sheet: tab, ...args }, env(), f.drive);
	while (true) {
		assert.equal(r.status, 200, JSON.stringify(r));
		pages.push(r.result);
		if (r.result.next_row === null) break;
		assert.ok(r.result.cursor);
		r = await runTool("read", { scope: "hq-core", id: "ledger", sheet: tab, cursor: r.result.cursor, max_rows: args.max_rows, max_chars: args.max_chars }, env(), f.drive);
	}
	assert.equal(pages[pages.length - 1].cursor, null);
	for (let i = 1; i < pages.length; i++) assert.equal(pages[i].start_row, pages[i - 1].covered_end_row + 1);
	assert.equal(pages[pages.length - 1].covered_end_row, pages[pages.length - 1].grid_row_count);
	return { text: pages.map((p) => p.text).join(""), pages };
}

const sha = (s: string) => createHash("sha256").update(s).digest("hex");

test("all-blank tab joins to the legacy header and single newline", async () => {
	const f = sheetFake({ rows: [], grid: 10 });
	const want = await legacy(f);
	const { text, pages } = await rows(f, { max_rows: 3 });
	assert.equal(text, want);
	assert.equal(want, `Tab ${TAB}. One line per sheet row, R number then the cells as a JSON array.\n\n`);
	assert.equal(pages[pages.length - 1].discarded_tail_rows, 10);
	assert.equal(f.state.wholeReads, 1, "row mode never reads the whole tab");
});

test("an interior blank chunk across page ends is restored, the global tail is dropped", async () => {
	const f = sheetFake({ rows: [["a"], [], [], [], [], [], ["b"], [], [], []], grid: 25 });
	const want = await legacy(f);
	for (const max_rows of [1, 2, 3, 4, 256]) {
		const { text, pages } = await rows(f, { max_rows });
		assert.equal(text, want, `max_rows ${max_rows}`);
		assert.equal(pages[pages.length - 1].discarded_tail_rows, 18);
	}
	assert.match(want, /R2\t\[\]\nR3\t\[\]\nR4\t\[\]\nR5\t\[\]\nR6\t\[\]\nR7\t\["b"\]\n$/);
});

test("leading blank rows, single-row tab and header-only grid match exactly", async () => {
	for (const [r, grid] of [[[[], [], ["x"]], 3], [[["only"]], 1], [[[], ["z"]], 1000]] as [Row[], number][]) {
		const f = sheetFake({ rows: r, grid });
		assert.equal((await rows(f, { max_rows: 2 })).text, await legacy(f));
	}
});

test("randomized Unicode, escapes and blank runs join byte for byte at many page sizes", async () => {
	let seed = 42;
	const rnd = (n: number) => ((seed = (seed * 1103515245 + 12345) % 2 ** 31), seed % n);
	const alphabet = ["a", "é", "界", "😀", '"', "\\", "\t", "\n", "'", " ", "\u2028", "0"];
	for (let t = 0; t < 30; t++) {
		const n = 1 + rnd(80);
		const data: Row[] = Array.from({ length: n }, () => (rnd(3) === 0 ? [] : Array.from({ length: 1 + rnd(4) }, (_, c) => Array.from({ length: rnd(12) }, () => alphabet[rnd(alphabet.length)]).join("") || (c === 0 ? "" : "v"))));
		for (const row of data) if (row.length && row[row.length - 1] === "") row[row.length - 1] = "end";
		const f = sheetFake({ rows: data, grid: n + rnd(40) });
		const want = await legacy(f);
		const { text } = await rows(f, { max_rows: 1 + rnd(20), max_chars: 120 + rnd(400) });
		assert.equal(sha(text), sha(want), `case ${t}`);
	}
});

test("a character-mode prefix ending on a whole row resumes with start_row and joins exactly", async () => {
	const data: Row[] = Array.from({ length: 300 }, (_, i) => (i % 7 === 3 ? [] : [`id-${i}`, "界".repeat(i % 50)]));
	data.push(["last"]);
	const f = sheetFake({ rows: data, grid: 400 });
	const want = await legacy(f);
	const first: any = await runTool("read", { scope: "hq-core", id: "ledger", sheet: TAB, offset: 0, max_chars: 5000 }, env(), f.drive);
	const prefix: string = first.result.text;
	const lastRow = Number(prefix.trimEnd().split("\n").pop()!.match(/^R(\d+)\t/)![1]);
	sheetCache.clear();
	const { text } = await rows(f, { start_row: lastRow + 1, max_rows: 17, max_chars: 3000 });
	assert.equal(prefix + text, want);
	assert.equal(sha(prefix + text), sha(want));
});

test("a row longer than max_chars or the range budget refuses, never truncates", async () => {
	const f = sheetFake({ rows: [["a"], ["y".repeat(5000)], ["b"]], grid: 3 });
	const r1: any = await runTool("read", { scope: "hq-core", id: "ledger", sheet: TAB, start_row: 2, max_chars: 1000 }, env(), f.drive);
	assert.equal(r1.status, 400);
	assert.equal(r1.detail, "row_too_large");
	const big = sheetFake({ rows: [["a"], ["界".repeat(ROW_PAGE_MAX_BYTES / 3 + 10)]], grid: 2 });
	const r2: any = await runTool("read", { scope: "hq-core", id: "ledger", sheet: TAB, start_row: 1, max_rows: 2, max_chars: 200_000 }, env(), big.drive);
	assert.equal(r2.status, 200, "the range shrinks to the row before the oversized one");
	assert.equal(r2.result.covered_end_row, 1);
	const r3: any = await runTool("read", { scope: "hq-core", id: "ledger", sheet: TAB, cursor: r2.result.cursor, max_rows: 2, max_chars: 200_000 }, env(), big.drive);
	assert.equal(r3.status, 400);
	assert.equal(r3.detail, "row_too_large");
});

test("held blank rows flush across pages when max_chars is tiny", async () => {
	const f = sheetFake({ rows: [["a"], ...Array.from({ length: 40 }, () => []), ["b"]], grid: 50 });
	assert.equal((await rows(f, { max_rows: 5, max_chars: 120 })).text, await legacy(f));
});

test("tampered, foreign, expired or keyless cursors refuse and never fabricate rows", async () => {
	const f = sheetFake({ rows: [["a"], [], [], ["b"], ["c"]], grid: 8 });
	const first: any = await runTool("read", { scope: "hq-core", id: "ledger", sheet: TAB, max_rows: 2 }, env(), f.drive);
	const c: string = first.result.cursor;
	const call = (a: Record<string, unknown>, e = env()) => runTool("read", { scope: "hq-core", id: "ledger", sheet: TAB, ...a }, e, f.drive) as Promise<any>;
	const flip = (s: string, i: number) => s.slice(0, i) + (s[i] === "A" ? "B" : "A") + s.slice(i + 1);
	for (const bad of [flip(c, 3), flip(c, c.length - 2), c.split(".")[0] + ".", "x." + c.split(".")[1], c + "A"]) assert.equal((await call({ cursor: bad })).detail, "invalid_cursor");
	assert.equal((await call({ cursor: c, sheet: "Other" })).detail, "invalid_cursor");
	assert.equal((await runTool("read", { scope: "hq-core", id: "other", sheet: TAB, cursor: c }, env(), f.drive) as any).detail, "invalid_cursor");
	assert.equal((await call({ cursor: c, expect_version: "601" })).detail, "invalid_cursor");
	assert.equal((await call({ cursor: c }, env({ ROW_CURSOR_KEY: Buffer.alloc(32, 8).toString("base64url") }))).detail, "invalid_cursor");
	// Rewrite the held-empty count with a valid shape but no valid signature.
	const forged = Buffer.from(JSON.stringify(JSON.parse(Buffer.from(c.split(".")[0]!, "base64url").toString()).map((v: unknown, i: number) => (i === 6 ? 2 : v)))).toString("base64url") + "." + c.split(".")[1];
	assert.equal((await call({ cursor: forged })).detail, "invalid_cursor");
	const keyless = await call({ cursor: c }, { ALLOWED_SCOPES: "hq-core" } as any);
	assert.equal(keyless.status, 503);
	assert.equal(keyless.detail, "cursor_unavailable");
	assert.equal((await call({ start_row: 1 }, env({ ROW_CURSOR_KEY: "short" }))).detail, "cursor_unavailable");
	assert.equal((await call({ offset: 0 }, { ALLOWED_SCOPES: "hq-core" } as any)).status, 200, "character mode needs no cursor key");
	const realNow = Date.now;
	Date.now = () => realNow() + 7 * 60 * 60 * 1000;
	try {
		assert.equal((await call({ cursor: c })).detail, "invalid_cursor");
	} finally {
		Date.now = realNow;
	}
	assert.equal((await call({ cursor: c })).status, 200);
});

test("every row page re-proves version, grid, actor, membership and withholding", async () => {
	const f = sheetFake({ rows: [["a"], ["b"], ["c"]], grid: 6 });
	const first: any = await runTool("read", { scope: "hq-core", id: "ledger", sheet: TAB, max_rows: 1 }, env(), f.drive);
	const c = first.result.cursor;
	const next = (e = env(), principal?: any) => runTool("read", { scope: "hq-core", id: "ledger", sheet: TAB, cursor: c, max_rows: 1 }, e, f.drive, principal) as Promise<any>;
	f.state.version = "603";
	assert.equal((await next()).detail, "changed_during_read");
	f.state.version = "602";
	f.state.onVersion = () => { f.state.version = "604"; };
	assert.equal((await next()).detail, "changed_during_read");
	f.state.onVersion = () => {};
	f.state.version = "602";
	f.state.grid = 7;
	assert.equal((await next()).detail, "changed_during_read");
	f.state.grid = 6;
	assert.equal((await next(env({ ALLOWED_SCOPES: "ep-core" }))).status, 403);
	assert.equal((await next(env(), { kind: "person", email: "nobody@example.com" })).status, 403);
	assert.equal((await next(env({ WITHHELD_SOURCES: '["ledger"]' }))).status, 403);
	f.state.member = false;
	assert.equal((await next()).status, 403);
	f.state.member = true;
	assert.equal((await next()).status, 200);
	const v: any = await runTool("read", { scope: "hq-core", id: "ledger", sheet: TAB, start_row: 1, expect_version: "601" }, env(), f.drive);
	assert.equal(v.detail, "changed_during_read");
});

test("row arguments are exclusive with offset and require a sheet; the advertised schema lists them", async () => {
	const f = sheetFake({ rows: [["a"]], grid: 1 });
	for (const a of [{ sheet: TAB, start_row: 1, offset: 0 }, { start_row: 1 }, { sheet: TAB, start_row: 1, cursor: "a.b" }, { max_rows: 2 }])
		assert.equal(((await runTool("read", { scope: "hq-core", id: "ledger", ...a }, env(), f.drive)) as any).status, 400, JSON.stringify(a));
	const { TOOLS } = await import("../src/tools.ts");
	const shape = TOOLS.find((t) => t.name === "read")!.schema.shape;
	for (const k of ["start_row", "max_rows", "cursor", "offset", "expect_version"]) assert.ok(k in shape, k);
	assert.ok(TOOLS.find((t) => t.name === "read")!.schema.extend({}), "MCP registration can still extend the schema");
});
