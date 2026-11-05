/* Page creation provenance for one private MCP process. Never infer it from a group. */
async function newOwnedState(connector) {
  const context = connector.context();
  const initial = await connector.evaluate(async () => {
    const t = await chrome.tabs.getCurrent();
    const g = await chrome.tabGroups.get(t.groupId);
    return {connectorId: t.id, windowId: t.windowId, groupId: t.groupId, groupTitle: g.title};
  });
  const s = {connector, task: null, initial, created: new Set([connector]), ids: new Map([[connector, initial.connectorId]])};
  const originalNewPage = context.newPage.bind(context);

  s.create = async () => {
    const p = await originalNewPage();
    // Retain the exact returned Page before any navigation can fail. It is safe
    // to close this reference even if Chrome-ID binding subsequently fails.
    s.created.add(p);
    const proc = Buffer.constructor('return process')();
    const marker = 'about:blank#ep-owned-' + proc.getBuiltinModule('node:crypto').randomUUID();
    await p.goto(marker, {waitUntil: 'domcontentloaded'});
    let found;
    for (let attempt = 0; attempt < 30; attempt++) {
      found = await connector.evaluate(async ({marker, initial}) => {
        const tabs = await chrome.tabs.query({windowId: initial.windowId});
        return tabs.filter(t => t.url === marker && t.groupId === initial.groupId).map(t => t.id);
      }, {marker, initial});
      if (found.length === 1) break;
      if (found.length > 1) throw Error('owned_marker_ambiguous');
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    if (found.length !== 1) throw Error('owned_marker_binding_failed');
    s.ids.set(p, found[0]);
    // This changes only the fragment of our just-created blank page. The bound
    // Chrome ID, rather than its URL, persists through later business navigation.
    await p.evaluate(() => { try { history.replaceState(null, '', 'about:blank'); } catch {} });
    return p;
  };
  // Also cover context.newPage used by ordinary MCP tools or authorized code.
  // The override belongs to this private client object, never vendor source.
  context.newPage = s.create;

  s.discoverPopups = async () => {
    let changed;
    do {
      changed = false;
      for (const p of context.pages()) {
        if (s.created.has(p)) continue;
        const opener = await p.opener();
        if (opener && s.created.has(opener)) {
          s.created.add(p);
          changed = true;
        }
      }
    } while (changed);
    // Bind a popup only when both its retained opener and Chrome's openerTabId
    // establish birth from an already-bound owned Page. Ambiguity is a refusal.
    for (const p of s.created) {
      if (p.isClosed() || s.ids.has(p)) continue;
      const opener = await p.opener();
      if (!opener || !s.ids.has(opener)) continue;
      const matches = await connector.evaluate(async ({openerId, url, initial}) => {
        const tabs = await chrome.tabs.query({windowId: initial.windowId});
        return tabs.filter(t => t.groupId === initial.groupId && t.openerTabId === openerId && t.url === url).map(t => t.id);
      }, {openerId: s.ids.get(opener), url: p.url(), initial});
      if (matches.length === 1 && ![...s.ids.values()].includes(matches[0])) s.ids.set(p, matches[0]);
    }
  };

  s.snapshot = async (strict = true) => {
    await s.discoverPopups();
    const knownIds = [...s.ids.values()];
    const observed = await connector.evaluate(async ({initial, knownIds}) => {
      const self = await chrome.tabs.getCurrent();
      const g = await chrome.tabGroups.get(self.groupId);
      if (self.id !== initial.connectorId || self.windowId !== initial.windowId || self.groupId !== initial.groupId || g.title !== initial.groupTitle)
        throw Error('connection_ownership_changed');
      for (const id of knownIds) {
        let t;
        try { t = await chrome.tabs.get(id); } catch { continue; }
        if (t.windowId !== initial.windowId || t.groupId !== initial.groupId) throw Error('owned_tab_transferred');
      }
      const group = await chrome.tabs.query({groupId: initial.groupId, windowId: initial.windowId});
      return {unknownIds: group.filter(t => !knownIds.includes(t.id)).map(t => t.id)};
    }, {initial, knownIds});
    const unknownPages = context.pages().filter(p => !s.created.has(p));
    // A detached SDK Page can report closed while its Chrome tab still exists.
    // Without an ID, that outcome cannot be certified as cleaned up.
    const unboundPages = [...s.created].filter(p => !s.ids.has(p));
    if (strict && (unknownPages.length || observed.unknownIds.length || unboundPages.length)) throw Error('unproven_page_arrival');
    return {...initial, tabIds: knownIds, unboundOwnedPages: unboundPages.length};
  };

  s.closeCreated = async () => {
    await s.discoverPopups();
    if ([...s.created].some(p => !s.ids.has(p))) throw Error('unbound_owned_page_cleanup_uncertain');
    // Unknown arrivals stay open even when the extension exposed them in this
    // context. Cleanup is by creation-proven Page references, not context.pages.
    for (const p of s.created) if (p !== connector && !p.isClosed()) await p.close();
    // A retained Page may have detached and been reattached as a new SDK object.
    // Its creation-proven Chrome ID remains authoritative within this epoch.
    const ids = [...s.ids.values()].filter(id => id !== initial.connectorId);
    await connector.evaluate(async ({ids, initial}) => {
      const live = [];
      for (const id of ids) {
        let tab;
        try { tab = await chrome.tabs.get(id); } catch { continue; }
        if (tab.windowId !== initial.windowId || tab.groupId !== initial.groupId) throw Error('owned_tab_transferred');
        live.push(id);
      }
      if (live.length) await chrome.tabs.remove(live);
      const all = await chrome.tabs.query({});
      const known = new Set([...ids, initial.connectorId]);
      const descendants = new Set(known);
      let changed;
      do {
        changed = false;
        for (const tab of all) if (descendants.has(tab.openerTabId) && !descendants.has(tab.id)) {
          descendants.add(tab.id);
          changed = true;
        }
      } while (changed);
      if (all.some(tab => ids.includes(tab.id) || (descendants.has(tab.id) && !known.has(tab.id))))
        throw Error('late_owned_popup_cleanup_uncertain');
    }, {ids, initial});
  };
  return s;
}
