import { test } from "node:test";
import assert from "node:assert/strict";
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
