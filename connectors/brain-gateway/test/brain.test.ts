import { test } from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync } from "node:crypto";
import {
	allowedScopes,
	assertScope,
	BrainError,
	BRAIN_FOLDERS,
	createBrainReads,
	CURRENT_DECISION_LOG,
	MAX_CHARS,
	newestDecisionHeadings,
} from "../src/brain.ts";
import { driveFetch, parseKey, signAssertion } from "../src/google.ts";
import { runTool, TOOLS } from "../src/tools.ts";

const DOC = "application/vnd.google-apps.document";
const SCOPES = "hq-core,ep-core,ag-core";

type F = { id: string; name: string; mimeType: string; modifiedTime: string; version: string };
const file = (id: string, extra: Partial<F> = {}): F => ({ id, name: `n-${id}`, mimeType: DOC, modifiedTime: "2026-11-20T00:00:00Z", version: "1", ...extra });

/** Fake Drive: folder listings, per-file versions and exports. Hooks let a test mutate state mid-read. */
function fakeDrive(opts: {
	pages?: F[][];
	bodies?: Record<string, string>;
	versions?: Record<string, string[]>;
	exportInit?: (id: string) => ResponseInit & { headers?: Record<string, string> };
	listingsAfterRead?: F[][];
}) {
	const calls: string[] = [];
	let listCalls = 0;
	const verIdx: Record<string, number> = {};
	const drive = async (path: string) => {
		calls.push(path);
		const url = new URL(path, "https://x");
		if (url.pathname === "/drive/v3/files" && url.searchParams.get("q")) {
			const token = url.searchParams.get("pageToken");
			const pages = opts.pages ?? [[]];
			const idx = token ? Number(token) : 0;
			listCalls++;
			// Listings after the first complete discovery use the post-read set, when given.
			const set = listCalls > pages.length && opts.listingsAfterRead ? opts.listingsAfterRead : pages;
			return new Response(JSON.stringify({ files: set[idx] ?? [], nextPageToken: idx + 1 < set.length ? String(idx + 1) : undefined }), { status: 200 });
		}
		const exp = url.pathname.match(/^\/drive\/v3\/files\/([^/]+)\/export$/);
		const media = url.pathname.match(/^\/drive\/v3\/files\/([^/]+)$/);
		if (exp || (media && url.searchParams.get("alt") === "media")) {
			const id = (exp ?? media)![1];
			const init = opts.exportInit?.(id) ?? {};
			return new Response(opts.bodies?.[id] ?? "", { status: 200, ...init });
		}
		if (media) {
			const id = media[1];
			const list = opts.versions?.[id] ?? ["1"];
			const i = verIdx[id] ?? 0;
			verIdx[id] = i + 1;
			return new Response(JSON.stringify(file(id, { version: list[Math.min(i, list.length - 1)] })), { status: 200 });
		}
		return new Response("nope", { status: 404 });
	};
	return { drive, calls };
}

test("only allowed scopes resolve, private scopes are refused", () => {
	assert.deepEqual(allowedScopes("hq-core, ep-core ,bogus"), ["hq-core", "ep-core"]);
	assert.deepEqual(allowedScopes(undefined), []);
	assert.equal(assertScope(SCOPES, "hq-core"), "hq-core");
	assert.throws(() => assertScope(SCOPES, "ep-private"), (e: any) => e instanceof BrainError && e.code === "scope_not_allowed");
	assert.throws(() => assertScope(SCOPES, "__proto__"), BrainError);
});

test("discover walks every page and returns complete", async () => {
	const { drive } = fakeDrive({ pages: [[file("a")], [file("b")], [file("c")]] });
	const r = await createBrainReads(drive).discover("hq-core");
	assert.deepEqual(r.files.map((f) => f.id), ["a", "b", "c"]);
	assert.equal(r.complete, true);
	assert.equal(r.folderId, BRAIN_FOLDERS["hq-core"]);
});

