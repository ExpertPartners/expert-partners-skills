// One tool registry serves both the MCP connector (/mcp) and the Hub HTTP endpoint (/api/tools).
import { z } from "zod";
import {
	type Computer,
	Factory,
	FactoryError,
	isConversational,
	isOnline,
	listComputers,
	machineLabel,
	messageText,
	READINESS_BASE,
	resolveComputer,
	resolveMachine,
	sleep,
} from "./factory";

export interface ToolEnv {
	FACTORY_API_KEY: string;
	AUTOMATION_WEBHOOKS?: string;
}

export interface ToolDef {
	name: string;
	description: string;
	schema: z.ZodObject<any>;
	readOnly?: boolean;
	run: (args: any, f: Factory, env: ToolEnv) => Promise<unknown>;
}

// Defaults set by Allison: Auto Model and High autonomy.
export const DEFAULT_SETTINGS = { model: "auto", autonomyLevel: "high", interactionMode: "auto" } as const;

const effort = z.enum(["none", "dynamic", "off", "minimal", "low", "medium", "high", "xhigh", "max"]);
const tag = z.object({ name: z.string().min(1), metadata: z.record(z.string(), z.string()).optional() });
const machine = z
	.string()
	.describe('Which Mac. "M2" (Ember M2, browser and visible work) or "M4" (Allison M4, invisible background only), a computer name, or a computer id.');

const computer = z
	.string()
	.describe('Any computer the Factory API returns, listed or unlisted: its id or name. "M2" and "M4" also work.');

const settingsShape = {
	model: z.string().optional().describe('Model id. Default "auto" (Auto Model / Factory Router).'),
	reasoningEffort: effort.optional(),
	interactionMode: z.enum(["auto", "spec", "agi", "mission"]).optional().describe('Default "auto". Use "spec" when architecture is unclear, "mission" for multi-feature work.'),
	autonomyLevel: z.enum(["off", "low", "medium", "high"]).optional().describe('Default "high".'),
	specModeModel: z.string().optional(),
	specModeReasoningEffort: effort.optional(),
	tags: z.array(tag).optional(),
	worktree: z
		.object({
			repoRoot: z.string(),
			branch: z.string().optional(),
			lifecycle: z.enum(["ephemeral", "persistent"]).optional(),
			path: z.string().optional(),
			parentWorktreePath: z.string().optional(),
			setupProfileId: z.string().optional(),
		})
		.optional(),
	enabledToolIds: z.array(z.string()).optional(),
	disabledToolIds: z.array(z.string()).optional(),
	restrictToolIds: z.array(z.string()).optional(),
	compactionModel: z.string().optional(),
	compactionThresholdCheckEnabled: z.boolean().optional(),
};
const createOnly = {
	toolExecutionMode: z.enum(["direct_only", "script_only"]).optional(),
	allowSubagentsInScripts: z.boolean().optional(),
	systemPrompt: z.string().optional().describe("Appended to the Droid preset system prompt."),
};

const image = z.object({
	data: z.string().describe("Base64 data"),
	mediaType: z.enum(["image/jpeg", "image/png", "image/gif", "image/webp"]),
});
const file = z.object({
	kind: z.enum(["pdf", "text"]),
	data: z.string().describe("Base64 for pdf, plain text for text"),
	name: z.string().optional(),
});

function messageBody(a: { text: string; images?: any[]; files?: any[]; computerId?: string; sender?: any }) {
	const body: any = { text: a.text };
	if (a.images?.length) body.images = a.images.map((i) => ({ type: "base64", data: i.data, mediaType: i.mediaType }));
	if (a.files?.length) {
		body.files = a.files.map((x) =>
			x.kind === "pdf"
				? { type: "base64", mediaType: "application/pdf", data: x.data, ...(x.name ? { name: x.name } : {}) }
				: { type: "text", mediaType: "text/plain", data: x.data, ...(x.name ? { name: x.name } : {}) },
		);
	}
	if (a.computerId) body.computerId = a.computerId;
	if (a.sender) body.sender = a.sender;
	return body;
}

