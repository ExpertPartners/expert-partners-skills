---
name: weekly-cash-flow-review
description: Run Allison's weekly cash flow review across Mercury and Stripe. Use whenever she asks for a cash flow review, weekly money check, "where's my cash", "how did this week look", what came in and went out, or any request to review recent business cash movement. Also use when she asks about anomalies, large transactions, or week-over-week comparison. Trigger even without the word "weekly" when the intent is reviewing recent cash activity.
---

# Weekly Cash Flow Review

Inherits the operating-doctrine skill and the Fractional CFO project instructions. Read-only. All math in code, never eyeballed.

## What this produces

One report: bottom line first, then inflows, outflows, anomalies, and week-over-week movement, per entity, never blended.

## Steps

1. State the window. Default is the last 7 full days; extend to 14 if she asks or if the prior review is more than a week old. State the as-of timestamp.

2. Pull Mercury. Use listTransactions for every account across both entities for the window, with auto-pagination until complete. Pull current balances via getAccounts.

3. Pull Stripe. Read charges, payouts, refunds, and disputes for the window. Note payouts in transit (created but not yet landed in Mercury).

4. Translate. Map every transaction through canonical-categories before aggregating. Route unmapped items to the Unmapped Categories section.

5. Compute in an analysis artifact: total inflows and outflows per entity, net cash movement, ending balances per account, top 5 largest transactions each direction, and week-over-week delta against the prior period.

6. Flag anomalies:
   - Any single transaction over 2,500 dollars not seen in the prior 8 weeks
   - Any recurring charge that changed amount by more than 15 percent
   - Any new counterparty receiving money
   - Duplicate-looking charges (same counterparty, same amount, within 3 days)
   - Any dispute or refund, individually listed
   - Internal transfers that do not net to zero

7. Reconcile Stripe to Mercury at the payout level: every Stripe payout in the window should appear as a Mercury deposit. List any payout older than 3 business days that has not landed.

## Report format

Plain text, no bold, no dividers. Structure:

Bottom line: one or two sentences on cash position and the single most important thing this week.
Expert Partners LLC: inflows, outflows, net, ending cash, notable items.
Moxie Signature Group: same structure.
Anomalies and flags: the list from step 6, with the evidence.
Stripe payout reconciliation: clean or listed exceptions.
Unmapped categories: proposed mappings needing approval, if any.
Week over week: the delta and what drove it.

## Guardrails

Never blend entities in a total. Never count internal transfers as inflow or outflow. Every figure carries source and as-of date. If Mercury or Stripe fails mid-pull, report what completed and name what is missing rather than estimating.
