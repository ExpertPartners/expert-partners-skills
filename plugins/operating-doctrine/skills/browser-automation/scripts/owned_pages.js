/* One private MCP process. Birth provenance is independent of group membership. */
async function newOwnedState(connector) {
  const context = connector.context();
  // Chrome can hand a --new-window launch to the most recently created window
  // when connections start close together, so two jobs once shared a window.
  // Move this connector into its own window before recording ownership.
  await connector.evaluate(async () => {
    const t = await chrome.tabs.getCurrent();
    const others = (await chrome.tabs.query({windowId: t.windowId})).filter(x => x.id !== t.id);
    if (!others.length) return;
    const g = await chrome.tabGroups.get(t.groupId);
    const w = await chrome.windows.create({tabId: t.id, focused: false});
    const groupId = await chrome.tabs.group({tabIds: [t.id], createProperties: {windowId: w.id}});
    await chrome.tabGroups.update(groupId, {title: g.title, color: g.color});
    const placed = await chrome.tabs.query({windowId: w.id});
    if (placed.length !== 1 || placed[0].id !== t.id) throw Error('owned_window_isolation_failed');
  });
  const initial = await connector.evaluate(async () => {
    const t = await chrome.tabs.getCurrent();
    const g = await chrome.tabGroups.get(t.groupId);
    return {connectorId: t.id, windowId: t.windowId, groupId: t.groupId, groupTitle: g.title};
  });
  const s = {connector, task: null, initial, created: new Set([connector]),
    ids: new Map([[connector, initial.connectorId]]), tabIds: new Set([initial.connectorId]),
    closedIds: new Set(), pendingIds: new Set()};

  s.create = async () => {
    const proc = Buffer.constructor('return process')();
    const marker = 'about:blank#ep-owned-' + proc.getBuiltinModule('node:crypto').randomUUID();
    // Chrome supplies the birth ID directly in an explicitly owned window.
    // Avoid Target.createTarget's implicit active-window placement and do not
    // navigate an unbound SDK Page to establish identity.
    const id = await connector.evaluate(async ({initial, marker}) => {
      const t = await chrome.tabs.create({windowId: initial.windowId, url: marker, active: true});
      return t.id;
    }, {initial, marker});
    s.tabIds.add(id);
    s.pendingIds.add(id);
    await connector.evaluate(async ({initial, id}) => {
      const t = await chrome.tabs.get(id);
      if (t.windowId !== initial.windowId) throw Error('created_tab_transferred');
      await chrome.tabs.group({groupId: initial.groupId, tabIds: [id]});
    }, {initial, id});
    let matches = [];
    for (let attempt = 0; attempt < 100; attempt++) {
      matches = context.pages().filter(p => p.url() === marker);
      if (matches.length === 1) break;
      if (matches.length > 1) throw Error('owned_marker_ambiguous');
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    if (matches.length !== 1) throw Error('owned_page_binding_failed');
    const p = matches[0];
    s.created.add(p);
    s.ids.set(p, id);
    s.pendingIds.delete(id);
    return p;
  };
  context.newPage = s.create; // Private client instance only, never vendor source.

  s.discoverPopups = async () => {
    let changed;
    do {
      changed = false;
      for (const p of context.pages()) {
        if (s.created.has(p)) continue;
        const opener = await p.opener();
        if (opener && s.created.has(opener)) { s.created.add(p); changed = true; }
      }
    } while (changed);
    for (const p of s.created) {
      if (p.isClosed() || s.ids.has(p)) continue;
      const opener = await p.opener();
      if (!opener || !s.ids.has(opener)) continue;
      const matches = await connector.evaluate(async ({openerId, url, initial}) => {
        const tabs = await chrome.tabs.query({windowId: initial.windowId});
        return tabs.filter(t => t.groupId === initial.groupId && t.openerTabId === openerId && t.url === url).map(t => t.id);
      }, {openerId: s.ids.get(opener), url: p.url(), initial});
      if (matches.length === 1 && !s.tabIds.has(matches[0])) {
        s.ids.set(p, matches[0]); s.tabIds.add(matches[0]);
      }
    }
  };

  s.snapshot = async (strict = true) => {
    await s.discoverPopups();
    const knownIds = [...s.tabIds].filter(id => !s.closedIds.has(id));
    const observed = await connector.evaluate(async ({initial, knownIds, pendingIds}) => {
      const self = await chrome.tabs.getCurrent();
      const g = await chrome.tabGroups.get(self.groupId);
      if (self.id !== initial.connectorId || self.windowId !== initial.windowId || self.groupId !== initial.groupId || g.title !== initial.groupTitle)
        throw Error('connection_ownership_changed');
      for (const id of knownIds) {
        let t;
        try { t = await chrome.tabs.get(id); } catch { throw Error('saved_owned_tab_missing'); }
        if (t.windowId !== initial.windowId) throw Error('owned_tab_transferred');
        if (t.groupId !== initial.groupId) {
          if (!pendingIds.includes(id) || t.groupId !== -1) throw Error('owned_tab_transferred');
          const targets = await chrome.debugger.getTargets();
          if (targets.some(x => x.tabId === id && x.attached)) throw Error('owned_tab_claimed');
        }
      }
      const group = await chrome.tabs.query({groupId: initial.groupId, windowId: initial.windowId});
      // Watermark for failed cleanup: tab IDs only grow within one Chrome run.
      const newestTabId = Math.max(0, ...(await chrome.tabs.query({})).map(t => t.id));
      return {unknownIds: group.filter(t => !knownIds.includes(t.id)).map(t => t.id), newestTabId};
    }, {initial, knownIds, pendingIds: [...s.pendingIds]});
    const unknownPages = context.pages().filter(p => !s.created.has(p));
    const unbound = [...s.created].filter(p => !s.ids.has(p)).length + s.pendingIds.size;
    if (strict && (unknownPages.length || observed.unknownIds.length || unbound)) throw Error('unproven_page_arrival');
    return {...initial, tabIds: knownIds, unboundOwnedPages: unbound, newestTabId: observed.newestTabId};
  };

  s.closeIds = async (ids) => {
    const closed = await connector.evaluate(async ({ids, initial, knownIds, pendingIds}) => {
      const before = await chrome.tabs.query({});
      const beforeIds = new Set(before.map(t => t.id));
      const descendants = new Set(knownIds);
      let changed;
      do {
        changed = false;
        for (const t of before) if (descendants.has(t.openerTabId) && !descendants.has(t.id)) {
          descendants.add(t.id); changed = true;
        }
      } while (changed);
      if (before.some(t => descendants.has(t.id) && !knownIds.includes(t.id))) throw Error('uncheckpointed_page_arrival');
      for (const id of knownIds) if (!beforeIds.has(id)) throw Error('saved_owned_tab_missing');
      for (const id of ids) {
        const t = before.find(t => t.id === id);
        if (t.windowId !== initial.windowId || (t.groupId !== initial.groupId && !(pendingIds.includes(id) && t.groupId === -1)))
          throw Error('owned_tab_transferred');
      }
      if (ids.length) await chrome.tabs.remove(ids);
      const after = await chrome.tabs.query({});
      // Chrome drops openerTabId when the opener disappears. Global ID deltas
      // detect newly born tabs even when that ancestry signal is already gone.
      if (after.some(t => ids.includes(t.id) || !beforeIds.has(t.id))) throw Error('owned_page_close_inventory_uncertain');
      return ids;
    }, {ids, initial, knownIds: [...s.tabIds].filter(id => !s.closedIds.has(id)), pendingIds: [...s.pendingIds]});
    for (const id of closed) { s.closedIds.add(id); s.pendingIds.delete(id); }
  };

  s.closePage = async (p) => {
    if (!s.created.has(p) || p === connector || !s.ids.has(p)) throw Error('page_close_not_owned');
    await s.closeIds([s.ids.get(p)]);
  };
  s.closeCreated = async () => {
    await s.discoverPopups();
    if ([...s.created].some(p => !s.ids.has(p))) throw Error('unbound_owned_page_cleanup_uncertain');
    await s.closeIds([...s.tabIds].filter(id => id !== initial.connectorId && !s.closedIds.has(id)));
  };
  s.closeWindow = async () => {
    // All owned work pages have already closed. A window that also holds an
    // unknown tab (Allison's or a peer's) is kept; only this connector closes.
    return await connector.evaluate(async (initial) => {
      const self = await chrome.tabs.getCurrent();
      const tabs = await chrome.tabs.query({windowId: initial.windowId});
      if (self.id !== initial.connectorId || self.windowId !== initial.windowId) throw Error('connection_ownership_changed');
      if (tabs.length !== 1 || tabs[0].id !== self.id) {
        setTimeout(() => chrome.tabs.remove(self.id), 250);
        return {scheduled: true, shared: true, windowId: initial.windowId};
      }
      setTimeout(async () => {
        const remaining = await chrome.tabs.query({windowId: initial.windowId});
        if (remaining.length === 1 && remaining[0].id === self.id)
          await chrome.windows.remove(initial.windowId);
        else
          await chrome.tabs.remove(self.id);
      }, 250);
      return {scheduled: true, shared: false, windowId: initial.windowId};
    }, initial);
  };
  return s;
}
