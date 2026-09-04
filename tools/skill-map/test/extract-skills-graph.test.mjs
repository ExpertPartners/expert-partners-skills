// Regression coverage for extract-skills-graph.mjs (aura issue #212, 2026-09-04).
// Builds throwaway eps and aura fixture trees and runs the real extractor as a child
// process, so every assertion is about the CLI's actual exit code, stderr, and JSON.
//
// What must stay true:
//   1. two canonical SKILL.md files with the same id still FAIL (real duplicate);
//   2. a pipeline-produced deployed copy of an existing canonical skill does NOT
//      fail as a duplicate, and is recorded under flags.deployedMounts;
//   3. a copy under a deployed-mount root without the DEPLOYED COPY header, or whose
//      header names a canonical home that does not exist or does not own the id,
//      FAILS with a message naming the corruption (never a bare "duplicate");
//   4. the pre-existing gates (declared duplicates, dangling references) still hold.
//
// Run: npm test  (from tools/skill-map, after npm ci)

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const EXTRACTOR = path.join(here, '..', 'extract-skills-graph.mjs');

const PIPELINE_HEADER = (canonical, stamp = 'v1.0', date = '2026-09-04') => [
  `# DEPLOYED COPY (${date}, skill-deploy pipeline): the canonical home is`,
  `# ${canonical}. Deployed at ${stamp}.`,
  '# Edit the canonical copy first, then redeploy via tools/skill-deploy.',
];

function writeSkill(root, relDir, { name, fields = {}, headerLines = [], body = 'Instructions.' }) {
  const dir = path.join(root, relDir);
  fs.mkdirSync(dir, { recursive: true });
  const fm = {
    description: `Test skill ${name}. Use when testing ${name}.`,
    tier: 'project',
    zone: 'routing',
    status: 'live',
    ...fields,
  };
  const lines = ['---', `name: ${name}`];
  for (const [k, v] of Object.entries(fm)) {
    if (v === undefined) continue;
    lines.push(Array.isArray(v) ? `${k}: [${v.join(', ')}]` : `${k}: ${v}`);
  }
  lines.push(...headerLines, '---', '', `# ${name}`, '', body, '');
  fs.writeFileSync(path.join(dir, 'SKILL.md'), lines.join('\n'));
  return dir;
}

// A minimal but complete estate: the inherit root, one eps canonical skill, one
// aura-native canonical skill (its only home is aura .claude/skills).
function makeRepos() {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'skills-graph-test-'));
  const eps = path.join(base, 'eps');
  const aura = path.join(base, 'aura');
  fs.mkdirSync(path.join(eps, 'tools', 'skill-map'), { recursive: true });
  fs.mkdirSync(aura, { recursive: true });
  writeSkill(eps, 'plugins/operating-doctrine/skills/operating-doctrine', {
    name: 'operating-doctrine',
    fields: { tier: 'plugin', zone: 'brain', inherits: [] },
  });
  writeSkill(eps, 'skills/alpha', { name: 'alpha', fields: { tier: 'organization', zone: 'hands' } });
  writeSkill(aura, '.claude/skills/beta', { name: 'beta' });
  return { base, eps, aura, out: path.join(base, 'graph.json') };
}

function run({ eps, aura, out }) {
  const r = spawnSync(process.execPath, [EXTRACTOR, '--eps', eps, '--aura', aura, '--out', out], { encoding: 'utf8' });
  const graph = r.status === 0 && fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')) : null;
  return { status: r.status, stdout: r.stdout, stderr: r.stderr, graph };
}

const ids = graph => graph.nodes.map(n => n.id).sort();

test('baseline: canonical skills in both repos map, nothing deployed', () => {
  const r = run(makeRepos());
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(ids(r.graph), ['alpha', 'beta', 'operating-doctrine']);
  assert.deepEqual(r.graph.flags.deployedMounts, []);
  assert.deepEqual(r.graph.flags.declaredDuplicates, []);
});

test('REAL duplicate: a second canonical SKILL.md with the same id still fails', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.claude/skills/alpha', { name: 'alpha' }); // no header: a second canonical identity
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /duplicate skill id "alpha"/);
});

test('REAL duplicate inside one repo still fails', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, 'doctrine/skills/beta', { name: 'beta' });
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /duplicate skill id "beta"/);
});

test('legitimate deployed mirrors under .agents/skills do NOT create duplicates', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.agents/skills/alpha', {
    name: 'alpha', fields: { tier: 'organization', zone: 'hands' },
    headerLines: PIPELINE_HEADER('expert-partners-skills skills/alpha/SKILL.md', 'v1.0'),
  });
  writeSkill(repos.aura, '.agents/skills/beta', {
    name: 'beta',
    headerLines: PIPELINE_HEADER('aura .claude/skills/beta/SKILL.md', 'tree sha256 0123456789ab'),
  });
  const r = run(repos);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(ids(r.graph), ['alpha', 'beta', 'operating-doctrine'], 'mirrors are never nodes');
  const mounts = r.graph.flags.deployedMounts;
  assert.equal(mounts.length, 2);
  assert.deepEqual(mounts.map(m => [m.id, m.canonical, m.mount]), [
    ['alpha', 'eps:skills/alpha/SKILL.md', 'aura:.agents/skills/'],
    ['beta', 'aura:.claude/skills/beta/SKILL.md', 'aura:.agents/skills/'],
  ]);
  assert.equal(mounts[1].stamp, 'tree sha256 0123456789ab');
  assert.equal(mounts[0].deployedAt, '2026-09-04');
  assert.doesNotMatch(r.stderr, /duplicate skill id/);
});

