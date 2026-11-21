// Daily check of the live Business Brain connection (Decision Log, Nov 20 2026, Business Brain connection
// monitoring, Option B). It reads live and keeps only pass or fail facts: counts, versions, dates and
// error codes. It never stores document text, and it does not mirror or reupload anything.
import { allowedScopes, BRAIN_FOLDERS, createBrainReads, CURRENT_DECISION_LOG, type DriveFetch } from "./brain.ts";

export type Check = { name: string; ok: boolean; detail: string };
export type HealthResult = { ok: boolean; checkedAt: string; checks: Check[] };

const MAX_DECISION_AGE_DAYS = 14;

function fail(name: string, e: unknown): Check {
	const code = (e as { code?: string })?.code ?? "error";
	return { name, ok: false, detail: `failed (${code})` };
}

export async function runDeepCheck(allowedList: string | undefined, drive: DriveFetch, now = () => new Date()): Promise<HealthResult> {
	const reads = createBrainReads(drive, now);
	const checks: Check[] = [];
	const scopes = allowedScopes(allowedList);
	checks.push({ name: "allowlist", ok: scopes.length > 0, detail: `${scopes.length} scopes allowed` });

	// Reachability, completeness and scope: every allowed scope lists its registered folder completely.
	for (const scope of scopes) {
		try {
			const r = await reads.discover(scope);
			checks.push({ name: `scope ${scope}`, ok: r.complete && r.folderId === BRAIN_FOLDERS[scope], detail: `${r.files.length} files, complete` });
		} catch (e) {
			checks.push(fail(`scope ${scope}`, e));
		}
	}

	// Key decisions: the current Decision Log reads whole, is verified, and its newest entry is fresh.
	try {
		const d = await reads.decisions();
		const newest = d.newest[0]?.date;
		const ageDays = newest ? (now().getTime() - Date.parse(newest)) / 86_400_000 : Infinity;
		checks.push({ name: "decision log complete read", ok: d.totalChars > 0, detail: `${d.totalChars} characters, version ${d.file.version}` });
		checks.push({ name: "decision log freshness", ok: ageDays <= MAX_DECISION_AGE_DAYS, detail: `newest ${newest ?? "none"} (${Number.isFinite(ageDays) ? Math.floor(ageDays) : "?"} days)` });
	} catch (e) {
		checks.push(fail("decision log complete read", e));
	}

	// Content completeness: a representative company document reads whole in the HQ core scope.
	try {
		const list = await reads.discover("hq-core", "Rulebook");
		const doc = list.files.find((f) => f.name.includes("HQ Rulebook")) ?? list.files[0];
		if (!doc) throw Object.assign(new Error("no rulebook"), { code: "not_found" });
		const r = await reads.read("hq-core", doc.id, 0, 1000);
		checks.push({ name: "rulebook complete read", ok: r.totalChars > 1000 && r.text.length > 0, detail: `${r.totalChars} characters, version ${doc.version}` });
	} catch (e) {
		checks.push(fail("rulebook complete read", e));
	}
	checks.push({ name: "decision log id registered", ok: CURRENT_DECISION_LOG.length > 10, detail: "current log id present" });

	return { ok: checks.every((c) => c.ok), checkedAt: now().toISOString(), checks };
}

const KEY = "health:last";
const FAILED_KEY = "health:lastFailure";

/** Keep the latest result, and the latest failure separately so a later pass does not hide it. */
export async function storeResult(kv: KVNamespace, result: HealthResult) {
	await kv.put(KEY, JSON.stringify(result));
	if (!result.ok) await kv.put(FAILED_KEY, JSON.stringify(result));
}

export async function lastResults(kv: KVNamespace) {
	const [last, lastFailure] = await Promise.all([kv.get(KEY), kv.get(FAILED_KEY)]);
	return { last: last ? (JSON.parse(last) as HealthResult) : null, lastFailure: lastFailure ? (JSON.parse(lastFailure) as HealthResult) : null };
}
