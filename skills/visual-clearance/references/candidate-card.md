---
classification: internal
classification_owner: allison
classification_date: 2026-09-28
date: 2026-09-28
source: Visual Clearance v1 dispatch
topic: visual-clearance candidate cards and evaluation input
---

# Candidate cards

The human sees at most five cards, ranked USE, LICENSE, REQUEST PERMISSION, COMMISSION, REJECT. Fewer is normal. When no candidate is defensible the output leads with "No defensible candidate found." and one route, which is a successful result, not a failure to report.

## Card fields

Thumbnail or pointer, subject, source, creator, source URL, dimensions, location state with the evidence behind it, rights state (basis and license), exact-use clearance, attribution requirement and text, technical fit, risk flags, why, one NEXT action, and the human gates on that action.

## NEXT actions

| Action | Meaning | Gate |
| --- | --- | --- |
| USE | Identity, rights, third-party and technical gates all pass on recorded evidence | Final use approval |
| LICENSE | A purchasable license covers the exact use | Spending approval |
| REQUEST PERMISSION | The owner or creator can grant rights or confirm identity; a draft request is attached | Sending approval |
| COMMISSION | No existing image can clear; shoot it under a written license | Spending approval |
| REJECT | Fails identity, rights or fit for this use; one line says why | none |

## Choosing the one NEXT action

Apply the first rule that matches. `clearance_rules.decide` enforces the same order, and every other blocker still appears in the card's Why line.

1. Generated imagery offered for a named place: REJECT.
2. Location REJECT, or UNVERIFIED on a named-place request: REJECT, even when a creator or owner is reachable. Raise the grade with recorded evidence first; a permission request never substitutes for identity evidence.
3. Technical fit FAIL for this surface on an original file: REJECT for this use. When the measured file is only an observed web derivative (`dimensions_basis: observed_web`) and only resolution fails, the image is not rejected; the missing original-resolution file becomes an ask in the permission route, and the candidate can never read USE until the original is measured.
4. Rights NOT CLEARED: LICENSE when a purchasable license covers the exact use, else REQUEST PERMISSION when an owner or creator route exists, else REJECT.
5. PROBABLE on a named-place request: REQUEST PERMISSION when the owner or creator can confirm identity and grant rights, else REJECT.
6. Rights NEEDS HUMAN DECISION (ShareAlike in advertising or print, unresolved people, logo or home flags): REQUEST PERMISSION when a route exists, else REJECT. Allison can still decide the gate herself.
7. Everything passes and the visual review is recorded: USE.

When no candidate survives, the route is REQUEST PERMISSION if an official owner source for the named place is known (list it in `known_owner_sources`), COMMISSION if none is known, and LICENSE for a non-identity request.

## Evaluation input for `render_cards.py`

One JSON file per request: `as_of`, `request` (subject, `place_key`, `represents_named_place`, `intended_use`, `use_contexts`, `brand`, `profile`, `modifications`, `commercial`, `visual_direction`, `known_owner_sources`), `register_check` (`status` of `checked` or `unreachable`, with a note), `search_log`, and `candidates`. Each candidate carries `source_class`, `dimensions`, `capture_date`, `location.evidence` (and any `claimed_grade`), `rights` (basis, license id and URL, evidence pointer, commercial use, modification, conditions, scope, permission), `third_party_flags`, `visual_review`, `owner_contact_route` and `license_purchase`. The pilot fixtures in `tests/fixtures/` are working examples.

The renderer refuses to run without a register check, and refuses to present a candidate as USE while its visual review items are unrecorded. Run the review, record it in `visual_review`, then render.

## Presentation

Show the rendered cards as they come out. Do not add a card the renderer screened out, do not upgrade a NEXT action in prose, and do not summarize a REQUEST PERMISSION card as if permission were obtained.
