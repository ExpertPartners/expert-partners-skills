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
import { createHash } from 'node:crypto';
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

test('uncommitted stale bytes without historical proof remain fatal', () => {
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

// --- canonical-first delivery: proof is an exact historical pipeline render ---
const DEPLOY_SCRIPT = path.join(here, '..', '..', 'skill-deploy', 'deploy-skill.sh');
function gitRun(root, ...args) {
  const r = spawnSync('git', ['-C', root, ...args], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  return r.stdout.trim();
}
function commitFiles(root, message) {
  gitRun(root, 'add', '.');
  gitRun(root, 'commit', '-m', message);
  return gitRun(root, 'rev-parse', 'HEAD');
}
function rewriteManifest(dir) {
  const files = [];
  function visit(at, prefix = '') {
    for (const e of fs.readdirSync(at, { withFileTypes: true })) {
      const rel = prefix + e.name;
      if (e.isDirectory()) visit(path.join(at, e.name), `${rel}/`);
      else if (rel !== 'checksums.sha256') files.push(rel);
    }
  }
  visit(dir);
  const digest = bytes => createHash('sha256').update(bytes).digest('hex');
  const text = files.sort((a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b)))
    .map(rel => `${digest(fs.readFileSync(path.join(dir, rel)))}  ./${rel}\n`).join('');
  fs.writeFileSync(path.join(dir, 'checksums.sha256'), text);
}
function committedDeployment({ native = false, plugin = false } = {}) {
  const repos = makeRepos();
  const root = native ? repos.aura : repos.eps;
  const name = plugin ? 'gamma' : native ? 'beta' : 'alpha';
  let source = repos.files[name];
  if (plugin) {
    source = writeSkill(repos.eps, 'plugins/example/skills/gamma', { name: 'gamma' });
    fs.mkdirSync(path.join(repos.eps, 'plugins/example/.claude-plugin'), { recursive: true });
    fs.writeFileSync(path.join(repos.eps, 'plugins/example/.claude-plugin/plugin.json'), '{"version":"1.2.3"}\n');
  } else if (!native) {
    fs.appendFileSync(source, '\n# Alpha -- v1.0\n');
  }
  const reference = path.join(path.dirname(source), 'references', 'contract.txt');
  fs.mkdirSync(path.dirname(reference));
  fs.writeFileSync(reference, 'Historical reference bytes.\n');
  gitRun(root, 'init', '-b', 'main');
  gitRun(root, 'config', 'user.name', 'Fixture');
  gitRun(root, 'config', 'user.email', 'fixture@example.invalid');
  const prior = commitFiles(root, 'canonical version one');
  const canonicalPath = path.relative(root, source).split(path.sep).join('/');
  const blob = gitRun(root, 'rev-parse', `${prior}:${canonicalPath}`);
  const pipeline = path.join(repos.eps, 'tools/skill-deploy/deploy-skill.sh');
  fs.mkdirSync(path.dirname(pipeline), { recursive: true });
  fs.copyFileSync(DEPLOY_SCRIPT, pipeline);
  const mount = path.join(repos.aura, '.agents/skills');
  const args = [pipeline, name, ...(native ? ['--from', path.dirname(source)] : []), '--to', mount];
  const rendered = spawnSync('bash', args, {
    encoding: 'utf8', env: { ...process.env, SKILL_DEPLOY_TODAY: '2026-09-20' },
  });
  assert.equal(rendered.status, 0, rendered.stderr);
  fs.appendFileSync(source, '\nA newly committed canonical instruction.\n');
  commitFiles(root, 'canonical version two');
  const dir = path.join(mount, name);
  return { ...repos, root, source, prior, blob, canonicalPath, dir, file: path.join(dir, 'SKILL.md') };
}
function assertFatal(repos, pattern) {
  const r = run(repos);
  assert.equal(r.status, 1, r.stderr);
  assert.match(r.stderr, pattern);
  assert.equal(r.graph, null);
  assert.doesNotMatch(r.stderr, /WARNING: VERIFIED STALE/);
}

test('exact prior committed pipeline deployment is VERIFIED STALE with proof and redeploy debt', () => {
  const repos = committedDeployment();
  const r = run(repos);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stderr, /VERIFIED STALE \/ awaiting redeploy/);
  const mount = r.graph.flags.deployedMounts.find(m => m.id === 'alpha');
  assert.equal(mount.status, 'VERIFIED STALE');
  assert.equal(mount.awaitingRedeploy, true);
  assert.equal(mount.verifiedCanonicalCommit, repos.prior);
  assert.equal(mount.verifiedCanonicalBlob, repos.blob);
  assert.equal(r.graph.nodes.filter(n => n.id === 'alpha').length, 1);
  // The canonical graph allowance does NOT change the dedicated deployment gate.
  const verify = spawnSync('bash', [path.join(repos.eps, 'tools/skill-deploy/deploy-skill.sh'),
    'alpha', '--to', path.dirname(repos.dir), '--verify'], { encoding: 'utf8' });
  assert.notEqual(verify.status, 0);
  assert.match(verify.stdout + verify.stderr, /DRIFT/);
});

test('Aura-native tree-stamped prior committed deployment is also provable', () => {
  const repos = committedDeployment({ native: true });
  const r = run(repos);
  assert.equal(r.status, 0, r.stderr);
  const mount = r.graph.flags.deployedMounts.find(m => m.id === 'beta');
  assert.match(mount.stamp, /^tree sha256 [a-f0-9]{12}$/);
  assert.equal(mount.verifiedCanonicalCommit, repos.prior);
});

test('plugin deployment proves historical plugin release as well as skill bytes', () => {
  const repos = committedDeployment({ plugin: true });
  const r = run(repos);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.graph.flags.deployedMounts.find(m => m.id === 'gamma').stamp, '1.2.3');
});

