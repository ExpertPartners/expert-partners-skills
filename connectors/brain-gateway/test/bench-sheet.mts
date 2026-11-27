// Prepare fixtures in a different process so fixture construction is not charged to read memory.
// node --experimental-strip-types test/bench-sheet.mts prepare /tmp/brain-sheet.json [real|max]
// node --expose-gc --experimental-strip-types test/bench-sheet.mts run /tmp/brain-sheet.json [prefill]
import { createReadStream, writeFileSync } from "node:fs";
import { Readable } from "node:stream";
import { createHash } from "node:crypto";
import { runTool } from "../src/tools.ts";
import { SHEET_MAX_BYTES, SHEET_MAX_CHARS, sheetCache } from "../src/brain.ts";

const [mode, path, option] = process.argv.slice(2);
if (!path || !["prepare", "run"].includes(mode!)) throw new Error("Use prepare|run and an absolute fixture path");
const title = "Coverage";
if (mode === "prepare") {
	const max = option === "max";
	const n = max ? 16_000 : 10_201;
	const target = max ? SHEET_MAX_CHARS : 7_145_792;
	const cols = max ? 1 : 15;
	let remaining = target - `Tab ${title}. One line per sheet row, R number then the cells as a JSON array.\n`.length;
	const values = Array.from({ length: n }, (_, i) => {
		const overhead = `R${i + 1}\t${JSON.stringify(Array(cols).fill(""))}\n`.length;
		const size = Math.floor(remaining / (n - i)) - overhead;
		remaining -= size + overhead;
		let left = size;
		return Array.from({ length: cols }, (_, j) => {
			const length = Math.floor(left / (cols - j));
			left -= length;
			return (max ? "界界界界界界界aaa" : "ledger source café 界😀 value ").repeat(Math.ceil(length / (max ? 10 : 29))).slice(0, length);
		});
	});
	const expected = `Tab ${title}. One line per sheet row, R number then the cells as a JSON array.\n${values.map((row, i) => `R${i + 1}\t${JSON.stringify(row)}\n`).join("")}`;
	// Fixture cells can split a surrogate, so JSON escaping can increase the serialized size.
	if (expected.length !== target) throw new Error(`Fixture size ${expected.length}, expected ${target}`);
	let body = JSON.stringify({ values });
	if (max) body += " ".repeat(SHEET_MAX_BYTES - Buffer.byteLength(body));
	writeFileSync(path, body);
	console.log(JSON.stringify({ bytes: Buffer.byteLength(body), chars: expected.length, sha256: createHash("sha256").update(expected).digest("hex") }));
} else {
	const calls = { values: 0, versions: 0, lists: 0 };
	const drive = async (p: string) => {
		if (p.includes("/values/")) { calls.values++; return new Response(Readable.toWeb(createReadStream(path, { highWaterMark: 65_536 })) as unknown as ReadableStream); }
		if (p.startsWith("/v4/")) return Response.json({ sheets: [{ properties: { title } }] });
		if (p.startsWith("/drive/v3/files?")) { calls.lists++; return Response.json({ files: [{ id: "benchmark", name: "Benchmark", mimeType: "application/vnd.google-apps.spreadsheet", modifiedTime: "x" }] }); }
		calls.versions++;
		return Response.json({ id: "benchmark", version: "1" });
	};
	// Establish the normal tool policy epoch before prefilling the full cache budget.
	await runTool("list_scopes", {}, { ALLOWED_SCOPES: "hq-core" }, drive);
	if (option === "prefill") sheetCache.set("other", "1", "Other", "x".repeat(8_000_000));
	globalThis.gc?.();
	const baselineRss = process.memoryUsage().rss;
	const cpu = () => { const u = process.cpuUsage(); return (u.user + u.system) / 1000; };
	const pages: { cpuMs: number; wallMs: number }[] = [];
	const hash = createHash("sha256");
	let offset: number | null = 0, total = 0;
	while (offset !== null) {
		const c = cpu(), t = Date.now();
		const r = await runTool("read", { scope: "hq-core", id: "benchmark", sheet: title, offset, max_chars: 200_000, expect_version: "1" }, { ALLOWED_SCOPES: "hq-core" }, drive);
		if (!r.ok) throw new Error(JSON.stringify(r));
		pages.push({ cpuMs: +(cpu() - c).toFixed(2), wallMs: Date.now() - t });
		const page = r.result as { nextOffset: number | null; text: string; totalChars: number };
		hash.update(page.text);
		offset = page.nextOffset;
		total = page.totalChars;
		// The maximum-size tab deliberately exceeds the cache admission budget. One cold page suffices.
		if (total > 8_000_000) break;
	}
	console.log(JSON.stringify({ total, pages, calls, cache: sheetCache.stats(), baselineRss, peakRss: process.resourceUsage().maxRSS * 1024, endMemory: process.memoryUsage(), sha256: offset === null ? hash.digest("hex") : null }));
}
