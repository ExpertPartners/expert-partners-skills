#!/usr/bin/env python3
"""Bounded, public, read-only video discovery. No media download or login support."""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import io
import ipaddress
import json
import os
import re
import socket
import time
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit, unquote

import requests
import tldextract
from bs4 import BeautifulSoup
from defusedxml import ElementTree
from protego import Protego

UA = 'PublicVideoDiscovery/0.1 (bounded read-only public research)'

class NoAccountAuth(requests.auth.AuthBase):
    """Keep environment proxy support without implicitly loading account netrc."""
    def __call__(self, request):
        return request


def request_delay(http, url):
    p = urlsplit(url)
    origin = urlunsplit((p.scheme, p.netloc, '', '', ''))
    policy = getattr(http, 'robots', {}).get(origin)
    return max(http.delay, (policy.crawl_delay(UA) or 0) if policy else 0)

PSL = tldextract.TLDExtract(suffix_list_urls=())
TRACKING = {'fbclid', 'gclid', '_rvid', 'mc_cid', 'mc_eid'}
VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')
MEDIA_EXT = re.compile(r'\.(?:mp4|webm|mov|m4v|m3u8|mpd)(?:$|\?)', re.I)
BINARY_EXT = re.compile(r'\.(?:png|jpe?g|gif|webp|svg|ico|woff2?|ttf|zip|pdf|mp3|wav)(?:$|\?)', re.I)

def now():
    return datetime.now(timezone.utc).isoformat()

def domain(url):
    h = urlsplit(url).hostname or ''
    e = PSL(h)
    return e.top_domain_under_public_suffix or h

def normalize_url(value, base=''):
    if not isinstance(value, str) or not value.strip():
        return ''
    value = html.unescape(value.strip()).replace('\\/', '/')
    if any(c in value for c in '\\"<>'):
        return ''
    if value.startswith('//'):
        value = 'https:' + value
    try:
        if base:
            value = urljoin(base, value)
        p = urlsplit(value)
    except ValueError:
        return ''
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        return ''
    try:
        port = p.port
    except ValueError:
        return ''
    host = p.hostname.lower()
    netloc = ('[' + host + ']') if ':' in host else host
    if port and not (p.scheme == 'http' and port == 80 or p.scheme == 'https' and port == 443):
        netloc += ':' + str(port)
    query = sorted((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                   if not k.lower().startswith('utm_') and k.lower() not in TRACKING)
    # Do not lowercase paths or strip Vimeo privacy hashes / signed query parameters.
    return urlunsplit((p.scheme.lower(), netloc, p.path or '/', urlencode(query), ''))

def decode_text(text):
    for _ in range(2):
        text = html.unescape(text).replace('\\/', '/')
        text = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m[1], 16)), text)
        text = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)), text)
    return text

@dataclass(frozen=True)
class Reference:
    platform: str
    video_id: str
    url: str


def identify_url(url):
    url = normalize_url(url)
    if not url:
        return None
    p = urlsplit(url)
    h, parts, q = p.hostname, p.path.strip('/').split('/'), dict(parse_qsl(p.query))
    vid = None
    if h in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com',
             'youtube-nocookie.com', 'www.youtube-nocookie.com', 'youtu.be'}:
        if h == 'youtu.be':
            vid = parts[0]
        elif parts[0] == 'watch':
            vid = q.get('v')
        elif parts[0] in {'embed', 'shorts', 'live', 'v', 'podcast'} and len(parts) > 1:
            vid = parts[1]
        if vid and VIDEO_ID.fullmatch(vid):
            return Reference('youtube', vid, 'https://www.youtube.com/watch?v=' + vid)
    if h in {'i.ytimg.com', 'img.youtube.com'} and len(parts) > 1 and parts[0] in {'vi','vi_webp'}:
        if VIDEO_ID.fullmatch(parts[1]):
            return Reference('youtube', parts[1], 'https://www.youtube.com/watch?v=' + parts[1])
    if h in {'vimeo.com', 'www.vimeo.com', 'player.vimeo.com'}:
        match = re.fullmatch(r'(?:(?:video|channels/[^/]+|groups/[^/]+/videos|album/\d+/video|showcase/\d+/video)/)?(\d{6,12})(?:/([a-fA-F0-9]{6,64}))?', p.path.strip('/'))
        if match:
            vid, token = match.groups()
            token = token or q.get('h')
            return Reference('vimeo', vid, 'https://vimeo.com/' + vid + ('/' + token if token else ''))
    if h in {'filmot.com', 'www.filmot.com'} and parts[0] in {'video', 'sidebyside'} and len(parts)>1:
        if VIDEO_ID.fullmatch(parts[1]):
            return Reference('youtube', parts[1], 'https://www.youtube.com/watch?v=' + parts[1])
    if h in {'www.loom.com','loom.com'} and len(parts)>1 and parts[0] in {'share','embed'} and re.fullmatch('[a-f0-9]{32}',parts[1]):
        return Reference('loom', parts[1], 'https://www.loom.com/share/' + parts[1])
    if h in {'fast.wistia.com','fast.wistia.net','home.wistia.com'} and len(parts)>2 and parts[-2] in {'iframe','medias'} and re.fullmatch('[a-z0-9]{10}',parts[-1]):
        return Reference('wistia',parts[-1],'https://fast.wistia.net/embed/iframe/'+parts[-1])
    if MEDIA_EXT.search(url):
        # Different encodings/URLs remain distinct; no claim of content-level deduplication.
        return Reference('direct', hashlib.sha256(url.encode()).hexdigest()[:20], url)
    return None