test('a changed stale body is fatal even with a recomputed checksum manifest', () => {
  const repos = committedDeployment();
  fs.appendFileSync(repos.file, '\nHand-edited instructions.\n');
  rewriteManifest(repos.dir);
  assertFatal(repos, /no exact prior committed canonical render/);
});

test('a stale reference modification is fatal even with a recomputed manifest', () => {
  const repos = committedDeployment();
  fs.appendFileSync(path.join(repos.dir, 'references/contract.txt'), 'Hand edit.\n');
  rewriteManifest(repos.dir);
  assertFatal(repos, /no exact prior committed canonical render/);
});

test('an extra stale deployed file is fatal even with a recomputed manifest', () => {
  const repos = committedDeployment();
  fs.writeFileSync(path.join(repos.dir, 'extra.txt'), 'Uncommitted provenance.\n');
  rewriteManifest(repos.dir);
  assertFatal(repos, /no exact prior committed canonical render/);
});

test('an absent historical reference is fatal even with a recomputed manifest', () => {
  const repos = committedDeployment();
  fs.renameSync(path.join(repos.dir, 'references/contract.txt'), path.join(repos.base, 'saved-reference.txt'));
  rewriteManifest(repos.dir);
  assertFatal(repos, /no exact prior committed canonical render/);
});

test('stale copy without a checksum manifest is fatal', () => {
  const repos = committedDeployment();
  fs.renameSync(path.join(repos.dir, 'checksums.sha256'), path.join(repos.base, 'saved-checksums.sha256'));
  assertFatal(repos, /missing or invalid deployment checksum manifest/);
});

test('a stale checksum mismatch is fatal', () => {
  const repos = committedDeployment();
  fs.appendFileSync(path.join(repos.dir, 'checksums.sha256'), '\n');
  assertFatal(repos, /missing or invalid deployment checksum manifest/);
});

