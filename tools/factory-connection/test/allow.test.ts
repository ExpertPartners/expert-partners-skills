import { test } from "node:test";
import assert from "node:assert/strict";
import { isAllowedEmail } from "../src/allow.ts";
import { isConversational, isOnline, machineLabel, messageText } from "../src/factory.ts";

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