def extract_references(text, base=''):
    text = decode_text(text)
    urls = re.findall(r'''(?:https?:)?//[^\s<>"'\\]+''', text)
    soup = BeautifulSoup(text if '<' in text and not text.lstrip().startswith('<?xml') else '', 'html.parser')
    for node in soup.find_all(True):
        for attr in ('src', 'href', 'data-src', 'data-video-url', 'content'):
            v = node.get(attr)
            if isinstance(v,str):
                urls.append(normalize_url(v,base))
    found = {}
    for u in urls:
        u = normalize_url(u.rstrip('),;]}'))
        if not u:continue
        r = identify_url(u)
        if r:
            found[(r.platform,r.video_id,r.url)] = r
        # Encoded URL parameters (e.g. search redirects), never guess bare numbers.
        for _, value in parse_qsl(urlsplit(u).query):
            if value.startswith(('https://','http://')):
                r = identify_url(value)
                if r: found[(r.platform,r.video_id,r.url)] = r
    if domain(base) == 'youtube.com':
        for vid in re.findall(r'"videoId"\s*:\s*"([A-Za-z0-9_-]{11})"', text):
            r = Reference('youtube',vid,'https://www.youtube.com/watch?v='+vid)
            found[(r.platform,r.video_id,r.url)] = r
    return list(found.values())

@dataclass
class Record:
    platform: str
    video_id: str
    url: str
    seed: bool = False
    title: str = ''
    title_basis: str = ''
    creator: str = ''
    creator_url: str = ''
    ownership: str = 'unverified'
    association: str = 'unverified'
    listing_status: str = 'unknown'
    accessibility: str = 'reference_only'
    playback: str = 'not_tested'
    verification_category: str = 'not_reverified'
    verification_basis: str = ''
    publisher_attribution: str = ''
    credited_publisher: str = ''
    sample_viewable: bool = False
    verification_checked_at: str = ''
    verification_evidence: list = field(default_factory=list)
    source_pages: list = field(default_factory=list)
    discovery_methods: list = field(default_factory=list)
    references: list = field(default_factory=list)
    metadata: list = field(default_factory=list)
    checks: list = field(default_factory=list)

class Catalog:
    def __init__(self):
        self.records = {}

    def add(self, ref, source, method, seed=False, title='', excerpt='', associated=False):
        key = (ref.platform,ref.video_id)
        r = self.records.setdefault(key, Record(ref.platform,ref.video_id,ref.url))
        r.seed |= seed
        if source not in r.source_pages: r.source_pages.append(source)
        if method not in r.discovery_methods: r.discovery_methods.append(method)
        item = dict(url=ref.url, source=source, method=method, excerpt=excerpt[:400])
        if item not in r.references: r.references.append(item)
        if ref.platform == 'vimeo' and len(urlsplit(ref.url).path.strip('/').split('/')) > 1:
            r.url = ref.url  # Preserve only privacy tokens actually found in public references.
        if title and not r.title:
            r.title, r.title_basis = title, method
        if associated and r.ownership != 'verified_creator':
            r.association = 'creator_site_reference'
        elif r.association == 'unverified' and method == 'search_index':
            r.association = 'search_mention_unverified'
        return r

    def ingest(self,text,source,method,**kwargs):
        return [self.add(ref,source,method,**kwargs) for ref in extract_references(text,source)]


def classify(checks, has_metadata=False):
    """Only explicit platform evidence determines private/deleted/unlisted status."""
    states = {c.get('result') for c in checks}
    if 'private' in states and 'deleted' in states: return 'conflicting_evidence'
    restricted = states & {'private','deleted'}
    if restricted and states & {'playback_observed','media_endpoint_accessible','viewable_sample_confirmed'}:
        return 'conflicting_evidence'
    if restricted: return next(iter(restricted))
    if 'playback_observed' in states: return 'confirmed_playable'
    if 'viewable_sample_confirmed' in states: return 'viewable_sample_confirmed_full_duration_untested'
    if 'sample_frame_decoded' in states: return 'partial_media_decodable_full_playback_unverified'
    if 'media_endpoint_accessible' in states: return 'media_endpoint_accessible'
    if 'formats_advertised' in states: return 'formats_advertised_playback_unverified'
    if has_metadata or 'metadata_available' in states: return 'metadata_available_playback_unverified'
    if states & {'blocked','robots_disallowed','terms_restricted','domain_stopped'}:
        return 'verification_blocked'
    if states & {'http_404','http_410','inaccessible_unknown'}: return 'inaccessible_unknown'
    return 'reference_only'

