// Read-only Business Brain reads. Ported from the Hub reader contract (expert-partners-hub
// src/lib/business-brain.server.ts): scope map, direct-child discovery, membership and version checks
// around every export, complete reads only, no cache and no stored copy of any document.

// Routing metadata only. The live Departments, Workspaces and Brain Folders map owns scope.
export const BRAIN_FOLDERS = {
	"hq-core": "1Za4sU2YQ3UP2E-ujxVNtvH-2sQ-zndjw",
	"hq-hr": "1t3Lr7CezMDnZY1M0ctZPw8U7ea9i0TaY",
	"hq-employees": "19hYKhOLuAFmhdzkAkSQE2zlqydB74NL1",
	"hq-skills": "1PO-DnL5z3v2W_gPkyu7btZmd8yxEUi-w",
	"hq-finance": "1Nw46FjauvrOILS1-mE8rkxVaS5jqRXaF",
	"hq-operations": "1hmbZa0J-9wF-xAEPyaj9PSh97vr9zFyk",
	"hq-audits": "1YTZ3MD7mQKH8fpswJsYvM0p59u491bBA",
	"hq-outputs": "1ABDlp7H_zvG2PO_XAhPej8Sf6y1YBCJ_",
	"hq-analytics": "1Yp9EEiJENMvztLNWTxVWJ1TdntFaDs2d",
	"hq-partnersync": "1N4bLj6BlDjdn_UCE7YWiUd-RTUAAgJqj",
	"hq-library": "1YADuyGnPhDHoLcJHV873QoipltoNtBwE",
	"ep-core": "1IhLDYB5YBCE_2ea9EHN5enxm8nefxbLm",
	"ep-discovery": "1k2Rnz5i4VesUVDIYhJgJcTn_VcB4M9AH",
	"ep-marketing": "1JYwT0hn96Q4w3eDKtmd3QAWyeLwDQIeI",
	"ep-sales": "1ZtDDguWRQXsSlyI1hEGbYeUNLnzGue4m",
	"ep-client-experience": "11rF1ooU9Ub2j2-czoF0U7T25zR9wYsEa",
	"ep-operations": "1XOWZgfhoFiTK8g29prsmUSv1ahJrqXST",
	"ep-outputs": "1LI5FS-N-CPiyngTvV6vgRoS6LpcoYF01",
	"ep-private": "1f8N4r14ENZZh5hi3TVF_zaChIZulXBvb",
	"ag-core": "1s9602UPWf6aCfSK1zAR6EdTI5XEQD1OO",
	"ag-marketing": "1DhRqS1OU-PKnaQTOoy1qqjY6KNJI-tf1",
	"ag-sales": "1igSMH0uwHkJ6FfXDZiUxCNfo2zARPe5B",
	"ag-listings": "18KuyOhUKwHkSHdWElXgDsOQnyid77Hx9",
	"ag-client-experience": "1o6B9Zb9rmWQncVfZabDgsBGpoEKPFurj",
	"ag-operations": "1NXOwo8Cq5Jb7MTsnzZ5XNRkbybi89RV1",
	"ag-outputs": "14MfoyCMP2011nGdhf2VowNfpCk8Mh1Hh",
	"ag-private": "1jvcBly_KLDJnyTKFADtPjVTSWxfGLL8A",
	// Workspace and shelf homes that sit inside another department folder.
	"hq-library-marketing": "1bjwhy6jGjUZBDHtbdXsKRM_q04GTy7PO",
	"ep-events": "1AVq7ONpjLZxrtppVd5qEussIEPnjZuua",
	"ep-acn": "1-OlQOuM1rVQkG8cyAGxTym_O7S4ySnoK",
	"ag-strong-ones": "1QK-anvUQ7wYyperKEMs5SpsjIdyUPeZT",
	"ag-case-studies": "1bBsS9eFbM3iNvwhpVLrkkNBsphn4VkxN",
} as const;
export type BrainScope = keyof typeof BRAIN_FOLDERS;
export const CURRENT_DECISION_LOG = "1ausL1HV3ns3VMZH86jD8zjWnAKSQ3DaUfFzkiwR1qWc";
export const DECISION_LOG_SCOPE: BrainScope = "hq-core";
export const MAX_CHARS = 2_000_000;
export const DEFAULT_PAGE_CHARS = 60_000;
export const MAX_PAGE_CHARS = 200_000;
/** Subfolders below a scope root are reachable this many levels down, no further. */
export const MAX_NESTED_DEPTH = 4;
const FOLDER_MIME = "application/vnd.google-apps.folder";
const REGISTERED_ROOTS: ReadonlySet<string> = new Set(Object.values(BRAIN_FOLDERS));

