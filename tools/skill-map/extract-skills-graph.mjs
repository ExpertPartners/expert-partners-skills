#!/usr/bin/env node
// Skill Map Stage 1 extraction pipeline (aura intake/2026-08-04-skill-map-architecture-report.md).
// Walks the canonical skill repos, strict-parses every SKILL.md frontmatter (gray-matter),
// validates the additive skill-map metadata block (zod), and emits skills-graph.json.
// The build FAILS on: YAML parse errors, schema violations, name/folder mismatch,
// duplicate skill ids (outside the declared duplicate list), and any inherits / calls /
// defers-to id that does not resolve to a real SKILL.md.
//
// STRICT MODE (ruling 14, "skills are born dressed", Allison 2026-08-04): a SKILL.md
// in any canonical repo missing the skill-map block, or missing zone, tier, or status,
// FAILS the build. The former warning-and-holding-area behavior (unzoned as a non-fatal
// flag) is retired. Vendor catalog packs and non-canonical paths stay excluded via
// EXCLUDE, exactly as before.
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

const ZONES = ['surfaces', 'brain', 'hands', 'routing', 'finance', 'content', 'cataloging', 'brands'];
const TIERS = ['user', 'organization', 'plugin', 'project'];
const STATUSES = ['live', 'designed', 'benched', 'retired', 'sleeping'];
// Brand id vocabulary, RULED by Allison 2026-08-05 (Skill Map Rulings lane, flags item 8).
// Each id may carry a parent brand id (null = top-level). Registry source: aura ADR 0045.
// A ninth id for Allison's AI education lane (You've Got a Friend) mints only on the day
// its voice card is born, not before (ruled 2026-08-05).
const BRAND_IDS = {
  'expert-partners': { parent: null },
  'epic': { parent: null },
  'fam': { parent: null },
  'ag-personal-brand': { parent: null },
  'ag-luxury': { parent: null },
  'don-hobbs': { parent: 'expert-partners' },
  'the-strong-ones': { parent: 'ag-personal-brand' },
  'moxie': { parent: null },
};
const BRANDS = Object.keys(BRAND_IDS);
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

// Declared duplicates / pointers: paths that intentionally shadow a canonical copy.
// The mapped node comes from `keep`; the other path is recorded, not mapped.
// Ruled 2026-08-05 (flags item 3): the plugin path is canonical; the repo-root
// copy is now a pointer file naming the plugin path, kept here so the walk skips it.
const DECLARED_DUPLICATES = [
  { id: 'operating-doctrine', keep: 'eps:plugins/operating-doctrine/skills/operating-doctrine/SKILL.md', duplicate: 'eps:operating-doctrine/SKILL.md' },
  // session-wrap adopted into canonical 2026-08-05 (add-on brief note 4); the aura
  // .claude/skills copy stays loadable as the deployed copy for Aura Code sessions.
  { id: 'session-wrap', keep: 'eps:skills/session-wrap/SKILL.md', duplicate: 'aura:.claude/skills/session-wrap/SKILL.md' },
];

// ---------- schema ----------

const idList = z.union([z.string(), z.array(z.string())]).transform(v => (Array.isArray(v) ? v : [v]));

// brand-scope is list-valued (ruled 2026-08-05, flags item 6): a single id or a list,
// normalized to a list; null/omitted normalizes to [].
const brandList = z.union([z.enum(BRANDS), z.array(z.enum(BRANDS))]).nullish()
  .transform(v => (v == null ? [] : Array.isArray(v) ? v : [v]));

const SkillMeta = z.object({
  name: z.string().min(1),
  description: z.string().optional(),
  // zone, tier, status are REQUIRED (ruling 14 strict mode) -- no defaults, no null.
  tier: z.enum(TIERS),
  zone: z.enum(ZONES),
  status: z.enum(STATUSES),
  inherits: idList.default([INHERIT_ROOT]),
  calls: z.array(z.string()).default([]),
  'defers-to': z.array(z.string()).default([]),
  'brand-scope': brandList.default([]),
  subtitle: z.string().nullish().default(null),
  'render-note': z.string().nullish().default(null),
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

    // Strict-mode gate (ruling 14): name the violation precisely before the general
    // schema pass, so the CI error reads as the born-dressed rule, not a zod detail.
    const missingCore = ['zone', 'tier', 'status'].filter(f => parsed.data[f] == null);
    if (missingCore.length === 3) {
      fail(`missing skill-map block: ${tagged} has no zone/tier/status -- every new skill is born with its skill-map frontmatter block filled in (ruling 14, skills are born dressed); a skill without its block does not merge`);
      continue;
    }
    if (missingCore.length > 0) {
      fail(`born-dressed violation: ${tagged} is missing required field(s) ${missingCore.join(', ')} (ruling 14 strict mode: zone, tier, and status are required on every canonical SKILL.md)`);
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
      zone: meta.zone,
      status: meta.status,
      inherits: meta.inherits,
      calls: meta.calls,
      defersTo: meta['defers-to'],
      brandScope: meta['brand-scope'],
      subtitle: meta.subtitle ?? null,
      renderNote: meta['render-note'] ?? null,
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

// ---------- emit ----------
// (The former non-fatal "unzoned" holding area is retired: ruling 14 strict mode
// makes an unzoned skill a build failure above, so the flag can never be non-empty.)

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
  brands: BRAND_IDS,
  nodes: [...nodes.values()].sort((a, b) => a.id.localeCompare(b.id)),
  edges: edges.sort((a, b) => (a.from + a.type + a.to).localeCompare(b.from + b.type + b.to)),
  flags: {
    declaredDuplicates: duplicateRecords.sort(),
  },
  excluded: skippedPaths.sort(),
};

fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(outFile, JSON.stringify(graph, null, 2) + '\n');
console.log(`skills-graph.json written: ${graph.nodes.length} nodes, ${graph.edges.length} edges (strict mode: zone/tier/status verified on all), ${duplicateRecords.length} declared duplicate(s), ${skippedPaths.length} excluded path(s).`);
console.log(`output: ${outFile}`);
