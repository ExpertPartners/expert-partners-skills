---
classification: internal
classification_owner: allison
classification_date: 2026-09-28
date: 2026-09-28
captured_at: 2026-09-28
project: NORTH'S ESTATE CONTROL TOWER / Luxury Photo Sourcing
source: visual-clearance evaluate_site_record.py over the AG Luxury website's own candidate record, read in place
topic: visual-clearance first real intake, AG Luxury website community photo record
---
# Visual Clearance first real intake: AG Luxury website photo record

SESSION: Luxury Photo Sourcing - Visual Clearance Build (amendment)

This is a dated evaluation of another owner's record, kept as evidence. It is not a register, grants nothing, changes no status in the owner's files, and is superseded by the owner's record whenever the two differ.

## Source revision read

`ExpertPartners/ag-luxury-site` PR #58, branch `codex/ag-community-photo-research-20260928`, head `f2f9095696284114c10686a9f40e5a7992795b59`. That is the revision NORTH inspected, and the PR merged at that head on 2026-09-28 16:26 UTC. Read in a separate read-only clone, not Codex's worktree:

- `docs/visual-photo-replacements-2026-09-28.md`
- `docs/evidence/community-photo-candidates-2026-09-28.json` (SHA-256 `2205cde8b3d42fbdbe845093aaff28b98a28045da7ab435fb87f5d14f0823ad7`)
- `source-reference/asset-manifest.json` (55 packaged media files with path, size and SHA-256, no rights fields)
- Also read for the Light Farms and area-photo provenance the manifest does not carry: `docs/neighborhood-source-register.md`, `docs/evidence/area-photo-assets-2026-09-28.json`

Evaluation output SHA-256: JSON `f84cc352c6027bdc61f51620fa31d9d737b46e6081de897733eefe2bffe9d149`, table `20d7e5c4fc2a7c8781393ad8ce5e10f4c4b616996b32615fb57fb6c66b93f39d`. Regenerate with `python3 skills/visual-clearance/scripts/evaluate_site_record.py --record <that file at f2f9095> --revision f2f9095696284114c10686a9f40e5a7992795b59 --as-of 2026-09-28`.

## Existing work reused, not repeated

All 23 candidates, their source pages, image URLs, publishers, photographer status, identity notes, observed dimensions, placement list, documented placement minimums, contact routes, Realtor-library findings and the reusable request text. No search was re-run. The placement minimums were taken from the record's `targetCrops` into three consumer profiles, and the run fails if the owner's values drift from them. The website's Light Farms provenance and its excluded water-tower finding were read from its source register and fed into the skill's pilot fixture.

## Results

23 candidates. VERIFIED 0, PROBABLE 20, UNVERIFIED 3. Exact-use cleared 0. NEXT: REQUEST PERMISSION 20, REJECT at current evidence 3. Observed sizes are web images, so a size failure asks for the original instead of rejecting the photograph.