@dataclass
class Fetch:
    url: str
    result: str
    status: int | None = None
    text: str = ''
    headers: dict = field(default_factory=dict)
    evidence: str = ''

class PublicHTTP:
    """Shared request budget, robots gate, redirect checks, and domain circuit breakers."""
    def __init__(self,out,limit=100,delay=1.5,timeout=20,blocked=(),public_check=True,resume=False):
        self.out = Path(out); (self.out/'evidence').mkdir(parents=True,exist_ok=True)
        self.limit = min(max(limit,1),100)
        self.delay = max(delay,1.0)
        self.timeout = timeout
        self.counts = Counter(); self.last = {}; self.stopped = {d:'preexisting blocking response' for d in blocked}
        self.robots = {}; self.cache = {}; self.log = []
        self.public_check = public_check
        self.offline = False
        self.session = requests.Session(); self.session.headers['User-Agent'] = UA
        self.session.auth = NoAccountAuth()
        self.session.trust_env = True
        if resume:
            self.restore()

    def record(self, f, method='GET', detail=''):
        item = dict(time=now(),method=method,url=f.url,result=f.result,status=f.status,evidence=f.evidence,headers=f.headers,detail=detail)
        self.log.append(item)
        with (self.out/'requests.jsonl').open('a') as stream: stream.write(json.dumps(item)+'\n')
        return f

    def restore(self):
        path=self.out/'requests.jsonl'
        if not path.exists():return
        for line in path.read_text().splitlines():
            item=json.loads(line);self.log.append(item)
            result=item['result'];url=item['url'];method=item['method']
            if item['status'] is not None or result in {'network_error','blocked'}:
                self.counts[domain(url)]+=1
            if result=='blocked':self.stopped[domain(url)]='prior blocking response'
            if result not in {'ok','http_404','http_410','nontext_body_not_requested'}:continue
            evidence=item.get('evidence','')
            body=(self.out/evidence).read_text() if evidence and (self.out/evidence).exists() else ''
            headers=item.get('headers',{})
            if not headers:
                headers={'content-type':'application/json' if body.lstrip().startswith(('[','{')) else 'application/xml' if body.lstrip().startswith('<?xml') else 'text/html' if '<html' in body.lower() else 'text/plain'}
            self.cache[(method,url)]=Fetch(url,result,item['status'],body,headers,evidence)
        for item in reversed(self.log):
            if item['result']=='redirect':
                target=normalize_url(urljoin(item['url'],item.get('headers',{}).get('location','')))
                cached=self.cache.get((item['method'],target))
                if cached:self.cache[(item['method'],item['url'])]=cached

    def public_url(self,url):
        p=urlsplit(url)
        if p.scheme not in {'http','https'} or not p.hostname or p.username or p.password:
            return False
        if p.port not in {None,80,443}: return False
        if not self.public_check: return True
        try:
            return all(ipaddress.ip_address(i[4][0]).is_global for i in socket.getaddrinfo(p.hostname,p.port or 443,type=socket.SOCK_STREAM))
        except (ValueError,OSError): return False

    def allowed(self,url):
        # Vimeo's published terms notice prohibits general page scraping. API exceptions are explicit.
        if domain(url)=='vimeo.com':
            return False,'terms_restricted'
        p=urlsplit(url); origin=urlunsplit((p.scheme,p.netloc,'','',''))
        if origin not in self.robots:
            f=self.fetch(origin+'/robots.txt',robots=True)
            if f.status in {404,410}:
                self.robots[origin]=Protego.parse('')
            elif f.result=='ok' and not f.text.lstrip().startswith('<'):
                self.robots[origin]=Protego.parse(f.text)
            else:
                self.robots[origin]=None
        policy=self.robots[origin]
        if policy is None:return False,'robots_unavailable'
        return (True,'') if policy.can_fetch(url,UA) else (False,'robots_disallowed')

    def fetch(self,url,method='GET',api=False,robots=False,redirects=0):
        url=normalize_url(url)
        key=(method,url)
        if key in self.cache:return self.cache[key]
        if self.offline:return self.record(Fetch(url,'domain_stopped' if domain(url) in self.stopped else 'offline_cache_miss'),method)
        if not url or not self.public_url(url):return self.record(Fetch(url,'unsafe_or_unresolvable_url'),method)
        d=domain(url)
        if d in self.stopped:return self.record(Fetch(url,'domain_stopped'),method,self.stopped[d])
        if self.counts[d]>=self.limit:return self.record(Fetch(url,'budget_exhausted'),method)
        if not api and not robots:
            ok,why=self.allowed(url)
            if not ok:return self.record(Fetch(url,why),method)
        if d in self.stopped:return self.record(Fetch(url,'domain_stopped'),method)
        # Never GET a recognizable full video, even if a crawl link points at it.
        if method=='GET' and MEDIA_EXT.search(url):return self.record(Fetch(url,'media_body_not_requested'),method)
        for attempt in range(2):
            if self.counts[d]>=self.limit:return self.record(Fetch(url,'budget_exhausted'),method)
            delay=self.delay
            p=urlsplit(url); origin=urlunsplit((p.scheme,p.netloc,'','',''))
            policy=self.robots.get(origin)
            if policy:
                delay=max(delay,policy.crawl_delay(UA) or 0)
            time.sleep(max(0,delay-(time.monotonic()-self.last.get(d,0))))
            self.counts[d]+=1; self.last[d]=time.monotonic()
            try:
                # No cookies retained between requests; no credentials are sourced automatically.
                self.session.cookies.clear()
                response=self.session.request(method,url,timeout=self.timeout,allow_redirects=False,stream=True)
                with response as resp:
                    status=resp.status_code
                    headers={k.lower():v for k,v in resp.headers.items() if k.lower() in {'content-type','content-length','location','accept-ranges','last-modified','etag','retry-after'}}
                    f=Fetch(url,'ok',status,headers=headers)
                    if status in {401,403,429,451}:
                        self.stopped[d]=f'HTTP {status} at {url}';f.result='blocked'
                    elif status in {301,302,303,307,308}:
                        self.record(Fetch(url,'redirect',status,headers=headers),method)
                        if redirects>=5:return self.record(Fetch(url,'redirect_limit',status),method)
                        target=urljoin(url,headers.get('location',''))
                        # Only carry the API exemption to another explicitly supported API URL.
                        return self.fetch(target,method,api=api and is_api_url(target),redirects=redirects+1)
                    elif status>=500:
                        f.result='transient_failure';self.record(f,method)
                        if attempt==0:continue
                        return f
                    elif status>=400:f.result=f'http_{status}'
                    elif method=='GET':
                        ct=headers.get('content-type','').lower()
                        if not any(x in ct for x in ('text/','json','xml','javascript')):
                            f.result='nontext_body_not_requested'
                        else:
                            chunks=[];size=0
                            for chunk in resp.iter_content(65536):
                                size+=len(chunk)
                                if size>4_000_000:
                                    f.result='body_limit';break
                                chunks.append(chunk)
                            f.text=b''.join(chunks).decode(resp.encoding if resp.encoding and resp.encoding!='ISO-8859-1' else 'utf-8',errors='replace')
                            if re.search(r'<title>\s*(?:Just a moment|Access Denied|Attention Required)|cf-chl-|g-recaptcha-response',f.text,re.I):
                                f.result='blocked';self.stopped[d]='challenge page'
                    if f.text:
                        digest=hashlib.sha256(f.text.encode()).hexdigest()
                        f.evidence='evidence/'+digest+'.txt'
                        (self.out/f.evidence).write_text(f.text)
                    self.cache[key]=f
                    return self.record(f,method)
            except requests.RequestException as exc:
                msg=str(exc)
                blocked=bool(re.search(r'\b(?:401|403|429|451)\b',msg))
                f=Fetch(url,'blocked' if blocked else 'network_error')
                if blocked:self.stopped[d]='network/proxy blocking response'
                self.record(f,method,msg[:350])
                if blocked or attempt==1:return f
        raise AssertionError('unreachable')


