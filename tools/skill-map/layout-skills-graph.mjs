// Skill Map Stage 2 layout step (aura intake/2026-08-04-skill-map-architecture-report.md).
// Runs ELK.js (layered algorithm, INCLUDE_CHILDREN over the compound zone
// containers) at BUILD TIME ONLY, inside the same regeneration step as
// extraction, and bakes absolute x/y/width/height into skills-graph.json.
// ELK never ships to any browser; the renderer on hq.allisongaddy.com reads
// the committed coordinates and draws static SVG.
//
// Modeling, per the approved architecture and the 2026-08-05 rulings:
// - Zones stay compound containers in one INCLUDE_CHILDREN layered run, so
//   calls and defers-to can cross zone boundaries without losing containment.
//   ELK routes all drawn edges in the hierarchy; coordinates are translated
//   from each returned edge container into the renderer's absolute space.
// - The brands zone renders each brand as its own tinted sub-room, and that
//   run uses elk.hierarchyHandling INCLUDE_CHILDREN for the nesting. Ruled
//   parent links nest two rooms: don-hobbs inside expert-partners and
//   the-strong-ones inside ag-personal-brand. A skill scoped to several
//   brands (fam-epic-brand -> fam + epic) gets one joint room, since a node
//   cannot sit in two containers.
// - operating-doctrine renders per its render-note (single faint anchor,
//   inheritance edges collapsed): inherits edges are NOT given to ELK and
//   carry no routed points; only calls and defers-to edges are routed.

import ELK from 'elkjs/lib/elk.bundled.js';

// ---------- sizing (single source of truth for the renderer: wrapped
// subtitle lines and all box dimensions are baked into the JSON) ----------

const TITLE_CHAR_W = 7.4;   // ~13px system sans, weight 500
const SUB_CHAR_W = 6.0;     // ~11.5px system sans, weight 400
const NODE_W_MIN = 132;
const NODE_W_MAX = 300;
const NODE_PAD_X = 22;
const ANNOT_H = 15;         // status annotation strip above the node rect
const SUB_WRAP_AT = 32;     // wrap subtitle lines longer than this many chars
const CANVAS_PAD = 8;

function wrapSubtitle(subtitle) {
  if (!subtitle) return [];
  if (subtitle.length <= SUB_WRAP_AT) return [subtitle];
  const words = subtitle.split(/\s+/);
  const lines = [];
  let line = '';
  for (const w of words) {
    if (line && (line + ' ' + w).length > SUB_WRAP_AT) { lines.push(line); line = w; }
    else line = line ? line + ' ' + w : w;
  }
  if (line) lines.push(line);
  return lines;
}

function nodeBox(node) {
  const subtitleLines = wrapSubtitle(node.subtitle);
  const longestSub = subtitleLines.reduce((m, l) => Math.max(m, l.length), 0);
  const width = Math.min(
    NODE_W_MAX,
    Math.max(NODE_W_MIN, Math.ceil(Math.max(node.id.length * TITLE_CHAR_W, longestSub * SUB_CHAR_W)) + NODE_PAD_X * 2),
  );
  const rectH = subtitleLines.length === 0 ? 34 : 34 + subtitleLines.length * 14;
  return { width, height: rectH + ANNOT_H, rectH, subtitleLines };
}

// ---------- zone and room vocabulary (labels are content; colors live in the renderer) ----------

const ZONE_LABELS = {
  brain: { label: 'The brain', caption: 'the law and the map of the house' },
  brands: { label: 'The voices', caption: 'one room per brand, registry per ADR 0045' },
  content: { label: 'The marketing engines', caption: 'strategy, offers, content, conversations' },
  hands: { label: 'The hands', caption: 'funnel work and account operations' },
  routing: { label: 'Session machinery', caption: 'routing, ledgers, session lifecycle' },
  surfaces: { label: 'The surfaces', caption: 'where Allison meets the system' },
  finance: { label: 'The money', caption: 'cash, close, runway' },
  cataloging: { label: 'The librarians', caption: 'catalogs and registries' },
};
// Stable input and output order; ELK positions only populated zone containers.
const ZONE_ORDER = ['brain', 'brands', 'content', 'hands', 'routing', 'surfaces', 'finance', 'cataloging'];