function pickSettings(a: Record<string, unknown>, keys: string[]) {
	const out: Record<string, unknown> = {};
	for (const k of keys) if (a[k] !== undefined) out[k] = a[k];
	return out;
}

function compactMessages(msgs: any[], full: boolean) {
	return msgs
		.filter((m) => full || isConversational(m))
		.map((m) => ({
			id: m.id,
			role: m.role,
			at: new Date(m.createdAt).toISOString(),
			source: m.userMessageSource ?? undefined,
			sender: m.sender ?? undefined,
			text: messageText(m, full ? 20000 : 3000),
		}));
}

async function sessionsPage(f: Factory, limit = 100, cursor?: string, computerId?: string) {
	return f.call<any>("GET", "/api/v0/sessions", { query: { limit, cursor, computerId } });
}

async function recentSessions(f: Factory, pages: number) {
	const all: any[] = [];
	let cursor: string | undefined;
	for (let i = 0; i < pages; i++) {
		const d = await sessionsPage(f, 100, cursor);
		all.push(...(d.sessions ?? []));
		if (!d.pagination?.hasMore || !d.pagination?.nextCursor) break;
		cursor = d.pagination.nextCursor;
	}
	return all;
}

/** Workstream orchestrators and missions are parents whose children carry mission-v2 tags. */
async function childrenOf(f: Factory, id: string) {
	try {
		const d = await f.call<any>("GET", `/api/v0/sessions/${id}/children`, {
			query: { includeAttention: "true", includeUsage: "true" },
		});
		return (d.sessions ?? []) as any[];
	} catch {
		return [];
	}
}

function kindOf(children: any[]): "workstream-or-mission" | "has-subagents" | "single" {
	if (!children.length) return "single";
	const tags = children.flatMap((c) => (c.tags ?? []).map((t: any) => t.name));
	if (tags.includes("mission-v2")) return "workstream-or-mission";
	return "has-subagents";
}

async function lastAssistantText(f: Factory, id: string) {
	const d = await f.call<any>("GET", `/api/v0/sessions/${id}/messages`, { query: { limit: 30, role: "assistant" } });
	// The messages API returns the newest messages first.
	const last = (d.messages ?? []).find((m: any) => messageText(m));
	return last ? messageText(last, 6000) : "";
}

async function watch(f: Factory, id: string, waitSeconds: number) {
	const deadline = Date.now() + Math.min(Math.max(waitSeconds, 0), 290) * 1000;
	let s = await f.call<any>("GET", `/api/v0/sessions/${id}`);
	// Give a just-posted message a moment to flip the session to pending or running.
	if (s.status === "idle" && waitSeconds > 0) {
		await sleep(3000);
		s = await f.call<any>("GET", `/api/v0/sessions/${id}`);
	}
	while (s.status !== "idle" && Date.now() < deadline) {
		await sleep(5000);
		s = await f.call<any>("GET", `/api/v0/sessions/${id}`);
	}
	const done = s.status === "idle";
	let attention: unknown = null;
	if (!done && s.parent_session_id) {
		const sib = await childrenOf(f, s.parent_session_id);
		attention = sib.find((c) => c.sessionId === id)?.attention ?? null;
	}
	return {
		sessionId: id,
		title: s.title,
		status: s.status,
		done,
		messageCount: s.messageCount,
		attention,
		lastReply: done ? await lastAssistantText(f, id) : undefined,
		next: done ? undefined : "Still running. Call watch_session again with this sessionId.",
		link: `https://app.factory.ai/sessions/${id}`,
	};
}

