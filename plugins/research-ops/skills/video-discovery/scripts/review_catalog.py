#!/usr/bin/env python3
"""Review a fixed catalog offline, preserving its original evidence in a new directory."""
import argparse
import json
import shutil
from pathlib import Path

from video_discovery import Investigation, Record, classify, identify_url, now


def verification_category(creator_owned=False, sample_viewable=False, third_party_credit=False):
    if creator_owned:
        return 'creator_owned_playable' if sample_viewable else 'creator_owned_playback_unconfirmed'
    return 'third_party_or_unrelated' if third_party_credit else 'unresolved'


def matching_hits(video_id, batch):
    hits = []
    for hit in (batch or {}).get('result', {}).get('data', {}).get('web', []):
        ref = identify_url(hit.get('url', ''))
        if ref and (ref.platform != 'youtube' or ref.video_id != video_id):
            continue
        if (ref and ref.video_id == video_id) or (not ref and video_id in hit.get('description', '')):
            hits.append(hit)
    return hits


def valid_sample(record, sample):
    """Require bounded decoder evidence for this exact direct URL, never metadata alone."""
    return (
        record.platform == 'direct'
        and sample.get('url') == record.url
        and sample.get('video_id') == record.video_id
        and sample.get('method') == 'bounded_seek_decode'
        and sample.get('result') == 'viewable_sample_confirmed'
        and sample.get('decoded_span_seconds', 0) >= 2
        and sample.get('distinct_decoded_frames', 0) > 1
        and 0 < sample.get('bytes_read', 0) <= 2 * 1024 * 1024
        and 0 < sample.get('request_count', 0) <= 8
        and sample.get('bytes_read', 0) + sample.get('prior_prefix_bytes', 0)
        <= sample.get('original_file_bytes', 0) // 4
    )


def review(catalog, destination, samples=(), decisions=()):
    catalog, destination = Path(catalog), Path(destination)
    if destination.exists():
        raise ValueError('Use a fresh output directory to preserve earlier evidence')
    if destination.resolve().is_relative_to(catalog.parent.resolve()):
        raise ValueError('Review output must be outside the source directory')
    data = json.loads(catalog.read_text())
    records = [Record(**raw) for raw in data['records']]
    keys = {(r.platform, r.video_id) for r in records}
    by_key = {(r.platform, r.video_id): r for r in records}
    sample_map, decision_map = {}, {}
    for sample in samples:
        key = ('direct', sample['video_id'])
        if key not in keys or key in sample_map:
            raise ValueError('Unknown or duplicate sample ID')
        if sample.get('url') != by_key[key].url:
            raise ValueError('Sample URL does not match candidate')
        if sample.get('result') == 'viewable_sample_confirmed' and not valid_sample(by_key[key], sample):
            raise ValueError('Insufficient bounded playback evidence for ' + sample['video_id'])
        sample_map[key] = sample
    for decision in decisions:
        key = (decision['platform'], decision['video_id'])
        if key not in keys or key in decision_map:
            raise ValueError('Unknown or duplicate decision ID')
        if not decision.get('basis') or not decision.get('source'):
            raise ValueError('A review decision requires source and basis')
        if decision.get('attribution') not in {'third_party_public_credit', 'creator_site_publication_verified', 'unresolved'}:
            raise ValueError('Reviews cannot assert platform ownership without platform metadata')
        if decision['attribution'] == 'third_party_public_credit' and not decision.get('publisher'):
            raise ValueError('Third-party credits require the named publisher')
        decision_map[key] = decision
    shutil.copytree(catalog.parent, destination)
    config = dict(data['configuration'], output=str(destination), resume=True)
    inv = Investigation(argparse.Namespace(**config))
    inv.http.offline = True
    inv.notes, inv.page_titles = list(data['notes']), data['page_titles']
    for record in records:
        key = (record.platform, record.video_id)
        inv.catalog.records[key] = record
        if record.seed:
            continue
        sample, decision = sample_map.get(key), decision_map.get(key)
        if sample:
            record.checks.append(sample)
            record.sample_viewable = valid_sample(record, sample)
            record.playback = ('two_seconds_decoded_full_duration_audio_and_browser_untested'
                               if record.sample_viewable else 'sample_verification_unsuccessful')
        if decision:
            record.publisher_attribution = decision['attribution']
            record.credited_publisher = decision.get('publisher', '')
            record.verification_basis = decision['basis']
            record.verification_evidence.append(dict(decision, method='documented_public_credit_review'))
        third_party = record.publisher_attribution == 'third_party_public_credit'
        owned = record.ownership == 'verified_creator'
        # Conflicting ownership and public credit must be reviewed, never silently counted.
        record.verification_category = 'unresolved' if owned and third_party else verification_category(
            owned, record.sample_viewable, third_party)
        record.accessibility = classify(record.checks, bool(record.metadata))
        record.verification_checked_at = now()
    inv.notes.append(dict(source='offline_fixed_catalog_review', result='completed',
                          reason='No discovery or network calls. Seed rows retained. Original directory preserved.'))
    inv.export()
    with (destination / 'findings.md').open('a') as report:
        report.write('\n## Fixed-catalog verification\n\n')
        report.write('Playable here means a bounded two-second moving-video sample; full duration, audio and browser playback remain untested. Website publication alone does not prove ownership.\n\n')
        report.write('| Video | Classification | Basis |\n|---|---|---|\n')
        for r in records:
            if not r.seed:
                basis = r.verification_basis.replace('|', '\\|').replace('\n', ' ')
                report.write(f'| [{r.platform}:{r.video_id}]({r.url}) | {r.verification_category} | {basis} |\n')
    (destination / 'review-inputs.json').write_text(json.dumps(dict(samples=list(samples), decisions=list(decisions)), indent=2) + '\n')
    return json.loads((destination / 'catalog.json').read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--samples', type=Path)
    parser.add_argument('--decisions', type=Path)
    args = parser.parse_args()
    review(args.catalog, args.output,
           json.loads(args.samples.read_text()) if args.samples else [],
           json.loads(args.decisions.read_text()) if args.decisions else [])


if __name__ == '__main__':
    main()
