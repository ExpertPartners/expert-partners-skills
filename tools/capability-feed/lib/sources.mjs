// Reads the canonical inputs the AI Workforce feed is generated from. Every input
// already has an owning producer or owner in this repo; this module only reads.
//
//   .claude-plugin/marketplace.json            plugin packages (marketplace owner)
//   plugins/<name>/.claude-plugin/plugin.json  package manifests
//   plugins/<name>/README.md                   package display name and, for a
//                                              collection, its shelves
//   tools/skill-map/skills-graph.json          every canonical skill, its lifecycle
//                                              status and relationships (produced by
//                                              tools/skill-map, never hand-edited)
//   <this repo's SKILL.md sources>             published description and display name
//   tools/capability-feed/feed.config.json     presentation policy (see README.md)
//   capability record sources named in config  future AI Capability Curator records

import fs from 'node:fs';
import path from 'node:path';
import matter from 'gray-matter';

// Shapes of the canonical inputs as their owners write them. The JSON files are
// read unvalidated; build-feed.mjs checks the fields it relies on before use.

/**
 * @typedef {object} MarketplaceEntry
 * @property {string} name
 * @property {string} source
 * @property {string} [version]
 * @property {string} [description]
 */

/**
 * @typedef {object} Marketplace
 * @property {string} [name]
 * @property {{ name?: string }} [owner]
 * @property {MarketplaceEntry[]} [plugins]
 */

/**
 * @typedef {object} PluginManifest
 * @property {string} [name]
 * @property {string} [version]
 * @property {string} [description]
 * @property {{ name?: string }} [author]
 */

/**
 * One node of tools/skill-map/skills-graph.json (schema skill-map/v1).
 * @typedef {object} GraphNode
 * @property {string} id
 * @property {string} source
 * @property {string} repo
 * @property {string} tier
 * @property {string} zone
 * @property {string} status
 * @property {string[]} inherits
 * @property {string[]} calls
 * @property {string[]} defersTo
 * @property {string[]} brandScope
 * @property {string | null} [subtitle]
 */

/**
 * @typedef {object} SkillGraph
 * @property {string} [schema]
 * @property {GraphNode[]} nodes
 * @property {{ zones?: { id: string, label: string }[] }} [layout]
 */

/**
 * Presentation policy for one package in feed.config.json.
 * @typedef {object} PackageRule
 * @property {string} [presentAs]
 * @property {boolean} [portable]
 * @property {string} [evidence]
 */

/**
 * @typedef {object} FeedConfig
 * @property {Record<string, PackageRule>} [packages]
 * @property {{ path?: string }[]} [capabilityRecordSources]
 */

/**
 * @typedef {object} PluginInput
 * @property {MarketplaceEntry} entry
 * @property {PluginManifest | null} manifest
 * @property {string | null} readme
 * @property {string} dir repo-relative, forward slashes
 */

/** @typedef {{ description: string | null, heading: string | null }} SkillDoc */

/**
 * A capability record as written by its source: any fields, none validated yet.
 * @typedef {{ [field: string]: unknown } | null} CapabilityRecordInput
 */

/**
 * @typedef {object} CapabilityRecordDoc
 * @property {unknown} [schema]
 * @property {CapabilityRecordInput[]} [records]
 */

/** @typedef {{ file: string, doc: CapabilityRecordDoc }} CapabilityRecordFile */

/**
 * @typedef {object} FeedInputs
 * @property {FeedConfig} config
 * @property {SkillGraph} graph
 * @property {Marketplace} marketplace
 * @property {PluginInput[]} plugins
 * @property {Map<string, SkillDoc>} skillDocs
 * @property {CapabilityRecordFile[]} [capabilityRecords]
 */

/** @typedef {{ name: string, skillIds: string[] }} Shelf */
/** @typedef {{ label: string, url: string }} SourceLink */
/** @typedef {{ credit: string | null, links: SourceLink[] }} Provenance */

export class FeedSourceError extends Error {
  /** @param {string | string[]} problems */
  constructor(problems) {
    const list = Array.isArray(problems) ? problems : [problems];
    super(`AI Workforce feed refused, canonical sources are invalid:\n  - ${list.join('\n  - ')}`);
    this.name = 'FeedSourceError';
    this.problems = list;
  }
}

/**
 * The parsed JSON document, or null after recording why it could not be read.
 * @param {string} abs
 * @param {string} label
 * @param {string[]} problems
 * @returns {unknown}
 */
function readJson(abs, label, problems) {
  if (!fs.existsSync(abs)) { problems.push(`${label} is missing (${abs})`); return null; }
  try {
    return JSON.parse(fs.readFileSync(abs, 'utf8'));
  } catch (e) {
    problems.push(`${label} is not valid JSON: ${/** @type {Error} */ (e).message}`);
    return null;
  }
}

/**
 * Body H1 of a markdown document, outside any frontmatter.
 * @param {string} markdown
 * @returns {string | null}
 */
