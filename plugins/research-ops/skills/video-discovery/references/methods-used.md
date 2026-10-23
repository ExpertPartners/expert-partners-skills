---
classification: public
date: 2026-10-23
source: Original local implementation, request audit and verification exercise
topic: Video discovery method inventory
---

# Methods actually used

This is an implementation and execution inventory, not a new discovery run or a
publication of the original creator's catalog. Research records, source captures,
exact candidate IDs and decoded stills remain in the original local workspace.
Rows describe the original exercise and subsequent fixed-candidate verification.
A capability implemented in code is not evidence of a successful live check.

## Completed retrieval and analysis

| Method | What actually happened | What it establishes |
| --- | --- | --- |
| Ordinary public HTTP | Retrieved public HTML, XML, JSON and JavaScript with requests, without account credentials or retained cookies. | Source evidence at retrieval time. |
| Robots checks | Parsed wildcard rules with Protego; carried blocking state across related subdomains and later runs. | Which retrievals were permitted or stopped. |
| Sitemaps | Parsed XML URL sets and indexes using defusedxml. | Publicly referenced page URLs. |
| Bounded creator-site crawl | Followed relevant first-party links and supplied marketing subdomain pages within shared domain budgets. | A bounded, incomplete site footprint. |
| Page and embed extraction | BeautifulSoup parsed links, iframe/video/source attributes, labels and page titles. | References and context, not video ownership. |
| Inline JavaScript and structured source | Decoded escaped slash/Unicode strings and extracted URLs in inline scripts, JSON-LD and serialized source. | Video references without executing site code. |
| External JavaScript | Retrieved linked first-party script source via ordinary HTTP. | Referenced URLs; scripts were not executed. |
| Platform/direct URL recognition | Extracted YouTube URL variants, Vimeo URLs/player IDs and existing privacy hashes, and direct media URLs. | Candidates keyed by platform ID or normalized direct URL hash. |
| Search indexes | Used an already-connected Firecrawl search tool, saved its results and imported them into the CLI. Later queries used only existing exact video IDs. | Indexed references, with source URLs; snippets alone do not prove uploader or playback. |
| Exact-ID corroboration | Rejected search hits pointing to different video IDs; compared remaining hits with existing publisher credits and source labels. | Public credit attribution with uncertainty retained. |
| Vimeo supported oEmbed | Requested public oEmbed metadata successfully. | Titles and exact author profile metadata; no playback proof. |
| Deprecated Vimeo Simple API | Tested the optional public profile video-list endpoint successfully. | Additional public metadata and exact profile matches; not a required dependency. |
| Identity matching | Compared public author/profile/channel identifiers with supplied creator identities. | Creator attribution only when exact identifiers match; display names are insufficient. |
| Wayback CDX and snapshots | Queried the public CDX index and inspected a bounded sample of 15 archived HTML pages. | Historical references and publisher labels, not current video availability. |
| Conflicting source review | Preserved contradictory archived labels for a shared ID and recorded index corroboration separately. | A reasoned public credit, without claiming current platform identity verification. |
| Common Crawl collection discovery | Retrieved the collection list. Index query retrieval stopped at robots restrictions. | Collection availability only; no corpus search result or WARC retrieval. |
| Direct-media HEAD | Checked media content type, advertised size and range support. | Accessible endpoint, not decoded playback. |
| Prefix range sampling | Read at most 512 KiB per file under HTTP 206 and attempted offline ffmpeg first-frame decoding. MP4 metadata at the tail made the original attempt fail. | Partial transport evidence; the failed decode was not counted as playback. |
| Seekable bounded decoding | PyAV decoded two seconds / 61 distinct noncorrupt H.264 frames per tested direct asset using strict HTTP byte ranges. Limits were 2 MiB new bytes and eight requests per file, with prior prefix plus new bytes at most a quarter of the original file. | A genuinely viewable short moving-video sample, not full duration, audio or browser playback. |
| Still inspection | Saved first/last decoded PNGs and visually inspected two stills using the available image viewer. | Human-readable sample content evidence; not ownership or full playback. |
| Fresh publication check | Re-fetched an already-known marketing page and matched exact media URLs to video labels and testimonial text. | Creator-site publication, explicitly separate from original ownership. |
| Content-addressed evidence | Saved response text under SHA-256 names and recorded timestamps, methods, status, request counts and stops in append-only audit logs. | Reproducible provenance and failure records. |
| Resume/offline replay | Restored budgets, blocked domains and cached responses; corrected parser issues and re-extracted cached evidence with networking disabled. | Repeatable local extraction without a new crawl. |
| Deduplication and exports | Merged platform-ID/normalized-URL records while retaining seeds, sources, privacy hashes and checks; exported JSON, CSV and Markdown with CSV formula protection. | Searchable catalogs with provenance, not audiovisual fingerprint deduplication. |
| Baseline preservation | Snapshotted original outputs before reviewing the fixed candidate set; retained all seven original seed rows unchanged. | Separation of initial findings from subsequent verification. |
| Automated and independent checks | Ran the original 81 tests and separate integrity assertions covering source hashes, unchanged candidates/seeds, log-prefix preservation and byte/request limits. Packaged tests replace real identities and source captures with synthetic fixtures and add reusable-review regressions. | Tested extraction, normalization, deduplication, uncertainty and boundary behavior; not proof every optional live source works. |
| Workspace/repository inspection | Read local Git status/remotes and file locations. | Original delivery lived outside Development; the reusable skill is now proposed through a separate draft PR in the existing skills repository. |

