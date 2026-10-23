#!/usr/bin/env python3
"""Verify existing direct-video candidates using bounded, seekable HTTP ranges.

No discovery; no full media files; no unrestricted decoder networking. Saves
small decoded stills, request hashes and sample timing, not downloaded video.
"""
import argparse
import hashlib
import io
import json
import re
import time
from pathlib import Path

import av
import requests
from video_discovery import PublicHTTP, Fetch, domain, now, request_delay

class RangeLimit(Exception):pass

class BoundedRangeReader(io.RawIOBase):
    def __init__(self,http,url,total,byte_limit=2*1024*1024,request_limit=8,block_size=262144,prior_bytes=0):
        self.http=http;self.url=url;self.total=total
        # Include the previously retrieved 512 KiB prefix in the quarter-file bound.
        self.byte_limit=min(byte_limit,total//4-prior_bytes)
        self.request_limit=request_limit;self.block_size=block_size
        self.position=0;self.blocks={};self.bytes_read=0;self.request_count=0;self.ranges=[]
        self.ok,self.reason=http.allowed(url)
        if not self.ok:raise RangeLimit(self.reason)
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        pos=offset if whence==0 else self.position+offset if whence==1 else self.total+offset if whence==2 else -1
        if pos<0:raise ValueError('invalid seek')
        self.position=pos;return pos
    def load_block(self,index):
        if index in self.blocks:return self.blocks[index]
        start=index*self.block_size;end=min(start+self.block_size,self.total)-1;size=end-start+1
        if size<=0:return b''
        if self.bytes_read+size>self.byte_limit:raise RangeLimit('per-file byte limit')
        h=self.http;d=domain(self.url)
        for attempt in range(2):
            if self.request_count>=self.request_limit:raise RangeLimit('per-file request limit')
            if d in h.stopped:raise RangeLimit('domain stopped')
            if h.counts[d]>=h.limit:raise RangeLimit('shared domain request limit')
            if not h.public_url(self.url):raise RangeLimit('unsafe public URL')
            time.sleep(max(0,request_delay(h,self.url)-(time.monotonic()-h.last.get(d,0))))
            h.counts[d]+=1;h.last[d]=time.monotonic();self.request_count+=1
            try:
                h.session.cookies.clear()
                with h.session.get(self.url,headers={'Range':f'bytes={start}-{end}','Accept-Encoding':'identity'},
                                   timeout=h.timeout,allow_redirects=False,stream=True) as resp:
                    headers={k.lower():v for k,v in resp.headers.items() if k.lower() in {'content-type','content-range','content-length','content-encoding'}}
                    status=resp.status_code
                    if status in {401,403,429,451}:
                        h.stopped[d]='blocking range response';h.record(Fetch(self.url,'blocked',status,headers=headers),'GET_RANGE')
                        raise RangeLimit('blocking response')
                    if status>=500:
                        h.record(Fetch(self.url,'transient_failure',status,headers=headers),'GET_RANGE')
                        if attempt==0:continue
                        raise RangeLimit('transient failure after one retry')
                    expected=f'bytes {start}-{end}/{self.total}'
                    if status!=206 or headers.get('content-range')!=expected or headers.get('content-encoding','identity')!='identity':
                        h.record(Fetch(self.url,'range_mismatch_body_not_read',status,headers=headers),'GET_RANGE')
                        raise RangeLimit('range not honored; no body read')
                    body=resp.raw.read(size,decode_content=False)
                    self.bytes_read+=len(body)
                    item=dict(start=start,end=end,total=self.total,status=status,bytes_read=len(body),sha256=hashlib.sha256(body).hexdigest())
                    self.ranges.append(item)
                    h.record(Fetch(self.url,'bounded_seek_sample',status,headers=headers),'GET_RANGE',json.dumps(item))
                    if len(body)!=size:raise RangeLimit('incomplete range')
                    self.blocks[index]=body;return body
            except requests.RequestException as exc:
                blocked=bool(re.search(r'\b(?:401|403|429|451)\b',str(exc)))
                if blocked:h.stopped[d]='network blocking response'
                h.record(Fetch(self.url,'blocked' if blocked else 'network_error'),'GET_RANGE',str(exc)[:300])
                if blocked or attempt==1:raise RangeLimit(str(exc)) from exc
        raise RangeLimit('range retrieval failed')
    def read(self,size=-1):
        if size<0:raise RangeLimit('unbounded read refused')
        if self.position>=self.total or size==0:return b''
        size=min(size,self.total-self.position)
        result=[]
        while size:
            index,offset=divmod(self.position,self.block_size)
            body=self.load_block(index);chunk=body[offset:offset+size]
            if not chunk:break
            result.append(chunk);self.position+=len(chunk);size-=len(chunk)
        return b''.join(result)
    def readinto(self,buffer):
        data=self.read(len(buffer));buffer[:len(data)]=data;return len(data)


def verify_one(http,r,destination):
    head=next((c for c in reversed(r['checks']) if c.get('method')=='media_head' and c.get('result')=='media_endpoint_accessible'),None)
    result=dict(video_id=r['video_id'],url=r['url'],time=now(),method='bounded_seek_decode',result='unverified',decoded_frames=0)
    if not head:return result
    reader=None
    try:
        total=int(head['headers']['content-length'])
        prior_bytes=sum(c.get('bytes_read',0) for c in r['checks'] if c.get('method')=='range_decode')
        reader=BoundedRangeReader(http,r['url'],total,prior_bytes=prior_bytes)
        first_time=None;last_time=None;hashes=set();last_frame=None;audio_packets=0
        with av.open(reader,format='mp4',mode='r') as container:
            stream=container.streams.video[0];stream.codec_context.options={'err_detect':'explode'}
            result.update(duration_seconds=float(container.duration/av.time_base) if container.duration else None,
                          codec=stream.codec_context.name,width=stream.codec_context.width,height=stream.codec_context.height,
                          audio_streams=len(container.streams.audio))
            for frame in container.decode(stream):
                if frame.is_corrupt:raise RangeLimit('decoder reported corrupt frame')
                frame_time=float(frame.time) if frame.time is not None else None
                if frame_time is None:raise RangeLimit('missing frame timestamps')
                if first_time is None:
                    first_time=frame_time
                    frame.to_image().save(destination/(r['video_id']+'-first.png'))
                last_time=frame_time;last_frame=frame;result['decoded_frames']+=1
                hashes.add(hashlib.sha256(bytes(frame.planes[0])).hexdigest())
                if last_time-first_time>=2.0 or result['decoded_frames']>=180:break
            if last_frame is not None:last_frame.to_image().save(destination/(r['video_id']+'-last.png'))
        span=(last_time-first_time) if first_time is not None else 0
        result.update(sample_start_seconds=first_time,sample_end_seconds=last_time,decoded_span_seconds=span,
                      distinct_decoded_frames=len(hashes),result='viewable_sample_confirmed' if span>=2 and len(hashes)>1 else 'partial_decode_insufficient')
    except Exception as exc:result.update(error=type(exc).__name__+': '+str(exc)[:500])
    if reader:
        result.update(bytes_read=reader.bytes_read,byte_limit=reader.byte_limit,request_count=reader.request_count,ranges=reader.ranges,
                      original_file_bytes=reader.total,prior_prefix_bytes=prior_bytes)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalog',type=Path,default=Path('output/catalog.json'))
    p.add_argument('--result-dir',type=Path,default=Path('verification'));args=p.parse_args()
    out=args.result_dir;out.mkdir(exist_ok=True);(out/'stills').mkdir(exist_ok=True)
    data=json.loads(args.catalog.read_text());cfg=data['configuration']
    http=PublicHTTP(args.catalog.parent,limit=cfg['max_pages'],delay=cfg['delay'],blocked=cfg['blocked_domain'],resume=True)
    path=out/'direct_verification.json';results=json.loads(path.read_text()) if path.exists() else []
    done={r['video_id'] for r in results}
    for r in data['records']:
        if r['seed'] or r['platform']!='direct' or r['video_id'] in done:continue
        result=verify_one(http,r,out/'stills');results.append(result)
        path.write_text(json.dumps(results,indent=2))
        print(json.dumps(result),flush=True)
    (out/'request_counts.json').write_text(json.dumps(dict(http.counts),indent=2))

if __name__=='__main__':main()
