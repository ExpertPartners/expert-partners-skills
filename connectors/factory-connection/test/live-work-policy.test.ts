import { test } from "node:test";
import assert from "node:assert/strict";
import { sourceDecisionDigest, sourceAuthorityManifest } from "../src/source-decision-authority.ts";
import { liveWorkPolicy } from "../src/live-work-policy.ts";
import { workPreflight, type WorkPolicy } from "../src/work-preflight.ts";
const seed: WorkPolicy = {version:1,source:{url:"https://docs.google.com/spreadsheets/d/test",revision:"old"},items:[]};
const row = ["closed","https://example.com/decision","testing","https://app.factory.ai/sessions/existing-owner","capability","pending",'["capstone homework"]',false,true,'[]'];
function reader(rows: unknown[][], versions = ["2","2"]) {
 return async (path: string) => new Response(JSON.stringify(path.includes("/values/") ? {values:[[],...rows]} : {version:versions.shift()}));
}
test("every dispatch reads live ownership, installed state and stable version",async()=>{
 const first = await liveWorkPolicy(seed,"unused",reader([row]));
 assert.equal(first.source.revision,"2");
 assert.equal(workPreflight(first,{action:"source_search",capabilityId:"capability"}).code,"SOURCE_RECOVERY_CLOSED");
 assert.equal(workPreflight(first,{action:"continue",capabilityId:"capability"},"existing-owner").allowed,true);
 const changed = [...row]; changed[7]=true;
 const next = await liveWorkPolicy(seed,"unused",reader([changed],["3","3"]));
 assert.equal(workPreflight(next,{action:"replacement_build",capabilityId:"capability"}).code,"CAPABILITY_EXISTS");
});
test("concurrent writes, incomplete dispositions and unavailable authority cannot fall back to stale policy",async()=>{
 await assert.rejects(liveWorkPolicy(seed,"unused",reader([row],["2","3"])));
 await assert.rejects(liveWorkPolicy(seed,"unused",reader([row,row])));
 await assert.rejects(liveWorkPolicy(seed,"unused",reader([[...row.slice(0,7),"false",true,"[]"]])));
 await assert.rejects(liveWorkPolicy(seed,"unused",async()=>new Response("unavailable",{status:503})));
});
test("editing the Gap recovery cell cannot supersede the founder's recorded closure",async()=>{
 const url="https://docs.google.com/document/d/founder-log/edit";
 const quote="Keep the fixture source recovery closed.";
 const heading="January 1, 2026. Fixture source decision";
 const receipt={id:"fixture-close",recordedAt:"2026-01-01T00:00:00.000Z",action:"close",founder:"Founder",supersedes:null,
  capabilities:[{id:"capability",aliases:["capstone homework"]}],provenance:{heading,quote,sourceUrl:url}};
 const text=heading+"\n"+quote+"\nSOURCE RECOVERY DECISION BEGIN v1\n"+JSON.stringify(receipt)+"\nSOURCE RECOVERY DECISION END\n";
 const protectedSeed={...seed,source:{...seed.source,decisionLogUrl:url,founderDecisionActor:"Founder",...await sourceAuthorityManifest(text,url,"Founder")},items:[
  {id:"capability",aliases:["capstone homework"],sourceRecovery:"closed" as const,decisionUrl:url,ownerSession:"existing-owner",implementation:"testing",installed:false,replacementApproved:true,evidence:[]}
 ]};
 const opened=[...row];opened[0]="open";opened[1]="not-a-verified-decision";
 const read=async(path:string)=> path.includes("/export") ? new Response(text) : new Response(JSON.stringify(path.includes("/values/")?{values:[[],opened]}:{version:path.includes("founder-log")?"9":"2"}));
 const p=await liveWorkPolicy(protectedSeed,"unused",read);
 assert.equal(p.items[0]!.sourceRecovery,"closed");
 assert.equal(p.items[0]!.decisionUrl,url);
 assert.equal(workPreflight(p,{action:"continue",capabilityId:"capability"},"existing-owner").allowed,true);
});