## Evaluated, blocked, or unexercised

| Source/capability | Actual disposition |
| --- | --- |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Evaluated upstream documentation, installed it and implemented a guarded metadata-only adapter. No successful live platform extraction was performed. Format advertisement would still not establish playback. |
| [baba20o/filmot-cli](https://github.com/baba20o/filmot-cli) | Evaluated upstream documentation. API access required credentials that were not provisioned. The CLI/API was not run. |
| Filmot web search | Robots restrictions prevented the search retrieval. Unrelated indexed Filmot hits were excluded. No blocked route was bypassed. |
| YouTube channel, playlists, feeds, oEmbed, player | A proxy 403 stopped direct YouTube retrievals. No channel enumeration, playlist retrieval, successful direct metadata check or legitimate player playback was completed. These paths remain blocked/unconfirmed. |
| Vimeo general website scraping | Skipped because of an explicit scraping restriction. Supported oEmbed and the optional legacy metadata endpoint were used instead. |
| Official authenticated platform APIs | Not called; no credentials or paid subscriptions were created or requested. |
| Connected YouTube metadata provider | Inspected its public tool contract; its internal player calls were not executed as an alternate path around the existing block. |
| Browser/Playwright rendering | Implemented an optional fresh-context renderer with media, third-party HTTP and WebSockets blocked. Not exercised in the live investigation because ordinary source exposed the references. No browser playback was tested. |
| Wistia/Loom recognition | URL recognition exists in the extractor; no successful live discovery or platform verification was established for either. |
| Full video/audio verification | Never downloaded complete video files, decoded full duration, tested audio, or asserted full-player playback. |
| Private/unlisted enumeration | No ID guessing, passwords, private-account access, domain-restriction bypass or exhaustive unlisted enumeration. An absent listing never became an unlisted claim. |

## Known execution limitations

Initial malformed/serialized HTML URL parsing consumed some requests before it was
fixed. Regression tests and cache-only replay preserved the original request
audit rather than concealing those attempts. Search-index results can be stale or
misleading, archive samples are incomplete, and a CDN-hosted customer testimonial
can be creator-published without proving creator ownership. None of those gaps is
converted to a positive ownership or playback classification.

Packaging adds a generic offline review command in place of the original
case-specific updater. It accepts documented public credits and already-produced
decoder evidence; it performs no new discovery. The packaged synthetic suite and
repository checks are recorded in the PR description separately from the original
live exercise. No new creator search was performed during skill packaging.
