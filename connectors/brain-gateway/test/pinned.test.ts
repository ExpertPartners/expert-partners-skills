import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { URL } from "node:url";
import { DEPARTMENTS } from "../src/access.ts";
import { runTool } from "../src/tools.ts";

const config = JSON.parse(readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8").replace(/^\s*\/\/.*$/gm, ""));
const NAME = "gap108-week2-builder";
const DRIVE = "fictional-course-drive";
const pins = [
	{ id: "pinned-builder", parent: "fictional-captures", drive: DRIVE },
	{ id: "pinned-visual", parent: "fictional-frames", drive: DRIVE },
	{ id: "pinned-native", parent: "fictional-frames", drive: DRIVE },
];
const env = { ALLOWED_SCOPES: config.vars.ALLOWED_SCOPES as string, PINNED_FILE_READS: JSON.stringify({ [NAME]: pins }) };
const allison = { kind: "person" as const, email: "Allison@ExpertPartners.com" };
const BODY = "Fictional pinned body é 🙂 line\n".repeat(40);
const forbidden = async () => { throw new Error("Refused request must not reach Drive"); };

type Opts = { wrongDrive?: boolean; trashed?: boolean; notUnderParent?: boolean; movedDuringRead?: boolean; versions?: string[]; pageTokens?: boolean };
/** Folder ancestry above each pinned parent, ending at the shared drive's top folder. */
const ANCESTRY: Record<string, string[]> = {
	"fictional-captures": ["fictional-course"],
	"fictional-frames": ["fictional-course"],
	"fictional-course": [DRIVE],
	[DRIVE]: [],
};
function ancestry(url: URL) {
	const id = decodeURIComponent(url.pathname.slice("/drive/v3/files/".length));
	if (url.searchParams.get("fields") !== "id,parents" || !(id in ANCESTRY)) return undefined;
	return Response.json({ id, parents: ANCESTRY[id] });
}
function driveFor(pin: (typeof pins)[number], o: Opts = {}) {
	let lists = 0;
	let v = 0;
	const versions = o.versions ?? ["3"];
	return async (path: string) => {
		const url = new URL(path, "https://drive.invalid");
		if (url.pathname === "/drive/v3/files") {
			assert.equal(url.searchParams.get("q"), `'${pin.parent}' in parents and trashed=false`);
			lists++;
			const gone = o.notUnderParent || (o.movedDuringRead && lists > 1);
			if (o.pageTokens && !url.searchParams.get("pageToken")) return Response.json({ files: [{ id: "sibling" }], nextPageToken: "p2" });
			return Response.json({ files: gone ? [{ id: "sibling" }] : [{ id: "sibling" }, { id: pin.id }] });
		}
		const folder = ancestry(url);
		if (folder) return folder;
		assert.ok(url.pathname.startsWith(`/drive/v3/files/${pin.id}`), url.pathname);
		if (url.searchParams.get("alt") === "media") return new Response(BODY, { headers: { "content-type": "text/markdown" } });
		const fields = url.searchParams.get("fields") ?? "";
		if (fields.includes("driveId"))
			return Response.json({ id: pin.id, mimeType: "text/markdown", driveId: o.wrongDrive ? "other-drive" : pin.drive, trashed: !!o.trashed });
		return Response.json({ id: pin.id, name: "Fictional pinned source", mimeType: "text/markdown", modifiedTime: "x", version: versions[Math.min(v++, versions.length - 1)] });
	};
}
async function readAll(pin: (typeof pins)[number], max: number) {
	let offset: number | null = 0;
	let text = "";
	let version: string | undefined;
	while (offset !== null) {
		const r = await runTool("read", { scope: NAME, id: pin.id, offset, max_chars: max, ...(version ? { expect_version: version } : {}) }, env, driveFor(pin), allison);
		assert.equal(r.status, 200, JSON.stringify(r));
		const p = (r as any).result;
		version ??= p.file.version;
		assert.equal(p.file.version, version);
		assert.equal(p.exception, NAME);
		text += p.text;
		offset = p.nextOffset;
	}
	return text;
}
const noLeak = (r: unknown) => {
	const s = JSON.stringify(r);
	for (const p of pins) for (const v of [p.id, p.parent, p.drive]) assert.ok(!s.includes(v), `leaked ${v}`);
	assert.ok(!s.includes("Fictional pinned"));
};

test("Allison as leader reads each pinned file completely, paged with one version, and across Drive list pages", async () => {
	for (const pin of pins) assert.equal(await readAll(pin, 97), BODY);
	const r = await runTool("read", { scope: NAME, id: pins[0]!.id }, env, driveFor(pins[0]!, { pageTokens: true }), allison);
	assert.equal(r.status, 200);
});

test("the exception never appears in list_scopes or discover", async () => {
	const ls = await runTool("list_scopes", {}, env, forbidden, allison);
	assert.ok(ls.ok && !JSON.stringify(ls.result).includes(NAME));
	const d = await runTool("discover", { scope: NAME }, env, forbidden, allison);
	assert.equal(d.status, 403);
	noLeak(d);
});

test("Don, unknown people, every department, narrowed Hub sessions and AG actors are refused before Drive", async () => {
	const principals = [
		{ kind: "person" as const, email: "don@expertpartners.com" },
		{ kind: "person" as const, email: "unknown@expertpartners.com" },
		...Object.keys(DEPARTMENTS).map((id) => ({ kind: "department" as const, id })),
		...Object.keys(DEPARTMENTS).map((department) => ({ kind: "person" as const, email: "allison@expertpartners.com", department })),
	];
	for (const principal of principals) {
		const r = await runTool("read", { scope: NAME, id: pins[0]!.id }, env, forbidden, principal);
		assert.equal(r.status, 403, JSON.stringify(principal));
		noLeak(r);
	}
});

test("wrong ID, folder, sheet, missing secret and withheld files are refused before Drive", async () => {
	for (const args of [{ scope: NAME, id: "sibling" }, { scope: NAME, id: pins[0]!.id, folder: pins[0]!.parent }]) {
		const r = await runTool("read", args, env, forbidden, allison);
		assert.equal(r.status, 403);
		noLeak(r);
	}
	assert.notEqual((await runTool("read", { scope: NAME, id: pins[0]!.id, sheet: "x" }, env, forbidden, allison)).status, 200);
	assert.equal((await runTool("read", { scope: NAME, id: pins[0]!.id }, { ...env, PINNED_FILE_READS: undefined }, forbidden, allison)).status, 403);
	for (const w of [pins[0]!.id, pins[0]!.parent]) {
		const r = await runTool("read", { scope: NAME, id: pins[0]!.id }, { ...env, WITHHELD_SOURCES: JSON.stringify([w]) }, forbidden, allison);
		assert.equal(r.status, 403);
		noLeak(r);
	}
});

test("wrong drive, trashed, not under the pinned parent and moved during the read are refused without metadata", async () => {
	for (const o of [{ wrongDrive: true }, { trashed: true }, { notUnderParent: true }]) {
		const r = await runTool("read", { scope: NAME, id: pins[1]!.id }, env, driveFor(pins[1]!, o), allison);
		assert.equal(r.status, 403, JSON.stringify(o));
		noLeak(r);
	}
	const moved = await runTool("read", { scope: NAME, id: pins[1]!.id }, env, driveFor(pins[1]!, { movedDuringRead: true }), allison);
	assert.equal(moved.status, 502);
	assert.equal((moved as any).detail, "left_scope");
	noLeak(moved);
});

test("a pinned file below a withheld archive folder is refused at any ancestor, and other pins still read", async () => {
	for (const archive of ["fictional-course", DRIVE, pins[1]!.parent]) {
		const w = { ...env, WITHHELD_ARCHIVE_ROOTS: JSON.stringify([archive]) };
		const r = await runTool("read", { scope: NAME, id: pins[1]!.id }, w, archive === pins[1]!.parent ? forbidden : driveFor(pins[1]!), allison);
		assert.equal(r.status, 403, archive);
		noLeak(r);
	}
	const unrelated = { ...env, WITHHELD_ARCHIVE_ROOTS: JSON.stringify(["unrelated-archive"]) };
	assert.equal((await runTool("read", { scope: NAME, id: pins[1]!.id }, unrelated, driveFor(pins[1]!), allison)).status, 200);
});

test("version drift during a read or between pages refuses", async () => {
	const during = await runTool("read", { scope: NAME, id: pins[2]!.id }, env, driveFor(pins[2]!, { versions: ["3", "4"] }), allison);
	assert.equal((during as any).detail, "changed_during_read");
	noLeak(during);
	const between = await runTool("read", { scope: NAME, id: pins[2]!.id, offset: 10, expect_version: "2" }, env, driveFor(pins[2]!), allison);
	assert.equal((between as any).detail, "changed_during_read");
});

test("a malformed secret refuses every pinned read", async () => {
	const bad = [
		"{",
		"[]",
		"{}",
		JSON.stringify({ [NAME]: pins.slice(0, 2) }),
		JSON.stringify({ [NAME]: [...pins, { id: "fourth", parent: "p", drive: DRIVE }] }),
		JSON.stringify({ [NAME]: [pins[0], pins[0], pins[1]] }),
		JSON.stringify({ [NAME]: [{ id: pins[0]!.id, parent: pins[0]!.parent }, pins[1], pins[2]] }),
		JSON.stringify({ [NAME]: [{ ...pins[0], parent: "bad/../x" }, pins[1], pins[2]] }),
	];
	for (const secret of bad) {
		const r = await runTool("read", { scope: NAME, id: pins[0]!.id }, { ...env, PINNED_FILE_READS: secret }, forbidden, allison);
		assert.equal(r.status, 502, secret);
		noLeak(r);
	}
});
