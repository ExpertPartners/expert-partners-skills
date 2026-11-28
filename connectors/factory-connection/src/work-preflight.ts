// Policy is a derived view of existing owning records, never another work queue.
export type WorkIntent = {
 action: "source_search" | "replacement_build" | "continue" | "inspect" | "escalate";
 capabilityId: string;
 outcome?: string;
 evidence?: string[];
 recommendation?: string;
};
export type WorkPolicy = {
 version: 1;
 source: { url: string; revision: string; companyToolBuilderSession?: string;
  decisionLogUrl?: string; founderDecisionActor?: string; decisionReceiptDigest?: string;
  decisionRecoveryFallback?: {id:string;recovery:"closed"|"open";decisionId:string;aliases:string[];sourceUrl:string}[];
  decisionAuthority?: {status:"verified"|"unverified";url:string;revision?:string;gapOverrides:string[];sourceOnlyClosures:string[]};
 };
 checks?: {stage: string; evidence: unknown}[];
 items: {
  id: string; aliases: string[]; sourceRecovery: "closed" | "open" | "unverified";
  decisionUrl: string; ownerSession: string; implementation: string;
  installed: boolean; replacementApproved: boolean;
  evidence: string[];
 }[];
};
export function validPolicy(p: unknown): p is WorkPolicy {
 const v = p as WorkPolicy;
 return !!v && v.version === 1 && !!v.source?.url && !!v.source.revision &&
  Array.isArray(v.items) && v.items.every(i => !!i.id && Array.isArray(i.aliases) &&
   i.aliases.every(a => typeof a === "string" && a.length > 2) &&
   ["closed", "open", "unverified"].includes(i.sourceRecovery) && !!i.decisionUrl &&
   typeof i.ownerSession === "string" && typeof i.implementation === "string" &&
   typeof i.installed === "boolean" && typeof i.replacementApproved === "boolean" &&
   Array.isArray(i.evidence));
}
export function workPreflight(policy: WorkPolicy, intent: WorkIntent, targetSession?: string) {
 const direct = policy.items.find(i => i.id === intent.capabilityId);
 const normalized = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
 const outcome = normalized(intent.outcome ?? "");
 const equivalents = outcome ? policy.items.filter(i => [i.id,...i.aliases].some(a => normalized(a) === outcome)) : [];
 const ambiguous = equivalents.length>1;
 const conflict = !!direct && equivalents.some(i=>i.id!==direct.id);
 const item = ambiguous ? undefined : conflict ? equivalents[0] : direct ?? equivalents[0];
 const evidence = item ? [item.decisionUrl, ...item.evidence] : intent.evidence ?? [];
 const result = (allowed: boolean, code: string, reason: string) => ({
  allowed, code, reason, capabilityId: item?.id ?? intent.capabilityId,
  ownerSession: item?.ownerSession || null, evidence, source: policy.source,
 });
 if (intent.action === "inspect") return result(true, "INSPECTION", "Read existing records without commissioning work.");
 if (intent.action === "escalate") return result(!!intent.recommendation?.trim() && !!intent.evidence?.length,
  "FOUNDER_RECOMMENDATION", "Carry the specific recommendation and source evidence to Allison through the existing owner.");
 if (ambiguous) return result(false,"AMBIGUOUS_CAPABILITY_OUTCOME","The outcome matches more than one existing disposition. Reconcile those existing records before commissioning or continuing work.");
 if (conflict) return result(false,"CAPABILITY_OUTCOME_CONFLICT","The capability ID and outcome identify different existing work. Route the outcome to its existing owner; do not dispatch this conflicting request.");
 if (!item) return result(false, "RECONCILE_FIRST", "Reconcile current decisions, gap dispositions, installed capability and ownership in the existing records first.");
 if (intent.action === "source_search" && item.sourceRecovery!=="closed" && (item.sourceRecovery==="unverified" || policy.source.decisionAuthority?.status==="unverified"))
  return result(false,"SOURCE_AUTHORITY_UNVERIFIED","Source authority is unverified. Restore the existing decision record before source recovery; approved implementation remains separate.");
 if (intent.action === "source_search") return result(false,
  item.sourceRecovery === "closed" ? "SOURCE_RECOVERY_CLOSED" : "EXISTING_SEARCH_OWNER",
  item.sourceRecovery === "closed" ? "Allison closed source recovery. Only an explicit superseding decision in the owning record can reopen it." :
   "Use the existing source owner and its one bounded search assignment. This preflight does not commission another search.");
 if (intent.action === "replacement_build") return result(false,
  item.installed ? "CAPABILITY_EXISTS" : item.ownerSession ? "EXISTING_BUILD_OWNER" : "RECONCILE_FIRST",
  item.installed ? "Reuse or extend the installed capability through its existing owner." :
   "A replacement is not a new commission. Route it to the existing owner; unassigned work needs reconciliation first.");
 if (intent.action === "continue") return result(!!item.replacementApproved && !!item.ownerSession && targetSession === item.ownerSession,
  "EXISTING_OWNER_CONTINUATION", "Approved implementation continues only in its existing owner session. Source closure does not close implementation or imply a test pass.");
 return result(false, "INVALID_ACTION", "Unknown action.");
}

/** A backstop for legacy free-text dispatches. Explicit metadata is the complete contract;
 * arbitrary natural-language/tool routes cannot be proven equivalent to that contract. */
export function legacyIntent(policy: WorkPolicy, text: string): WorkIntent | null {
 const lower = text.toLowerCase();
 const search = /\b(search|hunt|recover|find|locate)\b[^.!?\n]{0,140}\b(original|video|homework|replay|source|capstone|build 101)\b/i;
 const build = /^\s*(?:please\s+)?(?:build(?!\s+101\b)|commission|rebuild|create|implement)\b|\b(?:please|you must|need you to|want you to|your task is to)\s+(?:build(?!\s+101\b)|commission|rebuild|create|implement)\b/i;
 for (const sentence of lower.split(/[.!?\n;#]+|\b(?:and|but|then)\b/)) {
  if (/\b(?:do not|don't|never|stop)\s+(?:\w+\s+){0,2}(?:search|hunt|recover|find|locate|build|commission|rebuild|create|implement)\b|^\s*(?:no|closed|rejected)\b/.test(sentence)) continue;
  const item = policy.items.find(i => [i.id, ...i.aliases].some(a => sentence.includes(a.toLowerCase())));
  if (!item) continue;
  if (search.test(sentence)) return { action: "source_search", capabilityId: item.id };
  if (build.test(sentence)) return { action: "replacement_build", capabilityId: item.id };
 }
 for (const sentence of lower.split(/[.!?\n;#]+|\b(?:and|but|then)\b/)) {
  if (/\b(?:do not|don't|never|stop)\s+(?:\w+\s+){0,2}(?:search|hunt|recover|find|locate|build|commission|rebuild|create|implement)\b|^\s*(?:no|closed|rejected)\b/.test(sentence)) continue;
  if (/\b(search|hunt|recover|find|locate)\b.{0,140}\b(original|missing source|unrecovered source)\b/.test(sentence))
   return {action: "source_search", capabilityId: "unreconciled-source"};
  if (/\b(commission|start|create)\b.{0,140}\b(replacement build|reconstruction build|duplicate build)\b/.test(sentence))
   return {action: "replacement_build", capabilityId: "unreconciled-build"};
 }
 return null;
}
