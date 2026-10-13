// Proofs for the AI Workforce feed producer. Each describe block maps to one of
// the required guarantees in README.md ("What the tests prove").

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { readInputs, FeedSourceError } from '../lib/sources.mjs';
import { buildRecords, buildEnvelope, serialize, sameRecords } from '../lib/build-feed.mjs';
import { parseWorkforceEnvelope, contractIssues } from '../lib/hq-contract.mjs';
import { scanForLeaks } from '../lib/public-safety.mjs';
import { makeRepo, skillMd } from './fixture-repo.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const CLI = path.join(here, '..', 'generate-feed.mjs');
const LIVE_REPO = path.resolve(here, '..', '..', '..');
const NOW = '2026-10-03T12:00:00Z';

function generate(root, now = NOW) {
  return buildEnvelope(buildRecords(readInputs(root)), { generatedAt: now });
}
function byId(env) { return new Map(env.records.map(r => [r.id, r])); }
function cli(root, ...args) {
  return spawnSync(process.execPath, [CLI, '--repo', root, ...args], { encoding: 'utf8' });
}
const feedPath = root => path.join(root, 'tools/capability-feed/ai-workforce-feed.json');

describe('1. deterministic generation', () => {
  test('same inputs and clock produce byte-identical output', () => {
    const root = makeRepo();
    assert.equal(serialize(generate(root)), serialize(generate(root)));
  });

  test('records do not depend on the clock; only the timestamps move', () => {
    const root = makeRepo();
    const a = generate(root, '2026-10-03T12:00:00Z');
    const b = generate(root, '2027-01-01T00:00:00Z');
    assert.ok(sameRecords(a, b));
    assert.notEqual(a.generatedAt, b.generatedAt);
    assert.equal(a.verifiedAt, a.generatedAt);
  });

  test('--write leaves an unchanged feed untouched, timestamps included', () => {
    const root = makeRepo();
    assert.equal(cli(root, '--write', '--now', '2026-10-03T12:00:00Z').status, 0);
    const first = fs.readFileSync(feedPath(root), 'utf8');
    const r = cli(root, '--write', '--now', '2027-01-01T00:00:00Z');
    assert.equal(r.status, 0);
    assert.match(r.stdout, /unchanged/);
    assert.equal(fs.readFileSync(feedPath(root), 'utf8'), first);
  });
});

describe('2. invalid source data fails safely', () => {
  const cases = [
    ['graph with the wrong schema', s => s, /schema is "skill-map\/v0"/],
    ['unknown lifecycle status', s => { s.nodes[0].status = 'shipping'; return s; }, /unknown lifecycle status/],
    ['marketplace and plugin.json versions disagree', s => { s.manifests.alpha.version = '9.9.9'; return s; }, /version mismatch for "alpha"/],
    ['skill in a plugin folder the marketplace does not list', s => {
      s.skills['plugins/rogue/skills/rogue-one'] = skillMd({ name: 'rogue-one', description: 'Rogue.' });
      s.nodes.push({ id: 'rogue-one', source: 'eps:plugins/rogue/skills/rogue-one/SKILL.md', repo: 'eps' });
      return s;
    }, /not a marketplace plugin/],
    ['config names a package that does not exist', s => { s.config.packages.ghost = { presentAs: 'plugin', evidence: 'x' }; return s; }, /"ghost", which is not in marketplace\.json/],
    ['config rule without evidence', s => { delete s.config.packages['agent-kit'].evidence; return s; }, /must cite its canonical evidence/],
    ['collection shelf lists a non-member', s => { s.readmes['agent-kit'] = s.readmes['agent-kit'].replace('- kit-planner', '- kit-planner, alpha-one'); return s; }, /lists "alpha-one", which is not a skill in the package/],
    ['duplicate skill id', s => { s.nodes.push({ ...s.nodes[2] }); return s; }, /duplicate id "alpha-one"/],
    ['graph naming a SKILL.md that is not there', s => { delete s.skills['skills/solo']; return s; }, /does not exist in this checkout/],
  ];
  for (const [name, mutate, reason] of cases) {
    test(`refuses: ${name}`, () => {
      const root = makeRepo(mutate);
      if (name === 'graph with the wrong schema') {
        const g = JSON.parse(fs.readFileSync(path.join(root, 'tools/skill-map/skills-graph.json'), 'utf8'));
        g.schema = 'skill-map/v0';
        fs.writeFileSync(path.join(root, 'tools/skill-map/skills-graph.json'), JSON.stringify(g));
      }
      assert.throws(() => generate(root), e => e instanceof FeedSourceError && reason.test(e.message));
    });
  }

  test('a refused run exits 2 and leaves the last good feed in place', () => {
    const root = makeRepo();
    assert.equal(cli(root, '--write', '--now', NOW).status, 0);
    const good = fs.readFileSync(feedPath(root), 'utf8');
    fs.writeFileSync(path.join(root, '.claude-plugin/marketplace.json'), '{ not json');
    const r = cli(root, '--write', '--now', '2027-01-01T00:00:00Z');
    assert.equal(r.status, 2);
    assert.match(r.stderr, /refused/);
    assert.equal(fs.readFileSync(feedPath(root), 'utf8'), good);
  });
});

