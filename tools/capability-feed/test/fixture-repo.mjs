// A small synthetic repository with the same shape as this one, so every rule of
// the generator can be exercised without touching real canonical sources.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

function write(root, rel, content) {
  const abs = path.join(root, rel);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, typeof content === 'string' ? content : `${JSON.stringify(content, null, 2)}\n`);
}

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

export function graphFor(nodes) {
  return {
    schema: 'skill-map/v1',
    generatedFrom: { eps: 'fixture', aura: 'fixture' },
    zones: ['brain', 'content', 'hands'],
    brands: {},
    nodes: nodes.map(n => ({ ...NODE_DEFAULTS, ...n })),
    edges: [],
    flags: {},
    excluded: [],
    layout: { zones: [{ id: 'brain', label: 'The brain' }, { id: 'content', label: 'The marketing engines' }, { id: 'hands', label: 'The hands' }] },
  };
}

/** Build a fixture repo; `mutate` may edit the spec before it is written. Returns the root path. */
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
    },
    nodes: [
      { id: 'kit-writer', source: 'eps:plugins/agent-kit/skills/kit-writer/SKILL.md', repo: 'eps', status: 'designed', subtitle: 'bios on demand', inherits: [] },
      { id: 'kit-planner', source: 'eps:plugins/agent-kit/skills/kit-planner/SKILL.md', repo: 'eps', status: 'designed', inherits: [] },
      { id: 'alpha-one', source: 'eps:plugins/alpha/skills/alpha-one/SKILL.md', repo: 'eps', zone: 'hands' },
      { id: 'alpha-two', source: 'eps:plugins/alpha/skills/alpha-two/SKILL.md', repo: 'eps', zone: 'hands', calls: ['alpha-one'], defersTo: ['house-one'] },
      { id: 'house-one', source: 'eps:plugins/household/skills/house-one/SKILL.md', repo: 'eps', zone: 'hands' },
      { id: 'solo', source: 'eps:skills/solo/SKILL.md', repo: 'eps', tier: 'organization', zone: 'brain' },
      { id: 'aura-thing', source: 'aura:.claude/skills/aura-thing/SKILL.md', repo: 'aura', tier: 'project', zone: 'brain', status: 'retired', subtitle: 'an old aura job' },
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
