---
classification: internal
classification_owner: allison
classification_date: 2026-09-21
date: 2026-09-21
source: Phase Two research compared with live ADRs 0056, 0078, 0022, 0025, 0027 and Manifest v1.20
topic: proposed knowledge architecture baseline amendments
---
# Founder decision packet: proposals only

No proposal below is adopted, and no dependent automation was built. The v1.3 audit can inventory and safely repair evidenced gaps under existing authority without these amendments. Destination for decisions: NORTH'S ESTATE CONTROL TOWER / Repo Tower. Any accepted Estate-wide amendment belongs in Aura through a separately authorized governance pass, not this worker.

## 1. Document types and richer metadata

**Exact proposed rule:** Adopt one documented vocabulary for governed knowledge, with required type, stable ID, owner, scope and lifecycle metadata and type-specific provenance fields. Keep ADR 0025's `classification`, classification owner/date and all four classes. Require an approved schema with explicit field applicability before adding CI enforcement.

**Uncovered today:** ADR 0056 names date/source/topic/classification; ADR 0025 defines classification handling. Neither adopts the research's 21-type catalog or universal richer schema. Research itself uses `distilled`, `disposition`, `applicability` and `exception` outside its principal catalog, so copying it directly would be inconsistent.

**Automation dependent:** Universal schema checks, type-aware index generation, owner/ID resolution and typed source lineage.

**Migration impact:** Existing skill `status: live`, ADR `accepted`, ruling `standing/reconstructed`, manifest and repo-specific metadata cannot be rewritten to fit a new enum without a compatibility map. The Entity index names repository owners; it is not a person/role-handle directory.

**Recommendation:** Approve development of a minimal schema proposal and compatibility pilot, not wholesale adoption of the research schema. Existing fields and source formats remain valid until the exact schema and migration scope are accepted.

## 2. Accepted canon and lifecycle

**Exact proposed rule:** Define, for each governed document type, the evidence of adoption, current force and supersession required for inclusion in current-answer retrieval. Specify how those states map to existing ADR and ruling statuses; merging a draft or changing a field alone must not establish authority.

**Uncovered today:** The Estate already distinguishes research, unreviewed intake and accepted rulings. It does not use the research's single definition (default branch plus status active plus review window) for every document. Dated ruling files can live in Aura intake, contradicting a blanket folder exclusion.

**Automation dependent:** Type/status compatibility, current-canon filtering and machine validation of promotion/supersession chains.

**Migration impact:** Preserve current accepted/standing/reconstructed records, explicit successors and intake rulings. Do not mark existing documents noncanonical solely for missing new fields.

**Recommendation:** Adopt an explicit compatibility-aware definition if desired; reject the literal universal `status: active` test and blanket research/intake directory filter.

## 3. Authority tiers and disposition permissions

**Exact proposed rule:** Establish an Estate-wide table mapping content operations and owner roles to existing delegated authority, required approvals, and founder-only gates, before automating semantic promotions or cross-repo dispositions.

**Uncovered today:** Path two, ADR 0022 and standing push rules already have specific delegation. The research's Tier 0/1/2 and one-human-gate lifecycle would replace or narrow parts of that authority. A report verb does not confer a new permission.

**Automation dependent:** Automatic semantic disposition execution, approval routing, downstream writes or adoption of approval-ref fields as sufficient authority.

**Migration impact:** Must reconcile existing reversible-work authorization and actual staffed roles, without adding unnecessary approvals or weakening destructive/access/business-truth gates.

**Recommendation:** Preserve existing authority. Do not adopt a new tier system unless a concrete unresolved operation proves the need.

## 4. Verification dates and review intervals

**Exact proposed rule:** Define a substantive verification field and event, distinct from modification and classification dates, with explicit per-type review triggers or intervals. Expiry creates a review finding, never automatic retirement or loss of authority.

**Uncovered today:** The Manifest has its own review cadence and timestamp contract; ADR 0056 has intake cadence. There is no universal per-document verified/review_by schema or per-type expiry rule.

**Automation dependent:** Review-due reports, freshness badges and checks based on substantive verification.

**Migration impact:** Existing timestamps cannot be relabeled as verification without evidence. No mass re-dating or scheduled semantic review follows from this skill change.

**Recommendation:** Use existing substantive evidence now. Require a bounded trigger/field proposal before introducing universal intervals or new recurring jobs.

## 5. Mandatory directories and indexes

**Exact proposed rule:** If a common physical foundation is desired, define its applicability per current Entity type and its relationship to existing owner taxonomies, preserving framework-native application layout and existing curated-index names.

**Uncovered today:** ADR 0056 requires lean instructions, intake handling and a described index, not the report's five lifecycle directories. ADR 0022 already specifies applicable brand taxonomy; current owner canon may have recorded successors.

**Automation dependent:** New scaffold requirements, universal path validators and mandatory directory migrations.

**Migration impact:** Broad moves can break consumers and supersede accepted layouts. Literal INDEX.md and canon/ everywhere would create avoidable change.

**Recommendation:** Do not adopt the universal tree. Continue class-aware assessments using current conventions; bring specific unsolved layout gaps back with evidence.

## 6. Decision records for all business decisions

**Exact proposed rule:** Define which consequential business decisions must be recorded as formal decision records, and how that relates to existing Aura ruling-of-record and repo-scoped ADR mechanisms.

**Uncovered today:** ADR 0056 point 9 governs repos carrying decisions and requires MADR integrity/preserved supersession. It does not require every business decision in every repo to become a new numbered ADR.

**Automation dependent:** Mandatory business-decision coverage checks, universal numbering and new acceptance gates.

**Migration impact:** Must not duplicate existing dated rulings or renumber historical records. Existing documented decisions remain evidence.

**Recommendation:** Keep the present mechanisms until actual decision gaps justify a precise coverage amendment.

## 7. Consumer notices and derived human views

**Exact proposed rule:** Define the source and maintenance contract for consumer relationships and any generated human view, including audience filtering and the authority required for automated downstream notices.

**Uncovered today:** One-owner pointers and generated-copy controls exist. A required consumers field, cross-repo intake fan-out, weekly digest, monthly retrieval schedule and Notion view service are not adopted by this research.

**Automation dependent:** Reverse consumer indexes, automatic notices, derived Notion generation and new scheduled checks.

**Migration impact:** Adds metadata ownership, external writes and possible duplicate queues. Existing systems of record and classification distribution boundaries must remain intact.

**Recommendation:** Preserve the derived-view principle and assess real consumers now. Authorize a concrete implementation only after its source schema, audience and write scope are settled.

## Matters already covered, not new founder decisions

ADR 0025 already addresses finance/legal/client sensitivity, confidentiality and restricted host-only material. Do not replace it with the research's three-class `confidentiality` field or imply labels grant access. Unknown handling is a case-specific stop and verification task, not a reason to invent a new global classification contract. Current Manifest Entity ownership, one-owner pointers, source preservation, and existing baseline checks are retained. No new vector store, knowledge graph, watcher or alternative repo skill is warranted by this change.
