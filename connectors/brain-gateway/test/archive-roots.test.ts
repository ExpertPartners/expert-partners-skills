import { test } from "node:test";
import assert from "node:assert/strict";
import { BRAIN_FOLDERS } from "../src/brain.ts";
import { runTool } from "../src/tools.ts";

// Fictional ids. The real archive roots live only in the WITHHELD_ARCHIVE_ROOTS secret.
const DOC = "application/vnd.google-apps.document";
const FOLDER = "application/vnd.google-apps.folder";
const EP = BRAIN_FOLDERS["ep-core"];
const AG = BRAIN_FOLDERS["ag-core"];
const OPS = BRAIN_FOLDERS["hq-operations"];
const MARKETING = BRAIN_FOLDERS["ag-marketing"];
const STRONG = BRAIN_FOLDERS["ag-strong-ones"];
const ARCHIVES = ["ep-archived", "ag-archived", "so-archives", "ops-archives"];
const env = {
	ALLOWED_SCOPES: "ep-core,ag-core,hq-operations,ag-marketing,ag-strong-ones",
	WITHHELD_SOURCES: JSON.stringify(["quarantined-doc"]),
	WITHHELD_ARCHIVE_ROOTS: JSON.stringify(ARCHIVES),
};

type Node = { mimeType: string; parents: string[]; drive: string };
const folder = (parent: string, drive = "D-AG"): Node => ({ mimeType: FOLDER, parents: [parent], drive });
const doc = (parent: string, drive = "D-AG"): Node => ({ mimeType: DOC, parents: [parent], drive });
const NODES: Record<string, Node> = {
	[EP]: folder("D-EP", "D-EP"),
	"ep-archived": folder(EP, "D-EP"),
	"ep-old": doc("ep-archived", "D-EP"),
	"ep-current": doc(EP, "D-EP"),
	"quarantined-doc": doc(EP, "D-EP"),
	[AG]: folder("D-AG"),
	"sources-history": folder(AG),
	"ag-current": doc("sources-history"),
	"ag-archived": folder("sources-history"),
	"ag-old": doc("ag-archived"),
	"ag-deep": folder("ag-archived"),
	"ag-deep-old": doc("ag-deep"),
	[MARKETING]: folder("D-AG"),
	[STRONG]: folder(MARKETING),
	"so-current": doc(STRONG),
	"so-archives": folder(STRONG),
	"so-old": doc("so-archives"),
	[OPS]: folder("D-HQ", "D-HQ"),
	"ops-archives": folder(OPS, "D-HQ"),
	"ops-old": doc("ops-archives", "D-HQ"),
	"ops-current": doc(OPS, "D-HQ"),
};

async function drive(path: string) {
	const url = new URL(path, "https://x");
	const q = url.searchParams.get("q");
	if (url.pathname === "/drive/v3/files" && q) {
		const parent = q.match(/^'([^']+)' in parents/)![1]!;
		const files = Object.entries(NODES)
			.filter(([, n]) => n.parents.includes(parent))
			.map(([id, n]) => ({ id, name: `n-${id}`, mimeType: n.mimeType, modifiedTime: "2026-11-27T00:00:00Z", version: "1" }));
		return Response.json({ files });
	}
	const exp = url.pathname.match(/^\/drive\/v3\/files\/([^/]+)\/export$/);
	if (exp) return new Response(`body of ${exp[1]}`);
	const meta = url.pathname.match(/^\/drive\/v3\/files\/([^/]+)$/);
	if (meta) {
		const id = decodeURIComponent(meta[1]!);
		const n = NODES[id];
		if (!n) return new Response("missing", { status: 404 });
		if (url.searchParams.get("fields")!.includes("trashed")) return Response.json({ id, mimeType: n.mimeType, parents: n.parents, trashed: false, driveId: n.drive });
		return Response.json({ id, name: `n-${id}`, mimeType: n.mimeType, modifiedTime: "2026-11-27T00:00:00Z", version: "1" });
	}
	return new Response("nope", { status: 404 });
}

