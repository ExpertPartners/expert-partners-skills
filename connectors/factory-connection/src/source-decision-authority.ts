/** Structured receipts belong to the existing decision document, never another queue.
 * A cell edit or an actor label alone cannot supersede a recorded closure. */
export type RecoveryDecisionState = {
 recovery: "closed" | "open"; decisionId: string; aliases: string[]; sourceUrl: string;
};
type Receipt = {
 id: string; recordedAt: string; action: "close" | "reopen"; founder: string;
 supersedes: string | null;
 capabilities: {id: string; aliases?: string[]}[];
 provenance: {heading: string; quote: string; sourceUrl: string};
};
const idPattern=/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const blocks=/^SOURCE RECOVERY DECISION BEGIN v1\s*\r?\n([\s\S]*?)^SOURCE RECOVERY DECISION END\s*$/gm;
const datedHeading=/^(?:[A-Z][a-z]+ \d{1,2}, \d{4}\.|\d{4}-\d{2}-\d{2}[. ])/;
/** A trusted routing-record digest pins the complete accepted receipt history.
 * Advancing it is part of recording an evidenced founder supersession, never a
 * consequence of reading a mutable Gap cell or an edited authority document. */
export async function sourceDecisionDigest(text:string):Promise<string> {
 const canonical=(v:any):any=>Array.isArray(v)?v.map(canonical):v && typeof v==="object"?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
 const receipts=[...text.matchAll(blocks)].map(m=>canonical(JSON.parse(m[1]!))).sort((a,b)=>a.id.localeCompare(b.id));
 const bytes=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(JSON.stringify(receipts)));
 return [...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,"0")).join("");
}
/** Publish both fields in one save of the existing private routing seed. */
export async function sourceAuthorityManifest(text:string,url:string,founder:string) {
 const states=parseSourceDecisions(text,url,founder);
 return {decisionReceiptDigest:await sourceDecisionDigest(text),decisionRecoveryFallback:[...states].map(([id,state])=>({id,...state}))};
}
function required(ok: unknown): asserts ok {
 if (!ok) throw new Error("Invalid or ambiguous source decision authority");
}
export function decisionDocumentId(value: string): string {
 const u=new URL(value);
 const id=u.pathname.match(/^\/document\/d\/([\w-]+)(?:\/|$)/)?.[1];
 required(u.protocol==="https:" && u.hostname==="docs.google.com" && !u.username && !u.password && !u.port && id);
 return id;
}
export function parseSourceDecisions(text: string, url: string, founder: string): Map<string,RecoveryDecisionState> {
 const documentId=decisionDocumentId(url);
 required(founder.trim() && text.length<=10_000_000);
 const matches=[...text.matchAll(blocks)];
 required(!text.replace(blocks,"").includes("SOURCE RECOVERY DECISION"));
 required(matches.length>0 && matches.length<=10_000);
 required(matches.length===(text.match(/^SOURCE RECOVERY DECISION BEGIN v1\s*$/gm)??[]).length);
 required(matches.length===(text.match(/^SOURCE RECOVERY DECISION END\s*$/gm)??[]).length);
 const human=text.replace(blocks,"").replace(/\r\n/g,"\n");
 const lines=human.split("\n");
 const receipts=new Map<string,Receipt>();
 const humanSections=new Map<string,string>();
 const byCapability=new Map<string,Receipt[]>();
 for (const match of matches) {
  const r=JSON.parse(match[1]!) as Receipt;
  required(r && typeof r==="object" && typeof r.id==="string" && idPattern.test(r.id) && !receipts.has(r.id));
  required(typeof r.recordedAt==="string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(r.recordedAt));
  required(Number.isFinite(Date.parse(r.recordedAt)) && new Date(r.recordedAt).toISOString()===r.recordedAt);
  required(["close","reopen"].includes(r.action) && r.founder===founder);
  required(r.supersedes===null || typeof r.supersedes==="string" && idPattern.test(r.supersedes));
  required(Array.isArray(r.capabilities) && r.capabilities.length>0 && r.capabilities.length<=5000);
  const p=r.provenance;
  required(p && typeof p.heading==="string" && p.heading.trim() && !p.heading.includes("\n"));
  required(typeof p.quote==="string" && p.quote.trim() && p.quote.length<=10_000);
  required(typeof p.sourceUrl==="string" && decisionDocumentId(p.sourceUrl)===documentId);
  const headings=lines.flatMap((line,index)=>line.trim()===p.heading.trim()?[index]:[]);
  required(headings.length===1);
  const start=headings[0]!+1;
  const next=lines.findIndex((line,index)=>index>=start && datedHeading.test(line.trim()));
  const section=lines.slice(start,next<0?undefined:next).join("\n");
  required(section.includes(p.quote.replace(/\r\n/g,"\n")));
  humanSections.set(r.id,section);
  const seen=new Set<string>();
  for (const c of r.capabilities) {
   required(c && typeof c.id==="string" && idPattern.test(c.id) && !seen.has(c.id));
   seen.add(c.id);
   required(c.aliases===undefined || Array.isArray(c.aliases) && c.aliases.every(a=>typeof a==="string" && a.length>2 && a.length<=512));
   required(r.action!=="close" || !!c.aliases?.length);
   byCapability.set(c.id,[...(byCapability.get(c.id)??[]),r]);
  }
  receipts.set(r.id,r);
 }
 const states=new Map<string,RecoveryDecisionState>();
 for (const [capability,events] of byCapability) {
  const roots=events.filter(r=>r.supersedes===null);
  required(roots.length===1 && roots[0]!.action==="close");
  const children=new Map<string,Receipt>();
  for (const r of events) {
   if (r.supersedes===null) continue;
   const parent=receipts.get(r.supersedes);
   required(parent && parent.capabilities.some(c=>c.id===capability) && !children.has(parent.id));
   required(r.recordedAt>=parent.recordedAt);
   children.set(parent.id,r);
  }
  const visited=new Set<string>();
  const aliases=new Set<string>();
  let current: Receipt|undefined=roots[0];
  let previous: Receipt|undefined;
  while (current) {
   required(!visited.has(current.id));
   visited.add(current.id);
   required(current.action!=="reopen" || previous?.action==="close" && current.supersedes===previous.id);
   if (current.action==="reopen") {
    required(current.provenance.heading!==previous!.provenance.heading && current.provenance.quote!==previous!.provenance.quote);
    required(humanSections.get(current.id)!.includes(`${founder} explicitly superseded source recovery closure ${previous!.id} for ${capability}.`));
   }
   for (const alias of current.capabilities.find(c=>c.id===capability)!.aliases??[]) aliases.add(alias);
   states.set(capability,{recovery:current.action==="close"?"closed":"open",decisionId:current.id,aliases:[...aliases],sourceUrl:current.provenance.sourceUrl});
   previous=current;
   current=children.get(current.id);
  }
  required(visited.size===events.length);
 }
 return states;
}
