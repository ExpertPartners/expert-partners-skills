---
classification: internal
classification_owner: allison
classification_date: 2026-09-21
date: 2026-09-22
source: Phase Two digest reconciled with live ADRs 0056, 0060, 0078, 0022, 0025, 0027, 0047 and Manifest v1.21
topic: proposed knowledge architecture baseline amendments
---
# Founder decision packet: proposals only

No proposal below is adopted, and no dependent automation was built. The v1.4 audit can inventory and safely repair evidenced gaps under existing authority without these amendments. Current decision destination: NORTH'S ESTATE CONTROL TOWER / Repo Design Tower (this packet originated at Repo Tower; its seven items are preserved). Any accepted Estate-wide amendment belongs in Aura through a separately authorized governance pass, not this worker.

## September 22 digest reconciliation

Read live through Estate Brain: `aura docs/research/digests/2026-09-22-phase-two-internal-knowledge-architecture-for-the-expert-partners-estate-reposit.md`, disposition `awaiting ruling`, `core: false`, source revision `headRevisionId:0B1at6OUW67YURGgxT1BxTnozVEFZWVV3K29vdG5DNUsrdUtrPQ`, source hash prefix `f63e60c12d748c4f`. The digest was sufficient for this reconciliation; the original was not escalated to or reread. Section references below are the digest's source-section anchors, not claims of a new original-source read.

The digest's advisory suggestion to adopt the vocabulary/schema and three authority tiers now is not accepted here. The existing seven-item packet remains the decision unit. `ADOPT NOW` below is a recommendation for Allison's ruling, not an adoption receipt. Exact proposed ADR text appears only for that recommendation. No Aura amendment, universal schema, new status, directory tree, watcher, database or control plane is implemented.

| Item | Recommendation | Minimum outcome |
| --- | --- | --- |
| 1. Types and metadata | PILOT FIRST | Map existing formats to identity, owner, authority, source and verification before proposing fields. |
| 2. Accepted canon | ADOPT NOW | Add the compatibility clarification below to ADR 0056 point 10; no new universal lifecycle. |
| 3. Authority tiers | REJECT / KEEP CURRENT RULE | Preserve existing delegation and founder gates. |
| 4. Verification dates | PILOT FIRST | Prove a substantive verification event; no global intervals or expiry of authority. |
| 5. Directories and indexes | REJECT / KEEP CURRENT RULE | Existing class-aware layouts and curated-index conventions remain. |
| 6. Business decision records | REJECT / KEEP CURRENT RULE | Use ADR 0060 and existing ADR/ruling mechanisms; no universal numbered ADR mandate. |
| 7. Consumer notices and views | PILOT FIRST | Prove one-way owner-derived views and audience boundaries before scoped implementation. |

## 1. Document types and richer metadata

**Exact proposed rule:** Adopt one documented vocabulary for governed knowledge, with required type, stable ID, owner, scope and lifecycle metadata and type-specific provenance fields. Keep ADR 0025's `classification`, classification owner/date and all four classes. Require an approved schema with explicit field applicability before adding CI enforcement.

**Uncovered today:** ADR 0056 names date/source/topic/classification; ADR 0025 defines classification handling. Neither adopts the research's 21-type catalog or universal richer schema. Research itself uses `distilled`, `disposition`, `applicability` and `exception` outside its principal catalog, so copying it directly would be inconsistent.

**Automation dependent:** Universal schema checks, type-aware index generation, owner/ID resolution and typed source lineage.

**Migration impact:** Existing skill `status: live`, ADR `accepted`, ruling `standing/reconstructed`, manifest and repo-specific metadata cannot be rewritten to fit a new enum without a compatibility map. The Entity index names repository owners; it is not a person/role-handle directory.