def is_api_url(url):
    p=urlsplit(url)
    return (p.hostname=='vimeo.com' and (p.path=='/api/oembed.json' or p.path.startswith('/api/v2/'))) or (p.hostname=='www.youtube.com' and p.path=='/oembed')


def apply_metadata(r, data, source, method, youtube_channel_id='', youtube_url='', vimeo_url=''):
    r.metadata.append(dict(source=source,method=method,data=data))
    title=data.get('title')
    if title:r.title=str(title);r.title_basis=method
    author=data.get('author_name') or data.get('user_name') or data.get('uploader') or data.get('channel')
    author_url=data.get('author_url') or data.get('user_url') or data.get('channel_url') or data.get('uploader_url')
    if author:r.creator=str(author)
    if author_url:r.creator_url=str(author_url)
    def profile(u):return normalize_url(u).rstrip('/').removesuffix('/videos').casefold()
    exact=False;other=False
    if r.platform=='youtube':
        cid=data.get('channel_id')
        if cid and youtube_channel_id:exact=cid==youtube_channel_id;other=not exact
        elif author_url:
            accepted={profile(youtube_url)}
            if youtube_channel_id:accepted.add(profile('https://www.youtube.com/channel/'+youtube_channel_id))
            actual=profile(author_url).replace('://youtube.com/','://www.youtube.com/')
            accepted={a.replace('://youtube.com/','://www.youtube.com/') for a in accepted}
            exact=actual in accepted;other=bool(accepted-{''}) and not exact
    elif r.platform=='vimeo' and author_url and vimeo_url:
        exact=profile(author_url)==profile(vimeo_url);other=not exact
    if exact:r.ownership='verified_creator';r.association='creator_owned'
    elif other:r.ownership='other_creator'
    # Matching display names alone never verify ownership.
    privacy=data.get('privacy',{})
    availability=data.get('availability')
    if availability=='unlisted' or isinstance(privacy,dict) and privacy.get('view')=='unlisted':r.listing_status='unlisted_explicit'
    elif availability=='public':r.listing_status='public_explicit'
    r.checks.append(dict(time=now(),source=source,method=method,result='metadata_available'))