test('mirror classification is independent of walk order (.agents sorts before .claude)', () => {
  // The aura-native canonical (.claude) is walked AFTER its .agents mirror on a
  // sorted filesystem; the two-pass design must still resolve the mirror.
  const repos = makeRepos();
  writeSkill(repos.aura, '.agents/skills/beta', {
    name: 'beta', headerLines: PIPELINE_HEADER('aura .claude/skills/beta/SKILL.md', 'tree sha256 0123456789ab'),
  });
  const r = run(repos);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.graph.flags.deployedMounts.length, 1);
  assert.equal(r.graph.nodes.find(n => n.id === 'beta').source, 'aura:.claude/skills/beta/SKILL.md');
});

test('a copy under the mount root WITHOUT the pipeline header fails as corruption, not as a duplicate', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.agents/skills/beta', { name: 'beta' }); // hand-copied, no header
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /deployed copy without a DEPLOYED COPY header: aura:\.agents\/skills\/beta\/SKILL\.md/);
  assert.doesNotMatch(r.stderr, /duplicate skill id/);
});

test('a hand-written header that is not the pipeline format is not a header', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.agents/skills/beta', {
    name: 'beta',
    headerLines: ['# DEPLOYED COPY (2026-08-08, some build lane): the canonical home is', '# aura .claude/skills/beta/SKILL.md.'],
  });
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /without a DEPLOYED COPY header/);
});

test('a mirror whose header names a nonexistent canonical path fails', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.agents/skills/beta', {
    name: 'beta', headerLines: PIPELINE_HEADER('aura .Codex/skills/beta/SKILL.md', 'tree sha256 0123456789ab'),
  });
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /names a canonical home that does not exist: aura:\.agents\/skills\/beta\/SKILL\.md -> aura:\.Codex\/skills\/beta\/SKILL\.md/);
});

test('a mirror whose header names an unknown repo fails', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.agents/skills/beta', {
    name: 'beta', headerLines: PIPELINE_HEADER('partnersync .claude/skills/beta/SKILL.md', 'v2.0'),
  });
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /names an unknown canonical repo/);
});

test('an orphan mirror (id no canonical skill owns) fails', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.agents/skills/gamma', {
    name: 'gamma', headerLines: PIPELINE_HEADER('expert-partners-skills skills/alpha/SKILL.md', 'v1.0'),
  });
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /orphan deployed copy: aura:\.agents\/skills\/gamma\/SKILL\.md carries id "gamma"/);
});

test('a mirror pointing at the wrong canonical home for its id fails', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.agents/skills/beta', {
    name: 'beta', headerLines: PIPELINE_HEADER('expert-partners-skills skills/alpha/SKILL.md', 'v1.0'),
  });
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /points at the wrong canonical home: aura:\.agents\/skills\/beta\/SKILL\.md names eps:skills\/alpha\/SKILL\.md, but "beta" is canonical at aura:\.claude\/skills\/beta\/SKILL\.md/);
});

test('a mirror whose frontmatter name disagrees with its folder fails', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.agents/skills/beta', {
    name: 'alpha', headerLines: PIPELINE_HEADER('aura .claude/skills/beta/SKILL.md', 'tree sha256 0123456789ab'),
  });
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /name\/folder mismatch: aura:\.agents\/skills\/beta\/SKILL\.md declares name "alpha"/);
});

test('a pipeline header outside a mount root also marks a deployed copy (no hand list needed)', () => {
  // The three eps skills deployed to aura .claude/skills are registered by hand in
  // DECLARED_DUPLICATES today; a fourth deployed there tomorrow carries the header
  // and resolves without an extractor edit.
  const repos = makeRepos();
  writeSkill(repos.aura, '.claude/skills/alpha', {
    name: 'alpha', fields: { tier: 'organization', zone: 'hands' },
    headerLines: PIPELINE_HEADER('expert-partners-skills skills/alpha/SKILL.md', 'v1.0'),
  });
  const r = run(repos);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(ids(r.graph), ['alpha', 'beta', 'operating-doctrine']);
  assert.deepEqual(r.graph.flags.deployedMounts.map(m => [m.path, m.mount]), [['aura:.claude/skills/alpha/SKILL.md', null]]);
});

test('a header in the body (prose about the header) does not classify the file', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.claude/skills/delta', {
    name: 'delta',
    body: PIPELINE_HEADER('expert-partners-skills skills/alpha/SKILL.md').join('\n'),
  });
  const r = run(repos);
  assert.equal(r.status, 0, r.stderr);
  assert.ok(ids(r.graph).includes('delta'));
  assert.deepEqual(r.graph.flags.deployedMounts, []);
});

test('declared duplicate pointer is still recorded, not mapped', () => {
  const repos = makeRepos();
  fs.mkdirSync(path.join(repos.eps, 'operating-doctrine'), { recursive: true });
  fs.writeFileSync(path.join(repos.eps, 'operating-doctrine', 'SKILL.md'), 'Pointer: see plugins/operating-doctrine.\n');
  const r = run(repos);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(r.graph.flags.declaredDuplicates, ['eps:operating-doctrine/SKILL.md']);
  assert.equal(r.graph.nodes.filter(n => n.id === 'operating-doctrine').length, 1);
});

test('dangling references still fail', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.claude/skills/epsilon', { name: 'epsilon', fields: { calls: ['nowhere'] } });
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /dangling calls reference: epsilon -> "nowhere"/);
});

test('born-dressed strict mode still fails an unzoned canonical skill', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.claude/skills/zeta', { name: 'zeta', fields: { zone: undefined } });
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /born-dressed violation: aura:\.claude\/skills\/zeta\/SKILL\.md is missing required field\(s\) zone/);
});