export function firstHeading(markdown) {
  const body = matter(markdown).content;
  const m = body.match(/^#\s+(.+?)\s*$/m);
  return m ? m[1] : null;
}

/**
 * Shelves from a collection README section named "Skills by function": a plain
 * line names the shelf, the bullet lines under it name skill ids. Returns an
 * ordered list of { name, skillIds }.
 * @param {string} markdown
 * @returns {Shelf[]}
 */
export function parseShelves(markdown) {
  const section = markdown.match(/^##\s+Skills by function\s*$([\s\S]*?)(?=^##\s|(?![\s\S]))/m);
  if (!section) return [];
  /** @type {Shelf[]} */
  const shelves = [];
  for (const raw of section[1].split('\n')) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith('- ')) {
      if (!shelves.length) continue;
      for (const part of line.slice(2).split(',')) {
        const id = part.split(':')[0].trim().replace(/`/g, '');
        if (/^[a-z0-9-]+$/.test(id)) /** @type {Shelf} */ (shelves.at(-1)).skillIds.push(id);
      }
    } else {
      shelves.push({ name: line, skillIds: [] });
    }
  }
  return shelves.filter(s => s.skillIds.length);
}

/**
 * Optional provenance declared by a package README, in a section named
 * "Source material": prose credit plus https links, for example
 *   ## Source material
 *   Adapted from Jane Doe's free skills bank.
 *   - [Jane Doe's skills bank](https://example.com/bank)
 * Absent section means no provenance is claimed.
 * @param {string} markdown
 * @returns {Provenance | null}
 */
export function parseProvenance(markdown) {
  const section = markdown.match(/^##\s+Source material\s*$([\s\S]*?)(?=^##\s|(?![\s\S]))/m);
  if (!section) return null;
  const links = [...section[1].matchAll(/\[([^\]]+)\]\((https:\/\/[^)\s]+)\)/g)].map(m => ({ label: m[1], url: m[2] }));
  const credit = section[1].split('\n').map(l => l.trim()).find(l => l && !l.startsWith('-') && !l.startsWith('['));
  return credit || links.length ? { credit: credit ?? null, links } : null;
}

/**
 * Read everything the generator needs from a repo checkout. Throws FeedSourceError.
 * @param {string} repoRoot
 * @param {{ graphPath?: string, configPath?: string }} [options]
 * @returns {FeedInputs}
 */
export function readInputs(repoRoot, { graphPath, configPath } = {}) {
  /** @type {string[]} */
  const problems = [];
  const root = path.resolve(repoRoot);
  const configAbs = path.resolve(root, configPath ?? 'tools/capability-feed/feed.config.json');
  const graphAbs = path.resolve(root, graphPath ?? 'tools/skill-map/skills-graph.json');

  // Each is null only after a recorded problem, and problems throw just below.
  const config = /** @type {FeedConfig} */ (readJson(configAbs, 'feed.config.json', problems));
  const graph = /** @type {SkillGraph} */ (readJson(graphAbs, 'skills-graph.json', problems));
  const marketplace = /** @type {Marketplace} */ (readJson(path.join(root, '.claude-plugin', 'marketplace.json'), 'marketplace.json', problems));
  if (problems.length) throw new FeedSourceError(problems);

  /** @type {PluginInput[]} */
  const plugins = [];
  for (const entry of marketplace.plugins ?? []) {
    if (!entry || typeof entry.name !== 'string' || typeof entry.source !== 'string') {
      problems.push(`marketplace.json has a plugin entry without a name or source: ${JSON.stringify(entry)}`);
      continue;
    }
    const dir = path.resolve(root, entry.source);
    if (!dir.startsWith(root + path.sep)) { problems.push(`marketplace plugin "${entry.name}" source escapes the repo: ${entry.source}`); continue; }
    const manifest = /** @type {PluginManifest | null} */ (readJson(path.join(dir, '.claude-plugin', 'plugin.json'), `plugin.json for "${entry.name}"`, problems));
    const readmeAbs = path.join(dir, 'README.md');
    const readme = fs.existsSync(readmeAbs) ? fs.readFileSync(readmeAbs, 'utf8') : null;
    plugins.push({ entry, manifest, readme, dir: path.relative(root, dir).split(path.sep).join('/') });
  }

  // Published descriptions and display names for the skills this repo owns, read from
  // this repository's tree so the feed stays a pure function of it.
  /** @type {Map<string, SkillDoc>} */
  const skillDocs = new Map();
  for (const node of graph?.nodes ?? []) {
    if (typeof node?.source !== 'string' || !node.source.startsWith('eps:')) continue;
    const rel = node.source.slice('eps:'.length);
    const abs = path.join(root, rel);
    if (!fs.existsSync(abs)) { problems.push(`skill graph names ${node.source}, which does not exist in this checkout`); continue; }
    let parsed;
    try { parsed = matter(fs.readFileSync(abs, 'utf8')); } catch (e) { problems.push(`frontmatter does not parse: ${node.source}: ${/** @type {Error} */ (e).message.split('\n')[0]}`); continue; }
    const desc = typeof parsed.data.description === 'string' ? parsed.data.description : null;
    const h1 = parsed.content.match(/^#\s+(.+?)\s*$/m)?.[1] ?? null;
    skillDocs.set(node.id, { description: desc, heading: h1 });
  }

  // Future canonical capability records (AI Capability Curator, ADR 0098, history in GitHub Archive).
  // Each configured source is a repo-relative directory of *.json files; see README.
  /** @type {CapabilityRecordFile[]} */
  const capabilityRecords = [];
  for (const src of config?.capabilityRecordSources ?? []) {
    const dirAbs = path.resolve(root, src.path ?? '');
    if (!src.path || !dirAbs.startsWith(root + path.sep)) { problems.push(`capabilityRecordSources entry has no in-repo path: ${JSON.stringify(src)}`); continue; }
    if (!fs.existsSync(dirAbs)) { problems.push(`capability record source ${src.path} does not exist`); continue; }
    for (const file of fs.readdirSync(dirAbs).filter(f => f.endsWith('.json')).sort()) {
      const doc = /** @type {CapabilityRecordDoc | null} */ (readJson(path.join(dirAbs, file), `${src.path}/${file}`, problems));
      if (doc) capabilityRecords.push({ file: `${src.path}/${file}`, doc });
    }
  }

  if (problems.length) throw new FeedSourceError(problems);
  return { config, graph, marketplace, plugins, skillDocs, capabilityRecords };
}
