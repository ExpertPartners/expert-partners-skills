import {test} from "node:test";
import assert from "node:assert/strict";
import {parseSourceDecisions} from "../src/source-decision-authority.ts";
const url="https://docs.google.com/document/d/fixture-log/edit";
const close={id:"close-one",recordedAt:"2026-01-01T00:00:00.000Z",action:"close",founder:"Founder",supersedes:null,capabilities:[{id:"fixture",aliases:["original homework"]}],provenance:{heading:"January 1, 2026. Close original",quote:"Stop source recovery.",sourceUrl:url}};
const reopen={...close,id:"open-two",recordedAt:"2026-01-02T00:00:00.000Z",action:"reopen",supersedes:close.id,capabilities:[{id:"fixture"}],provenance:{heading:"January 2, 2026. Supersede closure",quote:"Search again for this specific original.",sourceUrl:url}};
const block=(r:any)=>`SOURCE RECOVERY DECISION BEGIN v1\n${JSON.stringify(r)}\nSOURCE RECOVERY DECISION END\n`;
const human=(r:any)=>`${r.provenance.heading}\n${r.provenance.quote}\n${r.action==="reopen"?`Founder explicitly superseded source recovery closure ${r.supersedes} for fixture.\n`:""}`;
const doc=(...rs:any[])=>rs.map(r=>human(r)+block(r)).join("\n");
test("recorded closure and explicit founder supersession preserve historical aliases",()=>{
 assert.equal(parseSourceDecisions(doc(close),url,"Founder").get("fixture")?.recovery,"closed");
 const state=parseSourceDecisions(doc(close,reopen),url,"Founder").get("fixture");
 assert.equal(state?.recovery,"open");assert.deepEqual(state?.aliases,["original homework"]);
});
test("actor labels, unrecorded quotes and reused closure prose cannot authorize reopening",()=>{
 assert.throws(()=>parseSourceDecisions(block(close),url,"Founder"));
 assert.throws(()=>parseSourceDecisions(doc(close)+human(reopen).replace("Founder explicitly superseded source recovery closure close-one for fixture.\n","")+block(reopen),url,"Founder"));
 assert.throws(()=>parseSourceDecisions(doc(close)+block({...reopen,provenance:close.provenance}),url,"Founder"));
 assert.throws(()=>parseSourceDecisions(doc({...close,founder:"Other"}),url,"Founder"));
});
test("forks, replay, orphan supersession, wrong authority and malformed markers fail closed",()=>{
 for(const text of [doc(close,reopen,{...reopen,id:"fork"}),doc(close,close),doc(close,{...reopen,supersedes:"unknown"}),doc({...close,provenance:{...close.provenance,sourceUrl:"https://docs.google.com/document/d/other/edit"}}),doc(close)+"SOURCE RECOVERY DECISION BEGIN v1\n{}",doc(close)+"SOURCE RECOVERY DECISION BEGIN v2\n{}\nSOURCE RECOVERY DECISION END v2"])
  assert.throws(()=>parseSourceDecisions(text,url,"Founder"));
});
