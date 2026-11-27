import { test } from "node:test";
import assert from "node:assert/strict";
import { orderedWorkPolicy } from "../src/ordered-work-policy.ts";
import { workPreflight, type WorkPolicy } from "../src/work-preflight.ts";
const seed:WorkPolicy={version:1,source:{url:"https://example.com/ledger",revision:"1",companyToolBuilderSession:"existing-owner"},items:[{
 id:"existing-capability",aliases:["nineteen piece brain completeness check"],sourceRecovery:"closed",decisionUrl:"https://example.com/decision",ownerSession:"existing-owner",implementation:"repairing",installed:true,replacementApproved:true,evidence:[]
}]};
test("ordered reads complete before any decision and expose their actual evidence",async()=>{
 const order:string[]=[];
 const f={call:async<T>()=>{order.push("company_tool_builder");return {messages:[{id:"msg",content:[{type:"text",text:"Existing correction underway"}]}]} as T;}};
 const fetcher=(async()=>{order.push("skills_marketplace");return new Response(JSON.stringify({nodes:[{id:"foundations",subtitle:"Check the live business brain"}]}));}) as typeof fetch;
 const result=await orderedWorkPolicy(seed,"unused",f,fetcher,async()=>{order.push("gap_build_list");return seed;});
 assert.deepEqual(order,["company_tool_builder","skills_marketplace","gap_build_list"]);
 assert.deepEqual(result.checks?.map(c=>c.stage),order);
 const renamed=workPreflight(result,{action:"replacement_build",capabilityId:"new-name",outcome:"Nineteen-piece brain completeness check"});
 assert.equal(renamed.code,"CAPABILITY_EXISTS");assert.equal(renamed.ownerSession,"existing-owner");assert.equal(renamed.capabilityId,"existing-capability");
});
test("unavailable earlier sources stop subsequent reads rather than masquerade as an empty register",async()=>{
 let later=0;
 const f={call:async<T>()=>{throw new Error("offline");return null as T;}};
 await assert.rejects(orderedWorkPolicy(seed,"unused",f,(async()=>{later++;throw new Error("unexpected");}) as typeof fetch));
 assert.equal(later,0);
 await assert.rejects(orderedWorkPolicy(seed,"unused",{call:async<T>()=>({messages:[]} as T)},(async()=>new Response("offline",{status:503})) as typeof fetch,async()=>{later++;return seed;}));
 assert.equal(later,0);
});
