// One read-only tool registry serves both the MCP connector (/mcp) and the Hub HTTP endpoint (/api/tools).
// There are no write tools. Nothing here can create, edit, share, trash or delete anything.
import { z } from "zod";
import { effectiveScopes, mayReadException, pinnedReadFor, sha256Hex, type Principal } from "./access.ts";
import {
	BrainError,
	canonicalScope,
	type BrainScope,
	BRAIN_FOLDERS,
	createBrainReads,
	DEFAULT_PAGE_CHARS,
	parseWithheld,
	sheetCache,
	type DriveFetch,
	MAX_NESTED_DEPTH,
	MAX_PAGE_CHARS,
	DEFAULT_PAGE_ROWS,
	MAX_PAGE_ROWS,
	type RowRequest,
} from "./brain.ts";
import { driveFetch } from "./google.ts";
import { cursorKey, CURSOR_MAX_LENGTH, CURSOR_TTL_MS, openCursor, sealCursor } from "./cursor.ts";

export interface ToolEnv {
	GOOGLE_SA_KEY?: string;
	ALLOWED_SCOPES?: string;
	WITHHELD_SOURCES?: string;
	FILE_READ_EXCEPTIONS?: string;
	PINNED_FILE_READS?: string;
	/** Dedicated HMAC key for row-mode cursors, base64url of at least 32 random bytes. */
	ROW_CURSOR_KEY?: string;
}

export interface ToolDef {
	name: string;
	description: string;
	schema: z.ZodObject<any>;
	/** `scopes` is what the caller may read, already intersected with the deployed allowlist. */
	run: (args: any, reads: ReturnType<typeof createBrainReads>, scopes: BrainScope[]) => Promise<unknown>;
}

function inScope(scopes: BrainScope[], scope: string): BrainScope {
	scope = canonicalScope(scope);
	if (!scopes.includes(scope as BrainScope)) throw new BrainError("scope_not_allowed", `Scope "${scope}" is not available through this gateway.`);
	return scope as BrainScope;
}

const scope = z.string().describe('A brain scope key from list_scopes, for example "hq-core", "ep-core" or "ag-core".');
const folder = z
	.string()
	.regex(/^[\w-]+$/)
	.optional()
	.describe(`Optional subfolder id from discover. It must sit inside the scope, at most ${MAX_NESTED_DEPTH} levels down. Omit it for the scope's own folder.`);

export const TOOLS: ToolDef[] = [
	{
		name: "list_scopes",
		description: "List the Business Brain scopes this gateway can read, with each scope's Drive folder id.",
		schema: z.object({}),
		run: async (_a, _r, scopes) => ({ scopes: scopes.map((s) => ({ scope: s, folderId: BRAIN_FOLDERS[s] })) }),
	},
	{
		name: "discover",
		description:
			"List the current direct children of one brain scope, newest first, across every page. Optional query filters by file name. Folders are listed but only documents and spreadsheets can be read. Pass a listed subfolder id as folder to list inside it.",
		schema: z.object({ scope, query: z.string().max(200).optional().describe("Filter by file name containing this text."), folder }),
		run: async (a, r, scopes) => r.discover(inScope(scopes, a.scope), a.query, a.folder),
	},
	{
		name: "read",
		description:
			"Read one document that is currently a direct child of the scope, or of the subfolder given as folder (get its id from discover). The whole document is fetched and verified (same version before and after, still in scope) and returned in pages: pass nextOffset back as offset until it is null, and pass the first page's file.version as expect_version so a change between pages is refused. For a spreadsheet, read without sheet to list its tabs, then pass one exact tab title as sheet to read that whole tab with sheet row numbers. Tab pages end on whole rows. partialRow marks a single row longer than the page. Large tabs can instead be read in bounded native row pages: pass sheet with start_row (1 for a new read, or the row after a complete character-mode prefix) and optional max_rows, then pass each returned cursor back with the same sheet until next_row is null. Joining every row page's text in order, after any character-mode prefix, gives exactly the whole-tab text: interior empty rows are written once a later row proves them, and only the tab's final empty tail is left out (discarded_tail_rows). Scope and version are checked again on every page. A row that does not fit max_chars is refused, never truncated.",
		schema: z.object({
			scope,
			id: z.string().regex(/^[\w-]+$/).describe("A file id returned by discover for this scope."),
			offset: z.number().int().min(0).optional(),
			max_chars: z.number().int().min(1).max(MAX_PAGE_CHARS).optional().describe(`Page size, default ${DEFAULT_PAGE_CHARS}.`),
			folder,
			sheet: z.string().min(1).max(100).optional().describe("Spreadsheets only. One exact tab title from the tab list."),
			expect_version: z.string().regex(/^\d+$/).optional().describe("file.version from the first page. A later page refuses with changed_during_read if the document changed."),
			start_row: z.number().int().min(1).max(10_000_000).optional().describe("Row mode only, with sheet. First sheet row of a new row read. Not with offset or cursor."),
			max_rows: z.number().int().min(1).max(MAX_PAGE_ROWS).optional().describe(`Row mode only. Rows fetched per page, default ${DEFAULT_PAGE_ROWS}. A page may cover fewer rows to fit max_chars.`),
			cursor: z.string().min(1).max(CURSOR_MAX_LENGTH).optional().describe("Row mode only. The cursor from the previous row page, with the same sheet. Not with offset or start_row."),
		}),
		run: async (a, r, scopes) => r.read(inScope(scopes, a.scope), a.id, a.offset ?? 0, a.max_chars ?? DEFAULT_PAGE_CHARS, a.folder, a.sheet, a.expect_version),
	},
	{
		name: "decisions",
		description:
			"Read the complete current HQ Decision Log, verify it, and return every heading sharing the newest decision date. The archive is never consulted. To read the full log, use read on the Decision Log id in hq-core.",
		schema: z.object({}),
		run: async (_a, r, scopes) => {
			inScope(scopes, "hq-core");
			return r.decisions();
		},
	},
];

