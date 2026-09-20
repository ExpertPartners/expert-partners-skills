// Geometry contract for the existing static SVG renderer. ELK remains build-time only.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import ELK from 'elkjs/lib/elk.bundled.js';
import { layoutGraph } from '../layout-skills-graph.mjs';

const node = (id, zone, brandScope = []) => ({ id, zone, brandScope, subtitle: null });
const edge = (from, to, type = 'calls') => ({ from, to, type });
const contains = (outer, inner) => inner.x >= outer.x - 0.1 && inner.y >= outer.y - 0.1
  && inner.x + inner.width <= outer.x + outer.width + 0.1
  && inner.y + inner.height <= outer.y + outer.height + 0.1;
const onBoundary = (point, box) => contains(box, { ...point, width: 0, height: 0 })
  && [point.x - box.x, point.x - box.x - box.width,
    point.y - box.y, point.y - box.y - box.height].some(d => Math.abs(d) <= 0.1);

function fixture() {
  return {
    brands: {
      'expert-partners': { parent: null }, 'don-hobbs': { parent: 'expert-partners' },
      'ag-personal-brand': { parent: null }, 'the-strong-ones': { parent: 'ag-personal-brand' },
      fam: { parent: null }, epic: { parent: null },
    },
    nodes: [
      node('operating-doctrine', 'brain'), node('new-project', 'routing'),
      node('session-home', 'routing'), node('repo-standards', 'hands'),
      node('audit-helper', 'hands'), node('brand-voice', 'brands'),
      node('ep-brand', 'brands', ['expert-partners']), node('don-brand', 'brands', ['don-hobbs']),
      node('ag-brand', 'brands', ['ag-personal-brand']), node('strong-brand', 'brands', ['the-strong-ones']),
      node('joint-brand', 'brands', ['fam', 'epic']),
    ],
    edges: [
      edge('new-project', 'repo-standards'), edge('session-home', 'new-project'),
      edge('repo-standards', 'audit-helper', 'defers-to'),
      edge('audit-helper', 'don-brand', 'defers-to'),
      edge('brand-voice', 'ep-brand', 'defers-to'), edge('ep-brand', 'don-brand', 'defers-to'),
      edge('brand-voice', 'strong-brand', 'defers-to'), edge('brand-voice', 'joint-brand', 'defers-to'),
      edge('new-project', 'operating-doctrine', 'inherits'),
    ],
  };
}

function assertRoutes(graph) {
  const byId = new Map(graph.nodes.map(n => [n.id, n.layout]));
  for (const e of graph.edges) {
    if (e.type === 'inherits') { assert.equal(e.points, null); continue; }
    assert.ok(e.points?.length >= 2, `${e.from} -> ${e.to} has visible geometry`);
    for (const p of e.points) {
      assert.ok(Number.isFinite(p.x) && Number.isFinite(p.y));
      assert.ok(p.x >= 0 && p.x <= graph.layout.width && p.y >= 0 && p.y <= graph.layout.height);
    }
    assert.ok(onBoundary(e.points[0], byId.get(e.from)), `${e.from} source boundary`);
    assert.ok(onBoundary(e.points.at(-1), byId.get(e.to)), `${e.to} target boundary`);
    assert.ok(e.points.some(p => p.x !== e.points[0].x || p.y !== e.points[0].y), 'nonzero route');
    for (let i = 1; i < e.points.length; i++) {
      const a = e.points[i - 1], b = e.points[i];
      assert.ok(a.x === b.x || a.y === b.y, 'orthogonal route');
      // The renderer draws nodes after arrows: crossing a node interior would
      // hide that route. Endpoints on box boundaries are deliberately allowed.
      for (const [id, box] of byId) {
        const through = a.x === b.x
          ? a.x > box.x + 0.1 && a.x < box.x + box.width - 0.1
            && Math.max(a.y, b.y) > box.y + 0.1 && Math.min(a.y, b.y) < box.y + box.height - 0.1
          : a.y > box.y + 0.1 && a.y < box.y + box.height - 0.1
            && Math.max(a.x, b.x) > box.x + 0.1 && Math.min(a.x, b.x) < box.x + box.width - 0.1;
        assert.ok(!through, `${e.from} -> ${e.to} must not be hidden behind ${id}`);
      }
    }
  }
}

