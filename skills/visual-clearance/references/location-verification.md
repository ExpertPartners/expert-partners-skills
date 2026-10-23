---
classification: internal
classification_owner: allison
classification_date: 2026-09-28
date: 2026-09-28
source: Visual Clearance v1 dispatch; AI-Assisted Visual Asset Sourcing research report 2026-09-28 (evidence, not authority)
topic: visual-clearance location verification protocol
---

# Location verification

A named-place page may use only VERIFIED imagery. The grade comes from evidence the skill has recorded, never from what a search result, filename, uploader or model says the image shows. `scripts/clearance_rules.py grade_location` implements this ladder; this page explains it.

## Evidence ladder

Record each item with a short detail and, where one exists, a pointer (source page URL, Drive capture, map link viewed). An item with neither does not count.

| Code | Evidence type (`type` value) | Examples |
| --- | --- | --- |
| A | `source_metadata` | Original uploader or photographer title, caption and categories on the source landing page |
| B | `embedded_gps` | EXIF GPS and capture date from `inspect_image.py` (usually stripped on stock, often kept on Commons) |
| C | `landmark_match_official` | Monument sign text, water tower, amenity center or entry matched against the official community, developer or city source |
| D | `map_corroboration` | View compared against satellite or street-level imagery, viewing only, never copied |
| E | `independent_corroboration` | A developer, city or news photo of the same structure |
| F | `reverse_image_earliest` | Reverse image search finding the earliest source, mislabeling or a different original owner |
| none | `search_label`, `ai_inference`, `page_placement` | Recorded for transparency, worth nothing as evidence. `page_placement` is an image merely appearing on a neighborhood, agent or developer page without a caption naming the scene |
| stop | `contradiction` | Anything showing the image depicts somewhere else |

## Grades

- VERIFIED: a landmark match against an official source (C) plus at least one independent confirmation (A, D or E).
- PROBABLE: at least one credible item (A, B, C, D or E) without that independent pairing.
- UNVERIFIED: only a search label, the AI's own claim, or nothing.
- REJECT: any recorded contradiction, whatever else is recorded.

## Rules

- Grades rise only when new evidence is recorded. A claimed grade above what the evidence supports is flagged as a grade violation and the computed grade stands.
- A caption from the community's own owner (developer, HOA, official site) is still one A item. It makes an image PROBABLE, not VERIFIED.
- PROBABLE is not VERIFIED. It can support a generic or secondary use; it cannot carry a named-place page.
- Reverse image results (F) protect provenance and ownership; they do not by themselves locate the image.
- Map and street-level imagery is for viewing during verification. It is never downloaded, stored or used as a candidate (Mapillary under CC BY-SA is the one downloadable exception, as evidence only).
- Flag currency when the capture date is unknown or more than about three years old, because communities change.
- An edited image keeps its original's grade only while the edit does not alter identifying features.

## Known traps from the 2026-09-28 benchmark

- Newman Village, Frisco: a separate Newman Village apartment complex (newmanfrisco.com) returns for the same words. Label matching fails here.
- Windsong Ranch, Prosper: the Commons category "Windsong Horse and Carriage Ranch" is a different subject.
- Fields, Frisco: "Fields pond frisco.jpg" carries only a filename claim and an October 2019 date that may predate the community. UNVERIFIED.
- Light Farms, Celina: three Commons images carry a real title and category (A). The official monument or water tower match (C) is still owed before any of them can read VERIFIED.
