---
name: canonical-categories
description: Background translation layer for normalizing financial data across Mercury, QuickBooks, Stripe, and Monarch into one canonical category scheme. Load whenever any analysis aggregates, compares, or reports transactions from more than one source, or whenever category mapping, normalization, or unmapped transactions come up. This skill is background knowledge, not a user-facing workflow.
disable-model-invocation: false
user-invocable: false
---

# Canonical Categories (Background Skill)

Inherits the operating-doctrine skill and the Fractional CFO project instructions.

## What this skill does

It enforces one behavior: no cross-source financial math happens on raw source categories. Everything translates to the canonical scheme first.

## The map

The authoritative map lives in project knowledge at canonical-categories.md. That file, not this skill, holds the current mappings. Read it fresh at the start of any normalization; do not rely on remembered mappings, because the map evolves as Allison approves new rows.

## Translation procedure

1. Read canonical-categories.md from project knowledge.
2. Translate at the transaction level, before any aggregation.
3. One transaction, one canonical category.
4. Transfers (xfer-*) never enter income or expense totals.
5. Apply the entity-separation rules alongside translation; category and entity are assigned together.

## Unmapped handling

When a source category, Stripe product, or Monarch category has no row in the map:

1. Do not guess silently and do not dump it into an other bucket.
2. Propose a mapping with one line of reasoning.
3. Put the proposal in an Unmapped Categories section at the end of the report.
4. After Allison approves, update canonical-categories.md in project knowledge so the map stays current.

## Conflict rule

When two sources categorize the same underlying transaction differently, QuickBooks wins for financial statement purposes, and the mismatch gets flagged for bookkeeping cleanup. Mercury wins for cash position purposes. The report never shows two different numbers for the same thing without naming why.
