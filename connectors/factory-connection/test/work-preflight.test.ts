import { test } from "node:test";
import assert from "node:assert/strict";
import { legacyIntent, validPolicy, workPreflight, type WorkPolicy } from "../src/work-preflight.ts";
const policy: WorkPolicy = {version:1,source:{url:"https://example.com/ledger",revision:"r1"},items:[
 {id:"homework",aliases:["capstone homework"],sourceRecovery:"closed",decisionUrl:"https://example.com/decision",ownerSession:"week-owner",implementation:"pending_test",installed:false,replacementApproved:true,evidence:["https://example.com/standard"]},
 {id:"lesson",aliases:["Build 101"],sourceRecovery:"closed",decisionUrl:"https://example.com/decision",ownerSession:"lesson-owner",implementation:"assigned",installed:false,replacementApproved:true,evidence:[]},
 {id:"audit",aliases:["brain auditor"],sourceRecovery:"closed",decisionUrl:"https://example.com/decision",ownerSession:"tool-owner",implementation:"assigned",installed:false,replacementApproved:true,evidence:[]},
]};
test("closed homework and every lesson slot reject reopening, including owner continuation as search",()=>{
 for(const id of ["homework","lesson"]) assert.equal(workPreflight(policy,{action:"source_search",capabilityId:id},"week-owner").code,"SOURCE_RECOVERY_CLOSED");
});
test("duplicate build routes to owner and installed capability is reused",()=>{
 const r=workPreflight(policy,{action:"replacement_build",capabilityId:"audit"});
 assert.equal(r.allowed,false); assert.equal(r.ownerSession,"tool-owner");
 assert.equal(workPreflight({...policy,items:[{...policy.items[2]!,installed:true}]},{action:"replacement_build",capabilityId:"audit"}).code,"CAPABILITY_EXISTS");
});
test("approved replacement continues without reopening recovery or inventing a pass",()=>{
 assert.equal(workPreflight(policy,{action:"continue",capabilityId:"audit"},"tool-owner").allowed,true);
 assert.equal(workPreflight(policy,{action:"continue",capabilityId:"audit"},"other").allowed,false);
 assert.equal(policy.items[2]!.implementation,"assigned");
});
test("a different known capability ID cannot launder an existing outcome to another owner",()=>{
 const r=workPreflight(policy,{action:"continue",capabilityId:"lesson",outcome:"brain auditor"},"lesson-owner");
 assert.equal(r.allowed,false);
 assert.equal(r.ownerSession,"tool-owner");
});
test("ambiguous registered outcomes never authorize continuation through a chosen ID",()=>{
 const ambiguous={...policy,items:[...policy.items,{...policy.items[2]!,id:"other-audit",ownerSession:"other-owner"}]};
 const r=workPreflight(ambiguous,{action:"continue",capabilityId:"audit",outcome:"brain auditor"},"tool-owner");
 assert.equal(r.allowed,false);
 assert.equal(r.ownerSession,null);
});
test("unresolved item reaches founder only with a specific recommendation and evidence",()=>{
 assert.equal(workPreflight(policy,{action:"escalate",capabilityId:"unknown",recommendation:"Fill from held teaching",evidence:["https://example.com/held"]}).allowed,true);
 assert.equal(workPreflight(policy,{action:"escalate",capabilityId:"unknown"}).allowed,false);
 assert.equal(workPreflight(policy,{action:"replacement_build",capabilityId:"unknown"}).allowed,false);
});
test("all-week contract, malformed policy, and legacy positive and negative dispatch",()=>{
 assert.equal(validPolicy(policy),true); assert.equal(validPolicy({}),false);
 assert.deepEqual(legacyIntent(policy,"Find the original capstone homework"),{action:"source_search",capabilityId:"homework"});
 assert.equal(legacyIntent(policy,"No original capstone homework search. Continue existing work."),null);
 assert.equal(legacyIntent(policy,"Commission a brain auditor" )?.action,"replacement_build");
 assert.equal(legacyIntent(policy,"Controlled live results passed for capstone homework and Build 101; duplicate Auditor commission routed to owner"),null);
 assert.equal(workPreflight(policy,{action:"inspect",capabilityId:"week-99"}).allowed,true);
});

test("an unrelated negative qualifier cannot cancel a positive recovery request",()=>{
 for(const text of ["Find original capstone homework without asking me.","Find original capstone homework and do not create a new tracker.","Do not build a replacement; find original capstone homework."])
  assert.equal(legacyIntent(policy,text)?.action,"source_search");
});

test("action clauses preserve a registered multiword capability name containing and",()=>{
 const p={...policy,items:[{...policy.items[0]!,id:"audit",aliases:["business brain document and instruction health check"]}]};
 assert.equal(legacyIntent(p,"Build a business brain document and instruction health check.")?.action,"replacement_build");
});
