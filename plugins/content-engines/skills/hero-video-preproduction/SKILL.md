---
name: hero-video-preproduction
description: End-to-end pre-production workflow for website hero videos and brand films, especially luxury real estate. Use when a client provides a reference video to emulate and asks for shot-by-shot analysis, storyboard/contact sheets, an audit of their existing footage and photos, market/brand adaptation, tiered production plans (existing-only vs AI-hybrid vs premium pickup shoot), pickup-shoot call sheets, or web hero delivery specs. Covers reference deconstruction, asset classification, and approval-gated planning, everything BEFORE any video generation.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-11-02 (Decision Log 2026-10-25, Which of the 19 personal
# skills move into the marketplace). Moved in from Allison's claude.ai skills.
tier: plugin
zone: content
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "hero video plan, stops at the approval gate"
---

# Hero Video Pre-Production

Turn a reference hero video plus a client's existing asset library into an approval-ready production package: timestamped shot list, storyboard contact sheet, asset audit, adapted shot map, production options, pickup-shoot plan, and delivery specs.

## Non-negotiable rules

1. **Never generate video before explicit client approval of a shot map.** The workflow ends at an approval gate; say so in every deliverable.
2. **Never invent or assume footage the client did not provide.** Audit what exists, state where you looked, and list every gap explicitly.
3. **Adapt, don't copy.** The new film must serve the same strategic purposes as the reference without reproducing its footage, branding, or exact creative execution.
4. If the client restricts AI usage (common: "no AI faces in trust moments"), re-plan around a real-footage spine (see "C-lite" in `references/frameworks.md`).

## Workflow

### Phase 1: Reference deconstruction

1. Obtain the best copy of the reference. If given a Loom/screen capture of a website, find the production file instead (grep the page HTML for CDN mp4/webm URLs, §4 of `references/pickup-and-delivery.md`). Captures often contain more than one loop; the production file gives exact cuts.
2. Run the analysis script:
   ```bash
   python3 scripts/analyze_reference.py hero.mp4 --out ref_analysis --title "REFERENCE STORYBOARD"
   ```
   It detects cuts, exports per-shot midpoint frames, `shots.csv`, and a numbered storyboard contact sheet.
3. **View the contact sheet** and write the full shot list table plus structural metrics (fields and metrics in §1–2 of `references/frameworks.md`). Verify shot labels against the built sheet; loop start offsets differ between captures and production files.

### Phase 2: Market/brand adaptation

Read the client's brand materials (brief, bio, palette, target market) before mapping. Map every reference shot or motif group to a replacement serving the same strategic purpose in the client's market. Structure the film into a small number of "visual worlds" (3 is ideal) instead of many named locations, which avoids the tourism-montage failure. Design an original narrative spine (e.g., a descent-and-arrival arc vs the reference's carousel) and **one signature visual moment** ownable by the client's brand, ideally encoding a brand color as light. Enforce talent-usage discipline: client-specified screen share (often 20–25%), with face-forward shots limited to 2–3 trust anchors (mid-film and close).

### Phase 3: Asset audit

Inventory everything the client uploaded (cloud drives, upload folders, remote machines). Sample videos cheaply (extract start/mid/end frames rather than watching full files) and identify content before assuming relevance (supposed "listing footage" may turn out to be conference recordings). Build a visual asset sheet:

```bash
python3 scripts/asset_contact_sheet.py --out assets.jpg --title "EXISTING ASSETS" \
  --group "PROPERTY A STILLS" /path/to/dir --group "HERO VIDEO" /path/video.mp4
```

Classify every asset into the 8-class taxonomy (§3 of `references/frameworks.md`), naming which reference shot each useful asset replaces and the required work. Flag geographic-honesty risks: never present a recognizable property from another city as the target market. Restrict such assets to geographically anonymous tight details (water, fire, stone textures, twilight atmosphere).

### Phase 4: Production options

Present three tiers, A (existing footage only), B (AI-enhanced hybrid), C (premium hybrid with pickup shoot), each with final shot list, assets used, missing assets, AI tools, pickup shots, editing requirements, strengths, and realism/continuity risks (§4 of `references/frameworks.md`). Recommend one with a clear upgrade path (e.g., approve B now, book C's shoot; real footage replaces AI shots one-for-one without changing the edit structure).

### Phase 5: Shot map, pickup plan, delivery specs

Produce the approval package: final shot map with all per-shot fields (§5 of frameworks), a pickup-shoot plan scheduled backward from sunset with verbatim talent direction (§1 of `references/pickup-and-delivery.md`), the four-category sourcing matrix, and web delivery specs (durations, encode ladder, poster strategy, reduced-motion and slow-connection fallbacks, §2). **Stop and await approval.** After approval, write numbered production-ready prompts for each AI shot tied to exact source files.

## Deliverable standards

Deliver one master Markdown document (executive summary, phase sections, tables for shot lists/maps/matrices) plus the contact-sheet JPEGs with clear filenames. Include a revision-compliance table when responding to client feedback. Keep a `task_state.md` with key facts and file paths, because these projects span multiple approval rounds and context loss is likely.

## Quality bars

Reference-grade luxury pacing is 0.7–1.3s per shot, hard cuts only, rotation of ~5 motif families with no immediate repeats, and a loop seam hidden in an anonymous aerial. Apply the anti-failure QC checklist (§6 of frameworks) to every planned shot. Real footage is mandatory wherever a viewer could study the client's face.
