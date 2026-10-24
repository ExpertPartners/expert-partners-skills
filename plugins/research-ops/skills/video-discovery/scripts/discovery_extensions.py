"""Optional text-only captions, bounded full CDX inventory and saved metadata imports."""
import hashlib
import io
import json
import re
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from video_discovery import (BINARY_EXT, MEDIA_EXT, VIDEO_ID, classify, domain,
                             identify_url, normalize_url, now)


def guarded_ydl(http, options):
    import yt_dlp
    from yt_dlp.networking import Response

    class GuardedYDL(yt_dlp.YoutubeDL):
        def urlopen(self, request):
            method = getattr(request, 'method', 'GET')
            if method not in {'GET', 'HEAD'}:
                raise ValueError('Only public GET/HEAD are permitted')
            url = request if isinstance(request, str) else request.url
            response = http.fetch(url, method=method)
            if response.result != 'ok':
                raise ValueError('Public retrieval stopped: ' + response.result)
            return Response(io.BytesIO(response.text.encode()), url=response.url,
                            headers=response.headers, status=response.status)

    return GuardedYDL(dict(options, skip_download=True, quiet=True, no_warnings=True,
                          noplaylist=True, retries=0, extractor_retries=0, cachedir=False))


def read_captions(inv, record, languages):
    """yt-dlp selects subtitle tracks; our policy client retrieves text only."""
    if record.platform != 'youtube':
        return
    if domain(record.url) in inv.http.stopped:
        record.checks.append(dict(method='captions', result='domain_stopped', time=now()))
        return
    try:
        with guarded_ydl(inv.http, dict(writesubtitles=True, writeautomaticsub=True,
                subtitleslangs=languages, subtitlesformat='json3/vtt', skip_download=True)) as ydl:
            data = ydl.extract_info(record.url, download=False)
        if not isinstance(data, dict) or data.get('id') != record.video_id:
            raise ValueError('Caption extractor identity mismatch')
        tracks = data.get('requested_subtitles') or {}
        captured = 0
        for language, track in list(tracks.items())[:5]:
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,35}', language):
                continue
            if track.get('ext') not in {'json3', 'vtt'}:
                continue
            # No extractor-provided headers, cookies, POSTs, or media formats.
            url = normalize_url(track.get('url', ''))
            if not url or domain(url) != 'youtube.com' or domain(record.url) in inv.http.stopped:
                continue
            result = inv.http.fetch(url)
            record.checks.append(dict(method='captions', result=result.result,
                source=url, time=now(), evidence=result.evidence))
            if result.result != 'ok':
                continue
            if track['ext'] == 'json3':
                body = json.loads(result.text)
                if not isinstance(body, dict) or not isinstance(body.get('events'), list):
                    raise ValueError('Invalid JSON3 caption text')
            elif not result.text.lstrip('\ufeff \r\n').startswith('WEBVTT'):
                raise ValueError('Invalid WebVTT caption text')
            record.captions.append(dict(language=language, format=track['ext'],
                evidence=result.evidence, source=url, checked_at=now(),
                provenance='yt_dlp_selected_caption_track', completeness='retrieved_track_not_content_reviewed'))
            captured += 1
        record.checks.append(dict(method='captions', result='caption_text_available' if captured else 'captions_unavailable', time=now()))
    except Exception as exc:
        record.checks.append(dict(method='captions', result='captions_unconfirmed',
                                  time=now(), detail=str(exc)[:400]))


def import_youtube_details(inv, path):
    """Import explicitly attributed saved connector evidence; never call that connector."""
    raw = Path(path).read_bytes()
    if len(raw) > 4_000_000:
        raise ValueError('Saved details exceed 4 MB')
    batches = json.loads(raw)
    if not isinstance(batches, list):
        raise ValueError('Expected an array of saved-detail envelopes')
    validated = []
    for envelope in batches:
        if not isinstance(envelope, dict) or envelope.get('provider') != 'firecrawl':
            raise ValueError('Each saved record must identify provider firecrawl')
        if not envelope.get('retrieved_at') or not envelope.get('source_url'):
            raise ValueError('Saved details require retrieval date and source URL')
        ref = identify_url(envelope['source_url'])
        data = envelope.get('data')
        if not isinstance(data, dict) or not ref or ref.platform != 'youtube':
            raise ValueError('Expected one YouTube video details object')
        vid = data.get('video_id', data.get('id'))
        if vid != ref.video_id or not VIDEO_ID.fullmatch(str(vid)):
            raise ValueError('Saved details video ID mismatch')
        validated.append((envelope, ref, data))
    digest = hashlib.sha256(raw).hexdigest()
    evidence = 'evidence/' + digest + '.json'
    (Path(inv.args.output) / evidence).write_bytes(raw)
    for envelope, ref, data in validated:
        r = inv.catalog.add(ref, envelope['source_url'], 'saved_firecrawl_youtube_details')
        metadata = {key: data[key] for key in ('title', 'channel_id', 'channel', 'channel_url', 'uploader', 'uploader_url') if key in data}
        if data.get('is_unlisted') is True:
            metadata['availability'] = 'unlisted'
        inv.metadata(r, metadata, envelope['source_url'], 'saved_firecrawl_youtube_details')
        status = data.get('playability_status', data.get('playability'))
        if isinstance(status, dict):
            status = status.get('status')
        # Provider-reported OK is retained but never becomes observed playback.
        r.checks.append(dict(method='saved_firecrawl_youtube_details',
            result='provider_reports_playability_ok' if status == 'OK' else 'provider_playability_unconfirmed',
            provider_status=status, evidence=evidence, source=envelope['source_url'],
            retrieved_at=envelope['retrieved_at'], imported_at=now()))
        r.accessibility = classify(r.checks, bool(r.metadata))
    inv.notes.append(dict(source=str(path), method='saved_firecrawl_youtube_details',
        records=len(validated), evidence=evidence, network_requests=0,
        limitation='Imported historical provider claims; no current playback observation or block bypass.'))


