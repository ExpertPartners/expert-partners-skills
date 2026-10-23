#!/usr/bin/env python3
"""Optional partial-media verification: bounded HTTP Range + offline first-frame decode.

Never reads a full video. Requires an existing catalog and ffmpeg; shares the saved
request budget and blocking state. Does not establish end-to-end player playback.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import requests
from video_discovery import Fetch, Investigation, Record, classify, domain, now, request_delay


def valid_range(headers, requested):
    match=re.fullmatch(r'bytes 0-(\d+)/(\d+)',headers.get('content-range',''))
    if not match:return False
    end,total=map(int,match.groups())
    return end==requested-1 and total>requested*2


def sample(http,url,size):
    if not http.public_url(url):return None,'unsafe_or_unresolvable_url'
    d=domain(url)
    if d in http.stopped:return None,'domain_stopped'
    ok,why=http.allowed(url)
    if not ok:return None,why
    for attempt in range(2):
        if d in http.stopped:return None,'domain_stopped'
        if http.counts[d]>=http.limit:return None,'budget_exhausted'
        time.sleep(max(0,request_delay(http,url)-(time.monotonic()-http.last.get(d,0))))
        http.counts[d]+=1;http.last[d]=time.monotonic()
        try:
            http.session.cookies.clear()
            with http.session.get(url,headers={'Range':f'bytes=0-{size-1}','Accept-Encoding':'identity'},timeout=http.timeout,stream=True,allow_redirects=False) as resp:
                headers={k.lower():v for k,v in resp.headers.items() if k.lower() in {'content-type','content-range','content-length','content-encoding'}}
                if resp.status_code in {401,403,429,451}:
                    http.stopped[d]='blocking response during range probe'
                    http.record(Fetch(url,'blocked',resp.status_code,headers=headers),'GET_RANGE')
                    return None,'blocked'
                if resp.status_code>=500:
                    http.record(Fetch(url,'transient_failure',resp.status_code,headers=headers),'GET_RANGE')
                    if attempt==0:continue
                    return None,'transient_failure'
                # A server that ignores Range is closed before any body read.
                if resp.status_code!=206 or not valid_range(headers,size) or headers.get('content-encoding','identity')!='identity':
                    http.record(Fetch(url,'range_not_honored_body_not_read',resp.status_code,headers=headers),'GET_RANGE')
                    return None,'range_not_honored_body_not_read'
                body=resp.raw.read(size,decode_content=False)
                http.record(Fetch(url,'partial_media_sample',resp.status_code,headers=headers),'GET_RANGE',f'{len(body)} bytes; sha256={hashlib.sha256(body).hexdigest()}')
                return body,'partial_media_sample'
        except requests.RequestException as exc:
            blocked=bool(re.search(r'\b(?:401|403|429|451)\b',str(exc)))
            result='blocked' if blocked else 'network_error'
            if blocked:http.stopped[d]='network block during range probe'
            http.record(Fetch(url,result),'GET_RANGE',str(exc)[:300])
            if blocked or attempt==1:return None,result
    return None,'network_error'


def decode_frame(body):
    if not shutil.which('ffmpeg'):return False,'ffmpeg unavailable'
    try:
        proc=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-protocol_whitelist','pipe',
                             '-i','pipe:0','-map','0:v:0','-frames:v','1','-f','null','-',
                             '-progress','pipe:1'],input=body,capture_output=True,timeout=20)
        progress=proc.stdout.decode(errors='replace')
        frames=[int(n) for n in re.findall(r'^frame=(\d+)$',progress,re.M)]
        return bool(frames and max(frames)>0),proc.stderr.decode(errors='replace')[-500:]
    except (OSError,subprocess.TimeoutExpired) as exc:return False,str(exc)[:300]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path);p.add_argument('--max-bytes',type=int,default=524288)
    args=p.parse_args()
    data=json.loads((args.output/'catalog.json').read_text())
    config=data['configuration'];config['resume']=True;config['output']=str(args.output)
    inv=Investigation(argparse.Namespace(**config))
    inv.notes=data['notes'];inv.page_titles=data['page_titles']
    for raw in data['records']:
        r=Record(**raw);inv.catalog.records[(r.platform,r.video_id)]=r
        if r.platform!='direct' or any(c.get('method')=='range_decode' for c in r.checks):continue
        head=next((c for c in reversed(r.checks) if c.get('method')=='media_head' and c.get('result')=='media_endpoint_accessible'),None)
        if not head:continue
        try:total=int(head.get('headers',{}).get('content-length','0'))
        except ValueError:total=0
        size=min(max(1024,args.max_bytes),524288,total//4)
        if size<16384:continue
        body,result=sample(inv.http,r.url,size)
        decoded,detail=decode_frame(body) if body else (False,'')
        check=dict(time=now(),source=r.url,method='range_decode',result='sample_frame_decoded' if decoded else result,
                   bytes_read=len(body or b''),maximum_bytes=size,detail=detail)
        r.checks.append(check)
        if decoded:r.playback='one_frame_decoded_full_playback_unverified'
        r.accessibility=classify(r.checks,bool(r.metadata))
        print(r.video_id,check['result'],check['bytes_read'],flush=True)
    inv.notes.append(dict(source='partial_media_probe',result='completed',scope='Up to 512 KiB and at most one quarter of each direct media file. HTTP 206 and total size required; full files never read. ffmpeg has only the pipe protocol. A decoded frame proves partial media decoding, not full or browser playback.'))
    inv.export()

if __name__=='__main__':main()
