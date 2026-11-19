const test = require("node:test");
const assert = require("node:assert/strict");
const {once} = require("node:events");
const {startBridge, vendorEndpoint} = require("../../plugins/operating-doctrine/skills/browser-automation/scripts/relay_bridge.cjs");

const bundle = process.env.EP_TEST_PLAYWRIGHT_BUNDLE;
const path = "/extension/01234567-abcd-4def-8123-0123456789ab";

test("vendor endpoint is strictly loopback and requires the relay path", () => {
  assert.equal(vendorEndpoint("ws://127.0.0.1:3456" + path), "ws://127.0.0.1:3456" + path);
  assert.equal(vendorEndpoint("ws://[::1]:3456" + path), "ws://[::1]:3456" + path);
  for (const value of [
    "ws://127.0.0.1:3456/other",
    "ws://127.0.0.2:3456" + path,
    "ws://[::]:3456" + path,
    "ws://[::ffff:127.0.0.1]:3456" + path,
    "ws://[2001:db8::1]:3456" + path,
    "ws://127.0.0.1:70000" + path,
    "ws://example.com:3456" + path,
    "ws://127.0.0.1:3456" + path + "?a=1",
  ])
    assert.throws(() => vendorEndpoint(value));
});

test("the proxy gates wire traffic on durable claim hooks", {skip: !bundle, timeout: 4000}, async () => {
  const wire = require(bundle);
  const vendor = new wire.wsServer({host: "::1", port: 0});
  await once(vendor, "listening");
  const records = [];
  const bridge = await startBridge(wire, {
    claim: async row => { records.push(["claim", row.tabId]); return row; },
    release: async row => { records.push(["release", row.tabId]); },
    finish: async row => { records.push(["finish", row.tabId]); },
  });
  try {
    const connected = once(vendor, "connection");
    const extension = new wire.ws(bridge.install("ws://[::1]:" + vendor.address().port + path));
    await once(extension, "open");
    const [upstream] = await connected;
    const first = once(upstream, "message");
    extension.send(JSON.stringify({
      method: "chrome.tabs.onCreated",
      params: [{id: 5, windowId: 4, url: "about:blank"}],
    }));
    await first;
    assert.deepEqual(records, [["claim", 5]]);

    const initialized = once(upstream, "message");
    extension.send(JSON.stringify({method: "extension.initialized", params: []}));
    await initialized;
    const removal = once(extension, "message");
    upstream.send(JSON.stringify({id: 10, method: "chrome.tabs.remove", params: [[5]]}));
    await removal;
    const confirmed = once(upstream, "message");
    extension.send(JSON.stringify({id: 10}));
    await confirmed;
    assert.deepEqual(records, [["claim", 5], ["finish", 5]]);
  } finally {
    await bridge.stop();
    vendor.close();
  }
});