/** A new session takes a moment to register on its Mac; the first message can 404 until then. */
async function postFirstMessage(f: Factory, sessionId: string, body: unknown) {
	for (let i = 0; ; i++) {
		try {
			return await f.call("POST", `/api/v0/sessions/${sessionId}/messages`, { body });
		} catch (e) {
			if (!(e instanceof FactoryError) || e.status !== 404 || i >= 7) throw e;
			await sleep(1500);
		}
	}
}

function webhooks(env: ToolEnv): Record<string, { url: string; secret: string; description?: string }> {
	if (!env.AUTOMATION_WEBHOOKS) return {};
	try {
		return JSON.parse(env.AUTOMATION_WEBHOOKS);
	} catch {
		return {};
	}
}

const id = z.string().describe("Session id");

export const TOOLS: ToolDef[] = [
	// ---------- Sessions API, all ten actions ----------
	{
		name: "list_sessions",
		description: "List Factory sessions, newest first, with cursor paging. Optionally only one machine.",
		readOnly: true,
		schema: z.object({
			limit: z.number().int().min(1).max(100).optional(),
			cursor: z.string().optional(),
			machine: machine.optional(),
		}),
		run: async (a, f) => {
			const computers = await listComputers(f, true);
			const c = a.machine ? await resolveComputer(f, a.machine) : undefined;
			const d = await sessionsPage(f, a.limit ?? 50, a.cursor, c?.id);
			return {
				sessions: (d.sessions ?? []).map((s: any) => ({
					...s,
					machine: machineLabel(computers, s.computerId),
					updated: new Date(s.updatedAt).toISOString(),
				})),
				pagination: d.pagination,
			};
		},
	},
	{
		name: "create_session",
		description:
			"Start a Factory session on a named Mac with full settings. Defaults are Auto Model and High autonomy. Name bounded jobs 'Section - Mission' and put that name as the first line of firstMessage. Optional firstMessage sends the work right away.",
		schema: z.object({
			machine,
			cwd: z.string().optional().describe("Working directory on that Mac"),
			firstMessage: z.string().optional(),
			...settingsShape,
			...createOnly,
		}),
		run: async (a, f) => {
			const c = await resolveMachine(f, a.machine);
			const sessionSettings: any = {
				...DEFAULT_SETTINGS,
				...pickSettings(a, [...Object.keys(settingsShape), "toolExecutionMode", "allowSubagentsInScripts"]),
			};
			if (a.systemPrompt) sessionSettings.systemPrompt = { type: "preset", preset: "droid", append: a.systemPrompt };
			const s = await f.call<any>("POST", "/api/v0/sessions", {
				body: { computerId: c.id, ...(a.cwd ? { cwd: a.cwd } : {}), sessionSettings },
			});
			let message: unknown;
			if (a.firstMessage) {
				message = await postFirstMessage(f, s.sessionId, { text: a.firstMessage });
			}
			return { ...s, machine: c.name, settings: sessionSettings, message, link: `https://app.factory.ai/sessions/${s.sessionId}` };
		},
	},
	{
		name: "get_session",
		description: "Get one session with settings, artifacts (PRs, issues, pages) and credits.",
		readOnly: true,
		schema: z.object({ sessionId: id, computerId: z.string().optional() }),
		run: (a, f) => f.call("GET", `/api/v0/sessions/${a.sessionId}`, { query: { computerId: a.computerId } }),
	},
	{
		name: "update_session",
		description:
			"Change a session's settings, including tags and archivedAt. Allison archives sessions herself, so do not archive one unless she asks. archive=true sets archivedAt to now, archive=false clears it. Tested 2026-11-09, archivedAt set by API is stored by Factory but does not move the session to Archived in the Factory app.",
		schema: z.object({ sessionId: id, archive: z.boolean().optional(), archivedAt: z.string().optional(), ...settingsShape }),
		run: (a, f) => {
			const sessionSettings: any = pickSettings(a, [...Object.keys(settingsShape), "archivedAt"]);
			if (a.archive === true) sessionSettings.archivedAt = new Date().toISOString();
			if (a.archive === false) sessionSettings.archivedAt = "";
			return f.call("PATCH", `/api/v0/sessions/${a.sessionId}`, { body: { sessionSettings } });
		},
	},
	{
		name: "delete_session",
		description: "Permanently delete a session.",
		schema: z.object({ sessionId: id, computerId: z.string().optional() }),
		run: async (a, f) => {
			await f.call("DELETE", `/api/v0/sessions/${a.sessionId}`, { query: { computerId: a.computerId } });
			return { deleted: a.sessionId };
		},
	},
	{
		name: "list_children",
		description:
			"List the sessions a parent started (Workstream agents, mission agents, subagents) with what each waits on (attention) and usage.",
		readOnly: true,
		schema: z.object({
			sessionId: id,
			includeAttention: z.boolean().optional(),
			includeUsage: z.boolean().optional(),
			includeArtifacts: z.boolean().optional(),
		}),
		run: (a, f) =>
			f.call("GET", `/api/v0/sessions/${a.sessionId}/children`, {
				query: {
					includeAttention: String(a.includeAttention ?? true),
					includeUsage: String(a.includeUsage ?? true),
					includeArtifacts: String(a.includeArtifacts ?? false),
				},
			}),
	},
	{
		name: "interrupt_session",
		description: "Stop a running session's current turn. Safe if already idle.",
		schema: z.object({ sessionId: id }),
		run: (a, f) => f.call("POST", `/api/v0/sessions/${a.sessionId}/interrupt`),
	},
	{
		name: "read_messages",
		description:
			"Read a session's message history, newest first; pass the cursor for older pages. By default returns only readable user and assistant turns; set full=true for every message including tool calls. Works when the session's Mac is offline (Session Contents Sync is on).",
		readOnly: true,
		schema: z.object({
			sessionId: id,
			limit: z.number().int().min(1).max(200).optional(),
			cursor: z.string().optional(),
			role: z.enum(["user", "assistant", "tool"]).optional(),
			full: z.boolean().optional(),
		}),
		run: async (a, f) => {
			const d = await f.call<any>("GET", `/api/v0/sessions/${a.sessionId}/messages`, {
				query: { limit: a.limit ?? 50, cursor: a.cursor, role: a.role },
			});
			return { messages: compactMessages(d.messages ?? [], !!a.full), pagination: d.pagination };
		},
	},
	{
		name: "post_message",
		description:
			"Send a message to a session, with optional images and PDF or text files. The session's Mac must be online, otherwise Factory answers 503 and nothing is queued.",
		schema: z.object({
			sessionId: id,
			text: z.string(),
			images: z.array(image).optional(),
			files: z.array(file).optional(),
			computerId: z.string().optional(),
		}),
		run: (a, f) => f.call("POST", `/api/v0/sessions/${a.sessionId}/messages`, { body: messageBody(a) }),
	},
	{
		name: "get_message",
		description: "Get one message by id.",
		readOnly: true,
		schema: z.object({ sessionId: id, messageId: z.string() }),
		run: (a, f) => f.call("GET", `/api/v0/sessions/${a.sessionId}/messages/${a.messageId}`),
	},

	// ---------- Helpers ----------
	{
		name: "start_and_watch",
		description:
			"Create a session on a Mac, send the work, and wait until it finishes. Name it on the first line as Section - Mission with an exact sidebar section, and ask it to end with Ready to archive (up to waitSeconds, default 45, max 290). Returns the final reply, or the sessionId to keep watching with watch_session. Defaults Auto Model and High autonomy.",
		schema: z.object({
			machine,
			message: z.string().describe("The full brief. First line is the session name, 'Section - Mission'."),
			cwd: z.string().optional(),
			waitSeconds: z.number().int().min(0).max(290).optional(),
			...settingsShape,
		}),
		run: async (a, f) => {
			const c = await resolveMachine(f, a.machine);
			if (!isOnline(c)) throw new Error(`${c.name} is offline or asleep. Factory cannot reach it, so nothing was started.`);
			const sessionSettings = { ...DEFAULT_SETTINGS, ...pickSettings(a, Object.keys(settingsShape)) };
			const s = await f.call<any>("POST", "/api/v0/sessions", {
				body: { computerId: c.id, ...(a.cwd ? { cwd: a.cwd } : {}), sessionSettings },
			});
			await postFirstMessage(f, s.sessionId, { text: a.message });
			return { machine: c.name, ...(await watch(f, s.sessionId, a.waitSeconds ?? 45)) };
		},
	},
	{
		name: "watch_session",
		description: "Wait for a session to finish (up to waitSeconds, default 45, max 290) and return its final reply.",
		readOnly: true,
		schema: z.object({ sessionId: id, waitSeconds: z.number().int().min(0).max(290).optional() }),
		run: (a, f) => watch(f, a.sessionId, a.waitSeconds ?? 45),
	},
	{
		name: "whats_running",
		description:
			"What every session is doing right now: running or pending sessions, sessions updated in the last N hours, which Mac each is on, whether each Mac is online, and Workstream or mission agents waiting on Allison.",
		readOnly: true,
		schema: z.object({ hours: z.number().min(1).max(168).optional() }),
		run: async (a, f) => {
			const since = Date.now() - (a.hours ?? 12) * 3600_000;
			const [computers, sessions] = await Promise.all([listComputers(f), recentSessions(f, 2)]);
			const recent = sessions.filter((s) => s.updatedAt >= since || s.status !== "idle");
			// Live status comes from the detail call; the list can lag.
			const detailed = await Promise.all(
				recent.slice(0, 25).map(async (s) => {
					try {
						return { ...s, ...(await f.call<any>("GET", `/api/v0/sessions/${s.sessionId}`)) };
					} catch {
						return s;
					}
				}),
			);
			const parents = await Promise.all(
				detailed.slice(0, 12).map(async (s) => ({ s, kids: await childrenOf(f, s.sessionId) })),
			);
			const waiting = parents.flatMap(({ s, kids }) =>
				kids.filter((k) => k.attention).map((k) => ({ parent: s.title, agent: k.title, sessionId: k.sessionId, attention: k.attention })),
			);
			return {
				machines: computers.map((c: Computer) => ({ name: machineLabel(computers, c.id), online: isOnline(c), lastSeen: c.lastSeenAt ? new Date(c.lastSeenAt).toISOString() : null })),
				active: detailed.filter((s) => s.status !== "idle").map((s) => ({ title: s.title, status: s.status, machine: machineLabel(computers, s.computerId), sessionId: s.sessionId })),
				recentlyUpdated: detailed.map((s) => ({
					title: s.title,
					status: s.status,
					machine: machineLabel(computers, s.computerId),
					updated: new Date(s.updatedAt).toISOString(),
					kind: kindOf(parents.find((p) => p.s.sessionId === s.sessionId)?.kids ?? []),
					sessionId: s.sessionId,
				})),
				waitingOnAllison: waiting,
			};
		},
	},
	{
		name: "find_owner",
		description:
			"Find the session or Workstream that already owns a mission before starting new work. Matches titles, marks Workstream orchestrators and missions, and returns each top match's recent assignments so you can tell a new assignment from a duplicate.",
		readOnly: true,
		schema: z.object({
			query: z.string().describe("Mission words, section name or program name"),
			pages: z.number().int().min(1).max(10).optional().describe("How many pages of 100 sessions to search, default 5"),
		}),
		run: async (a, f) => {
			const words = a.query.toLowerCase().split(/[^a-z0-9]+/).filter((w: string) => w.length > 2);
			const [computers, sessions] = await Promise.all([listComputers(f), recentSessions(f, a.pages ?? 5)]);
			const scored = sessions
				.map((s) => {
					const t = (s.title ?? "").toLowerCase();
					const hits = words.filter((w: string) => t.includes(w)).length;
					return { s, score: words.length ? hits / words.length : 0 };
				})
				.filter((x) => x.score > 0)
				.sort((x, y) => y.score - x.score || y.s.updatedAt - x.s.updatedAt)
				.slice(0, 8);
			const out = await Promise.all(
				scored.map(async ({ s, score }) => {
					const kids = await childrenOf(f, s.sessionId);
					const kind = kindOf(kids);
					let recentAssignments: unknown[] = [];
					if (score >= 0.5) {
						const d = await f.call<any>("GET", `/api/v0/sessions/${s.sessionId}/messages`, { query: { limit: 60, role: "user" } });
						recentAssignments = compactMessages(d.messages ?? [], false).slice(0, 5);
					}
					return {
						title: s.title,
						sessionId: s.sessionId,
						score: Math.round(score * 100) / 100,
						kind,
						agents: kids.map((k) => ({ title: k.title, status: k.status, attention: k.attention ?? null })),
						machine: machineLabel(computers, s.computerId),
						updated: new Date(s.updatedAt).toISOString(),
						recentAssignments,
						link: `https://app.factory.ai/sessions/${s.sessionId}`,
					};
				}),
			);
			return {
				matches: out,
				searched: sessions.length,
				hint: "kind workstream-or-mission means a Workstream orchestrator or mission that owns continuing work. Send new work for it there with post_message.",
			};
		},
	},

	// ---------- Computers ----------
	{
		name: "list_computers",
		description: "List Factory computers with online state.",
		readOnly: true,
		schema: z.object({ includeUnlisted: z.boolean().optional() }),
		run: async (a, f) => {
			const d = await f.call<any>("GET", "/api/v0/computers", { query: { includeUnlisted: a.includeUnlisted ? "true" : undefined } });
			const list: Computer[] = d.computers ?? [];
			return list.map((c) => ({ id: c.id, name: c.name, label: machineLabel(list, c.id), status: c.status, online: isOnline(c), providerType: c.providerType, lastSeenAt: c.lastSeenAt ? new Date(c.lastSeenAt).toISOString() : null, remoteUser: c.remoteUser }));
		},
	},
	{
		name: "get_computer",
		description: "Get one computer by id or name, including unlisted Factory cloud computers. M2 and M4 also work.",
		readOnly: true,
		schema: z.object({ machine: computer }),
		run: async (a, f) => f.call("GET", `/api/v0/computers/${(await resolveComputer(f, a.machine)).id}`),
	},
	{
		name: "computer_providers",
		description: "List providers available for new managed computers.",
		readOnly: true,
		schema: z.object({}),
		run: (_a, f) => f.call("GET", "/api/v0/computers/providers"),
	},
	{
		name: "computer_metrics",
		description: "CPU, memory and disk metrics for a Factory-managed computer. Not supported for Macs connected through Remote Control.",
		readOnly: true,
		schema: z.object({ machine: computer, start: z.string().optional() }),
		run: async (a, f) => f.call("GET", `/api/v0/computers/${(await resolveComputer(f, a.machine)).id}/metrics`, { query: { start: a.start } }),
	},
	{
		name: "create_computer",
		description: "Create a Factory-managed Droid Computer. Routine work does not need one, the Macs cover it.",
		schema: z.object({
			name: z.string(),
			provider: z.string().optional(),
			repos: z.array(z.string()).optional(),
			autoInstallDeps: z.boolean().optional(),
		}),
		run: (a, f) => f.call("POST", "/api/v0/computers", { body: a }),
	},
	{
		name: "update_computer",
		description: "Rename a computer or change its remote user.",
		schema: z.object({ machine: computer, name: z.string().optional(), remoteUser: z.string().optional() }),
		run: async (a, f) => {
			const c = await resolveComputer(f, a.machine);
			return f.call("PATCH", `/api/v0/computers/${c.id}`, { body: pickSettings(a, ["name", "remoteUser"]) });
		},
	},
	{
		name: "delete_computer",
		description: "Delete a computer registration.",
		schema: z.object({ machine: computer }),
		run: async (a, f) => f.call("DELETE", `/api/v0/computers/${(await resolveComputer(f, a.machine)).id}`),
	},
	{
		name: "refresh_computer",
		description: "Refresh a managed computer.",
		schema: z.object({ machine: computer }),
		run: async (a, f) => f.call("POST", `/api/v0/computers/${(await resolveComputer(f, a.machine)).id}/refresh`),
	},
	{
		name: "restart_computer",
		description: "Restart a managed computer.",
		schema: z.object({ machine: computer }),
		run: async (a, f) => f.call("POST", `/api/v0/computers/${(await resolveComputer(f, a.machine)).id}/restart`, { body: {} }),
	},
	{
		name: "retry_install_deps",
		description: "Retry the install-dependencies step on a managed computer.",
		schema: z.object({ machine: computer }),
		run: async (a, f) => f.call("POST", `/api/v0/computers/${(await resolveComputer(f, a.machine)).id}/install-deps`),
	},

	// ---------- CI Automations API ----------
	{ name: "ci_scan", description: "Scan repositories for Factory CI workflows.", readOnly: true, schema: z.object({}), run: (_a, f) => f.call("GET", "/api/v0/automations/ci/scan") },
	{ name: "ci_list_jobs", description: "List CI automation jobs.", readOnly: true, schema: z.object({}), run: (_a, f) => f.call("GET", "/api/v0/automations/ci/jobs") },
	{ name: "ci_list_repositories", description: "List CI-eligible repositories.", readOnly: true, schema: z.object({}), run: (_a, f) => f.call("GET", "/api/v0/automations/ci/repositories") },
	{ name: "ci_list_repository_owners", description: "List CI repository owners.", readOnly: true, schema: z.object({}), run: (_a, f) => f.call("GET", "/api/v0/automations/ci/repository-owners") },
	{ name: "ci_list_runs", description: "List GitHub Actions runs for CI automation workflows.", readOnly: true, schema: z.object({}), run: (_a, f) => f.call("GET", "/api/v0/automations/ci/runs") },
	{
		name: "ci_open_workflow_pr",
		description: "Open a pull request that creates, edits or deletes a Factory CI workflow. body is passed to POST /api/v0/automations/ci/edit as is.",
		schema: z.object({ body: z.record(z.string(), z.any()) }),
		run: (a, f) => f.call("POST", "/api/v0/automations/ci/edit", { body: a.body }),
	},

	// ---------- Webhook automation triggers ----------
	{
		name: "list_automation_webhooks",
		description: "List the Factory webhook automations this connection can trigger (names only, never secrets).",
		readOnly: true,
		schema: z.object({}),
		run: async (_a, _f, env) => Object.entries(webhooks(env)).map(([name, w]) => ({ name, description: w.description ?? "" })),
	},
	{
		name: "trigger_automation_webhook",
		description: "Start a Factory webhook automation run by name with a JSON payload. Factory answers 200 when accepted; the run itself shows in the automation's Events feed.",
		schema: z.object({ name: z.string(), payload: z.record(z.string(), z.any()).optional() }),
		run: async (a, _f, env) => {
			const w = webhooks(env)[a.name];
			if (!w) throw new Error(`No webhook automation named "${a.name}". Known: ${Object.keys(webhooks(env)).join(", ") || "none yet"}.`);
			const res = await fetch(w.url, {
				method: "POST",
				headers: { "Content-Type": "application/json", "X-Webhook-Secret": w.secret },
				body: JSON.stringify(a.payload ?? {}),
			});
			return { name: a.name, status: res.status, accepted: res.status === 200 };
		},
	},

	// ---------- Agent Readiness ----------
	{
		name: "list_readiness_reports",
		description: "List Agent Readiness reports for the organization's repositories, newest first.",
		readOnly: true,
		schema: z.object({ repoId: z.string().optional(), limit: z.number().int().min(1).max(100).optional(), startAfter: z.string().optional() }),
		run: (a, f) =>
			f.call("GET", "/api/organization/agent-readiness-reports", { base: READINESS_BASE, query: { repoId: a.repoId, limit: a.limit ?? 10, startAfter: a.startAfter } }),
	},

	// ---------- AutoWiki ----------
	{ name: "wiki_list", description: "List the latest AutoWiki runs.", readOnly: true, schema: z.object({}), run: (_a, f) => f.call("GET", "/api/v0/wiki") },
	{
		name: "wiki_create",
		description: "Create an AutoWiki run. body is passed to POST /api/v0/wiki as is.",
		schema: z.object({ body: z.record(z.string(), z.any()) }),
		run: (a, f) => f.call("POST", "/api/v0/wiki", { body: a.body }),
	},
	{ name: "wiki_get", description: "Get an AutoWiki run.", readOnly: true, schema: z.object({ wikiRunId: z.string() }), run: (a, f) => f.call("GET", `/api/v0/wiki/${a.wikiRunId}`) },
	{
		name: "wiki_history",
		description: "List AutoWiki run history for a repository URL.",
		readOnly: true,
		schema: z.object({ repoUrl: z.string() }),
		run: (a, f) => f.call("GET", `/api/v0/wiki/history/${encodeURIComponent(a.repoUrl)}`),
	},
	{
		name: "wiki_page",
		description: "Get one AutoWiki page.",
		readOnly: true,
		schema: z.object({ wikiRunId: z.string(), pageId: z.string() }),
		run: (a, f) => f.call("GET", `/api/v0/wiki/${a.wikiRunId}/pages/${encodeURIComponent(a.pageId)}`),
	},
	{
		name: "wiki_search",
		description: "Search an AutoWiki run.",
		readOnly: true,
		schema: z.object({ wikiRunId: z.string(), q: z.string() }),
		run: (a, f) => f.call("GET", `/api/v0/wiki/${a.wikiRunId}/search`, { query: { q: a.q, query: a.q } }),
	},
	{
		name: "wiki_privacy",
		description: "Update an AutoWiki run's privacy level. body is passed as is.",
		schema: z.object({ wikiRunId: z.string(), body: z.record(z.string(), z.any()) }),
		run: (a, f) => f.call("POST", `/api/v0/wiki/${a.wikiRunId}/privacy`, { body: a.body }),
	},
	{ name: "wiki_delete", description: "Delete an AutoWiki run.", schema: z.object({ wikiRunId: z.string() }), run: (a, f) => f.call("DELETE", `/api/v0/wiki/${a.wikiRunId}`) },
];

export function findTool(name: string) {
	return TOOLS.find((t) => t.name === name);
}

/** Run a tool by name with validated args. Errors come back as data, never with secrets. */
export async function runTool(name: string, args: unknown, env: ToolEnv) {
	const t = findTool(name);
	if (!t) return { ok: false as const, status: 404, error: `Unknown tool ${name}` };
	const parsed = t.schema.safeParse(args ?? {});
	if (!parsed.success) return { ok: false as const, status: 400, error: parsed.error.message };
	try {
		const result = await t.run(parsed.data, new Factory(env.FACTORY_API_KEY), env);
		return { ok: true as const, status: 200, result };
	} catch (e) {
		if (e instanceof FactoryError) {
			return { ok: false as const, status: e.status === 401 ? 502 : e.status, error: e.message, detail: e.body };
		}
		return { ok: false as const, status: 500, error: (e as Error).message };
	}
}