describe('3. secrets and private-only fields cannot leak', () => {
  test('private frontmatter keys and body text never reach the feed', () => {
    const root = makeRepo(s => {
      s.skills['plugins/alpha/skills/alpha-one'] = skillMd({
        name: 'alpha-one', description: 'Does the first alpha job.', zone: 'hands',
        extra: 'private-notes: "internal only, do not publish"\naccess-list: [allison, don]\ncredentials: "vault item 42"',
      });
      return s;
    });
    const text = serialize(generate(root));
    for (const forbidden of ['internal only', 'access-list', 'vault item 42', 'credentials', 'Body text that must never reach the feed']) {
      assert.ok(!text.includes(forbidden), `feed leaked: ${forbidden}`);
    }
  });

  const leaks = {
    '1Password reference': 'Reads op://Automation/Some Item/credential before running.',
    'email address': 'Sends a summary to someone@example.com every day.',
    'private repo URL': 'Source at https://github.com/ExpertPartners/aura/blob/main/x.md today.',
    // Assembled at runtime so the repo's own secret scanner does not flag the fixture.
    'credential assignment': `Calls the API with ${['api', 'key'].join('_')}=${'xyz'.repeat(4)} each time.`,
    'phone number': 'Texts 214-555-0199 when done.',
    'private host': 'Runs on embers-mac-mini.local over SSH.',
  };
  for (const [name, description] of Object.entries(leaks)) {
    test(`refuses a feed carrying a ${name}`, () => {
      const root = makeRepo(s => { s.skills['skills/solo'] = skillMd({ name: 'solo', description, tier: 'organization', zone: 'brain' }); return s; });
      assert.throws(() => generate(root), e => e instanceof FeedSourceError && /public-safety/.test(e.message));
    });
  }

  test('capability records: unknown fields are dropped, unsafe links refused', () => {
    const ok = makeRepo(s => {
      s.config.capabilityRecordSources = [{ path: 'capability-records' }];
      s.capabilityRecords['capability-records/a.json'] = {
        schema: 'expert-partners-capability-record/v1',
        records: [{ id: 'alpha-one', lastVerified: '2026-10-02 by the AI Capability Curator', privateNotes: 'Don said keep this quiet', accessList: ['allison@'] }],
      };
      return s;
    });
    const text = serialize(generate(ok));
    assert.ok(!text.includes('keep this quiet') && !text.includes('accessList') && !text.includes('privateNotes'));

    const bad = makeRepo(s => {
      s.config.capabilityRecordSources = [{ path: 'capability-records' }];
      s.capabilityRecords['capability-records/a.json'] = {
        schema: 'expert-partners-capability-record/v1',
        records: [{ id: 'alpha-one', sourceLinks: [{ label: 'repo', url: 'https://github.com/ExpertPartners/expert-partners-skills' }] }],
      };
      return s;
    });
    assert.throws(() => generate(bad), FeedSourceError);
  });

  test('a feed too large for one HQ read is refused', () => {
    const records = buildRecords(readInputs(makeRepo()));
    assert.throws(() => buildEnvelope(records, { generatedAt: NOW, maxBytes: 1000 }), e => e instanceof FeedSourceError && /size/.test(e.message));
  });

  test('the leak scanner masks what it reports', () => {
    const [finding] = scanForLeaks({ a: 'token ghp_abcdefghijklmnopqrstuvwxyz0123' });
    assert.equal(finding.rule, 'github-token');
    assert.ok(!finding.excerpt.includes('abcdefghijklmnop'));
  });
});

