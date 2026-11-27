import { checkArrivals } from "./arrivals.ts";
import type { DriveFetch } from "./brain.ts";
import type { Check } from "./health.ts";

const SOURCES = ["fireflies", "plaud", "zoom"] as const;
const SCOPE = "company";
const HOUR = 3_600_000;
const MAX_BYTES = 8192;
const ID = /^[A-Za-z0-9_-]{10,128}$/;
const LOCAL = new Intl.DateTimeFormat("en-CA", {
	timeZone: "America/Chicago", year: "numeric", month: "2-digit", day: "2-digit",
});

export function completedRecordingDay(now: Date) {
	const midnight = (day: string) => {
		const utc = Date.parse(`${day}T00:00:00Z`);
		// Chicago civil midnight always falls on an exact UTC hour, including DST change days.
		for (let i = 0; i < 24; i++) {
			const point = new Date(utc + i * HOUR);
			if (LOCAL.format(point) === day) return point.toISOString();
		}
		throw new Error("invalid recording day");
	};
	const today = LOCAL.format(now);
	const prior = new Date(Date.parse(`${today}T00:00:00Z`) - 24 * HOUR).toISOString().slice(0, 10);
	return { windowStart: midnight(prior), windowEnd: midnight(today), maxAgeMs: 36 * HOUR };
}

function fileIds(raw?: string): Partial<Record<(typeof SOURCES)[number], string>> {
	if (!raw) return {};
	try {
		const ids = JSON.parse(raw);
		if (!ids || typeof ids !== "object" || Array.isArray(ids) ||
			Object.keys(ids).some((key) => !(SOURCES as readonly string[]).includes(key)) ||
			Object.values(ids).some((id) => typeof id !== "string" || !ID.test(id)) ||
			new Set(Object.values(ids)).size !== Object.values(ids).length) return {};
		return ids;
	} catch {
		return {};
	}
}

async function readAggregate(drive: DriveFetch, id: string) {
	const path = `/drive/v3/files/${id}`;
	const metadata = async () => {
		const response = await drive(`${path}?supportsAllDrives=true&fields=id,mimeType,trashed,version`);
		if (!response.ok) throw new Error();
		const value = await response.json() as { id?: string; mimeType?: string; trashed?: boolean; version?: string };
		if (value.id !== id || value.mimeType !== "application/json" || value.trashed !== false ||
			typeof value.version !== "string" || !/^\d+$/.test(value.version)) throw new Error();
		return value.version;
	};
	const version = await metadata();
	const response = await drive(`${path}?alt=media&supportsAllDrives=true`);
	if (!response.ok || !response.body) throw new Error();
	const reader = response.body.getReader();
	const decoder = new TextDecoder();
	let size = 0;
	let text = "";
	try {
		while (true) {
			const { value, done } = await reader.read();
			if (done) break;
			size += value.length;
			// The aggregate contract contains only ASCII labels, numbers and timestamps.
			if (size > MAX_BYTES || value.some((byte: number) => byte > 127)) throw new Error();
			text += decoder.decode(value);
		}
	} finally {
		await reader.cancel();
	}
	if (await metadata() !== version) throw new Error();
	return JSON.parse(text) as unknown;
}

/** One independently published aggregate per source, pinned by ID and read with the existing Drive identity. */
export async function recordingArrivalChecks(rawIds: string | undefined, drive: DriveFetch, now: Date): Promise<Check[]> {
	const ids = fileIds(rawIds);
	const window = completedRecordingDay(now);
	return Promise.all(SOURCES.map(async (source) => {
		const id = ids[source];
		const coverage = [{ source, scope: SCOPE }];
		try {
			return checkArrivals(id ? await readAggregate(drive, id) : undefined, coverage, window, now)[0];
		} catch {
			return { name: `arrivals ${source}/${SCOPE}`, ok: false, detail: "snapshot_unreadable" };
		}
	}));
}
