"use strict";

const fs = require("node:fs");
const net = require("node:net");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { startBridge } = require("./relay_bridge.cjs");

async function main() {
  const [socket, bundle, python, ledger, generation, job] = process.argv.slice(2);
  if (![socket, bundle, python, ledger].every(path.isAbsolute) || !generation || !job)
    throw Error("relay_broker_settings_invalid");
  process.umask(0o077);
  function persist(operation, value) {
    const result = spawnSync(python, [
      path.join(__dirname, "relay_ownership.py"), ledger, generation, job, operation,
    ], {input: JSON.stringify(value), timeout: 17500, maxBuffer: 8192, encoding: "utf8"});
    if (result.status !== 0)
      throw Error("relay_ledger_refused");
    return JSON.parse(result.stdout);
  }

  const bridge = await startBridge(require(bundle), {
    claim: tab => persist("claim", {tab}),
    observe: (claim, tab) => persist("observe", {claim, tab}),
    release: claim => persist("release", {claim}),
    finish: claim => persist("finish", {claim}),
    error: code => process.stderr.write(code + "\n"),
  });

  async function call(input) {
    switch (input?.method) {
      case "install":
        return bridge.install(input.url);
      case "resolve":
        return bridge.claims.resolve(input.target, input.initial === true);
      case "bindPage": {
        if (typeof input.marker !== "string" || !/^[a-f0-9]{32}$/.test(input.marker))
          throw Error("relay_page_marker_invalid");
        const eligible = [...bridge.claims.owned.values()].filter(
          row => (row.tabId === bridge.claims.initial?.tabId) === input.initial
        );
        const key = JSON.stringify("__ep_owned_" + input.marker);
        const seen = await Promise.all(eligible.map(async row => {
          const value = await bridge.privateCall("chrome.debugger.sendCommand", [
            {tabId: row.tabId}, "Runtime.evaluate",
            {expression: `Object.prototype.hasOwnProperty.call(globalThis,${key})`, returnByValue: true},
          ]);
          return value?.result?.value === true ? row : null;
        }));
        const matches = seen.filter(Boolean);
        if (matches.length !== 1 || !bridge.claims.owned.has(matches[0].tabId))
          throw Error("relay_page_marker_unbound");
        return matches[0];
      }
      case "observe":
        return await bridge.claims.checkpointTarget(input.target, input.url);
      case "observeTab":
        return await bridge.claims.checkpointTab(input.tabId, input.url);
      case "close":
        await bridge.privateCall("chrome.tabs.remove", [[input.tabId]]);
        return true;
      case "status":
        return {initialized: bridge.claims.initialized, claims: [...bridge.claims.owned.values()]};
      default:
        throw Error("relay_rpc_invalid");
    }
  }

  const server = net.createServer(conn => {
    let data = Buffer.alloc(0);
    let received = false;
    conn.setTimeout(20000, () => conn.destroy());
    conn.on("error", () => {});
    conn.on("data", chunk => {
      if (received || chunk.length + data.length > 16384) return conn.destroy();
      data = Buffer.concat([data, chunk]);
      if (!data.includes(10)) return;
      received = true;
      Promise.resolve().then(() => call(JSON.parse(data.toString())))
        .then(result => conn.end(JSON.stringify({result}) + "\n"),
              () => conn.end('{"error":"relay_rpc_refused"}\n'));
    });
  });
  let closing = false;
  async function shutdown() {
    if (closing) return;
    closing = true;
    server.close();
    try {
      await bridge.stop();
    } catch {
      process.exitCode = 2;
    }
  }
  server.once("error", shutdown);
  process.once("SIGTERM", shutdown);
  process.once("SIGINT", shutdown);
  server.listen(socket, () => {
    fs.chmodSync(socket, 0o600);
    process.stdout.write("ready\n");
  });
}

main().catch(() => {
  process.stderr.write("relay_broker_failed\n");
  process.exitCode = 2;
});
