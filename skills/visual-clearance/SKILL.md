---
name: visual-clearance
description: "Clears visual assets for real use. Fires when an AI needs to find, source, evaluate, verify, license, clear, document, file or reuse photography or other visual assets for a website, community or city page, listing, presentation, print piece, social post, advertising or other commercial use, and when asked whether an image is safe or appropriate to reuse. Checks the visual-assets register first, sources through any approved research or browser tool, grades location from recorded evidence as VERIFIED, PROBABLE, UNVERIFIED or REJECT, keeps rights bases distinct and clears only the exact intended use, tests technical fit against a surface profile, and returns at most five candidate cards with one NEXT action each. No defensible candidate is a successful result. Final use, outreach, spending and commissioning stay human-gated. Does not fire merely because an image is being generated or graphically edited. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-09-28 (Luxury Photo Sourcing table, Visual Clearance v1 dispatch).
# Canonical home is this file. It is homed under skills/ and carried by no plugin.
# Delivery shelves are owed separately through tools/skill-deploy/deploy-skill.sh;
# v1 ships canonical source only, see "Delivery" below.
tier: organization
zone: hands
status: designed
subtitle: "sourcing, identity, rights and provenance for visual assets"
---

# Visual Clearance -- v1.0 (2026-09-28)

Visual clearance is a rights-and-identity clearance process that happens to begin with search. Search is the cheap part. The value is proving that an image shows the place it claims to show, proving the Estate may use it for the exact intended purpose, and keeping that proof durable. When nothing defensible exists, the job is to say so fast and route to permission or a commissioned shoot, never to force a result.

The 2026-09-28 research report (AI-Assisted Visual Asset Sourcing for AG Luxury, Drive file `12GWlfoG8Q_jBclTfaBSFTm_KncAhkO_N`) is design evidence, not governance. Its benchmark found zero openly licensed community hero images ready to use across six named North Texas communities. Expect that outcome and handle it well.

## Owners, never duplicated

| Concern | Owner |
| --- | --- |
| This method, its scripts, schema and profiles | this skill, `expert-partners-skills skills/visual-clearance/` |
| Asset records, approval state, rights, provenance, location evidence, usages, hashes | today, the consuming application's own asset records (AG Luxury website: `ExpertPartners/ag-luxury-site`); a shared `visual-assets` register is proposed and waits on an ownership decision (see [register and filing](references/register-and-filing.md)) |
| Master image files and large evidence (PDF captures, contracts) | Google Drive, referenced by pointer |
| Brand visual rules and voice | the owning brand repo, resolved through the Estate Manifest and `aura registry.yaml` |
| Page layouts, placements, placement size requirements, preview behavior, publishing | the consuming application; this skill reads them and never edits them |

No vendor (Perplexity, Canva, Adobe, Grok or any other) is ever the source of truth for a clearance.

## Workflow

A. Define the request. Collect or infer subject or place, intended use and use contexts, brand, required format or crop, visual direction, and whether a named real place is represented. Read the brand's canon and the requesting application first; ask only for what neither supplies. Use the technical-fit profile the surface supplies or the matching one in [profiles/](profiles/). When none matches the surface, build a request-scoped profile from the stated format and crop, say so on the output, and never grade against a different surface's profile.

B. Check owned and cleared assets first. Read the current record owner before any external search: the application's own asset and candidate records at a pinned revision (`scripts/evaluate_site_record.py` for the AG Luxury website record), or the visual-assets register once it exists. Reuse the owner's existing candidates, sources, contact routes and dimensions instead of repeating their searches; never copy them into a second register. Reuse only when the record's status, brand scope, place identity, use scope, modifications, expiry, review date and technical fit all cover the new request (`clearance_rules.check_reuse`). If the register is unreachable, say so on the output and continue sourcing, but never claim an owned asset exists or does not exist.

