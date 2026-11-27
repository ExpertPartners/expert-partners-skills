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
} from "./brain.ts";
import { driveFetch } from "./google.ts";

export interface ToolEnv {
	GOOGLE_SA_KEY?: string;
	ALLOWED_SCOPES?: string;
	WITHHELD_SOURCES?: string;
	FILE_READ_EXCEPTIONS?: string;
	PINNED_FILE_READS?: string;
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
			"Read one document that is currently a direct child of the scope, or of the subfolder given as folder (get its id from discover). The whole document is fetched and verified (same version before and after, still in scope) and returned in pages: pass nextOffset back as offset until it is null, and pass the first page's file.version as expect_version so a change between pages is refused. For a spreadsheet, read without sheet to list its tabs, then pass one exact tab title as sheet to read that whole tab with sheet row numbers. Tab pages end on whole rows. partialRow marks a single row longer than the page.",
		schema: z.object({
			scope,
			id: z.string().regex(/^[\w-]+$/).describe("A file id returned by discover for this scope."),
			offset: z.number().int().min(0).optional(),
			max_chars: z.number().int().min(1).max(MAX_PAGE_CHARS).optional().describe(`Page size, default ${DEFAULT_PAGE_CHARS}.`),
			folder,
			sheet: z.string().min(1).max(100).optional().describe("Spreadsheets only. One exact tab title from the tab list."),
			expect_version: z.string().regex(/^\d+$/).optional().describe("file.version from the first page. A later page refuses with changed_during_read if the document changed."),
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
			const a = parsed.data as { scope: string; id: string; offset?: number; max_chars?: number; folder?: string; sheet?: string; expect_version?: string };
			const pin = pinnedReadFor(principal, a.scope, a.id, a.folder, env.PINNED_FILE_READS);
			if (pin) {
				if (a.sheet !== undefined) throw new BrainError("not_a_spreadsheet", "Only a spreadsheet takes a sheet.");
				return { ok: true, result: await reads.readPinned(a.scope, pin, a.offset ?? 0, a.max_chars ?? DEFAULT_PAGE_CHARS, a.expect_version), status: 200 };
			}
			if (mayReadException(env.ALLOWED_SCOPES, principal, a.scope, a.id, a.folder, env.FILE_READ_EXCEPTIONS)) {
				const result = await reads.read("ag-personal-core", a.id, a.offset ?? 0, a.max_chars ?? DEFAULT_PAGE_CHARS, undefined, a.sheet, a.expect_version);
				if (!mayReadException(env.ALLOWED_SCOPES, principal, a.scope, a.id, a.folder, env.FILE_READ_EXCEPTIONS) || parseWithheld(env.WITHHELD_SOURCES).has(a.id))
					throw new BrainError("not_in_scope", "The file is not a readable document in this scope.");
				return { ok: true, result, status: 200 };
			}
		}
		const result = await tool.run(parsed.data, reads, effectiveScopes(env.ALLOWED_SCOPES, principal));
		if (name === "read") {
			const a = parsed.data as { scope: string; id: string; folder?: string };
			inScope(effectiveScopes(env.ALLOWED_SCOPES, principal), a.scope);
			const withheld = parseWithheld(env.WITHHELD_SOURCES);
			if (withheld.has(a.id) || (a.folder !== undefined && withheld.has(a.folder)))
				throw new BrainError("not_in_scope", "The file is not a readable document in this scope.");
		}
		return { ok: true, result, status: 200 };
	} catch (e) {
		if (name === "read") sheetCache.forget((parsed.data as { id: string }).id);
		// Never echo provider payloads, URLs, credentials or document text in errors.
		if (e instanceof BrainError) return { ok: false, error: e.message, status: e.code === "scope_not_allowed" || e.code === "not_in_scope" ? 403 : 502, detail: e.code };
		return { ok: false, error: "The complete current Drive source could not be verified. No fallback was used.", status: 502 };
	}
}
