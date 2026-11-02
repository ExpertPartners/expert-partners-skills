#!/usr/bin/env python3
"""Build a numbered storyboard contact sheet from a finalized shots CSV.

Usage:
    python3 build_contact_sheet.py <shots.csv> <frames_dir> <output.png> --title "TITLE"

<shots.csv> columns: shot,start,end,dur  (the FINAL, manually verified list —
merge fade leaders / delete false positives before running this).
<frames_dir> must contain one image per shot; files are matched by sorted order,
so regenerate frames after any merge so counts align (assert will catch drift).

Also useful for REVIEW sheets during analysis: run it on the raw CSV first,
view the sheet in batches of ~12 shots, and record observations per shot before
finalizing. Small labeled grids beat viewing 60 frames one at a time.
"""
import argparse
import csv
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def tc(s):
    m = int(s // 60)
    return f'{m}:{s - 60 * m:05.2f}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv_path')
    ap.add_argument('frames_dir')
    ap.add_argument('output')
    ap.add_argument('--title', default='STORYBOARD CONTACT SHEET')
    ap.add_argument('--cols', type=int, default=5)
    args = ap.parse_args()

    shots = list(csv.DictReader(open(args.csv_path)))
    files = sorted(f for f in os.listdir(args.frames_dir)
                   if f.lower().endswith(('.png', '.jpg', '.jpeg')))
    assert len(shots) == len(files), (
        f'{len(shots)} shots in CSV but {len(files)} frames in {args.frames_dir}')

    font = ImageFont.truetype(FONT_BOLD, 26)
    font_sm = ImageFont.truetype(FONT_REG, 20)
    title_font = ImageFont.truetype(FONT_BOLD, 34)

    cols, tw, th, lh = args.cols, 480, 270, 62
    rows = (len(shots) + cols - 1) // cols
    W = cols * tw + (cols + 1) * 12
    H = rows * (th + lh + 12) + 90
    sheet = Image.new('RGB', (W, H), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    d.text((16, 20), args.title, fill=(240, 240, 240), font=title_font)

    for j, (s, fname) in enumerate(zip(shots, files)):
        x = 12 + (j % cols) * (tw + 12)
        y = 90 + (j // cols) * (th + lh + 12)
        im = Image.open(os.path.join(args.frames_dir, fname))
        im.thumbnail((tw, th * 2))
        # letterbox non-16:9 frames (e.g. vertical) instead of distorting
        cell = Image.new('RGB', (tw, th), (8, 8, 8))
        cell.paste(im, ((tw - im.width) // 2, max(0, (th - im.height) // 2)))
        sheet.paste(cell, (x, y))
        start, end = float(s['start']), float(s['end'])
        d.text((x + 4, y + th + 4), f"SHOT {int(s['shot']):02d}",
               fill=(255, 215, 130), font=font)
        d.text((x + 4, y + th + 34),
               f'{tc(start)} \u2192 {tc(end)}   ({end - start:.1f}s)',
               fill=(220, 220, 220), font=font_sm)

    sheet.save(args.output)
    print('saved', args.output, sheet.size)


if __name__ == '__main__':
    sys.exit(main())
