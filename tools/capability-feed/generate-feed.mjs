#!/usr/bin/env node
// Generates the public-safe AI Workforce feed for Expert Partners HQ from canonical
// repo truth. See README.md for the rail end to end.
//
// Usage: node generate-feed.mjs [--write | --check | --stdout] [options]
//   --write   regenerate; rewrite the feed file only when its records change
//             (an unchanged feed keeps its timestamps, so main does not churn)
//   --check   exit 1 when the committed feed differs from what the canonical
//             sources produce (drift, or a hand edit), or fails HQ's contract
//   --stdout  print the generated envelope instead of touching the file
// Options:
//   --repo <dir>     repository root (default: this script's repo)
//   --graph <file>   skill graph to read (default: tools/skill-map/skills-graph.json)
//   --config <file>  presentation policy (default: tools/capability-feed/feed.config.json)
//   --out <file>     feed file (default: tools/capability-feed/ai-workforce-feed.json)
//   --now <iso>      clock override, for reproducible runs and tests
//
// Exit codes: 0 ok, 1 drift (--check), 2 refused (invalid canonical sources).

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readInputs, FeedSourceError } from './lib/sources.mjs';
import { buildRecords, buildEnvelope, sameRecords, serialize } from './lib/build-feed.mjs';
import { contractIssues } from './lib/hq-contract.mjs';

const argv = process.argv.slice(2);
const has = flag => argv.includes(flag);
function arg(flag, fallback) {
  const i = argv.indexOf(flag);
  return i !== -1 && argv[i + 1] ? argv[i + 1] : fallback;
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(arg('--repo', path.join(scriptDir, '..', '..')));
const outFile = path.resolve(repoRoot, arg('--out', 'tools/capability-feed/ai-workforce-feed.json'));
const now = arg('--now', null) ?? new Date().toISOString();

function readExisting() {
  if (!fs.existsSync(outFile)) return null;
  try { return JSON.parse(fs.readFileSync(outFile, 'utf8')); } catch { return undefined; }
}

function main() {
  const inputs = readInputs(repoRoot, { graphPath: arg('--graph'), configPath: arg('--config') });
  const records = buildRecords(inputs);
  const envelope = buildEnvelope(records, { generatedAt: now });
  const rel = path.relative(repoRoot, outFile);
  const counts = ['collection', 'plugin', 'capability', 'agent', 'skill']
    .map(k => [k, records.filter(r => r.kind === k).length]).filter(([, c]) => c).map(([k, c]) => `${c} ${k}`).join(', ');

  if (has('--stdout')) {
    process.stdout.write(serialize(envelope));
    return 0;
  }

  const existing = readExisting();
  const existingValid = existing && contractIssues(existing).length === 0;

  if (has('--check')) {
    if (existing === null) { console.error(`DRIFT: ${rel} does not exist. Run: node tools/capability-feed/generate-feed.mjs --write`); return 1; }
    if (!existingValid) {
      console.error(`DRIFT: ${rel} does not satisfy HQ's contract:\n  ${existing === undefined ? 'not valid JSON' : contractIssues(existing).join('\n  ')}`);
      return 1;
    }
    if (!sameRecords(existing, envelope)) {
      console.error(`DRIFT: ${rel} is stale or hand-edited; it differs from what the canonical sources produce. Run: node tools/capability-feed/generate-feed.mjs --write`);
      return 1;
    }
    console.log(`${rel} matches canonical sources (${records.length} records: ${counts}).`);
    return 0;
  }

  if (has('--write')) {
    if (existingValid && sameRecords(existing, envelope)) {
      console.log(`${rel} unchanged (${records.length} records: ${counts}).`);
      return 0;
    }
    fs.writeFileSync(outFile, serialize(envelope));
    console.log(`${rel} written: ${records.length} records (${counts}), generatedAt ${envelope.generatedAt}.`);
    return 0;
  }

  console.log(`Feed valid: ${records.length} records (${counts}). Nothing written; pass --write, --check, or --stdout.`);
  return 0;
}

try {
  process.exitCode = main();
} catch (e) {
  if (e instanceof FeedSourceError) {
    console.error(e.message);
    process.exitCode = 2;
  } else {
    throw e;
  }
}
