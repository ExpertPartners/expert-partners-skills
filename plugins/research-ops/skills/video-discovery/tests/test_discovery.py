import json
from pathlib import Path
import pytest
import requests
from video_discovery import (Catalog, PublicHTTP, Reference, Record, apply_metadata,
                             classify, extract_references, identify_url, normalize_url)

@pytest.mark.parametrize('url',[
 'https://youtu.be/AbCdEf123_-?t=30',
 'https://www.youtube.com/watch?v=AbCdEf123_-&list=PLabc',
 'https://youtube.com/embed/AbCdEf123_-?rel=0',
 'https://www.youtube-nocookie.com/embed/AbCdEf123_-',
 'https://youtube.com/shorts/AbCdEf123_-',
 'https://music.youtube.com/podcast/AbCdEf123_-',
 'https://i.ytimg.com/vi/AbCdEf123_-/hqdefault.jpg',
])
def test_youtube_forms(url):
 assert identify_url(url)==Reference('youtube','AbCdEf123_-','https://www.youtube.com/watch?v=AbCdEf123_-')

@pytest.mark.parametrize('url',[
 'https://youtube.com.evil.example/watch?v=AbCdEf123_-',
 'https://youtu.be/short', 'https://youtube.com/watch?v=AbCdEf123_-X',
 'https://vimeo.com/examplecreator/videos','https://vimeo.com/123abc',
 'javascript:alert(1)','http://user:pass@youtube.com/watch?v=AbCdEf123_-'
])
def test_reject_false_ids(url):assert identify_url(url) is None

def test_hash_preserved():
 r=identify_url('https://player.vimeo.com/video/1234567890?h=abc123def4&autoplay=1')
 assert r==Reference('vimeo','1234567890','https://vimeo.com/1234567890/abc123def4')
 assert identify_url(r.url)==r

def test_escaped_inline_javascript():
 text=r'''<script>var a="https:\u002F\u002Fwww.youtube.com\u002Fembed\u002FAbCdEf123_-";var b="https:\/\/player.vimeo.com\/video\/2345678901?h=abcdef1234";</script>'''
 assert {(r.platform,r.video_id) for r in extract_references(text)}=={('youtube','AbCdEf123_-'),('vimeo','2345678901')}

def test_relative_media_and_no_numeric_guessing():
 refs=extract_references('<video src="/media/test.mp4"></video><script>{"id":1234567890,"videoId":"AbCdEf123_-"}</script>','https://example.com/page')
 assert len(refs)==1 and refs[0].platform=='direct'

def test_normalization():
 assert normalize_url('../Video?b=2&utm_source=x&a=1#t','https://EXAMPLE.com/a/page')=='https://example.com/Video?a=1&b=2'
 assert normalize_url('https://example.com:443/v?h=abc&sig=xyz')=='https://example.com/v?h=abc&sig=xyz'
 assert normalize_url('https://example.com:bad/')==''

def test_dedupe_keeps_provenance_and_seed_and_hash():
 c=Catalog()
 c.add(identify_url('https://vimeo.com/1234567890'),'seed','seed',seed=True)
 c.add(identify_url('https://player.vimeo.com/video/1234567890?h=abc123def4'),'https://example.com','embed')
 c.add(identify_url('https://vimeo.com/1234567890'),'https://example.com/other','link')
 assert len(c.records)==1
 r=next(iter(c.records.values()))
 assert r.seed and len(r.source_pages)==3 and r.url.endswith('/abc123def4')

@pytest.mark.parametrize('checks,meta,expected',[
 ([],False,'reference_only'),
 ([{'result':'ok'}],False,'reference_only'),
 ([{'result':'ok'}],True,'metadata_available_playback_unverified'),
 ([{'result':'http_404'}],False,'inaccessible_unknown'),
 ([{'result':'http_410'}],False,'inaccessible_unknown'),
 ([{'result':'blocked'}],False,'verification_blocked'),
 ([{'result':'private'}],False,'private'),
 ([{'result':'deleted'}],False,'deleted'),
 ([{'result':'private'},{'result':'deleted'}],False,'conflicting_evidence'),
 ([{'result':'media_endpoint_accessible'}],False,'media_endpoint_accessible'),
 ([{'result':'formats_advertised'}],True,'formats_advertised_playback_unverified'),
])
def test_uncertain_classification(checks,meta,expected):assert classify(checks,meta)==expected

