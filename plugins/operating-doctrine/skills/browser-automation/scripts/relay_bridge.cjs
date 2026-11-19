"use strict";

const http = require("node:http");
const { randomUUID } = require("node:crypto");
const { RelayClaims } = require("./relay_claims.cjs");

const maxFrame = 16 * 1024 * 1024;

function vendorEndpoint(value) {
  if (typeof value !== "string" ||
      !/^ws:\/\/(?:127\.0\.0\.1|\[::1\]):[1-9]\d{0,4}\/extension\/[a-f0-9-]{36}$/.test(value))
    throw Error("relay_endpoint_invalid");
  const url = new URL(value);
  if (!url.port || Number(url.port) > 65535)
    throw Error("relay_endpoint_invalid");
  return url.toString();
}

function frame(data, binary) {
  if (binary || data.length > maxFrame)
    throw Error("relay_frame_invalid");
  const value = JSON.parse(data.toString("utf8"));
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw Error("relay_frame_invalid");
  return value;
}

async function startBridge({ ws: WebSocket, wsServer: WebSocketServer }, callbacks) {
  const claims = new RelayClaims(callbacks);
  const endpoint = "/extension/" + randomUUID();
  const server = http.createServer((_, res) => res.writeHead(404).end());
  const wss = new WebSocketServer({ noServer: true, maxPayload: maxFrame });
  let upstream, downstream, destination, stopped = false, used = false;
  let privateSequence = 0;
  const privateReplies = new Map();
  let ordered = Promise.resolve();
  let stopPromise;

  function stop() {
    if (stopPromise)
      return stopPromise;
    stopped = true;
    upstream?.terminate();
    downstream?.terminate();
    for (const reply of privateReplies.values()) reply(null);
    privateReplies.clear();
    stopPromise = ordered.then(() => claims.disconnect()).finally(() => {
      wss.close();
      server.close();
    });
    return stopPromise;
  }

  function fail() {
    stop().catch(() => callbacks.error?.("relay_release_unverified"));
  }

  function enqueue(work) {
    // Use a single ordered chain for claim and command bookkeeping. If a
    // durable receipt fails, do not forward that frame or any later one.
    ordered = ordered.then(async () => {
      if (!stopped)
        await work();
    }).catch(() => {
      callbacks.error?.("relay_frame_refused");
      fail();
    });
  }

  const send = (socket, data) => new Promise((resolve, reject) => {
    if (socket.readyState !== WebSocket.OPEN)
      return reject(Error("relay_closed"));
    socket.send(data, { binary: false }, e => e ? reject(e) : resolve());
  });

  server.on("upgrade", (request, socket, head) => {
    if (stopped || used || !destination || request.url !== endpoint)
      return socket.destroy();
    used = true;
    wss.handleUpgrade(request, socket, head, conn => {
      downstream = conn;
      downstream.on("close", fail);
      downstream.on("error", fail);
      upstream = new WebSocket(destination, { maxPayload: maxFrame });
      const opened = new Promise((resolve, reject) => {
        upstream.once("open", resolve);
        upstream.once("error", reject);
        upstream.once("close", () => reject(Error("relay_closed")));
      });
      opened.catch(() => {});
      upstream.on("close", fail);
      upstream.on("error", fail);
      downstream.on("message", (data, binary) => enqueue(async () => {
        const message = frame(data, binary);
        await claims.event(message);
        if (message.id < 0) {
          const done = privateReplies.get(message.id);
          privateReplies.delete(message.id);
          if (done) done(message.error ? null : {result: message.result});
          return;
        }
        await opened;
        await send(upstream, data);
      }));
      upstream.on("message", (data, binary) => enqueue(async () => {
        const message = frame(data, binary);
        if (!Number.isSafeInteger(message.id) || message.id <= 0)
          throw Error("relay_frame_invalid");
        claims.request(message);
        await send(downstream, data);
      }));
    });
  });

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  return {
    claims,
    install(value) {
      if (destination || stopped)
        throw Error("relay_endpoint_already_bound");
      destination = vendorEndpoint(value);
      const vendor = new URL(destination);
      if (vendor.hostname === "127.0.0.1" && Number(vendor.port) === server.address().port) {
        destination = undefined;
        throw Error("relay_endpoint_is_bridge");
      }
      return `ws://127.0.0.1:${server.address().port}${endpoint}`;
    },
    async privateCall(method, params) {
      const id = --privateSequence;
      const command = {id, method, params};
      let timer;
      const result = await new Promise(resolve => {
        timer = setTimeout(() => resolve(null), 8000);
        privateReplies.set(id, resolve);
        enqueue(async () => {
          claims.request(command);
          await send(downstream, JSON.stringify(command));
        });
      }).finally(() => {
        clearTimeout(timer);
        privateReplies.delete(id);
      });
      if (!result) throw Error("relay_private_reply_unverified");
      return result.result;
    },
    stop,
  };
}

module.exports = { startBridge, vendorEndpoint };
