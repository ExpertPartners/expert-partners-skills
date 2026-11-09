// Thin client for the Factory Public API (https://docs.factory.com/openapi.json).
// The API key is read from the FACTORY_API_KEY Worker secret and never logged or returned.

export const API_BASE = "https://api.factory.ai";
export const READINESS_BASE = "https://app.factory.ai";

export class FactoryError extends Error {
	status: number;
	body: unknown;
	path: string;
	constructor(status: number, body: unknown, path: string) {
		super(`Factory API ${status} on ${path}`);
		this.status = status;
		this.body = body;
		this.path = path;
	}
}

export type Query = Record<string, string | number | boolean | undefined | null>;

export class Factory {
	private key: string;
	private base: string;
	constructor(key: string, base = API_BASE) {
		this.key = key;
		this.base = base;
	}

	async call<T = any>(
		method: string,
		path: string,
		opts: { query?: Query; body?: unknown; base?: string } = {},
	): Promise<T> {
		const url = new URL(path, opts.base ?? this.base);
		for (const [k, v] of Object.entries(opts.query ?? {})) {
			if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
		}
		const init: RequestInit = {
			method,
			headers: {
				Authorization: `Bearer ${this.key}`,
				Accept: "application/json",
				...(opts.body !== undefined ? { "Content-Type": "application/json" } : {}),
			},
			body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
		};
		const res = await fetch(url.toString(), init);
		const text = await res.text();
		let data: unknown = text;
		try {
			data = text ? JSON.parse(text) : null;
		} catch {
			/* keep raw text */
		}
		if (!res.ok) throw new FactoryError(res.status, data, `${method} ${url.pathname}`);
		return data as T;
	}
}

export interface Computer {
	id: string;
	name: string;
	status: string;
	providerType?: string;
	lastSeenAt?: number;
	remoteUser?: string;
}

// Plain names Allison and the skill use for the two Macs.
const MACHINE_ALIASES: Record<string, string> = {
	m2: "ember-mac-mini-m2",
	ember: "ember-mac-mini-m2",
	"ember m2": "ember-mac-mini-m2",
	m4: "ag-mac-mini-m4",
	allison: "ag-mac-mini-m4",
	"allison m4": "ag-mac-mini-m4",
};

export async function listComputers(f: Factory): Promise<Computer[]> {
	const d = await f.call<any>("GET", "/api/v0/computers");
	return (d.computers ?? d.items ?? d) as Computer[];
}

/** Resolve "M2", "M4", a computer name or an id to a computer. */
export async function resolveMachine(f: Factory, machine: string): Promise<Computer> {
	const computers = await listComputers(f);
	const want = MACHINE_ALIASES[machine.trim().toLowerCase()] ?? machine.trim();
	const hit = computers.find((c) => c.id === want || c.name.toLowerCase() === want.toLowerCase());
	if (!hit) {
		throw new Error(
			`Unknown machine "${machine}". Known: ${computers.map((c) => c.name).join(", ")}, or M2 and M4.`,
		);
	}
	return hit;
}

export function machineLabel(computers: Computer[], id?: string | null): string {
	if (!id) return "unrecorded";
	const c = computers.find((x) => x.id === id);
	if (!c) return `gone (${id.slice(0, 8)})`;
	if (c.name === "ember-mac-mini-m2") return "Ember M2";
	if (c.name === "ag-mac-mini-m4") return "Allison M4";
	return c.name;
}

export function isOnline(c: Computer, now = Date.now()): boolean {
	return c.status === "active" && !!c.lastSeenAt && now - c.lastSeenAt < 5 * 60_000;
}

/** Text of a message's text blocks, trimmed. */
export function messageText(m: any, max = 2000): string {
	const t = (m?.content ?? [])
		.filter((c: any) => c?.type === "text")
		.map((c: any) => c.text as string)
		.join("\n")
		.trim();
	return t.length > max ? `${t.slice(0, max)}...` : t;
}

/** Drop harness noise (system reminders, tool chatter) for human-readable history. */
export function isConversational(m: any): boolean {
	if (m.role !== "user" && m.role !== "assistant") return false;
	const t = messageText(m, 200000);
	if (!t) return false;
	if (m.role === "user" && /^<system-reminder>/.test(t)) return false;
	return true;
}

export const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
