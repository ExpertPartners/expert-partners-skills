import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

import discovery_extensions as ext
from video_discovery import Investigation, Record, parser, Fetch


@pytest.fixture
def inv(tmp_path):
    args = parser().parse_args(['--creator','Example Creator','--youtube','https://youtube.com/@example',
        '--youtube-channel-id','UC-example','--vimeo','https://vimeo.com/example/videos',
        '--website','example.com','--output',str(tmp_path)])
    args.output = str(tmp_path)
    return Investigation(args)


def test_import_metadata_preserves_block_and_does_not_claim_playback(inv, tmp_path, monkeypatch):
    inv.http.stopped['youtube.com'] = 'prior 403'
    monkeypatch.setattr(inv.http, 'fetch', lambda *a, **k: pytest.fail('Import must be offline'))
    payload = [dict(provider='firecrawl', source_url='https://youtu.be/AbCdEf123_-',
        retrieved_at='2026-10-20T00:00:00Z', data=dict(video_id='AbCdEf123_-', title='Title',
        channel_id='UC-example', is_unlisted=True, playability_status={'status':'OK'}))]
    path = tmp_path/'details.json';path.write_text(json.dumps(payload))
    ext.import_youtube_details(inv,path)
    r = inv.catalog.records[('youtube','AbCdEf123_-')]
    assert r.ownership == 'verified_creator' and r.listing_status == 'unlisted_explicit'
    assert r.accessibility == 'metadata_available_playback_unverified'
    assert r.playback == 'not_tested' and inv.http.stopped['youtube.com'] == 'prior 403'
    check = r.checks[-1]
    assert check['retrieved_at'] == payload[0]['retrieved_at']
    assert (tmp_path/check['evidence']).read_text() == path.read_text()


@pytest.mark.parametrize('change', [dict(provider='unknown'),dict(retrieved_at=''),
    dict(source_url='https://youtu.be/XyZaBc456_-'),dict(data={'video_id':'bad'})])
def test_saved_details_reject_bad_identity_or_provenance(inv,tmp_path,change):
    record=dict(provider='firecrawl',source_url='https://youtu.be/AbCdEf123_-',retrieved_at='date',
                data={'video_id':'AbCdEf123_-'})
    record.update(change)
    p=tmp_path/'details.json';p.write_text(json.dumps([record]))
    with pytest.raises(ValueError):ext.import_youtube_details(inv,p)
    assert not inv.catalog.records


def caption_setup(inv,monkeypatch,data,body='WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello\n'):
    calls=[]
    class Extractor:
        def extract_info(self,url,download):
            assert download is False
            calls.append(url)
            return data
    def factory(http,options):
        assert options['skip_download'] and options['writeautomaticsub']
        return nullcontext(Extractor())
    monkeypatch.setattr(ext,'guarded_ydl',factory)
    monkeypatch.setattr(inv.http,'fetch',lambda url: Fetch(url,'ok',200,body,evidence='evidence/caption.txt'))
    return Record('youtube','AbCdEf123_-','https://youtube.com/watch?v=AbCdEf123_-'),calls


def test_captions_text_only_and_no_playback_promotion(inv,monkeypatch):
    data=dict(id='AbCdEf123_-', requested_subtitles={'en':dict(ext='vtt',url='https://www.youtube.com/api/timedtext?v=AbCdEf123_-')})
    r,calls=caption_setup(inv,monkeypatch,data)
    ext.read_captions(inv,r,['en'])
    assert len(calls)==1 and len(r.captions)==1 and r.playback=='not_tested'
    assert r.captions[0]['completeness']=='retrieved_track_not_content_reviewed'


def test_blocked_platform_never_uses_caption_extractor(inv,monkeypatch):
    r,calls=caption_setup(inv,monkeypatch,{})
    inv.http.stopped['youtube.com']='403'
    ext.read_captions(inv,r,['en'])
    assert not calls and not r.captions and r.checks[-1]['result']=='domain_stopped'


@pytest.mark.parametrize('track',[
    dict(ext='mp4',url='https://youtube.com/video.mp4'),
    dict(ext='vtt',url='https://evil.example/caption.vtt')])
