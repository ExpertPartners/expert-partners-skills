import { test } from "node:test";
import assert from "node:assert/strict";
import { BRAIN_FOLDERS, MAX_NESTED_DEPTH } from "../src/brain.ts";
import { runTool } from "../src/tools.ts";
import { effectiveScopes } from "../src/access.ts";

const DOC = "application/vnd.google-apps.document";
const FOLDER = "application/vnd.google-apps.folder";
const ROOT = BRAIN_FOLDERS["ag-marketing"];
const env = { ALLOWED_SCOPES: Object.keys(BRAIN_FOLDERS).filter((s) => !s.endsWith("-private")).join(",") };

type Node = { mimeType: string; parents: string[]; trashed?: boolean; driveId?: string; version?: string };

/** A small Drive tree. Every node names its parents; listings and metadata come from the same map. */
function tree(nodes: Record<string, Node>, bodies: Record<string, string> = {}) {
	const calls: string[] = [];
	const all: Record<string, Node> = { [ROOT]: { mimeType: FOLDER, parents: ["drive-root"], driveId: "D1" }, ...nodes };
	const drive = async (path: string) => {
		calls.push(path);
		const url = new URL(path, "https://x");
		const q = url.searchParams.get("q");
		if (url.pathname === "/drive/v3/files" && q) {
			const parent = q.match(/^'([^']+)' in parents/)![1];
			const files = Object.entries(all)
				.filter(([, n]) => n.parents.includes(parent) && !n.trashed)
				.map(([id, n]) => ({ id, name: `n-${id}`, mimeType: n.mimeType, modifiedTime: "2026-11-24T00:00:00Z", version: n.version ?? "1" }));
			return Response.json({ files });
		}
		const exp = url.pathname.match(/^\/drive\/v3\/files\/([^/]+)\/export$/);
		if (exp) return new Response(bodies[exp[1]!] ?? "", { status: 200 });
		const meta = url.pathname.match(/^\/drive\/v3\/files\/([^/]+)$/);
		if (meta) {
			const id = decodeURIComponent(meta[1]!);
			const n = all[id];
			if (!n) return new Response("missing", { status: 404 });
			if (url.searchParams.get("fields")!.includes("parents"))
				return Response.json({ id, mimeType: n.mimeType, parents: n.parents, trashed: n.trashed ?? false, driveId: n.driveId ?? "D1" });
			return Response.json({ id, name: `n-${id}`, mimeType: n.mimeType, modifiedTime: "2026-11-24T00:00:00Z", version: n.version ?? "1" });
		}
		return new Response("nope", { status: 404 });
	};
	return { drive, calls, all };
}

const f = (parent: string, extra: Partial<Node> = {}): Node => ({ mimeType: FOLDER, parents: [parent], ...extra });
const d = (parent: string): Node => ({ mimeType: DOC, parents: [parent] });

test("omitting folder keeps the existing discover contract and makes no metadata call", async () => {
	const t = tree({ a: d(ROOT) });
	const r = await runTool("discover", { scope: "ag-marketing" }, env, t.drive);
	assert.ok(r.ok);
	assert.deepEqual(Object.keys(r.result as object).sort(), ["complete", "files", "folderId", "readAt", "scope", "withheld"]);
	assert.equal(t.calls.length, 1);
});

test("a verified subfolder lists its own children, one to four levels down", async () => {
	const t = tree({ s1: f(ROOT), s2: f("s1"), s3: f("s2"), s4: f("s3"), leaf1: d("s1"), leaf4: d("s4") });
	const one = await runTool("discover", { scope: "ag-marketing", folder: "s1" }, env, t.drive);
	assert.ok(one.ok);
	assert.deepEqual((one.result as any).folder, { id: "s1", depth: 1 });
	assert.equal((one.result as any).folderId, ROOT, "folderId stays the registered scope root");
	assert.deepEqual((one.result as any).files.map((x: any) => x.id).sort(), ["leaf1", "s2"]);
	const four = await runTool("discover", { scope: "ag-marketing", folder: "s4" }, env, t.drive);
	assert.ok(four.ok);
	assert.deepEqual((four.result as any).folder, { id: "s4", depth: MAX_NESTED_DEPTH });
	assert.deepEqual((four.result as any).files.map((x: any) => x.id), ["leaf4"]);
});