def test_name_is_not_identity():
 r=Record('vimeo','1234567890','https://vimeo.com/1234567890')
 apply_metadata(r,{'title':'X','author_name':'Example Creator'},'api','oembed',vimeo_url='https://vimeo.com/examplecreator/videos')
 assert r.ownership=='unverified'
 apply_metadata(r,{'author_name':'Example Creator','author_url':'https://vimeo.com/imposter'},'api','oembed',vimeo_url='https://vimeo.com/examplecreator/videos')
 assert r.ownership=='other_creator'
 apply_metadata(r,{'author_url':'https://vimeo.com/examplecreator'},'api','oembed',vimeo_url='https://vimeo.com/examplecreator/videos')
 assert r.ownership=='verified_creator'
 assert r.listing_status=='unknown'

def test_partial_oembed_not_playback():
 r=Record('vimeo','1234567890','https://vimeo.com/1234567890')
 apply_metadata(r,{'type':'video','html':'<iframe>','video_id':1234567890},'api','oembed')
 assert classify(r.checks,True)=='metadata_available_playback_unverified'
 assert r.playback=='not_tested' and r.ownership=='unverified'

class FakeResponse:
 def __init__(self,status=200,body='',headers=None):
  self.status_code=status;self.body=body;self.headers=headers or {'Content-Type':'text/plain'};self.encoding='utf-8';self.read=False
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def iter_content(self,n):self.read=True;yield self.body.encode()

@pytest.fixture
def client(tmp_path,monkeypatch):
 monkeypatch.setattr('video_discovery.time.sleep',lambda _:None)
 return PublicHTTP(tmp_path,limit=10,public_check=False)

def sequence(client,monkeypatch,responses):
 calls=[]
 def send(method,url,**kwargs):
  calls.append((method,url));r=responses.pop(0)
  if isinstance(r,Exception):raise r
  return r
 monkeypatch.setattr(client.session,'request',send)
 return calls

def test_robots_wildcards_stop_query(client,monkeypatch):
 calls=sequence(client,monkeypatch,[FakeResponse(body='User-agent: *\nDisallow: /search*\n')])
 assert client.fetch('https://example.com/search?q=hello').result=='robots_disallowed'
 assert len(calls)==1

def test_403_circuit_breaker_covers_subdomains(client,monkeypatch):
 calls=sequence(client,monkeypatch,[FakeResponse(403)])
 assert client.fetch('https://www.example.com/a').result=='robots_unavailable'
 assert client.fetch('https://player.example.com/b').result=='domain_stopped'
 assert len(calls)==1

def test_transient_retry_exactly_once(client,monkeypatch):
 calls=sequence(client,monkeypatch,[FakeResponse(503),FakeResponse(503)])
 assert client.fetch('https://example.com/api',api=True).result=='transient_failure'
 assert len(calls)==2

def test_proxy_403_not_retried(client,monkeypatch):
 calls=sequence(client,monkeypatch,[requests.exceptions.ProxyError('Tunnel connection failed: 403 Forbidden')])
 assert client.fetch('https://example.com/a',api=True).result=='blocked'
 assert len(calls)==1

def test_shared_domain_budget(client,monkeypatch):
 client.limit=1
 calls=sequence(client,monkeypatch,[FakeResponse()])
 client.fetch('https://a.example.com/first',api=True)
 assert client.fetch('https://b.example.com/next',api=True).result=='budget_exhausted'
 assert len(calls)==1

def test_media_body_never_read(client,monkeypatch):
 media=FakeResponse(headers={'Content-Type':'video/mp4'})
 calls=sequence(client,monkeypatch,[media])
 assert client.fetch('https://example.com/opaque',api=True).result=='nontext_body_not_requested'
 assert not media.read
 assert client.fetch('https://example.com/video.mp4',api=True).result=='media_body_not_requested'
 assert len(calls)==1

def test_redirect_rechecks_robots(client,monkeypatch):
 calls=sequence(client,monkeypatch,[FakeResponse(302,headers={'Location':'https://other.example/search'}),FakeResponse(body='User-agent: *\nDisallow: /search')])
 assert client.fetch('https://example.com/api',api=True).result=='robots_disallowed'
 assert len(calls)==2

def test_cache_avoids_second_request(client,monkeypatch):
 calls=sequence(client,monkeypatch,[FakeResponse(body='metadata')])
 a=client.fetch('https://example.com/api',api=True)
 assert client.fetch('https://example.com/api',api=True) is a
 assert len(calls)==1

def test_blocked_page_never_returned_as_ok(client,monkeypatch):
 calls=sequence(client,monkeypatch,[FakeResponse(body='<title>Just a moment...</title>',headers={'Content-Type':'text/html'})])
 assert client.fetch('https://example.com/page',api=True).result=='blocked'
 assert client.fetch('https://example.com/other',api=True).result=='domain_stopped'

