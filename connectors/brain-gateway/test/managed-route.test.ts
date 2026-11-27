import { test } from "node:test";
import assert from "node:assert/strict";
import { managedMcpRequest } from "../src/managed-route.ts";
test("only the exact managed alias is canonicalized before the existing OAuth gate", async () => {
 const req = new Request("https://example.test/mcp/managed?protocol=2025", {method:"POST",headers:{authorization:"Bearer test-only", "content-type":"application/json"},body:'{"method":"initialize"}'});
 const routed=managedMcpRequest(req);
 assert.equal(routed.url,"https://example.test/mcp?protocol=2025");
 assert.equal(routed.method,"POST");assert.equal(routed.headers.get("authorization"),"Bearer test-only");
 assert.equal(await routed.text(),'{"method":"initialize"}');
 for(const path of ["/mcp","/mcp/managed/","/token","/api/tools/read","/mcp/managed-other"]){const other=new Request("https://example.test"+path);assert.equal(managedMcpRequest(other),other);}
 const anonymous=managedMcpRequest(new Request("https://example.test/mcp/managed"));assert.equal(anonymous.headers.get("authorization"),null);
});