test("nested reach fails closed: too deep, outside the root, shortcut, trashed, multi-parent, cross-drive, missing", async () => {
	const t = tree({
		s1: f(ROOT), s2: f("s1"), s3: f("s2"), s4: f("s3"), s5: f("s4"),
		elsewhere: f("other-root"),
		shortcut: f(ROOT, { mimeType: "application/vnd.google-apps.shortcut" }),
		bin: f(ROOT, { trashed: true }), underBin: f("bin"),
		twoParents: f(ROOT, { parents: [ROOT, "other-root"] }),
		otherDrive: f(ROOT, { driveId: "D2" }),
		doc: d(ROOT),
	});
	for (const folder of ["s5", "elsewhere", "shortcut", "bin", "underBin", "twoParents", "otherDrive", "doc", "missing"]) {
		const r = await runTool("discover", { scope: "ag-marketing", folder }, env, t.drive);
		assert.equal(r.ok, false, folder);
		assert.equal(r.status, 403, folder);
		assert.equal((r as any).detail, "not_in_scope", folder);
	}
});

test("a withheld subfolder or withheld ancestor is refused, and its contents never list", async () => {
	const t = tree({ hid: f(ROOT), below: f("hid"), secret: d("below") });
	const w = { ...env, WITHHELD_SOURCES: JSON.stringify(["hid"]) };
	for (const folder of ["hid", "below"]) {
		const r = await runTool("discover", { scope: "ag-marketing", folder }, w, t.drive);
		assert.equal(r.status, 403, folder);
		assert.doesNotMatch(JSON.stringify(r), /secret/);
	}
	const read = await runTool("read", { scope: "ag-marketing", id: "secret", folder: "below" }, w, t.drive);
	assert.equal(read.status, 403);
});

test("a nested document reads whole only through its verified folder", async () => {
	const t = tree({ s1: f(ROOT), s2: f("s1"), doc: d("s2") }, { doc: "nested body" });
	const ok = await runTool("read", { scope: "ag-marketing", id: "doc", folder: "s2" }, env, t.drive);
	assert.ok(ok.ok);
	assert.equal((ok.result as any).text, "nested body");
	assert.equal((ok.result as any).nextOffset, null);
	assert.deepEqual((ok.result as any).folder, { id: "s2", depth: 2 });
	const direct = await runTool("read", { scope: "ag-marketing", id: "doc" }, env, t.drive);
	assert.equal(direct.status, 403, "a nested file is not a direct child of the scope");
	const wrong = await runTool("read", { scope: "ag-marketing", id: "doc", folder: "s1" }, env, t.drive);
	assert.equal(wrong.status, 403, "the file must be a direct child of the named folder");
});

test("a folder moved out of scope during the read is refused", async () => {
	const t = tree({ s1: f(ROOT), doc: d("s1") }, { doc: "body" });
	let exported = false;
	const drive = async (p: string) => {
		const res = await t.drive(p);
		if (p.includes("/export")) {
			exported = true;
			t.all["s1"] = f("other-root");
		}
		return res;
	};
	const r = await runTool("read", { scope: "ag-marketing", id: "doc", folder: "s1" }, env, drive);
	assert.ok(exported);
	assert.equal(r.ok, false);
	assert.equal((r as any).detail, "left_scope");
});

test("folder never widens scope: denied scopes refuse before any Drive call, and ids are validated", async () => {
	const never = async () => { throw new Error("must not call Drive"); };
	const r = await runTool("discover", { scope: "ag-strong-ones", folder: "x" }, env, never, { kind: "person", email: "don@expertpartners.com" });
	assert.equal(r.status, 403);
	const cro = await runTool("discover", { scope: "ep-events", folder: "x" }, env, never, { kind: "department", id: "ep-cro" });
	assert.equal(cro.status, 403);
	for (const folder of ["../x", "a/b", "a'b"]) {
		const bad = await runTool("discover", { scope: "ag-marketing", folder }, env, never);
		assert.equal(bad.status, 400, folder);
	}
});

test("each nested home is reachable by its owning department, not only by leader prefix", () => {
	const homes: Record<string, string[]> = {
		"ep-cgo": ["ep-events", "hq-library-marketing"],
		"ep-ceo": ["ep-acn"],
		"ag-cgo": ["ag-strong-ones", "hq-library-marketing"],
		"ag-ceo": ["ag-case-studies"],
	};
	for (const [dept, scopes] of Object.entries(homes)) {
		const s = effectiveScopes(env.ALLOWED_SCOPES, { kind: "department", id: dept });
		for (const scope of scopes) assert.ok(s.includes(scope as any), `${dept} reaches ${scope}`);
	}
	for (const [dept, scope] of [["ep-cro", "ep-events"], ["ep-coo", "ep-acn"], ["ag-cro", "ag-strong-ones"], ["ep-cgo", "ag-strong-ones"], ["ag-cgo", "ep-events"]]) {
		assert.ok(!effectiveScopes(env.ALLOWED_SCOPES, { kind: "department", id: dept! }).includes(scope as any), `${dept} must not reach ${scope}`);
	}
});
