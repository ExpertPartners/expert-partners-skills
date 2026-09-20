// Read-only proof for a stale deployment during canonical-first skill delivery.
// Only an exact pipeline render of a committed ancestor at the SAME canonical
// path is admissible. No tag/other-branch search, version-only trust, or mutation.
// The dedicated deploy-skill --verify gate still requires the CURRENT version.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';

const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const byteOrder = (a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b));
const git = (root, args) => execFileSync('git', ['--no-replace-objects', '-C', root, ...args],
  { stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 32 * 1024 * 1024 });
const safePath = p => p && !path.posix.isAbsolute(p) && !/[\\\r\n\0]/.test(p)
  && p.split('/').every(part => part && part !== '.' && part !== '..');
const junk = p => {
  const parts = p.split('/');
  const base = parts.at(-1);
  return ['checksums.sha256', '.DS_Store'].includes(base) || base.startsWith('._')
    || base.endsWith('.pyc') || parts.slice(0, -1).includes('__pycache__');
};

function deployedFiles(dir) {
  const files = new Map();
  function visit(at, prefix = '') {
    for (const entry of fs.readdirSync(at, { withFileTypes: true })) {
      const rel = prefix + entry.name;
      if (!safePath(rel)) throw new Error(`unsafe deployed path: ${rel}`);
      if (entry.isDirectory()) visit(path.join(at, entry.name), `${rel}/`);
      else if (entry.isFile()) files.set(rel, fs.readFileSync(path.join(at, entry.name)));
      else throw new Error(`non-regular deployed file: ${rel}`);
    }
  }
  if (!fs.lstatSync(dir).isDirectory()) throw new Error('deployed directory is not a regular directory');
  visit(dir);
  return files;
}

// Byte-for-byte checksum manifest emitted by deploy-skill.sh manifest().
function manifest(files) {
  return [...files.keys()].sort(byteOrder)
    .map(rel => `${sha256(files.get(rel))}  ./${rel}\n`).join('');
}

function committedFiles(root, commit, dir) {
  const entries = git(root, ['ls-tree', '-r', '-z', commit, '--', `${dir}/`])
    .toString('utf8').split('\0').filter(Boolean);
  const files = new Map();
  for (const entry of entries) {
    const match = entry.match(/^(\d+) (\w+) ([a-f0-9]+)\t([\s\S]+)$/);
    if (!match) throw new Error('unreadable historical tree');
    const [, mode, kind, object, fullPath] = match;
    if (!fullPath.startsWith(`${dir}/`)) throw new Error('historical path escaped canonical directory');
    const rel = fullPath.slice(dir.length + 1);
    if (!safePath(rel)) throw new Error(`unsafe historical path: ${rel}`);
    if (junk(rel)) continue; // same exclusions as deploy-skill.sh list_source_files()
    if (kind !== 'blob' || !['100644', '100755'].includes(mode)) {
      throw new Error(`non-regular historical source: ${rel}`);
    }
    files.set(rel, git(root, ['cat-file', 'blob', object]));
  }
  return files;
}

function pipelineStamp(root, commit, canonicalPath, files) {
  // Plugin-only EPS skills use the plugin release; standalone and Aura-native
  // skills use the first vX.Y line (all matches on that line), else a tree hash.
  const plugin = canonicalPath.match(/^plugins\/([^/]+)\/skills\/[^/]+\/SKILL\.md$/);
  if (plugin) {
    const metadata = JSON.parse(git(root,
      ['show', `${commit}:plugins/${plugin[1]}/.claude-plugin/plugin.json`]).toString('utf8'));
    if (typeof metadata.version !== 'string' || !metadata.version) throw new Error('invalid historical plugin version');
    return metadata.version;
  }
  const text = files.get('SKILL.md').toString('utf8');
  const versionLine = text.split('\n').find(line => /v[0-9]+\.[0-9]+/.test(line));
  return versionLine ? versionLine.match(/v[0-9]+\.[0-9]+/g).join('\n')
    : `tree sha256 ${sha256(manifest(files)).slice(0, 12)}`;
}

function renderSkill(source, canonicalLabel, stamp, date) {
  const text = source.toString('utf8');
  if (!Buffer.from(text).equals(source)) throw new Error('historical SKILL.md is not UTF-8');
  const lines = text.split('\n');
  const end = lines.findIndex((line, i) => i > 0 && line.trim() === '---');
  if (lines[0] !== '---' || end < 0 || lines.slice(1, end).some(line => line.startsWith('# DEPLOYED COPY ('))) {
    throw new Error('historical source is not a canonical skill');
  }
  lines.splice(end, 0,
    `# DEPLOYED COPY (${date}, skill-deploy pipeline): the canonical home is`,
    `# ${canonicalLabel}. Deployed at ${stamp}.`,
    '# Edit the canonical copy first, then redeploy via tools/skill-deploy.');
  return Buffer.from(lines.join('\n'));
}

export function proveHistoricalDeployment({ root, canonicalPath, canonicalLabel, deployedDir, header, stripped }) {
  try {
    if (!safePath(canonicalPath)) throw new Error('unsafe canonical path');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(header.date)
        || new Date(`${header.date}T00:00:00Z`).toISOString().slice(0, 10) !== header.date) {
      throw new Error('invalid deployment date');
    }
    const deployed = deployedFiles(deployedDir);
    const checksums = deployed.get('checksums.sha256');
    deployed.delete('checksums.sha256'); // in-memory only
    if (!checksums || !checksums.equals(Buffer.from(manifest(deployed)))) {
      throw new Error('missing or invalid deployment checksum manifest');
    }
    const dir = path.posix.dirname(canonicalPath);
    const plugin = canonicalPath.match(/^plugins\/([^/]+)\/skills\//);
    const paths = [dir];
    if (plugin) paths.push(`plugins/${plugin[1]}/.claude-plugin/plugin.json`);
    // First-parent history of the checked-out canonical lineage, never --all.
    // Shallow/missing history cannot prove a missing version and fails closed.
    const commits = git(root, ['log', '--first-parent', '--format=%H', 'HEAD', '--', ...paths])
      .toString('utf8').trim().split('\n').filter(Boolean);
    for (const commit of commits) {
      let source;
      try { source = git(root, ['show', `${commit}:${canonicalPath}`]); }
      catch { continue; } // deletion in history is not a canonical candidate
      if (!source.equals(Buffer.from(stripped))) continue;
      const files = committedFiles(root, commit, dir);
      if (!files.has('SKILL.md')) continue;
      const stamp = pipelineStamp(root, commit, canonicalPath, files);
      if (stamp !== header.stamp) continue;
      files.set('SKILL.md', renderSkill(source, canonicalLabel, stamp, header.date));
      if (files.size !== deployed.size || [...files].some(([rel, bytes]) => !deployed.has(rel) || !bytes.equals(deployed.get(rel)))) continue;
      const blob = git(root, ['rev-parse', `${commit}:${canonicalPath}`]).toString('utf8').trim();
      return { commit, blob };
    }
    throw new Error('no exact prior committed canonical render in available first-parent history (fetch full history if shallow)');
  } catch (error) {
    return { error: error.message };
  }
}
