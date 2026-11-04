// A small synthetic repository with the same shape as this one, so every rule of
// the generator can be exercised without touching real canonical sources.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

/**
 * @typedef {object} SkillMdSpec
 * @property {string} name
 * @property {string} description
 * @property {string} [status]
 * @property {string} [zone]
 * @property {string} [tier]
 * @property {string | null} [subtitle]
 * @property {string} [extra]
 * @property {string | null} [heading]
 * @property {string[]} [calls]
 * @property {string[]} [defersTo]
 */

/**
 * A skill graph node; graphFor fills the fields left out from NODE_DEFAULTS.
 * @typedef {object} FixtureNode
 * @property {string} id
 * @property {string} source
 * @property {string} repo
 * @property {string} [status]
 * @property {string} [zone]
 * @property {string} [tier]
 * @property {string | null} [subtitle]
 * @property {string[]} [inherits]
 * @property {string[]} [calls]
 * @property {string[]} [defersTo]
 */

/**
 * Everything a fixture repo is written from.
 * @typedef {object} FixtureSpec
 * @property {{ name: string, owner: { name: string }, plugins: { name: string, source: string, version: string, description: string }[] }} marketplace
 * @property {Record<string, { name: string, version: string, description: string, author?: { name: string } }>} manifests plugin.json by package name
 * @property {Record<string, string>} readmes README.md by package name
 * @property {Record<string, string>} skills SKILL.md text by skill directory
 * @property {FixtureNode[]} nodes
 * @property {{ packages: Record<string, { presentAs?: string, portable?: boolean, evidence?: string }>, capabilityRecordSources: { path: string }[] }} config
 * @property {Record<string, { schema: string, records: object[] }>} capabilityRecords capability record documents by repo-relative path
 */

/**
 * @param {string} root
 * @param {string} rel
 * @param {string | object} content text, or a value written as JSON
 */
function write(root, rel, content) {
  const abs = path.join(root, rel);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, typeof content === 'string' ? content : `${JSON.stringify(content, null, 2)}\n`);
}

/** @param {SkillMdSpec} spec */
export function skillMd({ name, description, status = 'live', zone = 'content', tier = 'plugin', subtitle = null, extra = '', heading = null, calls = [], defersTo = [] }) {
  return [
    '---',
    `name: ${name}`,
    `description: ${JSON.stringify(description)}`,
    `tier: ${tier}`,
    `zone: ${zone}`,
    `status: ${status}`,
    ...(subtitle ? [`subtitle: ${JSON.stringify(subtitle)}`] : []),
    ...(calls.length ? [`calls: [${calls.join(', ')}]`] : []),
    ...(defersTo.length ? [`defers-to: [${defersTo.join(', ')}]`] : []),
    extra,
    '---',
    `# ${heading ?? name}`,
    '',
    'Body text that must never reach the feed.',
    '',
  ].filter(l => l !== '').join('\n');
}

const NODE_DEFAULTS = { tier: 'plugin', zone: 'content', status: 'live', inherits: ['operating-doctrine'], calls: [], defersTo: [], brandScope: [], subtitle: null, renderNote: null };

/** @param {FixtureNode[]} nodes */
export function graphFor(nodes) {
  return {
    schema: 'skill-map/v1',
    generatedFrom: { eps: 'fixture' },
    zones: ['brain', 'content', 'hands'],
    brands: {},
    nodes: nodes.map(n => ({ ...NODE_DEFAULTS, ...n })),
    edges: [],
    flags: {},
    excluded: [],
    layout: { zones: [{ id: 'brain', label: 'The brain' }, { id: 'content', label: 'The marketing engines' }, { id: 'hands', label: 'The hands' }] },
  };
}

/**
 * Build a fixture repo; `mutate` may edit the spec before it is written. Returns the root path.
 * @param {(spec: FixtureSpec) => FixtureSpec} [mutate]
 * @returns {string}
 */
