// Regression coverage for extract-skills-graph.mjs (aura issue #212, 2026-09-04).
// Builds throwaway eps and aura fixture trees and runs the real extractor as a child
// process, so every assertion is about the CLI's actual exit code, stderr, and JSON.
//
// What must stay true:
//   1. two canonical SKILL.md files with the same id still FAIL (real duplicate);
//   2. a pipeline-produced deployed copy of an existing canonical skill does NOT
//      fail as a duplicate, and is recorded under flags.deployedMounts;
//   3. a copy under a deployed-mount root without the DEPLOYED COPY header, whose
//      header names a canonical home that does not exist or does not own the id,
//      or whose bytes differ from that canonical, FAILS with a message naming the
//      corruption (never a bare "duplicate");
//   4. the pre-existing gates (declared duplicates, dangling references, strict
//      born-dressed mode) still hold.
//
// Mirrors here are built the way the pipeline builds them: canonical bytes with the
// three header lines injected into the frontmatter. That is what the byte-fidelity
// check in pass 3 compares against, so a fixture that fakes a mirror by re-rendering
// the frontmatter would (correctly) fail.
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

const headerLines = (canonical, stamp = 'v1.0', date = '2026-09-04') => [
  `# DEPLOYED COPY (${date}, skill-deploy pipeline): the canonical home is`,
  `# ${canonical}. Deployed at ${stamp}.`,
  '# Edit the canonical copy first, then redeploy via tools/skill-deploy.',
];

function writeSkill(root, relDir, { name, fields = {}, extraHeader = [], body = 'Instructions.' }) {
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
  lines.push(...extraHeader, '---', '', `# ${name}`, '', body, '');
  const file = path.join(dir, 'SKILL.md');
  fs.writeFileSync(file, lines.join('\n'));
  return file;
}

// Deploy a mirror exactly as tools/skill-deploy/deploy-skill.sh render() does:
// take the canonical bytes and insert the three header lines before the closing
// '---' of the frontmatter. Nothing else changes, which is what pass 3 verifies.
function deployMirror(canonicalFile, destDir, canonicalLabel, stamp = 'v1.0', date = '2026-09-04') {
  const text = fs.readFileSync(canonicalFile, 'utf8');
  const lines = text.split('\n');
  const end = lines.slice(1).findIndex(l => l.trim() === '---') + 1;
  lines.splice(end, 0, ...headerLines(canonicalLabel, stamp, date));
  fs.mkdirSync(destDir, { recursive: true });
  const out = path.join(destDir, 'SKILL.md');
  fs.writeFileSync(out, lines.join('\n'));
  return out;
}

// A minimal but complete estate: the inherit root, one eps canonical skill, one
// aura-native canonical skill (its only home is aura .claude/skills).
function makeRepos() {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'skills-graph-test-'));
  const eps = path.join(base, 'eps');
  const aura = path.join(base, 'aura');
  fs.mkdirSync(path.join(eps, 'tools', 'skill-map'), { recursive: true });
  fs.mkdirSync(aura, { recursive: true });
  const files = {};
  files.doctrine = writeSkill(eps, 'plugins/operating-doctrine/skills/operating-doctrine', {
    name: 'operating-doctrine',
    fields: { tier: 'plugin', zone: 'brain', inherits: [] },
  });
  files.alpha = writeSkill(eps, 'skills/alpha', { name: 'alpha', fields: { tier: 'organization', zone: 'hands' } });
  files.beta = writeSkill(aura, '.claude/skills/beta', { name: 'beta' });
  return { base, eps, aura, files, out: path.join(base, 'graph.json') };
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
  deployMirror(repos.files.alpha, path.join(repos.aura, '.agents/skills/alpha'),
    'expert-partners-skills skills/alpha/SKILL.md', 'v1.0');
  deployMirror(repos.files.beta, path.join(repos.aura, '.agents/skills/beta'),
    'aura .claude/skills/beta/SKILL.md', 'tree sha256 0123456789ab');
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
  deployMirror(repos.files.beta, path.join(repos.aura, '.agents/skills/beta'),
    'aura .claude/skills/beta/SKILL.md', 'tree sha256 0123456789ab');
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
    extraHeader: ['# DEPLOYED COPY (2026-08-08, some build lane): the canonical home is', '# aura .claude/skills/beta/SKILL.md.'],
  });
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /without a DEPLOYED COPY header/);
});

