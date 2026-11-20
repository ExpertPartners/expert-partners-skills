// Google service account access for Drive, read-only. The key is the GOOGLE_SA_KEY Worker secret
// (JSON). There is no domain-wide delegation: the service account sees only the folders and shared
// drives it was added to as a Viewer. The key and tokens are never logged or returned.
import type { DriveFetch } from "./brain.ts";

export const DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly";
const API = "https://www.googleapis.com";

type SaKey = { client_email: string; private_key: string; token_uri?: string };

const b64url = (data: ArrayBuffer | string) => {
	const bytes = typeof data === "string" ? new TextEncoder().encode(data) : new Uint8Array(data);
	let s = "";
	for (const b of bytes) s += String.fromCharCode(b);
	return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};

function pemToDer(pem: string): ArrayBuffer {
	const body = pem.replace(/-----(BEGIN|END) PRIVATE KEY-----/g, "").replace(/\s+/g, "");
	const bin = atob(body);
	const out = new Uint8Array(bin.length);
	for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
	return out.buffer;
}

export function parseKey(raw: string | undefined): SaKey {
	if (!raw) throw new Error("GOOGLE_SA_KEY is not set");
	const key = JSON.parse(raw) as SaKey;
	if (!key.client_email || !key.private_key) throw new Error("GOOGLE_SA_KEY is not a service account key");
	return key;
}

export async function signAssertion(key: SaKey, nowSec: number): Promise<string> {
	const header = b64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
	const claims = b64url(
		JSON.stringify({
			iss: key.client_email,
			scope: DRIVE_SCOPE,
			aud: key.token_uri ?? "https://oauth2.googleapis.com/token",
			iat: nowSec,
			exp: nowSec + 3600,
		}),
	);
	const cryptoKey = await crypto.subtle.importKey("pkcs8", pemToDer(key.private_key), { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
	const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", cryptoKey, new TextEncoder().encode(`${header}.${claims}`));
	return `${header}.${claims}.${b64url(sig)}`;
}

let cached: { token: string; expiresAt: number } | null = null;

async function accessToken(raw: string | undefined, fetchImpl: typeof fetch): Promise<string> {
	const now = Math.floor(Date.now() / 1000);
	if (cached && cached.expiresAt - 60 > now) return cached.token;
	const key = parseKey(raw);
	const assertion = await signAssertion(key, now);
	const res = await fetchImpl(key.token_uri ?? "https://oauth2.googleapis.com/token", {
		method: "POST",
		headers: { "content-type": "application/x-www-form-urlencoded" },
		body: new URLSearchParams({ grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion }),
	});
	if (!res.ok) throw new Error(`Google token exchange answered ${res.status}`);
	const body = (await res.json()) as { access_token?: string; expires_in?: number };
	if (!body.access_token) throw new Error("Google returned no access token");
	cached = { token: body.access_token, expiresAt: now + (body.expires_in ?? 3600) };
	return cached.token;
}

/** Drive GET-only client. Anything that is not a read of the Drive v3 files API is refused here. */
export function driveFetch(rawKey: string | undefined, fetchImpl: typeof fetch = fetch): DriveFetch {
	return async (path: string) => {
		if (!path.startsWith("/drive/v3/files")) throw new Error("Only the Drive v3 files API is reachable.");
		const token = await accessToken(rawKey, fetchImpl);
		return fetchImpl(`${API}${path}`, { method: "GET", headers: { authorization: `Bearer ${token}` } });
	};
}
