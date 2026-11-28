import { driveFetch } from "../../brain-gateway/src/google.ts";
import { validPolicy, type WorkPolicy } from "./work-preflight.ts";
import { decisionDocumentId, parseSourceDecisions, sourceDecisionDigest, type RecoveryDecisionState } from "./source-decision-authority.ts";

// Parsed evidence is reused only after a fresh read proves the same Drive version.
// An unavailable/new version never reuses cached permission to reopen recovery.
const authorityCache=new Map<string,{version:string;states:Map<string,RecoveryDecisionState>}>();

/** Resolve the existing owning sheet on every dispatch. KV supplies routing only.
 * No policy cache can silently outlive a founder decision or ownership change. */
export async function liveWorkPolicy(seed: WorkPolicy, key: string,
 providedRead?: ReturnType<typeof driveFetch>): Promise<WorkPolicy> {
 const read=providedRead??driveFetch(key);
 const id = new URL(seed.source.url).pathname.match(/\/spreadsheets\/d\/([\w-]+)/)?.[1];
 if (!id) throw new Error("Invalid owning spreadsheet route");
 const get = async (path: string) => {
  const response = await read(path);
  if (!response.ok) throw new Error(`Owning record unavailable (${response.status})`);
  return await response.json() as any;
 };
 const metadata = `/drive/v3/files/${id}?fields=version&supportsAllDrives=true`;
 const before = await get(metadata);
 const authorityUrl=seed.source.decisionLogUrl??"";
 const founder=seed.source.founderDecisionActor??"";
 const digest=seed.source.decisionReceiptDigest??"";
 const protectedStates=new Map((seed.source.decisionRecoveryFallback??[]).map(({id,...state})=>[id,state]));
 const cacheKey=authorityUrl+"\n"+founder+"\n"+digest+"\n"+JSON.stringify([...protectedStates]);
 const cached=providedRead?undefined:authorityCache.get(cacheKey);
 let candidate: {version:string;states:Map<string,RecoveryDecisionState>}|undefined;
 let authorityMetadata="";
 try {
  const logId=decisionDocumentId(authorityUrl);
  if (!founder || !/^[a-f0-9]{64}$/.test(digest)) throw new Error("Founder authority configuration missing");
  authorityMetadata=`/drive/v3/files/${logId}?fields=version&supportsAllDrives=true`;
  const logBefore=await get(authorityMetadata);
  if (typeof logBefore.version!=="string" || !logBefore.version) throw new Error("Decision version missing");
  if (cached?.version===logBefore.version) candidate=cached;
  else {
   const response=await read(`/drive/v3/files/${logId}/export?mimeType=text%2Fplain`);
   if (!response.ok) throw new Error("Decision authority unavailable");
   const text=await response.text();
   if (await sourceDecisionDigest(text)!==digest) throw new Error("Decision receipt history does not match trusted routing record");
   candidate={version:logBefore.version,states:parseSourceDecisions(text,authorityUrl,founder)};
  }
  if (!candidate) throw new Error("Decision authority missing");
  if (protectedStates.size!==candidate.states.size || [...candidate.states].some(([id,state])=>{
   const saved=protectedStates.get(id);
   return !saved || saved.recovery!==state.recovery || saved.decisionId!==state.decisionId || saved.sourceUrl!==state.sourceUrl || JSON.stringify(saved.aliases)!==JSON.stringify(state.aliases);
  })) throw new Error("Trusted receipt history and recovery fallback must be published together");
 } catch { candidate=undefined; /* Recovery fails closed below; verified implementation ownership stays live. */ }
 const data = await get(`/v4/spreadsheets/${id}/values/${encodeURIComponent("'Gap Build List'!K:T")}?valueRenderOption=UNFORMATTED_VALUE`);
 const after = await get(metadata);
 if (!before.version || before.version !== after.version) throw new Error("Owning record changed during preflight; retry against a stable revision");
 if (candidate) {
  try {
   const logAfter=await get(authorityMetadata);
   if (logAfter.version!==candidate.version) candidate=undefined;
  } catch {candidate=undefined;}
 }
 const items: WorkPolicy["items"] = [];
 const seen = new Set<string>();
 for (const row of (data.values ?? []).slice(1)) {
  if (!row[0]) continue;
  const [recovery, decision, implementation, owner, id, tests, aliases, installed, approved, evidence] = row;
  const session = typeof owner === "string" && owner.match(/^https:\/\/app\.factory\.ai\/sessions\/([\w-]+)$/)?.[1];
  if (row.length !== 10 || !session || !tests || seen.has(id) || !["closed","open"].includes(recovery)) throw new Error("Incomplete or duplicate owning disposition");
  seen.add(id);
  items.push({ id, aliases: JSON.parse(aliases), sourceRecovery: recovery, decisionUrl: decision,
   ownerSession: session, implementation, installed, replacementApproved: approved, evidence: JSON.parse(evidence) });
 }
 // A closed cell without its decision receipt is incomplete authority, not an
 // implicit permission for a later cell edit to reopen it.
 const rememberedClosed=[...seed.items.filter(i=>i.sourceRecovery==="closed").map(i=>i.id),...[...(cached?.states??[])].filter(([,s])=>s.recovery==="closed").map(([id])=>id)];
 if (candidate && (items.some(i=>i.sourceRecovery==="closed" && !candidate!.states.has(i.id)) || rememberedClosed.some(id=>!candidate!.states.has(id)))) candidate=undefined;
 const gapOverrides:string[]=[];
 const sourceOnlyClosures:string[]=[];
 const fallback=new Map(seed.items.map(i=>[i.id,i]));
 for (const [id,state] of protectedStates) {
  const prior=fallback.get(id);
  fallback.set(id,{id,aliases:state.aliases,sourceRecovery:state.recovery,decisionUrl:state.sourceUrl,ownerSession:prior?.ownerSession??"",implementation:prior?.implementation??"Restore existing owning row.",installed:prior?.installed??false,replacementApproved:prior?.replacementApproved??false,evidence:prior?.evidence??[]});
 }
 const states=candidate?.states;
 for (const item of items) {
  const state=states?.get(item.id);
  if (state) {
   let referenceMatches=false;
   try {referenceMatches=decisionDocumentId(item.decisionUrl)===decisionDocumentId(authorityUrl);} catch { /* Never use a Gap URL as the authority route. */ }
   if (item.sourceRecovery!==state.recovery || !referenceMatches) gapOverrides.push(item.id);
   item.sourceRecovery=state.recovery;
   item.decisionUrl=state.sourceUrl;
   item.aliases=[...new Set([...item.aliases,...state.aliases])];
  } else {
   const prior=cached?.states.get(item.id);
   const saved=fallback.get(item.id);
   item.sourceRecovery=item.sourceRecovery==="closed" || prior?.recovery==="closed" || !prior && saved?.sourceRecovery==="closed" ? "closed" : "unverified";
   item.aliases=[...new Set([...item.aliases,...(prior?.aliases??saved?.aliases??[])])];
  }
 }
 // Removing an implementation row never removes its recorded source closure.
 const remembered=new Map([...protectedStates,...(cached?.states??[])]);
 for (const [id,item] of fallback) if (!remembered.has(id) && item.sourceRecovery==="closed") remembered.set(id,{recovery:"closed",decisionId:"",aliases:item.aliases,sourceUrl:item.decisionUrl});
 const missing=new Map([...remembered,...(candidate?.states??[])]);
 for (const [capability,state] of missing) if (!seen.has(capability)) {
  sourceOnlyClosures.push(capability);
  items.push({id:capability,aliases:state.aliases,sourceRecovery:state.recovery==="closed"?"closed":"unverified",
   decisionUrl:state.sourceUrl,ownerSession:"",implementation:"Restore the existing owning row before implementation continuation.",
   installed:false,replacementApproved:false,evidence:[state.sourceUrl]});
 }
 if (candidate && !providedRead) {
  if (authorityCache.size>=8 && !authorityCache.has(cacheKey)) authorityCache.delete(authorityCache.keys().next().value!);
  authorityCache.set(cacheKey,candidate);
 }
 const policy:WorkPolicy = {version: 1, source: {...seed.source, revision: String(after.version),decisionAuthority:{
  status:candidate?"verified":"unverified",url:authorityUrl,...(candidate?{revision:candidate.version}:{}),gapOverrides,sourceOnlyClosures,
 }}, items};
 if (!items.length || !validPolicy(policy)) throw new Error("Invalid live owning dispositions");
 return policy;
}
