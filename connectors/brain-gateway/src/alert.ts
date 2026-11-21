// Failure alert for the daily Drive brain check (Decision Log, Nov 20 2026, Business Brain connection monitoring).
// Texts Allison through the existing Sendblue line only when a check fails, and once when it recovers.
// The text names failed checks and their short error codes. It never carries document text.
import type { HealthResult } from "./health.ts";

export interface AlertEnv {
	SENDBLUE_API_KEY_ID?: string;
	SENDBLUE_API_SECRET?: string;
	ALERT_TO?: string;
	ALERT_FROM?: string;
}

const SEND_URL = "https://api.sendblue.co/api/send-message";
const STATE_KEY = "alert:state";

export function alertText(result: HealthResult, recovered: boolean): string {
	if (recovered) return "Drive brain gateway is healthy again. Today's check passed.";
	const failed = result.checks.filter((c) => !c.ok).slice(0, 4);
	const lines = failed.map((c) => `${c.name}: ${c.detail}`.slice(0, 110));
	return `Drive brain gateway check failed (${result.checkedAt.slice(0, 16).replace("T", " ")} UTC). ${lines.join(" | ")}. Claude, ChatGPT, Factory, Ember and the Hub may be reading stale or no brain until this is fixed.`;
}

/** Sends at most one text per run. Returns what happened so the cron can log it. */
export async function maybeAlert(kv: KVNamespace, env: AlertEnv, result: HealthResult, doFetch: typeof fetch = fetch): Promise<"sent" | "recovered" | "quiet" | "unconfigured" | "send_failed"> {
	const previous = await kv.get(STATE_KEY);
	const wasFailing = previous === "failing";
	if (result.ok && !wasFailing) return "quiet";
	if (!env.SENDBLUE_API_KEY_ID || !env.SENDBLUE_API_SECRET || !env.ALERT_TO || !env.ALERT_FROM) return "unconfigured";
	const recovered = result.ok && wasFailing;
	try {
		const res = await doFetch(SEND_URL, {
			method: "POST",
			headers: { "content-type": "application/json", "sb-api-key-id": env.SENDBLUE_API_KEY_ID, "sb-api-secret-key": env.SENDBLUE_API_SECRET, "user-agent": "brain-gateway-alert" },
			body: JSON.stringify({ number: env.ALERT_TO, from_number: env.ALERT_FROM, content: alertText(result, recovered) }),
		});
		if (!res.ok) return "send_failed";
	} catch {
		return "send_failed";
	}
	// State changes only after a confirmed send, so a refused text is retried on the next run.
	await kv.put(STATE_KEY, result.ok ? "ok" : "failing");
	return recovered ? "recovered" : "sent";
}