export function makeRepo(mutate = s => s) {
  const spec = mutate({
    marketplace: {
      name: 'expert-partners',
      owner: { name: 'ExpertPartners' },
      plugins: [
        { name: 'agent-kit', source: './plugins/agent-kit', version: '0.1.0', description: 'Portable skills for agents.' },
        { name: 'alpha', source: './plugins/alpha', version: '1.2.0', description: 'Alpha operations toolbox' },
        { name: 'household', source: './plugins/household', version: '0.1.0', description: 'Household line, separate entity.' },
      ],
    },
    manifests: {
      'agent-kit': { name: 'agent-kit', version: '0.1.0', description: 'Portable skills.' },
      alpha: { name: 'alpha', version: '1.2.0', description: 'Alpha operations toolbox.', author: { name: 'Allison Gaddy' } },
      household: { name: 'household', version: '0.1.0', description: 'Household line.' },
    },
    readmes: {
      'agent-kit': '# Agent Kit\n\nTwo portable skills.\n\n## Skills by function\n\nWriting\n- kit-writer: writes things\n\nPlanning\n- kit-planner\n\n## Status\n\nDesigned.\n',
    },
    skills: {
      'plugins/agent-kit/skills/kit-writer': skillMd({ name: 'kit-writer', description: 'Writes bios for agents. Use when the agent says write my bio.', status: 'designed', subtitle: 'bios on demand', heading: 'Kit Writer -- v1.0 (2026-10-01)' }),
      'plugins/agent-kit/skills/kit-planner': skillMd({ name: 'kit-planner', description: 'Plans the week.', status: 'designed' }),
      'plugins/alpha/skills/alpha-one': skillMd({ name: 'alpha-one', description: 'Does the first alpha job.', zone: 'hands' }),
      'plugins/alpha/skills/alpha-two': skillMd({ name: 'alpha-two', description: 'Does the second alpha job.', zone: 'hands', calls: ['alpha-one'], defersTo: ['house-one'] }),
      'plugins/household/skills/house-one': skillMd({ name: 'house-one', description: 'Household inbox sweep.', zone: 'hands' }),
      'skills/solo': skillMd({ name: 'solo', description: 'A standalone skill.', tier: 'organization', zone: 'brain' }),
      'skills/old-thing': skillMd({ name: 'old-thing', description: 'An old job.', status: 'retired', tier: 'project', zone: 'brain', subtitle: 'an old job' }),
    },
    nodes: [
      { id: 'kit-writer', source: 'eps:plugins/agent-kit/skills/kit-writer/SKILL.md', repo: 'eps', status: 'designed', subtitle: 'bios on demand', inherits: [] },
      { id: 'kit-planner', source: 'eps:plugins/agent-kit/skills/kit-planner/SKILL.md', repo: 'eps', status: 'designed', inherits: [] },
      { id: 'alpha-one', source: 'eps:plugins/alpha/skills/alpha-one/SKILL.md', repo: 'eps', zone: 'hands' },
      { id: 'alpha-two', source: 'eps:plugins/alpha/skills/alpha-two/SKILL.md', repo: 'eps', zone: 'hands', calls: ['alpha-one'], defersTo: ['house-one'] },
      { id: 'house-one', source: 'eps:plugins/household/skills/house-one/SKILL.md', repo: 'eps', zone: 'hands' },
      { id: 'solo', source: 'eps:skills/solo/SKILL.md', repo: 'eps', tier: 'organization', zone: 'brain' },
      { id: 'old-thing', source: 'eps:skills/old-thing/SKILL.md', repo: 'eps', tier: 'project', zone: 'brain', status: 'retired', subtitle: 'an old job' },
    ],
    config: {
      packages: {
        'agent-kit': { presentAs: 'collection', portable: true, evidence: 'fixture README says portable' },
        household: { presentAs: 'excluded', evidence: 'fixture plugin.json says separate entity' },
      },
      capabilityRecordSources: [],
    },
    capabilityRecords: {},
  });

  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'capability-feed-fixture-'));
  write(root, '.claude-plugin/marketplace.json', spec.marketplace);
  for (const [name, manifest] of Object.entries(spec.manifests)) write(root, `plugins/${name}/.claude-plugin/plugin.json`, manifest);
  for (const [name, readme] of Object.entries(spec.readmes)) write(root, `plugins/${name}/README.md`, readme);
  for (const [dir, md] of Object.entries(spec.skills)) write(root, `${dir}/SKILL.md`, md);
  write(root, 'tools/skill-map/skills-graph.json', graphFor(spec.nodes));
  write(root, 'tools/capability-feed/feed.config.json', spec.config);
  for (const [rel, doc] of Object.entries(spec.capabilityRecords)) write(root, rel, doc);
  return root;
}
