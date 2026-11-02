#!/usr/bin/env python3
"""Deconstruct a reference video into shots and build a numbered storyboard contact sheet.

Usage:
    python3 analyze_reference.py <video> [--out DIR] [--threshold 0.18] [--title "TEXT"]

Outputs (in --out, default ./ref_analysis):
    cut_times.txt                  one cut timestamp per line (seconds)
    shots.csv                      shot_no,start,end,duration
    shots/sNN.jpg                  midpoint frame per shot (full res)
    storyboard_contact_sheet.jpg   numbered grid with in/out timecodes

Then VIEW the contact sheet and write per-shot labels/analysis manually —
scene detection finds cuts, but subject/framing/purpose require human/AI eyes.
If cuts look wrong (missed fast cuts or false positives from flash frames),
re-run with --threshold between 0.12 (sensitive) and 0.30 (strict).
"""
import argparse, csv, os, re, subprocess, sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_duration(video):
    r = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'csv=p=0', video])
    return float(r.stdout.strip())


def detect_cuts(video, out_dir, threshold):
    meta = os.path.join(out_dir, '_cuts_meta.txt')
    run(['ffmpeg', '-hide_banner', '-y', '-i', video,
         '-vf', f"select='gt(scene,{threshold})',metadata=print:file={meta}",
         '-f', 'null', '-'])
    times = []
    if os.path.exists(meta):
        with open(meta) as f:
            times = [float(m) for m in re.findall(r'pts_time:([0-9.]+)', f.read())]
    return times


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--out', default='ref_analysis')
    ap.add_argument('--threshold', type=float, default=0.18)
    ap.add_argument('--title', default='REFERENCE STORYBOARD')
    ap.add_argument('--cols', type=int, default=5)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    shots_dir = os.path.join(a.out, 'shots')
    os.makedirs(shots_dir, exist_ok=True)

    dur = probe_duration(a.video)
    cuts = [0.0] + detect_cuts(a.video, a.out, a.threshold) + [dur]
    cuts = sorted(set(round(c, 3) for c in cuts))
    # drop cuts closer than 2 frames (~0.08s) — usually detection noise
    clean = [cuts[0]]
    for c in cuts[1:]:
        if c - clean[-1] >= 0.09:
            clean.append(c)
    cuts = clean

    with open(os.path.join(a.out, 'cut_times.txt'), 'w') as f:
        f.write('\n'.join(str(c) for c in cuts[1:-1]) + '\n')

    rows = []
    for i in range(len(cuts) - 1):
        s, e = cuts[i], cuts[i + 1]
        mid = (s + e) / 2
        fp = os.path.join(shots_dir, f's{i+1:02d}.jpg')
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(mid),
             '-i', a.video, '-frames:v', '1', '-q:v', '2', fp])
        rows.append((i + 1, s, e, e - s))
    with open(os.path.join(a.out, 'shots.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['shot_no', 'start_s', 'end_s', 'duration_s'])
        for r in rows:
            w.writerow([r[0], f'{r[1]:.3f}', f'{r[2]:.3f}', f'{r[3]:.3f}'])

    # contact sheet
    from PIL import Image, ImageDraw, ImageFont
    try:
        f_big = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 17)
        f_sm = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    except OSError:
        f_big = f_sm = ImageFont.load_default()
    COLS, TW, CAP, HDR = a.cols, 384, 34, 64
    im0 = Image.open(os.path.join(shots_dir, 's01.jpg'))
    ih = int(im0.height * TW / im0.width)
    th = ih + CAP
    nrows = (len(rows) + COLS - 1) // COLS
    sheet = Image.new('RGB', (COLS * TW, nrows * th + HDR), (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    avg = dur / len(rows)
    d.text((20, 14), f'{a.title}  |  {dur:.2f}s  ·  {len(rows)} shots  ·  avg {avg:.2f}s/shot',
           fill=(232, 226, 208), font=f_big)
    for i, (no, s, e, du) in enumerate(rows):
        img = Image.open(os.path.join(shots_dir, f's{no:02d}.jpg')).resize((TW, ih))
        x, y = (i % COLS) * TW, HDR + (i // COLS) * th
        sheet.paste(img, (x, y))
        d.text((x + 8, y + ih + 4), f'#{no:02d}  {s:.2f}-{e:.2f}s  ({du:.2f}s)',
               fill=(177, 154, 85), font=f_big)
    out = os.path.join(a.out, 'storyboard_contact_sheet.jpg')
    sheet.save(out, quality=88)
    print(f'{len(rows)} shots, avg {avg:.2f}s | sheet: {out}')


if __name__ == '__main__':
    sys.exit(main())
