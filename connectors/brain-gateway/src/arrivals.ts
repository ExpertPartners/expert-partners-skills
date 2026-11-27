// Aggregate-only arrival validation. The ingestion owner supplies the authenticated
// snapshot; this module neither fetches content nor creates a schedule or store.
import type { Check } from "./health.ts";

export type ArrivalPair = { source: string; scope: string };
export type ArrivalWindow = { windowStart: string; windowEnd: string; maxAgeMs: number };
type Row = ArrivalPair & {
	state: "verified" | "unsupported" | "unconfigured" | "incomplete";
	expected: number | null;
	arrived: number | null;
	destinationReady: boolean;
};

const LIMIT = 128;
const LABEL = /^[a-z][a-z0-9-]{0,63}$/;
const ROOT_KEYS = ["schemaVersion", "observedAt", "windowStart", "windowEnd", "complete", "sources"];
const ROW_KEYS = ["source", "scope", "state", "expected", "arrived", "destinationReady"];

function object(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

function keys(value: Record<string, unknown>, allowed: string[]): boolean {
	return Object.keys(value).length === allowed.length && allowed.every((key) => Object.prototype.hasOwnProperty.call(value, key));
}

function stamp(value: unknown): number {
	if (typeof value !== "string" || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?Z$/.test(value)) return NaN;
	const ms = Date.parse(value);
	return Number.isFinite(ms) && new Date(ms).toISOString() === value.replace(/(?<!\.\d{3})Z$/, ".000Z") ? ms : NaN;
}

function count(value: unknown): boolean {
	return value === null || (typeof value === "number" && Number.isSafeInteger(value) && value >= 0);
}

function pair(value: unknown): value is ArrivalPair & Record<string, unknown> {
	return object(value) && typeof value.source === "string" && LABEL.test(value.source)
		&& typeof value.scope === "string" && LABEL.test(value.scope);
}

const id = (p: ArrivalPair) => `${p.source}/${p.scope}`;
const failure = (name: string, detail: string): Check => ({ name, ok: false, detail });

/** Validate one completed interval against configured coverage, never response-selected coverage.
 * Output contains only trusted pair labels, aggregate integers and fixed codes.
 * Missing authentication/producer wiring passes undefined and remains unconfigured.
 */
export function checkArrivals(
	snapshot: unknown,
	coverage: readonly ArrivalPair[],
	window: ArrivalWindow,
	now = new Date(),
): Check[] {
	const start = stamp(window.windowStart);
	const end = stamp(window.windowEnd);
	const at = now.getTime();
	if (!coverage.length || coverage.length > LIMIT || !coverage.every(pair)
		|| new Set(coverage.map(id)).size !== coverage.length
		|| !Number.isFinite(start) || !Number.isFinite(end) || start >= end || end > at
		|| !Number.isFinite(at) || !Number.isSafeInteger(window.maxAgeMs) || window.maxAgeMs <= 0) {
		return [failure("arrivals configuration", "unconfigured")];
	}
	const gaps = (code: string) => coverage.map((p) => failure(`arrivals ${id(p)}`, code));
	if (snapshot === undefined) return gaps("unconfigured");
	if (!object(snapshot) || !keys(snapshot, ROOT_KEYS) || snapshot.schemaVersion !== 1
		|| typeof snapshot.complete !== "boolean" || !Array.isArray(snapshot.sources)
		|| snapshot.sources.length > LIMIT) return gaps("invalid_snapshot");
	const observed = stamp(snapshot.observedAt);
	if (!Number.isFinite(observed) || stamp(snapshot.windowStart) !== start || stamp(snapshot.windowEnd) !== end
		|| observed < end || observed > at) return gaps("invalid_interval");
	if (at - observed > window.maxAgeMs) return gaps("stale_snapshot");
	if (!snapshot.complete) return gaps("incomplete_snapshot");
	const rows = new Map<string, Row>();
	const required = new Set(coverage.map(id));
	for (const value of snapshot.sources) {
		if (!object(value) || !keys(value, ROW_KEYS) || !pair(value)
			|| typeof value.state !== "string" || !["verified", "unsupported", "unconfigured", "incomplete"].includes(value.state)
			|| !count(value.expected) || !count(value.arrived) || typeof value.destinationReady !== "boolean"
			|| !required.has(id(value)) || rows.has(id(value))) return gaps("invalid_coverage");
		rows.set(id(value), value as Row);
	}
	return coverage.map((p) => {
		const name = `arrivals ${id(p)}`;
		const row = rows.get(id(p));
		if (!row) return failure(name, "missing_source");
		if (row.state !== "verified") return failure(name, row.state);
		if (row.expected === null || row.arrived === null) return failure(name, "incomplete_counts");
		if (!row.destinationReady) return failure(name, "destination_unavailable");
		const detail = `expected ${row.expected}, arrived ${row.arrived}`;
		return { name, ok: row.expected === row.arrived, detail: `${row.expected === row.arrived ? "verified" : "mismatch"}: ${detail}` };
	});
}