test("discover query is escaped into the Drive search", async () => {
	const { drive, calls } = fakeDrive({ pages: [[file("a")]] });
	await createBrainReads(drive).discover("hq-core", "O'Brien\\x");
	const q = new URL(calls[0], "https://x").searchParams.get("q")!;
	assert.match(q, /name contains 'O\\'Brien\\\\x'/);
});

test("incomplete discovery and repeated page tokens fail closed", async () => {
	const incomplete = async () => new Response(JSON.stringify({ files: [file("a")], incompleteSearch: true }), { status: 200 });
	await assert.rejects(createBrainReads(incomplete).discover("hq-core"), /incomplete/);
	const loop = async () => new Response(JSON.stringify({ files: [file("a")], nextPageToken: "same" }), { status: 200 });
	await assert.rejects(createBrainReads(loop).discover("hq-core"), /repeated/);
	const bad = async () => new Response(JSON.stringify({ files: [{ id: "a" }] }), { status: 200 });
	await assert.rejects(createBrainReads(bad).discover("hq-core"), /incomplete/);
});

test("read returns the whole verified document in pages", async () => {
	const text = "x".repeat(250);
	const { drive } = fakeDrive({ pages: [[file("d1")]], bodies: { d1: text } });
	const reads = createBrainReads(drive);
	const first = await reads.read("hq-core", "d1", 0, 100);
	assert.equal(first.totalChars, 250);
	assert.equal(first.text.length, 100);
	assert.equal(first.nextOffset, 100);
	const last = await reads.read("hq-core", "d1", 200, 100);
	assert.equal(last.text.length, 50);
	assert.equal(last.nextOffset, null);
});

test("read refuses files outside the scope, shortcuts and unreadable types", async () => {
	const { drive } = fakeDrive({ pages: [[file("sc", { mimeType: "application/vnd.google-apps.shortcut" }), file("pdf", { mimeType: "application/pdf" })]] });
	const reads = createBrainReads(drive);
	await assert.rejects(reads.read("hq-core", "other"), /not a readable document/);
	await assert.rejects(reads.read("hq-core", "sc"), /not a readable document/);
	await assert.rejects(reads.read("hq-core", "pdf"), /not a readable document/);
});

test("a document that changes during the read is rejected", async () => {
	const { drive } = fakeDrive({ pages: [[file("d1")]], bodies: { d1: "hello" }, versions: { d1: ["1", "2"] } });
	await assert.rejects(createBrainReads(drive).read("hq-core", "d1"), /changed during the read/);
});

test("a document that leaves the scope during the read is rejected", async () => {
	const { drive } = fakeDrive({ pages: [[file("d1")]], bodies: { d1: "hello" }, listingsAfterRead: [[]] });
	// First discovery sees d1, the membership recheck does not.
	let discoveries = 0;
	const wrapped = async (p: string) => {
		if (p.includes("in+parents") || p.includes("in%20parents") || new URL(p, "https://x").searchParams.get("q")) {
			discoveries++;
			if (discoveries >= 2) return new Response(JSON.stringify({ files: [] }), { status: 200 });
		}
		return drive(p);
	};
	await assert.rejects(createBrainReads(wrapped).read("hq-core", "d1"), /left the selected scope/);
});

test("partial, oversized, empty, envelope and invalid UTF-8 exports fail without fallback", async () => {
	const cases: Array<[string, ReturnType<typeof fakeDrive>, RegExp]> = [
		["partial", fakeDrive({ pages: [[file("d1")]], bodies: { d1: "x" }, exportInit: () => ({ headers: { "content-range": "bytes 0-0/9" } }) }), /complete document export/],
		["envelope", fakeDrive({ pages: [[file("d1")]], bodies: { d1: "x" }, exportInit: () => ({ headers: { "content-type": "application/json" } }) }), /not a JSON envelope/],
		["empty", fakeDrive({ pages: [[file("d1")]], bodies: { d1: "   " } }), /empty or exceeds/],
		["large", fakeDrive({ pages: [[file("d1")]], bodies: { d1: "y".repeat(MAX_CHARS + 1) } }), /exceeds the full-read limit/],
	];
	for (const [name, f, re] of cases) await assert.rejects(createBrainReads(f.drive).read("hq-core", "d1"), re, name);
	const bad = {
		drive: async (p: string) => {
			const u = new URL(p, "https://x");
			if (u.searchParams.get("q")) return new Response(JSON.stringify({ files: [file("d1")] }), { status: 200 });
			if (u.pathname.endsWith("/export")) return new Response(new Uint8Array([0xff, 0xfe, 0xfd]), { status: 200 });
			return new Response(JSON.stringify(file("d1")), { status: 200 });
		},
	};
	await assert.rejects(createBrainReads(bad.drive).read("hq-core", "d1"));
});

test("the largest allowed log (about 1.4M characters) reads whole and pages to the end", async () => {
	const big = "z".repeat(1_400_000);
	const { drive } = fakeDrive({ pages: [[file("d1")]], bodies: { d1: big } });
	const reads = createBrainReads(drive);
	let offset: number | null = 0;
	let total = 0;
	while (offset !== null) {
		const page = await reads.read("hq-core", "d1", offset, 200_000);
		total += page.text.length;
		offset = page.nextOffset;
	}
	assert.equal(total, 1_400_000);
});

test("newest decision headings scan the whole text, handle mixed order and same-day ties", () => {
	const text = [
		"2026-11-08. Act by default",
		"# November 20, 2026. Default action rule",
		"November 9, 2026. Older",
		"2026-11-20. Second decision the same day",
		"Plain paragraph that mentions November 21, 2026 mid sentence",
	].join("\n");
	const r = newestDecisionHeadings(text);
	assert.deepEqual(r.map((e) => e.date), ["2026-11-20", "2026-11-20"]);
	assert.throws(() => newestDecisionHeadings("no dated headings here"), /Authority is unverified/);
});

test("decisions reads the current log id from hq-core", async () => {
	const { drive } = fakeDrive({
		pages: [[file(CURRENT_DECISION_LOG)]],
		bodies: { [CURRENT_DECISION_LOG]: "2026-11-20. Newest\n2026-11-08. Older" },
	});
	const r = await createBrainReads(drive).decisions();
	assert.equal(r.newest.length, 1);
	assert.equal(r.authority, "current-log-only");
});

test("tool registry is read-only and exposes exactly four tools", () => {
	assert.deepEqual(TOOLS.map((t) => t.name).sort(), ["decisions", "discover", "list_scopes", "read"]);
	assert.ok(!TOOLS.some((t) => /write|create|update|delete|share|trash|save/i.test(t.name)));
});

test("runTool enforces scope, validates arguments and hides provider detail", async () => {
	const env = { ALLOWED_SCOPES: SCOPES };
	const { drive } = fakeDrive({ pages: [[file("d1")]], bodies: { d1: "hi" } });
	const ok = await runTool("list_scopes", {}, env, drive);
	assert.ok(ok.ok && (ok.result as any).scopes.length === 3);
	const priv = await runTool("discover", { scope: "ep-private" }, env, drive);
	assert.equal(priv.ok, false);
	assert.equal(priv.status, 403);
	const badArgs = await runTool("read", { scope: "hq-core", id: "../etc/passwd" }, env, drive);
	assert.equal(badArgs.status, 400);
	const unknown = await runTool("save_file", {}, env, drive);
	assert.equal(unknown.status, 404);
	const boom = await runTool("discover", { scope: "hq-core" }, env, async () => {
		throw new Error("secret-token-abc https://internal");
	});
	assert.equal(boom.ok, false);
	assert.doesNotMatch(JSON.stringify(boom), /secret-token|internal/);
	const readOk = await runTool("read", { scope: "hq-core", id: "d1" }, env, drive);
	assert.ok(readOk.ok);
	const dec = await runTool("decisions", {}, { ALLOWED_SCOPES: "ep-core" }, drive);
	assert.equal(dec.status, 403);
});

test("the Drive client only reaches GET on the Drive v3 files API", async () => {
	const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
	const key = JSON.stringify({ client_email: "sa@example.iam.gserviceaccount.com", private_key: privateKey.export({ type: "pkcs8", format: "pem" }).toString() });
	const seen: Array<{ url: string; method?: string }> = [];
	const fetchImpl = (async (url: string, init?: RequestInit) => {
		seen.push({ url, method: init?.method });
		if (url.includes("oauth2.googleapis.com")) return new Response(JSON.stringify({ access_token: "t", expires_in: 3600 }), { status: 200 });
		return new Response("{}", { status: 200 });
	}) as typeof fetch;
	const drive = driveFetch(key, fetchImpl);
	await drive("/drive/v3/files?q=x");
	await assert.rejects(drive("/drive/v3/about"), /Only the Drive v3 files API/);
	await assert.rejects(drive("/gmail/v1/users/me/messages"), /Only the Drive v3 files API/);
	assert.ok(seen.filter((s) => s.url.includes("googleapis.com/drive")).every((s) => s.method === "GET"));
});

test("the service account assertion asks only for drive.readonly", async () => {
	const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
	const k = parseKey(JSON.stringify({ client_email: "sa@x", private_key: privateKey.export({ type: "pkcs8", format: "pem" }).toString() }));
	const jwt = await signAssertion(k, 1_000_000);
	const [, claims] = jwt.split(".");
	const body = JSON.parse(Buffer.from(claims, "base64url").toString());
	assert.equal(body.scope, "https://www.googleapis.com/auth/drive.readonly");
	assert.equal(body.iss, "sa@x");
	assert.equal(body.sub, undefined, "no delegated subject, so no domain-wide delegation");
	assert.throws(() => parseKey(undefined), /not set/);
	assert.throws(() => parseKey("{}"), /not a service account key/);
});
