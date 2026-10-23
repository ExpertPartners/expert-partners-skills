---
classification: internal
classification_owner: allison
classification_date: 2026-09-28
date: 2026-09-28
captured_at: 2026-09-28
project: NORTH'S ESTATE CONTROL TOWER / Luxury Photo Sourcing
source: fresh instructions-only cold reader of visual-clearance at 58ba7e3, rubric withheld
topic: visual-clearance amendment behavioral cases
---
# Visual Clearance amendment, behavioral responses (fixed, verbatim)

SESSION: Luxury Photo Sourcing - Visual Clearance Build (amendment)

The reader saw only a copy of `skills/visual-clearance/` at commit `58ba7e3` (tree `abd815989ec9ae738f904c28325f5be41e2a873c`) with `tests/behavioral-rubric.md` removed, and answered the two new cases without running scripts. Response SHA-256 `b43b3bf466cc42a81f0ff38bc094c3abd358d3c4dae9462879e9db375b0c16c3`.

Grade against the rubric rows, by this worker. existing-site-record: PASS (owner record read in place at a pinned revision, no re-search, no second register, nothing promoted, preview not treated as permission, every placement checked, no edits to the website repository). undersized-derivative: PASS (PROBABLE from the owner caption, rights NOT CLEARED, all three placements fail on resolution only, the original-file ask rides REQUEST PERMISSION under rule 3's derivative clause, never USE). The earlier ten cases were graded by an independent agent in `intake/2026-09-28-visual-clearance-v1-behavior-responses.md`; this pair was graded by the worker, which is a weaker check and is labeled as such.

## Response

Case existing-site-record
1. Fires? Yes. This is clearance of website imagery for commercial use, plus a direct "is it safe to publish" question.
2. Read first: the owner's own record, ExpertPartners/ag-luxury-site docs/evidence/community-photo-candidates-2026-09-28.json, at a pinned revision, evaluated in place with evaluate_site_record.py. Before evaluating, I check that its targetCrops still match the three profiles. They do, including the 390x844 mobile crop. The shared visual-assets register is not born yet, so I report it as unborn and claim nothing about it. No re-search. I reuse the record's 23 sources, captions, contact routes and dimensions as they stand.
3. Location grade, per guide from the recorded evidence. A publisher caption naming the scene counts as one source_metadata (A) item, which makes that guide PROBABLE. A guide whose image only appears on a page (page_placement) is UNVERIFIED. None can be VERIFIED because no landmark match against an official source (C) is recorded.
4. Rights: NOT CLEARED for all 23. The basis is visible_online, or downloadable where a Realtor library applies. "No website reuse permission verified" means no grant exists, and showing in the private preview is not evidence of permission. MLS or listing images also carry an unresolved identifiable_home flag, and any image with a sign in frame carries a trademark_logo flag.
5. Fit per placement, run on observed web sizes only (dimensions_basis observed_web):
   - Directory is the largest centered 4:3 crop. It needs at least 1200x900.
   - Hero is an exact 16:9 crop. The smallest one meeting both minimums is 2134x1200, not 2000x1200. The mobile slice also needs a crop height of 844 or more to reach density 1.0.
   - Mid-guide uses the whole image when it is 3:2 or wider. It needs 2000x1300.
   - A guide that falls short on size alone gets an ask for the original file. It is not rejected for size.
6. NEXT, per guide, by the candidate-card precedence:
   - UNVERIFIED guides get REJECT under rule 2, even when a contact route is reachable.
   - PROBABLE guides get REQUEST PERMISSION under rule 4 (rights NOT CLEARED plus a recorded owner route). Each draft asks for the grant, confirmation of who shot the image, and the original-resolution file.
   - Drafts are grouped by the publisher's contact route.
7. Answer to "which are ready to publish": none. Exact-use cleared is 0 of 23. No guide can read USE until it is VERIFIED, the rights are granted, the original is measured and the visual review is recorded.
8. Human gates for Allison: sending each grouped request, final use, any license or commission spending, and the MLS home and sign decisions.
9. What I would NOT do:
   - Edit, migrate, re-status or delete anything in the ag-luxury-site repository, its branches, the preview or the deployment.
   - Copy its records into a second register.
   - Publish, or send any outreach.
   - Read the preview as permission, or upgrade PROBABLE to VERIFIED by relabeling.

Case undersized-derivative
1. Fires? Yes. It asks for evaluation of a website image for the directory, hero and mid-guide placements.
2. Read first: the ag-luxury-site record for Windsong Ranch at a pinned revision, plus the AG Luxury canon before any draft. The shared register is unborn, so it is reported as unreachable. No re-search. The developer's page is the recorded source and the owner route. I also note the known trap: the Commons category "Windsong Horse and Carriage Ranch" is a different subject.
3. Location grade: PROBABLE. The developer's own caption "The Lagoon at Windsong Ranch" is one A item, and an owner caption still does not make an image VERIFIED. Reaching VERIFIED needs a landmark match against an official Windsong Ranch source (C), which is an AI evidence task.
4. Rights: NOT CLEARED. The basis is visible_online, no permission exists, commercial use and modification are unknown, and developer media is copyrighted.
5. Fit on 1200x675, observed web:
   - Directory 4:3: the crop is 900x675 against a 1200x900 minimum. FAIL.
   - Hero 16:9: the crop is the full 1200x675 against 2134x1200 required. FAIL. The safe zone is 240,202,720x270. The mobile slice is 311x675 at x=444, density 0.80, which is below 1.0. It would need a 2.50x upscale at 2x density and 3.75x at 3x.
   - Mid-guide 3:2 or wider: the whole image, 1200x675, against 2000x1300. FAIL.
   - Every failure is resolution only.
6. NEXT: REQUEST PERMISSION to the developer's marketing team, the same for all three placements.
   - Rule 3 does not reject, because the only failure is resolution on an observed web derivative. That makes the original file an ask instead.
   - Rule 4 then selects the action: rights are NOT CLEARED and an owner route exists.
   - The draft asks for a written grant covering the three placements with crop and overlay rights. It also asks who shot the photo and whether the developer can sublicense it, and for the original-resolution file.
   - If no contact route were recorded, the action would be REJECT.
7. The card can never read USE until three things are true: the original is measured and passes, C evidence makes it VERIFIED, and the visual review is recorded.
8. Human gates for Allison: approval to send the request, final use, and any spending if the route later becomes COMMISSION.
9. What I would NOT do:
   - Reject it for size, upscale it, or place the 1200x675 file anywhere.
   - Call it VERIFIED because of the caption.
   - Substitute an AI-generated lagoon.
   - Send the request.
   - Touch the ag-luxury-site repository, its branch or its deployment.