describe('4. skill and plugin relationships resolve', () => {
  test('plugin lists its skills, skills point back, calls resolve', () => {
    const recs = byId(generate(makeRepo()));
    const plugin = recs.get('alpha-plugin');
    assert.equal(plugin.kind, 'plugin');
    assert.deepEqual(plugin.containsSkillIds, ['alpha-one', 'alpha-two']);
    assert.equal(plugin.maintainer, 'Allison Gaddy');
    assert.deepEqual(recs.get('alpha-two').relatedIds, ['alpha-one', 'alpha-plugin']);
    assert.ok(recs.get('alpha-one').relatedIds.includes('alpha-plugin'));
  });

  test('an excluded package removes its skills and every reference to them', () => {
    const env = generate(makeRepo());
    const recs = byId(env);
    assert.ok(!recs.has('household-plugin') && !recs.has('house-one') && !recs.has('household'));
    assert.ok(!serialize(env).includes('house-one'));
  });

  test('every relationship in the feed names a record in the feed', () => {
    const env = generate(makeRepo());
    const ids = new Set(env.records.map(r => r.id));
    for (const r of env.records) {
      for (const id of [...r.relatedIds, ...r.containsSkillIds, ...r.collectionIds]) assert.ok(ids.has(id), `${r.id} -> ${id}`);
    }
  });
});

describe('5. collection membership resolves', () => {
  test('a collection lists members in canonical shelf order and members name it', () => {
    const recs = byId(generate(makeRepo()));
    const kit = recs.get('agent-kit');
    assert.equal(kit.kind, 'collection');
    assert.equal(kit.humanName, 'Agent Kit');
    assert.deepEqual(kit.containsSkillIds, ['kit-writer', 'kit-planner']);
    assert.deepEqual(kit.categories, ['Writing', 'Planning']);
    assert.equal(kit.portable, true);
    assert.equal(kit.status, 'Designed');
    const writer = recs.get('kit-writer');
    assert.deepEqual(writer.collectionIds, ['agent-kit']);
    assert.deepEqual(writer.categories, ['The marketing engines', 'Writing']);
    assert.equal(writer.humanName, 'Kit Writer');
    assert.ok(!recs.has('agent-kit-plugin'), 'a collection is not also listed as a plugin');
  });

  test('provenance flows only when the package README declares it', () => {
    const none = byId(generate(makeRepo()));
    assert.equal(none.get('kit-writer').source, undefined);
    assert.deepEqual(none.get('kit-writer').sourceLinks, []);

    const declared = byId(generate(makeRepo(s => {
      s.readmes['agent-kit'] += '\n## Source material\n\nAdapted from Jane Example\'s free skills bank.\n- [Jane Example\'s skills bank](https://example.org/bank)\n';
      return s;
    })));
    assert.equal(declared.get('agent-kit').source, "Adapted from Jane Example's free skills bank.");
    assert.deepEqual(declared.get('kit-writer').sourceLinks, [{ label: "Jane Example's skills bank", url: 'https://example.org/bank' }]);
  });
});

describe('6. unknown deployment state is never promoted to Active', () => {
  test('canonical lifecycle maps honestly; live is Unknown, not Active', () => {
    const recs = byId(generate(makeRepo()));
    assert.equal(recs.get('alpha-one').status, 'Unknown');
    assert.equal(recs.get('kit-writer').status, 'Designed');
    assert.equal(recs.get('aura-thing').status, 'Retired');
    assert.deepEqual(recs.get('alpha-one').verifiedSurfaces, []);
    assert.ok(![...recs.values()].some(r => r.status === 'Active'));
  });

  const withRecord = rec => makeRepo(s => {
    s.config.capabilityRecordSources = [{ path: 'capability-records' }];
    s.capabilityRecords['capability-records/curator.json'] = { schema: 'expert-partners-capability-record/v1', records: [rec] };
    return s;
  });

  test('a capability record claiming Active without verified surfaces is refused', () => {
    assert.throws(() => generate(withRecord({ id: 'alpha-one', status: 'Active' })), FeedSourceError);
    assert.throws(() => generate(withRecord({ id: 'alpha-one', status: 'Active', verifiedSurfaces: ['Claude Code'] })), FeedSourceError);
  });

  test('Active with verified surfaces and a verification date is accepted and rolls up honestly', () => {
    const recs = byId(generate(withRecord({ id: 'alpha-one', status: 'Active', verifiedSurfaces: ['Claude Code'], lastVerified: '2026-10-02, Curator check' })));
    assert.equal(recs.get('alpha-one').status, 'Active');
    assert.match(recs.get('alpha-one').accessNote, /Claude Code/);
    assert.equal(recs.get('alpha-plugin').status, 'Unknown', 'a plugin is Active only when everything current inside it is');
  });

  test('a new capability record can group existing skills', () => {
    const recs = byId(generate(withRecord({ id: 'bio-help', kind: 'capability', humanName: 'Bio Help', summary: 'Gets an agent a bio.', containsSkillIds: ['kit-writer'] })));
    assert.equal(recs.get('bio-help').kind, 'capability');
    assert.deepEqual(recs.get('bio-help').containsSkillIds, ['kit-writer']);
    assert.throws(() => generate(withRecord({ id: 'bio-help', kind: 'capability', humanName: 'B', summary: 'S', containsSkillIds: ['nope'] })), FeedSourceError);
  });
});

