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
// DEPLOYED COPIES (added 2026-09-04, aura issue #212): a skill deployed as a copy to a
// second agent surface is the SAME skill, not a second identity. The pipeline in
// tools/skill-deploy/deploy-skill.sh is the sole producer of such copies and stamps each
// with a DEPLOYED COPY header naming its canonical home (ADR 0056 point 8). This
// extractor classifies a SKILL.md as a deployed copy when it sits under a deployed-mount
// root (Codex discovers repo skills only under .agents/skills, so everything there is a
// copy by construction) or when it carries that header anywhere. A deployed copy is
// never mapped as a node; it must carry the header, the header must name the very
// canonical SKILL.md that owns its id, and stripping the header must yield the
// canonical file byte for byte. That last check is what makes the header a proof
// rather than a claim: without it a genuinely different skill wearing a canonical's
// name plus three pasted header lines would pass as a legitimate mirror. The deploy
// pipeline's --verify covers a copy's non-SKILL.md files and its manifest; this
// covers the identity file wherever it lives.
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
import { layoutGraph } from './layout-skills-graph.mjs';

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
  // The ONLY legitimate entry: a pointer file with no frontmatter at all, which
  // cannot carry a DEPLOYED COPY header and so cannot be classified by pass 3.
  // Ruled 2026-08-05 (flags item 3): the plugin path is canonical; the repo-root
  // copy is a pointer file naming it, kept here so the walk skips it.
  { id: 'operating-doctrine', keep: 'eps:plugins/operating-doctrine/skills/operating-doctrine/SKILL.md', duplicate: 'eps:operating-doctrine/SKILL.md' },
  // The aura .claude/skills copies of session-wrap, repo-standards and
  // research-intake USED to be listed here (2026-08-05, 08-07, 08-08). They are
  // not any more: a hand-maintained exemption list skipped them before any
  // classification ran, so those three paths were exempt from the header
  // requirement, the canonical-exists check, and the id-ownership check, which
  // is exactly the corruption class of aura issue #212 (research-intake was in
  // fact a hand-made copy with no manifest, found 2026-09-04). They are now
  // ordinary deployed copies: pipeline-produced, header-verified, byte-checked
  // against canonical in pass 3, and reported under flags.deployedMounts.
];

// Deployed-mount roots: every SKILL.md under one of these is a deployed copy by
// construction, whatever its header says. .agents/skills is the Codex repo-scope
// discovery path (learn.chatgpt.com/docs/build-skills, verified 2026-09-04); Codex
// cannot be pointed at .claude/skills, so the estate mirrors its project mount there
// through the deploy pipeline (aura .claude/skills -> aura .agents/skills).
const DEPLOYED_MOUNT_ROOTS = [
  /^[a-z-]+:\.agents\/skills\//,
];

// The DEPLOYED COPY header contract, written by tools/skill-deploy/deploy-skill.sh
// (render()) as YAML comment lines inside the frontmatter. Two lines: the date and
// producer, then "<repo> <path>. Deployed at <stamp>." Keep in step with the script.
const DEPLOYED_HEADER = /^# DEPLOYED COPY \((\d{4}-\d{2}-\d{2}), skill-deploy pipeline\): the canonical home is\s*\n# (\S+) (\S+?SKILL\.md)\. Deployed at (.+?)\.\s*$/m;
// The same three lines as a removable block, for the byte-fidelity check below:
// stripping it from a deployed copy must yield the canonical file byte for byte.
const DEPLOYED_HEADER_BLOCK = /^# DEPLOYED COPY \(\d{4}-\d{2}-\d{2}, skill-deploy pipeline\): the canonical home is\n# \S+ \S+?SKILL\.md\. Deployed at .+?\.\n# Edit the canonical copy first, then redeploy via tools\/skill-deploy\.\n/m;
// Header repo names -> walk keys. A header naming a repo this walk does not cover
// cannot be verified and fails the build.
const REPO_NAME_TO_KEY = { 'expert-partners-skills': 'eps', 'aura': 'aura' };

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

// Declared before repo discovery: the missing-checkout guard below calls fail(),
// and a const declared later sits in its temporal dead zone, so that guard used to
// die with a ReferenceError instead of printing the clear error it was written to give.
const errors = [];
function fail(msg) { console.error(`ERROR: ${msg}`); errors.push(msg); }

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