**Recommendation: PILOT FIRST.** Digest B.1/B.5 supports inspectable meaning, but its 21-type catalog and 11-field schema have no adoption basis. Pilot a mapping of existing records to identity, owner, authority, source and substantive verification, including skill/ADR/ruling/digest compatibility. Keep ADR 0025 unchanged. A successful pilot and an exact schema/migration proposal must precede any universal standard or CI gate.

## 2. Accepted canon and lifecycle

**Exact proposed rule:** Define, for each governed document type, the evidence of adoption, current force and supersession required for inclusion in current-answer retrieval. Specify how those states map to existing ADR and ruling statuses; merging a draft or changing a field alone must not establish authority.

**Uncovered today:** The Estate already distinguishes research, unreviewed intake and accepted rulings. It does not use the research's single definition (default branch plus status active plus review window) for every document. Dated ruling files can live in Aura intake, contradicting a blanket folder exclusion.

**Automation dependent:** Type/status compatibility, current-canon filtering and machine validation of promotion/supersession chains.

**Migration impact:** Preserve current accepted/standing/reconstructed records, explicit successors and intake rulings. Do not mark existing documents noncanonical solely for missing new fields.

**Recommendation: ADOPT NOW, compatibility clarification only.** Digest B.2/B.6/B.10 makes the risk concrete, but its literal active-status, review-window and folder tests conflict with current formats. ADR 0060 already controls who creates durable decisions, supersession and conflict handling. Make that dependency explicit in ADR 0056 without adopting the research lifecycle.

**Exact proposed ADR-0056 amendment language, append to point 10 (proposal only):**

> Current-answer retrieval must trace the owning source and evidence that it remains in force under the applicable accepted decision and supersession process, including ADR 0060 for durable decisions. Preserve each existing record type's status convention; do not require a universal `status: active`, infer adoption from merge or metadata alone, or remove authority solely because a new field is absent or a research-proposed review window has elapsed. Research and ordinary intake are evidence, not authority. Verify specifically recorded accepted rulings in Aura intake under the ruling-of-record format and ADR 0060 rather than excluding them by folder. If current authoritative claims conflict without an accepted supersession, stop the affected operation and route the conflict to Allison. If the owning canon cannot be reached through authorized live paths, report `cannot verify`; do not substitute a derived view, research or memory.

This text adds no authority tier, promotion permission or metadata schema. All other items remain outside this proposed amendment.

## 3. Authority tiers and disposition permissions

**Exact proposed rule:** Establish an Estate-wide table mapping content operations and owner roles to existing delegated authority, required approvals, and founder-only gates, before automating semantic promotions or cross-repo dispositions.

**Uncovered today:** Path two, ADR 0022 and standing push rules already have specific delegation. The research's Tier 0/1/2 and one-human-gate lifecycle would replace or narrow parts of that authority. A report verb does not confer a new permission.

**Automation dependent:** Automatic semantic disposition execution, approval routing, downstream writes or adoption of approval-ref fields as sufficient authority.

**Migration impact:** Must reconcile existing reversible-work authorization and actual staffed roles, without adding unnecessary approvals or weakening destructive/access/business-truth gates.

**Recommendation: REJECT / KEEP CURRENT RULE.** Digest B.6/F and its advisory three-tier recommendation do not supersede existing operation-specific authority. Keep reversible-work delegation, ADR 0060 decision authority and destructive/access/business-truth gates. Report dispositions describe actions; they grant no permission. No new tiers or approval-ref shortcut.

## 4. Verification dates and review intervals

**Exact proposed rule:** Define a substantive verification field and event, distinct from modification and classification dates, with explicit per-type review triggers or intervals. Expiry creates a review finding, never automatic retirement or loss of authority.

**Uncovered today:** The Manifest has its own review cadence and timestamp contract; ADR 0056 has intake cadence. There is no universal per-document verified/review_by schema or per-type expiry rule.

**Automation dependent:** Review-due reports, freshness badges and checks based on substantive verification.

**Migration impact:** Existing timestamps cannot be relabeled as verification without evidence. No mass re-dating or scheduled semantic review follows from this skill change.

