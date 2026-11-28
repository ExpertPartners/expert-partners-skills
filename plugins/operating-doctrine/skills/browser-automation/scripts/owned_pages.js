/* One private MCP process. Birth provenance is independent of group membership. */
async function newOwnedState(connector, birth = null) {
  const context = connector.context();
  // The Python receipt saves the nonce before this call. The private Node
  // process fsyncs returned birth IDs before moving the group. If an evaluate
  // response is lost, the seed's nonce still identifies that one creation.
  const record = data => {
    if (!birth) return;
    const fs = Buffer.constructor('return process')().getBuiltinModule('node:fs');
    const {path, ...identity} = birth;
    const temp = path + '.tmp';
    const fd = fs.openSync(temp, 'wx', 0o600);
    try {
      fs.writeFileSync(fd, JSON.stringify({...identity, ...data}));
      fs.fsyncSync(fd);
    } finally { fs.closeSync(fd); }
    fs.renameSync(temp, path);
    const parent = Buffer.constructor('return process')().getBuiltinModule('node:path').dirname(path);
    const directory = fs.openSync(parent, 'r');
    try { fs.fsyncSync(directory); } finally { fs.closeSync(directory); }
  };
  // Extension 0.6.0 creates the first group in the last-focused window
  // (microsoft/playwright#44302). Keep the existing group when isolating:
  // windows.create({tabId}) ungroups the tab and the extension releases it.
  // Remove this fallback once a released extension pins first-group windowId.
  const origin = await connector.evaluate(async expected => {
    const t = await chrome.tabs.getCurrent();
    if (expected) {
      let exact = false;
      try { exact = JSON.parse(new URL(t.url).searchParams.get('client')).name === expected; } catch {}
      if (!exact) throw Error('birth_connector_changed');
    }
    const others = (await chrome.tabs.query({windowId: t.windowId})).filter(x => x.id !== t.id);
    const g = await chrome.tabGroups.get(t.groupId);
    const initial = {connectorId:t.id,windowId:t.windowId,groupId:t.groupId,groupTitle:g.title};
    if (!others.length) return {...initial, shared:false};
    const members = await chrome.tabs.query({groupId: t.groupId});
    if (t.groupId < 0 || members.length !== 1 || members[0].id !== t.id)
      throw Error('owned_window_isolation_unproven');
    return {...initial, shared:true};
  }, birth?.client_name);
  if (birth) {
    if (birth.connectorId !== null && origin.connectorId !== birth.connectorId)
      throw Error('birth_connector_changed');
    birth = {...birth,connectorId:origin.connectorId,sourceWindowId:origin.windowId};
  }
  record({stage:'observed', origin});
  if (origin.shared) {
    const marker = birth ? birth.marker : 'about:blank';
    record({stage:'creating', origin});
    const created = await connector.evaluate(async marker => {
      const w = await chrome.windows.create({url:marker, focused:false});
      const t = w.tabs?.[0];
      if (!t || w.tabs.length !== 1 || t.windowId !== w.id || t.groupId !== -1 ||
          !(t.url === marker || (t.url === '' && t.pendingUrl === marker)))
        throw Error('owned_window_isolation_unproven');
      return {windowId:w.id,seedId:t.id};
    }, marker);
    record({stage:'created', origin, ...created});
    await connector.evaluate(async ({origin, created, marker}) => {
      const blankSeed = t => t.url === marker || (t.url === '' && t.pendingUrl === marker);
      const t = await chrome.tabs.getCurrent();
      const members = await chrome.tabs.query({groupId:origin.groupId});
      const destination = await chrome.tabs.query({windowId:created.windowId});
      if (t.id !== origin.connectorId || t.windowId !== origin.windowId || t.groupId !== origin.groupId ||
          destination.length !== 1 || destination[0].id !== created.seedId ||
          destination[0].groupId !== -1 || !blankSeed(destination[0]) ||
          members.length !== 1 || members[0].id !== t.id)
        throw Error('owned_window_isolation_unproven');
      await chrome.tabGroups.move(t.groupId, {windowId:created.windowId,index:-1});
      const moved = await chrome.tabs.query({windowId:created.windowId});
      if (moved.length !== 2 || !moved.some(x => x.id === t.id && x.groupId === t.groupId) ||
          !moved.some(x => x.id === created.seedId && x.groupId === -1 && blankSeed(x)))
        throw Error('owned_window_isolation_failed');
    }, {origin, created, marker});
    // Persist the isolated IDs BEFORE removing the unique seed. Even a lost
    // remove response now leaves exact evidence outside the dying transport.
    record({stage:'isolated', origin, ...created});
    await connector.evaluate(async ({created, origin}) => {
      await chrome.tabs.remove(created.seedId);
      const placed = await chrome.tabs.query({windowId:created.windowId});
      if (placed.length !== 1 || placed[0].id !== origin.connectorId ||
          placed[0].groupId !== origin.groupId)
        throw Error('owned_window_isolation_failed');
    }, {created, origin});
  } else {
    record({stage:'isolated', origin, windowId:origin.windowId});
  }
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

  // Extension 0.6.0 can reannounce a still-owned tab after a native debugger
  // target closes. Let that private transport attach; never attach or navigate
  // a target ourselves. The pinned in-process SDK exposes the CDP target ID.
  s.navigationReplacement = async (expected) => {
    const old = s.task;
    if (!old || !old.isClosed()) return null;
    const id = s.ids.get(old);
    if (!s.created.has(old) || !s.tabIds.has(id) || s.closedIds.has(id) ||
        id === initial.connectorId || s.pendingIds.size) throw Error('owned_replacement_unproven');
    const knownIds = [...s.tabIds].filter(tabId => !s.closedIds.has(tabId));
    for (let attempt = 0; attempt < (expected ? 1 : 10); attempt++) {
      const observed = await connector.evaluate(async ({initial, knownIds, id}) => {
        const self = await chrome.tabs.getCurrent();
        const group = await chrome.tabGroups.get(self.groupId);
        const tabs = await chrome.tabs.query({windowId: initial.windowId});
        if (self.id !== initial.connectorId || self.windowId !== initial.windowId ||
            self.groupId !== initial.groupId || group.title !== initial.groupTitle ||
            tabs.length !== knownIds.length ||
            tabs.some(t => t.groupId !== initial.groupId || !knownIds.includes(t.id)))
          throw Error('owned_replacement_unproven');
        const task = tabs.find(t => t.id === id);
        if (!task || !task.url?.startsWith('https://')) return null;
        if (task.pendingUrl || task.status !== 'complete') return {};
        const targets = (await chrome.debugger.getTargets()).filter(t =>
          t.tabId === id && t.type === 'page');
        if (targets.length !== 1 || !targets[0].attached || !targets[0].id) return {};
        return {targetId: targets[0].id, origin: new URL(task.url).origin};
      }, {initial, knownIds, id});
      if (observed === null) return null;
      const unknown = context.pages().filter(p => !s.created.has(p));
      if (unknown.length > 1) throw Error('owned_replacement_unproven');
      if (observed.targetId && unknown.length === 1) {
        const page = unknown[0];
        const sdkTarget = page._connection?.toImpl?.(page)?.delegate?._targetId;
        if (page.isClosed() || sdkTarget !== observed.targetId ||
            new URL(page.url()).origin !== observed.origin ||
            context.pages().some(p => p !== page && !s.ids.has(p)))
          throw Error('owned_replacement_unproven');
        if (expected) {
          if (expected.targetId !== observed.targetId || expected.origin !== observed.origin)
            throw Error('owned_replacement_changed');
          s.created.delete(old);
          s.ids.delete(old);
          s.created.add(page);
          s.ids.set(page, id);
          s.task = page;
        }
        return observed;
      }
      if (!expected) await new Promise(resolve => setTimeout(resolve, 100));
    }
    return null;
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
    const workingPage = s.task ? (s.task.isClosed() ? 'closed' : 'live') : 'none';
    return {...initial, tabIds: knownIds, unboundOwnedPages: unbound, newestTabId: observed.newestTabId, workingPage};
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

// Called only after the allocating transport has stopped, in the same Chrome
// generation, through a fresh owned maintenance connector. No whole-window
// removal: close only the nonce seed and the exact, client-verified connector.
async function reconcileIsolationBirth(connector, birth) {
  return connector.evaluate(async b => {
    const read = async () => {
      const tabs = await chrome.tabs.query({});
      const seeds = tabs.filter(t => t.url === b.marker || (t.url === '' && t.pendingUrl === b.marker));
      if (seeds.length > 1) throw Error('birth_marker_ambiguous');
      const seed = seeds[0];
      if (seed && (seed.groupId !== -1 || (b.seedId !== undefined && seed.id !== b.seedId) ||
          (b.windowId !== undefined && seed.windowId !== b.windowId)))
        throw Error('birth_seed_transferred');
      const savedSeed = tabs.find(t => t.id === b.seedId);
      if (savedSeed && savedSeed !== seed) throw Error('birth_seed_changed');
      const removed = b.cleanup && Array.isArray(b.cleanup.tabIds) && b.cleanup.tabIds.length &&
        b.cleanup.tabIds.every(id => !tabs.some(t => t.id === id)) && !seed;
      if (b.stage === 'intent' || (b.stage === 'creating' && !seed && !removed))
        throw Error('birth_creation_outcome_unknown');
      if (b.stage === 'created' && !seed && !removed) throw Error('birth_seed_missing');
      const own = tabs.find(t => t.id === b.connectorId);
      if (!b.origin || b.origin.connectorId !== b.connectorId) throw Error('birth_origin_missing');
      if (own) {
        let exact = false;
        try {
          const u = new URL(own.url);
          exact = u.protocol + '//' + u.host + u.pathname === b.connectorOrigin &&
            JSON.parse(u.searchParams.get('client')).name === b.client_name;
        } catch {}
        const allowed = [b.origin.windowId, b.windowId, seed?.windowId];
        if (!exact || !allowed.includes(own.windowId) ||
            ![b.origin.groupId, -1].includes(own.groupId))
          throw Error('birth_connector_changed');
      }
      const ids = [own?.id, seed?.id].filter(Number.isInteger);
      const status = await chrome.runtime.sendMessage({type:'getStatus'});
      if (!status || !Array.isArray(status.sessions) ||
          status.sessions.some(s => !Array.isArray(s.tabIds)))
        throw Error('birth_status_unavailable');
      const targets = await chrome.debugger.getTargets();
      if (status.sessions.some(s => s.tabIds.some(id => ids.includes(id))) ||
          targets.some(t => ids.includes(t.tabId) && t.attached))
        throw Error('birth_still_claimed');
      const windowId = b.windowId ?? seed?.windowId ?? b.cleanup?.windowId ?? b.origin.windowId;
      const proof = JSON.stringify([ids, windowId,
        tabs.filter(t => t.windowId === windowId).map(t => [t.id,t.groupId]).sort()]);
      return {ids, windowId, proof};
    };
    try {
      const r = await read();
      if (!b.remove) return r;
      if (r.proof !== b.expected || (await read()).proof !== b.expected)
        throw Error('birth_inventory_changed');
      if (r.ids.length) await chrome.tabs.remove(r.ids);
      const after = await chrome.tabs.query({});
      if (after.some(t => r.ids.includes(t.id) || t.url === b.marker || t.pendingUrl === b.marker))
        throw Error('birth_close_unverified');
      const remains = (await chrome.windows.getAll()).some(w => w.id === r.windowId);
      if (remains && !after.some(t => t.windowId === r.windowId))
        throw Error('birth_window_close_unverified');
      return {closed:true, tabIds:r.ids, windowId:r.windowId, windowClosed:!remains};
    } catch (error) {
      // Fixed labels only. No tab URLs, client names or extension tokens.
      const reason = /^birth_[a-z_]+$/.test(error.message) ? error.message : 'birth_census_failed';
      return {held:true,reason};
    }
  }, birth);
}
