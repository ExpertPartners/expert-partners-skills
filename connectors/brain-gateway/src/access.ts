// Who may read which scopes. Enforced here, in the gateway, because instructions and folder maps
// do not create Drive permissions (Decision Log, Nov 20 2026, Business Brain department access).
//
// Approved basis (Decision Log Nov 20 2026):
// - Leader-level access, whole brain: Allison and Don for Expert Partners and HQ, Allison alone for AG Luxury.
// - Department AIs start with their own department folder plus shared HQ governance, and reach another
//   department only through a named, approved exception.
// - Private, proposed and system folders stay out unless the allowlist names them.
import { allowedScopes, BrainError, type BrainScope } from "./brain.ts";

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

const EP_SYSTEM = ["ep-outputs"];
const AG_SYSTEM = ["ag-outputs"];
// Shared HQ governance (Rulebook, Decision Log) is context for every department in both companies.
const GOVERNANCE = ["hq-core"];

/**
 * Departments from [HQ][V1.0] Departments, Workspaces and Brain Folders. Each lists the folders its map
 * entry names plus its company's system outputs folder and shared governance. `exceptions` is for named,
 * approved cross-department sources only and stays empty until a decision names the source.
 */
export const DEPARTMENTS: Record<string, { label: string; scopes: BrainScope[]; exceptions: BrainScope[] }> = {
	"ep-ceo": { label: "EP Chief Executive Officer", scopes: ["ep-core", "ep-discovery", ...EP_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ep-cgo": { label: "EP Chief Growth Officer", scopes: ["ep-marketing", "hq-library", ...EP_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ep-cro": { label: "EP Chief Revenue Officer", scopes: ["ep-sales", ...EP_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ep-cco": { label: "EP Chief Client Officer", scopes: ["ep-client-experience", ...EP_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ep-coo": { label: "EP Chief Operations Officer", scopes: ["ep-operations", ...EP_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ag-ceo": { label: "AG Chief Executive Officer", scopes: ["ag-core", ...AG_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ag-cgo": { label: "AG Chief Growth Officer", scopes: ["ag-marketing", "hq-library", ...AG_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ag-cro": { label: "AG Chief Revenue Officer", scopes: ["ag-sales", "ag-listings", ...AG_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ag-cco": { label: "AG Chief Client Officer", scopes: ["ag-client-experience", ...AG_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"ag-coo": { label: "AG Chief Operations Officer", scopes: ["ag-operations", ...AG_SYSTEM, ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"hq-chro": { label: "HQ Chief HR Officer", scopes: ["hq-hr", "hq-employees", "hq-skills", ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"hq-cfo": { label: "HQ Chief Finance Officer", scopes: ["hq-finance", ...GOVERNANCE] as BrainScope[], exceptions: [] },
	"hq-caio": { label: "HQ Chief AI Officer", scopes: ["hq-operations", "hq-analytics", "hq-partnersync", ...GOVERNANCE] as BrainScope[], exceptions: [] },
};

function departmentScopes(id: string): BrainScope[] {
	const d = DEPARTMENTS[id];
	if (!d) throw new BrainError("unknown_department", "That department is not known to this gateway.");
	return [...d.scopes, ...d.exceptions];
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