**Recommendation: PILOT FIRST.** Digest B.5/B.7 correctly separates verification from edits. Pilot an evidenced substantive verification event and map it to existing timestamps on a bounded sample. Define success and exceptions before proposing any shared field. No universal intervals, mass re-dating, automatic retirement or recurring job is authorized.

## 5. Mandatory directories and indexes

**Exact proposed rule:** If a common physical foundation is desired, define its applicability per current Entity type and its relationship to existing owner taxonomies, preserving framework-native application layout and existing curated-index names.

**Uncovered today:** ADR 0056 requires lean instructions, intake handling and a described index, not the report's five lifecycle directories. ADR 0022 already specifies applicable brand taxonomy; current owner canon may have recorded successors.

**Automation dependent:** New scaffold requirements, universal path validators and mandatory directory migrations.

**Migration impact:** Broad moves can break consumers and supersede accepted layouts. Literal INDEX.md and canon/ everywhere would create avoidable change.

**Recommendation: REJECT / KEEP CURRENT RULE.** Digest B.4 yields to live conventions. Preserve ADR 0022 where applicable and its accepted successors, ADR 0056 point 10 and the current Entity class. Two usable front doors plus an owner-linked knowledge spine are design concerns, not five mandatory physical directories. No universal empty tree, literal INDEX.md mandate or Template Repo.

## 6. Decision records for all business decisions

**Exact proposed rule:** Define which consequential business decisions must be recorded as formal decision records, and how that relates to existing Aura ruling-of-record and repo-scoped ADR mechanisms.

**Uncovered today:** ADR 0056 point 9 governs repos carrying decisions and requires MADR integrity/preserved supersession. It does not require every business decision in every repo to become a new numbered ADR.

**Automation dependent:** Mandatory business-decision coverage checks, universal numbering and new acceptance gates.

**Migration impact:** Must not duplicate existing dated rulings or renumber historical records. Existing documented decisions remain evidence.

**Recommendation: REJECT / KEEP CURRENT RULE.** The digest's business-wide decision-record suggestion adds no demonstrated gap beyond ADR 0060's durable-decision protocol and existing repo-scoped ADR/ruling mechanisms. Retain ADR 0056 point 9 integrity for repositories carrying decisions. Do not duplicate dated rulings or require every business choice to become a numbered ADR.

## 7. Consumer notices and derived human views

**Exact proposed rule:** Define the source and maintenance contract for consumer relationships and any generated human view, including audience filtering and the authority required for automated downstream notices.

**Uncovered today:** One-owner pointers and generated-copy controls exist. A required consumers field, cross-repo intake fan-out, weekly digest, monthly retrieval schedule and Notion view service are not adopted by this research.

**Automation dependent:** Reverse consumer indexes, automatic notices, derived Notion generation and new scheduled checks.

**Migration impact:** Adds metadata ownership, external writes and possible duplicate queues. Existing systems of record and classification distribution boundaries must remain intact.

**Recommendation: PILOT FIRST.** Digest B.8/B.11 supports one owner and derived human navigation; its notification fan-out and schedules are unadopted machinery. Preserve the one-way owning-canon-to-view principle now. Before implementation, pilot with existing sources to prove traceable source revisions, an owner correction route, audience/classification boundaries and repeat-run stability. No consumer service, Notion write, recurring sweep or second editable canon is authorized by this packet.

## Matters already covered, not new founder decisions

ADR 0025 already addresses finance/legal/client sensitivity, confidentiality and restricted host-only material. Do not replace it with the research's three-class `confidentiality` field or imply labels grant access. Unknown handling is a case-specific stop and verification task, not a reason to invent a new global classification contract. Current Manifest Entity ownership, one-owner pointers, source preservation, and existing baseline checks are retained. No new vector store, knowledge graph, watcher or alternative repo skill is warranted by this change.
