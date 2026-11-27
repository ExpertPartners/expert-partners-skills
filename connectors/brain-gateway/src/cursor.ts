// Row-mode continuation cursors. A cursor only says where the next row page starts and what earlier pages
// already wrote; it never grants access, and every request still runs the full scope and version proofs.
// It is HMAC-signed with the dedicated ROW_CURSOR_KEY secret so a caller cannot invent held empty rows.
import { BrainError } from "./brain.ts";

export const CURSOR_MAX_LENGTH = 1024;
export const CURSOR_TTL_MS = 6 * 60 * 60 * 1000;
/** Google Sheets caps a spreadsheet at ten million cells, so no tab can have more rows. */
const MAX_GRID_ROWS = 10_000_000;
const CONTEXT = "brain-gateway/rows-cursor/v1.";

export type CursorState = {
	scope: string;
	id: string;
	sheet: string;
	folder: string;
	version: string;
	next: number;
	pending: number;
	emitted: boolean;
	grid: number;
	exp: number;
};

const b64url = (bytes: Uint8Array) => {
	let s = "";
	for (const b of bytes) s += String.fromCharCode(b);
	return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};
const fromB64url = (s: string) => {
	const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (s.length % 4)) % 4));
	return Uint8Array.from(bin, (c) => c.charCodeAt(0));
};

const unavailable = () => new BrainError("cursor_unavailable", "Row mode is unavailable because its cursor key is not configured. Character-offset mode is unaffected.");
const invalid = () => new BrainError("invalid_cursor", "The row cursor is invalid, expired or belongs to another read. Restart from start_row.");

/** A missing or weak key refuses row mode entirely. There is no unsigned fallback. */
export async function cursorKey(raw: string | undefined): Promise<CryptoKey> {
	if (!raw || !/^[A-Za-z0-9_-]{43,128}$/.test(raw)) throw unavailable();
	const bytes = fromB64url(raw);
	if (bytes.byteLength < 32) throw unavailable();
	return crypto.subtle.importKey("raw", bytes, { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

export async function sealCursor(key: CryptoKey, c: CursorState): Promise<string> {
	const payload = b64url(new TextEncoder().encode(JSON.stringify([c.scope, c.id, c.sheet, c.folder, c.version, c.next, c.pending, c.emitted ? 1 : 0, c.grid, c.exp])));
	const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(CONTEXT + payload)));
	const token = `${payload}.${b64url(mac)}`;
	if (token.length > CURSOR_MAX_LENGTH) throw new BrainError("invalid_row_range", "This read cannot be continued with a bounded cursor.");
	return token;
}

export async function openCursor(key: CryptoKey, token: string, nowMs: number): Promise<CursorState> {
	if (token.length > CURSOR_MAX_LENGTH) throw invalid();
	const m = token.match(/^([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]{43})$/);
	if (!m) throw invalid();
	let ok = false;
	try {
		ok = await crypto.subtle.verify("HMAC", key, fromB64url(m[2]!), new TextEncoder().encode(CONTEXT + m[1]!));
	} catch {
		ok = false;
	}
	if (!ok) throw invalid();
	let f: unknown;
	try {
		f = JSON.parse(new TextDecoder("utf-8", { fatal: true, ignoreBOM: false }).decode(fromB64url(m[1]!)));
	} catch {
		throw invalid();
	}
	if (!Array.isArray(f) || f.length !== 10) throw invalid();
	const [scope, id, sheet, folder, version, next, pending, emitted, grid, exp] = f;
	const str = (v: unknown) => typeof v === "string";
	const int = (v: unknown, min: number, max: number) => Number.isSafeInteger(v) && (v as number) >= min && (v as number) <= max;
	if (!str(scope) || !str(id) || !str(sheet) || !str(folder) || !str(version) || !/^\d+$/.test(version)) throw invalid();
	if (!int(grid, 1, MAX_GRID_ROWS) || !int(next, 1, grid) || !int(pending, 0, next - 1) || (emitted !== 0 && emitted !== 1)) throw invalid();
	if (!int(exp, 0, Number.MAX_SAFE_INTEGER) || exp <= nowMs) throw invalid();
	return { scope, id, sheet, folder, version, next, pending, emitted: emitted === 1, grid, exp };
}
