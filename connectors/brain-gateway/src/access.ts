// Who may read which scopes. Enforced here, in the gateway, because instructions and folder maps
// do not create Drive permissions (Decision Log, Nov 20 2026, Business Brain department access).
//
// Approved basis (Decision Log Nov 20 2026):
// - Leader-level access, whole brain: Allison and Don for Expert Partners and HQ, Allison alone for AG Luxury.
// - Nov 27 2026: every department/workspace AI reads all three company Cores. Other department
//   folders still require their existing profile grant or a named, approved exception.
// - Private and system folders stay out unless the allowlist names them.
import { allowedScopes, BRAIN_FOLDERS, BrainError, type BrainScope, type PinnedFile } from "./brain.ts";

export type Principal =
	| { kind: "person"; email: string; department?: string } // OAuth sign-in (Claude, ChatGPT, Factory) or the Hub session, optionally narrowed
	| { kind: "department"; id: string }; // a department token, fixed to that department's scopes

type Match = (scope: BrainScope) => boolean;
const prefix = (...p: string[]): Match => (s) => p.some((x) => s.startsWith(x));

/** Leader profiles. Everyone else gets nothing. Emails are compared lower case. */
export const PEOPLE: Record<string, { label: string; match: Match }> = {
	"allison@expertpartners.com": { label: "Allison, leader of HQ, EP and AG", match: prefix("hq-", "ep-", "ag-") },
	"don@expertpartners.com": { label: "Don, leader of HQ and EP (not AG)", match: prefix("hq-", "ep-") },
};

const HQ_SYSTEM = ["hq-outputs"];
const EP_SYSTEM = ["ep-outputs"];
const AG_SYSTEM = ["ag-outputs"];
// Shared HQ governance (Rulebook, Decision Log) is context for every department in both companies.
// The AI Experience Director folder (hq-experience) is shared the same way, so builders consult it before designing.
const GOVERNANCE = ["hq-core", "hq-experience"];
/** Company knowledge is shared by AI profiles, not by changing the human leader boundary. */
export const COMPANY_CORES: readonly BrainScope[] = ["hq-core", "ep-core", "ag-core"];

/**
 * Nov 27 2026: each company's CEO project is its whole-brain project. Private folders stay leader-only, and the
 * legacy ag-personal-* keys are excluded because they route to the same folders as ag-core and ag-marketing.
 */
const wholeBrain = (prefix: "hq-" | "ep-" | "ag-"): BrainScope[] =>
	(Object.keys(BRAIN_FOLDERS) as BrainScope[]).filter((s) => s.startsWith(prefix) && !s.endsWith("-private") && !s.startsWith("ag-personal-"));

/**
 * Departments from [HQ][V1.0] Departments, Workspaces and Brain Folders. Each lists the folders its map
 * entry names plus its company's system outputs folder and shared governance. `exceptions` is for named,
 * approved cross-department sources only and stays empty until a decision names the source.
 */