const BRAND_LABELS = {
  'expert-partners': 'Expert Partners',
  epic: 'EPIC',
  fam: 'FAM',
  'ag-personal-brand': 'AG Personal Brand',
  'ag-luxury': 'AG Luxury',
  'don-hobbs': 'Don Hobbs',
  'the-strong-ones': 'The Strong Ones',
  moxie: 'Moxie',
};

const ZONE_PAD = '[top=48,left=22,bottom=22,right=22]';
const ROOM_PAD = '[top=34,left=16,bottom=16,right=16]';

// ---------- layout ----------

export async function layoutGraph(graph) {
  const nodesById = new Map(graph.nodes.map(n => [n.id, n]));
  const boxes = new Map(graph.nodes.map(n => [n.id, nodeBox(n)]));

  const byZone = new Map();
  for (const n of graph.nodes) {
    if (!byZone.has(n.zone)) byZone.set(n.zone, []);
    byZone.get(n.zone).push(n);
  }
  const zoneIds = ZONE_ORDER.filter(z => byZone.has(z));

  // Validate every relationship even though inherits is deliberately collapsed.
  for (const e of graph.edges) {
    if (!nodesById.has(e.from) || !nodesById.has(e.to)) {
      throw new Error(`dangling ${e.type} edge ${e.from} -> ${e.to}`);
    }
  }
  const routedEdges = graph.edges.map((e, i) => ({ ...e, _idx: i })).filter(e => e.type !== 'inherits');

  function elkNode(n) {
    const b = boxes.get(n.id);
    return { id: n.id, width: b.width, height: b.height };
  }

  // Brand rooms: key by the brandScope signature (joint room for multi-scope).
  const roomMeta = new Map(); // elk id -> {key, brands, label}
  function buildBrandChildren(zoneNodes) {
    const roomMembers = new Map();
    const loose = [];
    for (const n of zoneNodes) {
      if (n.brandScope.length === 0) { loose.push(n); continue; }
      const key = n.brandScope.join('+');
      if (!roomMembers.has(key)) roomMembers.set(key, []);
      roomMembers.get(key).push(n);
    }
    const roomParent = new Map();
    for (const key of roomMembers.keys()) {
      const scope = key.split('+');
      if (scope.length === 1) {
        const parent = graph.brands[scope[0]]?.parent;
        if (parent && roomMembers.has(parent)) roomParent.set(key, parent);
      }
    }
    function roomElk(key) {
      const scope = key.split('+');
      const label = scope.map(b => BRAND_LABELS[b] ?? b).join(' and ');
      roomMeta.set(`room:${key}`, { key, brands: scope, label });
      const childRooms = [...roomParent.entries()].filter(([, p]) => p === key).map(([k]) => k);
      return {
        id: `room:${key}`,
        layoutOptions: { 'elk.padding': ROOM_PAD, 'elk.spacing.nodeNode': '20' },
        children: [
          ...roomMembers.get(key).map(n => elkNode(n)),
          ...childRooms.map(k => roomElk(k)),
        ],
      };
    }
    const topRooms = [...roomMembers.keys()].filter(k => !roomParent.has(k)).sort();
    return [...loose.map(n => elkNode(n)), ...topRooms.map(k => roomElk(k))];
  }

  const root = {
    id: 'skill-map',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.hierarchyHandling': 'INCLUDE_CHILDREN',
      'elk.direction': 'RIGHT',
      'elk.edgeRouting': 'ORTHOGONAL',
      'elk.padding': `[top=${CANVAS_PAD},left=${CANVAS_PAD},bottom=${CANVAS_PAD},right=${CANVAS_PAD}]`,
      'elk.spacing.nodeNode': '30',
      'elk.layered.spacing.nodeNodeBetweenLayers': '46',
      'elk.randomSeed': '1',
    },
    children: zoneIds.map(zid => ({
      id: `zone:${zid}`,
      layoutOptions: { 'elk.padding': ZONE_PAD, 'elk.spacing.nodeNode': '24' },
      children: zid === 'brands' ? buildBrandChildren(byZone.get(zid)) : byZone.get(zid).map(elkNode),
    })),
    edges: routedEdges.map(e => ({ id: `edge:${e._idx}`, sources: [e.from], targets: [e.to] })),
  };
  const laid = await new ELK().layout(root);
  const absNodes = new Map();
  const zonesById = new Map();
  const edgeRoutes = new Map();
  const containerOrigin = new Map();

  // ELK node positions and edge sections are relative to their containing
  // compound. Keep a single absolute origin table for zones, rooms and edges.
  (function walk(el, ox, oy, zone) {
    const x = ox + (el.x ?? 0);
    const y = oy + (el.y ?? 0);
    containerOrigin.set(el.id, { x, y });
    if (el.id.startsWith('zone:')) {
      const zid = el.id.slice(5);
      const zl = ZONE_LABELS[zid] ?? { label: zid, caption: '' };
      zone = { id: zid, ...zl, x, y, width: el.width, height: el.height, rooms: [] };
      zonesById.set(zid, zone);
    } else if (roomMeta.has(el.id)) {
      const m = roomMeta.get(el.id);
      zone.rooms.push({ key: m.key, brands: m.brands, label: m.label, parent: null, x, y, width: el.width, height: el.height });
    } else if (nodesById.has(el.id)) {
      absNodes.set(el.id, { x, y, width: el.width, height: el.height });
    }
    for (const c of el.children ?? []) walk(c, x, y, zone);
  })(laid, 0, 0, null);
  const zonesOut = zoneIds.map(zid => zonesById.get(zid));

  (function collect(el) {
    for (const e of el.edges ?? []) {
      const idx = Number(e.id.slice(5));
      const origin = containerOrigin.get(e.container ?? el.id);
      if (!origin) throw new Error(`layout missing container for edge ${e.id}`);
      const pts = [];
      for (const s of e.sections ?? []) pts.push(s.startPoint, ...(s.bendPoints ?? []), s.endPoint);
      edgeRoutes.set(idx, pts.map(p => ({ x: Math.round((p.x + origin.x) * 10) / 10, y: Math.round((p.y + origin.y) * 10) / 10 })));
    }
    for (const c of el.children ?? []) collect(c);
  })(laid);

  // Room parent links, recorded flat with a parent key for the renderer.
  for (const zone of zonesOut) {
    for (const room of zone.rooms) {
      const scope = room.key.split('+');
      if (scope.length === 1) {
        const parent = graph.brands[scope[0]]?.parent;
        if (parent && zone.rooms.some(r => r.key === parent)) room.parent = parent;
      }
    }
  }

  // ---------- bake ----------

  const round = v => Math.round(v * 10) / 10;
  for (const n of graph.nodes) {
    const abs = absNodes.get(n.id);
    const b = boxes.get(n.id);
    if (!abs) throw new Error(`layout missing for node ${n.id}`);
    n.layout = {
      x: round(abs.x), y: round(abs.y), width: abs.width, height: abs.height,
      rectHeight: b.rectH, annotationHeight: ANNOT_H, subtitleLines: b.subtitleLines,
    };
  }
  graph.edges.forEach((e, i) => {
    if (e.type === 'inherits') { e.points = null; return; } // collapsed per render-note
    const points = edgeRoutes.get(i);
    if (!points || points.length < 2 || points.some(p => !Number.isFinite(p.x) || !Number.isFinite(p.y))) {
      throw new Error(`layout missing routed points for ${e.type} edge ${e.from} -> ${e.to}`);
    }
    e.points = points;
  });
  graph.layout = {
    engine: 'elkjs layered, single INCLUDE_CHILDREN hierarchy over zones and brand rooms, build-time only',
    width: Math.ceil(laid.width),
    height: Math.ceil(laid.height),
    zones: zonesOut.map(z => ({
      ...z, x: round(z.x), y: round(z.y), width: round(z.width), height: round(z.height),
      rooms: z.rooms.map(r => ({ ...r, x: round(r.x), y: round(r.y), width: round(r.width), height: round(r.height) })),
    })),
  };
  return graph;
}
