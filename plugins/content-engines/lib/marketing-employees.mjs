import { pathToFileURL } from 'node:url';

const brands = new Set(['expert-partners', 'ag-luxury']);
const originals = {
  'meta-ads-analyst': 'GAP-W2-STD-12',
  'meta-ad-spy': 'GAP-W2-STD-13',
  'ig-gold-miner': 'GAP-W2-STD-14',
};
const origins = new Set(['meta-insights', 'authorized-export', 'authorized-report', 'meta-ad-library', 'instagram-post']);
const analystOrigins = new Set(['meta-insights', 'authorized-export', 'authorized-report']);
const metrics = ['spend', 'impressions', 'linkClicks', 'conversions', 'revenue'];
const reportedMetrics = [...metrics, 'ctr', 'cpc', 'cpa', 'cpm', 'roas', 'frequency', 'landingPageConversionRate'];

function check(predicate, field) {
  if (!predicate) throw new TypeError(`Invalid marketing employee input: ${field}`);
}
const obj = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const str = (x, max = 4000) => typeof x === 'string' && x.trim().length > 0 && x.length <= max;
const iso = x => typeof x === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x)
  && Number.isFinite(Date.parse(x)) && new Date(x).toISOString().slice(0, 10) === x;
const number = x => typeof x === 'number' && Number.isFinite(x) && x >= 0;
function urlOf(x) {
  try {
    const u = new URL(x);
    if (u.protocol === 'https:' && !u.username && !u.password && !u.port
      && !/[?&](?:access_token|token|password|signature|key)=/i.test(u.search)) return u;
  } catch { /* rejected */ }
}
function metaID(url) {
  const u = urlOf(url);
  if (u && ['www.facebook.com', 'facebook.com'].includes(u.hostname)
    && /^\/ads\/library\/?$/.test(u.pathname) && /^\d{5,25}$/.test(u.searchParams.get('id') ?? '')) {
    return u.searchParams.get('id');
  }
}
function instagramCode(url) {
  const u = urlOf(url);
  if (u && ['www.instagram.com', 'instagram.com'].includes(u.hostname)) {
    return u.pathname.match(/^\/(?:reel|p|tv)\/([A-Za-z0-9_-]{5,30})\/?$/)?.[1];
  }
}
function envelope(request) {
  check(obj(request) && request.schemaVersion === 1, 'schemaVersion');
  const { employee, brand, asOf, input } = request;
  check(Object.hasOwn(originals, employee), 'employee');
  check(brands.has(brand), 'brand');
  check(iso(asOf), 'asOf');
  check(obj(input), 'input');
}
function array(value, field, max = 5000) {
  const result = value === undefined ? [] : value;
  check(Array.isArray(result) && result.length <= max, field);
  return result;
}
function validateEvidence(value, asOf) {
  const map = new Map();
  for (const item of array(value, 'evidence', 2000)) {
    check(obj(item) && str(item.id, 160) && !map.has(item.id)
      && str(item.url, 2048) && urlOf(item.url) && iso(item.observedOn)
      && item.observedOn <= asOf && origins.has(item.origin) && str(item.excerpt), 'evidence item');
    if (item.origin === 'meta-ad-library') check(metaID(item.url), 'Meta Library ad URL');
    if (item.origin === 'instagram-post') check(instagramCode(item.url), 'Instagram post URL');
    const { id, url, observedOn, origin, excerpt } = item;
    map.set(id, { id, url, observedOn, origin, excerpt });
  }
  return map;
}
function ref(map, id, allowed) {
  const evidence = map.get(id);
  check(evidence && allowed.has(evidence.origin), 'evidence reference or origin');
  return evidence;
}
const division = (n, d, scale = 1) => n === null || d === null || d === 0
  ? null : Number.isFinite(n / d * scale) ? n / d * scale : null;