test('a mirror whose header names a nonexistent canonical path fails', () => {
  const repos = makeRepos();
  deployMirror(repos.files.beta, path.join(repos.aura, '.agents/skills/beta'),
    'aura .Codex/skills/beta/SKILL.md', 'tree sha256 0123456789ab');
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /names a canonical home that does not exist: aura:\.agents\/skills\/beta\/SKILL\.md -> aura:\.Codex\/skills\/beta\/SKILL\.md/);
});

test('a mirror whose header names an unknown repo fails', () => {
  const repos = makeRepos();
  deployMirror(repos.files.beta, path.join(repos.aura, '.agents/skills/beta'),
    'partnersync .claude/skills/beta/SKILL.md', 'v2.0');
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /names an unknown canonical repo/);
});

test('an orphan mirror (id no canonical skill owns) fails', () => {
  const repos = makeRepos();
  const gammaDir = path.join(repos.aura, '.agents/skills/gamma');
  deployMirror(repos.files.alpha, gammaDir, 'expert-partners-skills skills/alpha/SKILL.md', 'v1.0');
  fs.writeFileSync(path.join(gammaDir, 'SKILL.md'),
    fs.readFileSync(path.join(gammaDir, 'SKILL.md'), 'utf8').replace('name: alpha', 'name: gamma'));
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /orphan deployed copy: aura:\.agents\/skills\/gamma\/SKILL\.md carries id "gamma"/);
});

test('a mirror pointing at the wrong canonical home for its id fails', () => {
  const repos = makeRepos();
  deployMirror(repos.files.beta, path.join(repos.aura, '.agents/skills/beta'),
    'expert-partners-skills skills/alpha/SKILL.md', 'v1.0');
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /points at the wrong canonical home: aura:\.agents\/skills\/beta\/SKILL\.md names eps:skills\/alpha\/SKILL\.md, but "beta" is canonical at aura:\.claude\/skills\/beta\/SKILL\.md/);
});

test('a mirror whose frontmatter name disagrees with its folder fails', () => {
  const repos = makeRepos();
  const dir = path.join(repos.aura, '.agents/skills/beta');
  deployMirror(repos.files.alpha, dir, 'expert-partners-skills skills/alpha/SKILL.md', 'v1.0');
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /name\/folder mismatch: aura:\.agents\/skills\/beta\/SKILL\.md declares name "alpha"/);
});

// --- byte fidelity: a header is a claim; these prove the extractor demands proof ---

test('a DIVERGENT skill wearing a valid pipeline header is caught, not accepted as a mirror', () => {
  // The failure mode the header alone cannot catch: a real second skill with a
  // canonical's name and body of its own, plus three pasted header lines.
  const repos = makeRepos();
  const dir = path.join(repos.aura, '.agents/skills/alpha');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'SKILL.md'), [
    '---',
    'name: alpha',
    'description: A COMPLETELY DIFFERENT SKILL wearing the alpha name.',
    'tier: organization',
    'zone: hands',
    'status: live',
    ...headerLines('expert-partners-skills skills/alpha/SKILL.md', 'v9.9'),
    '---',
    '',
    '# alpha',
    '',
    'Totally different instructions.',
    '',
  ].join('\n'));
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /is not a faithful render of its canonical: aura:\.agents\/skills\/alpha\/SKILL\.md differs from eps:skills\/alpha\/SKILL\.md beyond the DEPLOYED COPY header/);
  assert.doesNotMatch(r.stderr, /duplicate skill id/);
});

test('a mirror that drifted by one line in the body is caught', () => {
  const repos = makeRepos();
  const file = deployMirror(repos.files.beta, path.join(repos.aura, '.agents/skills/beta'),
    'aura .claude/skills/beta/SKILL.md', 'tree sha256 0123456789ab');
  fs.appendFileSync(file, '\nHand-edited afterwards.\n');
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /is not a faithful render of its canonical/);
});

