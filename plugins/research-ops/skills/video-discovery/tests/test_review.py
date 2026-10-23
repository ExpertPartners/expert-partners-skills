import json
from dataclasses import asdict

import pytest

from review_catalog import review, valid_sample
from video_discovery import Record, identify_url, parser


@pytest.fixture
def catalog(tmp_path):
    root = tmp_path / 'original'
    root.mkdir()
    cfg = vars(parser().parse_args(['--creator', 'Example Creator', '--youtube',
        'https://youtube.com/@examplecreator', '--vimeo', 'https://vimeo.com/examplecreator',
        '--website', 'example.com', '--output', str(root)]))
    cfg['output'] = str(root)
    seed = Record('youtube', 'AbCdEf123_-', 'https://www.youtube.com/watch?v=AbCdEf123_-', seed=True)
    ref = identify_url('https://example.com/testimonial.mp4')
    direct = Record(ref.platform, ref.video_id, ref.url)
    video = Record('youtube', 'XyZaBc456_-', 'https://www.youtube.com/watch?v=XyZaBc456_-')
    data = dict(configuration=cfg, notes=[], page_titles={}, records=[asdict(r) for r in [seed, direct, video]])
    path = root / 'catalog.json'
    path.write_text(json.dumps(data))
    (root / 'requests.jsonl').write_text('')
    (root / 'evidence').mkdir()
    (root / 'evidence' / 'preserved.txt').write_text('Original evidence')
    return path, direct, video


def sample(r):
    return dict(video_id=r.video_id, url=r.url, method='bounded_seek_decode',
        result='viewable_sample_confirmed', decoded_span_seconds=2, distinct_decoded_frames=61,
        bytes_read=4000, request_count=2, prior_prefix_bytes=0, original_file_bytes=100000)


def test_review_preserves_sources_seeds_and_keys(catalog, tmp_path, monkeypatch):
    path, direct, _ = catalog
    original = path.read_bytes()
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: pytest.fail('Network forbidden'))
    result = review(path, tmp_path / 'reviewed', [sample(direct)])
    before = json.loads(original)
    assert path.read_bytes() == original
    rows = {(r['platform'], r['video_id']): r for r in result['records']}
    assert set(rows) == {(r['platform'], r['video_id']) for r in before['records']}
    assert rows[('youtube', 'AbCdEf123_-')] == before['records'][0]
    assert result['summary']['additional_creator_owned_playable'] == 0
    assert rows[('direct', direct.video_id)]['verification_category'] == 'unresolved'
    assert (tmp_path / 'reviewed/evidence/preserved.txt').read_text() == 'Original evidence'
    assert (tmp_path / 'reviewed/catalog.csv').exists()
    assert 'Fixed-catalog verification' in (tmp_path / 'reviewed/findings.md').read_text()


@pytest.mark.parametrize('changes', [
    {'url': 'https://other.example/video.mp4'}, {'decoded_span_seconds': 0.1},
    {'distinct_decoded_frames': 1}, {'bytes_read': 100000}, {'request_count': 9},
    {'original_file_bytes': 1}, {'method': 'oembed'},
])
def test_invalid_sample_does_not_create_output(catalog, tmp_path, changes):
    path, direct, _ = catalog
    bad = dict(sample(direct), **changes)
    assert not valid_sample(direct, bad)
    with pytest.raises(ValueError):
        review(path, tmp_path / 'reviewed', [bad])
    assert not (tmp_path / 'reviewed').exists()


def test_failed_decode_retains_uncertainty(catalog, tmp_path):
    path, direct, _ = catalog
    result = review(path, tmp_path / 'reviewed', [dict(video_id=direct.video_id, url=direct.url,
        method='bounded_seek_decode', result='unverified', error='domain stopped')])
    assert result['summary']['viewable_samples'] == 0
    assert result['summary']['additional_creator_owned_playable'] == 0


def test_third_party_credit_is_not_platform_verification(catalog, tmp_path):
    path, _, video = catalog
    decision = dict(platform=video.platform, video_id=video.video_id, attribution='third_party_public_credit',
                    source='https://example.org/show', basis='Exact ID credited to show', publisher='Example Show')
    result = review(path, tmp_path / 'reviewed', decisions=[decision])
    row = next(r for r in result['records'] if r['video_id'] == video.video_id)
    assert row['verification_category'] == 'third_party_or_unrelated'
    assert row['ownership'] == 'unverified'


def test_reject_added_candidates_and_ownership_override(catalog, tmp_path):
    path, _, video = catalog
    decision = dict(platform=video.platform, video_id='unknown', attribution='unresolved', source='url', basis='basis')
    with pytest.raises(ValueError):
        review(path, tmp_path / 'reviewed', decisions=[decision])
    decision.update(video_id=video.video_id, attribution='verified_creator')
    with pytest.raises(ValueError):
        review(path, tmp_path / 'reviewed', decisions=[decision])


def test_existing_and_nested_outputs_refused(catalog, tmp_path):
    path, _, _ = catalog
    with pytest.raises(ValueError):
        review(path, path.parent)
    with pytest.raises(ValueError):
        review(path, path.parent / 'nested')
