import { messageText, type Factory } from "./factory.ts";
import { liveWorkPolicy } from "./live-work-policy.ts";
import type { WorkPolicy } from "./work-preflight.ts";

/** The order is executable, not an instruction an agent must remember.
 * These are reads of existing ownership, marketplace and gap records only. */
export async function orderedWorkPolicy(seed: WorkPolicy, key: string,
 factory: Pick<Factory, "call">, fetchImpl: typeof fetch = fetch,
 readGaps = liveWorkPolicy): Promise<WorkPolicy> {
 const owner = seed.source.companyToolBuilderSession;
 if (!owner || !/^[a-zA-Z0-9-]+$/.test(owner)) throw new Error("Existing build-owner route missing");
 const assignment = await factory.call<any>("GET", `/api/v0/sessions/${owner}/messages`, {query:{limit:100,role:"assistant"}});
 if (!Array.isArray(assignment.messages)) throw new Error("Existing build assignments unavailable");
 const ownerEvidence = assignment.messages.map((m: any) => ({id:m.id,text:messageText(m,6000)})).filter((m: any) => m.text);
 const marketplace = await fetchImpl("https://raw.githubusercontent.com/ExpertPartners/expert-partners-skills/main/tools/skill-map/skills-graph.json", {signal:AbortSignal.timeout(15000)});
 if (!marketplace.ok) throw new Error("Existing marketplace unavailable");
 const graph = await marketplace.json() as any;
 if (!Array.isArray(graph.nodes) || !graph.nodes.length) throw new Error("Existing marketplace incomplete");
 const policy = await readGaps(seed,key);
 return {...policy,checks:[
  {stage:"company_tool_builder",evidence:{sessionId:owner,messages:ownerEvidence}},
  {stage:"skills_marketplace",evidence:{revision:graph.generatedFrom,capabilities:graph.nodes.map((n:any)=>({id:n.id,outcome:n.subtitle,source:n.source}))}},
  {stage:"gap_build_list",evidence:policy.source},
 ]};
}