const nodes = new Map();        // id -> node
const duplicateRecords = [];    // declared duplicates encountered
const deployedMounts = [];      // deployed copies encountered (recorded, never mapped)
const skippedPaths = [];        // excluded files, recorded for the report

// Pass 1: collect and classify every SKILL.md. Classification never depends on walk
// order, so a deployed copy that sorts before its canonical (.agents before .claude)
// is handled the same as one that sorts after it.
const canonicalFiles = [];  // { repoKey, tagged, abs, raw }
const deployedFiles = [];   // { repoKey, tagged, abs, raw, header, mountRoot }

function readDeployedHeader(raw) {
  // Only the frontmatter block may carry the header; a stray match in the body is
  // prose about the header, not the header.
  const fm = raw.match(/^---\n([\s\S]*?)\n---/);
  if (!fm) return null;
  const m = fm[1].match(DEPLOYED_HEADER);
  if (!m) return null;
  return { date: m[1], repoName: m[2], canonicalPath: m[3], stamp: m[4] };
}

for (const [repoKey, root] of Object.entries(REPOS)) {
  if (!fs.existsSync(root)) continue;
  for (const abs of walk(root)) {
    const rel = path.relative(root, abs).split(path.sep).join('/');
    const tagged = `${repoKey}:${rel}`;

    if (EXCLUDE.some(rx => rx.test(tagged) || rx.test(`/${rel}/`) || rx.test(abs))) {
      skippedPaths.push(tagged);
      continue;
    }

    const dup = DECLARED_DUPLICATES.find(d => d.duplicate === tagged);
    if (dup) { duplicateRecords.push(tagged); continue; }

    const raw = fs.readFileSync(abs, 'utf8');
    const header = readDeployedHeader(raw);
    // Capture the matched mount root itself, so adding a root to
    // DEPLOYED_MOUNT_ROOTS needs no second edit and can never emit a wrong value.
    const mountRoot = DEPLOYED_MOUNT_ROOTS.map(rx => tagged.match(rx)?.[0]).find(Boolean) ?? null;
    if (mountRoot || header) {
      deployedFiles.push({ repoKey, tagged, abs, raw, header, mountRoot });
    } else {
      canonicalFiles.push({ repoKey, tagged, abs, raw });
    }
  }
}

