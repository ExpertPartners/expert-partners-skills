/* V2 keeps authority in the relay, never in an about:blank page. */
async function newRelayOwnedState(connector, broker) {
  const context = connector.context();
  const newPage = context.newPage.bind(context);
  const created = new Set();
  const ids = new Map();
  const windows = new Map();

  async function claimFor(page, initial) {
    const marker = broker.marker();
    const key = "__ep_owned_" + marker;
    await page.evaluate(k => Object.defineProperty(globalThis, k, {value: true, configurable: true}), key);
    try {
      return await broker.bindPage(marker, initial);
    } finally {
      await page.evaluate(k => { delete globalThis[k]; }, key);
    }
  }

  function bind(page, claim) {
    if (!claim || ids.has(page) || [...ids.values()].includes(claim.tabId))
      throw Error("owned_page_binding_failed");
    ids.set(page, claim.tabId);
    windows.set(page, claim.windowId);
    created.add(page);
    return claim;
  }

  const initial = bind(connector, await claimFor(connector, true));
  const s = {connector, task: null, initial: {
    connectorId: initial.tabId, windowId: initial.windowId,
    groupId: null, groupTitle: null,
  }, created, ids};

  s.create = async () => {
    const page = await newPage();
    const claim = await claimFor(page, false);
    if (!claim) throw Error("owned_page_binding_failed");
    bind(page, claim);
    return page;
  };
  context.newPage = s.create;

  s.snapshot = async (strict = true) => {
    for (const page of context.pages()) {
      if (created.has(page)) continue;
      const opener = await page.opener();
      if (!opener || !created.has(opener)) {
        if (strict) throw Error("unproven_page_arrival");
        continue;
      }
      const claim = await claimFor(page, false);
      if (!claim) {
        if (strict) throw Error("owned_page_binding_failed");
        continue;
      }
      bind(page, claim);
    }
    const records = [];
    for (const page of created) {
      if (page.isClosed()) continue;
      const current = await broker.observe(ids.get(page), page.url());
      if (current?.tabId !== ids.get(page) || current.windowId !== windows.get(page))
        throw Error("connection_ownership_changed");
      records.push(current);
    }
    if (connector.isClosed()) throw Error("connection_ownership_changed");
    const workingPage = s.task ? (s.task.isClosed() ? "closed" : "live") : "none";
    return {...s.initial, tabIds: records.map(tab => tab.tabId), unboundOwnedPages: 0, workingPage};
  };

  s.closePage = async page => {
    if (page === connector || !created.has(page) || page.isClosed())
      throw Error("page_close_not_owned");
    await broker.close(ids.get(page));
  };
  s.closeCreated = async () => {
    await s.snapshot();
    for (const page of created) {
      if (page !== connector && !page.isClosed()) await s.closePage(page);
    }
  };
  return s;
}

if (typeof module !== "undefined") module.exports = {newRelayOwnedState};