C. Source candidates down the waterfall in [sourcing-waterfall.md](references/sourcing-waterfall.md), using the best available approved research, search or browser tool. Perplexity is preferred for deep web research when present; any approved tool runs the same method. Log every source searched. No scrapers built to get around vendor terms.

D. Verify location with [location-verification.md](references/location-verification.md). Grades are VERIFIED, PROBABLE, UNVERIFIED or REJECT, from recorded evidence only. A search label or AI inference never verifies. A named-place page uses VERIFIED imagery only.

E. Clear rights with [rights-clearance.md](references/rights-clearance.md). Keep visible online, downloadable, royalty-free, Creative Commons, public domain, free for commercial use, paid commercial license, direct written permission and exact-use clearance distinct. Check people, logos and trademarks, identifiable homes, architecture and license conditions. State risk, never legal certainty.

F. Test technical fit with `scripts/fit_check.py` and the surface profile. Record the visual review items (calm center, overlay tolerance, mobile subject) before any card can read USE. Surface insufficient resolution explicitly.

G. Output at most five candidate cards per [candidate-card.md](references/candidate-card.md), rendered with `scripts/render_cards.py`. One NEXT action per card, from USE, REQUEST PERMISSION, LICENSE, COMMISSION or REJECT, chosen by the precedence in that reference (identity failures reject before any permission route). Never pad to five. "No defensible candidate found" with a route is a successful result.

H. Hold the human gates below. Draft outreach per [outreach-drafts.md](references/outreach-drafts.md); never send it.

I. File after approval. Only after Allison or the authorized human approves a specific card, hand a record validated by `scripts/validate_record.py` to the current record owner's own asset workflow (for the AG Luxury website, its source asset workflow run by the website owner). The skill never edits an application's repository, branch or deployment. A recommendation is not an approval.

## Never

- Represent a named place with anything but VERIFIED imagery, or raise a grade by relabeling instead of adding evidence.
- Use AI-generated imagery to depict a real named place or community.
- Treat visibility, downloadability, an MLS listing, a map or street-level image, or a social post as permission.
- Let attribution cure a use the license does not cover.
- Send outreach, buy a license or stock subscription, commission photography, or publish anything.
- Move large media binaries into Git, or store secrets, correspondence bodies or personal contact details in the register.

## Human gates

Allison or the authorized human decides: final use of any asset, sending any permission request, any spending (licenses, subscriptions, commissions), ShareAlike edge cases in advertising or print, and sensitive people, home or trademark decisions. The scripts mark every decision `auto_executable: false`; nothing here acts on its own recommendation.

## Deterministic helpers

| Script | Job |
| --- | --- |
| `scripts/inspect_image.py` | format, stored and display dimensions, SHA-256, EXIF date, GPS, artist and copyright |
| `scripts/fit_check.py` | parameterized crop, resolution, safe-zone and mobile-slice checks against a profile |
| `scripts/clearance_rules.py` | location grading, rights clearance, human gates, next action, register reuse |
| `scripts/render_cards.py` | ranked cards, five-card cap, zero-result route |
| `scripts/validate_record.py` | register record schema, cross-field rules and privacy checks |
| `scripts/evaluate_site_record.py` | evaluates an application's existing candidate record in place, every placement, with owner-drift checks |

Standard library only (PyYAML for YAML records). Tests: `python3 -m unittest discover -s skills/visual-clearance/tests -p 'test_*.py' -v`. Behavioral cases for cold-reader runs live in [tests/behavioral-cases.json](tests/behavioral-cases.json) with a withheld rubric.

## Delivery

Canonical source lives here and nowhere else. Deployed copies and upload ZIPs come only from `tools/skill-deploy/deploy-skill.sh`. v1 ships canonical source and validation evidence only: no claude.ai upload, no Aura deployed copy and no Codex mirror is produced until a separately authorized delivery step names its shelves. `status: designed` flips to `live` in that delivery pass. A dedicated Visual Librarian role is out of scope until recurring permission follow-ups, license re-checks and usage audits exist to own.
