# Public video discovery CLI

Python 3.11 or newer. Run from a separate local investigation directory; keep all
research data outside the skill checkout. No credentials are needed for the
initial prototype. Install dependencies in a virtual environment:

```bash
SKILL=/absolute/path/to/expert-partners-skills/plugins/research-ops/skills/video-discovery
python3 -m venv .venv
.venv/bin/pip install -r "$SKILL/requirements-dev.txt"
.venv/bin/python -m pytest "$SKILL/tests" -q
```

For discovery alone, use `requirements.txt`. Bounded decoding additionally needs
`requirements-verification.txt` (PyAV and Pillow). The optional historical prefix
probe needs an installed `ffmpeg`. Optional rendering needs Playwright and its
Chromium install; it was not needed in the original investigation.

## New investigation

```bash
.venv/bin/python "$SKILL/scripts/video_discovery.py" \
  --creator "Example Creator" \
  --youtube https://www.youtube.com/@examplecreator \
  --youtube-channel-id UC_EXACT_PUBLIC_CHANNEL_ID \
  --vimeo https://vimeo.com/examplecreator/videos \
  --website example.com \
  --site https://go.example.com/ \
  --output ./investigation --max-pages 100 --delay 1.5
```

Replace every example identity and domain. The channel ID must be verified public
metadata, never inferred from a display name. `--seeds seeds.json` accepts an array
of objects such as `[{"url":"https://www.youtube.com/watch?v=AbCdEf123_-"}]`.
These are synthetic example IDs, not links discovered in an investigation.

Optional flags: `--archives`, `--legacy-vimeo`, `--yt-dlp`, `--render URL`,
`--search-json search-results.json`, and `--blocked-domain DOMAIN`. Review current
provider terms before optional retrieval. YouTube pages/feeds/playlists may be
blocked; Vimeo website scraping is conservatively disabled in favor of supported
oEmbed and the optional legacy endpoint. No official authenticated API is called
without credentials and authorization; none are needed or requested here.

`--search-json` accepts a JSON array of query batches shaped as
`[{"query":"public search terms","data":{"web":[{"url":"https://example.com/episode","title":"Episode","description":"Indexed reference"}]}}]`.
The code imports saved permitted
results; it does not purchase search service or call Firecrawl itself. See the
actual importer before using a different connector response shape. Preserve the
original search response separately as evidence.

Outputs: `catalog.json` (full provenance and checks), searchable `catalog.csv`,
`summary.json`, `findings.md`, append-only `requests.jsonl`, and SHA-256-named
`evidence/*.txt`. CSV cells are protected from spreadsheet formula execution.
A fresh completed output directory is required. `--resume` is for an interrupted
run without a completed catalog and preserves budgets, cache and blocked domains.

## Verify an existing catalog without expanding discovery

First copy the complete investigation directory to a dated baseline outside it.
The decoder appends network audit records to the catalog's directory, so this
snapshot is necessary even though its candidate records are unchanged.

```bash
.venv/bin/python "$SKILL/scripts/verify_candidates.py" \
  --catalog ./investigation/catalog.json --result-dir ./verification
.venv/bin/python "$SKILL/scripts/review_catalog.py" \
  --catalog ./investigation/catalog.json \
  --samples ./verification/direct_verification.json \
  --decisions ./decisions.json --output ./reviewed-investigation
```

The decoder examines only non-seed direct media already in the catalog and skips
recorded result IDs on rerun. Use the same result directory to retain that ledger.
Do not delete prior results to retry a blocked source. It requires a successful
recorded HEAD size, strict 206 Content-Range, at most eight requests and 2 MiB of
new data per file, and no more than one quarter of the file including an earlier
prefix probe. The decoder network uses the same persisted domain budgets/blocks.
Only decoded PNG stills and audit metadata are saved, not video files. A successful
sample covers two seconds, not full duration, audio or browser playback.

The optional `--decisions` file is an array with `platform`, `video_id`,
`attribution`, `source`, `basis`, and optionally `publisher`. Allowed attributions
are `third_party_public_credit`, `creator_site_publication_verified`, `unresolved`.
Each decision needs an inspectable public source and specific reasoning. A
third-party credit also needs its publisher. This is a human/agent review input,
not an independent source of truth. It cannot assert creator ownership. Example:

```json
[
  {
    "platform": "youtube",
    "video_id": "AbCdEf123_-",
    "attribution": "third_party_public_credit",
    "publisher": "Example Interview Show",
    "source": "https://example.org/episode",
    "basis": "The supplied source credits this exact video to the interview show."
  }
]
```

The review command is offline and rejects new or duplicate IDs. It writes a fresh
copy, preserves seed records and prior evidence, and exports all four review
groups. Its `additional_creator_owned_playable` count uses exact creator metadata
plus a bounded viewable sample; publisher association alone never qualifies.
For platform videos, this prototype cannot establish playback and therefore does
not promote successful metadata to playable. In JSON, `confirmed_playable` is the
older full-playback status counter; bounded samples have a separate status and
`viewable_samples` count. Read those fields separately.

`scripts/replay_catalog.py OUTPUT` re-extracts cached evidence without network
calls; run it only on a baseline copy. It refuses catalogs with a subsequent
verification pass. `probe_media.py OUTPUT` retains the older optional 512 KiB
prefix/ffmpeg approach for reproducibility; it can fail on MP4 files whose metadata
is at the tail, so the seeking decoder is the practical verification command.

## Limitations and maintenance

This is a bounded discovery tool, not an exhaustive enumerator of unlisted videos.
No platform metadata, HTTP status, search snippet, or absent profile listing is
proof of playback or unlisted status. The direct-media deduplication key is a URL
hash, not an audiovisual fingerprint. URLs with time-limited signatures may expire;
normalization retains query values and Vimeo privacy hashes but reorders query
parameters, so byte-sensitive signed URLs can fail and must remain unresolved.

Run the tests after extraction, policy or classification changes. All packaged
fixtures are synthetic and work offline; the methods inventory records the
separate original live exercise. Review third-party endpoints and terms before a
new live run. Keep output, caches, virtual environments and captured media out of
version control. The original case-specific catalogs and reports are intentionally
not shipped in this public plugin.