export const READABLE_MIME = ["application/vnd.google-apps.document", "text/plain", "text/markdown"];

/** Only scopes named in the ALLOWED_SCOPES var are reachable. Everything else is refused. */
export function allowedScopes(list: string | undefined): BrainScope[] {
	if (!list) return [];
	return list
		.split(",")
		.map((s) => s.trim())
		.filter((s): s is BrainScope => Object.prototype.hasOwnProperty.call(BRAIN_FOLDERS, s));
}

/** Legacy EP client key resolves before authorization, so it never widens access. */
export function canonicalScope(scope: string): string {
	return scope === "ep-client" ? "ep-client-experience" : scope;
}

export function assertScope(list: string | undefined, scope: string): BrainScope {
	scope = canonicalScope(scope);
	if (!allowedScopes(list).includes(scope as BrainScope)) {
		throw new BrainError("scope_not_allowed", `Scope "${scope}" is not available through this gateway.`);
	}
	return scope as BrainScope;
}

export class BrainError extends Error {
	code: string;
	constructor(code: string, message: string) {
		super(message);
		this.code = code;
	}
}

export type DriveFetch = (path: string) => Promise<Response>;

export type BrainFile = {
	id: string;
	name: string;
	mimeType: string;
	modifiedTime: string;
	version?: string;
};

const MONTHS = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December",
];

