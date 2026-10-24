---
name: acn-currency-check
description: |
  The staying-current skill for Allison's ACN Advisor lane, built on the capability-refresh pattern. Fires monthly and whenever Allison asks if we are current, whether anything changed at ACN, whether the research brief is stale, or whether a rule, fee, threshold, promotion, or DingoBlu status has moved. Checks the two Firecrawl monitors for new hits, re-verifies the Business Support Fee, the current Compensation Plan version and Customer Qualified threshold, the Fast Start and Customer Bonus promotion for the current month, and DingoBlu's public status against live sources, then reports what changed since the 2026-08-05 ACN Master Research Brief and flags what needs a Back Office pull to confirm. Use it even when Allison does not name the skill, as long as the ask is about whether ACN knowledge is up to date. It inherits the operating-doctrine and the ACN Advisor guardrails and never overrides them.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Zoned hands 2026-08-05 (Skill Map Rulings lane, add-on brief note 3).
tier: plugin
zone: hands
status: live
subtitle: "monthly ACN staying-current check"
---

# ACN Currency Check

Keep the ACN knowledge base honest. Public ACN rules, fees, promotions, and the DingoBlu launch all move, and the 2026-08-05 ACN Master Research Brief is a snapshot, not a subscription. This skill re-verifies the moving parts against live sources on a schedule so the advisor lane never plans against stale rules.

## When this fires

1. Monthly, on the first ACN Advisor session of a new month.
2. Whenever Allison asks if we are current, what changed, or whether the brief is stale.
3. Before any recommendation that depends on a fee amount, threshold, promotion, or DingoBlu status more than 30 days old.

## Step 1. Check the Firecrawl monitors

Two monitors are already live. Do not create duplicates.

- Search monitor: 019fd292-3d0a-7746-ae06-a1f20ebd9611
- Page diff monitor: 019fd292-6d2b-762a-a225-22150e4ed684

Use firecrawl_monitor_checks on each to list checks since the last currency run, then firecrawl_monitor_check on any completed check to read new, changed, or removed pages and diffs. A monitor hit is a lead to investigate, never a conclusion. Fetch the underlying live page before reporting a change as real.

## Step 2. Re-verify the four moving parts against live sources

Fetch each live source directly (Firecrawl scrape or web fetch). Compare against the baseline below.

1. Business Support Fee and renewal fee. Source, the ACN public opportunity FAQ at acn.com. Baseline as of 2026-08-05, $25 monthly Business Support Fee and $49 annual renewal, public statement only, account billing controls.
2. Compensation Plan version and Customer Qualified threshold. Sources, the Compensation Plan Overview PDF linked from the ACN public FAQ (hosted on myacn.my.salesforce.com), the ACN Vimeo channel for dated plan videos, and known secondary hosts. Baseline, a January 1, 2026 ACN-branded overview on a secondary host appears to state two services and five Personal Customer Points, unverified, and an official ACN video dated March 2, 2026 exists whose contents were not publicly retrievable. Any newer dated plan artifact is a change worth reporting.
3. Fast Start and Customer Bonus promotion for the current month. Sources, ACN public promotion pages and dated ACN-branded overviews. Baseline, a public 2026 overview associates three services with a first bonus tier and six with a higher tier, promotional, unverified, thresholds change by enrollment period.
4. DingoBlu public status. Source, dingoblu.com. Baseline as of 2026-08-05, the site says Coming in 2026 with no consumer terms, no partner bank, no FDIC disclosure, no fee schedule, no point rules. Report any newly published legal document verbatim by name and date.

## Step 3. Report

Structure the report in this order.

1. What changed since the 2026-08-05 ACN Master Research Brief, each change with its live source URL and retrieval date.
2. What did not change, one line per moving part, so the confirmation is on the record.
3. What needs a Back Office pull to confirm, stated as the specific document or screen to capture. Public findings never graduate past unverified without a controlling document.
4. Monitor health, whether both monitors ran on schedule and whether either needs attention.

## Rules that never bend

- The Back Office controls. Every public finding stays labeled unverified until a controlling document or written ACN case response confirms it.
- A monitor hit, a social post, an upline deck, or a secondary-hosted PDF is never controlling.
- Never conflate the three thresholds. Active account status, Customer Qualified, and Fast Start bonus tiers are different things and get reported separately.
- DingoBlu stays on the watchlist until final legal terms publish. No deposits, no fund movement, never called a bank, never described as FDIC insured.
- No purchase recommendation exists to produce points or bonuses. Switches must save money or hold cost neutral on their own.
- Income language stays inside ACN compliance. Income is not guaranteed and IBOs may lose money.

## Formatting

Allison's rules everywhere. No em dashes, no bold, no italics, no dividers. Spoken register. Lead with what changed. End where the content ends.