const unique = a => [...new Set(a)];
function finding(kind, text, evidenceIds) { return { kind, text, evidenceIds: unique(evidenceIds) }; }
function analyst({ input }, evidence, out) {
  const { period, currency, conversionEvent } = input;
  const rows = array(input.rows, 'rows');
  const reported = array(input.reported, 'reported', 20);
  check(!rows.length || (obj(period) && iso(period.start) && iso(period.end)
    && period.start <= period.end && period.end <= out.asOf), 'period');
  check(!rows.length || (typeof currency === 'string' && /^[A-Z]{3}$/.test(currency)
    && str(conversionEvent, 120)), 'currency and conversion event');
  out.period = rows.length ? { start: period.start, end: period.end } : null;
  out.currency = rows.length ? currency : null;
  out.conversionEvent = rows.length ? conversionEvent : null;
  out.reported = [];
  const rowIDs = new Set();
  const totals = Object.fromEntries(metrics.map(k => [k, rows.length ? 0 : null]));
  for (const row of rows) {
    check(obj(row) && str(row.id, 200) && !rowIDs.has(row.id), 'unique row id');
    rowIDs.add(row.id);
    ref(evidence, row.evidenceId, analystOrigins);
    for (const key of metrics) {
      const value = row[key] ?? null;
      check(value === null || number(value), `row ${key}`);
      const total = totals[key];
      if (total === null || value === null) totals[key] = null;
      else {
        check(Number.isFinite(total + value), `total ${key}`);
        totals[key] = total + value;
      }
    }
  }
  const { spend, impressions, linkClicks, conversions, revenue } = totals;
  out.metrics = {
    ...totals, ctr: division(linkClicks, impressions), cpc: division(spend, linkClicks),
    cpa: division(spend, conversions), cpm: division(spend, impressions, 1000),
    roas: division(revenue, spend),
  };
  const ids = unique(rows.map(row => row.evidenceId));
  for (const item of reported) {
    check(obj(item) && reportedMetrics.includes(item.metric) && number(item.value)
      && str(item.context, 400), 'reported metric and context');
    ref(evidence, item.evidenceId, analystOrigins);
    out.reported.push({
      metric: item.metric, value: item.value, context: item.context, evidenceId: item.evidenceId,
    });
    out.findings.push(finding('observed', `Source reports ${item.metric} = ${item.value} (${item.context}).`, [item.evidenceId]));
    ids.push(item.evidenceId);
  }
  if (rows.length && Object.values(totals).some(x => x !== null)) {
    out.findings.push(finding('derived', `Recalculated available metrics from ${rows.length} supplied, non-overlapping row(s) in one reporting period.`, rows.map(row => row.evidenceId)));
    out.findings.push(finding('hypothesis', 'Compare the same conversion definition, attribution, time zone and spend across a matched prior period before changing budget or diagnosing creative fatigue.', rows.map(row => row.evidenceId)));
    out.status = 'partial';
    for (const [key, value] of Object.entries(out.metrics)) {
      if (value === null) out.limitations.push(`${key} is unavailable from complete inputs or has a zero denominator.`);
    }
    out.limitations.push('One period does not establish change, causality, comparable CPA, or warranted budget changes.');
  } else if (reported.length) {
    out.status = 'partial';
    out.limitations.push('Reported figures only. Raw denominators, exact aligned period and attribution were not supplied; do not back-solve or treat pipeline as realized revenue.');
    out.findings.push(finding('hypothesis', 'Reconcile the reported conversion event with a dated account export before comparing results or making budget decisions.', ids));
  } else {
    out.limitations.push('No analyzable account aggregates or clearly sourced reported figures. Use authorized Ads Insights, a non-overlapping export, or a dated read-only report.');
  }
}
const angleRules = [
  ['growth-systems', /\b(?:predictab|scale|recruit|brokerage|business system|lead generation|grow)\w*/i],
  ['seller-education', /\b(?:seller|selling your|listing strategy|home value|price your)\b/i],
  ['property-tour', /\b(?:sq\.?\s*ft|floor plan|roof(?:top)?|bedrooms?|luxury home|new construction|property tour)\b/i],
  ['location-fit', /\b(?:neighbou?rhood|walkable|relocat|commute|school district|downtown)\w*/i],
  ['buyer-decisions', /\b(?:home buy|buyer|mortgage|closing cost|interest rate|negotiat)\w*/i],
  ['sales-objections', /\b(?:objection|sales script|prospect|sales conversation|closing deals)\w*/i],
  ['agent-marketing', /\b(?:content|youtube|brand|social media|value proposition)\b/i],
];
function labels(text, fallback) {
  const matches = angleRules.filter(([, re]) => re.test(text)).map(([label]) => label);
  return matches.length ? matches.slice(0, 3) : [fallback];
}
function research({ input, employee, brand }, evidence, out) {
  const spy = employee === 'meta-ad-spy';
  const field = spy ? 'ads' : 'posts';
  const origin = new Set([spy ? 'meta-ad-library' : 'instagram-post']);
  const distinct = new Set();
  const buckets = new Map();
  const audienceNeed = input.audienceNeed
    ?? (brand === 'expert-partners' ? 'Help real estate professionals make a practical business decision.'
      : 'Help a North Dallas buyer or seller make a clearer property decision.');
  check(str(audienceNeed, 400), 'audienceNeed');
  out[field] = [];
  for (const item of array(input[field], field, 30)) {
    const who = spy ? 'advertiser' : 'creator';
    const tag = spy ? 'angle' : 'topic';
    check(obj(item) && str(item[who], 200) && str(item.hook, 600) && str(item.format, 80)
      && (item[tag] === undefined || str(item[tag], 100))
      && (item.cta === undefined || str(item.cta, 100))
      && (item.publishedOn === undefined || (iso(item.publishedOn) && item.publishedOn <= out.asOf)), field);
    const record = ref(evidence, item.evidenceId, origin);
    const id = spy ? metaID(record.url) : instagramCode(record.url);
    if (distinct.has(id)) continue;
    distinct.add(id);
    // A source name or URL alone is not content. The classified hook must be a literal source excerpt.
    check(record.excerpt.includes(item.hook), `${field} hook must appear in the source excerpt`);
    const tags = item[tag] ? [item[tag].trim().toLowerCase()] : labels(record.excerpt, 'uncategorized');
    const format = item.format.trim().toLowerCase();
    const profile = item[who].trim();
    out[field].push({
      evidenceId: record.id, [who]: profile, format, hook: item.hook, [tag]: tags[0],
      ...(item.cta ? { cta: item.cta } : {}), ...(item.publishedOn ? { publishedOn: item.publishedOn } : {}),
    });
    out.findings.push(finding('observed', `${profile} used this opening: ${item.hook}`, [record.id]));
    for (const label of tags) {
      if (label === 'uncategorized') continue;
      const key = JSON.stringify(spy ? [label] : [format, label]);
      const group = buckets.get(key) ?? { label, format, ids: [], people: new Set() };
      group.ids.push(record.id);
      group.people.add(profile.toLowerCase());
      buckets.set(key, group);
    }
  }
  const groups = [...buckets.values()].sort((a, b) => b.people.size - a.people.size || b.ids.length - a.ids.length);
  if (spy) {
    out.adPatterns = groups.map(g => ({ angle: g.label, count: g.ids.length, evidenceIds: g.ids }));
    out.limitations.push('Public creative coverage only. Presence, activity, age and repetition do not establish spend, CTR, conversions or profitability.');
  } else {
    out.opportunities = groups.map(g => ({
      format: g.format, topic: g.label, creatorCount: g.people.size, evidenceIds: g.ids, audienceNeed,
    }));
    out.limitations.push('A bounded post sample is not a current trend or a performance comparison. Adapt the format, not the creator’s wording or claims.');
  }
  const strongest = groups.find(g => g.people.size >= 2);
  if (strongest) {
    out.findings.push(finding('derived', `Observed ${strongest.label} across ${strongest.people.size} distinct ${spy ? 'advertisers' : 'creators'} in this sample.`, strongest.ids));
    out.findings.push(finding('hypothesis', spy
      ? `Test an original ${strongest.label} approach for this audience need: ${audienceNeed}`
      : `Try a ${strongest.format} about ${strongest.label} that addresses this audience need: ${audienceNeed}`, strongest.ids));
  }
  out.status = distinct.size ? (strongest ? 'ok' : 'partial') : 'needs-evidence';
  if (!distinct.size) out.limitations.push('No usable source content was observed. A URL or search snippet alone is not a verified creative or post.');
  else if (!strongest) out.limitations.push('No angle or format/topic pair was corroborated by distinct sources. Treat these as individual examples.');
}

