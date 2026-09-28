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

## Evaluation input for `render_cards.py`

One JSON file per request: `as_of`, `request` (subject, `place_key`, `represents_named_place`, `intended_use`, `use_contexts`, `brand`, `profile`, `modifications`, `commercial`, `visual_direction`, `known_owner_sources`), `register_check` (`status` of `checked` or `unreachable`, with a note), `search_log`, and `candidates`. Each candidate carries `source_class`, `dimensions`, `capture_date`, `location.evidence` (and any `claimed_grade`), `rights` (basis, license id and URL, evidence pointer, commercial use, modification, conditions, scope, permission), `third_party_flags`, `visual_review`, `owner_contact_route` and `license_purchase`. The pilot fixtures in `tests/fixtures/` are working examples.

The renderer refuses to run without a register check, and refuses to present a candidate as USE while its visual review items are unrecorded. Run the review, record it in `visual_review`, then render.

## Presentation

Show the rendered cards as they come out. Do not add a card the renderer screened out, do not upgrade a NEXT action in prose, and do not summarize a REQUEST PERMISSION card as if permission were obtained.
