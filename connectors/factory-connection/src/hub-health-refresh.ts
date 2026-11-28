import { z } from "zod";

const endpoint = "https://hq.expertpartners.com/api/campus/system-health";
const timeoutMs = 45_000;
const maxResponseBytes = 16_384;
const outcome = z.enum(["updated", "unavailable", "failed"]);
const responseSchema = z.object({
	sources: z.object({
		"failure-tracker": outcome,
		"change-log": outcome,
		"daily-health": outcome,
		hq: outcome,
		ep: outcome,
		ag: outcome,
	}),
});

export interface HubHealthRefreshEnv {
	HUB_SYSTEM_HEALTH_REFRESH_TOKEN?: string;
}

export class HubHealthRefreshError extends Error {
	readonly status: number;
	readonly upstreamStatus?: number;

	constructor(status: number, message: string, upstreamStatus?: number) {
		super(message);
		this.status = status;
		this.upstreamStatus = upstreamStatus;
	}
}

/** Fixed destination and server-held credential only. Never retry an uncertain POST. */
export async function refreshHubSystemHealth(env: HubHealthRefreshEnv, send: typeof fetch = fetch) {
	const token = env.HUB_SYSTEM_HEALTH_REFRESH_TOKEN;
	if (!token || token.length < 32 || /[\r\n]/.test(token)) {
		throw new HubHealthRefreshError(503, "Hub health refresh is not configured.");
	}
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), timeoutMs);
	try {
		const response = await send(endpoint, {
			method: "POST",
			headers: { Authorization: `Bearer ${token}` },
			redirect: "error",
			signal: controller.signal,
		});
		if (response.status !== 200) {
			// Do not read error bodies: they can contain credentials, identities or source text.
			await response.body?.cancel();
			if (response.status === 409)
				throw new HubHealthRefreshError(409, "Hub health refresh is already in progress.", 409);
			throw new HubHealthRefreshError(502, "Hub health refresh was refused or unavailable.", response.status);
		}
		const reader = response.body?.getReader();
		if (!reader) throw new HubHealthRefreshError(502, "Hub health refresh returned an invalid receipt.");
		const chunks: Uint8Array[] = [];
		let bytes = 0;
		try {
			for (;;) {
				const part = await reader.read();
				if (part.done) break;
				bytes += part.value.byteLength;
				if (bytes > maxResponseBytes)
					throw new HubHealthRefreshError(502, "Hub health refresh returned an invalid receipt.");
				chunks.push(part.value);
			}
		} finally {
			await reader.cancel();
		}
		const data = new Uint8Array(bytes);
		let offset = 0;
		for (const chunk of chunks) {
			data.set(chunk, offset);
			offset += chunk.byteLength;
		}
		const parsed = responseSchema.safeParse(JSON.parse(new TextDecoder().decode(data)));
		if (!parsed.success)
			throw new HubHealthRefreshError(502, "Hub health refresh returned an invalid receipt.");
		// Zod projects only the six enum outcomes, never upstream rows or other fields.
		return parsed.data;
	} catch (error) {
		if (error instanceof HubHealthRefreshError) throw error;
		throw new HubHealthRefreshError(
			controller.signal.aborted ? 504 : 502,
			controller.signal.aborted ? "Hub health refresh timed out; outcome is uncertain." : "Hub health refresh failed; outcome is uncertain.",
		);
	} finally {
		clearTimeout(timer);
	}
}
