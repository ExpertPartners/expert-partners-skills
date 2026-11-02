---
name: entity-separation
description: Dual-view rule set for Allison's finances. One dataset, two lenses. The blended owner lens (Monarch cockpit) shows business and personal together from Allison's perspective and is the default for day-to-day money questions. The entity-clean lens keeps Expert Partners LLC, Moxie Signature Group, and personal separated for the books, taxes, and LLC protection. Use in every financial analysis in this project, and directly whenever Allison asks whether entities are clean, whether something was booked to the right company, about commingling, owner draws, intercompany transfers, or which entity a transaction belongs to.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-11-02 (Decision Log 2026-10-25, Which of the 19 personal
# skills move into the marketplace). Moved in from Allison's claude.ai skills.
tier: plugin
zone: finance
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "blended owner lens and entity-clean lens"
---

# Entity Separation (Dual-View, v2)

Inherits the operating-doctrine skill and the Fractional CFO project instructions. This skill is a rule set that other skills apply, plus a standalone audit mode.

## The two lenses (the core change in v2)

Same transactions, two views. Neither replaces the other.

1. Blended owner lens. Business and personal in one picture, Allison's perspective, not IRS reporting. This is the DEFAULT lens for cash flow questions, spending questions, "where is my money" questions, and anything cockpit-shaped. Monarch is the home of this lens: it aggregates Mercury and personal accounts itself and Allison categorizes there.
2. Entity-clean lens. Expert Partners LLC, Moxie Signature Group, and Personal, never combined in a total. This lens is MANDATORY for anything that touches the books, taxes, the monthly close, per-entity runway, and any output going to the bookkeeper or CPA. QuickBooks is the home of this lens and its chart of accounts is the shared category language both lenses map to.

Why both: the blended view is how Allison actually runs her life and decisions. The clean view is what protects the LLC liability shield and keeps taxes defensible. Collapsing to one view sacrifices the other's job. We do not collapse.

## The three worlds (unchanged, they live inside the clean lens)

1. Expert Partners LLC: coaching company. EPIC, Expert Partners programs, events, Don Hobbs IP portfolio (Gateway to Mastery, Think Big Live Big, 2020 Vision), and revenue billing under the LLC including Free Agent Movement and AG personal brand offers.
2. Moxie Signature Group: real estate team under eXp Realty. Commissions, eXp revenue share, MLS and license costs, team expenses.
3. Personal: household finances, from Monarch.

## Hard rules

1. Every report states which lens it is using. Blended outputs are labeled blended. Clean outputs are labeled per entity.
2. In the entity-clean lens, no total, chart, average, or trend ever combines entities.
3. Every transaction gets an entity assignment before it enters any clean-lens aggregate. The blended lens still carries the assignment underneath; blending is a presentation choice, not a data merge that erases labels.
4. Cross-entity and owner flows are transfers, shown from both sides, in both lenses:
   - Owner draws and distributions: out of the business, into personal. Never expense.
   - Owner contributions: reverse direction. Never income.
   - Intercompany: flagged for a documented business purpose.
5. A draw that carries a business expense GL code in QuickBooks (vehicle, legal, or anything else) is a contamination flag, every time, until the bookkeeper resolves it. This pattern was observed live in July 2026; it is not hypothetical.
6. Personal-pattern spending on a business account, or business-pattern spending on a personal account, gets flagged, never reclassified silently. In the blended lens it still appears, with its flag visible.
7. Books stay clean even when the cockpit is blended. No blended number is ever written back toward QuickBooks.

## Entity assignment logic

Mercury: assignment follows the account. All Mercury accounts sit legally under Expert Partners LLC; functional assignment follows the account's job (the eXp Revenue Share, Moxie Passthrough Team Commissions, AG Real Estate Commissions, and Real Estate Ads accounts carry the real estate side). Record the account-to-entity mapping in project memory at first run and reuse it.
QuickBooks: assignment follows the company file, and the QBO chart of accounts is the canonical category reference for both lenses.
Stripe: assignment follows the account, and within it, the product map in canonical-categories.
Monarch: the blended home. Personal accounts in Monarch are Personal; business accounts Monarch aggregates (Mercury) keep their business assignment underneath the blend.

## Ambiguity protocol

When a transaction's entity is unclear, do not guess. Place it in an Entity Review section with the evidence and a recommended assignment, and let Allison confirm. Confirmed assignments for recurring counterparties get recorded in project memory so the question is asked once.

## Standalone audit mode

When Allison asks for an entity cleanliness check, run this over the trailing 90 days:

1. Pull all Mercury transactions and scan for personal-pattern merchants on business accounts (groceries, personal retail, personal subscriptions, gym, streaming).
2. Scan the newest Monarch snapshot for business-pattern merchants on personal accounts (business SaaS, ads platforms, contractor payments); flag as reimbursement candidates, do not move them.
3. List every owner draw and contribution with dates and amounts, both sides, and check each one's GL code in QuickBooks for the rule 5 miscoding pattern.
4. List every intercompany transfer and whether the purpose is evident.
5. Produce a contamination report: item, account, amount, why it looks misplaced, and the recommended fix (reimbursement, reclassification by the bookkeeper, or confirmation that it is correctly placed).

## Why this is non-negotiable

Commingling weakens LLC liability protection and creates tax exposure. The blended cockpit exists so Allison sees her whole financial life her way. This skill exists so that view never costs her the legal and tax protection the clean books provide. Both, structurally, every report.

## Version

v2.1, July 7, 2026. Dual-view rewrite per Allison's direction: Monarch is the blended owner cockpit for Allison and Claude, QuickBooks is the category reference and entity-clean books for taxes, and the n8n bridge feeds Monarch snapshots to the project nightly so Cowork stays the driver. Replaces v1 "never blend" with "clean books plus an explicit blended owner lens."
