import { test } from "node:test";
import assert from "node:assert/strict";
import { isAllowedEmail } from "../src/allow.ts";

test("only listed emails may sign in", () => {
	const list = "allison@expertpartners.com";
	assert.equal(isAllowedEmail(list, "allison@expertpartners.com"), true);
	assert.equal(isAllowedEmail(list, " Allison@ExpertPartners.com "), true);
	assert.equal(isAllowedEmail(list, "someone@expertpartners.com"), false);
	assert.equal(isAllowedEmail(list, ""), false);
	assert.equal(isAllowedEmail(undefined, "allison@expertpartners.com"), false);
	assert.equal(isAllowedEmail("", "allison@expertpartners.com"), false);
});