export function runMarketingEmployee(request) {
  envelope(request);
  const { employee, brand, asOf, input } = request;
  const evidence = validateEvidence(input.evidence, asOf);
  const out = {
    schemaVersion: 1, employee, brand, asOf, status: 'needs-evidence',
    provenance: { implementation: 'original-substitute', calOriginal: 'open', gap: originals[employee] },
    evidence: [], findings: [], limitations: [],
  };
  if (employee === 'meta-ads-analyst') analyst(request, evidence, out);
  else research(request, evidence, out);
  const used = new Set(out.findings.flatMap(item => item.evidenceIds));
  out.evidence = [...evidence.values()].filter(item => used.has(item.id));
  return out;
}

function clean(line) {
  return line.replace(/!\[[^\]]*\]\([^)]*\)/g, '').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/\\+/g, '').replace(/\*\*/g, '').replace(/\u200b/g, '').trim();
}
function parseAdLibrary(markdown, asOf, pinnedId) {
  const results = [];
  for (const chunk of markdown.split(/(?=Library ID: \d+)/)) {
    const id = chunk.match(/^Library ID: (\d{5,25})\b/)?.[1];
    if (!id || (pinnedId && id !== pinnedId)) continue;
    const split = chunk.match(/^(.+?)\r?\n\r?\n\*\*Sponsored\*\*(?:\s*\u200b)?\s*\r?\n([\s\S]*)/m);
    if (!split) continue;
    const advertiser = clean(split[1]);
    const excerpt = split[2].split(/\r?\n/).slice(0, 18).map(clean)
      .filter(line => line && line !== '* * *' && !/^(?:Open Dropdown|See ad details)$/i.test(line))
      .join('\n').trim().slice(0, 1600);
    const hook = excerpt.split('\n')[0]?.slice(0, 320);
    if (!str(advertiser, 200) || !str(hook) || excerpt.length < 25) continue;
    const evidenceId = `meta-${id}`;
    const format = /\b(?:Play Video|Mute|Unmute)\b|\[[\d:]+\]/i.test(split[2]) ? 'video' : 'not verified';
    results.push({
      evidence: { id: evidenceId, url: `https://www.facebook.com/ads/library/?id=${id}`, observedOn: asOf, origin: 'meta-ad-library', excerpt },
      item: { evidenceId, advertiser, hook, format },
    });
  }
  return results;
}
function parseInstagram(markdown, candidate, asOf) {
  const code = instagramCode(candidate);
  const title = markdown.match(/^# (Reel|Post|Video) by [^\n]*\(@([a-z0-9._]+)\)[^\n]*\r?\n/im);
  if (!code || !title) return [];
  const body = markdown.slice(title.index + title[0].length).split(/\r?\n/).map(clean);
  const dateLine = body.findIndex(l => /^\d{4}-\d{2}-\d{2}(?:\s*·|$)/.test(l));
  const publishedOn = dateLine >= 0 ? body[dateLine].slice(0, 10) : undefined;
  if (publishedOn && (!iso(publishedOn) || publishedOn > asOf)) return [];
  const excerpt = body.slice(0, dateLine < 0 ? 14 : dateLine).filter(Boolean).join('\n').slice(0, 1300);
  const hook = excerpt.split('\n')[0]?.slice(0, 320);
  if (!str(hook) || excerpt.length < 25 || /(?:log in to|page isn.t available|cookie consent)/i.test(hook)) return [];
  const evidenceId = `ig-${code}`;
  const format = title[1].toLowerCase() === 'reel' || new URL(candidate).pathname.startsWith('/reel/') ? 'reel' : 'post';
  return [{
    evidence: { id: evidenceId, url: `https://www.instagram.com/${format === 'reel' ? 'reel' : 'p'}/${code}/`, observedOn: asOf, origin: 'instagram-post', excerpt },
    item: { evidenceId, creator: `@${title[2]}`, hook, format, ...(publishedOn ? { publishedOn } : {}) },
  }];
}

// Transports are supplied by the authorized caller. The runtime requests only fixed Meta and
// Instagram origins. A transport must refuse redirects outside its public allowlist.
export async function acquireMarketingEvidence(request, { fetchPage, search } = {}) {
  envelope(request);
  if (request.employee === 'meta-ads-analyst') return runMarketingEmployee(request);
  check(typeof fetchPage === 'function', 'fetchPage transport');
  const { employee, brand, asOf, input } = request;
  const spy = employee === 'meta-ad-spy';
  const supplied = array(input.urls, 'urls', 12);
  check(input.query === undefined || str(input.query, 240), 'query');
  const defaultQuery = brand === 'expert-partners' ? 'real estate coaching' : 'North Dallas real estate';
  const query = input.query ?? defaultQuery;
  const canonical = link => {
    if (spy) {
      const id = metaID(link);
      return id && `https://www.facebook.com/ads/library/?id=${id}`;
    }
    const code = instagramCode(link);
    if (!code) return undefined;
    const format = urlOf(link).pathname.startsWith('/reel/') ? 'reel' : 'p';
    return `https://www.instagram.com/${format}/${code}/`;
  };
  check(supplied.every(url => str(url, 2048) && canonical(url)), 'public platform URLs');
  let candidates = supplied.map(canonical);
  const acquisitionLimits = [];
  if (!candidates.length && spy) {
    const params = new URLSearchParams({ active_status: 'active', ad_type: 'all', country: 'US', q: query });
    candidates = [`https://www.facebook.com/ads/library/?${params}`];
  } else if (!candidates.length && typeof search === 'function') {
    try {
      const links = await search(`site:instagram.com/reel ${query}`);
      candidates = unique(array(links, 'search results', 100).map(canonical).filter(Boolean)).slice(0, 8);
    } catch {
      acquisitionLimits.push('The authorized Instagram discovery route failed.');
    }
  }
  if (!candidates.length && !acquisitionLimits.length) acquisitionLimits.push('No Instagram post links discovered; use an approved discovery transport or direct public post links.');
  const collected = await Promise.all(candidates.map(async (url) => {
    try {
      const page = await fetchPage(url);
      const markdown = typeof page === 'string' ? page : page?.markdown;
      const status = page?.metadata?.statusCode;
      if (typeof markdown !== 'string' || (status && status >= 400)) return [];
      return spy ? parseAdLibrary(markdown, asOf, metaID(url)) : parseInstagram(markdown, url, asOf);
    } catch {
      return [];
    }
  }));
  const misses = collected.filter(items => !items.length).length;
  if (misses) acquisitionLimits.push(`${misses} source request(s) returned no usable creative/post text.`);
  const seen = new Set();
  const records = collected.flat().filter(({ evidence: item }) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  }).slice(0, 12);
  const output = runMarketingEmployee({
    ...request, input: {
      audienceNeed: input.audienceNeed, evidence: records.map(record => record.evidence),
      [spy ? 'ads' : 'posts']: records.map(record => record.item),
    },
  });
  output.acquisition = { requested: candidates.length, read: candidates.length - misses, accepted: records.length };
  output.limitations.push(...acquisitionLimits);
  if (misses && output.status === 'ok') output.status = 'partial';
  return output;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    let json = '';
    for await (const chunk of process.stdin) {
      json += chunk;
      if (json.length > 2_000_000) throw new TypeError('Input too large');
    }
    const request = JSON.parse(json);
    // stdin capture adapters let a connected harness feed actual pages through the same
    // acquisition path without adding network credentials to the plugin.
    const result = request.pages ? await acquireMarketingEvidence(request, {
      fetchPage: url => request.pages[url],
      search: () => request.discoveredUrls ?? [],
    }) : runMarketingEmployee(request);
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${error instanceof SyntaxError ? 'Invalid JSON input' : error.message}\n`);
    process.exitCode = 1;
  }
}
