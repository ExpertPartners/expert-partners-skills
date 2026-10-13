// Pure builder for the AI Workforce feed: canonical inputs in, HQ records out.
// No clock, no network, no filesystem. The only time value is passed in by the
// caller, so the same inputs always produce the same records.
//
// Truth rules (README.md has the long form):
//   - Every field comes from a named canonical source, or it is left empty / omitted.
//   - Lifecycle "live" means the canonical source is in force. It is NOT evidence of
//     deployment, so it maps to HQ status "Unknown". Only a canonical capability
//     record carrying verified surfaces can make a record "Active".
//   - Nothing is copied wholesale from a source; records are projected field by field.

import { FeedSourceError } from './sources.mjs';
import { parseShelves, parseProvenance, firstHeading } from './sources.mjs';
import { WORKFORCE_FEED_SCHEMA, WORKFORCE_STATUSES, contractIssues } from './hq-contract.mjs';
import { scanForLeaks, isPublicSafeUrl } from './public-safety.mjs';

export const GRAPH_SCHEMA = 'skill-map/v1';
export const CAPABILITY_RECORD_SCHEMA = 'expert-partners-capability-record/v1';
export const INHERIT_ROOT = 'operating-doctrine';

// Canonical lifecycle (skill-map frontmatter `status`) to HQ status.
export const LIFECYCLE_STATUS = {
  live: 'Unknown',
  designed: 'Designed',
  benched: 'Deprecated',
  retired: 'Retired',
  sleeping: 'Unknown',
};

const REPO_NAMES = { eps: 'expert-partners-skills', aura: 'aura' };
const ID_RX = /^[a-z0-9-]+$/;
const PRESENT_AS = ['plugin', 'collection', 'excluded'];
const KIND_ORDER = ['collection', 'plugin', 'capability', 'agent', 'skill'];

// HQ WorkforceRecord field order; every record is emitted in exactly this order.
const KEY_ORDER = [
  'id', 'humanName', 'kind', 'summary', 'status', 'source', 'maintainer', 'verifiedOwner',
  'collectionIds', 'categories', 'portable', 'verifiedSurfaces', 'invocationInstructions',
  'sourceLinks', 'lastVerified', 'containsSkillIds', 'replacedBy', 'replaces', 'relatedIds',
  'accessNote', 'technicalDetail', 'need', 'keywords', 'bestFor', 'useCases', 'askExamples',
  'outcome', 'example',
];

// Fields a canonical capability record may set on an existing record (replace),
// plus the two it may extend (union). Everything else in a record is ignored.
const RECORD_REPLACE_FIELDS = [
  'humanName', 'summary', 'status', 'source', 'maintainer', 'verifiedOwner', 'categories',
  'verifiedSurfaces', 'invocationInstructions', 'sourceLinks', 'lastVerified', 'replacedBy',
  'replaces', 'accessNote', 'bestFor', 'useCases', 'askExamples', 'outcome', 'portable',
];
const RECORD_UNION_FIELDS = ['relatedIds', 'keywords'];
const NEW_RECORD_KINDS = ['capability', 'agent'];

const STOPWORDS = new Set(['the', 'and', 'for', 'with', 'your', 'from', 'that', 'this', 'into', 'are', 'you', 'one', 'any', 'all', 'its', 'per', 'not', 'but', 'how', 'what', 'who', 'every', 'skill', 'skills']);

// ---------- text helpers ----------

const SMALL_WORDS = new Set(['a', 'an', 'and', 'or', 'of', 'to', 'in', 'on', 'by', 'for', 'the']);
export function titleCase(id) {
  return id.split('-').filter(Boolean).map((w, i) => {
    if (i > 0 && SMALL_WORDS.has(w)) return w;
    if (w.length <= 2) return w.toUpperCase();
    return w[0].toUpperCase() + w.slice(1);
  }).join(' ');
}

function collapse(s) { return String(s).replace(/\s+/g, ' ').trim(); }

