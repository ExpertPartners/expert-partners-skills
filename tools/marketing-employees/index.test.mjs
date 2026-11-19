import test from 'node:test';
import assert from 'node:assert/strict';
import { acquireMarketingEvidence, runMarketingEmployee } from './index.mjs';

const asOf = '2026-11-19';
const envelope = (employee, input, brand = 'expert-partners') => ({ schemaVersion: 1, employee, brand, asOf, input });
const record = (id, url, origin, excerpt) => ({ id, url, origin, excerpt, observedOn: asOf });
const exportEvidence = record('proof', 'https://example.com/metadata', 'authorized-export', 'Synthetic export');
const reportEvidence = { ...exportEvidence, origin: 'authorized-report' };
const row = { id: 'a', evidenceId: 'proof', spend: 100, impressions: 1000, linkClicks: 50, conversions: 5 };
const performance = { evidence: [exportEvidence], period: { start: '2026-10-01', end: '2026-10-31' }, currency: 'USD', conversionEvent: 'Registration' };
const adUrl = id => `https://www.facebook.com/ads/library/?id=${id}`;
const igUrl = code => `https://www.instagram.com/reel/${code}/`;

test('analyst recalculates KPIs without treatment of unavailable revenue as zero', () => {
  const result = runMarketingEmployee(envelope('meta-ads-analyst', { ...performance, rows: [row] }));
  const { ctr, cpc, cpa, cpm, revenue, roas } = result.metrics;
  assert.deepEqual({ ctr, cpc, cpa, cpm, revenue, roas }, { ctr: .05, cpc: 2, cpa: 20, cpm: 100, revenue: null, roas: null });
  assert.equal(result.status, 'partial');
  assert.equal(result.provenance.calOriginal, 'open');
});
test('analyst withholds incomplete totals and rejects duplicate rows and cross-origin data', () => {
  const partial = runMarketingEmployee(envelope('meta-ads-analyst', { ...performance, rows: [row, { ...row, id: 'b', spend: null, linkClicks: null }] }));
  assert.equal(partial.metrics.spend, null);
  assert.equal(partial.metrics.ctr, null);
  assert.equal(partial.metrics.impressions, 2000);
  assert.throws(() => runMarketingEmployee(envelope('meta-ads-analyst', { ...performance, rows: [row, row] })), /unique row/);
  assert.throws(() => runMarketingEmployee(envelope('meta-ads-analyst', { ...performance, rows: [row], evidence: [{ ...exportEvidence, origin: 'meta-ad-library', url: adUrl('123456') }] })), /origin/);
});
test('empty and source-reported analysis do not invent periods, denominators or ROAS', () => {
  assert.equal(runMarketingEmployee(envelope('meta-ads-analyst', {})).status, 'needs-evidence');
  const result = runMarketingEmployee(envelope('meta-ads-analyst', { evidence: [reportEvidence], reported: [
    { metric: 'cpa', value: 20, context: 'Reported only', evidenceId: 'proof' },
  ] }));
  assert.equal(result.status, 'partial');
  assert.equal(result.reported[0].value, 20);
  assert.equal(result.metrics.cpa, null);
  assert.equal(result.period, null);
});
test('spy acquires individual ads from a search page, extracts angles and deduplicates IDs', async () => {
  const chunk = (id, name, hook) => `Library ID: ${id}\n\nSee ad details\n\n[${name}](https://www.facebook.com/brand)\n\n**Sponsored**\n\n${hook}\n\nLearn more`;
  const content = [chunk('135790', 'Alpha', 'Build a real estate growth system that scales.'), chunk('246810', 'Beta', 'Scale your brokerage with a growth system.'), chunk('135790', 'Alpha', 'Duplicate text about growth.')].join('\n\n');
  const req = envelope('meta-ad-spy', { query: 'real estate coaching' });
  const result = await acquireMarketingEvidence(req, { fetchPage: url => {
    assert.equal(new URL(url).searchParams.get('q'), 'real estate coaching');
    return { markdown: content };
  } });
  assert.equal(result.status, 'ok');
  assert.deepEqual(result.adPatterns[0], { angle: 'growth-systems', count: 2, evidenceIds: ['meta-135790', 'meta-246810'] });
  assert.equal(result.ads[0].format, 'not verified');
  assert.equal(result.evidence[0].url, adUrl('135790'));
  assert.equal(Object.hasOwn(result, 'metrics'), false);
});
test('IG discovery fetches only direct posts, routes an audience need and rejects URL-only evidence', async () => {
  const req = envelope('ig-gold-miner', { query: 'Dallas property tours', audienceNeed: 'Compare how floor plans live.' }, 'ag-luxury');
  const urls = ['HOUSE11', 'HOUSE22'].map(igUrl);
  const result = await acquireMarketingEvidence(req, {
    search: query => {
      assert.match(query, /^site:instagram\.com\/reel /);
      return ['https://example.com/evil', ...urls, urls[0]];
    },
    fetchPage: url => `# Reel by Test (@${url === urls[0] ? 'alpha' : 'beta'})\n\nProperty tour: look at the floor plan before you decide.\n\n2026-11-01 · 100 plays`,
  });
  assert.deepEqual(result.acquisition, { requested: 2, read: 2, accepted: 2 });
  assert.deepEqual(result.opportunities[0], { format: 'reel', topic: 'property-tour', creatorCount: 2,
    evidenceIds: ['ig-HOUSE11', 'ig-HOUSE22'], audienceNeed: 'Compare how floor plans live.' });
  assert.equal(result.posts[0].publishedOn, '2026-11-01');
  const blocked = await acquireMarketingEvidence(req, { search: () => urls, fetchPage: () => 'Log in or sign up' });
  assert.equal(blocked.status, 'needs-evidence');
  assert.deepEqual(blocked.evidence, []);
  await assert.rejects(acquireMarketingEvidence(envelope('ig-gold-miner', { urls: ['https://instagram.com.example.com/reel/ABCDE'] }), { fetchPage: () => '' }), /platform URL/);
});
test('a hook not present in the source cannot be returned as observed', () => {
  assert.throws(() => runMarketingEmployee(envelope('meta-ad-spy', {
    evidence: [record('ad', adUrl('123456'), 'meta-ad-library', 'Observed creative only.')],
    ads: [{ evidenceId: 'ad', advertiser: 'Alpha', hook: 'Made up', format: 'unknown' }],
  })), /hook must appear/);
});
