#!/usr/bin/env bash
# video-transcript-relay: fetch and clean a video transcript
# Usage: ./fetch_transcript.sh "<video URL>" [output_dir]
# Prints: metadata summary, then the paths of the cleaned transcript and JSON sidecar.
# Exit 0 = transcript produced. Exit 3 = no subtitle track exists (caller falls back to whisper).

set -euo pipefail

URL="${1:-}"
OUTDIR="${2:-$HOME/Claude/transcripts}"

if [[ -z "$URL" ]]; then
  echo "Usage: $0 \"<video URL>\" [output_dir]" >&2
  exit 1
fi

command -v yt-dlp >/dev/null 2>&1 || {
  echo "yt-dlp not found. Install with: pipx install yt-dlp   (or) brew install yt-dlp" >&2
  exit 1
}

mkdir -p "$OUTDIR"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "Reading video metadata..."
META_JSON="$WORK/meta.json"
yt-dlp --no-warnings --skip-download --dump-single-json "$URL" > "$META_JSON"

read_meta() {
  python3 -c "
import json,sys
d=json.load(open('$META_JSON'))
v=d.get('$1') or ''
print(v)
"
}

TITLE="$(read_meta title)"
CHANNEL="$(read_meta uploader)"
UPLOAD_DATE="$(read_meta upload_date)"
DURATION="$(read_meta duration_string)"
VIDEO_ID="$(read_meta id)"

# Date prefix uses today, per the document formatting standard filename rule.
TODAY="$(date +%Y-%m-%d)"

# Sanitize for a filesystem-safe basename while keeping it human readable.
safe() { printf '%s' "$1" | tr '/:' '--' | tr -s ' ' ' ' | cut -c1-90; }
BASE="$TODAY $(safe "$CHANNEL") - $(safe "$TITLE") transcript"

echo "  Title:    $TITLE"
echo "  Channel:  $CHANNEL"
echo "  Uploaded: $UPLOAD_DATE"
echo "  Duration: $DURATION"

# Subtitle priority: manual en, manual any, auto en, auto any.
CAPTION_TYPE=""
fetch_subs() {
  local mode="$1" langs="$2"
  local flag="--write-subs"
  [[ "$mode" == "auto" ]] && flag="--write-auto-subs"
  yt-dlp --no-warnings --skip-download $flag \
    --sub-langs "$langs" --sub-format "vtt/best" \
    -o "$WORK/sub.%(ext)s" "$URL" >/dev/null 2>&1 || true
  compgen -G "$WORK/sub*.vtt" >/dev/null 2>&1
}

if   fetch_subs manual "en.*,en"; then CAPTION_TYPE="manual (English)"
elif fetch_subs manual "all";     then CAPTION_TYPE="manual (non-English)"
elif fetch_subs auto   "en.*,en"; then CAPTION_TYPE="auto-generated (English)"
elif fetch_subs auto   "all";     then CAPTION_TYPE="auto-generated (non-English)"
else
  echo "NO SUBTITLE TRACK of any kind is available for this video." >&2
  echo "Fall back to the audio path: download bestaudio and transcribe with whisper." >&2
  exit 3
fi

VTT="$(compgen -G "$WORK/sub*.vtt" | head -1)"
echo "  Captions: $CAPTION_TYPE"

TXT="$OUTDIR/$BASE.txt"
SIDECAR="$OUTDIR/$BASE.json"

# Clean the VTT: drop headers, cue numbers, timestamps, positioning and inline tags,
# de-duplicate the rolling repeated lines auto-captions emit, then reflow to paragraphs.
python3 - "$VTT" "$TXT" <<'PY'
import html, re, sys

src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8", errors="replace") as f:
    raw = f.read()

lines, seen_tail = [], []
for line in raw.splitlines():
    s = line.strip()
    if not s:
        continue
    if s.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE", "REGION")):
        continue
    if "-->" in s:
        continue
    if re.fullmatch(r"\d+", s):
        continue
    s = re.sub(r"<[^>]+>", "", s)                 # inline and karaoke timing tags
    s = re.sub(r"align:\S+|position:\S+", "", s)  # stray cue settings
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        continue
    # YouTube VTTs carry text as HTML entities; decode so ">>" etc. survive as text.
    s = html.unescape(s)
    # Non-speech noise tags: [music], [applause], [laughter], and () variants.
    s = re.sub(r"[\[(](?:music|applause|laughter|cheering|silence)[\])]", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        continue
    # Auto-captions repeat the rolling window; skip anything already just emitted.
    if s in seen_tail:
        continue
    seen_tail.append(s)
    if len(seen_tail) > 6:
        seen_tail.pop(0)
    lines.append(s)

text = " ".join(lines)
text = re.sub(r"\s+", " ", text).strip()
# Reflow into readable paragraphs at sentence boundaries, roughly 4 sentences each.
sentences = re.split(r"(?<=[.!?])\s+", text)
paras, buf = [], []
for sent in sentences:
    buf.append(sent)
    if len(buf) >= 4:
        paras.append(" ".join(buf)); buf = []
if buf:
    paras.append(" ".join(buf))

out = "\n\n".join(paras) if paras else text
with open(dst, "w", encoding="utf-8") as f:
    f.write(out + "\n")

print(len(out.split()))
PY

WORDS="$(wc -w < "$TXT" | tr -d ' ')"

python3 - "$SIDECAR" "$TITLE" "$CHANNEL" "$UPLOAD_DATE" "$DURATION" "$VIDEO_ID" "$URL" "$CAPTION_TYPE" "$WORDS" "$TXT" <<'PY'
import json, sys
p = sys.argv
json.dump({
    "title": p[2], "channel": p[3], "upload_date": p[4], "duration": p[5],
    "video_id": p[6], "url": p[7], "caption_type": p[8],
    "word_count": int(p[9]), "transcript_path": p[10],
    "drive_folder": "Video Transcripts",
}, open(p[1], "w", encoding="utf-8"), indent=2)
PY

echo ""
echo "  Words:    $WORDS"
echo ""
echo "TRANSCRIPT: $TXT"
echo "SIDECAR:    $SIDECAR"
echo ""
echo "Next: upload the transcript to Google Drive folder \"Video Transcripts\" via the"
echo "SA plus DWD path impersonating allison@expertpartners.com, then report the file ID and link."