// Pass 2: map canonical skills. This is the identity pass; a duplicate here is a
// REAL duplicate canonical id and fails the build exactly as before.
for (const { repoKey, tagged, abs, raw } of canonicalFiles) {
  let parsed;
  try {
    parsed = matter(raw);
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

// Pass 3: validate deployed copies against the canonical map. A copy is legitimate
// only when it is pipeline-produced (header present) and its header names the exact
// canonical SKILL.md that owns its id. Anything else is corruption, named precisely.
for (const { tagged, abs, raw, header, mountRoot } of deployedFiles) {
  const folder = path.basename(path.dirname(abs));
  if (!header) {
    fail(`deployed copy without a DEPLOYED COPY header: ${tagged} sits under a deployed mount root but was not produced by tools/skill-deploy/deploy-skill.sh (ADR 0056 point 8) -- redeploy it through the pipeline (--mirror-mount) instead of copying files by hand`);
    continue;
  }
  let parsed;
  try {
    parsed = matter(raw);
  } catch (e) {
    fail(`frontmatter does not parse: ${tagged} -> ${e.message.split('\n')[0]}`);
    continue;
  }
  const declaredName = parsed.data?.name;
  if (declaredName !== folder) {
    fail(`name/folder mismatch: ${tagged} declares name "${declaredName}" but lives in folder "${folder}"`);
    continue;
  }
  const repoKey = REPO_NAME_TO_KEY[header.repoName];
  if (!repoKey) {
    fail(`deployed copy names an unknown canonical repo: ${tagged} says its canonical home is "${header.repoName} ${header.canonicalPath}", and this walk covers only ${Object.keys(REPO_NAME_TO_KEY).join(', ')}`);
    continue;
  }
  const canonicalTagged = `${repoKey}:${header.canonicalPath}`;
  const canonicalAbs = path.join(REPOS[repoKey], ...header.canonicalPath.split('/'));
  if (canonicalTagged === tagged) {
    // The canonical file itself carries a header naming its own path: a mirror was
    // pasted back over canonical. Say that, because "orphan copy" would send the
    // operator to delete mirrors when the canonical is what needs restoring.
    fail(`canonical overwritten by a deployed copy: ${tagged} carries a DEPLOYED COPY header naming itself -- restore the canonical from git history, then redeploy its mirrors through tools/skill-deploy`);
    continue;
  }
  if (!fs.existsSync(canonicalAbs)) {
    fail(`deployed copy names a canonical home that does not exist: ${tagged} -> ${canonicalTagged} (a hand-transformed path, or canonical moved without a redeploy)`);
    continue;
  }
  const node = nodes.get(folder);
  if (!node) {
    fail(`orphan deployed copy: ${tagged} carries id "${folder}" but no canonical SKILL.md maps that id (canonical removed or renamed without removing the copy)`);
    continue;
  }
  if (node.source !== canonicalTagged) {
    fail(`deployed copy points at the wrong canonical home: ${tagged} names ${canonicalTagged}, but "${folder}" is canonical at ${node.source}`);
    continue;
  }
  // Byte fidelity. A header is a claim, not a proof: without this check a
  // genuinely different skill wearing a canonical's name plus three pasted
  // header lines would pass as a legitimate mirror and be verified by nothing
  // (the deploy pipeline's --verify only walks the mounts it is pointed at).
  // The pipeline writes exactly three header lines into the frontmatter, so
  // removing them must yield the canonical bytes.
  const stripped = raw.replace(DEPLOYED_HEADER_BLOCK, '');
  if (stripped === raw) {
    fail(`deployed copy carries a malformed DEPLOYED COPY header block: ${tagged} -- redeploy it through tools/skill-deploy instead of editing the header by hand`);
    continue;
  }
  if (stripped !== fs.readFileSync(canonicalAbs, 'utf8')) {
    fail(`deployed copy is not a faithful render of its canonical: ${tagged} differs from ${canonicalTagged} beyond the DEPLOYED COPY header -- it was hand-edited or built by something other than tools/skill-deploy; redeploy it (deploy-skill.sh --mirror-mount / --to ... --repair-drift)`);
    continue;
  }
  deployedMounts.push({
    path: tagged,
    id: folder,
    canonical: canonicalTagged,
    deployedAt: header.date,
    stamp: header.stamp,
    mount: mountRoot,
  });
}

// Declared duplicates are a hand-maintained exemption, so verify the hand: each
// entry's `keep` path must be the canonical this build actually mapped for that
// id. Without this the list can silently outlive the layout it describes.
for (const d of DECLARED_DUPLICATES) {
  if (!duplicateRecords.includes(d.duplicate)) continue;
  const node = nodes.get(d.id);
  if (!node) {
    fail(`declared duplicate "${d.id}": ${d.duplicate} was skipped as a pointer, but no canonical SKILL.md maps that id`);
  } else if (node.source !== d.keep) {
    fail(`declared duplicate "${d.id}": the list keeps ${d.keep}, but the mapped canonical is ${node.source} -- update DECLARED_DUPLICATES`);
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
    // Deployed copies verified against their canonical home this build. Each is the
    // same skill as its `canonical`, mounted for a second agent surface; none is a node.
    deployedMounts: deployedMounts.sort((a, b) => a.path.localeCompare(b.path)),
  },
  excluded: skippedPaths.sort(),
};

// Stage 2: bake build-time ELK layout (layered, INCLUDE_CHILDREN) into the same
// regeneration step, so the committed JSON always carries coordinates and the
// dashboard renderer never runs a layout engine. ELK stays a CI-only dependency.
await layoutGraph(graph);

fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(outFile, JSON.stringify(graph, null, 2) + '\n');
console.log(`skills-graph.json written: ${graph.nodes.length} nodes, ${graph.edges.length} edges (strict mode: zone/tier/status verified on all), ${duplicateRecords.length} declared duplicate(s), ${deployedMounts.length} deployed mount(s) verified against canonical, ${skippedPaths.length} excluded path(s).`);
console.log(`layout baked: ${graph.layout.width}x${graph.layout.height}, ${graph.layout.zones.length} zones, ${graph.layout.zones.reduce((a, z) => a + z.rooms.length, 0)} brand rooms (elkjs build-time only).`);
console.log(`output: ${outFile}`);
