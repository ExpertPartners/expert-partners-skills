---
classification: internal
classification_owner: allison
classification_date: 2026-09-28
date: 2026-09-28
source: Visual Clearance v1 dispatch ownership boundaries
topic: visual-assets register reads, record schema and filing after approval
---

# Register and filing

The canonical register is the `ExpertPartners/visual-assets` repository. It owns cleared asset metadata, approval state, rights and provenance records, location-verification evidence records, permission and license evidence pointers, hashes and approved usage records. This skill owns only the method and the schema at `schemas/asset-record.schema.json`.

## Reading the register

Read `register/` in visual-assets through the first path that works: a local checkout at a fetched revision, the Estate Brain door if it serves the repo, or the GitHub contents API. Name the revision read. If no path works, report `register unreachable` on the output and continue external sourcing without claiming what the register holds. An unregistered or unborn register is reported the same way.

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
