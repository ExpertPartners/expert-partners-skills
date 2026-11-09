import { test } from "node:test";
import assert from "node:assert/strict";
import { isAllowedEmail } from "../src/allow.ts";
import { isConversational, isOnline, machineLabel, messageText, resolveComputer, resolveMachine } from "../src/factory.ts";

test("only listed emails may sign in", () => {
	const list = "allison@expertpartners.com";
	assert.equal(isAllowedEmail(list, "allison@expertpartners.com"), true);
	assert.equal(isAllowedEmail(list, " Allison@ExpertPartners.com "), true);
	assert.equal(isAllowedEmail(list, "someone@expertpartners.com"), false);
	assert.equal(isAllowedEmail(list, ""), false);
	assert.equal(isAllowedEmail(undefined, "allison@expertpartners.com"), false);
	assert.equal(isAllowedEmail("", "allison@expertpartners.com"), false);
});

test("message text joins text blocks and drops reminders", () => {
	const m = { role: "assistant", content: [{ type: "text", text: "hello" }, { type: "tool_use" }, { type: "text", text: "world" }] };
	assert.equal(messageText(m), "hello\nworld");
	assert.equal(isConversational(m), true);
	assert.equal(isConversational({ role: "user", content: [{ type: "text", text: "<system-reminder>x</system-reminder>" }] }), false);
	assert.equal(isConversational({ role: "tool", content: [{ type: "text", text: "x" }] }), false);
});

test("machine labels and online state", () => {
	const now = 1_000_000_000;
	const cs = [
		{ id: "a", name: "ember-mac-mini-m2", status: "active", lastSeenAt: now - 60_000 },
		{ id: "b", name: "ag-mac-mini-m4", status: "active", lastSeenAt: now - 3_600_000 },
	];
	assert.equal(machineLabel(cs, "a"), "Ember M2");
	assert.equal(machineLabel(cs, "b"), "Allison M4");
	assert.match(machineLabel(cs, "zzzzzzzzzz"), /^gone/);
	assert.equal(isOnline(cs[0], now), true);
	assert.equal(isOnline(cs[1], now), false);
});

// Fake Factory API: like the live one, cloud computers appear only with includeUnlisted=true.
function fakeFactory() {
	const macs = [
		{ id: "2ec4e8b5-m2", name: "ember-mac-mini-m2", status: "active" },
		{ id: "8ebd71eb-m4", name: "ag-mac-mini-m4", status: "active" },
	];
	const cloud = [
		{ id: "6befb46d-cloud", name: "mission-181cfd17", status: "active", providerType: "e2b" },
		{ id: "20432e10-cloud", name: "droid-environment-159e59e7", status: "active", providerType: "e2b" },
	];
	return {
		call: async (_m: string, _p: string, o: any = {}) => ({ computers: o.query?.includeUnlisted === "true" ? [...cloud, ...macs] : macs }),
	} as any;
}

test("computer tools resolve any computer the API returns, listed or unlisted", async () => {
	const f = fakeFactory();
	assert.equal((await resolveComputer(f, "6befb46d-cloud")).name, "mission-181cfd17");
	assert.equal((await resolveComputer(f, "droid-environment-159e59e7")).id, "20432e10-cloud");
	assert.equal((await resolveComputer(f, "M2")).id, "2ec4e8b5-m2");
	assert.equal((await resolveComputer(f, "ag-mac-mini-m4")).id, "8ebd71eb-m4");
	await assert.rejects(resolveComputer(f, "nope"), /Unknown computer/);
});

test("sessions start only on the two Macs", async () => {
	const f = fakeFactory();
	assert.equal((await resolveMachine(f, "m2")).name, "ember-mac-mini-m2");
	assert.equal((await resolveMachine(f, "Allison M4")).name, "ag-mac-mini-m4");
	assert.equal((await resolveMachine(f, "8ebd71eb-m4")).name, "ag-mac-mini-m4");
	await assert.rejects(resolveMachine(f, "6befb46d-cloud"), /only on the two Macs/);
	await assert.rejects(resolveMachine(f, "droid-environment-159e59e7"), /only on the two Macs/);
});
