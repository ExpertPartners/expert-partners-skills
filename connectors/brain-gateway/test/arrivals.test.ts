import { test } from "node:test";
import assert from "node:assert/strict";
import { checkArrivals, type ArrivalPair } from "../src/arrivals.ts";

const NOW = new Date("2026-11-27T12:00:00Z");
const WINDOW = { windowStart: "2026-11-26T00:00:00Z", windowEnd: "2026-11-27T00:00:00Z", maxAgeMs: 3_600_000 };
const COVERAGE = [{ source: "fireflies", scope: "ep-core" }, { source: "plaud", scope: "ag-core" }, { source: "zoom", scope: "hq-core" }];
const row = (p = COVERAGE[0], extra = {}) => ({ ...p, state: "verified", expected: 2, arrived: 2, destinationReady: true, ...extra });
const snapshot = (extra = {}) => ({ schemaVersion: 1, ...WINDOW, maxAgeMs: undefined, observedAt: "2026-11-27T11:30:00Z", complete: true, sources: COVERAGE.map((p) => row(p)), ...extra });
function valid(extra = {}) {
	const { maxAgeMs: _unused, ...value } = snapshot(extra);
	return value;
}
const check = (value: unknown) => checkArrivals(value, COVERAGE, WINDOW, NOW);
const code = (value: unknown, expected: string) => assert.ok(check(value).every((c) => !c.ok && c.detail === expected), JSON.stringify(check(value)));

test("all configured sources pass only with complete equal verified counts", () => {
	assert.ok(check(valid()).every((c) => c.ok));
	assert.deepEqual(check(valid()).map((c) => c.name), COVERAGE.map((p) => `arrivals ${p.source}/${p.scope}`));
});
test("verified zero is distinct from unknown and absent producer", () => {
	assert.equal(check(valid({ sources: COVERAGE.map((p) => row(p, { expected: 0, arrived: 0 })) }))[0].ok, true);
	assert.equal(check(valid({ sources: COVERAGE.map((p) => row(p, { expected: null, arrived: null })) }))[0].detail, "incomplete_counts");
	code(undefined, "unconfigured");
});
test("each unsupported, unconfigured and incomplete source is nonpassing", () => {
	for (const state of ["unsupported", "unconfigured", "incomplete"]) {
		code(valid({ sources: COVERAGE.map((p) => row(p, { state, expected: null, arrived: null })) }), state);
	}
});
test("mismatch in either direction preserves exact counts", () => {
	for (const arrived of [1, 3]) {
		const c = check(valid({ sources: [row(COVERAGE[0], { arrived }), row(COVERAGE[1]), row(COVERAGE[2])] }))[0];
		assert.deepEqual(c, { name: "arrivals fireflies/ep-core", ok: false, detail: `mismatch: expected 2, arrived ${arrived}` });
	}
});
test("a missing source cannot silently disappear from coverage", () => {
	const c = check(valid({ sources: [row()] }));
	assert.equal(c.length, 3);
	assert.equal(c[1].detail, "missing_source");
	assert.equal(c[2].detail, "missing_source");
});
test("duplicate and unexpected pairs refuse the snapshot", () => {
	code(valid({ sources: [row(), row()] }), "invalid_coverage");
	code(valid({ sources: [row({ source: "other", scope: "ep-core" })] }), "invalid_coverage");
});
test("nonintegers, coerced counts and unsafe integers fail closed", () => {
	for (const expected of [-1, 1.1, "2", false, Infinity, NaN, Number.MAX_SAFE_INTEGER + 1]) {
		code(valid({ sources: [row(COVERAGE[0], { expected })] }), "invalid_coverage");
	}
	assert.ok(check(valid({ sources: COVERAGE.map((p) => row(p, { expected: Number.MAX_SAFE_INTEGER, arrived: Number.MAX_SAFE_INTEGER })) })).every((c) => c.ok));
});
test("no destination and incomplete enumeration do not pass", () => {
	code(valid({ sources: COVERAGE.map((p) => row(p, { destinationReady: false })) }), "destination_unavailable");
	code(valid({ complete: false }), "incomplete_snapshot");
});
test("state and destination flags require exact primitive types", () => {
	for (const extra of [{ state: true }, { state: ["verified"] }, { state: "unknown" }, { destinationReady: "true" }, { arrived: "2" }]) {
		code(valid({ sources: [row(COVERAGE[0], extra)] }), "invalid_coverage");
	}
});
test("stale, future, wrong-window and unclosed observations fail", () => {
	code(valid({ observedAt: "2026-11-27T10:59:59.999Z" }), "stale_snapshot");
	assert.ok(check(valid({ observedAt: "2026-11-27T11:00:00Z" })).every((c) => c.ok));
	for (const extra of [
		{ observedAt: "2026-11-27T12:00:00.001Z" },
		{ observedAt: "2026-11-26T23:59:59Z" },
		{ windowStart: "2026-11-25T00:00:00Z" },
		{ windowEnd: "2026-11-28T00:00:00Z" },
		{ observedAt: "2026-11-27T11:30:00+00:00" },
		{ observedAt: "2026-02-30T00:00:00Z" },
	]) code(valid(extra), "invalid_interval");
});
test("unexpected fields, schema types and oversized snapshots are refused", () => {
	for (const value of [null, [], {}, valid({ schemaVersion: true }), valid({ complete: "true" }), valid({ privateContent: "canary-private-body" }), valid({ sources: Array(129).fill(row()) })]) {
		code(value, "invalid_snapshot");
		assert.ok(!JSON.stringify(check(value)).includes("canary"));
	}
	code(valid({ sources: [row(COVERAGE[0], { title: "canary-private-title" })] }), "invalid_coverage");
});
test("invalid configuration produces a fixed gap without echoing labels", () => {
	for (const coverage of [[], [COVERAGE[0], COVERAGE[0]], [{ source: "canary@email.example", scope: "ep-core" }], Array(129).fill(COVERAGE[0])]) {
		assert.deepEqual(checkArrivals(valid(), coverage, WINDOW, NOW), [{ name: "arrivals configuration", ok: false, detail: "unconfigured" }]);
	}
	for (const maxAgeMs of [0, -1, 1.5, Infinity]) {
		assert.equal(checkArrivals(valid(), COVERAGE, { ...WINDOW, maxAgeMs }, NOW)[0].detail, "unconfigured");
	}
});
test("configured coverage supports exactly 128 pairs without truncation", () => {
	const coverage: ArrivalPair[] = Array.from({ length: 128 }, (_, i) => ({ source: `source-${i}`, scope: "ep-core" }));
	const c = checkArrivals(valid({ sources: coverage.map((p) => row(p)) }), coverage, WINDOW, NOW);
	assert.equal(c.length, 128);
	assert.ok(c.every((v) => v.ok));
});
