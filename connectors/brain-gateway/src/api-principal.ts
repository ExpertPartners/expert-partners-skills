import { departmentForToken, DEPARTMENTS, type Principal } from "./access.ts";

/** Constant-time compare for the Hub bearer token. */
export function safeEqual(a: string, b: string) {
	const enc = new TextEncoder();
	const x = enc.encode(a);
	const y = enc.encode(b);
	if (x.length !== y.length) return false;
	let diff = 0;
	for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
	return diff === 0;
}

/**
 * Two kinds of bearer. The Hub token acts as Allison and may only narrow itself with X-Brain-Department.
 * A department token is fixed to its department; the header can never select or widen its profile.
 */
export async function apiPrincipal(request: Request, bindings: { HUB_API_TOKEN?: string; DEPARTMENT_TOKEN_HASHES?: string }): Promise<Principal | "unknown_department" | null> {
	const auth = request.headers.get("authorization") ?? "";
	const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
	if (bindings.HUB_API_TOKEN && token && safeEqual(token, bindings.HUB_API_TOKEN)) {
		const dept = request.headers.get("x-brain-department") ?? undefined;
		if (dept && !Object.prototype.hasOwnProperty.call(DEPARTMENTS, dept)) return "unknown_department";
		return { kind: "person", email: "allison@expertpartners.com", department: dept };
	}
	const id = await departmentForToken(bindings.DEPARTMENT_TOKEN_HASHES, token);
	return id ? { kind: "department", id } : null;
}