test('a false historical version stamp is fatal despite an exact old body', () => {
  const repos = committedDeployment();
  fs.writeFileSync(repos.file, fs.readFileSync(repos.file, 'utf8').replace('Deployed at v1.0.', 'Deployed at v9.9.'));
  rewriteManifest(repos.dir);
  assertFatal(repos, /no exact prior committed canonical render/);
});

test('a moved pipeline header is fatal despite an exact stripped historical body', () => {
  const repos = committedDeployment();
  let text = fs.readFileSync(repos.file, 'utf8');
  const block = text.match(/^# DEPLOYED COPY \([\s\S]*?# Edit the canonical copy first, then redeploy via tools\/skill-deploy\.\n/m)[0];
  text = text.replace(block, '').replace('name: alpha\n', `name: alpha\n${block}`);
  fs.writeFileSync(repos.file, text);
  rewriteManifest(repos.dir);
  assertFatal(repos, /no exact prior committed canonical render/);
});

test('invalid or missing historical header remains fatal', () => {
  for (const mode of ['invalid', 'missing']) {
    const repos = committedDeployment();
    let text = fs.readFileSync(repos.file, 'utf8');
    text = mode === 'invalid' ? text.replace('skill-deploy pipeline', 'someone else')
      : text.replace(/^# DEPLOYED COPY \([\s\S]*?# Edit the canonical copy first, then redeploy via tools\/skill-deploy\.\n/m, '');
    fs.writeFileSync(repos.file, text);
    rewriteManifest(repos.dir);
    assertFatal(repos, /without a DEPLOYED COPY header/);
  }
});

test('historical match cannot override wrong ownership or an orphaned canonical', () => {
  const wrong = committedDeployment();
  fs.writeFileSync(wrong.file, fs.readFileSync(wrong.file, 'utf8')
    .replace('expert-partners-skills skills/alpha/SKILL.md', 'aura .claude/skills/beta/SKILL.md'));
  rewriteManifest(wrong.dir);
  assertFatal(wrong, /points at the wrong canonical home/);
  const orphan = committedDeployment();
  fs.renameSync(orphan.source, path.join(orphan.base, 'saved-SKILL.md'));
  assertFatal(orphan, /canonical home that does not exist/);
});

test('an unreachable side-branch version is not prior canonical history', () => {
  const repos = committedDeployment();
  gitRun(repos.root, 'switch', '-c', 'unmerged');
  fs.appendFileSync(repos.source, '\nOnly on an unrelated branch.\n');
  commitFiles(repos.root, 'unmerged source');
  const out = path.join(repos.base, 'branch-deployment');
  const render = spawnSync('bash', [path.join(repos.eps, 'tools/skill-deploy/deploy-skill.sh'), 'alpha', '--to', out], { encoding: 'utf8' });
  assert.equal(render.status, 0, render.stderr);
  for (const rel of ['SKILL.md', 'checksums.sha256', 'references/contract.txt']) {
    fs.copyFileSync(path.join(out, 'alpha', rel), path.join(repos.dir, rel));
  }
  gitRun(repos.root, 'switch', 'main');
  assertFatal(repos, /no exact prior committed canonical render/);
});

test('shallow history without the matching canonical commit fails closed', () => {
  const repos = committedDeployment();
  const shallow = path.join(repos.base, 'shallow');
  const clone = spawnSync('git', ['clone', '--depth=1', `file://${repos.root}`, shallow], { encoding: 'utf8' });
  assert.equal(clone.status, 0, clone.stderr);
  assertFatal({ ...repos, eps: shallow }, /fetch full history if shallow/);
});

test('historical proof rejects symlinked deployed reference files', () => {
  const repos = committedDeployment();
  const ref = path.join(repos.dir, 'references/contract.txt');
  const saved = path.join(repos.base, 'original-reference.txt');
  fs.renameSync(ref, saved);
  fs.symlinkSync(saved, ref);
  assertFatal(repos, /non-regular deployed file/);
});