| Guide | Identity | Rights | Observed | Directory 4:3 | Hero 16:9 + mobile | Mid-guide 3:2+ | NEXT |
| --- | --- | --- | --- | --- | --- | --- | --- |
| The Hills of Kingswood | PROBABLE | NOT CLEARED | 2560x1556 | 2074x1556 ok | 2560x1440 ok | 2560x1556 ok | REQUEST PERMISSION |
| Villages of Stonebriar Park | UNVERIFIED | NOT CLEARED | 2048x1366 | 1821x1366 ok | 2048x1152 needs 2134x1200 | 2048x1365 ok | REJECT |
| Starwood | PROBABLE | NOT CLEARED | 1200x950 | 1200x900 ok | 1200x675 needs 2134x1200 | 1200x800 needs 2000x1300 | REQUEST PERMISSION |
| Newman Village | PROBABLE | NOT CLEARED | 2500x1319 | 1758x1319 ok | 2344x1319 ok | 2500x1319 ok | REQUEST PERMISSION |
| Windsong Ranch | PROBABLE | NOT CLEARED | 1200x675 | 900x675 needs 1200x900 | 1200x675 needs 2134x1200 | 1200x675 needs 2000x1300 | REQUEST PERMISSION |
| Fields | UNVERIFIED | NOT CLEARED | 1200x635 | 846x635 needs 1200x900 | 1128x635 needs 2134x1200 | 1200x635 needs 2000x1300 | REJECT |
| Park Place Estates | PROBABLE | NOT CLEARED | 3264x2448 | 3264x2448 ok | 3264x1836 ok | 3264x2176 ok | REQUEST PERMISSION |
| Shoal Creek | PROBABLE | NOT CLEARED | 1919x1279 | 1705x1279 ok | 1919x1079 needs 2134x1200 | 1919x1279 needs 2000x1300 | REQUEST PERMISSION |
| Willow Bend West | PROBABLE | NOT CLEARED | 1200x800 | 1066x800 needs 1200x900 | 1200x675 needs 2134x1200 | 1200x800 needs 2000x1300 | REQUEST PERMISSION |
| The Tribute | UNVERIFIED | NOT CLEARED | 1800x729 | 972x729 needs 1200x900 | 1296x729 needs 2134x1200 | 1800x729 needs 2000x1300 | REJECT |
| Bellaire in Lantana | PROBABLE | NOT CLEARED (MLS) | 400x300 | 400x300 needs 1200x900 | 400x225 needs 2134x1200 | 400x266 needs 2000x1300 | REQUEST PERMISSION |
| Saddlebrook Estates in Bartonville | PROBABLE | NOT CLEARED (MLS) | 1536x1152 | 1536x1152 ok | 1536x864 needs 2134x1200 | 1536x1024 needs 2000x1300 | REQUEST PERMISSION |
| Oakwood Estates in Fairview | PROBABLE | NOT CLEARED | 2560x1707 | 2276x1707 ok | 2560x1440 ok | 2560x1706 ok | REQUEST PERMISSION |
| Chapel Creek | PROBABLE | NOT CLEARED | 1835x1241 | 1654x1241 ok | 1835x1032 needs 2134x1200 | 1835x1223 needs 2000x1300 | REQUEST PERMISSION |
| Normandy Estates | PROBABLE | NOT CLEARED | 700x467 | 622x467 needs 1200x900 | 700x393 needs 2134x1200 | 700x466 needs 2000x1300 | REQUEST PERMISSION |
| Willow Bend Lakes | PROBABLE | NOT CLEARED | 1889x1184 | 1578x1184 ok | 1889x1062 needs 2134x1200 | 1889x1184 needs 2000x1300 | REQUEST PERMISSION |
| Mustang Lakes | PROBABLE | NOT CLEARED | 1920x1402 | 1869x1402 ok | 1920x1080 needs 2134x1200 | 1920x1280 needs 2000x1300 | REQUEST PERMISSION |
| Castle Hills | PROBABLE | NOT CLEARED | 490x290 | 386x290 needs 1200x900 | 490x275 needs 2134x1200 | 490x290 needs 2000x1300 | REQUEST PERMISSION |
| The Highlands at Trophy Club | PROBABLE | NOT CLEARED (MLS) | 750x500 | 666x500 needs 1200x900 | 750x421 needs 2134x1200 | 750x500 needs 2000x1300 | REQUEST PERMISSION |
| Waterstone Estates | PROBABLE | NOT CLEARED | 2048x1322 | 1762x1322 ok | 2048x1152 needs 2134x1200 | 2048x1322 ok | REQUEST PERMISSION |
| Lexington Parks | PROBABLE | NOT CLEARED (MLS) | 1024x576 | 768x576 needs 1200x900 | 1024x576 needs 2134x1200 | 1024x576 needs 2000x1300 | REQUEST PERMISSION |
| Star Trail | PROBABLE | NOT CLEARED | 2000x1125 | 1500x1125 ok | 2000x1125 needs 2134x1200 | 2000x1125 needs 2000x1300 | REQUEST PERMISSION |
| Saddlebrook Estates in Lucas | PROBABLE | NOT CLEARED (MLS) | 640x480 | 640x480 needs 1200x900 | 640x360 needs 2134x1200 | 640x426 needs 2000x1300 | REQUEST PERMISSION |

The website's one placed community photograph, the Light Farms entrance (Commons original 1893x1262, CC BY-SA 4.0), measured the same way: directory 4:3 crop 1682x1262 passes; hero 16:9 crop 1893x1064 is below 2000x1200; mid-guide 1893x1262 is below 2000x1300. Identity PROBABLE (Commons record plus visible LIGHT FARMS sign; the official-site monument match is not recorded). Rights clear for website use with attribution and ShareAlike. The monument sign is an unresolved trademark decision, and Allison's aesthetic approval is not recorded.

## Remaining gaps

Identity. No candidate is VERIFIED. The 20 PROBABLE rest on a single caption or listing identification. An owner's own caption is one evidence item, not verification. Three are UNVERIFIED because the image only appears on a page without a caption naming the scene: Villages of Stonebriar Park, Fields, The Tribute.

Rights. All 23 are NOT CLEARED. Being shown on a publisher's page, in a Realtor library or in the private preview is not permission. 5 are listing photographs of private homes under MLS rules, none of them Allison's listings: Bellaire in Lantana, Saddlebrook Estates in Bartonville, The Highlands at Trophy Club, Lexington Parks, Saddlebrook Estates in Lucas. Windsong's Realtor library terms retain ownership and do not grant independent-site use.