def parse_cdx(text):
    data, end = json.JSONDecoder().raw_decode(text.lstrip())
    tail = text.lstrip()[end:].strip()
    if not isinstance(data, list) or (data and not isinstance(data[0], list)):
        raise ValueError('Invalid CDX JSON table')
    if data and (not {'timestamp', 'original', 'statuscode', 'mimetype'} <= set(data[0])):
        raise ValueError('CDX headers missing required fields')
    if data and any(not isinstance(row, list) or len(row) != len(data[0])
                    or not all(isinstance(value, str) for value in row) for row in data[1:]):
        raise ValueError('Invalid CDX row')
    rows = [dict(zip(data[0], row)) for row in data[1:]] if data else []
    if tail and ('\n' in tail or len(tail) > 4096):
        raise ValueError('Invalid CDX resume key')
    return rows, tail


def full_archives(inv):
    """Inventory every returned row; follow resume keys within explicit hard caps."""
    supplied = [normalize_url('https://' + inv.root + '/'), normalize_url(inv.args.vimeo)]
    supplied += [normalize_url(url) for url in inv.args.site]
    slug = urlsplit(normalize_url(inv.args.vimeo)).path.strip('/').split('/')[0]
    if re.fullmatch(r'[A-Za-z0-9_-]+', slug):
        supplied += ['https://vimeo.com/' + slug, 'https://vimeo.com/api/v2/' + slug + '/']
    supplied += inv.args.archive_target
    targets = list(dict.fromkeys(supplied))
    permitted = {inv.root, domain(inv.args.youtube), domain(inv.args.vimeo)}
    for target in targets:
        if normalize_url(target) != target or domain(target) not in permitted:
            raise ValueError('Archive target outside supplied public creator/platform scope: ' + target)
        if MEDIA_EXT.search(target) or re.search(r'/(?:login|account|logout|admin)(?:/|$)', urlsplit(target).path):
            raise ValueError('Archive target is not a public page/feed')
    inventory = []
    captures = set()
    snapshot_count = 0
    for target in targets:
        resume = ''
        seen_keys = set()
        exhausted = False
        index_pages = 0
        for _ in range(max(1, min(inv.args.archive_index_pages, 100))):
            params = dict(url=target, matchType='prefix', output='json', limit=1000, showResumeKey='true')
            if resume:
                params['resumeKey'] = resume
            url = 'https://web.archive.org/cdx/search/cdx?' + urlencode(params)
            response = inv.http.fetch(url)
            if response.result != 'ok':
                inv.notes.append(dict(source=url, result=response.result, method='wayback_full_index'))
                break
            index_pages += 1
            try:
                rows, next_key = parse_cdx(response.text)
            except (ValueError, TypeError) as exc:
                inv.notes.append(dict(source=url, result='invalid_cdx', reason=str(exc)))
                break
            for row in rows:
                item = dict(row, query=target, index_evidence=response.evidence, disposition='index_only')
                original = normalize_url(row.get('original', ''))
                timestamp = row.get('timestamp', '')
                # A returned row never widens the requested prefix or domain.
                if not original.startswith(target) or domain(original) not in permitted or not re.fullmatch(r'\d{14}', timestamp):
                    item['disposition'] = 'outside_target_or_invalid'
                elif row.get('statuscode') != '200':
                    item['disposition'] = 'non_success_index_only'
                elif row.get('mimetype') not in {'text/html', 'application/xhtml+xml', 'application/json', 'text/xml', 'application/xml'} or MEDIA_EXT.search(original) or BINARY_EXT.search(original):
                    item['disposition'] = 'non_page_index_only'
                elif (timestamp, original) in captures:
                    item['disposition'] = 'duplicate_capture'
                elif snapshot_count >= max(0, min(inv.args.archive_pages, 100)):
                    item['disposition'] = 'snapshot_limit'
                else:
                    captures.add((timestamp, original))
                    snapshot_count += 1
                    snapshot = f'https://web.archive.org/web/{timestamp}id_/{original}'
                    result = inv.http.fetch(snapshot)
                    item.update(disposition=result.result, snapshot=snapshot, evidence=result.evidence)
                    if result.result == 'ok':
                        inv.scan(result.text, snapshot, 'wayback_snapshot')
                inventory.append(item)
            if not next_key:
                exhausted = True
                break
            if next_key in seen_keys:
                inv.notes.append(dict(source=target, result='repeated_resume_key'))
                break
            seen_keys.add(next_key)
            resume = next_key
        inv.notes.append(dict(source=target, method='wayback_full_index', index_pages=index_pages,
                              index_exhausted=exhausted, snapshot_limit=inv.args.archive_pages))
    (Path(inv.args.output) / 'archive-inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
