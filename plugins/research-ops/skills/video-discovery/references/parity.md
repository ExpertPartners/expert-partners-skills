---
classification: public
---

# Capability parity

Every original inventory row has a carried route or an explicit limitation. The build checks coverage, routes and named tests. A mapping is not a claim that every source was live-tested; consult the original inventory and the test scope. Review-only steps stay review-only.

| Original capability / added capability | Carried route | Regression test |
|---|---|---|
| Ordinary public HTTP | `PublicHTTP.fetch` | `test_transient_retry_exactly_once` |
| Robots checks | `PublicHTTP.allowed` | `test_robots_wildcards_stop_query` |
| Sitemaps | `Investigation.crawl` | `test_empty_public_site_produces_empty_catalog` |
| Bounded creator-site crawl | `Investigation.crawl` | `test_shared_domain_budget` |
| Page and embed extraction | `extract_references` | `test_relative_media_and_no_numeric_guessing` |
| Inline JavaScript and structured source | `decode_text` | `test_escaped_inline_javascript` |
| External JavaScript | `Investigation.crawl` | `test_serialized_marketing_fixture` |
| Platform/direct URL recognition | `identify_url` | `test_youtube_forms` |
| Search indexes | `Investigation.import_search` | `test_exact_id_evidence_rejects_unrelated_search_results` |
| Exact-ID corroboration | `review_catalog.matching_hits` | `test_exact_id_evidence_rejects_unrelated_search_results` |
| Vimeo supported oEmbed | `Investigation.validate` | `test_partial_oembed_not_playback` |
| Deprecated Vimeo Simple API | `Investigation.vimeo_legacy` | `test_name_is_not_identity` |
| Identity matching | `apply_metadata` | `test_name_is_not_identity` |
| Wayback CDX and snapshots | `Investigation.archives` | `test_full_cdx_paginates_platform_paths_and_accounts_all_rows` |
| Conflicting source review | `review_catalog.review` | `test_third_party_credit_is_not_platform_verification` |
| Common Crawl collection discovery | `Investigation.archives` | `test_robots_wildcards_stop_query` |
| Direct-media HEAD | `Investigation.validate` | `test_uncertain_classification` |
| Prefix range sampling | `probe_media.sample` | `test_range_ignored_never_reads_body` |
| Seekable bounded decoding | `verify_candidates.verify_one` | `test_seeks_and_cache` |
| Still inspection | `verify_candidates.verify_one` | `test_sample_does_not_claim_full_duration_playback` |
| Fresh publication check | `Investigation.scan` | `test_review_preserves_sources_seeds_and_keys` |
| Content-addressed evidence | `PublicHTTP.record` | `test_resume_preserves_budget_cache_and_block` |
| Resume/offline replay | `PublicHTTP.restore` | `test_offline_replay_cannot_make_requests` |
| Deduplication and exports | `Investigation.export` | `test_dedupe_keeps_provenance_and_seed_and_hash` |
| Baseline preservation | `review_catalog.review` | `test_review_preserves_sources_seeds_and_keys` |
| Automated and independent checks | `tests/` | `test_empty_public_site_produces_empty_catalog` |
| Workspace/repository inspection | `README.md` | `test_existing_and_nested_outputs_refused` |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | `Investigation.ytdlp` | `test_media_body_never_read` |
| [baba20o/filmot-cli](https://github.com/baba20o/filmot-cli) | `references/methods-used.md` | `test_robots_wildcards_stop_query` |
| Filmot web search | `Investigation.platform_discovery` | `test_403_circuit_breaker_covers_subdomains` |
| YouTube channel, playlists, feeds, oEmbed, player | `Investigation.platform_discovery` | `test_proxy_403_not_retried` |
| Vimeo general website scraping | `PublicHTTP.allowed` | `test_uncertain_classification` |
| Official authenticated platform APIs | `references/methods-used.md` | `test_no_implicit_netrc_credentials` |
| Connected YouTube metadata provider | `discovery_extensions.import_youtube_details` | `test_import_metadata_preserves_block_and_does_not_claim_playback` |
| Browser/Playwright rendering | `Investigation.render` | `test_media_body_never_read` |
| Wistia/Loom recognition | `identify_url` | `test_reject_false_ids` |
| Full video/audio verification | `verify_candidates.BoundedRangeReader` | `test_refuse_full_file_response_without_read` |
| Private/unlisted enumeration | `README.md` | `test_uncertain_classification` |
| Caption-only transcript reads | `discovery_extensions.read_captions` | `test_captions_text_only_and_no_playback_promotion` |
| Full bounded per-path CDX inventory | `discovery_extensions.full_archives` | `test_full_cdx_paginates_platform_paths_and_accounts_all_rows` |
| Saved Firecrawl YouTube details import | `discovery_extensions.import_youtube_details` | `test_import_metadata_preserves_block_and_does_not_claim_playback` |

The three additions have offline regression coverage. Caption reading remains stopped on a previously blocked platform. Imported provider playability OK is not observed playback. Full CDX mode enumerates returned rows and reports whether pagination was exhausted, subject to the existing shared 100-request domain cap.

Archivarix and PublicWWW remain untested research routes. Vimeo API Playground was reported used by a separate research worker, not exercised by this CLI. No authenticated API integration or browser access is silently added.
