---
classification: internal
classification_owner: allison
classification_date: 2026-09-28
date: 2026-09-28
source: Visual Clearance v1 dispatch; AI-Assisted Visual Asset Sourcing research report 2026-09-28 (evidence, not authority; vendor terms as checked that day)
topic: visual-clearance rights clearance protocol
---

# Rights clearance

The only status that permits USE is exact-use clearance: a valid basis for the exact intended use, plus a VERIFIED identity when a place is named, plus resolved third-party concerns, plus met license conditions. `clearance_rules.evaluate_rights` computes the rights half (`RIGHTS CLEAR`, `NOT CLEARED` or `NEEDS HUMAN DECISION`); `decide` computes exact-use clearance. Every output is a risk assessment on recorded evidence, never legal advice or legal certainty. Edge cases go to Allison, and to counsel when she decides they need it.

## Rights bases stay distinct

| Basis (`rights.basis`) | What it actually means |
| --- | --- |
| `visible_online` | Grants no rights at all |
| `downloadable` | Describes access, not permission |
| `royalty_free` | Pay once or nothing, still under a license with restrictions |
| `creative_commons` | A family of licenses. NC forbids commercial use, ND forbids adaptation, BY requires attribution, SA requires adaptations to carry the same license |
| `public_domain` | No copyright restriction; trademark, privacy and property concerns still apply |
| `free_commercial_platform` | A platform license claim (Unsplash, Pexels, Pixabay), only as good as the uploader's ownership |
| `paid_commercial_license` | A purchased license whose scope is its terms (standard vs extended, editorial vs creative) |
| `written_permission` | A direct grant from the owner with recorded scope, credit terms and expiry |
| `owned_or_work_for_hire` | Commissioned or owned work under a written license or work-for-hire grant |

Exact-use clearance is computed, never entered. Never collapse "free to download" or "royalty-free" into "cleared".

## Conditions and failures

- Commercial use must be evidenced as allowed. NC, unknown or editorial-only fails commercial use.
- Planned crop, overlay or heading text needs evidenced modification rights. ND fails it.
- ShareAlike with modification: tolerable on a website with a visible credit line, flagged always. In advertising or print it is an edge case for Allison.
- Per-design licenses (Canva Pro content) cannot become standalone library assets. Hotlink-only API terms cannot put a master in the register. Single-seat or no-DAM terms (Unsplash+) conflict with a shared library and go to Allison.
- Paid and permission bases need recorded scope covering this exact use. Every basis except the no-rights ones needs a durable license or permission evidence pointer.
- Expired permission fails.
- Attribution required means attribution text is recorded (the renderer composes "Photo: creator, license, via source" when creator and license are known). Attribution never cures any failure above.

## Third-party concerns that survive any license

- Recognizable people need releases for advertising. Texas has statutory post-mortem publicity rights and common-law misappropriation for living people.
- Community logos and monument signs are trademarks and can imply endorsement, which Pexels, Pixabay and Canva terms prohibit. Prefer compositions that leave them out.
- Identifiable private homes raise privacy and implied-endorsement concerns.
- Architectural works: 17 U.S.C. section 120 permits pictures of buildings visible from public places; other architectural concerns go to review.
- Artwork, personal property and security features in frame are flagged.

## Source classes with standing answers

- MLS and listing photography is its own rights class. MLS access is not copyright. Reuse requires Allison's own listing, a photographer license covering the use, and seller consent for use outside the active listing. The VHT v. Zillow decisions (9th Cir. 2019, 2023) are the standing caution.
- Google Maps, Earth and Street View imagery may not be stored or republished. Viewing for verification only.
- Social media images are licensed to the platform, not to the Estate. Use them only as a lead to the photographer.
- Texas city media is not automatically public domain. Tourism bureau and press-kit media is usually editorial or partner-only. Developer, HOA and builder media is copyrighted; HOAs often do not own their photos, so confirm the photographer.
- US federal works (USGS, NASA, LOC) are generally public domain; check for embedded third-party material.
- Getty and Canva terms prohibit AI/ML use of licensed content. Run vision analysis only on candidate previews and never train on licensed files.

## Re-verify terms live

Vendor terms change. Before relying on a vendor summary above, re-read the vendor's current license page, capture it to Drive, and record that capture as the `license_evidence_pointer`. Openverse and other aggregators can carry stale or wrong license metadata; always confirm on the original landing page.
