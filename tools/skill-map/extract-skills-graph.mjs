#!/usr/bin/env node
// Skill Map Stage 1 extraction pipeline (aura intake/2026-08-04-skill-map-architecture-report.md).
// Walks the canonical skill repos, strict-parses every SKILL.md frontmatter (gray-matter),
// validates the additive skill-map metadata block (zod), and emits skills-graph.json.
// The build FAILS on: YAML parse errors, schema violations, name/folder mismatch,
// duplicate skill ids (outside the declared duplicate list), and any inherits / calls /
// defers-to id that does not resolve to a real SKILL.md. Unzoned skills are flagged,
// not fatal, per the approved schema.
//
// Usage: node extract-skills-graph.mjs [--eps <path>] [--aura <path>] [--out <file>]
//   --eps  expert-partners-skills checkout (default: this script's repo root)
//   --aura aura checkout (default: env AURA_PATH, else ../aura relative to the eps root)
//   --out  output path (default: <eps>/tools/skill-map/skills-graph.json)

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import matter from 'gray-matter';
import { z } from 'zod';

// ---------- configuration ----------

const ZONES = ['surfaces', 'brain', 'hands', 'routing', 'finance', 'content', 'cataloging'];
const TIERS = ['user', 'organization', 'plugin'];
const STATUSES = ['live', 'designed', 'benched', 'retired', 'sleeping'];
// Brand id vocabulary, assumed pending Allison's ruling (flags file item 8).
const BRANDS = ['expert-partners', 'epic', 'fam', 'ag-personal-brand', 'ag-luxury', 'don-hobbs', 'the-strong-ones', 'moxie'];
const INHERIT_ROOT = 'operating-doctrine';

// Paths that hold SKILL.md files but are NOT canonical skill sources
// (mirrors, extracts, caches). See aura intake/2026-08-04-skill-map-stage1-inventory.md.
const EXCLUDE = [
  /\/node_modules\//,
  /\/\.git\//,
  /\/\.cache\//,
  /\/worktrees\//,
  /^aura:skills\//,                  // stale sync mirrors of expert-partners-skills
  /^aura:docs\/estate\/extracts\//,  // reference extracts of external systems
];

// Declared duplicates: same content maintained at two paths on purpose.
// The mapped node comes from `keep`; the other path is recorded, not mapped.
const DECLARED_DUPLICATES = [
  { id: 'operating-doctrine', keep: 'eps:plugins/operating-doctrine/skills/operating-doctrine/SKILL.md', duplicate: 'eps:operating-doctrine/SKILL.md' },
];

// ---------- schema ----------

const idList = z.union([z.string(), z.array(z.string())]).transform(v => (Array.isArray(v) ? v : [v]));

const SkillMeta = z.object({
  name: z.string().min(1),
  description: z.string().optional(),
  tier: z.enum(TIERS).default('user'),
  zone: z.enum(ZONES).nullish().default(null),
  status: z.enum(STATUSES).default('designed'),
  inherits: idList.default([INHERIT_ROOT]),
  calls: z.array(z.string()).default([]),
  'defers-to': z.array(z.string()).default([]),
  'brand-scope': z.enum(BRANDS).nullish().default(null),
  subtitle: z.string().nullish().default(null),
}).passthrough(); // existing operational fields (allowed-tools, argument-hint, ...) pass through untouched

// ---------- cli / repo discovery ----------

const argv = process.argv.slice(2);
function arg(flag, fallback) {
  const i = argv.indexOf(flag);
  return i !== -1 && argv[i + 1] ? argv[i + 1] : fallback;
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const epsRoot = path.resolve(arg('--eps', path.join(scriptDir, '..', '..')));
const auraRoot = path.resolve(arg('--aura', process.env.AURA_PATH || path.join(epsRoot, '..', 'aura')));
const outFile = path.resolve(arg('--out', path.join(epsRoot, 'tools', 'skill-map', 'skills-graph.json')));

const REPOS = { eps: epsRoot, aura: auraRoot };
for (const [key, root] of Object.entries(REPOS)) {
  if (!fs.existsSync(root)) fail(`repo checkout missing: ${key} at ${root}`);
}

// ---------- walk ----------

function* walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === '.git' || entry.name === 'node_modules' || entry.name === '.cache') continue;
      yield* walk(p);
    } else if (entry.name === 'SKILL.md') {
      yield p;
    }
  }
}