def test_caption_tracks_cannot_request_media_or_external_hosts(inv,monkeypatch,track):
    r,_=caption_setup(inv,monkeypatch,dict(id='AbCdEf123_-',requested_subtitles={'en':track}))
    monkeypatch.setattr(inv.http,'fetch',lambda *a,**k:pytest.fail('Forbidden track fetched'))
    ext.read_captions(inv,r,['en'])
    assert not r.captions


@pytest.mark.parametrize('data,body',[
    (dict(id='XyZaBc456_-'),'WEBVTT'),
    (dict(id='AbCdEf123_-',requested_subtitles={'en':dict(ext='vtt',url='https://youtube.com/api/timedtext')}),'<html>blocked</html>'),
    (dict(id='AbCdEf123_-',requested_subtitles={'en':dict(ext='json3',url='https://youtube.com/api/timedtext')}),'{}')])
def test_caption_uncertainty(inv,monkeypatch,data,body):
    r,_=caption_setup(inv,monkeypatch,data,body)
    ext.read_captions(inv,r,['en'])
    assert not r.captions and r.checks[-1]['result']=='captions_unconfirmed'


def cdx(rows,token=''):
    return json.dumps([['timestamp','original','statuscode','mimetype']]+rows)+'\n\n'+token


@pytest.mark.parametrize('body', ['{}', '[["original"]]', cdx([[123,'url','200','text/html']]),
                                  cdx([['short']]), cdx([],'one\ntwo')])
def test_malformed_cdx_is_not_silently_accepted(body):
    with pytest.raises(ValueError):
        ext.parse_cdx(body)


def test_full_cdx_paginates_platform_paths_and_accounts_all_rows(inv,monkeypatch):
    inv.args.archive_pages=1;inv.args.archive_index_pages=3;calls=[]
    def fetch(url):
        calls.append(url)
        if '/cdx/' not in url:
            return Fetch(url,'ok',200,'<iframe src="https://youtube.com/embed/AbCdEf123_-"></iframe>')
        p=parse_qs(urlsplit(url).query)
        if p['url']==['https://example.com/']:
            if 'resumeKey' not in p:
                return Fetch(url,'ok',200,cdx([['20260101000000','https://example.com/a','200','text/html'],
                    ['20260101000000','https://example.com/v.mp4','200','video/mp4']], 'NEXT'))
            return Fetch(url,'ok',200,cdx([['20260102000000','https://example.com/b','200','text/html'],
                ['20260102000000','https://example.com/c','404','text/html']]))
        return Fetch(url,'ok',200,cdx([]))
    monkeypatch.setattr(inv.http,'fetch',fetch)
    ext.full_archives(inv)
    inventory=json.loads((Path(inv.args.output)/'archive-inventory.json').read_text())
    assert len(inventory)==4
    assert {r['disposition'] for r in inventory}=={'ok','snapshot_limit','non_page_index_only','non_success_index_only'}
    assert ('youtube','AbCdEf123_-') in inv.catalog.records
    assert any('resumeKey=NEXT' in u for u in calls)
    assert any('api%2Fv2%2Fexample' in u for u in calls)
    assert all(n.get('index_exhausted') for n in inv.notes if n.get('method')=='wayback_full_index')


def test_cdx_repeated_resume_key_stops_and_reports_incomplete(inv,monkeypatch):
    inv.args.archive_index_pages=20
    monkeypatch.setattr(inv.http,'fetch',lambda u:Fetch(u,'ok',200,cdx([],'same')))
    ext.full_archives(inv)
    assert any(n.get('result')=='repeated_resume_key' for n in inv.notes)
    assert all(not n.get('index_exhausted') for n in inv.notes if n.get('method')=='wayback_full_index')


def test_cdx_rejects_outside_scope_before_network(inv,monkeypatch):
    inv.args.archive_target=['https://other.example/private']
    monkeypatch.setattr(inv.http,'fetch',lambda *a:pytest.fail('No request allowed'))
    with pytest.raises(ValueError):ext.full_archives(inv)


def test_empty_public_site_produces_empty_catalog(inv,monkeypatch):
    monkeypatch.setattr(inv.http,'fetch',lambda u,**k:Fetch(u,'ok',200,'<html><title>No video</title></html>',{'content-type':'text/html'}))
    inv.args.depth=0
    inv.run()
    result=json.loads((Path(inv.args.output)/'catalog.json').read_text())
    assert result['records']==[] and result['summary']['candidates']==0