/** First sentence of published prose, whitespace collapsed. */
export function firstSentence(text) {
  const t = collapse(text);
  const m = t.match(/^(.+?[.!?])(?=\s+[A-Z0-9"'(]|$)/);
  return (m ? m[1] : t).trim();
}

function asSentence(fragment) {
  const t = collapse(fragment);
  if (!t) return t;
  const cap = t[0].toUpperCase() + t.slice(1);
  return /[.!?]$/.test(cap) ? cap : `${cap}.`;
}

/**
 * A display name from a document heading: markdown emphasis removed, and any
 * version stamp, tagline, or trailing parenthetical cut, so
 * "Pin -- v4.10 (2026-09-08)" reads "Pin".
 */
export function displayName(h) {
  if (!h) return null;
  let t = collapse(h.replace(/[`*_]/g, ''));
  while (/\([^()]*\)/.test(t)) t = t.replace(/\s*\([^()]*\)/g, '');
  t = t.split(/\s+(?:--|\u2014|\u2013|-)\s+|:\s+/)[0].trim();
  return t && t.length <= 200 ? t : null;
}

/**
 * The published "Use when ..." sentence of a description, verbatim, or null.
 * Quoted as written rather than parsed into fragments, so nothing is invented.
 */
export function useWhenSentence(description) {
  if (!description) return null;
  const sentences = collapse(description).split(/(?<=[.!?])\s+(?=[A-Z0-9"'(])/);
  return sentences.find(t => /^Use (?:it |this )?when(?:ever)?\b/.test(t)) ?? null;
}

/** Search keywords: words from the parts in priority order, capped, then sorted. */
export function keywordsFrom(...parts) {
  const out = new Set();
  for (const part of parts.flat()) {
    if (!part) continue;
    for (const w of String(part).toLowerCase().split(/[^a-z0-9]+/)) {
      if (w.length >= 3 && !STOPWORDS.has(w)) out.add(w);
      if (out.size >= 40) return [...out].sort();
    }
  }
  return [...out].sort();
}

export function isoSeconds(date) {
  const d = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(d.getTime())) throw new FeedSourceError(`not a valid timestamp: ${date}`);
  return d.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

// ---------- status wording ----------

function accessNoteFor(status, surfaces) {
  switch (status) {
    case 'Active': return `Verified available on: ${surfaces.join(', ')}.`;
    case 'Designed': return 'Designed, not yet deployed. Availability depends on what your AI assistant can load.';
    case 'Deprecated': return 'Not for new work.';
    case 'Retired': return 'Retired. Kept for history only.';
    default: return 'Where this is available has not been verified yet.';
  }
}

function usageLineFor(status) {
  if (status === 'Retired' || status === 'Deprecated') return 'Do not use for new work.';
  return 'Describe what you need in plain language. An AI assistant that has this skill loaded uses it when your request matches its purpose.';
}

export function aggregateStatus(statuses) {
  if (!statuses.length) return 'Unknown';
  const current = statuses.filter(s => s !== 'Retired' && s !== 'Deprecated');
  if (!current.length) return statuses.every(s => s === 'Retired') ? 'Retired' : 'Deprecated';
  return current.every(s => s === current[0]) ? current[0] : 'Unknown';
}

function ordered(rec) {
  const out = {};
  for (const k of KEY_ORDER) if (rec[k] !== undefined) out[k] = rec[k];
  return out;
}

// ---------- builder ----------

/** Build the HQ records from canonical inputs. Throws FeedSourceError when a source is invalid. */
export function buildRecords(inputs) {
  const problems = [];
  const { config, graph, marketplace, plugins, skillDocs, capabilityRecords = [] } = inputs;

  if (graph?.schema !== GRAPH_SCHEMA) problems.push(`skills-graph.json schema is ${JSON.stringify(graph?.schema)}, expected "${GRAPH_SCHEMA}"`);
  if (!Array.isArray(graph?.nodes)) problems.push('skills-graph.json has no nodes array');
  if (!Array.isArray(marketplace?.plugins)) problems.push('marketplace.json has no plugins array');
  if (problems.length) throw new FeedSourceError(problems);

  const zoneLabels = new Map((graph.layout?.zones ?? []).map(z => [z.id, z.label]));
  const zoneLabel = zone => zoneLabels.get(zone) ?? titleCase(zone);
  const marketplaceName = marketplace.name ?? 'expert-partners';
  const marketplaceOwner = marketplace.owner?.name;

  // Packages and their presentation policy.
  const policy = config?.packages ?? {};
  const pkgByDir = new Map();
  for (const p of plugins) {
    const name = p.entry.name;
    const rule = policy[name] ?? {};
    const presentAs = rule.presentAs ?? 'plugin';
    if (!PRESENT_AS.includes(presentAs)) problems.push(`feed.config.json: package "${name}" presentAs must be one of ${PRESENT_AS.join(', ')}`);
    if (!ID_RX.test(name)) problems.push(`marketplace plugin name "${name}" is not a valid feed id`);
    if (p.manifest?.name !== name) problems.push(`plugin.json name "${p.manifest?.name}" does not match marketplace entry "${name}"`);
    const version = p.entry.version ?? p.manifest?.version;
    if (p.entry.version && p.manifest?.version && p.entry.version !== p.manifest.version) {
      problems.push(`version mismatch for "${name}": marketplace.json ${p.entry.version}, plugin.json ${p.manifest.version}`);
    }
    if (!version) problems.push(`plugin "${name}" declares no version`);
    pkgByDir.set(p.dir, { p, name, rule, presentAs, version, id: presentAs === 'collection' ? name : `${name}-plugin`, skillIds: [] });
  }
  for (const [name, rule] of Object.entries(policy)) {
    if (!plugins.some(p => p.entry.name === name)) problems.push(`feed.config.json names package "${name}", which is not in marketplace.json`);
    if (typeof rule?.evidence !== 'string' || !rule.evidence.trim()) problems.push(`feed.config.json package "${name}" must cite its canonical evidence`);
  }

  // Skills.
  const seen = new Set();
  const skills = [];
  for (const n of graph.nodes) {
    if (!n || typeof n.id !== 'string' || !ID_RX.test(n.id) || n.id.length > 120) { problems.push(`skill graph node has an invalid id: ${JSON.stringify(n?.id)}`); continue; }
    if (seen.has(n.id)) { problems.push(`skill graph has duplicate id "${n.id}"`); continue; }
    seen.add(n.id);
    if (!(n.status in LIFECYCLE_STATUS)) { problems.push(`skill "${n.id}" has unknown lifecycle status ${JSON.stringify(n.status)}`); continue; }
    if (!(n.repo in REPO_NAMES) || typeof n.source !== 'string' || !n.source.startsWith(`${n.repo}:`)) { problems.push(`skill "${n.id}" has an unrecognized source ${JSON.stringify(n.source)}`); continue; }
    const m = n.source.match(/^eps:(plugins\/[^/]+)\/skills\/[^/]+\/SKILL\.md$/);
    let pkg = null;
    if (m) {
      pkg = pkgByDir.get(m[1]) ?? null;
      if (!pkg) { problems.push(`skill "${n.id}" lives in ${m[1]}, which is not a marketplace plugin`); continue; }
    }
    skills.push({ n, pkg });
  }

  const excluded = new Set(skills.filter(s => s.pkg?.presentAs === 'excluded').map(s => s.n.id));
  const records = new Map();
  const explicitStatus = new Set();

  // Collection shelves and provenance, from the package README.
  for (const pkg of pkgByDir.values()) {
    pkg.heading = displayName(pkg.p.readme ? firstHeading(pkg.p.readme) : null);
    pkg.shelves = pkg.presentAs === 'collection' && pkg.p.readme ? parseShelves(pkg.p.readme) : [];
    pkg.provenance = pkg.p.readme ? parseProvenance(pkg.p.readme) : null;
    for (const link of pkg.provenance?.links ?? []) {
      if (!isPublicSafeUrl(link.url)) problems.push(`package "${pkg.name}" README cites a link that is not public-safe: ${link.url}`);
    }
  }

  for (const { n, pkg } of skills) {
    if (excluded.has(n.id)) continue;
    const doc = n.repo === 'eps' ? skillDocs.get(n.id) : null;
    const status = LIFECYCLE_STATUS[n.status];
    const humanName = displayName(doc?.heading) ?? titleCase(n.id);
    const subtitle = typeof n.subtitle === 'string' && n.subtitle.trim() ? collapse(n.subtitle) : null;
    const summary = doc?.description ? firstSentence(doc.description) : subtitle ? asSentence(subtitle) : `${humanName}.`;
    const shelf = pkg?.shelves.find(s => s.skillIds.includes(n.id))?.name;
    const categories = [zoneLabel(n.zone), ...(shelf ? [shelf] : [])];
    const portable = pkg?.rule.portable === true ? true : 'unknown';
    const pkgKind = pkg?.presentAs === 'collection' ? 'collection' : 'plugin';
    const packaging = pkg
      ? (pkgKind === 'collection'
        ? `Part of the ${pkg.heading ?? titleCase(pkg.name)} collection.`
        : `Packaged in the ${titleCase(pkg.name)} plugin, version ${pkg.version}.`)
      : `Standalone skill in the ${REPO_NAMES[n.repo]} repository.`;
    const useWhen = useWhenSentence(doc?.description);
    const invocationInstructions = [packaging, usageLineFor(status)];
    if (portable === true && status !== 'Retired') invocationInstructions.push('Works with any AI assistant that can load skills or read a text file.');

    const technicalDetail = {
      canonicalSource: `${REPO_NAMES[n.repo]}/${n.source.slice(n.repo.length + 1)}`,
      lifecycle: n.status,
      tier: String(n.tier),
      zone: String(n.zone),
      packaging: pkg ? `${pkg.name} ${pkgKind} v${pkg.version} (${marketplaceName} marketplace)` : 'standalone',
    };
    const inherits = (n.inherits ?? []).filter(id => !excluded.has(id));
    const calls = (n.calls ?? []).filter(id => !excluded.has(id));
    const defersTo = (n.defersTo ?? []).filter(id => !excluded.has(id));
    if (inherits.length) technicalDetail.inherits = inherits.join(', ');
    if (calls.length) technicalDetail.calls = calls.join(', ');
    if (defersTo.length) technicalDetail.defersTo = defersTo.join(', ');
    if ((n.brandScope ?? []).length) technicalDetail.brandScope = n.brandScope.join(', ');

    if (pkg) pkg.skillIds.push(n.id);
    records.set(n.id, {
      id: n.id,
      humanName,
      kind: 'skill',
      summary,
      status,
      source: pkg?.provenance?.credit ?? undefined,
      maintainer: pkg ? (pkg.p.manifest?.author?.name ?? marketplaceOwner) : undefined,
      collectionIds: pkgKind === 'collection' && pkg ? [pkg.id] : [],
      categories,
      portable,
      verifiedSurfaces: [],
      invocationInstructions,
      sourceLinks: (pkg?.provenance?.links ?? []).map(l => ({ ...l })),
      lastVerified: `Not yet verified on any platform. Canonical lifecycle: ${n.status}.`,
      containsSkillIds: [],
      relatedIds: [...new Set([...inherits, ...calls, ...defersTo])].filter(id => id !== INHERIT_ROOT && id !== n.id),
      _packageId: pkg?.id,
      accessNote: accessNoteFor(status, []),
      technicalDetail,
      keywords: keywordsFrom(n.id, humanName, subtitle, categories, pkg?.name, summary),
      bestFor: subtitle ? [subtitle] : [],
      useCases: useWhen ? [useWhen] : [],
      askExamples: [],
      example: false,
    });
  }

  // Packages: one record each, plugin or collection.
  for (const pkg of pkgByDir.values()) {
    if (pkg.presentAs === 'excluded') continue;
    const isCollection = pkg.presentAs === 'collection';
    let contains = [...pkg.skillIds].sort();
    let categories = [...new Set(contains.map(id => records.get(id).categories[0]))].sort();
    if (isCollection) {
      for (const shelf of pkg.shelves) {
        for (const id of shelf.skillIds) if (!pkg.skillIds.includes(id)) problems.push(`collection "${pkg.name}" README shelf "${shelf.name}" lists "${id}", which is not a skill in the package`);
      }
      const shelfOrder = pkg.shelves.flatMap(s => s.skillIds).filter(id => pkg.skillIds.includes(id));
      contains = [...new Set([...shelfOrder, ...contains])];
      if (pkg.shelves.length) categories = pkg.shelves.map(s => s.name);
    }
    const portable = pkg.rule.portable === true ? true : 'unknown';
    const humanName = pkg.heading ?? (isCollection ? titleCase(pkg.name) : `${titleCase(pkg.name)} Plugin`);
    const invocationInstructions = isCollection && portable === true
      ? ['Choose a skill in this collection, then use it in any AI assistant that can load skills or read a text file.']
      : [`Packaged as the ${pkg.name} plugin, version ${pkg.version}, in the ${marketplaceName} plugin marketplace.`,
        contains.length === 1
          ? 'Contains 1 skill. It activates when a request matches its purpose.'
          : `Contains ${contains.length} skills. Each one activates when a request matches its purpose.`];
    records.set(pkg.id, {
      id: pkg.id,
      humanName,
      kind: isCollection ? 'collection' : 'plugin',
      summary: asSentence(pkg.p.entry.description ?? pkg.p.manifest?.description ?? humanName),
      status: 'Unknown', // aggregated below, after capability records apply
      source: pkg.provenance?.credit ?? undefined,
      maintainer: pkg.p.manifest?.author?.name ?? marketplaceOwner,
      collectionIds: [],
      categories,
      portable,
      verifiedSurfaces: [],
      invocationInstructions,
      sourceLinks: (pkg.provenance?.links ?? []).map(l => ({ ...l })),
      lastVerified: `Not yet verified on any platform. Package version ${pkg.version}.`,
      containsSkillIds: contains,
      relatedIds: [],
      accessNote: '',
      technicalDetail: {
        canonicalSource: `expert-partners-skills/${pkg.p.dir}`,
        packageVersion: String(pkg.version),
        marketplace: marketplaceName,
        presentedAs: isCollection ? 'collection' : 'plugin',
        skillCount: String(contains.length),
      },
      keywords: keywordsFrom(pkg.name, humanName, categories, pkg.p.entry.description),
      bestFor: [],
      useCases: [],
      askExamples: [],
      example: false,
      _isPackage: true,
    });
  }

  applyCapabilityRecords(records, capabilityRecords, explicitStatus, problems);

  // Package status is the honest aggregate of what it contains, unless a canonical
  // capability record set it explicitly.
  for (const rec of records.values()) {
    if (rec._isPackage && !explicitStatus.has(rec.id)) rec.status = aggregateStatus(rec.containsSkillIds.map(id => records.get(id)?.status).filter(Boolean));
    if (!rec.accessNote) rec.accessNote = accessNoteFor(rec.status, rec.verifiedSurfaces);
  }

  // Relationships resolve to records in this feed, and only to them.
  for (const rec of records.values()) {
    const related = new Set(rec.relatedIds);
    if (rec._packageId) related.add(rec._packageId);
    related.delete(rec.id);
    rec.relatedIds = [...related].filter(id => records.has(id)).sort();
    for (const field of ['replacedBy', 'replaces']) {
      if (rec[field] !== undefined && !records.has(rec[field])) problems.push(`record "${rec.id}" ${field} "${rec[field]}" does not resolve to a record in the feed`);
    }
    for (const id of rec.containsSkillIds) {
      const target = records.get(id);
      if (!target || target.kind !== 'skill') problems.push(`record "${rec.id}" contains "${id}", which is not a skill in the feed`);
    }
    for (const id of rec.collectionIds) {
      const target = records.get(id);
      if (!target || target.kind !== 'collection') problems.push(`record "${rec.id}" names collection "${id}", which is not a collection in the feed`);
      else if (!target.containsSkillIds.includes(rec.id)) problems.push(`collection "${id}" does not list member "${rec.id}"`);
    }
  }

  if (problems.length) throw new FeedSourceError(problems);

  return [...records.values()]
    .map(r => { delete r._packageId; delete r._isPackage; return ordered(r); })
    .sort((a, b) => (KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind)) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

function isStringList(v) { return Array.isArray(v) && v.every(x => typeof x === 'string'); }

function applyCapabilityRecords(records, sources, explicitStatus, problems) {
  const claimed = new Map();
  for (const { file, doc } of sources) {
    if (doc?.schema !== CAPABILITY_RECORD_SCHEMA || !Array.isArray(doc.records)) {
      problems.push(`${file}: expected { "schema": "${CAPABILITY_RECORD_SCHEMA}", "records": [...] }`);
      continue;
    }
    for (const r of doc.records) {
      const where = `${file} record ${JSON.stringify(r?.id)}`;
      if (!r || typeof r.id !== 'string' || !ID_RX.test(r.id) || r.id.length > 120) { problems.push(`${where}: invalid id`); continue; }
      if (claimed.has(r.id)) { problems.push(`${where}: already defined in ${claimed.get(r.id)} (one canonical record per id)`); continue; }
      claimed.set(r.id, file);

      let rec = records.get(r.id);
      if (!rec) {
        if (!NEW_RECORD_KINDS.includes(r.kind)) { problems.push(`${where}: a new record must have kind ${NEW_RECORD_KINDS.join(' or ')}`); continue; }
        if (typeof r.humanName !== 'string' || typeof r.summary !== 'string') { problems.push(`${where}: a new record needs humanName and summary`); continue; }
        rec = {
          id: r.id, humanName: r.humanName, kind: r.kind, summary: r.summary, status: 'Unknown',
          collectionIds: [], categories: [], portable: 'unknown', verifiedSurfaces: [], invocationInstructions: [],
          sourceLinks: [], lastVerified: 'Not yet verified on any platform.', containsSkillIds: [], relatedIds: [],
          accessNote: '', technicalDetail: { canonicalSource: file }, keywords: keywordsFrom(r.id, r.humanName),
          bestFor: [], useCases: [], askExamples: [], example: false,
        };
        if (r.containsSkillIds !== undefined) {
          if (!isStringList(r.containsSkillIds)) { problems.push(`${where}: containsSkillIds must be a list of ids`); continue; }
          rec.containsSkillIds = [...r.containsSkillIds];
        }
        records.set(r.id, rec);
      } else if (r.kind !== undefined && r.kind !== rec.kind) {
        problems.push(`${where}: cannot change kind from ${rec.kind} to ${r.kind}`);
        continue;
      }

      for (const field of RECORD_REPLACE_FIELDS) {
        if (r[field] === undefined) continue;
        const v = r[field];
        const okString = typeof v === 'string';
        const valid = {
          status: okString && WORKFORCE_STATUSES.includes(v),
          portable: v === true || v === false || v === 'unknown',
          categories: isStringList(v), verifiedSurfaces: isStringList(v), invocationInstructions: isStringList(v),
          bestFor: isStringList(v), useCases: isStringList(v), askExamples: isStringList(v),
          sourceLinks: Array.isArray(v) && v.every(l => l && typeof l.label === 'string' && typeof l.url === 'string' && isPublicSafeUrl(l.url)),
        }[field] ?? okString;
        if (!valid) { problems.push(`${where}: field "${field}" has an invalid value`); continue; }
        rec[field] = field === 'sourceLinks' ? v.map(l => ({ label: l.label, url: l.url })) : (Array.isArray(v) ? [...v] : v);
        if (field === 'status') explicitStatus.add(r.id);
      }
      for (const field of RECORD_UNION_FIELDS) {
        if (r[field] === undefined) continue;
        if (!isStringList(r[field])) { problems.push(`${where}: field "${field}" must be a list of strings`); continue; }
        rec[field] = field === 'keywords' ? keywordsFrom(rec.keywords, r.keywords) : [...new Set([...rec[field], ...r[field]])];
        if (field === 'relatedIds') for (const id of r[field]) if (!records.has(id)) problems.push(`${where}: relatedIds names "${id}", which is not in the feed`);
      }
      if (r.verifiedAt !== undefined) rec.technicalDetail = { ...rec.technicalDetail, verifiedAt: String(r.verifiedAt) };

      // Active is a claim about deployment. It needs named, verified surfaces.
      if (rec.status === 'Active' && (!rec.verifiedSurfaces.length || r.lastVerified === undefined)) {
        problems.push(`${where}: status Active requires verifiedSurfaces and lastVerified from a real verification`);
      }
      if (r.accessNote === undefined && (r.status !== undefined || r.verifiedSurfaces !== undefined)) {
        rec.accessNote = accessNoteFor(rec.status, rec.verifiedSurfaces);
      }
    }
  }
}

// HQ reads the feed from GitHub's repository contents API, which returns an empty
// `content` field for files over 1 MB unless a raw media type is requested
// (docs.github.com/en/rest/repos/contents, read 2026-10-03). Refuse a feed well before
// that size so a reader on the default media type never gets an empty body.
export const MAX_FEED_BYTES = 900 * 1024;

/** Wrap records in the HQ envelope, then refuse it unless it passes HQ's contract, the public-safety scan, and the size limit. */
export function buildEnvelope(records, { generatedAt, maxBytes = MAX_FEED_BYTES }) {
  const at = isoSeconds(generatedAt);
  const envelope = { schema: WORKFORCE_FEED_SCHEMA, source: 'canonical', generatedAt: at, verifiedAt: at, records };
  const problems = [];
  for (const issue of contractIssues(envelope)) problems.push(`HQ contract: ${issue}`);
  for (const f of scanForLeaks(envelope)) problems.push(`public-safety: ${f.rule} at ${f.at} (${f.excerpt})`);
  const bytes = Buffer.byteLength(serialize(envelope));
  if (bytes > maxBytes) problems.push(`size: the feed is ${bytes} bytes, over the ${maxBytes}-byte limit HQ's single read can serve; split the feed first`);
  if (problems.length) throw new FeedSourceError(problems);
  return envelope;
}

/** True when two envelopes carry identical records (timestamps are not compared). */
export function sameRecords(a, b) {
  return JSON.stringify(a?.records ?? null) === JSON.stringify(b?.records ?? null);
}

export function serialize(envelope) {
  return `${JSON.stringify(envelope, null, 2)}\n`;
}