export type ToolResult = { ok: true; result: unknown; status: 200 } | { ok: false; error: string; status: number; detail?: string };

/**
 * Run one tool for a principal. When no principal is given the caller is treated as Allison, the leader
 * of all three brains. The Worker entry points always pass an explicit principal; the default exists only
 * so the pre-profile tests and local scripts keep working.
 */
export async function runTool(name: string, args: unknown, env: ToolEnv, drive?: DriveFetch, principal: Principal = { kind: "person", email: "allison@expertpartners.com" }): Promise<ToolResult> {
	const tool = TOOLS.find((t) => t.name === name);
	if (!tool) return { ok: false, error: `Unknown tool ${name}`, status: 404 };
	const parsed = tool.schema.safeParse(args ?? {});
	if (!parsed.success) return { ok: false, error: "Invalid arguments", status: 400, detail: parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ") };
	try {
		// Only a digest of policy configuration, never tokens or authorization results, enters the cache.
		sheetCache.policy(await sha256Hex(JSON.stringify([env.ALLOWED_SCOPES, env.WITHHELD_SOURCES, env.FILE_READ_EXCEPTIONS, env.PINNED_FILE_READS])));
		const reads = createBrainReads(drive ?? driveFetch(env.GOOGLE_SA_KEY), undefined, parseWithheld(env.WITHHELD_SOURCES));
		if (name === "read") {
			const a = parsed.data as ReadArgs;
			const rowMode = a.start_row !== undefined || a.max_rows !== undefined || a.cursor !== undefined;
			if (rowMode && (a.offset !== undefined || a.sheet === undefined || (a.cursor !== undefined && a.start_row !== undefined)))
				return { ok: false, error: "Invalid arguments", status: 400, detail: "Row mode needs sheet, and takes start_row or cursor, never offset." };
			const pin = pinnedReadFor(principal, a.scope, a.id, a.folder, env.PINNED_FILE_READS);
			if (pin) {
				if (a.sheet !== undefined) throw new BrainError("not_a_spreadsheet", "Only a spreadsheet takes a sheet.");
				return { ok: true, result: await reads.readPinned(a.scope, pin, a.offset ?? 0, a.max_chars ?? DEFAULT_PAGE_CHARS, a.expect_version), status: 200 };
			}
			const exception = mayReadException(env.ALLOWED_SCOPES, principal, a.scope, a.id, a.folder, env.FILE_READ_EXCEPTIONS);
			if (rowMode) return { ok: true, result: await rowPage(a, env, reads, principal, exception), status: 200 };
			if (exception) {
				const result = await reads.read("ag-personal-core", a.id, a.offset ?? 0, a.max_chars ?? DEFAULT_PAGE_CHARS, undefined, a.sheet, a.expect_version);
				if (!mayReadException(env.ALLOWED_SCOPES, principal, a.scope, a.id, a.folder, env.FILE_READ_EXCEPTIONS) || parseWithheld(env.WITHHELD_SOURCES).has(a.id))
					throw new BrainError("not_in_scope", "The file is not a readable document in this scope.");
				return { ok: true, result, status: 200 };
			}
		}
		const result = await tool.run(parsed.data, reads, effectiveScopes(env.ALLOWED_SCOPES, principal));
		if (name === "read") afterRead(parsed.data as ReadArgs, env, principal);
		return { ok: true, result, status: 200 };
	} catch (e) {
		if (name === "read") sheetCache.forget((parsed.data as { id: string }).id);
		// Never echo provider payloads, URLs, credentials or document text in errors.
		if (e instanceof BrainError) return { ok: false, error: e.message, status: errorStatus(e.code), detail: e.code };
		return { ok: false, error: "The complete current Drive source could not be verified. No fallback was used.", status: 502 };
	}
}

type ReadArgs = { scope: string; id: string; offset?: number; max_chars?: number; folder?: string; sheet?: string; expect_version?: string; start_row?: number; max_rows?: number; cursor?: string };

function errorStatus(code: string) {
	if (code === "scope_not_allowed" || code === "not_in_scope") return 403;
	if (code === "invalid_cursor" || code === "invalid_row_range" || code === "row_too_large") return 400;
	if (code === "cursor_unavailable") return 503;
	return 502;
}

/** Entitlement and withholding are proved again after the read, so a change during the read is refused. */
function afterRead(a: ReadArgs, env: ToolEnv, principal: Principal) {
	inScope(effectiveScopes(env.ALLOWED_SCOPES, principal), a.scope);
	const withheld = parseWithheld(env.WITHHELD_SOURCES);
	if (withheld.has(a.id) || (a.folder !== undefined && withheld.has(a.folder)))
		throw new BrainError("not_in_scope", "The file is not a readable document in this scope.");
}

async function rowPage(a: ReadArgs, env: ToolEnv, reads: ReturnType<typeof createBrainReads>, principal: Principal, exception: boolean) {
	const key = await cursorKey(env.ROW_CURSOR_KEY);
	const scope = exception ? ("ag-personal-core" as const) : inScope(effectiveScopes(env.ALLOWED_SCOPES, principal), a.scope);
	const folder = exception ? undefined : a.folder;
	const sheet = a.sheet!;
	const base = { count: a.max_rows ?? DEFAULT_PAGE_ROWS, maxChars: a.max_chars ?? DEFAULT_PAGE_CHARS };
	let req: RowRequest;
	if (a.cursor !== undefined) {
		const c = await openCursor(key, a.cursor, Date.now());
		if (c.scope !== a.scope || c.id !== a.id || c.sheet !== sheet || c.folder !== (a.folder ?? "") || (a.expect_version !== undefined && a.expect_version !== c.version))
			throw new BrainError("invalid_cursor", "The row cursor is invalid, expired or belongs to another read. Restart from start_row.");
		req = { ...base, start: c.next, pending: c.pending, emitted: c.emitted, header: true, grid: c.grid, version: c.version };
	} else {
		const start = a.start_row ?? 1;
		// A later start continues a complete character-mode prefix, which already holds the header and rows before it.
		req = { ...base, start, pending: 0, emitted: start > 1, header: start > 1, version: a.expect_version };
	}
	const { state, ...page } = await reads.readRows(scope, a.id, sheet, req, folder);
	if (exception) {
		if (!mayReadException(env.ALLOWED_SCOPES, principal, a.scope, a.id, a.folder, env.FILE_READ_EXCEPTIONS) || parseWithheld(env.WITHHELD_SOURCES).has(a.id))
			throw new BrainError("not_in_scope", "The file is not a readable document in this scope.");
	} else afterRead(a, env, principal);
	const cursor = state
		? await sealCursor(key, { scope: a.scope, id: a.id, sheet, folder: a.folder ?? "", version: page.file.version!, ...state, exp: Date.now() + CURSOR_TTL_MS })
		: null;
	return { ...page, cursor };
}
