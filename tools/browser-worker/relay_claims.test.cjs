const test = require("node:test");
const assert = require("node:assert/strict");
const {RelayClaims} = require("../../plugins/operating-doctrine/skills/browser-automation/scripts/relay_claims.cjs");

const tab = (id, openerTabId) => ({id, openerTabId, windowId: 3, url: "about:blank"});
const created = value => ({method: "chrome.tabs.onCreated", params: [value]});
const initialized = {method: "extension.initialized", params: []};

function fixture() {
  const log = [];
  return {
    log,
    tracker: new RelayClaims({
      claim: async record => { log.push(["claim", record]); return record; },
      release: async record => { log.push(["release", record.tabId]); },
      finish: async record => { log.push(["finish", record.tabId]); },
    }),
  };
}

test("initializes only with one durable initial claim", async () => {
  const {tracker, log} = fixture();
  await assert.rejects(tracker.event(initialized), /initial_claim_unavailable/);
  await tracker.event(created(tab(1)));
  assert.deepEqual(log, [["claim", {tabId: 1, windowId: 3, urlClass: "blank"}]]);
  await assert.rejects(tracker.event(created(tab(2))), /initial_claim_ambiguous/);
  await tracker.event(initialized);
  assert.equal(tracker.initial.tabId, 1);
});

test("adopts own create results and owned-opener popups, never arbitrary claims", async () => {
  const {tracker} = fixture();
  await tracker.event(created(tab(1)));
  await tracker.event(initialized);
  tracker.request({id: 9, method: "chrome.tabs.create"});
  await tracker.event({id: 9, result: tab(2)});
  await tracker.event(created(tab(3, 2)));
  await assert.rejects(tracker.event(created(tab(4))), /unproven_claim/);
  assert.deepEqual([...tracker.owned.keys()], [1, 2, 3]);
});

test("requires exact removal authority and releases surviving claims on loss", async () => {
  const {tracker, log} = fixture();
  await tracker.event(created(tab(1)));
  await tracker.event(initialized);
  await tracker.event(created(tab(2, 1)));
  assert.throws(() => tracker.request({id: 5, method: "chrome.tabs.remove", params: [[2, 9]]}), /remove_not_owned/);
  tracker.request({id: 6, method: "chrome.tabs.remove", params: [[2]]});
  await tracker.event({id: 6});
  await tracker.disconnect();
  assert.deepEqual(log.slice(2), [["finish", 2], ["release", 1]]);
});

test("binds only the target ID returned for the requested owned Chrome tab", async () => {
  const {tracker} = fixture();
  await tracker.event(created(tab(1)));
  await tracker.event(initialized);
  assert.throws(() => tracker.request({
    id: 7, method: "chrome.debugger.sendCommand", params: [{tabId: 2}, "Target.getTargetInfo"],
  }), /debugger_not_owned/);
  tracker.request({
    id: 8, method: "chrome.debugger.sendCommand", params: [{tabId: 1}, "Target.getTargetInfo"],
  });
  await tracker.event({id: 8, result: {targetInfo: {targetId: "initial-cdp"}}});
  assert.equal(tracker.resolve("initial-cdp", true).tabId, 1);
  assert.throws(() => tracker.resolve("initial-cdp", false), /target_unbound/);
});
