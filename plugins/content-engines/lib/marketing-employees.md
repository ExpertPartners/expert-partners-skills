# Marketing employee runtime, v1

This self-contained Node.js module ships in `content-engines/lib/marketing-employees.mjs`. For other authorized server environments, pin this exact file to a reviewed commit through the existing build, not an editable copy. In a checkout `tools/marketing-employees/index.mjs` re-exports both functions. No dependencies, credentials, network writes or service startup.

The plugin skills own acquisition decisions, brief synthesis and brand context. The runtime checks evidence and generates a repeatable first pass; it cannot prove that caller-supplied data was authorized or authentic. The caller authenticates and checks user access before sourcing private data. Never persist credentialed URLs or include private input in public fixtures or logs.

## Request

`{schemaVersion:1,employee,brand,asOf,input}`. Employee is `meta-ads-analyst`, `meta-ad-spy`, or `ig-gold-miner`. Brand is `expert-partners` or `ag-luxury`. `asOf` is an ISO calendar date.

- `evidence` entries are `{id,url,observedOn,origin,excerpt}`. IDs are unique, URLs are HTTPS, dates are ISO calendar days, and excerpts are observed text. Analyst origins are `meta-insights`, `authorized-export`, `authorized-report`. Research origins are `meta-ad-library` and `instagram-post`, respectively.
- Analyst has `period:{start,end}`, `currency`, `conversionEvent` and `rows:[{id,evidenceId,spend,impressions,linkClicks,conversions,revenue?}]`. Rows must be non-overlapping and share attribution, counting definitions, currency and time zone. Numbers are nonnegative. Missing values are null, not zero; incomplete field totals are withheld. `reported:[{metric,value,context,evidenceId}]` is optional, separate from computed values and never used as a raw denominator. With no data, use `rows:[]`.
- Spy has `ads:[{evidenceId,advertiser,hook,format,angle?,cta?}]`; IG has `posts:[{evidenceId,creator,format,topic?,hook,publishedOn?}]`. `hook` must be an exact substring of the evidence excerpt. Omit angle/topic for source-based classification. `audienceNeed` can override the broad brand audience default.

## Entry points

`runMarketingEmployee(request)` takes structured, sourced data.

`await acquireMarketingEvidence(request,{fetchPage,search})` acquires public research input. `input` accepts `query`, `urls` (individual platform URLs, not search result pages), and `audienceNeed`. Spy builds a US public Meta Library query if URLs are not supplied. IG discovers posts through `search(query) -> string[]`, or reads supplied direct URLs. `fetchPage(url) -> {markdown,metadata?:{statusCode}} | string`. Only fetch requested public platform destinations; refuse disallowed redirects and credentials. Text that is blocked, missing or snippet-only stays unverified. Analyst stays on the caller's authorized report or Insights adapter and does not acquire private data through this public transport.

In a skill harness with platform fetch/search tools rather than a callable transport, acquire actual pages with those tools. Pass captured Markdown in top-level `pages` keyed by the canonical requested URL, plus `discoveredUrls` for IG query discovery, and run the module on stdin. Spy uses a URL with parameters in this order: `active_status=active&ad_type=all&country=US&q=...`, encoded by `URLSearchParams`. Individual links use `https://www.facebook.com/ads/library/?id=...` or `https://www.instagram.com/reel/.../` / `https://www.instagram.com/p/.../`. Store evidence only in the authorized task destination. Inspect the runtime output and use the appropriate skill to synthesize the brief; the generic taxonomy is a candidate classifier, not an editorial verdict.

## Response

All responses include `{schemaVersion,employee,brand,asOf,status,provenance,evidence,findings,limitations}`. Status is `ok`, `partial`, or `needs-evidence`. Provenance states `original-substitute`, `calOriginal:open` and the gap ID. Findings are `{kind,text,evidenceIds}`, with kind `observed`, `derived` or `hypothesis`. Limitations are strings. Malformed inputs throw `TypeError`; unavailable sources are evidence limitations, not fabricated records.

Analyst returns `period`, `currency`, `conversionEvent`, `reported`, and `metrics` with spend, impressions, linkClicks, conversions, revenue, ctr, cpc, cpa, cpm and roas. Null means unavailable; CTR and other rates use fractions. The single-period result is partial because it cannot support a matched diagnosis. Spy returns `ads` and `adPatterns:[{angle,count,evidenceIds}]`. IG returns `posts` and `opportunities:[{format,topic,creatorCount,evidenceIds,audienceNeed}]`. Public acquisition adds `{requested,read,accepted}` under `acquisition`.

Synthetic test: spend 100, 1,000 impressions, 50 link clicks and 5 conversions yields CTR 0.05, CPC 2, CPA 20 and CPM 100. Two distinct scoped source creatives with one angle yield a count of 2; two post IDs from distinct creators in one format/topic yield creatorCount 2. These fixtures test arithmetic and attribution, not live access.