class Investigation:
    def __init__(self,args):
        self.args=args;self.catalog=Catalog()
        self.http=PublicHTTP(args.output,args.max_pages,args.delay,blocked=args.blocked_domain,resume=args.resume)
        self.root=domain(normalize_url('https://'+args.website.removeprefix('https://').removeprefix('http://')))
        self.notes=[];self.visited=set();self.page_titles={}

    def owned(self,url):return domain(url)==self.root

    def metadata(self,r,data,source,method):
        apply_metadata(r,data,source,method,self.args.youtube_channel_id,self.args.youtube,self.args.vimeo)

    def import_search(self,path):
        queue=[]
        for batch in json.loads(Path(path).read_text()):
            q=batch.get('query','')
            data=batch.get('data',{})
            for hit in data.get('web',[]):
                # Exclude false positive Filmot hits lacking either exact creator or domain association.
                evidence=hit.get('title','')+' '+hit.get('description','')
                if domain(hit['url'])=='filmot.com' and self.args.creator.casefold() not in evidence.casefold() and self.root not in evidence:
                    continue
                self.catalog.ingest(hit['url'],hit['url'],'search_index',title=hit.get('title',''),excerpt=evidence)
                if self.owned(hit['url']):queue.append(hit['url'])
            self.notes.append(dict(source='search_index',query=q,result_count=len(data.get('web',[])),import_file=str(path)))
        return queue

    def scan(self,text,url,method):
        associated=self.owned(url) or (method=='wayback_snapshot' and self.root in url)
        records=self.catalog.ingest(text,url,method,associated=associated)
        soup=BeautifulSoup(text if not text.lstrip().startswith('<?xml') else '', 'html.parser')
        page_title=soup.title.get_text(' ',strip=True) if soup.title else ''
        self.page_titles[url]=page_title
        # A source page's title is context, never silently presented as a video title.
        for node in soup.select('iframe, video, source'):
            value=node.get('src') or node.get('data-src')
            ref=identify_url(urljoin(url,value)) if value else None
            if ref:
                self.catalog.add(ref,url,method,title=node.get('title','') or node.get('aria-label',''),associated=associated)
        return soup,records

    def crawl(self,entries):
        q=deque((normalize_url(u),0,'website_source') for u in entries)
        while q:
            url,depth,method=q.popleft()
            if not url or url in self.visited or depth>self.args.depth or not self.owned(url):continue
            if BINARY_EXT.search(url) or MEDIA_EXT.search(url):continue
            if self.http.counts[self.root]>=self.http.limit and ('GET',url) not in self.http.cache:continue
            self.visited.add(url)
            f=self.http.fetch(url)
            print(f'Crawl {f.result}: {url}',flush=True)
            if f.result!='ok':continue
            soup,_=self.scan(f.text,f.url,method)
            if 'xml' in f.headers.get('content-type','') or f.text.lstrip().startswith('<?xml'):
                try:
                    tree=ElementTree.fromstring(f.text)
                    for node in tree.iter():
                        if node.tag.rsplit('}',1)[-1]=='loc' and node.text:
                            q.append((normalize_url(node.text),depth,'sitemap_page'))
                except ElementTree.ParseError: self.notes.append(dict(source=url,result='invalid_xml'))
            for node in soup.select('a[href], iframe[src], iframe[data-src], script[src]'):
                value=node.get('href') or node.get('src') or node.get('data-src')
                linked=normalize_url(value,url)
                if not self.owned(linked):continue
                if node.name=='script' and not self.args.scripts:continue
                # Never follow logout/admin/account links, or click/submit a form.
                if re.search(r'/(?:logout|signout|admin|wp-admin|account|login)(?:/|\?|$)',linked,re.I):continue
                q.append((linked,depth+1,'javascript_source' if node.name=='script' else 'website_source'))
            # Linked subdomains only; no brute force enumeration.
            origin=urlunsplit((*urlsplit(url)[:2],'','',''))
            sm=origin+'/sitemap.xml'
            if sm not in self.visited and method!='javascript_source':q.append((sm,depth,'sitemap'))
            policy=self.http.robots.get(origin)
            if policy:
                for sm in policy.sitemaps or []:
                    if self.owned(sm):q.append((normalize_url(sm),depth,'sitemap'))

    def vimeo_legacy(self):
        slug=urlsplit(normalize_url(self.args.vimeo)).path.strip('/').split('/')[0]
        if not re.fullmatch(r'[A-Za-z0-9_-]+',slug):return
        # Legacy endpoint is optional and bounded to three documented pages.
        for page in range(1,4):
            url=f'https://vimeo.com/api/v2/{slug}/videos.json?page={page}'
            f=self.http.fetch(url,api=True)
            if f.result!='ok':break
            try:data=json.loads(f.text)
            except ValueError:break
            if not isinstance(data,list):break
            for item in data:
                ref=identify_url(item.get('url',''))
                if ref:
                    r=self.catalog.add(ref,url,'vimeo_legacy_api')
                    self.metadata(r,item,url,'vimeo_legacy_api')
            if len(data)<20:break

    def archives(self):
        query=urlencode({'url':'*.'+self.root+'/*','output':'json','filter':'mimetype:text/html','collapse':'urlkey','limit':100})
        url='https://web.archive.org/cdx/search/cdx?'+query
        f=self.http.fetch(url)
        if f.result=='ok':
            try:
                data=json.loads(f.text);rows=[dict(zip(data[0],row)) for row in data[1:]] if data else []
            except (ValueError,TypeError):rows=[]
            # Prefer distinct path names over tracking variants; newest sample among returned records.
            selected={}
            for row in rows:
                original=normalize_url(row.get('original',''))
                if not self.owned(original):continue
                if row.get('statuscode')!='200':continue
                if re.search(r'/(?:wp-login\.php|wp-admin|login|account|logout)(?:/|\?|$)',original,re.I):continue
                key=urlsplit(original).path
                if key not in selected or row['timestamp']>selected[key]['timestamp']:selected[key]=row
            for row in list(selected.values())[:self.args.archive_pages]:
                original=row['original'];snapshot=f"https://web.archive.org/web/{row['timestamp']}id_/{original}"
                r=self.http.fetch(snapshot)
                print(f'Archive {r.result}: {original}',flush=True)
                if r.result=='ok':self.scan(r.text,snapshot,'wayback_snapshot')
            self.notes.append(dict(source=url,result='sampled_archive',index_rows=len(rows),distinct_paths=len(selected),snapshot_limit=self.args.archive_pages))
        cc=self.http.fetch('https://index.commoncrawl.org/collinfo.json')
        if cc.result=='ok':
            try:collections=json.loads(cc.text)
            except ValueError:collections=[]
            for item in collections[:2]:
                url=item['cdx-api']+'?'+urlencode({'url':'*.'+self.root+'/*','output':'json','filter':'status:200','pageSize':1})
                f=self.http.fetch(url)  # Enforce robots; no WARC/media download.
                if f.result=='ok':
                    for line in f.text.splitlines()[:100]:
                        try:r=json.loads(line)
                        except ValueError:continue
                        self.catalog.ingest(r.get('url',''),url,'commoncrawl_index')
                self.notes.append(dict(source=url,result=f.result,coverage='index references only; WARC bodies not retrieved'))
                if f.result!='ok':break

    def platform_discovery(self):
        # Public YouTube pages, playlists and RSS only when ordinary access is allowed.
        base=normalize_url(self.args.youtube).rstrip('/')
        for suffix in ('/videos','/shorts','/streams','/playlists'):
            url=base+suffix;f=self.http.fetch(url)
            if f.result!='ok':
                self.notes.append(dict(source=url,result=f.result));break
            self.catalog.ingest(f.text,url,'youtube_channel_page')
            if suffix=='/playlists':
                lists=list(dict.fromkeys(re.findall(r'"playlistId"\s*:\s*"([A-Za-z0-9_-]+)"',f.text)))[:10]
                for pid in lists:
                    pu='https://www.youtube.com/playlist?'+urlencode({'list':pid})
                    pf=self.http.fetch(pu)
                    if pf.result=='ok':self.catalog.ingest(pf.text,pu,'youtube_public_playlist')
        if self.args.youtube_channel_id:
            url='https://www.youtube.com/feeds/videos.xml?'+urlencode({'channel_id':self.args.youtube_channel_id})
            f=self.http.fetch(url)
            if f.result=='ok':self.catalog.ingest(f.text,url,'youtube_rss')
        self.notes.append(dict(source=self.args.vimeo,result='profile_scraping_skipped',reason='Vimeo terms notice; use supported oEmbed and optional legacy API'))
        filmot='https://filmot.com/search/'+self.args.creator.replace(' ','%20')+'/1?channelID='+self.args.youtube_channel_id
        f=self.http.fetch(filmot)
        if f.result=='ok':self.catalog.ingest(f.text,filmot,'filmot_public_index')
        self.notes.append(dict(source=filmot,result=f.result,cli='baba20o/filmot-cli evaluated; API credentials required, not provisioned'))

    def validate(self):
        for r in self.catalog.records.values():
            if r.platform in {'youtube','vimeo'}:
                endpoint='https://www.youtube.com/oembed' if r.platform=='youtube' else 'https://vimeo.com/api/oembed.json'
                url=endpoint+'?'+urlencode({'url':r.url,'format':'json'})
                f=self.http.fetch(url,api=True)
                r.checks.append(dict(time=now(),source=url,method='oembed',result=f.result,status=f.status,evidence=f.evidence))
                if f.result=='ok':
                    try:data=json.loads(f.text)
                    except ValueError:data={}
                    expected=data.get('video_id') if isinstance(data,dict) else None
                    if isinstance(data,dict) and data.get('type')=='video' and (not expected or str(expected)==r.video_id):
                        self.metadata(r,data,url,'oembed')
            elif r.platform=='direct':
                f=self.http.fetch(r.url,method='HEAD')
                ct=f.headers.get('content-type','').lower()
                good=f.result=='ok' and f.status==200 and (ct.startswith('video/') or 'mpegurl' in ct or 'dash+xml' in ct)
                r.checks.append(dict(time=now(),source=r.url,method='media_head',result='media_endpoint_accessible' if good else f.result,status=f.status,headers=f.headers))
            if self.args.yt_dlp and r.platform not in {'direct','vimeo'}:
                self.ytdlp(r)
            r.accessibility=classify(r.checks,bool(r.metadata))
            print(f'Validate {r.platform}:{r.video_id}: {r.accessibility}',flush=True)

    def ytdlp(self,r):
        import yt_dlp
        from yt_dlp.networking import Response
        http=self.http
        class GuardedYDL(yt_dlp.YoutubeDL):
            def urlopen(self,req):
                method=req.method if hasattr(req,'method') else 'GET'
                url=req if isinstance(req,str) else req.url
                if method not in {'GET','HEAD'}:raise RuntimeError('Only GET/HEAD are permitted')
                f=http.fetch(url,method=method)
                if f.result!='ok':raise RuntimeError('Public retrieval stopped: '+f.result)
                return Response(io.BytesIO(f.text.encode()),url=f.url,headers=f.headers,status=f.status)
        try:
            with GuardedYDL({'skip_download':True,'quiet':True,'no_warnings':True,'noplaylist':True,'retries':0,'extractor_retries':0,'socket_timeout':15,'cachedir':False}) as ydl:
                data=ydl.extract_info(r.url,download=False)
            if not data or str(data.get('id'))!=r.video_id:raise ValueError('extractor identity mismatch')
            keep={k:data[k] for k in ('id','title','uploader','uploader_url','channel','channel_id','channel_url','availability') if k in data}
            self.metadata(r,keep,r.url,'yt_dlp')
            if data.get('formats'):r.checks.append(dict(time=now(),source=r.url,method='yt_dlp',result='formats_advertised',format_count=len(data['formats'])))
        except Exception as exc:
            r.checks.append(dict(time=now(),source=r.url,method='yt_dlp',result='extractor_unavailable',detail=str(exc)[:400]))

    def render(self,url):
        """Optional fresh browser, no media: all HTTP goes through the same policy/budget."""
        if not self.owned(url):raise ValueError('Render only a supplied creator website URL')
        try:from playwright.sync_api import sync_playwright
        except ImportError:
            self.notes.append(dict(source=url,result='render_unavailable',reason='Install playwright and Chromium optionally'));return
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True)
                context=browser.new_context(service_workers='block')
                def route_handler(route):
                    request=route.request
                    if request.method!='GET' or request.resource_type in {'media','image','font','websocket'} or not self.owned(request.url):
                        route.abort();return
                    f=self.http.fetch(request.url)
                    if f.result=='ok':route.fulfill(status=f.status,headers={'content-type':f.headers.get('content-type','text/html')},body=f.text)
                    else:route.abort()
                context.route('**/*',route_handler)
                context.route_web_socket('**/*', lambda ws: ws.close())
                page=context.new_page();page.goto(url,wait_until='domcontentloaded',timeout=25000)
                page.wait_for_timeout(1500)
                self.scan(page.content(),url,'rendered_dom')
                browser.close()
        except Exception as exc:self.notes.append(dict(source=url,result='render_failed',detail=str(exc)[:300]))

    def run(self):
        for path in self.args.seeds:
            for item in json.loads(Path(path).read_text()):
                ref=identify_url(item['url'])
                if ref:self.catalog.add(ref,'user_supplied_seed','seed',seed=True)
        entries=['https://'+self.root+'/','https://'+self.root+'/sitemap.xml']+self.args.site
        for path in self.args.search_json:entries+=self.import_search(path)
        if self.args.legacy_vimeo:self.vimeo_legacy()
        self.crawl(entries)
        for url in self.args.render:self.render(url)
        self.platform_discovery()
        if self.args.archives:self.archives()
        self.validate()
        self.export()

    def export(self):
        out=Path(self.args.output)
        records=sorted(self.catalog.records.values(),key=lambda r:(r.platform,r.video_id))
        summary=dict(creator=self.args.creator,checked_at=now(),candidates=len(records),seed_records=sum(r.seed for r in records),
                     new_candidates=sum(not r.seed for r in records),new_verified_creator=sum(not r.seed and r.ownership=='verified_creator' for r in records),
                     confirmed_playable=sum(r.accessibility=='confirmed_playable' for r in records),status_counts=dict(Counter(r.accessibility for r in records)),
                     platform_counts=dict(Counter(r.platform for r in records)),requests_per_domain=dict(self.http.counts),stopped_domains=self.http.stopped)
        summary.update(verification_category_counts=dict(Counter(r.verification_category for r in records if not r.seed)),
                       additional_creator_owned_playable=sum(not r.seed and r.verification_category=='creator_owned_playable' for r in records),
                       additional_creator_published_viewable_assets=sum(not r.seed and r.publisher_attribution=='creator_site_publication_verified' and r.sample_viewable for r in records),
                       viewable_samples=sum(r.sample_viewable for r in records))
        payload=dict(schema_version=2,summary=summary,configuration=vars(self.args),notes=self.notes,page_titles=self.page_titles,records=[asdict(r) for r in records])
        (out/'catalog.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False))
        fields=['platform','video_id','url','seed','title','title_basis','creator','creator_url','ownership','association','listing_status','accessibility','playback','verification_category','verification_basis','publisher_attribution','credited_publisher','sample_viewable','verification_checked_at','source_pages','discovery_methods']
        with (out/'catalog.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
            for r in records:
                row=asdict(r)
                for key in ('source_pages','discovery_methods'):row[key]=' | '.join(row[key])
                # Prevent spreadsheet formula execution; JSON retains exact strings.
                writer.writerow({k:("'"+v if isinstance(v,str) and v[:1] in '=+-@' else v) for k,v in row.items() if k in fields})
        lines=[f'# Video discovery: {self.args.creator}', '',f'Checked: {summary["checked_at"]}', '',
               f'{len(records)} unique candidate records; {summary["seed_records"]} seeds; {summary["new_candidates"]} additional candidates; {summary["new_verified_creator"]} additional records with verified creator ownership.',
               f'Confirmed playable: {summary["confirmed_playable"]}. No full video files were downloaded. Optional bounded samples, if recorded, establish only partial decoding. A successful oEmbed response, advertised format, or HEAD response is not proof of playback.', '',
               'Ownership requires an exact platform profile/channel match. Creator-site references may include third-party interviews or testimonials. Search snippets remain unverified unless independently corroborated. Unknown fields are left blank; no inaccessible ID is automatically labeled deleted/private. Missing from a profile does not prove unlisted status.', '',
               '| Platform / ID | Title | Ownership / association | Accessibility | Discovery sources |',
               '|---|---|---|---|---|']
        def clean(s):return str(s).replace('|','\\|').replace('\n',' ')
        for r in records:
            sources='<br>'.join(f'[{clean(m)}]({s})' for m,s in dict.fromkeys((x['method'],x['source']) for x in r.references))
            lines.append(f'| [{r.platform}:{r.video_id}]({r.url}) | {clean(r.title or "Unknown")} | {r.ownership}; {r.association} | {r.accessibility} | {sources} |')
        lines+=['','## Coverage and failures','', 'Request totals (includes robots, APIs, assets, redirects and retries): `'+json.dumps(dict(self.http.counts))+'`. A registrable domain has a hard 100-request cap, shared across its subdomains. Cached responses do not spend another request.','', '```json',json.dumps(self.notes,indent=2),'```','', 'Stopped domains: `'+json.dumps(self.http.stopped)+'`. See requests.jsonl and content-addressed evidence files for every retrieval.','', 'Archive discovery is sampled, not exhaustive. Common Crawl covers only permitted index references. Public references cannot enumerate all unlisted videos. Direct media deduplication uses normalized URLs, not audiovisual fingerprints. This prototype does not use account cookies, login, paid sources, unlisted-ID guessing, or domain-restriction bypasses.']
        (out/'findings.md').write_text('\n'.join(lines)+'\n')
        (out/'summary.json').write_text(json.dumps(summary,indent=2))
        print(json.dumps(summary,indent=2))


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--resume',action='store_true',help='Reuse evidence and request budgets from an interrupted run')
    p.add_argument('--creator',required=True);p.add_argument('--youtube',required=True);p.add_argument('--vimeo',required=True);p.add_argument('--website',required=True)
    p.add_argument('--youtube-channel-id',default='');p.add_argument('--site',action='append',default=[])
    p.add_argument('--seeds',action='append',default=[]);p.add_argument('--search-json',action='append',default=[])
    p.add_argument('--output',type=Path,default=Path('output'));p.add_argument('--max-pages',type=int,default=100,help='Hard request cap per registrable domain, maximum 100')
    p.add_argument('--depth',type=int,default=3);p.add_argument('--delay',type=float,default=1.5)
    p.add_argument('--scripts',action=argparse.BooleanOptionalAction,default=True)
    p.add_argument('--legacy-vimeo',action='store_true');p.add_argument('--archives',action='store_true');p.add_argument('--archive-pages',type=int,default=15)
    p.add_argument('--yt-dlp',action='store_true',help='Optional guarded metadata extraction, never playback proof')
    p.add_argument('--render',action='append',default=[],help='Optional creator page rendering; media/third-party requests disabled')
    p.add_argument('--blocked-domain',action='append',default=[],help='Carry an earlier blocking response into this run')
    return p


def main():
    args=parser().parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    if (args.output/'catalog.json').exists():raise SystemExit('Use a fresh output directory to preserve prior evidence')
    if (args.output/'requests.jsonl').exists() and not args.resume:raise SystemExit('Use --resume or a fresh output directory to preserve request budgets')
    # JSON-compatible configuration.
    args.output=str(args.output)
    Investigation(args).run()

if __name__=='__main__':main()