Resolution. Only 4 meet all three documented placements at their observed size: The Hills of Kingswood, Newman Village, Park Place Estates, Oakwood Estates in Fairview. The other 19 need an original-resolution file for at least one placement. The site record marks Villages of Stonebriar Park, Waterstone Estates as "at least hero target width", but their 16:9 crops are 1152 pixels tall, below the documented 1200 minimum. Width passes, height fails.

## Observations for the website owner (reported, not edited)

- The reusable request in `docs/visual-photo-replacements-2026-09-28.md` names "AG Luxury" to outside rights holders. AG Luxury canon (`canon/brand.md`, `canon/voice.md`) makes Allison Gaddy the public name and says AG Luxury never appears consumer-facing. The drafts below make that one change.
- The record's `resolutionStatus` compares width only for Villages of Stonebriar Park and Waterstone Estates. See the height finding above.
- The Light Farms hero row reads "2000 x 1200 preferred", while the general requirement reads minimum. The placed image falls below it for hero and mid-guide.
- The request text calls Allison a "real estate broker". Her license title is not verified here and belongs to her before sending.

## Evidence tasks for an AI worker (no human needed)

For each PROBABLE candidate, compare the pictured landmark or scene with the community's official site imagery or a viewing-only map check and record it as a C or D item. For the three UNVERIFIED, look for a caption on the original upload or a second official image of the same scene. Only recorded evidence changes a grade.

## Permission and evidence request drafts (not sent)

These use the website owner's reusable request as the base, with "AG Luxury" replaced by first person to match canon. Each lists the exact photographs, the sizes needed and the listing-specific asks. Contacts are referenced by pointer to the owner's contact table and not copied here. Sending any of them needs Allison's approval. Nothing was sent, bought or published.

### The Hills of Kingswood

Route: The Hills of Kingswood row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of The Hills of Kingswood

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - The Hills of Kingswood: source page https://thehillsofkingswood.com/gallery and image https://img1.wsimg.com/isteam/ip/4a1199a8-ff2f-4de1-ab7c-f5e67f83bfd3/092b5ec3-cf65-4a19-93e9-0746ca7c9404.jpg

### Starwood Community Association

Route: the Starwood Community Association row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Starwood

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Starwood: source page https://starwoodfrisco.com/ and image https://starwoodfrisco.com/wp-content/uploads/2025/02/Falls-Village-Entrance.jpg
    The largest version I can find is 1200 x 950 pixels. I would need the original, ideally at least 2134 x 1300.

### NV Homestead / J.R. Newman Homes

Route: the NV Homestead / J.R. Newman Homes row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Newman Village

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Newman Village: source page https://www.nvhomestead.com/ and image https://images.squarespace-cdn.com/content/v1/5b5612012487fdff0a859a47/1538154778097-QV2LKBZRCTPM2KZ3A88L/Newman+Village+Entry.jpeg

### Windsong Operations LLC / Tellus Group

Route: the Windsong Operations LLC / Tellus Group row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Windsong Ranch

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Windsong Ranch: source page https://windsongranchliving.com/amenities/lagoon/ and image https://windsongranchliving.com/wp-content/uploads/2020/07/WSR-Lagoon-Gallery__0003_Lagoon-01.jpg
    The largest version I can find is 1200 x 675 pixels. I would need the original, ideally at least 2134 x 1300.
  - Your Realtor resource page links community photos, but I could not find permission for use on an independent agent website, so I am asking for that scope directly.

### Brad Holden / Holden New Homes (Update Frisco)

Route: the Brad Holden / Holden New Homes (Update Frisco) row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Park Place Estates

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Park Place Estates: source page https://updatefrisco.com/2016/04/14/park-place-estates-builders-shaddock-homes-and-belclaire-homes-in-closeout/ and image https://updatefrisco.com/wp-content/uploads/2016/04/img_3375.jpg

### Jan Richey Real Estate

