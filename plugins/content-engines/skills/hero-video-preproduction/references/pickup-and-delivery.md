# Pickup Shoot Planning & Web Hero Delivery Specs

## 1. Pickup shoot plan pattern (2–3 hours, one afternoon)

Assume: one property, one vehicle, one nearby outdoor/skyline vantage, two wardrobe looks, 8–12 scenes, each needing only 1–2 usable seconds in the final edit.

Rules that make the plan professional:
- **Schedule backward from sunset (S).** Interiors first (light-independent), golden-hour signature shot protected at S−0:40→S−0:20, blue-hour close at S+0:05.
- Every setup gets: shot-map #, framing, camera move, wardrobe look, props, **verbatim talent direction**, and estimated minutes.
- Shoot 16:9 masters plus native 9:16 recomposes for mobile-critical scenes (faces, signature moment); recompose on set, never salvage by cropping.
- The trust anchor (kitchen conversation) gets the most time (~25 min); direct real laughter ("land the punchline; we'll use take four or five").
- Talent direction principle: inhabitant, not presenter. Walks are purposeful ("checking the property before a showing"), eyes off lens except designated takes.
- Props: keys or slim folio, never a phone. Vehicle detailed, plate anonymized (or removed in post).
- Contingencies: flat light → shoot anyway + flag for permitted AI sky/light pass; location loss → move scene to property terrace with licensed background plate.
- Crew: one DP with mirrorless + gimbal + fast prime/zoom; 4K 23.976, 10-bit log.

## 2. Web hero delivery specification

Typical approved targets: desktop loop 18–22s (~20 shots @ ~1.05s), mobile loop 10–14s (re-selection, not center-crop; only shots with subject in center ~42% of frame).

| Rendition | Codec | Bitrate | Notes |
|---|---|---|---|
| Archival master | ProRes 422 HQ 4K 23.976 10-bit | n/a | 16:9 + native-vertical master |
| Desktop primary | HEVC 1080p | ~4.5 Mbps | Safari + supporting |
| Desktop compatible | H.264 High 1080p | ~6 Mbps (max 8) | universal fallback |
| Desktop efficient | VP9 1080p | ~3.5 Mbps | Chrome/Firefox/Edge |
| Mobile | H.264/VP9 1080×1920 | 2.2–3.5 Mbps | media query or JS swap |
| Slow-connection | H.264 720p | ~1.8 Mbps | Network Info API `effectiveType` 3g / `Save-Data: on` |

All encodes: **no audio stream at all** (guarantees autoplay), `faststart` moov atom, 1s keyframe interval, 4:2:0. `autoplay muted playsinline loop preload="metadata"` for iOS inline.

Poster strategy: frame 1 of the loop as JPEG (~120KB q78) + WebP via `poster` attribute: first paint instant, video replaces invisibly. Deliver a second "brand alternate" poster (the signature moment frame) for video-disabled pages and OG share image.

Accessibility/perf: respect `prefers-reduced-motion: reduce` (render poster + manual play affordance, never autoplay); poster must work as a complete standalone hero image.

Loop seam: hide in the most anonymous shot type (aerial); match motion vector, horizon height, exposure ±3% between last and first shot.

## 3. Useful ffmpeg one-liners

```bash
# Scene-cut detection (threshold 0.12 sensitive → 0.30 strict)
ffmpeg -i in.mp4 -vf "select='gt(scene,0.18)',metadata=print:file=cuts.txt" -f null -

# Web encode ladder examples
ffmpeg -i master.mov -c:v libx264 -profile:v high -b:v 6M -maxrate 8M -bufsize 12M \
  -g 24 -pix_fmt yuv420p -an -movflags +faststart hero_h264_1080.mp4
ffmpeg -i master.mov -c:v libx265 -b:v 4.5M -g 24 -pix_fmt yuv420p -an \
  -tag:v hvc1 -movflags +faststart hero_hevc_1080.mp4
ffmpeg -i master.mov -c:v libvpx-vp9 -b:v 3.5M -g 24 -an hero_vp9_1080.webm

# Poster frame
ffmpeg -ss 0 -i hero.mp4 -frames:v 1 -q:v 3 poster.jpg
```

## 4. Finding the real hero file on a reference website

Screen captures (Loom) degrade analysis. Fetch the page HTML and grep for the actual asset; most luxury real estate sites serve heroes from a CDN:

```bash
curl -s "https://site.com/" -H "User-Agent: Mozilla/5.0" | grep -oE 'https?://[^"]*\.(mp4|webm|m3u8)[^"]*'
```

Common hosts: res.cloudinary.com (Luxury Presence sites use `/luxuryp/videos/...`), player.vimeo.com, wistia. Prefer the production file for frame-accurate cut detection; use the capture only as fallback.
