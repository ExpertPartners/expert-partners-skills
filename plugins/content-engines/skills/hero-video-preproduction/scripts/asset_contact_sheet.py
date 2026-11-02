#!/usr/bin/env python3
"""Build a labeled contact sheet of asset groups (images and/or video frame samples).

Usage:
    python3 asset_contact_sheet.py --out sheet.jpg \
        --group "GROUP TITLE" /path/to/imgs_dir_or_glob \
        --group "ANOTHER GROUP" "/path/*.jpg" ...

Videos in a group are sampled at start/mid/end automatically.
HEIC files are converted if pillow-heif is installed (sudo pip3 install pillow-heif).
"""
import argparse, glob, os, subprocess, sys, tempfile

VIDEO_EXT = {'.mp4', '.mov', '.m4v', '.webm', '.mkv', '.avi'}
IMG_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.tif', '.tiff', '.bmp'}


def expand(spec):
    if os.path.isdir(spec):
        return sorted(os.path.join(spec, f) for f in os.listdir(spec))
    return sorted(glob.glob(spec))


def sample_video(path, tmpdir):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', path], capture_output=True, text=True)
    try:
        dur = float(r.stdout.strip())
    except ValueError:
        return []
    outs = []
    base = os.path.splitext(os.path.basename(path))[0]
    for tag, t in [('a', 0.2), ('b', dur / 2), ('c', max(dur - 0.4, 0.3))]:
        fp = os.path.join(tmpdir, f'{base}_{tag}.jpg')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(t),
                        '-i', path, '-frames:v', '1', '-vf', 'scale=640:-1', '-q:v', '3', fp])
        if os.path.exists(fp):
            outs.append((fp, f'{os.path.basename(path)} @{t:.1f}s'))
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--title', default='EXISTING ASSET CONTACT SHEET')
    ap.add_argument('--group', nargs=2, action='append', metavar=('TITLE', 'PATHSPEC'),
                    required=True)
    a = ap.parse_args()

    from PIL import Image, ImageDraw, ImageFont
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except ImportError:
        pass
    try:
        f_hdr = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
        f_sm = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    except OSError:
        f_hdr = f_sm = ImageFont.load_default()

    tmpdir = tempfile.mkdtemp()
    groups = []
    for title, spec in a.group:
        items = []
        for f in expand(spec):
            ext = os.path.splitext(f)[1].lower()
            if ext in VIDEO_EXT:
                items += sample_video(f, tmpdir)
            elif ext in IMG_EXT:
                items.append((f, os.path.basename(f)))
        groups.append((title, items))

    COLS, TW, H, CAP = 5, 384, 220, 24
    W = COLS * TW
    total_h = 60
    for _, items in groups:
        r = (len(items) + COLS - 1) // COLS
        total_h += 44 + r * (H + CAP + 4)

    sheet = Image.new('RGB', (W, total_h), (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    d.text((20, 14), a.title, fill=(232, 226, 208), font=f_hdr)
    y = 60
    for title, items in groups:
        d.text((20, y + 10), title, fill=(177, 154, 85), font=f_hdr)
        y += 44
        for i, (fp, label) in enumerate(items):
            try:
                im = Image.open(fp)
                im.thumbnail((TW - 6, H))
            except Exception:
                continue
            x = (i % COLS) * TW
            yy = y + (i // COLS) * (H + CAP + 4)
            sheet.paste(im, (x + (TW - im.width) // 2, yy))
            d.text((x + 6, yy + H + 4), label[:52], fill=(200, 200, 200), font=f_sm)
        y += ((len(items) + COLS - 1) // COLS) * (H + CAP + 4)
    sheet.save(a.out, quality=87)
    print('saved', a.out, sheet.size)


if __name__ == '__main__':
    sys.exit(main())