Route: the Jan Richey Real Estate row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Shoal Creek, Willow Bend West, Chapel Creek, Willow Bend Lakes, Villages of Stonebriar Park

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Shoal Creek: source page https://janrichey.com/neighborhood/shoal-creek and image https://janrichey.com/wp-content/uploads/2015/10/ShoalCreekLake.jpg
    The largest version I can find is 1919 x 1279 pixels. I would need the original, ideally at least 2134 x 1300.
  - Willow Bend West: source page https://janrichey.com/neighborhood/willow-bend-west and image https://janrichey.com/wp-content/uploads/2015/12/IMG_9746west-1.jpg
    The largest version I can find is 1200 x 800 pixels. I would need the original, ideally at least 2134 x 1300.
  - Chapel Creek: source page https://janrichey.com/neighborhood/chapel-creek and image https://janrichey.com/wp-content/uploads/2015/10/ChapelCreekBridgeHouse.jpg
    The largest version I can find is 1835 x 1241 pixels. I would need the original, ideally at least 2134 x 1300.
  - Willow Bend Lakes: source page https://janrichey.com/neighborhood/willow-bend-lakes and image https://janrichey.com/wp-content/uploads/2015/10/WillowBendLakes2.jpg
    The largest version I can find is 1889 x 1184 pixels. I would need the original, ideally at least 2134 x 1300.
  - Villages of Stonebriar Park: source page https://janrichey.com/neighborhood/villages-of-stonebriar-park and image https://janrichey.com/wp-content/uploads/2015/10/Villages-of-Stonebriar-Park.jpg
    Please confirm the photograph shows Villages of Stonebriar Park and where in the community it was taken.

### DFW Moves

Route: the DFW Moves row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Bellaire in Lantana

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Bellaire in Lantana: source page https://www.dfwmoves.com/lantana-homes-real-estate/bellaire/ and image https://cdn.listingphotos.sierrastatic.com/pics2x/v1782039786/57/57_21294408_01.jpg
    The largest version I can find is 400 x 300 pixels. I would need the original, ideally at least 2134 x 1300.
    This is a listing photograph. Please connect me with the photographer, and I would also need the property owner's consent.

### Listing publisher on Zillow; photographer unidentified

Route: the Listing publisher on Zillow; photographer unidentified row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Saddlebrook Estates in Bartonville

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Saddlebrook Estates in Bartonville: source page https://www.zillow.com/homedetails/1248-Saddlebrook-Way-Bartonville-TX-76226/89512998_zpid/ and image https://photos.zillowstatic.com/fp/30afc501732c34c5fb31d3859a01d56c-cc_ft_1536.jpg
    The largest version I can find is 1536 x 1152 pixels. I would need the original, ideally at least 2134 x 1300.
    This is a listing photograph. Please connect me with the photographer, and I would also need the property owner's consent.

### Kelly Pearson Realty Group

Route: the Kelly Pearson Realty Group row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Oakwood Estates in Fairview

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Oakwood Estates in Fairview: source page https://kellypearsonrealtygroup.com/fairview-texas-lovejoy-isd-homes/ and image https://kellypearsonrealtygroup.com/wp-content/uploads/2023/02/OakwoodEstatesFairviewTexas1-scaled.jpg

### StarSide Builders

Route: the StarSide Builders row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Normandy Estates

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Normandy Estates: source page https://starsidebuilders.com/our-communities/normandy-estates/ and image https://starsidebuilders.com/wp-content/uploads/2024/05/Normandy-Estates-Waterfall.jpeg
    The largest version I can find is 700 x 467 pixels. I would need the original, ideally at least 2134 x 1300.

### Mustang Lakes developer

Route: the Mustang Lakes developer row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Mustang Lakes

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Mustang Lakes: source page https://mustanglakes.com/resort-style-living-in-mustang-lakes/ and image https://mustanglakes.com/wp-content/uploads/2022/07/DJI_0747XXXZf-Copy-1920x1402.jpg
    The largest version I can find is 1920 x 1402 pixels. I would need the original, ideally at least 2134 x 1300.
  - Your public gallery is a viewing page, and I could not find terms for use on an independent agent website, so I am asking directly.

### Castle Hills developer

Route: the Castle Hills developer row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Castle Hills

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Castle Hills: source page https://castlehills.com/homeowners.php and image https://castlehills.com/assets/images/amenities/amenities-castle-hills-village-shops.jpg
    The largest version I can find is 490 x 290 pixels. I would need the original, ideally at least 2134 x 1300.

### LEAGUE Real Estate listing publisher; MLS photographer unidentified

Route: the LEAGUE Real Estate listing publisher; MLS photographer unidentified row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of The Highlands at Trophy Club

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - The Highlands at Trophy Club: source page https://leaguere.com/properties/listing/NTREIS/21085375/Trophy-Club/2823-Exeter-Drive and image https://cdn.listingphotos.sierrastatic.com/pics3x/v1760552138/57/57_21085375_01.jpg
    The largest version I can find is 750 x 500 pixels. I would need the original, ideally at least 2134 x 1300.
    This is a listing photograph. Please connect me with the photographer, and I would also need the property owner's consent.

### Partners in Building