const errors = [];
function fail(msg) { console.error(`ERROR: ${msg}`); errors.push(msg); }

const nodes = new Map();        // id -> node
const duplicateRecords = [];    // declared duplicates encountered
const skippedPaths = [];        // excluded files, recorded for the report

for (const [repoKey, root] of Object.entries(REPOS)) {
  for (const abs of walk(root)) {
    const rel = path.relative(root, abs).split(path.sep).join('/');
    const tagged = `${repoKey}:${rel}`;

    if (EXCLUDE.some(rx => rx.test(tagged) || rx.test(`/${rel}/`) || rx.test(abs))) {
      skippedPaths.push(tagged);
      continue;
    }

    const dup = DECLARED_DUPLICATES.find(d => d.duplicate === tagged);
    if (dup) { duplicateRecords.push(tagged); continue; }

    let parsed;
    try {
      parsed = matter(fs.readFileSync(abs, 'utf8'));
    } catch (e) {
      fail(`frontmatter does not parse: ${tagged} -> ${e.message.split('\n')[0]}`);
      continue;
    }

    const check = SkillMeta.safeParse(parsed.data);
    if (!check.success) {
      fail(`schema violation: ${tagged} -> ${check.error.issues.map(i => `${i.path.join('.')}: ${i.message}`).join('; ')}`);
      continue;
    }
    const meta = check.data;

    const folder = path.basename(path.dirname(abs));
    if (meta.name !== folder) {
      fail(`name/folder mismatch: ${tagged} declares name "${meta.name}" but lives in folder "${folder}"`);
      continue;
    }

    if (nodes.has(meta.name)) {
      fail(`duplicate skill id "${meta.name}": ${tagged} collides with ${nodes.get(meta.name).source}`);
      continue;
    }

    nodes.set(meta.name, {
      id: meta.name,
      source: tagged,
      repo: repoKey,
      tier: meta.tier,
      zone: meta.zone ?? null,
      status: meta.status,
      inherits: meta.inherits,
      calls: meta.calls,
      defersTo: meta['defers-to'],
      brandScope: meta['brand-scope'] ?? null,
      subtitle: meta.subtitle ?? null,
    });
  }
}

// ---------- reference resolution (the drift gate) ----------

const edges = [];
for (const node of nodes.values()) {
  const refs = [
    ...node.inherits.map(to => ({ to, type: 'inherits' })),
    ...node.calls.map(to => ({ to, type: 'calls' })),
    ...node.defersTo.map(to => ({ to, type: 'defers-to' })),
  ];
  for (const { to, type } of refs) {
    if (node.id === INHERIT_ROOT && type === 'inherits' && node.inherits.length === 0) continue;
    if (!nodes.has(to)) {
      fail(`dangling ${type} reference: ${node.id} -> "${to}" does not resolve to any SKILL.md`);
      continue;
    }
    if (to === node.id) {
      fail(`self reference: ${node.id} ${type} itself`);
      continue;
    }
    edges.push({ from: node.id, to, type });
  }
}

// ---------- flags (non-fatal) ----------

const unzoned = [...nodes.values()].filter(n => !n.zone).map(n => n.id).sort();

// ---------- emit ----------

function headSha(root) {
  try { return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root }).toString().trim(); }
  catch { return null; }
}

if (errors.length) {
  console.error(`\nskills-graph build FAILED with ${errors.length} error(s).`);
  process.exit(1);
}

const graph = {
  schema: 'skill-map/v1',
  generatedFrom: Object.fromEntries(Object.entries(REPOS).map(([k, r]) => [k, headSha(r)])),
  zones: ZONES,
  nodes: [...nodes.values()].sort((a, b) => a.id.localeCompare(b.id)),
  edges: edges.sort((a, b) => (a.from + a.type + a.to).localeCompare(b.from + b.type + b.to)),
  flags: {
    unzoned,
    declaredDuplicates: duplicateRecords.sort(),
  },
  excluded: skippedPaths.sort(),
};

fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(outFile, JSON.stringify(graph, null, 2) + '\n');
console.log(`skills-graph.json written: ${graph.nodes.length} nodes, ${graph.edges.length} edges, ${unzoned.length} unzoned (flagged), ${duplicateRecords.length} declared duplicate(s), ${skippedPaths.length} excluded path(s).`);
console.log(`output: ${outFile}`);
