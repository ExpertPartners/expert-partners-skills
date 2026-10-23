import io
from types import SimpleNamespace
from collections import Counter
import pytest
from verify_candidates import BoundedRangeReader, RangeLimit

class Raw(io.BytesIO):
 def read(self,size=-1,decode_content=False):return super().read(size)

class Response:
 def __init__(self,status=206,body=b'abcd',headers=None):
  self.status_code=status;self.headers=headers or {'content-range':'bytes 0-3/10000000'}
  self.raw=Raw(body)
 def __enter__(self):return self
 def __exit__(self,*args):pass

class Session:
 def __init__(self,responses):self.responses=list(responses);self.calls=[];self.cookies=SimpleNamespace(clear=lambda:None)
 def get(self,url,**kw):self.calls.append(kw);return self.responses.pop(0)

@pytest.fixture
def make(monkeypatch):
 monkeypatch.setattr('verify_candidates.time.sleep',lambda _:None)
 def factory(responses,total=10000000,byte_limit=100):
  h=SimpleNamespace(allowed=lambda u:(True,''),stopped={},counts=Counter(),limit=90,delay=1,last={},timeout=20,
                    public_url=lambda u:True,session=Session(responses),record=lambda *args:None)
  r=BoundedRangeReader(h,'https://example.com/a.mp4',total,byte_limit=byte_limit,block_size=4)
  return r,h
 return factory

def test_seeks_and_cache(make):
 r,h=make([Response(),Response(body=b'wxyz',headers={'content-range':'bytes 9999996-9999999/10000000'})])
 assert r.read(2)==b'ab'
 assert r.seek(-4,2)==9999996 and r.read(4)==b'wxyz'
 r.seek(1);assert r.read(3)==b'bcd'
 assert len(h.session.calls)==2 and r.bytes_read==8

def test_refuse_unbounded_read(make):
 r,h=make([])
 with pytest.raises(RangeLimit):r.read()
 assert not h.session.calls

def test_refuse_full_file_response_without_read(make):
 response=Response(status=200)
 r,h=make([response])
 with pytest.raises(RangeLimit):r.read(2)
 assert response.raw.tell()==0

def test_refuse_mismatched_total_without_read(make):
 response=Response(headers={'content-range':'bytes 0-3/500'})
 r,h=make([response])
 with pytest.raises(RangeLimit):r.read(2)
 assert response.raw.tell()==0

def test_byte_budget(make):
 r,h=make([Response()],byte_limit=4)
 assert r.read(4)==b'abcd'
 with pytest.raises(RangeLimit):r.read(4)
 assert len(h.session.calls)==1

def test_block_stops_entire_domain(make):
 r,h=make([Response(status=403)])
 with pytest.raises(RangeLimit):r.read(4)
 assert 'example.com' in h.stopped
 with pytest.raises(RangeLimit):r.read(4)
 assert len(h.session.calls)==1

def test_retry_once(make):
 r,h=make([Response(status=503),Response(status=503)])
 with pytest.raises(RangeLimit):r.read(4)
 assert len(h.session.calls)==2

def test_shared_domain_budget(make):
 r,h=make([]);h.counts['example.com']=90
 with pytest.raises(RangeLimit):r.read(4)
 assert not h.session.calls

@pytest.mark.parametrize('owned,viewable,thirdparty,expected',[
 (True,True,False,'creator_owned_playable'),
 (True,False,False,'creator_owned_playback_unconfirmed'),
 (False,True,False,'unresolved'),
 (False,False,True,'third_party_or_unrelated'),
 (False,False,False,'unresolved')])
def test_categories_do_not_equate_publication_with_ownership(owned,viewable,thirdparty,expected):
 from review_catalog import verification_category
 assert verification_category(owned,viewable,thirdparty)==expected

def test_exact_id_evidence_rejects_unrelated_search_results():
 from review_catalog import matching_hits
 batch={'result':{'data':{'web':[
  {'url':'https://example.com/unrelated','description':'An unrelated product'},
  {'url':'https://youtube.com/watch?v=AbCdEf123_-','description':'Mentions XyZaBc456_-'},
  {'url':'https://youtube.com/watch?v=XyZaBc456_-','description':'Target'},
  {'url':'https://example.com/publisher','description':'Watch XyZaBc456_-'}]}}}
 assert len(matching_hits('XyZaBc456_-',batch))==2

def test_sample_does_not_claim_full_duration_playback():
 from video_discovery import classify
 assert classify([{'result':'viewable_sample_confirmed'}])=='viewable_sample_confirmed_full_duration_untested'

def test_ranges_respect_robots_crawl_delay(make,monkeypatch):
 from protego import Protego
 r,h=make([Response()])
 h.robots={'https://example.com':Protego.parse('User-agent: *\nCrawl-delay: 7\n')}
 h.last['example.com']=100
 sleeps=[]
 monkeypatch.setattr('verify_candidates.time.monotonic',lambda:100)
 monkeypatch.setattr('verify_candidates.time.sleep',sleeps.append)
 r.read(4)
 assert sleeps==[7]

def test_no_implicit_netrc_credentials(tmp_path,monkeypatch):
 import requests
 from video_discovery import PublicHTTP
 monkeypatch.setattr('requests.sessions.get_netrc_auth',lambda url:pytest.fail('netrc must not be consulted'))
 client=PublicHTTP(tmp_path)
 request=client.session.prepare_request(requests.Request('GET','https://example.com/'))
 assert 'Authorization' not in request.headers
