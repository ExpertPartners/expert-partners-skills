import { driveFetch } from "../../brain-gateway/src/google.ts";
import { validPolicy, type WorkPolicy } from "./work-preflight.ts";

/** Resolve the existing owning sheet on every dispatch. KV supplies routing only.
 * No policy cache can silently outlive a founder decision or ownership change. */
export async function liveWorkPolicy(seed: WorkPolicy, key: string,
 read = driveFetch(key)): Promise<WorkPolicy> {
 const id = new URL(seed.source.url).pathname.match(/\/spreadsheets\/d\/([\w-]+)/)?.[1];
 if (!id) throw new Error("Invalid owning spreadsheet route");
 const get = async (path: string) => {
  const response = await read(path);
  if (!response.ok) throw new Error(`Owning record unavailable (${response.status})`);
  return await response.json() as any;
 };
 const metadata = `/drive/v3/files/${id}?fields=version&supportsAllDrives=true`;
 const before = await get(metadata);
 const data = await get(`/v4/spreadsheets/${id}/values/${encodeURIComponent("'Gap Build List'!K:T")}?valueRenderOption=UNFORMATTED_VALUE`);
 const after = await get(metadata);
 if (!before.version || before.version !== after.version) throw new Error("Owning record changed during preflight; retry against a stable revision");
 const items: WorkPolicy["items"] = [];
 const seen = new Set<string>();
 for (const row of (data.values ?? []).slice(1)) {
  if (!row[0]) continue;
  const [recovery, decision, implementation, owner, id, tests, aliases, installed, approved, evidence] = row;
  const session = typeof owner === "string" && owner.match(/^https:\/\/app\.factory\.ai\/sessions\/([\w-]+)$/)?.[1];
  if (row.length !== 10 || !session || !tests || seen.has(id)) throw new Error("Incomplete or duplicate owning disposition");
  seen.add(id);
  items.push({ id, aliases: JSON.parse(aliases), sourceRecovery: recovery, decisionUrl: decision,
   ownerSession: session, implementation, installed, replacementApproved: approved, evidence: JSON.parse(evidence) });
 }
 const policy = {version: 1 as const, source: {url: seed.source.url, revision: String(after.version)}, items};
 if (!items.length || !validPolicy(policy)) throw new Error("Invalid live owning dispositions");
 return policy;
}
