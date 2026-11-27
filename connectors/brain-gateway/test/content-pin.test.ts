import { withRoots } from "./roots.ts";
import { test } from "node:test";
import assert from "node:assert/strict";
import { BRAIN_FOLDERS, contentDigest } from "../src/brain.ts";
import { runTool } from "../src/tools.ts";

// Drive has served export bodies of different length under one unchanged file.version (a 519 character
// difference observed between pages of one Decision Log read). The content digest must catch that.
const env = { ALLOWED_SCOPES: "hq-core" };
const source = { id: "synthetic-log", name: "Synthetic log", version: "5533", mimeType: "application/vnd.google-apps.document", modifiedTime: "2026-11-27T00:00:00Z" };
const OLD = "alpha beta gamma delta ".repeat(4);
const NEW = OLD + "epsilon appended later ";

function lagDrive(bodies: string[]) {
	let exports = 0;
	const drive = async (path: string) => {
		const url = new URL(path, "https://drive.invalid");
		if (url.pathname === "/drive/v3/files") {
			assert.equal(url.searchParams.get("q"), `'${BRAIN_FOLDERS["hq-core"]}' in parents and trashed=false`);
			return Response.json({ files: [source] });
		}
		if (url.pathname.endsWith("/export")) return new Response(bodies[Math.min(exports++, bodies.length - 1)]);
		return Response.json(source);
	};
	return { drive: withRoots(drive), exports: () => exports };
}
const read = (drive: any, extra: object) => runTool("read", { scope: "hq-core", id: source.id, max_chars: 40, ...extra }, env, drive);

test("every page carries the SHA-256 of the exact assembled text", async () => {
	const { drive } = lagDrive([OLD]);
	const r: any = await read(drive, { offset: 0 });
	assert.equal(r.status, 200);
	assert.equal(r.result.contentSha256, await contentDigest(OLD));
	assert.match(r.result.contentSha256, /^[0-9a-f]{64}$/);
});

test("same version but different export text between pages is refused, not spliced", async () => {
	const { drive } = lagDrive([OLD, NEW]);
	const first: any = await read(drive, { offset: 0 });
	assert.equal(first.result.file.version, "5533");
	assert.equal(first.result.totalChars, OLD.length);
	const second: any = await read(drive, { offset: first.result.nextOffset, expect_version: "5533", expect_content: first.result.contentSha256 });
	assert.equal(second.ok, false);
	assert.equal(second.detail, "changed_during_read");
	assert.equal(second.status, 502);
	assert.doesNotMatch(JSON.stringify(second), /epsilon|alpha/);
});

test("version-only continuation still passes the drift through, which is why the client totalChars guard stays", async () => {
	const { drive } = lagDrive([OLD, NEW]);
	const first: any = await read(drive, { offset: 0 });
	const second: any = await read(drive, { offset: first.result.nextOffset, expect_version: "5533" });
	assert.equal(second.status, 200);
	assert.notEqual(second.result.totalChars, first.result.totalChars);
	assert.notEqual(second.result.contentSha256, first.result.contentSha256);
});

test("a stable body with both pins reads to terminal null and reassembles exactly", async () => {
	const { drive } = lagDrive([NEW]);
	let offset: number | null = 0;
	let joined = "";
	let pin: { expect_version?: string; expect_content?: string } = {};
	while (offset !== null) {
		const r: any = await read(drive, { offset, ...pin });
		assert.equal(r.status, 200);
		pin = { expect_version: r.result.file.version, expect_content: r.result.contentSha256 };
		assert.equal(r.result.totalChars, NEW.length);
		joined += r.result.text;
		offset = r.result.nextOffset;
	}
	assert.equal(joined, NEW);
	assert.equal(await contentDigest(joined), pin.expect_content);
});

test("restart from offset 0 after the refusal pins the new text", async () => {
	const { drive } = lagDrive([OLD, NEW, NEW, NEW, NEW]);
	const first: any = await read(drive, { offset: 0 });
	const refused: any = await read(drive, { offset: first.result.nextOffset, expect_version: "5533", expect_content: first.result.contentSha256 });
	assert.equal(refused.detail, "changed_during_read");
	const restart: any = await read(drive, { offset: 0 });
	assert.equal(restart.result.contentSha256, await contentDigest(NEW));
	const next: any = await read(drive, { offset: restart.result.nextOffset, expect_version: "5533", expect_content: restart.result.contentSha256 });
	assert.equal(next.status, 200);
});

test("expect_content must be a lowercase SHA-256 hex digest", async () => {
	const { drive, exports } = lagDrive([OLD]);
	for (const bad of ["abc", "G".repeat(64), "A".repeat(64)]) {
		const r = await read(drive, { offset: 0, expect_content: bad });
		assert.equal(r.status, 400);
	}
	assert.equal(exports(), 0);
});
