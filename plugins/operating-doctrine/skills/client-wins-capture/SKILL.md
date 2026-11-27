---
name: client-wins-capture
description: "Capture real client wins into the owning company brain from CRM submissions, the Hub, social posts and reviews. Use for the scheduled wins sweep, a backfill or an arrival check. Preserve source evidence and consent, deduplicate cases and report every missing source or unsafe destination."
allowed-tools: []
tier: plugin
zone: brain
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "real client wins, filed with evidence and checked on arrival"
---

# Client Wins Capture

Capture evidence, not marketing copy. This skill does not publish testimonials, request reviews, change sharing or turn a won sales opportunity into a client result.

1. Read current governance and the owning folder map through the Brain Gateway, following every required page. Resolve the company's current Case Studies folder live. Do not create a missing destination, substitute a Testimonials document for a folder or write into a public source-history folder. Follow the [capture runbook](references/runbook.md).
2. Read every configured source using its supported connection. Fetch all pages on the first backfill, then changed records since the last successful source scan with overlap. Independently inspect the latest 100 records per source on every run. A refused or incomplete read is a source failure, never zero wins. Keep secrets in 1Password and resolve them only inside the consuming process.
3. Normalize attributable, verbatim wins and existing destination receipts into the bundled `scripts/capture.py` contract. Run it with Python 3 and JSON on stdin. It does no networking. Fixture records, inferred outcomes and missing evidence are not wins. Unknown consent is internal-only. A public post or review is not permission to republish.
4. Apply each allowed action serially through the Drive connector in the exact verified owning folder. Recheck effective destination access immediately before each write. Write one file per case, preserving its stable source key. Never widen source access. Read the created or updated file back, verify parent and content, then pass those observed receipts to the helper again. An uncertain write requires a destination search before retrying. Do not mark a source scan successful until all its pages and actions are reconciled.
5. Report source reads, eligible wins, filed, updated, unchanged, blocked, missing arrivals and failed sources. Only a read-back receipt proves arrival. Retain failed items for retry without advancing their successful checkpoint. Store the run receipt in the live owning department folder if suitable, otherwise report the exact save gap and retain it in the current working context. Do not put personal source content in a general status report. Schedule through the existing scheduler, one nightly run, with no parallel writer.

Keep original quotes exact. Do not combine different clients, infer consent, fabricate results or send captured material to social channels. Drafting public assets is a separate authorized use of the case-study and brand skills with field-specific permission.
