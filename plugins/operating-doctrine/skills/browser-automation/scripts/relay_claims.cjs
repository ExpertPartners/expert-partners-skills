"use strict";

const validId = value => Number.isInteger(value) && value > 0 && value <= 2147483647;

function project(tab) {
  if (!validId(tab?.id) || !validId(tab?.windowId) || typeof tab.url !== "string")
    throw Error("relay_identity_unavailable");
  const urlClass = tab.url === "about:blank" || tab.url.startsWith("about:blank#") ? "blank" :
    tab.url.startsWith("https://") ? "https" : tab.url.startsWith("http://") ? "http" :
    tab.url.startsWith("chrome-extension://") ? "extension" : "other";
  return {tabId: tab.id, windowId: tab.windowId, urlClass};
}

// Consume exactly one vendor relay stream, serially. The transport must await
// each hook before forwarding the frame to the Playwright client.
class RelayClaims {
  constructor({claim, release, finish, observe}) {
    this.claim = claim;
    this.release = release;
    this.finish = finish;
    this.observe = observe;
    this.initial = null;
    this.initialized = false;
    this.owned = new Map();
    this.seen = new Set();
    this.commands = new Map();
    this.targets = new Map();
  }

  async adopt(tab) {
    const record = project(tab);
    if (this.seen.has(record.tabId))
      throw Error("relay_claim_reannounced");
    this.owned.set(record.tabId, await this.claim(record));
    this.seen.add(record.tabId);
    return record;
  }

  request(message) {
    if (!Number.isSafeInteger(message.id) || this.commands.has(message.id))
      throw Error("relay_duplicate_or_invalid_command");
    if (!this.initialized)
      throw Error("relay_not_initialized");
    if (message.method === "chrome.tabs.create") {
      this.commands.set(message.id, {method: "create"});
    } else if (message.method === "chrome.tabs.remove") {
      const ids = [message.params?.[0]].flat();
      if (!ids.length || new Set(ids).size !== ids.length ||
          ids.some(id => !validId(id) || !this.owned.has(id)))
        throw Error("relay_remove_not_owned");
      this.commands.set(message.id, {method: "remove", records: ids.map(id => this.owned.get(id))});
    } else if (message.method.startsWith("chrome.debugger.")) {
      const id = message.params?.[0]?.tabId;
      if (!validId(id) || !this.owned.has(id))
        throw Error("relay_debugger_not_owned");
      if (message.method === "chrome.debugger.sendCommand" &&
          message.params[1] === "Target.getTargetInfo" && !message.params[0].sessionId)
        this.commands.set(message.id, {method: "target", id});
    }
  }

  async event(message) {
    switch (message.method) {
      case "chrome.tabs.onCreated": {
        const tab = message.params?.[0];
        if (!this.initialized) {
          if (this.initial)
            throw Error("relay_initial_claim_ambiguous");
          // The token-only vendor launch may announce before the blank
          // navigation has committed. The independent census checks after.
          this.initial = await this.adopt(tab);
        } else {
          if (!validId(tab?.openerTabId) || !this.owned.has(tab.openerTabId))
            throw Error("relay_unproven_claim");
          await this.adopt(tab);
        }
        return;
      }
      case "extension.initialized":
        if (this.initialized || !this.initial)
          throw Error("relay_initial_claim_unavailable");
        this.initialized = true;
        return;
      case "chrome.tabs.onRemoved": {
        const id = message.params?.[0];
        const claim = this.owned.get(id);
        if (claim) {
          await this.finish(claim);
          this.owned.delete(id);
        }
        return;
      }
      case "chrome.debugger.onDetach": {
        const id = message.params?.[0]?.tabId;
        const claim = this.owned.get(id);
        if (claim) {
          await this.release(claim);
          this.owned.delete(id);
        }
        return;
      }
    }
    if (!this.commands.has(message.id))
      return;
    const command = this.commands.get(message.id);
    this.commands.delete(message.id);
    if (message.error)
      return;
    if (command.method === "create") {
      await this.adopt(message.result);
    } else if (command.method === "target") {
      const claim = this.owned.get(command.id);
      const info = message.result?.targetInfo;
      if (!claim || typeof info?.targetId !== "string" || !info.targetId)
        throw Error("relay_target_unbound");
      const previous = this.targets.get(info.targetId);
      if (previous !== undefined && previous !== command.id)
        throw Error("relay_target_ambiguous");
      this.targets.set(info.targetId, command.id);
    } else {
      for (const claim of command.records) {
        await this.finish(claim);
        this.owned.delete(claim.tabId);
      }
    }
  }

  async disconnect() {
    for (const claim of this.owned.values())
      await this.release(claim);
    this.owned.clear();
    this.commands.clear();
    this.targets.clear();
  }

  resolve(target, initial) {
    const id = this.targets.get(target);
    const claim = this.owned.get(id);
    if (!claim || (claim.tabId === this.initial?.tabId) !== initial)
      throw Error("relay_target_unbound");
    return claim;
  }

  async checkpointTarget(target, url) {
    return await this.checkpointTab(this.targets.get(target), url);
  }

  async checkpointTab(id, url) {
    const claim = this.owned.get(id);
    if (!claim || !this.observe)
      throw Error("relay_target_unbound");
    const observation = project({id, windowId: claim.windowId, url});
    const updated = await this.observe(claim, observation);
    this.owned.set(id, updated);
    return updated;
  }
}

module.exports = { RelayClaims, project };
