import { test } from "node:test";
import assert from "node:assert/strict";
import { BRAIN_FOLDERS, BrainError, createBrainReads, type DriveFetch } from "../src/brain.ts";
import { runDeepCheck } from "../src/health.ts";
import { runTool } from "../src/tools.ts";
import { withRoots } from "./roots.ts";

const ROOT = BRAIN_FOLDERS["ep-core"];
const FOLDER = "application/vnd.google-apps.folder";
const ENV = { ALLOWED_SCOPES: "ep-core" };
const unreadable = (e: unknown) => e instanceof BrainError && e.code === "folder_unreadable";

/** An invisible root could list as empty successfully. Any listing here is a regression. */
function deniedRoot(status: number) {
	const calls: string[] = [];
	const drive: DriveFetch = async (path) => {
		calls.push(path);
		const url = new URL(path, "https://drive.invalid");
		assert.equal(url.pathname, `/drive/v3/files/${ROOT}`);
		assert.equal(url.searchParams.get("fields"), "id,mimeType,trashed,driveId");
		assert.equal(url.searchParams.get("supportsAllDrives"), "true");
		return new Response("provider detail must not leak", { status });
	};
	return { calls, drive };
}

for (const status of [403, 404]) {
	test(`discover refuses a ${status} root before listing, including through runTool`, async () => {
		const { drive, calls } = deniedRoot(status);
		await assert.rejects(createBrainReads(drive).discover("ep-core"), unreadable);
		assert.equal(calls.length, 1);
		const result = await runTool("discover", { scope: "ep-core" }, ENV, drive);
		assert.equal(result.ok, false);
		assert.equal(result.status, 502);
		if (result.ok) assert.fail("an unreadable root cannot return a discovery result");
		assert.equal(result.detail, "folder_unreadable");
		assert.equal("result" in result, false, "no empty files array may masquerade as a successful listing");
		assert.doesNotMatch(JSON.stringify(result), /"files"|provider detail/);
		assert.equal(calls.length, 2, "each attempt stops after its root GET");
	});

	test(`read refuses a ${status} scope root before listing or exporting a file`, async () => {
		const { drive, calls } = deniedRoot(status);
		await assert.rejects(createBrainReads(drive).read("ep-core", "document"), unreadable);
		const result = await runTool("read", { scope: "ep-core", id: "document" }, ENV, drive);
		assert.equal(result.ok, false);
		if (result.ok) assert.fail("an unreadable root cannot return document text");
		assert.equal(result.detail, "folder_unreadable");
		assert.equal(result.status, 502);
		assert.equal("result" in result, false);
		assert.equal(calls.length, 2);
	});
}

test("a healthy empty root returns a complete empty listing after one preflight", async () => {
	const calls: string[] = [];
	const drive = withRoots(async (path) => {
		calls.push(path);
		const url = new URL(path, "https://drive.invalid");
		assert.equal(url.pathname, "/drive/v3/files");
		assert.equal(url.searchParams.get("q"), `'${ROOT}' in parents and trashed=false`);
		return Response.json({ files: [] });
	}, { calls });
	const result = await createBrainReads(drive).discover("ep-core");
	assert.equal(result.complete, true);
	assert.deepEqual(result.files, []);
	assert.equal(calls.length, 2);
	assert.equal(new URL(calls[0]!, "https://drive.invalid").pathname, `/drive/v3/files/${ROOT}`);
});

for (const [name, override] of [
	["trashed", { trashed: true }],
	["wrong MIME type", { mimeType: "application/vnd.google-apps.document" }],
	["wrong id", { id: "other-root" }],
	["missing trashed flag", { trashed: undefined }],
] as const) {
	test(`a root with ${name} is unreadable and never lists children`, async () => {
		let calls = 0;
		const drive: DriveFetch = async (path) => {
			calls++;
			assert.equal(new URL(path, "https://drive.invalid").pathname, `/drive/v3/files/${ROOT}`);
			return Response.json({ id: ROOT, mimeType: FOLDER, trashed: false, driveId: "D1", ...override });
		};
		await assert.rejects(createBrainReads(drive).discover("ep-core"), unreadable);
		assert.equal(calls, 1);
	});
}

test("probe refuses an unreadable root and a healthy probe uses exactly one root GET", async () => {
	const bad = deniedRoot(404);
	await assert.rejects(createBrainReads(bad.drive).probe("ep-core"), unreadable);
	assert.equal(bad.calls.length, 1);
	const calls: string[] = [];
	const healthy = withRoots(async () => {
		assert.fail("probe must not list children or fetch other metadata");
	}, { calls });
	assert.deepEqual(await createBrainReads(healthy).probe("ep-core"), { scope: "ep-core", folderId: ROOT, reachable: true });
	assert.equal(calls.length, 1);
	const url = new URL(calls[0]!, "https://drive.invalid");
	assert.equal(url.pathname, `/drive/v3/files/${ROOT}`);
	assert.equal(url.searchParams.get("fields"), "id,mimeType,trashed,driveId");
});

test("non-access root failures remain drive_error rather than unreadable or empty", async () => {
	const { drive, calls } = deniedRoot(503);
	await assert.rejects(createBrainReads(drive).discover("ep-core"), (e: unknown) => e instanceof BrainError && e.code === "drive_error");
	assert.equal(calls.length, 1);
});

test("deep health check marks an unreadable scope as failed in full-listing and probe rotations", async () => {
	for (const date of ["2026-11-21T18:00:00Z", "2026-11-22T18:00:00Z"]) {
		const denied = deniedRoot(404);
		const fallback = withRoots(async () => Response.json({ files: [] }));
		const drive: DriveFetch = (path) => new URL(path, "https://drive.invalid").pathname === `/drive/v3/files/${ROOT}` ? denied.drive(path) : fallback(path);
		const health = await runDeepCheck("hq-core,ep-core", drive, () => new Date(date));
		assert.equal(health.ok, false);
		assert.deepEqual(health.checks.find((check) => check.name === "scope ep-core"), {
			name: "scope ep-core", ok: false, detail: "failed (folder_unreadable)",
		});
		assert.equal(denied.calls.length, 1);
	}
});
