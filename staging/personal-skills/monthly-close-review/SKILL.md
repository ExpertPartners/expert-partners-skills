---
name: monthly-close-review
description: Run Allison's monthly close review after month end. Use whenever she asks to review the month, check the close, reconcile the books, compare QuickBooks to the bank, review the P and L, "how did the month look", or any request that reconciles accounting records against actual bank and payment activity. Trigger for month-end, quarter-end, and year-end review requests.
---

# Monthly Close Review

Inherits the operating-doctrine skill and the Fractional CFO project instructions. Read-only: this skill reviews the close, it does not perform the close. It never posts, edits, or deletes anything in QuickBooks.

## What this produces

A close summary per entity that answers three questions: do the books match the bank, do the books match the payment processor, and what does the month actually say about the business.

## Steps

1. Confirm the period. Default is the most recently completed calendar month. State the as-of timestamp for every source.

2. Pull QuickBooks: P&L for the period, balance sheet as of period end, cash flow statement, AR aging summary, AP aging summary. Pull the prior period P&L for comparison.

3. Pull Mercury: getAccountStatements for the period for every account, plus listTransactions for the period as the detail layer.

4. Pull Stripe: charges, refunds, fees, and payouts for the period.

5. Reconcile cash. QuickBooks bank account balances at period end versus Mercury statement ending balances, account by account. List every difference with the amount.

6. Reconcile revenue. Stripe gross charges minus refunds for the period versus revenue booked in QuickBooks for Stripe-collected income. Reconcile Stripe fees against cod-merchant-fees in the books. Flag timing differences (payouts in transit at period end) separately from real mismatches.

7. Analyze the P&L through canonical categories: revenue by canonical line, expenses by canonical line, gross margin, net income, and the three largest movements versus prior month with the driver named for each.

8. Review AR and AP aging: anything past 60 days gets named individually with the counterparty and amount.

9. Flag close quality issues: uncategorized transactions in QuickBooks, negative balances that should not be negative, transfers booked as income or expense, and any account that moved more than 25 percent month over month without an obvious driver.

## Report format

Plain text, no bold, no dividers. Structure:

Bottom line: the month in two or three sentences, per entity.
Cash reconciliation: clean, or the exception list.
Revenue reconciliation: clean, or the exception list.
P&L story: revenue, margin, net income, and the three biggest movers with drivers.
AR and AP: aging exceptions past 60 days.
Close quality flags: the bookkeeping cleanup list, ready to hand to the bookkeeper.
Unmapped categories: proposed mappings needing approval, if any.

## Guardrails

Entities never blend. Timing differences are labeled as timing, not errors. Every reconciling item shows both sides with amounts. If a QuickBooks report and the Mercury statement disagree, the report says so plainly; it never forces them to match. Fix paths are recommendations for the bookkeeper, not actions this skill takes.
