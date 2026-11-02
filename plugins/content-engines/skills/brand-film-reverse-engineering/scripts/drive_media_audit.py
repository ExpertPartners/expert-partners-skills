#!/usr/bin/env python3
"""Inventory media assets in Google Drive for the asset-audit phase (requires gws CLI).

Usage:
    python3 drive_media_audit.py search              # keyword sweep, prints hits
    python3 drive_media_audit.py walk <folderId>...  # recursive tree of given roots

Search mode sweeps the query families that reliably surface personal-brand media:
video mimetypes, headshot/lifestyle/brand folder names, drone/aerial/skyline,
speaking/event/award, bio/brief docs. Walk mode maps discovered folder roots.

After locating candidates: download samples with
    gws drive files get --params '{"fileId": "<ID>", "alt": "media"}' --output <file>
then extract frames and VIEW them before classifying anything. Never classify an
asset from its filename alone.
"""
import json
import subprocess
import sys

SEARCH_QUERIES = [
    "mimeType contains 'video'",
    "name contains 'headshot'",
    "name contains 'lifestyle'",
    "name contains 'brand'",
    "name contains 'logo'",
    "name contains 'drone' or name contains 'aerial' or name contains 'skyline'",
    "name contains 'speaking' or name contains 'keynote' or name contains 'event'",
    "name contains 'award' or name contains 'press' or name contains 'forbes'",
    "name contains 'bio' or name contains 'brief'",
    "name contains 'family' or name contains 'archive'",
]


def gws_list(q):
    r = subprocess.run(
        ['gws', 'drive', 'files', 'list', '--params',
         json.dumps({'pageSize': 200, 'q': f'trashed=false and ({q})',
                     'fields': 'files(id,name,mimeType,size,parents,modifiedTime)'}),
         '--page-all'],
        capture_output=True, text=True)
    files = []
    for line in r.stdout.strip().splitlines():
        line = line.strip()
        if line.startswith('{'):
            try:
                files.extend(json.loads(line).get('files', []))
            except json.JSONDecodeError:
                pass
    return files


def fmt(f, depth=0):
    size = f.get('size')
    sz = f' ({int(size) / 1e6:.1f}MB)' if size else ''
    kind = 'DIR ' if f['mimeType'].endswith('folder') else '    '
    return f"{'  ' * depth}{kind}{f['name']}{sz}  [{f['mimeType']}]  id={f['id']}"


def walk(folder_id, depth=0, max_depth=4):
    if depth > max_depth:
        return
    for f in gws_list(f"'{folder_id}' in parents"):
        print(fmt(f, depth))
        if f['mimeType'].endswith('folder'):
            walk(f['id'], depth + 1, max_depth)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('search', 'walk'):
        print(__doc__)
        return 1
    if sys.argv[1] == 'search':
        for q in SEARCH_QUERIES:
            hits = gws_list(q)
            print(f"\n=== {q} === ({len(hits)} hits)")
            for f in hits[:60]:
                print(fmt(f))
    else:
        for root in sys.argv[2:]:
            print('=' * 80)
            print('ROOT:', root)
            walk(root)
    return 0


if __name__ == '__main__':
    sys.exit(main())