const ids = (r: any) => (r.result.files as { id: string }[]).map((f) => f.id).sort();
const discover = (scope: string, folder?: string, e: object = env) => runTool("discover", { scope, ...(folder ? { folder } : {}) }, e, drive);
const read = (scope: string, id: string, folder?: string, e: object = env) => runTool("read", { scope, id, ...(folder ? { folder } : {}) }, e, drive);

test("archive roots are never listed, and current siblings and the exact withheld source keep their meaning", async () => {
	const ep = await discover("ep-core");
	assert.ok(ep.ok);
	assert.deepEqual(ids(ep), ["ep-current"]);
	assert.equal((ep.result as any).withheld, 2, "the archive folder and the quarantined source");
	const ops = await discover("hq-operations");
	assert.deepEqual(ids(ops), ["ops-current"]);
	const so = await discover("ag-strong-ones");
	assert.deepEqual(ids(so), ["so-current"]);
	assert.equal((await read("hq-operations", "ops-current")).status, 200);
	assert.equal((await read("ep-core", "quarantined-doc")).status, 403);
});

test("a mixed sources-and-history folder keeps serving current sources while its archive subfolder is withheld", async () => {
	const mixed = await discover("ag-core", "sources-history");
	assert.ok(mixed.ok, JSON.stringify(mixed));
	assert.deepEqual(ids(mixed), ["ag-current"]);
	assert.equal((mixed.result as any).withheld, 1);
	const r = await read("ag-core", "ag-current", "sources-history");
	assert.equal(r.status, 200);
	assert.equal((r as any).result.text, "body of ag-current");
});

test("an archive root and every folder below it refuse discovery and reads, by any route", async () => {
	const cases: [string, string, string?][] = [
		["ep-core", "ep-archived"], ["ag-core", "ag-archived"], ["ag-core", "ag-deep"], ["ag-strong-ones", "so-archives"],
		["hq-operations", "ops-archives"], ["ag-marketing", "so-archives"], ["ag-marketing", STRONG],
	];
	for (const [scope, f] of cases) {
		const r = await discover(scope, f);
		assert.equal(r.status, 403, `${scope} ${f}`);
		assert.equal((r as any).detail, "not_in_scope");
	}
	const reads: [string, string, string | undefined][] = [
		["ep-core", "ep-old", "ep-archived"], ["ep-core", "ep-old", undefined], ["ag-core", "ag-old", "ag-archived"],
		["ag-core", "ag-deep-old", "ag-deep"], ["ag-strong-ones", "so-old", "so-archives"], ["ag-marketing", "so-old", "so-archives"],
		["hq-operations", "ops-old", "ops-archives"], ["hq-operations", "ops-old", undefined],
	];
	for (const [scope, id, f] of reads) {
		const r = await read(scope, id, f);
		assert.equal(r.status, 403, `${scope} ${id} ${f}`);
		assert.ok(!JSON.stringify(r).includes("body of"), "no archived text");
	}
});

test("without the archive list the folders behave as before, and a malformed list refuses everything", async () => {
	const before = { ALLOWED_SCOPES: env.ALLOWED_SCOPES };
	assert.deepEqual(ids(await discover("hq-operations", undefined, before)), ["ops-archives", "ops-current"]);
	assert.equal((await read("hq-operations", "ops-old", "ops-archives", before)).status, 200);
	for (const bad of ["{", "{}", '["ok", 3]', '["../x"]']) {
		const r = await discover("hq-operations", undefined, { ...env, WITHHELD_ARCHIVE_ROOTS: bad });
		assert.equal(r.status, 502, bad);
		assert.equal((r as any).detail, "withheld_invalid");
		assert.equal((await read("hq-operations", "ops-current", undefined, { ...env, WITHHELD_ARCHIVE_ROOTS: bad })).status, 502);
	}
	assert.deepEqual(ids(await discover("hq-operations", undefined, { ...env, WITHHELD_ARCHIVE_ROOTS: "" })), ["ops-archives", "ops-current"]);
});