test('a stale mirror (canonical moved, no redeploy) is caught', () => {
  const repos = makeRepos();
  deployMirror(repos.files.beta, path.join(repos.aura, '.agents/skills/beta'),
    'aura .claude/skills/beta/SKILL.md', 'tree sha256 0123456789ab');
  fs.appendFileSync(repos.files.beta, '\nA new canonical paragraph.\n');
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /is not a faithful render of its canonical/);
});

test('a canonical overwritten by its own deployed copy is diagnosed as that, not as an orphan', () => {
  const repos = makeRepos();
  deployMirror(repos.files.alpha, path.join(repos.eps, 'skills/alpha'),
    'expert-partners-skills skills/alpha/SKILL.md', 'v1.0');
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /canonical overwritten by a deployed copy: eps:skills\/alpha\/SKILL\.md carries a DEPLOYED COPY header naming itself -- restore the canonical from git history/);
  assert.doesNotMatch(r.stderr, /orphan deployed copy/);
});

test('a pipeline header outside a mount root also marks a deployed copy (no hand list needed)', () => {
  // The three eps skills deployed into aura .claude/skills are NOT registered by
  // hand any more; they resolve by header, and a fourth deployed there tomorrow
  // needs no extractor edit.
  const repos = makeRepos();
  deployMirror(repos.files.alpha, path.join(repos.aura, '.claude/skills/alpha'),
    'expert-partners-skills skills/alpha/SKILL.md', 'v1.0');
  const r = run(repos);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(ids(r.graph), ['alpha', 'beta', 'operating-doctrine']);
  assert.deepEqual(r.graph.flags.deployedMounts.map(m => [m.path, m.mount]),
    [['aura:.claude/skills/alpha/SKILL.md', null]]);
});

test('a header in the body (prose about the header) does not classify the file', () => {
  const repos = makeRepos();
  writeSkill(repos.aura, '.claude/skills/delta', {
    name: 'delta',
    body: headerLines('expert-partners-skills skills/alpha/SKILL.md').join('\n'),
  });
  const r = run(repos);
  assert.equal(r.status, 0, r.stderr);
  assert.ok(ids(r.graph).includes('delta'));
  assert.deepEqual(r.graph.flags.deployedMounts, []);
});

// --- the pointer-file exemption, and its own guard ---

test('declared duplicate pointer is still recorded, not mapped', () => {
  const repos = makeRepos();
  fs.mkdirSync(path.join(repos.eps, 'operating-doctrine'), { recursive: true });
  fs.writeFileSync(path.join(repos.eps, 'operating-doctrine', 'SKILL.md'), 'Pointer: see plugins/operating-doctrine.\n');
  const r = run(repos);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(r.graph.flags.declaredDuplicates, ['eps:operating-doctrine/SKILL.md']);
  assert.equal(r.graph.nodes.filter(n => n.id === 'operating-doctrine').length, 1);
});

test('a declared duplicate whose keep path is no longer the mapped canonical fails', () => {
  // The hand-maintained list must not outlive the layout it describes.
  const repos = makeRepos();
  fs.mkdirSync(path.join(repos.eps, 'operating-doctrine'), { recursive: true });
  fs.writeFileSync(path.join(repos.eps, 'operating-doctrine', 'SKILL.md'), 'Pointer file.\n');
  // Move the real canonical somewhere the list does not name.
  fs.rmSync(path.join(repos.eps, 'plugins/operating-doctrine/skills/operating-doctrine/SKILL.md'));
  writeSkill(repos.eps, 'skills/operating-doctrine', {
    name: 'operating-doctrine', fields: { tier: 'plugin', zone: 'brain', inherits: [] },
  });
  const r = run(repos);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /declared duplicate "operating-doctrine": the list keeps eps:plugins\/operating-doctrine\/skills\/operating-doctrine\/SKILL\.md, but the mapped canonical is eps:skills\/operating-doctrine\/SKILL\.md/);
});

// --- pre-existing gates, unchanged ---

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