export const DEPARTMENTS: Record<string, { label: string; scopes: BrainScope[]; exceptions: BrainScope[]; fileExceptions?: string[] }> = {
	"ep-ceo": { label: "EP Chief Executive Officer", scopes: [...wholeBrain("ep-"), ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ep-cgo": { label: "EP Chief Growth Officer", scopes: ["ep-marketing", "ep-events", "hq-library", "hq-library-marketing", ...EP_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ep-cro": { label: "EP Chief Revenue Officer", scopes: ["ep-sales", ...EP_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ep-cco": { label: "EP Chief Client Officer", scopes: ["ep-client-experience", ...EP_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ep-coo": { label: "EP Chief Operations Officer", scopes: ["ep-operations", ...EP_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ag-ceo": { label: "AG Chief Executive Officer", scopes: [...wholeBrain("ag-"), ...GOVERNANCE] as BrainScope[], exceptions: [], fileExceptions: ["ag-shared-brand"] },
	"ag-cgo": { label: "AG Luxury Chief Growth Officer", scopes: ["ag-marketing", "ag-strong-ones", "hq-library", "hq-library-marketing", ...AG_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [], fileExceptions: ["ag-shared-brand"] },
	"ag-personal-cgo": { label: "AG Personal Marketing", scopes: ["ag-personal-core", "ag-personal-marketing", ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ag-cro": { label: "AG Chief Revenue Officer", scopes: ["ag-sales", "ag-listings", ...AG_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [], fileExceptions: ["ag-shared-brand"] },
	"ag-cco": { label: "AG Chief Client Officer", scopes: ["ag-client-experience", ...AG_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [], fileExceptions: ["ag-shared-brand"] },
	"ag-coo": { label: "AG Chief Operations Officer", scopes: ["ag-operations", ...AG_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [], fileExceptions: ["ag-shared-brand"] },
	// HQ has no CEO seat; the Chief HR Officer is HQ's top seat and whole-brain project.
	"hq-chro": { label: "HQ Chief HR Officer", scopes: wholeBrain("hq-"), exceptions: [] },
	"hq-cfo": { label: "HQ Chief Finance Officer", scopes: ["hq-finance", ...HQ_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"hq-caio": { label: "HQ Chief AI Officer", scopes: ["hq-operations", "hq-analytics", "hq-partnersync", "hq-audits", ...HQ_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
};

function departmentScopes(id: string): BrainScope[] {
	const d = DEPARTMENTS[id];
	if (!d) throw new BrainError("unknown_department", "That department is not known to this gateway.");
	return [...new Set([...d.scopes, ...d.exceptions, ...COMPANY_CORES])];
}

/** The scopes this principal may read: the deployed allowlist, intersected with their profile. Never wider than either. */
export function effectiveScopes(allowedList: string | undefined, principal: Principal): BrainScope[] {
	const allowed = allowedScopes(allowedList);
	let profile: BrainScope[];
	if (principal.kind === "department") {
		profile = departmentScopes(principal.id);
	} else {
		const person = PEOPLE[principal.email.trim().toLowerCase()];
		if (!person) return [];
		profile = allowed.filter(person.match);
		if (principal.department) profile = profile.filter((s) => departmentScopes(principal.department!).includes(s));
	}
	return allowed.filter((s) => profile.includes(s));
}

/** Named exact-file exception, never a scope grant. Document IDs stay in the Worker secret. */
export function mayReadException(allowedList: string | undefined, principal: Principal, scope: string, id: string, folder: unknown, json: string | undefined): boolean {
	const department = principal.kind === "department" ? principal.id : principal.department;
	const profile = department ? DEPARTMENTS[department] : undefined;
	if (!profile?.fileExceptions?.includes("ag-shared-brand") || scope !== "ag-personal-core" || folder !== undefined) return false;
	// Keep the person's leader boundary and the department's existing Luxury entitlement.
	if (principal.kind === "person" && !PEOPLE[principal.email.trim().toLowerCase()]?.match("ag-core")) return false;
	const allowed = allowedScopes(allowedList);
	if (!allowed.includes("ag-core") || !allowed.includes("ag-personal-core") || !effectiveScopes(allowedList, principal).some((s) => s.startsWith("ag-") && !s.startsWith("ag-personal-"))) return false;
	if (!json) return false;
	let value: unknown;
	try { value = JSON.parse(json); } catch { throw new BrainError("file_exceptions_invalid", "The named file exception is unreadable."); }
	const files = (value && typeof value === "object" && !Array.isArray(value)) ? (value as Record<string, unknown>)["ag-shared-brand"] : undefined;
	if (!Array.isArray(files) || files.length !== 5 || new Set(files).size !== 5 || files.some((file) => typeof file !== "string" || !/^[\w-]+$/.test(file)))
		throw new BrainError("file_exceptions_invalid", "The named file exception is malformed.");
	return files.includes(id);
}

/** Exact files outside every scope root, each pinned to its parent folder and shared drive. Leader only. */
export const PINNED_EXCEPTIONS: Record<string, { count: number; leader: string }> = {
	"gap108-week2-builder": { count: 3, leader: "allison@expertpartners.com" },
};

/**
 * The pinned file this principal may read, or null when the request is not for a pinned exception.
 * Only the named leader acting without a department may use it. The IDs live in the PINNED_FILE_READS
 * secret as {"<exception>":[{"id":"…","parent":"…","drive":"…"}]}, never in this repository.
 */
export function pinnedReadFor(principal: Principal, scope: string, id: string, folder: unknown, json: string | undefined): PinnedFile | null {
	const exception = Object.prototype.hasOwnProperty.call(PINNED_EXCEPTIONS, scope) ? PINNED_EXCEPTIONS[scope]! : undefined;
	if (!exception) return null;
	const refuse = () => new BrainError("not_in_scope", "The file is not a readable document in this scope.");
	if (principal.kind !== "person" || principal.department !== undefined || principal.email.trim().toLowerCase() !== exception.leader) throw refuse();
	if (folder !== undefined || !json) throw refuse();
	let value: unknown;
	try { value = JSON.parse(json); } catch { throw new BrainError("file_exceptions_invalid", "The pinned file exception is unreadable."); }
	const files = value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>)[scope] : undefined;
	const valid = (f: unknown): f is PinnedFile =>
		!!f && typeof f === "object" && ["id", "parent", "drive"].every((k) => typeof (f as any)[k] === "string" && /^[\w-]+$/.test((f as any)[k])) && Object.keys(f).length === 3;
	if (!Array.isArray(files) || files.length !== exception.count || !files.every(valid) || new Set(files.map((f) => f.id)).size !== exception.count)
		throw new BrainError("file_exceptions_invalid", "The pinned file exception is malformed.");
	const pin = files.find((f) => f.id === id);
	if (!pin) throw refuse();
	return pin;
}

export async function sha256Hex(text: string): Promise<string> {
	const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
	return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Department tokens live only as SHA-256 hashes in the DEPARTMENT_TOKEN_HASHES secret: {"<hash>":"<department id>"}. */
export async function departmentForToken(hashesJson: string | undefined, token: string): Promise<string | null> {
	if (!hashesJson || !token) return null;
	let map: Record<string, string>;
	try {
		map = JSON.parse(hashesJson);
	} catch {
		return null;
	}
	const id = map[await sha256Hex(token)];
	return id && DEPARTMENTS[id] ? id : null;
}