test("authority outage stops recovery while retaining current approved implementation owner",async()=>{
 const opened=[...row];opened[0]="open";
 const configured={...seed,source:{...seed.source,decisionLogUrl:"https://docs.google.com/document/d/log/edit",founderDecisionActor:"Founder"}};
 const read=async(path:string)=>path.includes("/files/log")?new Response("unavailable",{status:503}):new Response(JSON.stringify(path.includes("/values/")?{values:[[],opened]}:{version:"2"}));
 const p=await liveWorkPolicy(configured,"unused",read);
 assert.equal(p.source.decisionAuthority?.status,"unverified");
 assert.equal(workPreflight(p,{action:"source_search",capabilityId:"capability"}).code,"SOURCE_AUTHORITY_UNVERIFIED");
 assert.equal(workPreflight(p,{action:"continue",capabilityId:"capability"},"existing-owner").allowed,true);
});
test("deleting a Gap implementation row cannot delete its recorded closure or invent an owner",async()=>{
 const url="https://docs.google.com/document/d/log/edit",heading="January 1, 2026. Closure",quote="Keep original closed.";
 const receipt={id:"close",recordedAt:"2026-01-01T00:00:00.000Z",action:"close",founder:"Founder",supersedes:null,capabilities:[{id:"missing",aliases:["missing original"]}],provenance:{heading,quote,sourceUrl:url}};
 const text=`${heading}\n${quote}\nSOURCE RECOVERY DECISION BEGIN v1\n${JSON.stringify(receipt)}\nSOURCE RECOVERY DECISION END\n`;
 const configured={...seed,source:{...seed.source,decisionLogUrl:url,founderDecisionActor:"Founder",...await sourceAuthorityManifest(text,url,"Founder")}};
 const read=async(path:string)=>path.includes("/export")?new Response(text):new Response(JSON.stringify(path.includes("/values/")?{values:[[]]}:{version:"2"}));
 const p=await liveWorkPolicy(configured,"unused",read);
 assert.equal(workPreflight(p,{action:"source_search",capabilityId:"missing"}).code,"SOURCE_RECOVERY_CLOSED");
 assert.equal(workPreflight(p,{action:"continue",capabilityId:"missing"},"existing-owner").allowed,false);
 assert.deepEqual(p.source.decisionAuthority?.sourceOnlyClosures,["missing"]);
});

test("receipt deletion or replay cannot advance the trusted history manifest",async()=>{
 const url="https://docs.google.com/document/d/log/edit",heading="January 1, 2026. Close",quote="Keep sources closed.";
 const receipt={id:"close",recordedAt:"2026-01-01T00:00:00.000Z",action:"close",founder:"Founder",supersedes:null,capabilities:[{id:"capability",aliases:["capstone homework"]}],provenance:{heading,quote,sourceUrl:url}};
 const original=`${heading}\n${quote}\nSOURCE RECOVERY DECISION BEGIN v1\n${JSON.stringify(receipt)}\nSOURCE RECOVERY DECISION END\n`;
 const configured={...seed,source:{...seed.source,decisionLogUrl:url,founderDecisionActor:"Founder",...await sourceAuthorityManifest(original,url,"Founder")},items:[{id:"capability",aliases:["capstone homework"],sourceRecovery:"closed" as const,decisionUrl:url,ownerSession:"existing-owner",implementation:"testing",installed:false,replacementApproved:true,evidence:[]}]};
 const modified=original.replaceAll('"capability"','"unrelated"');
 for(const rows of [[{...row,0:"open"}],[]]) {
  const values=rows.length?[["open",...row.slice(1)]]:[];
  const read=async(path:string)=>path.includes("/export")?new Response(modified):new Response(JSON.stringify(path.includes("/values/")?{values:[[],...values]}:{version:"99"}));
  const p=await liveWorkPolicy(configured,"unused",read);
  assert.equal(p.source.decisionAuthority?.status,"unverified");
  assert.equal(workPreflight(p,{action:"source_search",capabilityId:"capability"}).code,"SOURCE_RECOVERY_CLOSED");
 }
});

test("trusted fallback protects future closures after row loss and authority outage on a cold start",async()=>{
 const url="https://docs.google.com/document/d/log/edit",heading="January 1, 2026. Future closure",quote="Keep the future class source closed.";
 const receipt={id:"future-close",recordedAt:"2026-01-01T00:00:00.000Z",action:"close",founder:"Founder",supersedes:null,capabilities:[{id:"future",aliases:["new class handout"]}],provenance:{heading,quote,sourceUrl:url}};
 const text=`${heading}\n${quote}\nSOURCE RECOVERY DECISION BEGIN v1\n${JSON.stringify(receipt)}\nSOURCE RECOVERY DECISION END\n`;
 const configured={...seed,source:{...seed.source,decisionLogUrl:url,founderDecisionActor:"Founder",...await sourceAuthorityManifest(text,url,"Founder")}};
 const read=async(path:string)=>path.includes("/files/log")?new Response("unavailable",{status:503}):new Response(JSON.stringify(path.includes("/values/")?{values:[[]]}:{version:"2"}));
 const p=await liveWorkPolicy(configured,"unused",read);
 assert.equal(p.items[0]!.id,"future");assert.deepEqual(p.items[0]!.aliases,["new class handout"]);
 assert.equal(workPreflight(p,{action:"source_search",capabilityId:"future"}).code,"SOURCE_RECOVERY_CLOSED");
 assert.equal(workPreflight(p,{action:"continue",capabilityId:"future"},"existing-owner").allowed,false);
});
