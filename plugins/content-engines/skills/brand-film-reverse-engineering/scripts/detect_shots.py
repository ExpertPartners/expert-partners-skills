#!/usr/bin/env python3
"""Detect cuts in a reference video and extract one representative frame per shot.

Usage:
    python3 detect_shots.py <video> <outdir> [--threshold 0.25] [--soft-threshold 0.12]

Outputs in <outdir>:
    shots_raw.csv          shot,start,end,dur (seconds, from hard-threshold pass)
    soft_cuts.txt          extra candidate boundaries from the low-threshold pass
                           (review these manually: dissolves, whip pans, in-shot motion)
    frames/shotNN_<t>.png  representative mid-shot frame per detected shot
    frames_start_end/      first+last frames of each shot (transition verification)

Workflow notes:
- Run BOTH passes. The hard pass (default 0.25) gives the shot list skeleton; the
  soft pass (0.12) catches dissolves and soft cuts the hard pass misses. Every
  disagreement between the two passes must be verified visually before the shot
  list is final (false positives: camera whips, flash frames, subject movement).
- A fade-from-black opening often registers as a separate 0.3-1s "shot"; merge it
  into the first real shot during manual review.
"""
import argparse
import csv
import os
import re
import subprocess
import sys


def ffprobe_duration(video):
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=nw=1:nk=1', video],
        capture_output=True, text=True)
    return float(r.stdout.strip())


def detect_cuts(video, threshold):
    """Return sorted list of cut timestamps (seconds) via ffmpeg scdet/select."""
    r = subprocess.run(
        ['ffmpeg', '-i', video, '-vf',
         f"select='gt(scene,{threshold})',showinfo", '-f', 'null', '-'],
        capture_output=True, text=True)
    times = []
    for m in re.finditer(r'pts_time:([0-9.]+)', r.stderr):
        times.append(float(m.group(1)))
    return sorted(set(times))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('outdir')
    ap.add_argument('--threshold', type=float, default=0.25)
    ap.add_argument('--soft-threshold', type=float, default=0.12)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    frames_dir = os.path.join(args.outdir, 'frames')
    se_dir = os.path.join(args.outdir, 'frames_start_end')
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(se_dir, exist_ok=True)

    dur = ffprobe_duration(args.video)
    hard = detect_cuts(args.video, args.threshold)
    soft = detect_cuts(args.video, args.soft_threshold)

    bounds = [0.0] + hard + [dur]
    shots = [(i + 1, bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)
             if bounds[i + 1] - bounds[i] > 0.15]

    with open(os.path.join(args.outdir, 'shots_raw.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['shot', 'start', 'end', 'dur'])
        for n, s, e in shots:
            w.writerow([n, f'{s:.2f}', f'{e:.2f}', f'{e - s:.2f}'])

    extra = [t for t in soft if all(abs(t - h) > 0.25 for h in hard)]
    with open(os.path.join(args.outdir, 'soft_cuts.txt'), 'w') as f:
        f.write('\n'.join(f'{t:.2f}' for t in extra) + '\n')

    for n, s, e in shots:
        mid = (s + e) / 2
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{mid:.3f}', '-i', args.video,
                        '-frames:v', '1', '-vf', 'scale=640:-1',
                        os.path.join(frames_dir, f'shot{n:02d}_{mid:.2f}.png'), '-y'])
        for tag, t in (('a', s + 0.08), ('b', max(s, e - 0.12))):
            subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', args.video,
                            '-frames:v', '1', '-vf', 'scale=480:-1',
                            os.path.join(se_dir, f'shot{n:02d}{tag}_{t:.2f}.png'), '-y'])

    print(f'duration={dur:.2f}s  shots={len(shots)}  '
          f'soft-only candidates={len(extra)} (see soft_cuts.txt)')


if __name__ == '__main__':
    sys.exit(main())
