---
name: brand-film-reverse-engineering
description: Reverse-engineer a reference personal-brand or luxury real-estate film (About Me video, website hero video) and produce a complete adaptation package for a client, covering shot-by-shot analysis, storyboard contact sheet, transcript/cadence/narrative analyses, story substitution framework, Google Drive asset audit, gap inventories, and three production pathways, stopping at an approval gate before any script or video generation. Use when a user provides a competitor's or reference video and asks to analyze it, replicate its structure with their own story/market/footage, plan an About Me or hero film, or audit their assets against a reference.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "reverse-engineer a reference brand film"
---

# Brand Film Reverse-Engineering

Turn a reference film into a client-specific production plan. The output is a numbered deliverables package (up to 15 documents + README index), not a video: this skill ends at an **approval gate**: never write the client's script, invent their biography, or generate video/AI footage before explicit approval.

## Workflow

Work in a dedicated dir (e.g. `~/film_analysis/`) with a `deliverables/` subfolder. Full deliverable specs: `references/deliverable_specs.md`. Method details and pitfalls: `references/analysis_method.md` (read it before Steps 2 and 5).

### 1. Source verification (Deliverable 01)
ffprobe the uploaded MP4 (duration, resolution, fps). Transcribe audio with `manus-speech-to-text` and diff against any provided transcript/SRT; log every discrepancy, never silently correct. Map audio layers (music vs. voice) per segment. Check the public URL (YouTube etc.) only for title/caption context. The uploaded file is always the primary source.

### 2. Shot detection and storyboard (Deliverables 03, 14)
```bash
python3 scripts/detect_shots.py <video> <outdir>          # two-pass cut detection + frames
python3 scripts/build_contact_sheet.py <csv> <frames> <out.png> --title "..."
```
Build labeled review grids (~12 shots each), view them, and record per-shot observations into a notes file immediately (observations are lost after context compression). Verify every soft-pass candidate visually; merge fade leaders; finalize the CSV and regenerate frames before the final contact sheet. Then write the full shot list per spec, including the analytics table (avg shot length, interview vs. b-roll screen-time split, wardrobe/location counts).

### 3. Narrative analyses (Deliverables 02, 04–08)
From the word-timed STT: transcript map → chapter map (only chapters actually present; name what is deliberately absent) → sentence-function table → cadence analysis with reusable cadence template → word-visual relationship map → production-method reconstruction (evidence vs. inference, always separated).

### 4. Story substitution framework (Deliverable 09)
Map every reference chapter to the client's equivalent slot. Ground every candidate fact in documents actually located in their files; mark every unknown **REQUIRES YOUR INPUT**. Hunt for the client's "origin institution" (the unusual, uncopyable experience convertible to a client benefit in one sentence); it is the structural heart of the format.

### 5. Asset audit (Deliverable 10)
Search connected Google Drive (`scripts/drive_media_audit.py search`, then `walk <folderId>` on discovered roots; shared drives need `supportsAllDrives` params). **Never classify from filenames**: download samples, extract frames, view them. Classify each asset 1–8: use as-is / normal edit / AI enhancement / AI background replacement / motion reference / identity reference / do not use / missing. Flag AI-generated photo packs as do-not-use on screen, and note rights/privacy issues.

### 6. Gap inventories and pathways (Deliverables 11–13)
Missing-story questionnaire (chapter-grouped, vivid-answer questions + permissions section; recommend voice-memo answers). Missing-asset inventory (FILM / LICENSE / AI-FROM-OWNED / PICKUP / OPTIONAL + 3-item priority list). Three production pathways: A existing-assets-only, B minimal-shoot hybrid (usually the recommendation floor; the seated interview is non-negotiable if the reference is interview-led), C premium production. No vendor pricing without evidence.

### 7. Package and stop (Deliverables 00, 15)
Write the one-page creative summary and the README index (deliverables table + 3–5 headline findings + exactly what the client must provide next). Deliver everything, state clearly that no script/video was generated, and **wait for approval**.

## Non-negotiable rules

Never invent client biography; never claim an asset exists without locating it; never put synthetic faces/AI packs of the client on screen; AI is for invisible work on owned pixels only (upscale, reframe/outpaint, still push-ins, restoration). The luxury grammar to preserve in every adaptation: personal fact → client benefit within one breath; agent as guide not star (~20–25% presence); restraint (no CTA, no logo walls, stillness at the close).