test('routing -> hands calls and nested cross-zone defers-to retain real visible routes', async () => {
  const input = fixture();
  const semantics = input.edges.map(e => ({ ...e }));
  const graph = await layoutGraph(input);
  assert.deepEqual(graph.edges.map(({ points, ...e }) => e), semantics);
  assert.equal(graph.nodes.find(n => n.id === 'new-project').zone, 'routing');
  assert.equal(graph.nodes.find(n => n.id === 'repo-standards').zone, 'hands');
  assertRoutes(graph);
});

test('intra-zone calls and defers-to work without any cross-zone relationship', async () => {
  const input = fixture();
  const zone = id => input.nodes.find(n => n.id === id).zone;
  input.edges = input.edges.filter(e => e.type === 'inherits' || zone(e.from) === zone(e.to));
  assertRoutes(await layoutGraph(input));
});

test('zones keep their labels and every node; nested and joint brand rooms keep containment', async () => {
  const graph = await layoutGraph(fixture());
  assert.deepEqual(graph.layout.zones.map(z => [z.id, z.label]), [
    ['brain', 'The brain'], ['brands', 'The voices'], ['hands', 'The hands'], ['routing', 'Session machinery'],
  ]);
  for (const n of graph.nodes) {
    const zone = graph.layout.zones.find(z => z.id === n.zone);
    assert.ok(contains(zone, n.layout), `${n.id} stays in its zone`);
    if (n.brandScope.length) {
      assert.ok(contains(zone.rooms.find(r => r.key === n.brandScope.join('+')), n.layout));
    }
  }
  const rooms = graph.layout.zones.find(z => z.id === 'brands').rooms;
  for (const [child, parent] of [['don-hobbs', 'expert-partners'], ['the-strong-ones', 'ag-personal-brand']]) {
    const room = rooms.find(r => r.key === child);
    assert.equal(room.parent, parent);
    assert.ok(contains(rooms.find(r => r.key === parent), room));
  }
  const joint = rooms.find(r => r.key === 'fam+epic');
  assert.deepEqual(joint.brands, ['fam', 'epic']);
  assert.equal(joint.label, 'FAM and EPIC');
  assert.equal(joint.parent, null);
});

test('inherits stays collapsed and does not change ELK positioning', async () => {
  const withInheritance = await layoutGraph(fixture());
  const input = fixture();
  input.edges = input.edges.filter(e => e.type !== 'inherits');
  const without = await layoutGraph(input);
  assert.deepEqual(withInheritance.layout, without.layout);
  assert.deepEqual(withInheritance.nodes, without.nodes);
  assert.equal(withInheritance.edges.at(-1).points, null);
});

test('same graph produces exactly the same coordinates and routes', async () => {
  assert.deepEqual(await layoutGraph(fixture()), await layoutGraph(fixture()));
});

test('dangling calls, defers-to and collapsed inherits still fail before layout', async () => {
  for (const type of ['calls', 'defers-to', 'inherits']) {
    const input = fixture();
    input.edges.push(edge('new-project', 'missing', type));
    await assert.rejects(layoutGraph(input), new RegExp(`dangling ${type} edge`));
  }
});

test('missing routed geometry fails instead of silently hiding a relationship', async t => {
  const original = ELK.prototype.layout;
  t.mock.method(ELK.prototype, 'layout', async function (...args) {
    const laid = await original.apply(this, args);
    function strip(el) {
      for (const e of el.edges ?? []) e.sections = [];
      for (const child of el.children ?? []) strip(child);
    }
    strip(laid);
    return laid;
  });
  await assert.rejects(layoutGraph(fixture()), /layout missing routed points/);
});
