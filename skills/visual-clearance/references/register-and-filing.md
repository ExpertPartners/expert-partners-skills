---
classification: internal
classification_owner: allison
classification_date: 2026-09-28
date: 2026-09-28
source: Visual Clearance v1 dispatch ownership boundaries
topic: visual-assets register reads, record schema and filing after approval
---

# Register and filing

This skill owns only the method and the schema at `schemas/asset-record.schema.json`. It owns no records.

## Current record owners (reconciled 2026-09-28)

- AG Luxury website: `ExpertPartners/ag-luxury-site` owns the records for assets it places and candidates it researches. Placed-asset provenance lives in `docs/neighborhood-source-register.md` and `docs/evidence/area-photo-assets-2026-09-28.json`; candidate research and contact routes in `docs/evidence/community-photo-candidates-2026-09-28.json`; packaged media hashes in `source-reference/asset-manifest.json`. Read them at a pinned revision, by pointer. Never edit, migrate or delete them. Any future transfer needs an explicit owner-approved transition with source pointers and preserved history.
- Shared register: `ExpertPartners/visual-assets` is not created. Allison's 2026-10-07 direction (aura `intake/2026-10-07-ruling-visual-clearance-parked-asset-records-stay-with-owner.md`) keeps photo-rights records with the repository that uses the asset and revisits a shared registry only when a cleared asset is actually reused across a second brand, website or channel. The sections below describe the register for that day; until then, never write to it or behave as if it exists.

## The proposed shared register

It would own cleared asset metadata, approval state, rights and provenance records, location-verification evidence records, permission and license evidence pointers, hashes and approved usage records for assets whose approved scope spans consumers.

## Reading the register

Read the current owner's records first (above). For the shared register, read `register/` in visual-assets through the first path that works: a local checkout at a fetched revision, the Estate Brain door if it serves the repo, or the GitHub contents API. Name the revision read. If no path works, report `register unreachable` on the output and continue external sourcing without claiming what the register holds. An unregistered or unborn register is reported the same way.

## Pointer boundary

The register holds metadata and pointers, never the heavy or private material itself.

| Material | Lives in | Register holds |
| --- | --- | --- |
| Master files and derivatives | Google Drive | `drive:` pointer plus SHA-256 |
| Source and license page captures | Google Drive | `license_evidence_pointer`, `location_evidence[].pointer` |
| Permission emails | Gmail | `gmail:` thread pointer, never the body |
| Contracts and releases | Drive or the contract system | `contract:` or `drive:` pointer |
| Creator contact | the creator's public page or the system of record | `creator_contact_pointer`, never an email address or phone number |

Large binaries do not go into Git because the repository exists. Secrets never enter the register.

## Record shape

One YAML file per asset at `register/<asset_id>.yaml`, ids `VA-YYYY-NNNN`, `schema_version: "1.0"`. Required fields: asset_id, status (approved, retired, rejected), subject, place_key when a place is named, brand_scope, source_class, location_confidence, location_evidence, source_url, original_file_pointer, creator, creator_contact_pointer, capture_date, original_filename, dimensions, sha256, license, license_url, license_evidence_pointer, attribution_required, attribution_text, permission_type, permission_scope, permission_expires, release_state, third_party_flags, verified_on, verified_by, approval, modifications, derivatives, usages, review_due. Always quote `sha256` in YAML; an all-digit hash otherwise parses as a number and fails validation.

`rejected` records are worth filing when a trap would otherwise be re-evaluated (for example a mislabeled look-alike), so the next run finds the answer in the register first.

## Filing after approval

1. Allison or the authorized human approves a specific card. Record where that approval lives (`approval.approval_pointer`) and who gave it; an AI surface is never the approver.
2. Capture and hash the master with `inspect_image.py`; store the master and captures in Drive.
3. Write the record, run `validate_record.py` until it passes.
4. Commit on a branch in visual-assets and open a pull request through the repository's normal reviewed path. Never push to the default branch directly and never merge your own filing.
5. Add each new placement to `usages` when it goes live, and set `review_due` for re-verification (default twelve months).

A recommendation, a rendered card or a passing validator is not an approval, and does not authorize a filing.
