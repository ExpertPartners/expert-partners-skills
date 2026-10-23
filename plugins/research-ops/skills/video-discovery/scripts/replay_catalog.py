#!/usr/bin/env python3
"""Re-extract a completed investigation from saved evidence with no network calls."""
import argparse
import json
from pathlib import Path
from video_discovery import Investigation, classify

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    old=json.loads((args.output/'catalog.json').read_text())
    if any(r.get('verification_checked_at') for r in old['records']):
        raise SystemExit('This catalog has a subsequent verification pass. Replay a separate baseline copy to avoid replacing verification evidence.')
    config=old['configuration'];config['resume']=True;config['output']=str(args.output)
    inv=Investigation(argparse.Namespace(**config));inv.http.offline=True
    inv.run()
    for raw in old["records"]:
        record=inv.catalog.records.get((raw["platform"],raw["video_id"]))
        if record:
            checks=[c for c in raw["checks"] if c.get("method")=="range_decode"]
            record.checks.extend(checks)
            if checks:record.playback=raw["playback"]
            record.accessibility=classify(record.checks,bool(record.metadata))
    # Record parser replay independently of the network evidence.
    inv.notes.append({'source':'offline_replay','result':'completed','reason':'Re-extracted saved live HTTP responses with corrected malformed/serialized URL handling. No new network requests. Original request audit remains intact.'})
    inv.export()

if __name__=='__main__':main()