Route: the Partners in Building row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Waterstone Estates

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Waterstone Estates: source page https://partnersinbuilding.com/build-on-your-lot/dallas/north/waterstone-estates and image https://partnersinbuilding.com/sites/default/files/2024-04/waterstone_estates_entrance.jpg
    The largest version I can find is 2048 x 1322 pixels. I would need the original, ideally at least 2134 x 1300.
  - I saw your Realtor Partner Program but no photo-use terms, so I am asking directly.

### MLS 21314346 listing, courtesy of Saira Umair of Competitive Edge Realty LLC; image served through the listing publisher

Route: the MLS 21314346 listing, courtesy of Saira Umair of Competitive Edge Realty LLC; image served through the listing publisher row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Lexington Parks

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Lexington Parks: source page https://dustinpitts.com/search-homes/listing/NTREIS/21314346/Frisco/12436-Compassplant-Drive and image https://photos.prod.cirrussystem.net/444/225bc3b8347d27e9a029ed76abf60bda/188442846.jpeg
    The largest version I can find is 1024 x 576 pixels. I would need the original, ideally at least 2134 x 1300.
    This is a listing photograph. Please connect me with the photographer, and I would also need the property owner's consent.

### American Legend Homes

Route: the American Legend Homes row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Star Trail

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Star Trail: source page https://www.amlegendhomes.com/communities/texas/prosper/star-trail and image https://dlqxt4mfnxo6k.cloudfront.net/amlegendhomes.com/aHR0cHM6Ly9zMy5hbWF6b25hd3MuY29tL2J1aWxkZXJjbG91ZC83MjVmZDg1NjBhMWQyYmJlODcyZmExNTUwNWQ3ZDdhOC5qcGVn/exact/webp/2000/1125
    The largest version I can find is 2000 x 1125 pixels. I would need the original, ideally at least 2134 x 1300.

### Realtor.com listing publisher; MLS photographer unidentified

Route: the Realtor.com listing publisher; MLS photographer unidentified row of the contact table in ag-luxury-site `docs/visual-photo-replacements-2026-09-28.md` at `f2f9095`.

Subject: Website use of your photographs of Saddlebrook Estates in Lucas

Hello, I am Allison Gaddy, a North Texas real estate broker preparing neighborhood guides for agluxurytx.com. I would like to use the specific photographs listed below. The placements are a neighborhood-directory thumbnail, the guide hero, and one editorial image within each guide. May I use and crop these images on my public website? Please confirm who owns the photographs, whether agent website marketing use is allowed, the original-resolution files available, required credit and any limits, and the one-time or ongoing license price. If you are not the rights holder, would you connect me with the photographer or marketing contact who can grant these rights? Thank you, Allison Gaddy.

Photographs:
  - Saddlebrook Estates in Lucas: source page https://www.realtor.com/realestateandhomes-detail/1050-Saddlebrook-Dr_Allen_TX_75002_M85029-23390 and image https://p.rdcpix.com/v01/l2f392044-m0rd-w960_h720.webp
    The largest version I can find is 640 x 480 pixels. I would need the original, ideally at least 2134 x 1300.
    This is a listing photograph. Please connect me with the photographer, and I would also need the property owner's consent.

### Fields Frisco (identity first)

Route: the Fields row of the same contact table.

Subject: A question about a Fields photograph

Hello, I am Allison Gaddy, preparing a neighborhood guide for Fields on agluxurytx.com. Could you tell me what this photograph shows and where it was taken, and who owns it? If it is available for my website, the same questions apply as for any image: original-resolution file, credit, limits and price. Thank you, Allison Gaddy.

Photographs:
  - Fields: source page https://fieldsfrisco.com/ and image https://fieldsfrisco.com/wp-content/uploads/2025/05/Fields-1200x635-1.jpg
    The largest version I can find is 1200 x 635 pixels. I would need the original, ideally at least 2134 x 1300.

### The Tribute developer (identity first)

Route: the The Tribute row of the same contact table.

Subject: A question about a The Tribute photograph

Hello, I am Allison Gaddy, preparing a neighborhood guide for The Tribute on agluxurytx.com. Could you tell me what this photograph shows and where it was taken, and who owns it? If it is available for my website, the same questions apply as for any image: original-resolution file, credit, limits and price. Thank you, Allison Gaddy.

Photographs:
  - The Tribute: source page https://thetribute.com/find-your-home/ and image https://thetribute.com/wp-content/uploads/2019/08/Tribute-Spring-2019_hi-res-94-crop-1800x729.jpg
    The largest version I can find is 1800 x 729 pixels. I would need the original, ideally at least 2134 x 1300.