// Scan all dated headings, not a fixed offset, tail, modified date or assumed document order.
// Entries sharing the newest date are all returned. Their order does not establish authority.
export function newestDecisionHeadings(text: string) {
	const entries: { date: string; heading: string }[] = [];
	for (const line of text.split(/\r?\n/)) {
		const heading = line.replace(/^#{1,6}\s+/, "").trim();
		const match = heading.match(
			/^(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (20\d{2})(?:\.|:|\s[-–])\s*\S/i,
		);
		const iso = heading.match(/^(20\d{2})-(\d{2})-(\d{2})(?:\.|:|,|\s[-–])\s*\S/);
		if (!match && !iso) continue;
		const month = match ? MONTHS.findIndex((n) => n.toLowerCase() === match[1]!.toLowerCase()) : Number(iso![2]) - 1;
		const day = Number(match ? match[2] : iso![3]);
		const year = Number(match ? match[3] : iso![1]);
		const date = new Date(Date.UTC(year, month, day));
		if (date.getUTCMonth() !== month || date.getUTCDate() !== day) continue;
		entries.push({ date: date.toISOString().slice(0, 10), heading });
	}
	if (!entries.length) throw new BrainError("no_headings", "No dated decision headings were found. Authority is unverified.");
	const newest = entries.reduce((a, b) => (a.date > b.date ? a : b)).date;
	return entries.filter((e) => e.date === newest);
}

async function fullText(response: Response): Promise<string> {
	if (response.status !== 200 || response.headers.has("content-range"))
		throw new BrainError("incomplete_export", "Drive did not return a complete document export.");
	if (!response.body) throw new BrainError("incomplete_export", "Drive returned no document body.");
	const reader = response.body.getReader();
	const decoder = new TextDecoder("utf-8", { fatal: true, ignoreBOM: false });
	let text = "";
	try {
		while (true) {
			const next = await reader.read();
			if (next.done) break;
			text += decoder.decode(next.value, { stream: true });
			if (text.length > MAX_CHARS) throw new BrainError("too_large", "Document exceeds the full-read limit. Nothing is authoritative.");
		}
		text += decoder.decode();
		if (!text.trim() || text.length > MAX_CHARS) throw new BrainError("too_large", "Document is empty or exceeds the full-read limit.");
		if (/json/i.test(response.headers.get("content-type") ?? ""))
			throw new BrainError("envelope", "Expected a full plain-text Drive export, not a JSON envelope.");
		return text;
	} finally {
		await reader.cancel().catch(() => {});
		reader.releaseLock();
	}
}

export async function fileVersion(drive: DriveFetch, id: string): Promise<BrainFile> {
	const params = new URLSearchParams({ fields: "id,name,mimeType,modifiedTime,version", supportsAllDrives: "true" });
	const res = await drive(`/drive/v3/files/${encodeURIComponent(id)}?${params}`);
	if (!res.ok) throw new BrainError("drive_error", `Drive file lookup answered ${res.status}.`);
	const file = (await res.json()) as BrainFile;
	if (!file.id || !file.version) throw new BrainError("drive_error", "Drive returned no file version.");
	return file;
}

function escapeQuery(s: string) {
	return s.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

/**
 * Files withheld from every scope, from the WITHHELD_SOURCES secret: a JSON array of Drive file ids.
 * Ids stay out of this public repository. A historical source that still sits in an approved folder is
 * neither listed nor readable, so its title cannot surface. A malformed value refuses every read
 * instead of silently withholding nothing.
 */
export function parseWithheld(json: string | undefined): ReadonlySet<string> {
	if (json === undefined || json.trim() === "") return new Set();
	let ids: unknown;
	try {
		ids = JSON.parse(json);
	} catch {
		throw new BrainError("withheld_invalid", "The withheld source list is unreadable. No source was served.");
	}
	if (!Array.isArray(ids) || ids.some((id) => typeof id !== "string" || !/^[\w-]+$/.test(id)))
		throw new BrainError("withheld_invalid", "The withheld source list is malformed. No source was served.");
	return new Set(ids as string[]);
}

export function createBrainReads(drive: DriveFetch, now = () => new Date(), withheld: ReadonlySet<string> = new Set()) {
	type FolderMeta = { id?: string; mimeType?: string; parents?: string[]; trashed?: boolean; driveId?: string };
	async function folderMeta(id: string): Promise<FolderMeta> {
		const params = new URLSearchParams({ fields: "id,mimeType,parents,trashed,driveId", supportsAllDrives: "true" });
		const res = await drive(`/drive/v3/files/${encodeURIComponent(id)}?${params}`);
		if (res.status === 404) throw new BrainError("not_in_scope", "The folder is not inside this scope.");
		if (!res.ok) throw new BrainError("drive_error", `Drive folder lookup answered ${res.status}.`);
		return (await res.json()) as FolderMeta;
	}

	/**
	 * Proves a subfolder sits under the scope root by walking its parents upward, at most MAX_NESTED_DEPTH
	 * hops. Every hop must be one real folder (not a shortcut), untrashed, not withheld, with exactly one
	 * parent, in the same shared drive as the root. Anything else is refused rather than guessed.
	 */
	async function nestedFolder(scope: BrainScope, folder: string) {
		const root = BRAIN_FOLDERS[scope];
		if (folder === root) return { id: root, depth: 0 };
		if (withheld.has(folder)) throw new BrainError("not_in_scope", "The folder is not inside this scope.");
		const rootMeta = await folderMeta(root);
		let id = folder;
		for (let depth = 1; depth <= MAX_NESTED_DEPTH; depth++) {
			// Another scope's registered root is reachable only through its own scope key, where its department check runs.
			if (REGISTERED_ROOTS.has(id)) throw new BrainError("not_in_scope", "The folder is not inside this scope.");
			const meta = await folderMeta(id);
			if (meta.id !== id || meta.mimeType !== FOLDER_MIME || meta.trashed !== false || withheld.has(id))
				throw new BrainError("not_in_scope", "The folder is not inside this scope.");
			if (!Array.isArray(meta.parents) || meta.parents.length !== 1 || meta.driveId !== rootMeta.driveId)
				throw new BrainError("not_in_scope", "The folder is not inside this scope.");
			const parent = meta.parents[0]!;
			if (parent === root) return { id: folder, depth: depth };
			if (withheld.has(parent)) throw new BrainError("not_in_scope", "The folder is not inside this scope.");
			id = parent;
		}
		throw new BrainError("not_in_scope", `The folder is more than ${MAX_NESTED_DEPTH} levels below this scope.`);
	}

	async function discover(scope: BrainScope, query?: string, folder?: string) {
		const nested = folder === undefined ? undefined : await nestedFolder(scope, folder);
		const parentId = nested?.id ?? BRAIN_FOLDERS[scope];
		const files: BrainFile[] = [];
		const seen = new Set<string>();
		let pageToken = "";
		do {
			const q =
				`'${parentId}' in parents and trashed=false` +
				(query ? ` and name contains '${escapeQuery(query)}'` : "");
			const params = new URLSearchParams({
				q,
				orderBy: "modifiedTime desc",
				pageSize: "100",
				fields: "nextPageToken,incompleteSearch,files(id,name,mimeType,modifiedTime,version)",
				supportsAllDrives: "true",
				includeItemsFromAllDrives: "true",
				...(pageToken ? { pageToken } : {}),
			});
			const res = await drive(`/drive/v3/files?${params}`);
			if (!res.ok) throw new BrainError("drive_error", `Drive discovery answered ${res.status}.`);
			const body = (await res.json()) as { files?: BrainFile[]; nextPageToken?: string; incompleteSearch?: boolean };
			if (!Array.isArray(body.files) || body.incompleteSearch) throw new BrainError("incomplete_discovery", "Drive discovery was incomplete.");
			if (body.files.some((f) => !f.id || !f.name || !f.mimeType || !f.modifiedTime))
				throw new BrainError("incomplete_discovery", "Drive discovery returned incomplete file metadata.");
			files.push(...body.files);
			pageToken = body.nextPageToken ?? "";
			if (pageToken && seen.has(pageToken)) throw new BrainError("incomplete_discovery", "Drive repeated a discovery page.");
			seen.add(pageToken);
		} while (pageToken);
		const listed = files.filter((f) => !withheld.has(f.id));
		return {
			scope,
			folderId: BRAIN_FOLDERS[scope],
			...(nested ? { folder: nested } : {}),
			files: listed,
			complete: true,
			withheld: files.length - listed.length,
			readAt: now().toISOString(),
		};
	}

	/** One cheap request: the scope's registered folder answers and lists. Used by the daily check, which has a request budget. */
	async function probe(scope: BrainScope) {
		const params = new URLSearchParams({
			q: `'${BRAIN_FOLDERS[scope]}' in parents and trashed=false`,
			pageSize: "1",
			fields: "incompleteSearch,files(id)",
			supportsAllDrives: "true",
			includeItemsFromAllDrives: "true",
		});
		const res = await drive(`/drive/v3/files?${params}`);
		if (!res.ok) throw new BrainError("drive_error", `Drive probe answered ${res.status}.`);
		const body = (await res.json()) as { files?: unknown[]; incompleteSearch?: boolean };
		if (!Array.isArray(body.files) || body.incompleteSearch) throw new BrainError("incomplete_discovery", "Drive probe was incomplete.");
		return { scope, folderId: BRAIN_FOLDERS[scope], reachable: true };
	}

	/** Reads one whole document. Verifies direct membership in scope before and after, and that the version did not change. */
	async function readWhole(scope: BrainScope, id: string, folder?: string) {
		if (withheld.has(id)) throw new BrainError("not_in_scope", "The file is not a readable document in this scope.");
		const inventory = await discover(scope, undefined, folder);
		const found = inventory.files.find((f) => f.id === id);
		if (!found || !READABLE_MIME.includes(found.mimeType))
			throw new BrainError("not_in_scope", "The file is not a readable document in this scope.");
		const before = await fileVersion(drive, id);
		const res = await drive(
			`/drive/v3/files/${encodeURIComponent(id)}${
				found.mimeType === "application/vnd.google-apps.document" ? "/export?mimeType=text/plain&supportsAllDrives=true" : "?alt=media&supportsAllDrives=true"
			}`,
		);
		const text = await fullText(res);
		const after = await fileVersion(drive, id);
		if (after.version !== before.version) throw new BrainError("changed_during_read", "Document changed during the read. Read again.");
		// Rechecks the whole parent chain too, so a folder moved out of scope mid-read is refused.
		const membership = await discover(scope, undefined, folder).catch((e) => {
			if (e instanceof BrainError && e.code === "not_in_scope") throw new BrainError("left_scope", "Document left the selected scope during the read.");
			throw e;
		});
		if (!membership.files.some((f) => f.id === id)) throw new BrainError("left_scope", "Document left the selected scope during the read.");
		return { file: before, text, readAt: now().toISOString(), folder: inventory.folder };
	}

	/** Whole document verified, returned in pages so large documents fit an MCP reply. */
	async function read(scope: BrainScope, id: string, offset = 0, maxChars = DEFAULT_PAGE_CHARS, folder?: string) {
		const { file, text, readAt, folder: nested } = await readWhole(scope, id, folder);
		const size = Math.min(Math.max(1, maxChars), MAX_PAGE_CHARS);
		const start = Math.min(Math.max(0, offset), text.length);
		const end = Math.min(text.length, start + size);
		return {
			file,
			scope,
			...(nested ? { folder: nested } : {}),
			readAt,
			totalChars: text.length,
			offset: start,
			nextOffset: end < text.length ? end : null,
			text: text.slice(start, end),
		};
	}

	async function decisions() {
		const { file, text, readAt } = await readWhole(DECISION_LOG_SCOPE, CURRENT_DECISION_LOG);
		return {
			file,
			readAt,
			totalChars: text.length,
			authority: "current-log-only",
			newest: newestDecisionHeadings(text),
			sourceUrl: `https://docs.google.com/document/d/${CURRENT_DECISION_LOG}/edit`,
		};
	}

	return { discover, probe, read, decisions };
}
