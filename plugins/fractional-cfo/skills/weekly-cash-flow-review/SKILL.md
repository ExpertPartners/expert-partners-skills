---
name: weekly-cash-flow-review
description: Run Allison's weekly cash flow review across Mercury and PayPal. Use whenever she asks for a cash flow review, weekly money check, "where's my cash", "how did this week look", what came in and went out, or any request to review recent business cash movement. Also use when she asks about anomalies, large transactions, or week-over-week comparison. Trigger even without the word "weekly" when the intent is reviewing recent cash activity.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: finance
status: live
inherits: operating-doctrine
calls:
  - canonical-categories
  - entity-separation
brand-scope: null
subtitle: "weekly cash in and out, per entity"
---

# Weekly Cash Flow Review

Inherits the operating-doctrine skill and the Fractional CFO project instructions. Read-only. All math in code, never eyeballed.

Payment processor rule. PayPal is the only payment processor for every business line (HQ Decision Log, November 24, 2026, Stripe and PayPal). Stripe is discontinued. Never connect, authenticate to, configure, build against or recommend Stripe. Helcim was not approved and is not an option. Any Stripe money still moving (a reserve release, a final payout, a refund Allison already authorized) is legacy Stripe wind-down, reported from the Mercury side and labeled that way, never treated as a live revenue source.

## What this produces

One report: bottom line first, then inflows, outflows, anomalies, and week-over-week movement, per entity, never blended.

## Steps

1. State the window. Default is the last 7 full days; extend to 14 if she asks or if the prior review is more than a week old. State the as-of timestamp.

2. Pull Mercury. Use listTransactions for every account across both entities for the window, with auto-pagination until complete. Pull current balances via getAccounts.

3. Pull PayPal. Read transactions (sales, subscription payments, invoice payments, refunds, fees and transfers to the bank) and open disputes for the window through the PayPal connector. Note PayPal balance transfers that have been initiated but not yet landed in Mercury.

4. Translate. Map every transaction through canonical-categories before aggregating. Route unmapped items to the Unmapped Categories section.

5. Compute in an analysis artifact: total inflows and outflows per entity, net cash movement, ending balances per account, top 5 largest transactions each direction, and week-over-week delta against the prior period.

6. Flag anomalies:
   - Any single transaction over 2,500 dollars not seen in the prior 8 weeks
   - Any recurring charge that changed amount by more than 15 percent
   - Any new counterparty receiving money
   - Duplicate-looking charges (same counterparty, same amount, within 3 days)
   - Any dispute or refund, individually listed
   - Internal transfers that do not net to zero
   - Any Stripe deposit or debit in Mercury, listed as legacy Stripe wind-down

7. Reconcile PayPal to Mercury at the transfer level: every PayPal transfer to the bank in the window should appear as a Mercury deposit. List any transfer older than 3 business days that has not landed.

## Report format

Plain text, no bold, no dividers. Structure:

Bottom line: one or two sentences on cash position and the single most important thing this week.
Expert Partners LLC: inflows, outflows, net, ending cash, notable items.
Moxie Signature Group: same structure.
Anomalies and flags: the list from step 6, with the evidence.
PayPal transfer reconciliation: clean or listed exceptions.
Unmapped categories: proposed mappings added to the map, if any.
Week over week: the delta and what drove it.

## Guardrails

Never blend entities in a total. Never count internal transfers as inflow or outflow. Every figure carries source and as-of date. If Mercury or PayPal fails mid-pull, report what completed and name what is missing rather than estimating. Never reach for Stripe as a substitute source.
