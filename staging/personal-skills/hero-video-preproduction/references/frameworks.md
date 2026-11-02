# Frameworks: Shot List, Asset Audit, Production Options, Shot Map

## 1. Per-shot documentation fields (Phase 1 shot list table)

Document every shot with these columns. Timecodes come from `analyze_reference.py`; everything else requires viewing the storyboard contact sheet (and grids if needed).

| Field | Notes |
|---|---|
| # / In–Out / Duration | From shots.csv |
| Subject | What/who is in frame |
| Setting | Location type, not address |
| Framing | EW/W/M/MCU/CU, symmetry, fg layers |
| Angle | Low / eye / high / aerial / top-down |
| Camera move | Push, drift, lateral dolly, track, static; estimate % travel |
| Subject move | Walk direction, gesture, none |
| Light / time of day | Key direction, golden hour, twilight, window-driven |
| Palette & grade | Dominant colors, warmth, shadow lift |
| Speed | Normal / slow-mo / ramp |
| Transition in/out | Almost always hard cuts in luxury heroes; note any exception |
| Beat role | Position in the short-short-long rhythmic phrasing |
| Strategic purpose | What the shot sells (authority, access, trust, lifestyle) |
| Luxury signal | Why it reads expensive |

## 2. Structural metrics to extract from any reference hero

- Total loop duration, shot count, average shot length (luxury heroes: ~0.7–1.3s/shot).
- Loop seam location and disguise method (usually hidden in an anonymous aerial: matched motion vector, horizon height, exposure).
- Motif families and rotation rule (typical five: aerial geography, arrival/threshold, editorial interior, talent-as-inhabitant, land/water lifestyle; strong films never repeat a motif twice in a row).
- Talent economics: shots containing talent vs face-forward vs speaking; wardrobe changes as chapter markers.
- Rhythmic phrasing: short-short-long breathing pattern; count it.

## 3. Asset audit taxonomy (8 classes)

1. Use exactly as-is
2. Use after normal editing / color correction
3. Use after AI enhancement (upscale, still→motion animation)
4. Use after AI background/location replacement
5. Use as motion reference for an AI-generated shot
6. Use as identity/character reference
7. Do not use
8. Missing — must be licensed, generated, or filmed

For each useful asset record: what it is, class, which reference shot(s) it can replace, and required work. **Never invent footage the client did not provide; list every gap explicitly as Class 8.** State where you looked and what was not found.

Sourcing matrix (client-facing rollup of classes): **Must be filmed / Should be licensed / Can be created from existing assets with AI / Optional enhancements.**

## 4. Three production options (Phase 4)

- **Option A — Existing footage only:** conventional edit of owned assets. Usually a "photo-cinema" piece. Honest about what pillars it cannot fulfill.
- **Option B — AI-enhanced hybrid:** image-to-video on owned stills (Kling-class for architectural stability), talent shots via character-reference models (Higgsfield-class), environments (Runway-class), licensed clips only where landmark geometry must be accurate (skylines resist AI scrutiny).
- **Option C — Premium hybrid:** B plus a short targeted pickup shoot for all facial trust moments and signature shots.

For each option provide: final shot list, assets used, missing assets, AI tools, pickup shots, editing requirements, strengths, realism/continuity risks. Common client revision: **"C-lite"** — real footage mandatory for every face-forward trust moment; AI restricted to still animation, environmental enhancement, object removal, sky replacement, shot extension, non-identifiable transitions, and distant/back-view talent only as fallback.

## 5. Final shot map fields (for approval)

Per shot: duration, visual world/act, talent presence (none/back/distant/face), source (REAL pickup / LIC licensed / AI-EX from named existing asset / AI-EN enhancement), exact existing asset filename when applicable, mobile suitability (survives 9:16 center crop?), and why the shot earns its place.

## 6. Anti-failure QC checklist (every generated/edited shot)

Straight verticals on architecture (no AI bowing); consistent sun direction within a property suite; no duplicated windows/mullions; believable water/foliage motion speed (AI over-animates); talent faces only in filmed or single-source shots; no shot >1.4s except designated anchors; loop watched 5x by a fresh viewer who cannot find the seam.
