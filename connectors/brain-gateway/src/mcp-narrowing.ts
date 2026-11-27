import { AsyncLocalStorage } from "node:async_hooks";
import { DEPARTMENTS, type Principal } from "./access.ts";
import { isAllowedEmail } from "./allow.ts";

export type Narrowing = Readonly<{ department?: string; businessLine?: "AGRE" | "AGI" }>;

const storage = new AsyncLocalStorage<Narrowing>();

/**
 * The optional X-Brain-Department header can only narrow a signed-in person, exactly like the Hub token.
 * Absent means the plain person. Anything other than a known profile key is refused, never ignored.
 */
export function parseNarrowing(headers: Headers): Narrowing | null {
	const value = headers.get("x-brain-department");
	const line = headers.get("x-brain-business-line");
	if (value === null) return line === null ? Object.freeze({}) : null;
	if (!Object.prototype.hasOwnProperty.call(DEPARTMENTS, value)) return null;
	if (value.startsWith("ag-")) {
		return line === "AGRE" || line === "AGI" ? Object.freeze({ department: value, businessLine: line }) : null;
	}
	return line === null ? Object.freeze({ department: value }) : null;
}

export function runNarrowed<T>(narrowing: Narrowing, fn: () => T): T {
	return storage.run(narrowing, fn);
}

export function currentNarrowing(): Narrowing | undefined {
	return storage.getStore();
}

/**
 * Identity comes only from the provider's verified OAuth props; the department only from the request header
 * parsed before dispatch. A missing narrowing context fails closed rather than falling back to the whole person.
 */
export function mcpPrincipal(props: unknown, allowedEmails: string | undefined, narrowing: Narrowing | undefined): Extract<Principal, { kind: "person" }> | null {
	if (!narrowing || !props || typeof props !== "object") return null;
	const email = (props as Record<string, unknown>).email;
	if (typeof email !== "string" || !isAllowedEmail(allowedEmails, email)) return null;
	return Object.freeze({ kind: "person", email, ...(narrowing.department ? { department: narrowing.department } : {}), ...(narrowing.businessLine ? { businessLine: narrowing.businessLine } : {}) });
}
