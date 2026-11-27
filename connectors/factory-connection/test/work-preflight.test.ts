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
 assert.equal(workPreflight(policy,{action:"inspect",capabilityId:"week-99"}).allowed,true);
});
