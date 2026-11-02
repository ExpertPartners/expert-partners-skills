---
name: runway-and-burn
description: Compute burn rate, runway, and revenue sensitivity for Allison's businesses. Use whenever she asks about runway, burn, "how long can we go", cash cushion, sustainability, whether she can afford something, hiring affordability, what happens if revenue drops, or any forward-looking cash question. Trigger for scenario and what-if questions about cash, not just the literal words burn or runway.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-11-02 (Decision Log 2026-10-25, Which of the 19 personal
# skills move into the marketplace). Moved in from Allison's claude.ai skills.
tier: plugin
zone: finance
status: live
inherits: operating-doctrine
calls:
  - canonical-categories
  - entity-separation
brand-scope: null
subtitle: "burn, runway and revenue sensitivity"
---

# Runway and Burn

Inherits the operating-doctrine skill and the Fractional CFO project instructions. Read-only. All computation in code with the work shown.

## What this produces

Per entity: net monthly burn or surplus, months of runway at current trajectory, and a sensitivity table showing how runway moves when revenue moves.

## Definitions (use these exactly)

Gross burn: total monthly cash outflows, excluding transfers.
Net burn: gross burn minus monthly cash inflows. Negative net burn means the business is cash flow positive; say surplus, not negative burn.
Runway: current available cash divided by net burn, in months. If net burn is a surplus, runway is not the framing; report the monthly surplus and cushion instead.
Available cash: Mercury operating balances. Treasury balances get shown separately with a note on liquidity timing. Tax reserve balances are excluded from available cash and shown separately; spending the tax reserve is not runway.

## Steps

1. Pull Mercury balances per account per entity, tagged as operating, treasury, or tax reserve based on account names and the systems map. If an account's role is ambiguous, ask once and record the answer in project memory.

2. Compute trailing burn from Mercury transactions: 3-month and 6-month trailing averages of inflows and outflows through canonical categories, transfers excluded. Show both windows; if they diverge more than 20 percent, name what changed.

3. Cross-check against QuickBooks: trailing P&L expense average versus Mercury outflow average. Material divergence usually means timing (annual prepays, credit card float) or booking issues; name which.

4. Identify lumpy items: annual renewals, event production spikes, quarterly tax payments. Separate baseline burn from lumpy burn and show both.

5. Compute runway: available cash divided by net burn, using the 3-month trailing figure as primary and 6-month as the check.

6. Sensitivity table: runway at revenue of minus 30 percent, minus 15 percent, current, plus 15 percent, and plus 30 percent, holding expenses flat. Then one line on what expense flex exists (the largest discretionary canonical categories) if revenue drops.

7. Stripe forward signal: current active subscription MRR and its 3-month trend, as the leading indicator on the revenue side of the model.

## Report format

Plain text, no bold, no dividers. Structure:

Bottom line: runway or surplus per entity in one sentence each.
The numbers: available cash, tax reserve (separate), treasury (separate), gross burn, net burn, per entity.
Sensitivity: the five-scenario table.
What moves it: lumpy items ahead, MRR trend, and the biggest single lever.
Confidence notes: as-of dates, and any divergence between the 3-month and 6-month views.

## Guardrails

Never blend entities. Never count the tax reserve as spendable. Never present a single-point runway number without the sensitivity table. Projections are trailing-average extrapolations, and the report says so; this skill does not predict revenue, it shows what current trajectory implies.