describe('7. generated output drift is detected', () => {
  test('--check passes on a fresh feed and fails on a hand edit', () => {
    const root = makeRepo();
    assert.equal(cli(root, '--write', '--now', NOW).status, 0);
    assert.equal(cli(root, '--check').status, 0);
    const feed = JSON.parse(fs.readFileSync(feedPath(root), 'utf8'));
    feed.records[0].status = 'Active';
    fs.writeFileSync(feedPath(root), serialize(feed));
    const r = cli(root, '--check');
    assert.equal(r.status, 1);
    assert.match(r.stderr, /DRIFT/);
  });

  test('--check fails when a canonical source moved but the feed did not', () => {
    const root = makeRepo();
    assert.equal(cli(root, '--write', '--now', NOW).status, 0);
    const mp = path.join(root, '.claude-plugin/marketplace.json');
    fs.writeFileSync(mp, fs.readFileSync(mp, 'utf8').replace('Alpha operations toolbox', 'Alpha operations toolbox, renamed'));
    assert.equal(cli(root, '--check').status, 1);
  });

  test('--check fails when the feed is missing or breaks HQ\'s contract', () => {
    const root = makeRepo();
    assert.equal(cli(root, '--check').status, 1);
    fs.writeFileSync(feedPath(root), JSON.stringify({ schema: 'expert-partners-ai-workforce/v1', source: 'canonical', records: [] }));
    assert.equal(cli(root, '--check').status, 1);
  });
});

describe('8. canonical source changes produce the expected feed change', () => {
  test('a marketplace description change rewrites exactly that summary', () => {
    const before = byId(generate(makeRepo()));
    const after = byId(generate(makeRepo(s => { s.marketplace.plugins[1].description = 'Alpha, now with more'; return s; })));
    assert.equal(after.get('alpha-plugin').summary, 'Alpha, now with more.');
    for (const [id, rec] of before) if (id !== 'alpha-plugin') assert.deepEqual(after.get(id), rec, id);
  });

  test('a new skill in the graph appears, inside its plugin', () => {
    const recs = byId(generate(makeRepo(s => {
      s.skills['plugins/alpha/skills/alpha-three'] = skillMd({ name: 'alpha-three', description: 'Third job.', zone: 'hands' });
      s.nodes.push({ id: 'alpha-three', source: 'eps:plugins/alpha/skills/alpha-three/SKILL.md', repo: 'eps', zone: 'hands' });
      return s;
    })));
    assert.ok(recs.has('alpha-three'));
    assert.deepEqual(recs.get('alpha-plugin').containsSkillIds, ['alpha-one', 'alpha-three', 'alpha-two']);
  });

  test('a lifecycle change in the graph changes the status', () => {
    const recs = byId(generate(makeRepo(s => { s.nodes[2].status = 'retired'; return s; })));
    assert.equal(recs.get('alpha-one').status, 'Retired');
  });
});

describe('HQ consumer contract, end to end', () => {
  test('the envelope satisfies HQ\'s schema exactly as HQ parses it', () => {
    const env = generate(makeRepo());
    assert.deepEqual(contractIssues(env), []);
    const parsed = parseWorkforceEnvelope(JSON.parse(serialize(env)));
    assert.ok(parsed);
    assert.equal(parsed.source, 'canonical');
  });
});

describe('live repository', () => {
  test('the real canonical sources generate a valid, public-safe feed', () => {
    const env = generate(LIVE_REPO);
    assert.deepEqual(contractIssues(env), []);
    assert.deepEqual(scanForLeaks(env), []);
    const recs = byId(env);
    const toolkit = recs.get('real-estate-agent-toolkit');
    assert.equal(toolkit.kind, 'collection');
    assert.equal(toolkit.containsSkillIds.length, 40, 'the Real Estate Agent Toolkit stays one collection of 40 skills');
    assert.equal(toolkit.portable, true);
    for (const id of toolkit.containsSkillIds) {
      assert.deepEqual(recs.get(id).collectionIds, ['real-estate-agent-toolkit'], id);
      assert.equal(recs.get(id).portable, true, id);
    }
    assert.ok(!env.records.some(r => r.status === 'Active'), 'nothing is Active until a verification record says so');
    assert.ok(!env.records.some(r => r.id.startsWith('acn-')), 'the household ACN line stays off the Expert Partners HQ');
  });

  test('the committed feed file, when present, satisfies HQ\'s contract', () => {
    const file = feedPath(LIVE_REPO);
    if (!fs.existsSync(file)) return;
    assert.deepEqual(contractIssues(JSON.parse(fs.readFileSync(file, 'utf8'))), []);
  });
});
