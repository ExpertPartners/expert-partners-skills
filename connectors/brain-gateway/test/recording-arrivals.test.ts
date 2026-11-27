import assert from "node:assert/strict";
import test from "node:test";
import { completedRecordingDay, recordingArrivalChecks } from "../src/recording-arrivals.ts";
import type { DriveFetch } from "../src/brain.ts";

const now = new Date("2026-11-27T12:00:00Z");
const ids = { fireflies: "testFireflies1", plaud: "testPlaud111", zoom: "testZoom1111" };
const idFrom = (path: string) => path.slice(path.lastIndexOf("/") + 1).split("?")[0];
const snapshot = (source: string, expected = 1, arrived = 1) => ({
	schemaVersion: 1, observedAt: "2026-11-27T10:00:00Z", windowStart: "2026-11-26T06:00:00Z",
	windowEnd: "2026-11-27T06:00:00Z", complete: true,
	sources: [{ source, scope: "company", state: "verified", expected, arrived, destinationReady: true }],
});

test("previous Chicago civil day uses 23 or 25 hours across DST", () => {
	assert.deepEqual(completedRecordingDay(new Date("2026-03-09T12:00:00Z")), {
		windowStart: "2026-03-08T06:00:00.000Z", windowEnd: "2026-03-09T05:00:00.000Z", maxAgeMs: 129600000,
	});
	assert.deepEqual(completedRecordingDay(new Date("2026-11-02T05:59:59Z")), {
		windowStart: "2026-10-31T05:00:00.000Z", windowEnd: "2026-11-01T05:00:00.000Z", maxAgeMs: 129600000,
	});
	assert.deepEqual(completedRecordingDay(new Date("2026-11-02T06:00:00Z")), {
		windowStart: "2026-11-01T05:00:00.000Z", windowEnd: "2026-11-02T06:00:00.000Z", maxAgeMs: 129600000,
	});
});

test("daily reconciliation keeps mismatch, verified zero, and unreadable source distinct", async () => {
	const drive: DriveFetch = async (path) => {
		const id = idFrom(path);
		if (id === ids.zoom) return new Response(null, { status: 403 });
		if (!path.includes("alt=media")) return Response.json({ id, mimeType: "application/json", trashed: false, version: "3" });
		return Response.json(id === ids.fireflies ? snapshot("fireflies", 2, 1) : snapshot("plaud", 0, 0));
	};
	assert.deepEqual(await recordingArrivalChecks(JSON.stringify(ids), drive, now), [
		{ name: "arrivals fireflies/company", ok: false, detail: "mismatch: expected 2, arrived 1" },
		{ name: "arrivals plaud/company", ok: true, detail: "verified: expected 0, arrived 0" },
		{ name: "arrivals zoom/company", ok: false, detail: "snapshot_unreadable" },
	]);
});

test("refuses unstable, oversized, and wrong-source data", async () => {
	let firefliesVersion = 0;
	const drive: DriveFetch = async (path) => {
		const id = idFrom(path);
		if (!path.includes("alt=media")) {
			const version = id === ids.fireflies ? String(++firefliesVersion) : "1";
			return Response.json({ id, mimeType: "application/json", trashed: false, version });
		}
		return id === ids.plaud ? new Response("x".repeat(8193)) : Response.json(snapshot("fireflies"));
	};
	const checks = await recordingArrivalChecks(JSON.stringify(ids), drive, now);
	assert.deepEqual(checks.map((c) => c.detail), ["snapshot_unreadable", "snapshot_unreadable", "invalid_coverage"]);
	assert(checks.every((c) => !c.ok));
});

test("missing or untrusted configuration does not probe Drive or report zero arrivals", async () => {
	let calls = 0;
	const drive: DriveFetch = async () => { calls++; throw new Error(); };
	const checks = await recordingArrivalChecks(JSON.stringify({ ...ids, zoom: ids.plaud }), drive, now);
	assert.equal(calls, 0);
	assert.equal(checks.length, 3);
	assert(checks.every((c) => !c.ok && c.detail === "unconfigured"));
});
