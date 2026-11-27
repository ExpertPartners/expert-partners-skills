import { test } from "node:test";
import assert from "node:assert/strict";
import { runTool } from "../src/tools.ts";
const policy = {version:1,source:{url:"https://example.com/ledger",revision:"r1"},items:[
 {id:"closed-source",aliases:["capstone homework","Build 101"],sourceRecovery:"closed",decisionUrl:"https://example.com/decision",ownerSession:"existing-owner",implementation:"awaiting_test",installed:false,replacementApproved:true,evidence:[]}
]};
const env = {FACTORY_API_KEY:"unused-in-denied-tests",OAUTH_KV:{get:async()=>policy}};
test("all three dispatch entry points refuse before any Factory request",async()=>{
 let calls=0;
 const previous=globalThis.fetch;
 globalThis.fetch=async()=>{calls++;throw new Error("Unexpected external request");};
 try {
  for(const [name,args] of [
   ["create_session",{machine:"M4",firstMessage:"Find the original capstone homework"}],
   ["start_and_watch",{machine:"M4",message:"Find the Build 101 original videos"}],
   ["post_message",{sessionId:"other-owner",text:"Commission the capstone homework build"}],
   ["post_message",{sessionId:"other-owner",text:"Search for the missing original for week 99"}],
  ] as const) {
   const r=await runTool(name,args,env); assert.equal(r.ok,false); assert.equal(r.status,409);
  }
  assert.equal(calls,0);
 } finally {globalThis.fetch=previous;}
});
test("preflight keeps approved work and genuine recommendations usable",async()=>{
 const continued=await runTool("work_preflight",{sessionId:"existing-owner",workIntent:{action:"continue",capabilityId:"closed-source"}},env);
 assert.equal(continued.ok,true); assert.equal((continued as any).result.allowed,true);
 const escalated=await runTool("work_preflight",{workIntent:{action:"escalate",capabilityId:"unresolved",recommendation:"Use held teaching",evidence:["https://example.com/held"]}},env);
 assert.equal((escalated as any).result.allowed,true);
});
test("missing policy refuses dispatch rather than losing closures",async()=>{
 const r=await runTool("post_message",{sessionId:"existing-owner",text:"Continue"},{FACTORY_API_KEY:"unused"});
 assert.equal(r.status,503);
});
test("production refuses a missing live credential instead of evaluating its saved seed",async()=>{
 const r=await runTool("post_message",{sessionId:"existing-owner",text:"Continue"},{...env,WORK_POLICY_LIVE:"required"});
 assert.equal(r.status,503);
});
