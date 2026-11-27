import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { URL } from "node:url";
import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler, getMcpAuthContext } from "agents/mcp/server";
import { currentNarrowing, mcpPrincipal, parseNarrowing, runNarrowed } from "../src/mcp-narrowing.ts";
import { effectiveScopes, pinnedReadFor } from "../src/access.ts";
import { runTool } from "../src/tools.ts";

const config = JSON.parse(readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8").replace(/^\s*\/\/.*$/gm, ""));
const allowed = config.vars.ALLOWED_SCOPES;
const emails = "allison@expertpartners.com,don@expertpartners.com";
const headers = (department?: string, businessLine?: string) => new Headers({
	...(department !== undefined ? { "x-brain-department": department } : {}),
	...(businessLine !== undefined ? { "x-brain-business-line": businessLine } : {}),
});
const principal = (email: string, department?: string, line?: string) => mcpPrincipal({ email }, emails, parseNarrowing(headers(department, line)) ?? undefined)!;

test("absent labels preserve the person; labels never supply identity", () => {
	assert.deepEqual(principal("allison@expertpartners.com"), { kind: "person", email: "allison@expertpartners.com" });
	assert.equal(mcpPrincipal({ department: "ep-ceo" }, emails, {}), null);
	assert.equal(mcpPrincipal({ email: "stranger@example.com" }, emails, {}), null);
	assert.equal(mcpPrincipal({ email: "allison@expertpartners.com" }, emails, undefined), null);
	assert.deepEqual(mcpPrincipal({ email: "don@expertpartners.com", department: "ag-ceo", businessLine: "AGI" }, emails, {}),
		{ kind: "person", email: "don@expertpartners.com" });
	assert.equal(currentNarrowing(), undefined);
});

test("unknown, empty and prototype departments and invalid line combinations fail closed", () => {
	for (const department of ["", "nope", "__proto__", "constructor", "toString"])
		assert.equal(parseNarrowing(headers(department)), null);
	for (const line of [undefined, "", "agi", "AG", "AGRE, AGI", "__proto__"])
		assert.equal(parseNarrowing(headers("ag-ceo", line)), null);
	for (const department of [undefined, "ep-ceo", "hq-chro"])
		assert.equal(parseNarrowing(headers(department, "AGI")), null);
	for (const line of ["AGRE", "AGI"])
		assert.deepEqual(parseNarrowing(headers("ag-ceo", line)), { department: "ag-ceo", businessLine: line });
});

test("AG routing never grants Don AG or grants access beyond the department; pins remain leader only", async () => {
	for (const line of ["AGRE", "AGI"]) {
		const don = principal("don@expertpartners.com", "ag-ceo", line);
		assert.deepEqual(effectiveScopes(allowed, don), ["hq-core", "ep-core"]);
		assert.throws(() => pinnedReadFor(don, "gap108-week2-builder", "file", undefined, "{}"));
		const allison = principal("allison@expertpartners.com", "ag-cro", line);
		assert.deepEqual(effectiveScopes(allowed, allison), effectiveScopes(allowed, { kind: "department", id: "ag-cro" }));
		assert.throws(() => pinnedReadFor(allison, "gap108-week2-builder", "file", undefined, "{}"));
		const result = await runTool("list_scopes", { email: "allison@expertpartners.com", department: "ag-ceo", businessLine: "AGRE" }, { ALLOWED_SCOPES: allowed }, undefined, don);
		assert.ok(result.ok);
		assert.deepEqual((result.result as any).routing, { department: "ag-ceo", businessLine: line });
		assert.ok((result.result as any).scopes.every((s: any) => !s.scope.startsWith("ag-")));
	}
});

test("SDK factory captures each request before streamed bodies are consumed outside the narrowing context", async () => {
	const handler = createMcpHandler(() => {
		const actor = mcpPrincipal(getMcpAuthContext()?.props, emails, currentNarrowing());
		assert.ok(actor);
		const server = new McpServer({ name: "narrowing-unit", version: "1" });
		server.registerTool("list_scopes", { inputSchema: {} }, async () => {
			await new Promise((resolve) => setImmediate(resolve));
			const r = await runTool("list_scopes", {}, { ALLOWED_SCOPES: allowed }, undefined, actor);
			return { content: [{ type: "text" as const, text: JSON.stringify(r) }] };
		});
		return server;
	});
	const actors = Array.from({ length: 24 }, (_, i) => ({
		email: i % 2 ? "don@expertpartners.com" : "allison@expertpartners.com",
		department: i % 3 ? "ag-cro" : "ep-cro",
		line: i % 3 ? (i % 2 ? "AGRE" : "AGI") : undefined,
	}));
	const responses = await Promise.all(actors.map((a, i) => {
		const req = new Request("https://gw.invalid/mcp?email=allison@expertpartners.com&department=ag-ceo", {
			method: "POST",
			headers: { "content-type": "application/json", accept: "application/json, text/event-stream" },
			body: JSON.stringify({ jsonrpc: "2.0", id: i + 1, method: "tools/call", params: { name: "list_scopes", arguments: {} } }),
		});
		const props = { email: a.email };
		const ctx = { props, [Symbol.for("cloudflare.workers-oauth-provider.verified-context.v1")]: { version: 1, token: "synthetic-unit-token", clientId: "unit-client", scopes: [], props } };
		return runNarrowed(parseNarrowing(headers(a.department, a.line))!, () => handler(req, {}, ctx as any));
	}));
	assert.equal(currentNarrowing(), undefined);
	await Promise.all(responses.map(async (response, i) => {
		assert.equal(response.status, 200);
		const text = await response.text();
		const data = JSON.parse(text.startsWith("event:") ? text.split("\n").find((l) => l.startsWith("data:"))!.slice(5) : text);
		const tool = JSON.parse(data.result.content[0].text);
		assert.ok(tool.ok);
		assert.deepEqual(tool.result.scopes.map((s: any) => s.scope), effectiveScopes(allowed, principal(actors[i].email, actors[i].department, actors[i].line)));
		assert.deepEqual(tool.result.routing, { department: actors[i].department, ...(actors[i].line ? { businessLine: actors[i].line } : {}) });
	}));
});