def test_serialized_marketing_fixture():
 p=Path(__file__).parents[1]/'tests'/'fixtures'/'marketing.html'
 refs=extract_references(p.read_text(),'https://example.com/')
 assert len(refs)==10
 assert sum(r.platform=='direct' for r in refs)==8

@pytest.mark.parametrize('value',[None,'', '   ', 42])
def test_missing_or_empty_attribute(value):assert normalize_url(value,'https://example.com/page')==''

def test_resume_preserves_budget_cache_and_block(tmp_path,monkeypatch):
 monkeypatch.setattr('video_discovery.time.sleep',lambda _:None)
 c=PublicHTTP(tmp_path,limit=10,public_check=False)
 calls=sequence(c,monkeypatch,[FakeResponse(body='saved body'),FakeResponse(403)])
 c.fetch('https://example.com/first',api=True)
 c.fetch('https://blocked.example/path',api=True)
 restored=PublicHTTP(tmp_path,limit=10,public_check=False,resume=True)
 assert restored.counts['example.com']==1
 assert restored.fetch('https://example.com/first',api=True).text=='saved body'
 assert restored.fetch('https://blocked.example/next',api=True).result=='domain_stopped'
 assert len(calls)==2

def test_partial_decode_not_full_playback():
 assert classify([{'result':'sample_frame_decoded'}])=='partial_media_decodable_full_playback_unverified'

@pytest.mark.parametrize('headers,size,expected',[
 ({'content-range':'bytes 0-1023/10000'},1024,True),
 ({'content-range':'bytes 0-1023/1024'},1024,False),
 ({'content-range':'bytes 0-1023/2000'},1024,False),
 ({'content-range':'bytes 0-1023/*'},1024,False),
 ({'content-range':'bytes 1024-2047/10000'},1024,False),
 ({},1024,False),
])
def test_partial_range_must_not_be_whole_file(headers,size,expected):
 from probe_media import valid_range
 assert valid_range(headers,size)==expected

def test_range_ignored_never_reads_body(client,monkeypatch):
 from probe_media import sample
 media=FakeResponse(200,headers={'Content-Type':'video/mp4','Content-Length':'10000000'})
 calls=sequence(client,monkeypatch,[FakeResponse(body='User-agent: *\nAllow: /'),media])
 monkeypatch.setattr(client.session,'get',lambda url,**kw:client.session.request('GET',url,**kw))
 body,result=sample(client,'https://example.com/a.mp4',1024)
 assert body is None and result=='range_not_honored_body_not_read' and not media.read

@pytest.mark.parametrize('text',['https://[not-an-ip]/video','//[regex-expression', 'http://[::1', 'https://example.com:99999/'])
def test_malformed_script_url_is_not_fatal(text):
 assert normalize_url(text)==''
 assert extract_references(text)==[]

@pytest.mark.parametrize('value',[r'\"https://example.org/a\"',r'/\"https:/example.org/a',r'\"\"https://example.org/'])
def test_serialized_html_attributes_do_not_become_crawl_paths(value):
 assert normalize_url(value,'https://example.com/')==''

def test_escaped_json_does_not_corrupt_real_html_links():
 from bs4 import BeautifulSoup
 html='<a href="/real">Real</a><script>var data="<a href=\\"https://other.example/\\">";</script>'
 soup=BeautifulSoup(html,'html.parser')
 assert [normalize_url(n.get('href'),'https://example.com') for n in soup.select('a[href]')]==['https://example.com/real']

def test_offline_replay_cannot_make_requests(client,monkeypatch):
 calls=sequence(client,monkeypatch,[])
 client.offline=True
 assert client.fetch('https://example.com/not-saved').result=='offline_cache_miss'
 assert calls==[]

def test_offline_replay_keeps_blocking_reason(client):
 client.offline=True;client.stopped['youtube.com']='previous proxy 403'
 assert client.fetch('https://www.youtube.com/oembed?url=abc',api=True).result=='domain_stopped'

def test_site_reference_does_not_downgrade_verified_ownership():
 c=Catalog();ref=identify_url('https://vimeo.com/1234567890')
 r=c.add(ref,'api','api')
 apply_metadata(r,{'user_url':'https://vimeo.com/examplecreator'},'api','legacy',vimeo_url='https://vimeo.com/examplecreator/videos')
 c.add(ref,'https://example.com','embed',associated=True)
 assert r.association=='creator_owned'
